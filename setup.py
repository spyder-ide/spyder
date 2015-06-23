# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder
======

The Scientific PYthon Development EnviRonment
"""

from __future__ import print_function

import os
import os.path as osp
import subprocess
import sys
import re
import shutil

from distutils.core import setup
from distutils.command.build import build
from distutils.command.install_data import install_data

# Check for Python 3
PY3 = sys.version_info[0] == 3

# This is necessary to prevent an error while installing Spyder with pip
# See http://stackoverflow.com/a/18961843/438386
with_setuptools = False
if 'USE_SETUPTOOLS' in os.environ or 'pip' in __file__ or \
  'VIRTUAL_ENV' in os.environ:
    try:
        from setuptools.command.install import install
        with_setuptools = True
    except:
        with_setuptools = False

if not with_setuptools:
    from distutils.command.install import install  # analysis:ignore


def get_package_data(name, extlist):
    """Return data files for package *name* with extensions in *extlist*"""
    flist = []
    # Workaround to replace os.path.relpath (not available until Python 2.6):
    offset = len(name)+len(os.pathsep)
    for dirpath, _dirnames, filenames in os.walk(name):
        for fname in filenames:
            if not fname.startswith('.') and osp.splitext(fname)[1] in extlist:
                flist.append(osp.join(dirpath, fname)[offset:])
    return flist


def get_subpackages(name):
    """Return subpackages of package *name*"""
    splist = []
    for dirpath, _dirnames, _filenames in os.walk(name):
        if osp.isfile(osp.join(dirpath, '__init__.py')):
            splist.append(".".join(dirpath.split(os.sep)))
    return splist


def get_data_files():
    """Return data_files in a platform dependent manner"""
    if sys.platform.startswith('linux'):
        if PY3:
            data_files = [('share/applications', ['scripts/spyder3.desktop']),
                          ('share/pixmaps', ['img_src/spyder3.png'])]
        else:
            data_files = [('share/applications', ['scripts/spyder.desktop']),
                          ('share/pixmaps', ['img_src/spyder.png'])]
    elif os.name == 'nt':
        data_files = [('scripts', ['img_src/spyder.ico',
                                   'img_src/spyder_light.ico'])]
    else:
        data_files = []
    return data_files


class MyInstallData(install_data):
    def run(self):
        install_data.run(self)
        if sys.platform.startswith('linux'):
            try:
                subprocess.call(['update-desktop-database'])
            except:
                print("ERROR: unable to update desktop database",
                      file=sys.stderr)
CMDCLASS = {'install_data': MyInstallData}


# Sphinx build (documentation)
def get_html_help_exe():
    """Return HTML Help Workshop executable path (Windows only)"""
    if os.name == 'nt':
        hhc_base = r'C:\Program Files%s\HTML Help Workshop\hhc.exe'
        for hhc_exe in (hhc_base % '', hhc_base % ' (x86)'):
            if osp.isfile(hhc_exe):
                return hhc_exe
        else:
            return

try:
    from sphinx import setup_command

    class MyBuild(build):
        user_options = [('no-doc', None, "Don't build Spyder documentation")] \
                       + build.user_options
        def __init__(self, *args, **kwargs):
            build.__init__(self, *args, **kwargs)
            self.no_doc = False
        def with_doc(self):
            setup_dir = os.path.dirname(os.path.abspath(__file__))
            is_doc_dir = os.path.isdir(os.path.join(setup_dir, 'doc'))
            install_obj = self.distribution.get_command_obj('install')
            return (is_doc_dir and not self.no_doc and not install_obj.no_doc)
        sub_commands = build.sub_commands + [('build_doc', with_doc)]
    CMDCLASS['build'] = MyBuild


    class MyInstall(install):
        user_options = [('no-doc', None, "Don't build Spyder documentation")] \
                       + install.user_options
        def __init__(self, *args, **kwargs):
            install.__init__(self, *args, **kwargs)
            self.no_doc = False
    CMDCLASS['install'] = MyInstall


    class MyBuildDoc(setup_command.BuildDoc):
        def run(self):
            build = self.get_finalized_command('build')
            sys.path.insert(0, os.path.abspath(build.build_lib))
            dirname = self.distribution.get_command_obj('build').build_purelib
            self.builder_target_dir = osp.join(dirname, 'spyderlib', 'doc')
            
            if not osp.exists(self.builder_target_dir):
                os.mkdir(self.builder_target_dir)

            hhc_exe = get_html_help_exe()
            self.builder = "html" if hhc_exe is None else "htmlhelp"

            try:
                setup_command.BuildDoc.run(self)
            except UnicodeDecodeError:
                print("ERROR: unable to build documentation because Sphinx "\
                      "do not handle source path with non-ASCII characters. "\
                      "Please try to move the source package to another "\
                      "location (path with *only* ASCII characters).",
                      file=sys.stderr)
            sys.path.pop(0)
            
            # Building chm doc, if HTML Help Workshop is installed
            if hhc_exe is not None:
                fname = osp.join(self.builder_target_dir, 'Spyderdoc.chm')
                subprocess.call('"%s" %s' % (hhc_exe, fname), shell=True)
                if osp.isfile(fname):
                    dest = osp.join(dirname, 'spyderlib')
                    try:
                        shutil.move(fname, dest)
                    except shutil.Error:
                        print("Unable to replace %s" % dest)
                    shutil.rmtree(self.builder_target_dir)

    CMDCLASS['build_doc'] = MyBuildDoc
except ImportError:
    print('WARNING: unable to build documentation because Sphinx '\
          'is not installed', file=sys.stderr)


NAME = 'spyder'
LIBNAME = 'spyderlib'
from spyderlib import __version__, __project_url__


JOINEDARGS = ''.join(sys.argv)
WINDOWS_INSTALLER = 'bdist_wininst' in JOINEDARGS or 'bdist_msi' in JOINEDARGS
TARGET_MATCH = re.search(r'--target-version=([0-9]*)\.([0-9]*)', JOINEDARGS)
if TARGET_MATCH:
    TARGET_VERSION = TARGET_MATCH.groups()
else:
    TARGET_VERSION = (str(sys.version_info[0]), str(sys.version_info[1]))


def get_packages():
    """Return package list"""
    if WINDOWS_INSTALLER:
        # Adding pyflakes and rope to the package if available in the 
        # repository (this is not conventional but Spyder really need 
        # those tools and there is not decent package manager on 
        # Windows platforms, so...)
        import shutil
        import atexit
        extdir = 'external-py' + TARGET_VERSION[0]
        for name in ('rope', 'pyflakes'):
            srcdir = osp.join(extdir, name)
            if osp.isdir(srcdir):
                dstdir = osp.join(LIBNAME, 'utils', 'external', name)
                shutil.copytree(srcdir, dstdir)
                atexit.register(shutil.rmtree, osp.abspath(dstdir))
    packages = get_subpackages(LIBNAME)+get_subpackages('spyderplugins')
    return packages

# NOTE: the '[...]_win_post_install.py' script is installed even on non-Windows
# platforms due to a bug in pip installation process (see Issue 1158)
SCRIPTS = ['%s_win_post_install.py' % NAME]
if PY3 and sys.platform.startswith('linux'):
    SCRIPTS.append('spyder3')
else:
    SCRIPTS.append('spyder')
EXTLIST = ['.mo', '.svg', '.png', '.css', '.html', '.js', '.chm', '.ini',
           '.txt', '.rst', '.qss']
if os.name == 'nt':
    SCRIPTS += ['spyder.bat']
    EXTLIST += ['.ico']

# Adding a message for the Windows installers
WININST_MSG = ""
if WINDOWS_INSTALLER:
    WININST_MSG = \
"""Please uninstall any previous version of Spyder before continue.

"""


setup(name=NAME,
      version=__version__,
      description='Scientific PYthon Development EnviRonment',
      long_description=WININST_MSG + \
"""Spyder is an interactive Python development environment providing 
MATLAB-like features in a simple and light-weighted software.
It also provides ready-to-use pure-Python widgets to your PyQt4 or 
PySide application: source code editor with syntax highlighting and 
code introspection/analysis features, NumPy array editor, dictionary 
editor, Python console, etc.""",
      download_url='%s/files/%s-%s.zip' % (__project_url__, NAME, __version__),
      author="Pierre Raybaut",
      url=__project_url__,
      license='MIT',
      keywords='PyQt4 PySide editor shell console widgets IDE',
      platforms=['any'],
      packages=get_packages(),
      package_data={LIBNAME: get_package_data(LIBNAME, EXTLIST),
                    'spyderplugins':
                    get_package_data('spyderplugins', EXTLIST)},
      requires=["rope (>=0.9.2)", "sphinx (>=0.6.0)", "PyQt4 (>=4.4)"],
      scripts=[osp.join('scripts', fname) for fname in SCRIPTS],
      data_files=get_data_files(),
      options={"bdist_wininst":
               {"install_script": "%s_win_post_install.py" % NAME,
                "title": "%s %s" % (NAME.capitalize(), __version__),
                "bitmap": osp.join('img_src', 'spyder-bdist_wininst.bmp'),
                "target_version": '%s.%s' % TARGET_VERSION,
                "user_access_control": "auto"},
               "bdist_msi":
               {"install_script": "%s_win_post_install.py" % NAME}},
      classifiers=['License :: OSI Approved :: MIT License',
                   'Operating System :: MacOS',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: OS Independent',
                   'Operating System :: POSIX',
                   'Operating System :: Unix',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Development Status :: 5 - Production/Stable',
                   'Topic :: Scientific/Engineering',
                   'Topic :: Software Development :: Widget Sets'],
      cmdclass=CMDCLASS)
