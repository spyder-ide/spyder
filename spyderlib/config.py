# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder GUI-related configuration management
(for non-GUI configuration, see spyderlib/baseconfig.py)

Important note regarding shortcuts:
    For compatibility with QWERTZ keyboards, one must avoid using the following
    shortcuts:
        Ctrl + Alt + Q, W, F, G, Y, X, C, V, B, N
"""

import os
import sys
import os.path as osp

from spyderlib.qt.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

# Local import
from spyderlib.userconfig import UserConfig, get_home_dir, NoDefault
from spyderlib.baseconfig import (SUBFOLDER, CHECK_ALL, EXCLUDED_NAMES,
                                  get_module_data_path, _)
from spyderlib.utils import iofuncs, codeanalysis


SANS_SERIF = ['Sans Serif', 'DejaVu Sans', 'Bitstream Vera Sans',
              'Bitstream Charter', 'Times', 'Lucida Grande', 'Calibri',
              'MS Shell Dlg 2', 'Verdana', 'Geneva', 'Lucid', 'Arial',
              'Helvetica', 'Avant Garde', 'sans-serif']

MONOSPACE = ['Monospace', 'DejaVu Sans Mono', 'Consolas', 'Monaco',
             'Bitstream Vera Sans Mono', 'Andale Mono', 'Liberation Mono',
             'Courier New', 'Courier', 'monospace', 'Fixed', 'Terminal']

if sys.platform == 'darwin':
    BIG = MEDIUM = SMALL = 12
elif os.name == 'nt':
    BIG = 12    
    MEDIUM = 10
    SMALL = 9
else:
    BIG = 12    
    MEDIUM = 9
    SMALL = 9

# Extensions supported by Spyder's Editor
EDIT_FILETYPES = (
    (_("Python files"), ('.py', '.pyw', '.ipy')),
    (_("Cython/Pyrex files"), ('.pyx', '.pxd', '.pxi')),
    (_("C files"), ('.c', '.h')),
    (_("C++ files"), ('.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx')),
    (_("OpenCL files"), ('.cl', )),
    (_("Fortran files"), ('.f', '.for', '.f77', '.f90', '.f95', '.f2k')),
    (_("IDL files"), ('.pro', )),
    (_("Patch and diff files"), ('.patch', '.diff', '.rej')),
    (_("Batch files"), ('.bat', '.cmd')),
    (_("Text files"), ('.txt',)),
    (_("reStructured Text files"), ('.txt', '.rst')),
    (_("gettext files"), ('.po', '.pot')),
    (_("Web page files"), ('.css', '.htm', '.html',)),
    (_("Configuration files"), ('.properties', '.session', '.ini', '.inf',
                                '.reg', '.cfg', '.desktop')),
                 )

def _get_filters(filetypes):
    filters = []
    for title, ftypes in filetypes:
        filters.append("%s (*%s)" % (title, " *".join(ftypes)))
    filters.append("%s (*)" % _("All files"))
    return ";;".join(filters)

def _get_extensions(filetypes):
    ftype_list = []
    for _title, ftypes in filetypes:
        ftype_list += list(ftypes)
    return ftype_list

EDIT_FILTERS = _get_filters(EDIT_FILETYPES)
EDIT_EXT = _get_extensions(EDIT_FILETYPES)+['']

# Extensions supported by Spyder's Variable explorer
IMPORT_EXT = iofuncs.iofunctions.load_extensions.values()

# Extensions that should be visible in Spyder's file/project explorers
SHOW_EXT = ['.png', '.ico', '.svg']

# Extensions supported by Spyder (Editor or Variable explorer)
VALID_EXT = EDIT_EXT+IMPORT_EXT

# Find in files include/exclude patterns
INCLUDE_PATTERNS = [r'|'.join(['\\'+_ext+r'$' for _ext in EDIT_EXT if _ext])+\
                    r'|README|INSTALL',
                    r'\.pyw?$|\.ipy$|\.txt$|\.rst$',
                    '.']
EXCLUDE_PATTERNS = [r'\.pyc$|\.pyo$|\.orig$|\.hg|\.svn|build',
                    r'\.pyc$|\.pyo$|\.orig$|\.hg|\.svn']

# Name filters for file/project explorers (excluding files without extension)
NAME_FILTERS = ['*' + _ext for _ext in VALID_EXT + SHOW_EXT if _ext]+\
               ['README', 'INSTALL', 'LICENSE', 'CHANGELOG']

DEFAULTS = [
            ('main',
             {
              'vertical_dockwidget_titlebars': False,
              'vertical_tabs': False,
              'animated_docks': True,
              'window/size': (1260, 740),
              'window/position': (10, 10),
              'window/is_maximized': False,
              'window/is_fullscreen': False,
              'window/prefs_dialog_size': (745, 411),
              'lightwindow/size': (650, 400),
              'lightwindow/position': (30, 30),
              'lightwindow/is_maximized': False,
              'lightwindow/is_fullscreen': False,
              'memory_usage/enable': True,
              'memory_usage/timeout': 2000,
              'cpu_usage/enable': False,
              'cpu_usage/timeout': 2000,
              }),
            ('quick_layouts',
             {
              'place_holder': '',
              }),
            ('editor_appearance',
             {
              'cursor/width': 2,
              'calltips/font/family': MONOSPACE,
              'calltips/font/size': SMALL,
              'calltips/font/italic': False,
              'calltips/font/bold': False,
              'calltips/size': 600,
              'completion/font/family': MONOSPACE,
              'completion/font/size': SMALL,
              'completion/font/italic': False,
              'completion/font/bold': False,
              'completion/size': (300, 180),
              }),
            ('shell_appearance',
             {
              'cursor/width': 2,
              'calltips/font/family': MONOSPACE,
              'calltips/font/size': SMALL,
              'calltips/font/italic': False,
              'calltips/font/bold': False,
              'calltips/size': 600,
              'completion/font/family': MONOSPACE,
              'completion/font/size': SMALL,
              'completion/font/italic': False,
              'completion/font/bold': False,
              'completion/size': (300, 180),
              }),
            ('internal_console',
             {
              'max_line_count': 300,
              'working_dir_history': 30,
              'working_dir_adjusttocontents': False,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'calltips': True,
              'codecompletion/auto': False,
              'codecompletion/enter_key': True,
              'codecompletion/case_sensitive': True,
              'codecompletion/show_single': False,
              'external_editor/path': 'SciTE',
              'external_editor/gotoline': '-goto:',
              'light_background': True,
              }),
            ('console',
             {
              'shortcut': "Ctrl+Shift+C",
              'max_line_count': 10000,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'single_tab': True,
              'calltips': True,
              'object_inspector': True,
              'codecompletion/auto': True,
              'codecompletion/enter_key': True,
              'codecompletion/case_sensitive': True,
              'codecompletion/show_single': False,
              'show_elapsed_time': True,
              'show_icontext': False,
              'monitor/enabled': True,
              'qt/install_inputhook': os.name == 'nt' \
                                      or os.environ.get('QT_API') == 'pyside',
              'qt/api': 'default',
              'pyqt/api_version': 0,
              'pyqt/ignore_sip_setapi_errors': False,
              'matplotlib/patch': True,
              'matplotlib/backend/enabled': True,
              'matplotlib/backend/value': 'Qt4Agg',
              'umd/enabled': True,
              'umd/verbose': True,
              'umd/namelist': ['guidata', 'guiqwt'],
              'light_background': True,
              'merge_output_channels': os.name != 'nt',
              'colorize_sys_stderr': os.name != 'nt',
              }),
            ('ipython_console',
             {
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'show_banner': True,
              'use_gui_completion': True,
              'use_pager': True,
              'show_calltips': False,
              'ask_before_closing': True,
              'light_color': True,
              'dark_color': False,
              'buffer_size': 10000,
              'pylab': True,
              'pylab/autoload': True,
              'pylab/backend': 0,
              'pylab/inline/figure_format': 0,
              'pylab/inline/resolution': 72,
              'pylab/inline/width': 6,
              'pylab/inline/height': 4,
              'startup/run_lines': '',
              'startup/use_run_file': False,
              'startup/run_file': ''
              }),
            ('variable_explorer',
             {
              'shortcut': "Ctrl+Shift+V",
              'autorefresh': True,
              'autorefresh/timeout': 2000,
              'check_all': CHECK_ALL,
              'excluded_names': EXCLUDED_NAMES,
              'exclude_private': True,
              'exclude_uppercase': True,
              'exclude_capitalized': False,
              'exclude_unsupported': True,
              'inplace': False,
              'truncate': True,
              'minmax': False,
              'collvalue': False,
              'remote_editing': False,
              }),
            ('editor',
             {
              'shortcut': "Ctrl+Shift+E",
              'printer_header/font/family': SANS_SERIF,
              'printer_header/font/size': MEDIUM,
              'printer_header/font/italic': False,
              'printer_header/font/bold': False,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': False,
              'wrapflag': True,
              'code_analysis/pyflakes': True,
              'code_analysis/pep8': False,
              'todo_list': True,
              'realtime_analysis': True,
              'realtime_analysis/timeout': 2500,
              'outline_explorer': True,
              'line_numbers': True,
              'edge_line': True,
              'edge_line_column': 79,
              'toolbox_panel': True,
              'calltips': True,
              'go_to_definition': True,
              'close_parentheses': True,
              'close_quotes': False,
              'add_colons': True,
              'auto_unindent': True,
              'indent_chars': '*    *',
              'tab_stop_width': 40,
              'object_inspector': True,
              'codecompletion/auto': True,
              'codecompletion/enter_key': True,
              'codecompletion/case_sensitive': True,
              'codecompletion/show_single': False,
              'check_eol_chars': True,
              'tab_always_indent': False,
              'intelligent_backspace': True,
              'highlight_current_line': True,
              'occurence_highlighting': True,
              'occurence_highlighting/timeout': 1500,
              'always_remove_trailing_spaces': False,
              'fullpath_sorting': True,
              'show_tab_bar': True,
              'max_recent_files': 20,
              }),
            ('historylog',
             {
              'shortcut': "Ctrl+Shift+H",
              'enable': True,
              'max_entries': 100,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'go_to_eof': True,
              }),
            ('inspector',
             {
              'shortcut': "Ctrl+Shift+I",
              'enable': True,
              'max_history_entries': 20,
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              'rich_text/font/family': SANS_SERIF,
              'rich_text/font/size': BIG,
              'rich_text/font/italic': False,
              'rich_text/font/bold': False,
              'wrap': True,
              'math': True,
              'automatic_import': True,
              }),
            ('onlinehelp',
             {
              'shortcut': "Ctrl+Shift+D",
              'enable': True,
              'zoom_factor': .8,
              'max_history_entries': 20,
              }),
            ('outline_explorer',
             {
              'shortcut': "Ctrl+Shift+O",
              'enable': True,
              }),
            ('project_explorer',
             {
              'shortcut': "Ctrl+Shift+P",
              'enable': True,
              'name_filters': NAME_FILTERS,
              'show_all': False,
              }),
            ('arrayeditor',
             {
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              }),
            ('texteditor',
             {
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              }),
            ('dicteditor',
             {
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              }),
            ('explorer',
             {
              'enable': True,
              'wrap': True,
              'name_filters': NAME_FILTERS,
              'show_hidden': True,
              'show_all': False,
              'show_toolbar': True,
              'show_icontext': True,
              }),
            ('find_in_files',
             {
              'enable': True,
              'supported_encodings': ["utf-8", "iso-8859-1", "cp1252"],
              'include': INCLUDE_PATTERNS,
              'include_regexp': True,
              'exclude': EXCLUDE_PATTERNS,
              'exclude_regexp': True,
              'search_text_regexp': True,
              'search_text': [''],
              'search_text_samples': [codeanalysis.TASKS_PATTERN],
              'in_python_path': False,
              'more_options': True,
              }),
            ]

DEV = not __file__.startswith(sys.prefix)
DEV = False
CONF = UserConfig('spyder', defaults=DEFAULTS, load=(not DEV), version='2.4.0',
                  subfolder=SUBFOLDER, backup=True, raw_mode=True)
# Removing old .spyder.ini location:
old_location = osp.join(get_home_dir(), '.spyder.ini')
if osp.isfile(old_location):
    os.remove(old_location)


IMG_PATH = []
def add_image_path(path):
    if not osp.isdir(path):
        return
    global IMG_PATH
    IMG_PATH.append(path)
    for _root, dirs, _files in os.walk(path):
        for dir in dirs:
            IMG_PATH.append(osp.join(path, dir))

add_image_path(get_module_data_path('spyderlib', relpath='images'))

from spyderlib.otherplugins import PLUGIN_PATH
if PLUGIN_PATH is not None:
    add_image_path(osp.join(PLUGIN_PATH, 'images'))


def get_image_path(name, default="not_found.png"):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        return osp.abspath(osp.join(img_path, default))

def get_icon( name, default=None ):
    """Return image inside a QIcon object"""
    if default is None:
        return QIcon(get_image_path(name))
    elif isinstance(default, QIcon):
        icon_path = get_image_path(name, default=None)
        return default if icon_path is None else QIcon(icon_path)
    else:
        return QIcon(get_image_path(name, default))

def get_image_label( name, default="not_found.png" ):
    """Return image inside a QLabel object"""
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label

def font_is_installed(font):
    """Check if font is installed"""
    return [fam for fam in QFontDatabase().families() if unicode(fam)==font]
    
def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [ families ]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print "Warning: None of the following fonts is installed: %r" % families
        return QFont().family()
    
FONT_CACHE = {}
def get_font(section, option=None):
    """Get console font properties depending on OS and user options"""
    font = FONT_CACHE.get((section, option))
    if font is None:
        if option is None:
            option = 'font'
        else:
            option += '/font'
        families = CONF.get(section, option+"/family", None)
        if families is None:
            return QFont()
        family = get_family(families)
        weight = QFont.Normal
        italic = CONF.get(section, option+'/italic', False)
        if CONF.get(section, option+'/bold', False):
            weight = QFont.Bold
        size = CONF.get(section, option+'/size', 9)
        font = QFont(family, size, weight)
        font.setItalic(italic)
        FONT_CACHE[(section, option)] = font
    return font

def set_font(font, section, option=None):
    """Set font"""
    if option is None:
        option = 'font'
    else:
        option += '/font'
    CONF.set(section, option+'/family', unicode(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/italic', int(font.italic()))
    CONF.set(section, option+'/bold', int(font.bold()))
    FONT_CACHE[(section, option)] = font


def get_shortcut(context, name, default=NoDefault):
    """Get keyboard shortcut (key sequence string)"""
    return CONF.get('shortcuts', '%s/%s' % (context, name), default=default)

def set_shortcut(context, name, keystr):
    """Set keyboard shortcut (key sequence string)"""
    CONF.set('shortcuts', '%s/%s' % (context, name), keystr)
    
def iter_shortcuts():
    """Iterate over keyboard shortcuts"""
    for option in CONF.options('shortcuts'):
        context, name = option.split("/", 1)
        yield context, name, get_shortcut(context, name)
        
def reset_shortcuts():
    """Reset keyboard shortcuts to default values"""
    CONF.remove_section('shortcuts')


from spyderlib.widgets.sourcecode.syntaxhighlighters import (
                                COLOR_SCHEME_KEYS, COLOR_SCHEME_NAMES, COLORS)
def get_color_scheme(name):
    """Get syntax color scheme"""
    color_scheme = {}
    for key in COLOR_SCHEME_KEYS:
        color_scheme[key] = CONF.get("color_schemes", "%s/%s" % (name, key))
    return color_scheme

def set_color_scheme(name, color_scheme, replace=True):
    """Set syntax color scheme"""
    section = "color_schemes"
    names = CONF.get("color_schemes", "names", [])
    for key in COLOR_SCHEME_KEYS:
        option = "%s/%s" % (name, key)
        value = CONF.get(section, option, default=None)
        if value is None or replace or name not in names:
            CONF.set(section, option, color_scheme[key])
    names.append(unicode(name))
    CONF.set(section, "names", sorted(list(set(names))))

def set_default_color_scheme(name, replace=True):
    """Reset color scheme to default values"""
    assert name in COLOR_SCHEME_NAMES
    set_color_scheme(name, COLORS[name], replace=replace)

for _name in COLOR_SCHEME_NAMES:
    set_default_color_scheme(_name, replace=False)
CUSTOM_COLOR_SCHEME_NAME = "Custom"
set_color_scheme(CUSTOM_COLOR_SCHEME_NAME, COLORS["Spyder"], replace=False)
