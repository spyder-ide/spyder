# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder configuration options

Note: Leave this file free of Qt related imports, so that it can be used to
quickly load a user config file
"""

import os
import sys
import os.path as osp

# Local import
from spyderlib.userconfig import UserConfig
from spyderlib.baseconfig import (CHECK_ALL, EXCLUDED_NAMES, SUBFOLDER,
                                  get_home_dir, _)
from spyderlib.utils import iofuncs, codeanalysis


#==============================================================================
# Extensions supported by Spyder's Editor
#==============================================================================
EDIT_FILETYPES = (
    (_("Python files"), ('.py', '.pyw', '.ipy')),
    (_("Cython/Pyrex files"), ('.pyx', '.pxd', '.pxi')),
    (_("C files"), ('.c', '.h')),
    (_("C++ files"), ('.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx')),
    (_("OpenCL files"), ('.cl', )),
    (_("Fortran files"), ('.f', '.for', '.f77', '.f90', '.f95', '.f2k')),
    (_("IDL files"), ('.pro', )),
    (_("MATLAB files"), ('.m', )),
    (_("Julia files"), ('.jl',)),
    (_("Yaml files"), ('.yaml','.yml',)),
    (_("Patch and diff files"), ('.patch', '.diff', '.rej')),
    (_("Batch files"), ('.bat', '.cmd')),
    (_("Text files"), ('.txt',)),
    (_("reStructured Text files"), ('.txt', '.rst')),
    (_("gettext files"), ('.po', '.pot')),
    (_("NSIS files"), ('.nsi', '.nsh')),
    (_("Web page files"), ('.css', '.htm', '.html',)),
    (_("XML files"), ('.xml',)),
    (_("Javascript files"), ('.js',)),
    (_("Json files"), ('.json',)),
    (_("IPython notebooks"), ('.ipynb',)),
    (_("Enaml files"), ('.enaml',)),
    (_("Configuration files"), ('.properties', '.session', '.ini', '.inf',
                                '.reg', '.cfg', '.desktop')),
                 )

def _create_filter(title, ftypes):
    return "%s (*%s)" % (title, " *".join(ftypes))

ALL_FILTER = "%s (*)" % _("All files")

def _get_filters(filetypes):
    filters = []
    for title, ftypes in filetypes:
        filters.append(_create_filter(title, ftypes))
    filters.append(ALL_FILTER)
    return ";;".join(filters)

def _get_extensions(filetypes):
    ftype_list = []
    for _title, ftypes in filetypes:
        ftype_list += list(ftypes)
    return ftype_list

def get_filter(filetypes, ext):
    """Return filter associated to file extension"""
    if not ext:
        return ALL_FILTER
    for title, ftypes in filetypes:
        if ext in ftypes:
            return _create_filter(title, ftypes)
    else:
        return ''

EDIT_FILTERS = _get_filters(EDIT_FILETYPES)
EDIT_EXT = _get_extensions(EDIT_FILETYPES)+['']

# Extensions supported by Spyder's Variable explorer
IMPORT_EXT = list(iofuncs.iofunctions.load_extensions.values())

# Extensions that should be visible in Spyder's file/project explorers
SHOW_EXT = ['.png', '.ico', '.svg']

# Extensions supported by Spyder (Editor or Variable explorer)
VALID_EXT = EDIT_EXT+IMPORT_EXT


# Find in files include/exclude patterns
INCLUDE_PATTERNS = [r'|'.join(['\\'+_ext+r'$' for _ext in EDIT_EXT if _ext])+\
                    r'|README|INSTALL',
                    r'\.pyw?$|\.ipy$|\.txt$|\.rst$',
                    '.']
EXCLUDE_PATTERNS = [r'\.pyc$|\.pyo$|\.orig$|\.hg|\.svn|\bbuild\b',
                    r'\.pyc$|\.pyo$|\.orig$|\.hg|\.svn']


# Name filters for file/project explorers (excluding files without extension)
NAME_FILTERS = ['*' + _ext for _ext in VALID_EXT + SHOW_EXT if _ext]+\
               ['README', 'INSTALL', 'LICENSE', 'CHANGELOG']


# Port used to detect if there is a running instance and to communicate with
# it to open external files
OPEN_FILES_PORT = 21128

# Ctrl key
CTRL = "Meta" if sys.platform == 'darwin' else "Ctrl"


#==============================================================================
# Fonts
#==============================================================================
def is_ubuntu():
    "Detect if we are running in an Ubuntu-based distribution"
    if sys.platform.startswith('linux') and osp.isfile('/etc/lsb-release'):
        release_info = open('/etc/lsb-release').read()
        if 'Ubuntu' in release_info:
            return True
        else:
            return False
    else:
        return False


def is_gtk_desktop():
    "Detect if we are running in a Gtk-based desktop"
    if sys.platform.startswith('linux'):
        xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if xdg_desktop:
            gtk_desktops = ['Unity', 'GNOME', 'XFCE']
            if any([xdg_desktop.startswith(d) for d in gtk_desktops]):
                return True
            else:
                return False
        else:
            return False
    else:
        return False


SANS_SERIF = ['Sans Serif', 'DejaVu Sans', 'Bitstream Vera Sans',
              'Bitstream Charter', 'Lucida Grande', 'MS Shell Dlg 2',
              'Calibri', 'Verdana', 'Geneva', 'Lucid', 'Arial',
              'Helvetica', 'Avant Garde', 'Times', 'sans-serif']

MONOSPACE = ['Monospace', 'DejaVu Sans Mono', 'Consolas',
             'Bitstream Vera Sans Mono', 'Andale Mono', 'Liberation Mono',
             'Courier New', 'Courier', 'monospace', 'Fixed', 'Terminal']


if sys.platform == 'darwin':
    MONOSPACE = ['Menlo'] + MONOSPACE
    BIG = MEDIUM = SMALL = 12
elif os.name == 'nt':
    BIG = 12
    MEDIUM = 10
    SMALL = 9
elif is_ubuntu():
    SANS_SERIF = ['Ubuntu'] + SANS_SERIF
    MONOSPACE = ['Ubuntu Mono'] + MONOSPACE
    BIG = 13
    MEDIUM = SMALL = 11
else:
    BIG = 12
    MEDIUM = SMALL = 9


#==============================================================================
# Defaults
#==============================================================================
DEFAULTS = [
            ('main',
             {
              'single_instance': True,
              'open_files_port': OPEN_FILES_PORT,
              'tear_off_menus': False,
              'vertical_dockwidget_titlebars': False,
              'vertical_tabs': False,
              'animated_docks': True,
              'window/size': (1260, 740),
              'window/position': (10, 10),
              'window/is_maximized': True,
              'window/is_fullscreen': False,
              'window/prefs_dialog_size': (745, 411),
              'lightwindow/size': (650, 400),
              'lightwindow/position': (30, 30),
              'lightwindow/is_maximized': False,
              'lightwindow/is_fullscreen': False,

              # The following setting is currently not used but necessary from 
              # a programmatical point of view (see spyder.py):
              # (may become useful in the future if we add a button to change 
              # settings within the "light mode")
              'lightwindow/prefs_dialog_size': (745, 411),

              'memory_usage/enable': True,
              'memory_usage/timeout': 2000,
              'cpu_usage/enable': False,
              'cpu_usage/timeout': 2000,
              'use_custom_margin': True,
              'custom_margin': 0,
              'show_internal_console_if_traceback': True
              }),
            ('quick_layouts',
             {
              'place_holder': '',
              }),
            ('editor_appearance',
             {
              'cursor/width': 2,
              'completion/size': (300, 180),
              }),
            ('shell_appearance',
             {
              'cursor/width': 2,
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
              'external_editor/path': 'SciTE',
              'external_editor/gotoline': '-goto:',
              'light_background': True,
              }),
            ('console',
             {
              'max_line_count': 500,
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
              'show_elapsed_time': False,
              'show_icontext': False,
              'monitor/enabled': True,
              'qt/api': 'default',
              'pyqt/api_version': 2,
              'pyqt/ignore_sip_setapi_errors': False,
              'matplotlib/backend/enabled': True,
              'matplotlib/backend/value': 'MacOSX' if (sys.platform == 'darwin' \
                                           and os.environ.get('QT_API') == 'pyside')\
                                           else 'Qt4Agg',
              'umr/enabled': True,
              'umr/verbose': True,
              'umr/namelist': ['guidata', 'guiqwt'],
              'light_background': True,
              'merge_output_channels': os.name != 'nt',
              'colorize_sys_stderr': os.name != 'nt',
              'pythonstartup/default': True,
              'pythonstartup/custom': False,
              'pythonexecutable/default': True,
              'pythonexecutable/custom': False,
              'ets_backend': 'qt4'
              }),
            ('ipython_console',
             {
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'show_banner': True,
              'use_gui_completion': True,
              'use_pager': False,
              'show_calltips': True,
              'ask_before_closing': True,
              'object_inspector': True,
              'buffer_size': 500,
              'pylab': True,
              'pylab/autoload': False,
              'pylab/backend': 0,
              'pylab/inline/figure_format': 0,
              'pylab/inline/resolution': 72,
              'pylab/inline/width': 6,
              'pylab/inline/height': 4,
              'startup/run_lines': '',
              'startup/use_run_file': False,
              'startup/run_file': '',
              'greedy_completer': False,
              'autocall': 0,
              'symbolic_math': False,
              'in_prompt': '',
              'out_prompt': '',
              'light_color': True,
              'dark_color': False
              }),
            ('variable_explorer',
             {
              'autorefresh': False,
              'autorefresh/timeout': 2000,
              'check_all': CHECK_ALL,
              'excluded_names': EXCLUDED_NAMES,
              'exclude_private': True,
              'exclude_uppercase': True,
              'exclude_capitalized': False,
              'exclude_unsupported': True,
              'truncate': True,
              'minmax': False,
              'remote_editing': False,
              }),
            ('editor',
             {
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
              'blank_spaces': False,
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
              'check_eol_chars': True,
              'tab_always_indent': False,
              'intelligent_backspace': True,
              'highlight_current_line': True,
              'highlight_current_cell': True,
              'occurence_highlighting': True,
              'occurence_highlighting/timeout': 1500,
              'always_remove_trailing_spaces': False,
              'fullpath_sorting': True,
              'show_tab_bar': True,
              'max_recent_files': 20,
              'save_all_before_run': True,
              'focus_to_editor': True,
              'onsave_analysis': False
              }),
            ('historylog',
             {
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
              'connect/editor': False,
              'connect/python_console': False,
              'connect/ipython_console': False,
              'math': True,
              'automatic_import': True,
              }),
            ('onlinehelp',
             {
              'enable': True,
              'zoom_factor': .8,
              'max_history_entries': 20,
              }),
            ('outline_explorer',
             {
              'enable': True,
              'show_fullpath': False,
              'show_all_files': False,
              'show_comments': True,
              }),
            ('project_explorer',
             {
              'enable': True,
              'name_filters': NAME_FILTERS,
              'show_all': False,
              'show_hscrollbar': True
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
              'show_all': True,
              'show_icontext': False,
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
            ('workingdir',
             {
              'editor/open/browse_scriptdir': True,
              'editor/open/browse_workdir': False,
              'editor/new/browse_scriptdir': False,
              'editor/new/browse_workdir': True,
              'editor/open/auto_set_to_basedir': False,
              'editor/save/auto_set_to_basedir': False,
              'working_dir_adjusttocontents': False,
              'working_dir_history': 20,
              'startup/use_last_directory': True,
              }),
            ('shortcuts',
             {
              # ---- Global ----
              # -- In spyder.py
              '_/close pane': "Shift+Ctrl+F4",
              '_/preferences': "Ctrl+Alt+Shift+P",
              '_/maximize pane': "Ctrl+Alt+Shift+M",
              '_/fullscreen mode': "F11",
              '_/quit': "Ctrl+Q",
              '_/switch to/from layout 1': "Shift+Alt+F1",
              '_/set layout 1': "Ctrl+Shift+Alt+F1",
              '_/switch to/from layout 2': "Shift+Alt+F2",
              '_/set layout 2': "Ctrl+Shift+Alt+F2",
              '_/switch to/from layout 3': "Shift+Alt+F3",
              '_/set layout 3': "Ctrl+Shift+Alt+F3",
              # -- In plugins/editor
              '_/debug step over': "Ctrl+F10",
              '_/debug continue': "Ctrl+F12",
              '_/debug step into': "Ctrl+F11",
              '_/debug step return': "Ctrl+Shift+F11",
              '_/debug exit': "Ctrl+Shift+F12",
              # -- In plugins/init
              '_/switch to inspector': "Ctrl+Shift+H",
              '_/switch to outline_explorer': "Ctrl+Shift+O",
              '_/switch to editor': "Ctrl+Shift+E",
              '_/switch to historylog': "Ctrl+Shift+L",
              '_/switch to onlinehelp': "Ctrl+Shift+D",
              '_/switch to project_explorer': "Ctrl+Shift+P",
              '_/switch to console': "Ctrl+Shift+C",
              '_/switch to ipython_console': "Ctrl+Shift+I",
              '_/switch to variable_explorer': "Ctrl+Shift+V",
              '_/switch to find_in_files': "Ctrl+Shift+F",
              '_/switch to explorer': "Ctrl+Shift+X",
              # ---- Editor ----
              # -- In codeeditor
              'editor/code completion': CTRL+'+Space',
              'editor/duplicate line': "Ctrl+Alt+Up" if os.name == 'nt' else \
                                       "Shift+Alt+Up",
              'editor/copy line': "Ctrl+Alt+Down" if os.name == 'nt' else \
                                  "Shift+Alt+Down",
              'editor/delete line': 'Ctrl+D',
              'editor/move line up': "Alt+Up",
              'editor/move line down': "Alt+Down",
              'editor/go to definition': "Ctrl+G",
              'editor/toggle comment': "Ctrl+1",
              'editor/blockcomment': "Ctrl+4",
              'editor/unblockcomment': "Ctrl+5",
              # -- In widgets/editor
              'editor/inspect current object': 'Ctrl+I',
              'editor/go to line': 'Ctrl+L',
              'editor/file list management': 'Ctrl+E',
              'editor/go to previous file': 'Ctrl+Tab',
              'editor/go to next file': 'Ctrl+Shift+Tab',
              # -- In spyder.py
              'editor/find text': "Ctrl+F",
              'editor/find next': "F3",
              'editor/find previous': "Shift+F3",
              'editor/replace text': "Ctrl+H",
              # -- In plugins/editor
              'editor/show/hide outline': "Ctrl+Alt+O",
              'editor/show/hide project explorer': "Ctrl+Alt+P",
              'editor/new file': "Ctrl+N",
              'editor/open file': "Ctrl+O",
              'editor/save file': "Ctrl+S",
              'editor/save all': "Ctrl+Shift+S",
              'editor/print': "Ctrl+P",
              'editor/close all': "Ctrl+Shift+W",
              'editor/breakpoint': 'F12',
              'editor/conditional breakpoint': 'Shift+F12',
              'editor/debug with winpdb': "F7",
              'editor/debug': "Ctrl+F5",
              'editor/run': "F5",
              'editor/configure': "F6",
              'editor/re-run last script': "Ctrl+F6",
              'editor/run selection': "F9",
              'editor/last edit location': "Ctrl+Alt+Shift+Left",
              'editor/previous cursor position': "Ctrl+Alt+Left",
              'editor/next cursor position': "Ctrl+Alt+Right",
              # -- In p_breakpoints
              '_/switch to breakpoints': "Ctrl+Shift+B",
              # ---- Console (in widgets/shell) ----
              'console/inspect current object': "Ctrl+I",
              'console/clear shell': "Ctrl+L",
              'console/clear line': "Shift+Escape",
              # ---- Pylint (in p_pylint) ----
              'pylint/run analysis': "F8",
              # ---- Profiler (in p_profiler) ----
              'profiler/run profiler': "F10"
              }),
            ('color_schemes',
             {
              'names': ['Emacs', 'IDLE', 'Monokai', 'Pydev', 'Scintilla',
                        'Spyder', 'Spyder/Dark', 'Zenburn'],
              # ---- Emacs ----
              #      Name            Color     Bold  Italic
              'emacs/background':  "#000000",
              'emacs/currentline': "#2b2b43",
              'emacs/currentcell': "#1c1c2d",
              'emacs/occurence':   "#abab67",
              'emacs/ctrlclick':   "#0000ff",
              'emacs/sideareas':   "#555555",
              'emacs/matched_p':   "#009800",
              'emacs/unmatched_p': "#c80000",
              'emacs/normal':     ('#ffffff', False, False),
              'emacs/keyword':    ('#3c51e8', False, False),
              'emacs/builtin':    ('#900090', False, False),
              'emacs/definition': ('#ff8040', True, False),
              'emacs/comment':    ('#005100', False, False),
              'emacs/string':     ('#00aa00', False, True),
              'emacs/number':     ('#800000', False, False),
              'emacs/instance':   ('#ffffff', False, True),
              # ---- IDLE ----
              #      Name            Color     Bold  Italic
              'idle/background':   "#ffffff",
              'idle/currentline':  "#f2e6f3",
              'idle/currentcell':  "#feefff",
              'idle/occurence':    "#e8f2fe",
              'idle/ctrlclick':    "#0000ff",
              'idle/sideareas':    "#efefef",
              'idle/matched_p':    "#99ff99",
              'idle/unmatched_p':  "#ff9999",
              'idle/normal':      ('#000000', False, False),
              'idle/keyword':     ('#ff7700', True, False),
              'idle/builtin':     ('#900090', False, False),
              'idle/definition':  ('#0000ff', False, False),
              'idle/comment':     ('#dd0000', False, True),
              'idle/string':      ('#00aa00', False, False),
              'idle/number':      ('#924900', False, False),
              'idle/instance':    ('#777777', True, True),
              # ---- Monokai ----
              #      Name              Color     Bold  Italic
              'monokai/background':   "#2a2b24",
              'monokai/currentline':  "#484848",
              'monokai/currentcell':  "#3d3d3d",
              'monokai/occurence':    "#666666",
              'monokai/ctrlclick':    "#0000ff",
              'monokai/sideareas':    "#2a2b24",
              'monokai/matched_p':    "#688060",
              'monokai/unmatched_p':  "#bd6e76",
              'monokai/normal':      ("#ddddda", False, False),
              'monokai/keyword':     ("#f92672", False, False),
              'monokai/builtin':     ("#ae81ff", False, False),
              'monokai/definition':  ("#a6e22e", False, False),
              'monokai/comment':     ("#75715e", False, True),
              'monokai/string':      ("#e6db74", False, False),
              'monokai/number':      ("#ae81ff", False, False),
              'monokai/instance':    ("#ddddda", False, True),
              # ---- Pydev ----
              #      Name            Color     Bold  Italic
              'pydev/background':  "#ffffff",
              'pydev/currentline': "#e8f2fe",
              'pydev/currentcell': "#eff8fe",
              'pydev/occurence':   "#ffff99",
              'pydev/ctrlclick':   "#0000ff",
              'pydev/sideareas':   "#efefef",
              'pydev/matched_p':   "#99ff99",
              'pydev/unmatched_p': "#ff99992",
              'pydev/normal':     ('#000000', False, False),
              'pydev/keyword':    ('#0000ff', False, False),
              'pydev/builtin':    ('#900090', False, False),
              'pydev/definition': ('#000000', True, False),
              'pydev/comment':    ('#c0c0c0', False, False),
              'pydev/string':     ('#00aa00', False, True),
              'pydev/number':     ('#800000', False, False),
              'pydev/instance':   ('#000000', False, True),
              # ---- Scintilla ----
              #         Name             Color     Bold  Italic
              'scintilla/background':  "#ffffff",
              'scintilla/currentline': "#e1f0d1",
              'scintilla/currentcell': "#edfcdc",  
              'scintilla/occurence':   "#ffff99",
              'scintilla/ctrlclick':   "#0000ff",
              'scintilla/sideareas':   "#efefef",
              'scintilla/matched_p':   "#99ff99",
              'scintilla/unmatched_p': "#ff9999",
              'scintilla/normal':     ('#000000', False, False),
              'scintilla/keyword':    ('#00007f', True, False),
              'scintilla/builtin':    ('#000000', False, False),
              'scintilla/definition': ('#007f7f', True, False),
              'scintilla/comment':    ('#007f00', False, False),
              'scintilla/string':     ('#7f007f', False, False),
              'scintilla/number':     ('#007f7f', False, False),
              'scintilla/instance':   ('#000000', False, True),
              # ---- Spyder ----
              #       Name            Color     Bold  Italic
              'spyder/background':  "#ffffff",
              'spyder/currentline': "#f7ecf8",
              'spyder/currentcell': "#fdfdde",              
              'spyder/occurence':   "#ffff99",
              'spyder/ctrlclick':   "#0000ff",
              'spyder/sideareas':   "#efefef",
              'spyder/matched_p':   "#99ff99",
              'spyder/unmatched_p': "#ff9999",
              'spyder/normal':     ('#000000', False, False),
              'spyder/keyword':    ('#0000ff', False, False),
              'spyder/builtin':    ('#900090', False, False),
              'spyder/definition': ('#000000', True, False),
              'spyder/comment':    ('#adadad', False, True),
              'spyder/string':     ('#00aa00', False, False),
              'spyder/number':     ('#800000', False, False),
              'spyder/instance':   ('#924900', False, True),
              # ---- Spyder/Dark ----
              #           Name             Color     Bold  Italic
              'spyder/dark/background':  "#131926",
              'spyder/dark/currentline': "#2b2b43",
              'spyder/dark/currentcell': "#31314e",
              'spyder/dark/occurence':   "#abab67",
              'spyder/dark/ctrlclick':   "#0000ff",
              'spyder/dark/sideareas':   "#282828",
              'spyder/dark/matched_p':   "#009800",
              'spyder/dark/unmatched_p': "#c80000",
              'spyder/dark/normal':     ('#ffffff', False, False),
              'spyder/dark/keyword':    ('#558eff', False, False),
              'spyder/dark/builtin':    ('#aa00aa', False, False),
              'spyder/dark/definition': ('#ffffff', True, False),
              'spyder/dark/comment':    ('#7f7f7f', False, False),
              'spyder/dark/string':     ('#11a642', False, True),
              'spyder/dark/number':     ('#c80000', False, False),
              'spyder/dark/instance':   ('#be5f00', False, True),
              # ---- Zenburn ----
              #        Name            Color     Bold  Italic
              'zenburn/background':  "#3f3f3f",
              'zenburn/currentline': "#333333",
              'zenburn/currentcell': "#2c2c2c",
              'zenburn/occurence':   "#7a738f",
              'zenburn/ctrlclick':   "#0000ff",
              'zenburn/sideareas':   "#3f3f3f",
              'zenburn/matched_p':   "#688060",
              'zenburn/unmatched_p': "#bd6e76",
              'zenburn/normal':     ('#dcdccc', False, False),
              'zenburn/keyword':    ('#dfaf8f', True, False),
              'zenburn/builtin':    ('#efef8f', False, False),
              'zenburn/definition': ('#efef8f', False, False),
              'zenburn/comment':    ('#7f9f7f', False, True),
              'zenburn/string':     ('#cc9393', False, False),
              'zenburn/number':     ('#8cd0d3', False, False),
              'zenburn/instance':   ('#dcdccc', False, True)
             })
            ]


#==============================================================================
# Config instance
#==============================================================================
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    you need to do a MAJOR update in version, e.g. from 3.0.0 to 4.0.0
# 3. You don't need to touch this value if you're just adding a new option
CONF_VERSION = '15.2.0'

# XXX: Previously we had load=(not DEV) here but DEV was set to *False*.
# Check if it *really* needs to be updated or not
CONF = UserConfig('spyder', defaults=DEFAULTS, load=True, version=CONF_VERSION,
                  subfolder=SUBFOLDER, backup=True, raw_mode=True)

# Removing old .spyder.ini location:
old_location = osp.join(get_home_dir(), '.spyder.ini')
if osp.isfile(old_location):
    os.remove(old_location)
