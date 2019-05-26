# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder base configuration management

This file only deals with non-GUI configuration features
(in other words, we won't import any PyQt object here, avoiding any
sip API incompatibility issue in spyder's non-gui modules)
"""

from __future__ import print_function

import codecs
import getpass
import locale
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
import warnings

# Local imports
from spyder import __version__
from spyder.utils import encoding
from spyder.py3compat import (is_unicode, TEXT_TYPES, INT_TYPES, PY3,
                              to_text_string, is_text_string)


#==============================================================================
# Only for development
#==============================================================================
# To activate/deactivate certain things for development
# SPYDER_DEV is (and *only* has to be) set in bootstrap.py
DEV = os.environ.get('SPYDER_DEV')

# Manually override whether the dev configuration directory is used.
USE_DEV_CONFIG_DIR = os.environ.get('SPYDER_USE_DEV_CONFIG_DIR')

# Make Spyder use a temp clean configuration directory for testing purposes
# SPYDER_SAFE_MODE can be set using the --safe-mode option of bootstrap.py
SAFE_MODE = os.environ.get('SPYDER_SAFE_MODE')


def running_under_pytest():
    """
    Return True if currently running under py.test.

    This function is used to do some adjustment for testing. The environment
    variable SPYDER_PYTEST is defined in conftest.py.
    """
    return bool(os.environ.get('SPYDER_PYTEST'))


def is_stable_version(version):
    """
    Return true if version is stable, i.e. with letters in the final component.

    Stable version examples: ``1.2``, ``1.3.4``, ``1.0.5``.
    Non-stable version examples: ``1.3.4beta``, ``0.1.0rc1``, ``3.0.0dev0``.
    """
    if not isinstance(version, tuple):
        version = version.split('.')
    last_part = version[-1]

    if not re.search(r'[a-zA-Z]', last_part):
        return True
    else:
        return False


def use_dev_config_dir(use_dev_config_dir=USE_DEV_CONFIG_DIR):
    """Return whether the dev configuration directory should used."""
    if use_dev_config_dir is not None:
        if use_dev_config_dir.lower() in {'false', '0'}:
            use_dev_config_dir = False
    else:
        use_dev_config_dir = DEV or not is_stable_version(__version__)
    return use_dev_config_dir


#==============================================================================
# Debug helpers
#==============================================================================
# This is needed after restarting and using debug_print
STDOUT = sys.stdout if PY3 else codecs.getwriter('utf-8')(sys.stdout)
STDERR = sys.stderr


def get_debug_level():
    debug_env = os.environ.get('SPYDER_DEBUG', '')
    if not debug_env.isdigit():
        debug_env = bool(debug_env)
    return int(debug_env)


def debug_print(*message):
    """Output debug messages to stdout"""
    warnings.warn("debug_print is deprecated; use the logging module instead.")
    if get_debug_level():
        ss = STDOUT
        if PY3:
            # This is needed after restarting and using debug_print
            for m in message:
                ss.buffer.write(str(m).encode('utf-8'))
            print('', file=ss)
        else:
            print(*message, file=ss)


#==============================================================================
# Configuration paths
#==============================================================================
# Spyder settings dir
# NOTE: During the 2.x.x series this dir was named .spyder2, but
# since 3.0+ we've reverted back to use .spyder to simplify major
# updates in version (required when we change APIs by Linux
# packagers)
if sys.platform.startswith('linux'):
    SUBFOLDER = 'spyder'
else:
    SUBFOLDER = '.spyder'


# We can't have PY2 and PY3 settings in the same dir because:
# 1. This leads to ugly crashes and freezes (e.g. by trying to
#    embed a PY2 interpreter in PY3)
# 2. We need to save the list of installed modules (for code
#    completion) separately for each version
if PY3:
    SUBFOLDER = SUBFOLDER + '-py3'


# If running a development/beta version, save config in a seperate directory
# to avoid wiping or contaiminating the user's saved stable configuration.
if use_dev_config_dir():
    SUBFOLDER = SUBFOLDER + '-dev'


def get_home_dir():
    """
    Return user home directory
    """
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent
        # file paths.
        path = encoding.to_unicode_from_fs(osp.expanduser('~'))
    except Exception:
        path = ''

    if osp.isdir(path):
        return path
    else:
        # Get home from alternative locations
        for env_var in ('HOME', 'USERPROFILE', 'TMP'):
            # os.environ.get() returns a raw byte string which needs to be
            # decoded with the codec that the OS is using to represent
            # environment variables.
            path = encoding.to_unicode_from_fs(os.environ.get(env_var, ''))
            if osp.isdir(path):
                return path
            else:
                path = ''

        if not path:
            raise RuntimeError('Please set the environment variable HOME to '
                               'your user/home directory path so Spyder can '
                               'start properly.')


def get_clean_conf_dir():
    """
    Return the path to a temp clean configuration dir, for tests and safe mode.
    """
    if sys.platform.startswith("win"):
        current_user = ''
    else:
        current_user = '-' + str(getpass.getuser())

    conf_dir = osp.join(str(tempfile.gettempdir()),
                        'pytest-spyder{0!s}'.format(current_user),
                        SUBFOLDER)
    return conf_dir


def get_conf_path(filename=None):
    """Return absolute path to the config file with the specified filename."""
    # Define conf_dir
    if running_under_pytest() or SAFE_MODE:
        # Use clean config dir if running tests or the user requests it.
        conf_dir = get_clean_conf_dir()
    elif sys.platform.startswith('linux'):
        # This makes us follow the XDG standard to save our settings
        # on Linux, as it was requested on Issue 2629
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME', '')
        if not xdg_config_home:
            xdg_config_home = osp.join(get_home_dir(), '.config')
        if not osp.isdir(xdg_config_home):
            os.makedirs(xdg_config_home)
        conf_dir = osp.join(xdg_config_home, SUBFOLDER)
    else:
        conf_dir = osp.join(get_home_dir(), SUBFOLDER)

    # Create conf_dir
    if not osp.isdir(conf_dir):
        if running_under_pytest() or SAFE_MODE:
            os.makedirs(conf_dir)
        else:
            os.mkdir(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)


def get_module_path(modname):
    """Return module *modname* base path"""
    return osp.abspath(osp.dirname(sys.modules[modname].__file__))


def get_module_data_path(modname, relpath=None, attr_name='DATAPATH'):
    """Return module *modname* data path
    Note: relpath is ignored if module has an attribute named *attr_name*

    Handles py2exe/cx_Freeze distributions"""
    datapath = getattr(sys.modules[modname], attr_name, '')
    if datapath:
        return datapath
    else:
        datapath = get_module_path(modname)
        parentdir = osp.join(datapath, osp.pardir)
        if osp.isfile(parentdir):
            # Parent directory is not a directory but the 'library.zip' file:
            # this is either a py2exe or a cx_Freeze distribution
            datapath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                            modname))
        if relpath is not None:
            datapath = osp.abspath(osp.join(datapath, relpath))
        return datapath


def get_module_source_path(modname, basename=None):
    """Return module *modname* source path
    If *basename* is specified, return *modname.basename* path where
    *modname* is a package containing the module *basename*

    *basename* is a filename (not a module name), so it must include the
    file extension: .py or .pyw

    Handles py2exe/cx_Freeze distributions"""
    srcpath = get_module_path(modname)
    parentdir = osp.join(srcpath, osp.pardir)
    if osp.isfile(parentdir):
        # Parent directory is not a directory but the 'library.zip' file:
        # this is either a py2exe or a cx_Freeze distribution
        srcpath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                       modname))
    if basename is not None:
        srcpath = osp.abspath(osp.join(srcpath, basename))
    return srcpath


def is_py2exe_or_cx_Freeze():
    """Return True if this is a py2exe/cx_Freeze distribution of Spyder"""
    return osp.isfile(osp.join(get_module_path('spyder'), osp.pardir))


#==============================================================================
# Image path list
#==============================================================================
IMG_PATH = []
def add_image_path(path):
    if not osp.isdir(path):
        return
    global IMG_PATH
    IMG_PATH.append(path)
    for dirpath, dirnames, _filenames in os.walk(path):
        for dirname in dirnames:
            IMG_PATH.append(osp.join(dirpath, dirname))

add_image_path(get_module_data_path('spyder', relpath='images'))

def get_image_path(name, default="not_found.png"):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        img_path = osp.join(get_module_path('spyder'), 'images')
        return osp.abspath(osp.join(img_path, default))


#==============================================================================
# Translations
#==============================================================================
LANG_FILE = get_conf_path('langconfig')
DEFAULT_LANGUAGE = 'en'

# This needs to be updated every time a new language is added to spyder, and is
# used by the Preferences configuration to populate the Language QComboBox
LANGUAGE_CODES = {'en': u'English',
                  'fr': u'Français',
                  'es': u'Español',
                  'hu': u'Magyar',
                  'pt_BR': u'Português',
                  'ru': u'Русский',
                  'zh_CN': u'简体中文',
                  'ja': u'日本語',
                  'de': u'Deutsch'
                  }

# Disabled languages (because their translations are outdated)
DISABLED_LANGUAGES = []

def get_available_translations():
    """
    List available translations for spyder based on the folders found in the
    locale folder. This function checks if LANGUAGE_CODES contain the same
    information that is found in the 'locale' folder to ensure that when a new
    language is added, LANGUAGE_CODES is updated.
    """
    locale_path = get_module_data_path("spyder", relpath="locale",
                                       attr_name='LOCALEPATH')
    listdir = os.listdir(locale_path)
    langs = [d for d in listdir if osp.isdir(osp.join(locale_path, d))]
    langs = [DEFAULT_LANGUAGE] + langs

    # Remove disabled languages
    langs = list( set(langs) - set(DISABLED_LANGUAGES) )

    # Check that there is a language code available in case a new translation
    # is added, to ensure LANGUAGE_CODES is updated.
    for lang in langs:
        if lang not in LANGUAGE_CODES:
            error = ('Update LANGUAGE_CODES (inside config/base.py) if a new '
                     'translation has been added to Spyder')
            print(error)  # spyder: test-skip
            return ['en']
    return langs


def get_interface_language():
    """
    If Spyder has a translation available for the locale language, it will
    return the version provided by Spyder adjusted for language subdifferences,
    otherwise it will return DEFAULT_LANGUAGE.

    Example:
    1.) Spyder provides ('en',  'de', 'fr', 'es' 'hu' and 'pt_BR'), if the
    locale is either 'en_US' or 'en' or 'en_UK', this function will return 'en'

    2.) Spyder provides ('en',  'de', 'fr', 'es' 'hu' and 'pt_BR'), if the
    locale is either 'pt' or 'pt_BR', this function will return 'pt_BR'
    """

    # Solves issue #3627
    try:
        locale_language = locale.getdefaultlocale()[0]
    except ValueError:
        locale_language = DEFAULT_LANGUAGE

    # Tests expect English as the interface language
    if running_under_pytest():
        locale_language = DEFAULT_LANGUAGE

    language = DEFAULT_LANGUAGE

    if locale_language is not None:
        spyder_languages = get_available_translations()
        for lang in spyder_languages:
            if locale_language == lang:
                language = locale_language
                break
            elif locale_language.startswith(lang) or \
              lang.startswith(locale_language):
                language = lang
                break

    return language


def save_lang_conf(value):
    """Save language setting to language config file"""
    # Needed to avoid an error when trying to save LANG_FILE
    # but the operation fails for some reason.
    # See issue 8807
    try:
        with open(LANG_FILE, 'w') as f:
            f.write(value)
    except EnvironmentError:
        pass


def load_lang_conf():
    """
    Load language setting from language config file if it exists, otherwise
    try to use the local settings if Spyder provides a translation, or
    return the default if no translation provided.
    """
    if osp.isfile(LANG_FILE):
        with open(LANG_FILE, 'r') as f:
            lang = f.read()
    else:
        lang = get_interface_language()
        save_lang_conf(lang)

    # Save language again if it's been disabled
    if lang.strip('\n') in DISABLED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
        save_lang_conf(lang)

    return lang


def get_translation(modname, dirname=None):
    """Return translation callback for module *modname*"""
    if dirname is None:
        dirname = modname

    def translate_dumb(x):
        """Dumb function to not use translations."""
        if not is_unicode(x):
            return to_text_string(x, "utf-8")
        return x

    locale_path = get_module_data_path(dirname, relpath="locale",
                                       attr_name='LOCALEPATH')

    # If LANG is defined in Ubuntu, a warning message is displayed,
    # so in Unix systems we define the LANGUAGE variable.
    language = load_lang_conf()
    if os.name == 'nt':
        # Trying to set LANG on Windows can fail when Spyder is
        # run with admin privileges.
        # Fixes issue 6886
        try:
            os.environ["LANG"] = language      # Works on Windows
        except Exception:
            return translate_dumb
    else:
        os.environ["LANGUAGE"] = language  # Works on Linux

    import gettext
    try:
        _trans = gettext.translation(modname, locale_path, codeset="utf-8")
        lgettext = _trans.lgettext
        def translate_gettext(x):
            if not PY3 and is_unicode(x):
                x = x.encode("utf-8")
            y = lgettext(x)
            if is_text_string(y) and PY3:
                return y
            else:
                return to_text_string(y, "utf-8")
        return translate_gettext
    except Exception:
        return translate_dumb

# Translation callback
_ = get_translation("spyder")


#==============================================================================
# Namespace Browser (Variable Explorer) configuration management
#==============================================================================
# Variable explorer display / check all elements data types for sequences:
# (when saving the variable explorer contents, check_all is True,
CHECK_ALL = False #XXX: If True, this should take too much to compute...

EXCLUDED_NAMES = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc',
                  'typecodes', '__builtins__', '__main__', '__doc__', 'NaN',
                  'Inf', 'Infinity', 'sctypes', 'rcParams', 'rcParamsDefault',
                  'sctypeNA', 'typeNA', 'False_', 'True_',]

# To be able to get and set variables between Python 2 and 3
PICKLE_PROTOCOL = 2


#==============================================================================
# Mac application utilities
#==============================================================================
if PY3:
    MAC_APP_NAME = 'Spyder.app'
else:
    MAC_APP_NAME = 'Spyder-Py2.app'

def running_in_mac_app():
    if sys.platform == "darwin" and MAC_APP_NAME in __file__:
        return True
    else:
        return False


#==============================================================================
# Reset config files
#==============================================================================
SAVED_CONFIG_FILES = ('help', 'onlinehelp', 'path', 'pylint.results',
                      'spyder.ini', 'temp.py', 'temp.spydata', 'template.py',
                      'history.py', 'history_internal.py', 'workingdir',
                      '.projects', '.spyproject', '.ropeproject',
                      'monitor.log', 'monitor_debug.log', 'rope.log',
                      'langconfig', 'spyder.lock')


def reset_config_files():
    """Remove all config files"""
    print("*** Reset Spyder settings to defaults ***", file=STDERR)
    for fname in SAVED_CONFIG_FILES:
        cfg_fname = get_conf_path(fname)
        if osp.isfile(cfg_fname) or osp.islink(cfg_fname):
            os.remove(cfg_fname)
        elif osp.isdir(cfg_fname):
            shutil.rmtree(cfg_fname)
        else:
            continue
        print("removing:", cfg_fname, file=STDERR)
