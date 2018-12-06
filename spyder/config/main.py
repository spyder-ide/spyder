# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder configuration options

Note: Leave this file free of Qt related imports, so that it can be used to
quickly load a user config file
"""

import os
import os.path as osp
import sys

# Local import
from spyder.config.base import (CHECK_ALL, EXCLUDED_NAMES, get_home_dir,
                                SUBFOLDER)
from spyder.config.fonts import BIG, MEDIUM, MONOSPACE, SANS_SERIF
from spyder.config.user import UserConfig
from spyder.config.utils import IMPORT_EXT
from spyder.utils import codeanalysis


# =============================================================================
# Main constants
# =============================================================================
# Find in files exclude patterns
EXCLUDE_PATTERNS = ['*.csv, *.dat, *.log, *.tmp, *.bak, *.orig']

# Extensions that should be visible in Spyder's file/project explorers
SHOW_EXT = ['.py', '.ipynb', '.txt', '.dat', '.pdf', '.png', '.svg']


# Extensions supported by Spyder (Editor or Variable explorer)
USEFUL_EXT = IMPORT_EXT + SHOW_EXT


# Name filters for file/project explorers (excluding files without extension)
NAME_FILTERS = ['README', 'INSTALL', 'LICENSE', 'CHANGELOG'] + \
               ['*' + _ext for _ext in USEFUL_EXT if _ext]


# Port used to detect if there is a running instance and to communicate with
# it to open external files
OPEN_FILES_PORT = 21128


# OS Specific
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
CTRL = "Meta" if MAC else "Ctrl"

# Run cell shortcuts
if sys.platform == 'darwin':
    RUN_CELL_SHORTCUT = 'Meta+Return'
else:
    RUN_CELL_SHORTCUT = 'Ctrl+Return'
RE_RUN_LAST_CELL_SHORTCUT = 'Alt+Return'
RUN_CELL_AND_ADVANCE_SHORTCUT = 'Shift+Return'


# =============================================================================
#  Defaults
# =============================================================================
DEFAULTS = [
            ('main',
             {
              'opengl': 'software',
              'single_instance': True,
              'open_files_port': OPEN_FILES_PORT,
              'tear_off_menus': False,
              'normal_screen_resolution': True,
              'high_dpi_scaling': False,
              'high_dpi_custom_scale_factor': False,
              'high_dpi_custom_scale_factors': '1.5',
              'vertical_dockwidget_titlebars': False,
              'vertical_tabs': False,
              'animated_docks': True,
              'prompt_on_exit': False,
              'panes_locked': True,
              'window/size': (1260, 740),
              'window/position': (10, 10),
              'window/is_maximized': True,
              'window/is_fullscreen': False,
              'window/prefs_dialog_size': (745, 411),
              'show_status_bar': True,
              'memory_usage/enable': True,
              'memory_usage/timeout': 2000,
              'cpu_usage/enable': False,
              'cpu_usage/timeout': 2000,
              'use_custom_margin': True,
              'custom_margin': 0,
              'use_custom_cursor_blinking': False,
              'show_internal_errors': True,
              'check_updates_on_startup': True,
              'toolbars_visible': True,
              'cursor/width': 2,
              'completion/size': (300, 180),
              'report_error/remember_me': False,
              'report_error/remember_token': False,
              }),
            ('quick_layouts',
             {
              'place_holder': '',
              'names': ['Matlab layout', 'Rstudio layout', 'Vertical split', 'Horizontal split'],
              'order': ['Matlab layout', 'Rstudio layout', 'Vertical split', 'Horizontal split'],
              'active': ['Matlab layout', 'Rstudio layout', 'Vertical split', 'Horizontal split'],
              }),
            ('internal_console',
             {
              'max_line_count': 300,
              'working_dir_history': 30,
              'working_dir_adjusttocontents': False,
              'wrap': True,
              'calltips': True,
              'codecompletion/auto': False,
              'codecompletion/enter_key': True,
              'codecompletion/case_sensitive': True,
              'external_editor/path': 'SciTE',
              'external_editor/gotoline': '-goto:',
              'light_background': True,
              }),
            ('main_interpreter',
             {
              'default': True,
              'custom': False,
              'umr/enabled': True,
              'umr/verbose': True,
              'umr/namelist': [],
              'custom_interpreters_list': [],
              'custom_interpreter': '',
              }),
            ('ipython_console',
             {
              'show_banner': True,
              'completion_type': 0,
              'use_pager': False,
              'show_calltips': True,
              'ask_before_closing': False,
              'show_reset_namespace_warning': True,
              'buffer_size': 500,
              'pylab': True,
              'pylab/autoload': False,
              'pylab/backend': 0,
              'pylab/inline/figure_format': 0,
              'pylab/inline/resolution': 72,
              'pylab/inline/width': 6,
              'pylab/inline/height': 4,
              'pylab/inline/bbox_inches': True,
              'startup/run_lines': '',
              'startup/use_run_file': False,
              'startup/run_file': '',
              'greedy_completer': False,
              'jedi_completer': False,
              'autocall': 0,
              'symbolic_math': False,
              'in_prompt': '',
              'out_prompt': '',
              'show_elapsed_time': False,
              'ask_before_restart': True
              }),
            ('variable_explorer',
             {
              'check_all': CHECK_ALL,
              'dataframe_format': '.6g',  # No percent sign to avoid problems
                                          # with ConfigParser's interpolation
              'excluded_names': EXCLUDED_NAMES,
              'exclude_private': True,
              'exclude_uppercase': True,
              'exclude_capitalized': False,
              'exclude_unsupported': True,
              'truncate': True,
              'minmax': False
             }),
            ('plots',
             {
              'mute_inline_plotting': False,
              'show_plot_outline': False,
             }),
            ('editor',
             {
              'printer_header/font/family': SANS_SERIF,
              'printer_header/font/size': MEDIUM,
              'printer_header/font/italic': False,
              'printer_header/font/bold': False,
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
              'edge_line_columns': '79',
              'indent_guides': False,
              'scroll_past_end': False,
              'toolbox_panel': True,
              'calltips': True,
              'go_to_definition': True,
              'close_parentheses': True,
              'close_quotes': True,
              'add_colons': True,
              'auto_unindent': True,
              'indent_chars': '*    *',
              'tab_stop_width_spaces': 4,
              'codecompletion/auto': True,
              'codecompletion/enter_key': True,
              'codecompletion/case_sensitive': True,
              'check_eol_chars': True,
              'convert_eol_on_save': False,
              'convert_eol_on_save_to': 'LF',
              'tab_always_indent': False,
              'intelligent_backspace': True,
              'highlight_current_line': True,
              'highlight_current_cell': True,
              'occurrence_highlighting': True,
              'occurrence_highlighting/timeout': 1500,
              'always_remove_trailing_spaces': False,
              'show_tab_bar': True,
              'show_class_func_dropdown': False,
              'max_recent_files': 20,
              'save_all_before_run': True,
              'focus_to_editor': True,
              'run_cell_copy': False,
              'onsave_analysis': False
              }),
            ('historylog',
             {
              'enable': True,
              'max_entries': 100,
              'wrap': True,
              'go_to_eof': True,
              'line_numbers': False,
              }),
            ('help',
             {
              'enable': True,
              'max_history_entries': 20,
              'wrap': True,
              'connect/editor': False,
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
              'group_cells': True,
              'sort_files_alphabetically': False,
              'show_comments': True,
              }),
            ('project_explorer',
             {
              'name_filters': NAME_FILTERS,
              'show_all': True,
              'show_hscrollbar': True,
              'visible_if_project_open': True
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
              'exclude': EXCLUDE_PATTERNS,
              'exclude_regexp': False,
              'search_text_regexp': False,
              'search_text': [''],
              'search_text_samples': [codeanalysis.TASKS_PATTERN],
              'more_options': True,
              'case_sensitive': False
              }),
            ('breakpoints',
             {
              'enable': True,
              }),
            ('profiler',
             {
              'enable': True,
              }),
            ('pylint',
             {
              'enable': True,
              }),
            ('workingdir',
             {
              'working_dir_adjusttocontents': False,
              'working_dir_history': 20,
              'console/use_project_or_home_directory': False,
              'console/use_cwd': True,
              'console/use_fixed_directory': False,
              }),
            ('shortcuts',
             {
              # ---- Global ----
              # -- In app/spyder.py
              '_/close pane': "Shift+Ctrl+F4",
              '_/lock unlock panes': "Shift+Ctrl+F5",
              '_/use next layout': "Shift+Alt+PgDown",
              '_/use previous layout': "Shift+Alt+PgUp",
              '_/preferences': "Ctrl+Alt+Shift+P",
              '_/maximize pane': "Ctrl+Alt+Shift+M",
              '_/fullscreen mode': "F11",
              '_/save current layout': "Shift+Alt+S",
              '_/layout preferences': "Shift+Alt+P",
              '_/show toolbars': "Alt+Shift+T",
              '_/spyder documentation': "F1",
              '_/restart': "Shift+Alt+R",
              '_/quit': "Ctrl+Q",
              # -- In plugins/editor
              '_/file switcher': 'Ctrl+P',
              '_/symbol finder': 'Ctrl+Alt+P',
              '_/debug': "Ctrl+F5",
              '_/debug step over': "Ctrl+F10",
              '_/debug continue': "Ctrl+F12",
              '_/debug step into': "Ctrl+F11",
              '_/debug step return': "Ctrl+Shift+F11",
              '_/debug exit': "Ctrl+Shift+F12",
              '_/run': "F5",
              '_/configure': "Ctrl+F6",
              '_/re-run last script': "F6",
              # -- In plugins/init
              '_/switch to help': "Ctrl+Shift+H",
              '_/switch to outline_explorer': "Ctrl+Shift+O",
              '_/switch to editor': "Ctrl+Shift+E",
              '_/switch to historylog': "Ctrl+Shift+L",
              '_/switch to onlinehelp': "Ctrl+Shift+D",
              '_/switch to project_explorer': "Ctrl+Shift+P",
              '_/switch to ipython_console': "Ctrl+Shift+I",
              '_/switch to variable_explorer': "Ctrl+Shift+V",
              '_/switch to find_in_files': "Ctrl+Shift+F",
              '_/switch to explorer': "Ctrl+Shift+X",
              # -- In widgets/findreplace.py
              '_/find text': "Ctrl+F",
              '_/find next': "F3",
              '_/find previous': "Shift+F3",
              '_/replace text': "Ctrl+R",
              '_/hide find and replace': "Escape",
              # ---- Editor ----
              # -- In widgets/sourcecode/codeeditor.py
              'editor/code completion': CTRL+'+Space',
              'editor/duplicate line': "Ctrl+Alt+Up" if WIN else \
                                       "Shift+Alt+Up",
              'editor/copy line': "Ctrl+Alt+Down" if WIN else \
                                  "Shift+Alt+Down",
              'editor/delete line': 'Ctrl+D',
              'editor/transform to uppercase': 'Ctrl+Shift+U',
              'editor/transform to lowercase': 'Ctrl+U',
              'editor/indent': 'Ctrl+]',
              'editor/unindent': 'Ctrl+[',
              'editor/move line up': "Alt+Up",
              'editor/move line down': "Alt+Down",
              'editor/go to new line': "Ctrl+Shift+Return",
              'editor/go to definition': "Ctrl+G",
              'editor/toggle comment': "Ctrl+1",
              'editor/blockcomment': "Ctrl+4",
              'editor/unblockcomment': "Ctrl+5",
              'editor/start of line': "Meta+A",
              'editor/end of line': "Meta+E",
              'editor/previous line': "Meta+P",
              'editor/next line': "Meta+N",
              'editor/previous char': "Meta+B",
              'editor/next char': "Meta+F",
              'editor/previous word': "Ctrl+Left",
              'editor/next word': "Ctrl+Right",
              'editor/kill to line end': "Meta+K",
              'editor/kill to line start': "Meta+U",
              'editor/yank': 'Meta+Y',
              'editor/rotate kill ring': 'Shift+Meta+Y',
              'editor/kill previous word': 'Meta+Backspace',
              'editor/kill next word': 'Meta+D',
              'editor/start of document': 'Ctrl+Home',
              'editor/end of document': 'Ctrl+End',
              'editor/undo': 'Ctrl+Z',
              'editor/redo': 'Ctrl+Shift+Z',
              'editor/cut': 'Ctrl+X',
              'editor/copy': 'Ctrl+C',
              'editor/paste': 'Ctrl+V',
              'editor/delete': 'Del',
              'editor/select all': "Ctrl+A",
              # -- In widgets/editor.py
              'editor/inspect current object': 'Ctrl+I',
              'editor/breakpoint': 'F12',
              'editor/conditional breakpoint': 'Shift+F12',
              'editor/run selection': "F9",
              'editor/go to line': 'Ctrl+L',
              'editor/go to previous file': 'Ctrl+Shift+Tab',
              'editor/go to next file': 'Ctrl+Tab',
              'editor/cycle to previous file': 'Ctrl+PgUp',
              'editor/cycle to next file': 'Ctrl+PgDown',
              'editor/new file': "Ctrl+N",
              'editor/open last closed':"Ctrl+Shift+T",
              'editor/open file': "Ctrl+O",
              'editor/save file': "Ctrl+S",
              'editor/save all': "Ctrl+Alt+S",
              'editor/save as': 'Ctrl+Shift+S',
              'editor/close all': "Ctrl+Shift+W",
              'editor/last edit location': "Ctrl+Alt+Shift+Left",
              'editor/previous cursor position': "Ctrl+Alt+Left",
              'editor/next cursor position': "Ctrl+Alt+Right",
              'editor/previous warning': "Ctrl+Alt+Shift+,",
              'editor/next warning': "Ctrl+Alt+Shift+.",
              'editor/zoom in 1': "Ctrl++",
              'editor/zoom in 2': "Ctrl+=",
              'editor/zoom out': "Ctrl+-",
              'editor/zoom reset': "Ctrl+0",
              'editor/close file 1': "Ctrl+W",
              'editor/close file 2': "Ctrl+F4",
              'editor/run cell': RUN_CELL_SHORTCUT,
              'editor/run cell and advance': RUN_CELL_AND_ADVANCE_SHORTCUT,
              'editor/go to next cell': 'Ctrl+Down',
              'editor/go to previous cell': 'Ctrl+Up',
              'editor/re-run last cell': RE_RUN_LAST_CELL_SHORTCUT,
              'editor/split vertically': "Ctrl+{",
              'editor/split horizontally': "Ctrl+_",
              'editor/close split panel': "Alt+Shift+W",
              # -- In Breakpoints
              '_/switch to breakpoints': "Ctrl+Shift+B",
              # ---- Consoles (in widgets/shell) ----
              'console/inspect current object': "Ctrl+I",
              'console/clear shell': "Ctrl+L",
              'console/clear line': "Shift+Escape",
              # ---- In Pylint ----
              'pylint/run analysis': "F8",
              # ---- In Profiler ----
              'profiler/run profiler': "F10",
              # ---- In widgets/ipythonconsole/shell.py ----
              'ipython_console/new tab': "Ctrl+T",
              'ipython_console/reset namespace': "Ctrl+Alt+R",
              'ipython_console/restart kernel': "Ctrl+.",
              # ---- In widgets/arraybuider.py ----
              'array_builder/enter array inline': "Ctrl+Alt+M",
              'array_builder/enter array table': "Ctrl+M",
              # ---- In widgets/variableexplorer/aarayeditor.py ----
              'variable_explorer/copy': 'Ctrl+C',
              }),
            ('appearance',
             {
              'icon_theme': 'spyder 3',
              # Global Spyder fonts
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'rich_font/family': SANS_SERIF,
              'rich_font/size': BIG,
              'rich_font/italic': False,
              'rich_font/bold': False,
              'ui_theme': 'automatic',
              'names': ['emacs', 'idle', 'monokai', 'pydev', 'scintilla',
                        'spyder', 'spyder/dark', 'zenburn', 'solarized/light',
                        'solarized/dark', 'black/pastel', 'frontenddev',
                        'gedit/original/oblivion', 'havenjark', 'inkpot',
                        'minimal', 'mr', 'nightlion/aptana/theme',
                        'notepad++/like', 'oblivion', 'obsidian', 'pastel',
                        'recogneyes', 'retta', 'roboticket', 'schuss',
                        'sublime/text/2', 'sublime/te/mo/ex', 'sunburst',
                        'tango', 'vibrant/ink', 'wombat'],
              'selected': 'solarized/dark',
              # ---- Emacs ----
              'emacs/name':        "Emacs",
              #      Name            Color     Bold  Italic
              'emacs/background':  "#000000",
              'emacs/currentline': "#2b2b43",
              'emacs/currentcell': "#1c1c2d",
              'emacs/occurrence':   "#abab67",
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
              'idle/name':         "IDLE",
              #      Name            Color     Bold  Italic
              'idle/background':   "#ffffff",
              'idle/currentline':  "#f2e6f3",
              'idle/currentcell':  "#feefff",
              'idle/occurrence':    "#e8f2fe",
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
              'monokai/name':         "Monokai",
              #      Name              Color     Bold  Italic
              'monokai/background':   "#2a2b24",
              'monokai/currentline':  "#484848",
              'monokai/currentcell':  "#3d3d3d",
              'monokai/occurrence':    "#666666",
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
              'pydev/name':        "Pydev",
              #      Name            Color     Bold  Italic
              'pydev/background':  "#ffffff",
              'pydev/currentline': "#e8f2fe",
              'pydev/currentcell': "#eff8fe",
              'pydev/occurrence':   "#ffff99",
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
              'scintilla/name':        "Scintilla",
              #         Name             Color     Bold  Italic
              'scintilla/background':  "#ffffff",
              'scintilla/currentline': "#e1f0d1",
              'scintilla/currentcell': "#edfcdc",
              'scintilla/occurrence':   "#ffff99",
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
              'spyder/name':        "Spyder",
              #       Name            Color     Bold  Italic
              'spyder/background':  "#ffffff",
              'spyder/currentline': "#f7ecf8",
              'spyder/currentcell': "#fdfdde",
              'spyder/occurrence':   "#ffff99",
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
              'spyder/dark/name':        "Spyder Dark",
              #           Name             Color     Bold  Italic
              'spyder/dark/background':  "#131926",
              'spyder/dark/currentline': "#2b2b43",
              'spyder/dark/currentcell': "#31314e",
              'spyder/dark/occurrence':   "#abab67",
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
              'zenburn/name':        "Zenburn",
              #        Name            Color     Bold  Italic
              'zenburn/background':  "#3f3f3f",
              'zenburn/currentline': "#333333",
              'zenburn/currentcell': "#2c2c2c",
              'zenburn/occurrence':   "#7a738f",
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
              'zenburn/instance':   ('#dcdccc', False, True),
              # ---- Solarized Light ----
              'solarized/light/name':        "Solarized Light",
              #        Name            Color     Bold  Italic
              'solarized/light/background':  '#fdf6e3',
              'solarized/light/currentline': '#f5efdB',
              'solarized/light/currentcell': '#eee8d5',
              'solarized/light/occurrence':   '#839496',
              'solarized/light/ctrlclick':   '#d33682',
              'solarized/light/sideareas':   '#eee8d5',
              'solarized/light/matched_p':   '#586e75',
              'solarized/light/unmatched_p': '#dc322f',
              'solarized/light/normal':     ('#657b83', False, False),
              'solarized/light/keyword':    ('#859900', False, False),
              'solarized/light/builtin':    ('#6c71c4', False, False),
              'solarized/light/definition': ('#268bd2', True, False),
              'solarized/light/comment':    ('#93a1a1', False, True),
              'solarized/light/string':     ('#2aa198', False, False),
              'solarized/light/number':     ('#cb4b16', False, False),
              'solarized/light/instance':   ('#b58900', False, True),
              # ---- Solarized Dark ----
              'solarized/dark/name':        "Solarized Dark",
              #        Name            Color     Bold  Italic
              'solarized/dark/background':  '#002b36',
              'solarized/dark/currentline': '#083f4d',
              'solarized/dark/currentcell': '#073642',
              'solarized/dark/occurrence':   '#657b83',
              'solarized/dark/ctrlclick':   '#d33682',
              'solarized/dark/sideareas':   '#073642',
              'solarized/dark/matched_p':   '#93a1a1',
              'solarized/dark/unmatched_p': '#dc322f',
              'solarized/dark/normal':     ('#839496', False, False),
              'solarized/dark/keyword':    ('#859900', False, False),
              'solarized/dark/builtin':    ('#6c71c4', False, False),
              'solarized/dark/definition': ('#268bd2', True, False),
              'solarized/dark/comment':    ('#586e75', False, True),
              'solarized/dark/string':     ('#2aa198', False, False),
              'solarized/dark/number':     ('#cb4b16', False, False),
              'solarized/dark/instance':   ('#b58900', False, True),
              # ---- Black Pastel (Eclipse color theme) ----
              'black/pastel/name':        "Black Pastel",
              #      Name                   Color     Bold  Italic
              'black/pastel/background':  "#000000",
              'black/pastel/currentline': "#2f393c",
              'black/pastel/currentcell': "#000000",
              'black/pastel/occurence':   "#616161",
              'black/pastel/ctrlclick':   "#7d8c93",
              'black/pastel/sideareas':   "#2f393c",
              'black/pastel/matched_p':   "#c0c0c0",
              'black/pastel/unmatched_p': "#95bed8",
              'black/pastel/normal':     ('#c0c0c0', False, False),
              'black/pastel/keyword':    ('#82677e', False, False),
              'black/pastel/builtin':    ('#82677e', False, False),
              'black/pastel/definition': ('#82677e', False, False),
              'black/pastel/comment':    ('#7d8c93', False, False),
              'black/pastel/string':     ('#c78d9b', False, False),
              'black/pastel/number':     ('#c78d9b', False, False),
              'black/pastel/instance':   ('#678cb1', False, False),
              # ---- frontenddev (Eclipse color theme) ----
              'frontenddev/name':        "frontenddev",
              #      Name                  Color     Bold  Italic
              'frontenddev/background':  "#000000",
              'frontenddev/currentline': "#222220",
              'frontenddev/currentcell': "#000000",
              'frontenddev/occurence':   "#616161",
              'frontenddev/ctrlclick':   "#666666",
              'frontenddev/sideareas':   "#222220",
              'frontenddev/matched_p':   "#ffffff",
              'frontenddev/unmatched_p': "#ccffcc",
              'frontenddev/normal':     ('#ffffff', False, False),
              'frontenddev/keyword':    ('#999999', False, False),
              'frontenddev/builtin':    ('#9cf828', False, False),
              'frontenddev/definition': ('#f7c527', False, False),
              'frontenddev/comment':    ('#666666', False, False),
              'frontenddev/string':     ('#00a40f', False, False),
              'frontenddev/number':     ('#ff0000', False, False),
              'frontenddev/instance':   ('#c38705', False, False),
              # ---- Gedit Original Oblivion (Eclipse color theme) ----
              'gedit/original/oblivion/name':        "Gedit Original Oblivion",
              #      Name                              Color     Bold  Italic
              'gedit/original/oblivion/background':  "#2e3436",
              'gedit/original/oblivion/currentline': "#555753",
              'gedit/original/oblivion/currentcell': "#2e3436",
              'gedit/original/oblivion/occurence':   "#000000",
              'gedit/original/oblivion/ctrlclick':   "#888a85",
              'gedit/original/oblivion/sideareas':   "#555753",
              'gedit/original/oblivion/matched_p':   "#d3d7cf",
              'gedit/original/oblivion/unmatched_p': "#888a85",
              'gedit/original/oblivion/normal':     ('#d3d7cf', False, False),
              'gedit/original/oblivion/keyword':    ('#ffffff', False, False),
              'gedit/original/oblivion/builtin':    ('#bbbbbb', False, False),
              'gedit/original/oblivion/definition': ('#ffffff', False, False),
              'gedit/original/oblivion/comment':    ('#888a85', False, False),
              'gedit/original/oblivion/string':     ('#edd400', False, False),
              'gedit/original/oblivion/number':     ('#ce5c00', False, False),
              'gedit/original/oblivion/instance':   ('#bed6ff', False, False),
              # ---- Havenjark (Eclipse color theme) ----
              'havenjark/name':        "Havenjark",
              #      Name                Color     Bold  Italic
              'havenjark/background':  "#2d3639",
              'havenjark/currentline': "#00001f",
              'havenjark/currentcell': "#2d3639",
              'havenjark/occurence':   "#616161",
              'havenjark/ctrlclick':   "#b3b5af",
              'havenjark/sideareas':   "#00001f",
              'havenjark/matched_p':   "#c0b6a8",
              'havenjark/unmatched_p': "#2a4750",
              'havenjark/normal':     ('#c0b6a8', False, False),
              'havenjark/keyword':    ('#a38474', False, False),
              'havenjark/builtin':    ('#b8ada0', False, False),
              'havenjark/definition': ('#dfbe95', False, False),
              'havenjark/comment':    ('#aeaeae', False, False),
              'havenjark/string':     ('#cc9393', False, False),
              'havenjark/number':     ('#b9a185', False, False),
              'havenjark/instance':   ('#b3b784', False, False),
              # ---- Inkpot (Eclipse color theme) ----
              'inkpot/name':        "Inkpot",
              #      Name             Color     Bold  Italic
              'inkpot/background':  "#1f1f27",
              'inkpot/currentline': "#2d2d44",
              'inkpot/currentcell': "#1f1f27",
              'inkpot/occurence':   "#616161",
              'inkpot/ctrlclick':   "#1f1f27",
              'inkpot/sideareas':   "#2d2d44",
              'inkpot/matched_p':   "#cfbfad",
              'inkpot/unmatched_p': "#8b8bff",
              'inkpot/normal':     ('#cfbfad', False, False),
              'inkpot/keyword':    ('#808bed', False, False),
              'inkpot/builtin':    ('#87cefa', False, False),
              'inkpot/definition': ('#87cefa', False, False),
              'inkpot/comment':    ('#cd8b00', False, False),
              'inkpot/string':     ('#ffcd8b', False, False),
              'inkpot/number':     ('#ffcd8b', False, False),
              'inkpot/instance':   ('#cfbfad', False, False),
              # ---- minimal (Eclipse color theme) ----
              'minimal/name':        "minimal",
              #      Name              Color     Bold  Italic
              'minimal/background':  "#ffffff",
              'minimal/currentline': "#aaccff",
              'minimal/currentcell': "#ffffff",
              'minimal/occurence':   "#efefef",
              'minimal/ctrlclick':   "#05314d",
              'minimal/sideareas':   "#aaccff",
              'minimal/matched_p':   "#000000",
              'minimal/unmatched_p': "#efefff",
              'minimal/normal':     ('#000000', False, False),
              'minimal/keyword':    ('#5c8198', False, False),
              'minimal/builtin':    ('#000066', False, False),
              'minimal/definition': ('#5c8198', False, False),
              'minimal/comment':    ('#334466', False, False),
              'minimal/string':     ('#333333', False, False),
              'minimal/number':     ('#333333', False, False),
              'minimal/instance':   ('#566874', False, False),
              # ---- Mr (Eclipse color theme) ----
              'mr/name':        "Mr",
              #      Name         Color     Bold  Italic
              'mr/background':  "#ffffff",
              'mr/currentline': "#d8d8d8",
              'mr/currentcell': "#ffffff",
              'mr/occurence':   "#000000",
              'mr/ctrlclick':   "#ff3300",
              'mr/sideareas':   "#d8d8d8",
              'mr/matched_p':   "#333333",
              'mr/unmatched_p': "#d8d8d8",
              'mr/normal':     ('#333333', False, False),
              'mr/keyword':    ('#0000ff', False, False),
              'mr/builtin':    ('#006600', False, False),
              'mr/definition': ('#000099', False, False),
              'mr/comment':    ('#ff9900', False, False),
              'mr/string':     ('#cc0000', False, False),
              'mr/number':     ('#0000ff', False, False),
              'mr/instance':   ('#000099', False, False),
              # ---- NightLion Aptana Theme (Eclipse color theme) ----
              'nightlion/aptana/theme/name':        "NightLion Aptana Theme",
              #      Name                             Color     Bold  Italic
              'nightlion/aptana/theme/background':  "#1e1e1e",
              'nightlion/aptana/theme/currentline': "#505050",
              'nightlion/aptana/theme/currentcell': "#1e1e1e",
              'nightlion/aptana/theme/occurence':   "#616161",
              'nightlion/aptana/theme/ctrlclick':   "#b3b5af",
              'nightlion/aptana/theme/sideareas':   "#505050",
              'nightlion/aptana/theme/matched_p':   "#e2e2e2",
              'nightlion/aptana/theme/unmatched_p': "#364656",
              'nightlion/aptana/theme/normal':     ('#e2e2e2', False, False),
              'nightlion/aptana/theme/keyword':    ('#8dcbe2', False, False),
              'nightlion/aptana/theme/builtin':    ('#cae682', False, False),
              'nightlion/aptana/theme/definition': ('#dfbe95', False, False),
              'nightlion/aptana/theme/comment':    ('#7f9f7f', False, False),
              'nightlion/aptana/theme/string':     ('#cc9393', False, False),
              'nightlion/aptana/theme/number':     ('#eab882', False, False),
              'nightlion/aptana/theme/instance':   ('#b3b784', False, False),
              # ---- Notepad++ Like (Eclipse color theme) ----
              'notepad++/like/name':        "Notepad++ Like",
              #      Name                     Color     Bold  Italic
              'notepad++/like/background':  "#ffffff",
              'notepad++/like/currentline': "#eeeeee",
              'notepad++/like/currentcell': "#ffffff",
              'notepad++/like/occurence':   "#efefef",
              'notepad++/like/ctrlclick':   "#800080",
              'notepad++/like/sideareas':   "#eeeeee",
              'notepad++/like/matched_p':   "#8000ff",
              'notepad++/like/unmatched_p': "#eeeeee",
              'notepad++/like/normal':     ('#8000ff', False, False),
              'notepad++/like/keyword':    ('#0000ff', False, False),
              'notepad++/like/builtin':    ('#000080', False, False),
              'notepad++/like/definition': ('#ff00ff', False, False),
              'notepad++/like/comment':    ('#008000', False, False),
              'notepad++/like/string':     ('#808080', False, False),
              'notepad++/like/number':     ('#ff8000', False, False),
              'notepad++/like/instance':   ('#800080', False, False),
              # ---- Oblivion (Eclipse color theme) ----
              'oblivion/name':        "Oblivion",
              #      Name               Color     Bold  Italic
              'oblivion/background':  "#1e1e1e",
              'oblivion/currentline': "#2a2a2a",
              'oblivion/currentcell': "#1e1e1e",
              'oblivion/occurence':   "#000000",
              'oblivion/ctrlclick':   "#ccdf32",
              'oblivion/sideareas':   "#2a2a2a",
              'oblivion/matched_p':   "#d8d8d8",
              'oblivion/unmatched_p': "#000000",
              'oblivion/normal':     ('#d8d8d8', False, False),
              'oblivion/keyword':    ('#ffffff', False, False),
              'oblivion/builtin':    ('#d25252', False, False),
              'oblivion/definition': ('#ffffff', False, False),
              'oblivion/comment':    ('#c7dd0c', False, False),
              'oblivion/string':     ('#ffc600', False, False),
              'oblivion/number':     ('#7fb347', False, False),
              'oblivion/instance':   ('#bed6ff', False, False),
              # ---- Obsidian (Eclipse color theme) ----
              'obsidian/name':        "Obsidian",
              #      Name               Color     Bold  Italic
              'obsidian/background':  "#293134",
              'obsidian/currentline': "#2f393c",
              'obsidian/currentcell': "#293134",
              'obsidian/occurence':   "#616161",
              'obsidian/ctrlclick':   "#7d8c93",
              'obsidian/sideareas':   "#2f393c",
              'obsidian/matched_p':   "#e0e2e4",
              'obsidian/unmatched_p': "#804000",
              'obsidian/normal':     ('#e0e2e4', False, False),
              'obsidian/keyword':    ('#93c763', False, False),
              'obsidian/builtin':    ('#678cb1', False, False),
              'obsidian/definition': ('#678cb1', False, False),
              'obsidian/comment':    ('#7d8c93', False, False),
              'obsidian/string':     ('#ec7600', False, False),
              'obsidian/number':     ('#ffcd22', False, False),
              'obsidian/instance':   ('#678cb1', False, False),
              # ---- Pastel (Eclipse color theme) ----
              'pastel/name':        "Pastel",
              #      Name             Color     Bold  Italic
              'pastel/background':  "#1f2223",
              'pastel/currentline': "#2f393c",
              'pastel/currentcell': "#1f2223",
              'pastel/occurence':   "#616161",
              'pastel/ctrlclick':   "#7d8c93",
              'pastel/sideareas':   "#2f393c",
              'pastel/matched_p':   "#e0e2e4",
              'pastel/unmatched_p': "#95bed8",
              'pastel/normal':     ('#e0e2e4', False, False),
              'pastel/keyword':    ('#a57b61', False, False),
              'pastel/builtin':    ('#678cb1', False, False),
              'pastel/definition': ('#678cb1', False, False),
              'pastel/comment':    ('#7d8c93', False, False),
              'pastel/string':     ('#c78d9b', False, False),
              'pastel/number':     ('#c78d9b', False, False),
              'pastel/instance':   ('#678cb1', False, False),
              # ---- RecognEyes (Eclipse color theme) ----
              'recogneyes/name':        "RecognEyes",
              #      Name                 Color     Bold  Italic
              'recogneyes/background':  "#101020",
              'recogneyes/currentline': "#202030",
              'recogneyes/currentcell': "#101020",
              'recogneyes/occurence':   "#000000",
              'recogneyes/ctrlclick':   "#ccdf32",
              'recogneyes/sideareas':   "#202030",
              'recogneyes/matched_p':   "#d0d0d0",
              'recogneyes/unmatched_p': "#0000ff",
              'recogneyes/normal':     ('#d0d0d0', False, False),
              'recogneyes/keyword':    ('#00d0d0', False, False),
              'recogneyes/builtin':    ('#ff8080', False, False),
              'recogneyes/definition': ('#d0d0d0', False, False),
              'recogneyes/comment':    ('#00e000', False, False),
              'recogneyes/string':     ('#dc78dc', False, False),
              'recogneyes/number':     ('#ffff00', False, False),
              'recogneyes/instance':   ('#bed6ff', False, False),
              # ---- Retta (Eclipse color theme) ----
              'retta/name':        "Retta",
              #      Name            Color     Bold  Italic
              'retta/background':  "#000000",
              'retta/currentline': "#2a2a2a",
              'retta/currentcell': "#000000",
              'retta/occurence':   "#5e5c56",
              'retta/ctrlclick':   "#83786e",
              'retta/sideareas':   "#2a2a2a",
              'retta/matched_p':   "#f8e1aa",
              'retta/unmatched_p': "#527d5d",
              'retta/normal':     ('#f8e1aa', False, False),
              'retta/keyword':    ('#e79e3c', True, False),
              'retta/builtin':    ('#de6546', True, False),
              'retta/definition': ('#a4b0c0', False, False),
              'retta/comment':    ('#83786e', False, False),
              'retta/string':     ('#d6c248', False, False),
              'retta/number':     ('#d6c248', False, False),
              'retta/instance':   ('#de6546', False, False),
              # ---- Roboticket (Eclipse color theme) ----
              'roboticket/name':        "Roboticket",
              #      Name                 Color     Bold  Italic
              'roboticket/background':  "#f5f5f5",
              'roboticket/currentline': "#e0e0ff",
              'roboticket/currentcell': "#f5f5f5",
              'roboticket/occurence':   "#ffcfbb",
              'roboticket/ctrlclick':   "#ad95af",
              'roboticket/sideareas':   "#e0e0ff",
              'roboticket/matched_p':   "#585858",
              'roboticket/unmatched_p': "#bdd8f2",
              'roboticket/normal':     ('#585858', False, False),
              'roboticket/keyword':    ('#295f94', False, True),
              'roboticket/builtin':    ('#ab2525', False, False),
              'roboticket/definition': ('#bc5a65', True, False),
              'roboticket/comment':    ('#ad95af', False, True),
              'roboticket/string':     ('#317ecc', False, False),
              'roboticket/number':     ('#af0f91', False, False),
              'roboticket/instance':   ('#566874', False, False),
              # ---- Schuss (Eclipse color theme) ----
              'schuss/name':        "Schuss",
              #      Name             Color     Bold  Italic
              'schuss/background':  "#ffffff",
              'schuss/currentline': "#fff7cd",
              'schuss/currentcell': "#ffffff",
              'schuss/occurence':   "#cc6633",
              'schuss/ctrlclick':   "#05314d",
              'schuss/sideareas':   "#fff7cd",
              'schuss/matched_p':   "#430400",
              'schuss/unmatched_p': "#f4fdff",
              'schuss/normal':     ('#430400', False, False),
              'schuss/keyword':    ('#606060', False, False),
              'schuss/builtin':    ('#ca3349', False, False),
              'schuss/definition': ('#797a8a', False, False),
              'schuss/comment':    ('#d7d3cc', False, False),
              'schuss/string':     ('#585545', False, False),
              'schuss/number':     ('#d0321f', False, False),
              'schuss/instance':   ('#566874', False, False),
              # ---- Sublime Text 2 (Eclipse color theme) ----
              'sublime/text/2/name':        "Sublime Text 2",
              #      Name                     Color     Bold  Italic
              'sublime/text/2/background':  "#272822",
              'sublime/text/2/currentline': "#5b5a4e",
              'sublime/text/2/currentcell': "#272822",
              'sublime/text/2/occurence':   "#000000",
              'sublime/text/2/ctrlclick':   "#ffffff",
              'sublime/text/2/sideareas':   "#5b5a4e",
              'sublime/text/2/matched_p':   "#cfbfad",
              'sublime/text/2/unmatched_p': "#cc9900",
              'sublime/text/2/normal':     ('#cfbfad', False, False),
              'sublime/text/2/keyword':    ('#ff007f', False, False),
              'sublime/text/2/builtin':    ('#52e3f6', False, False),
              'sublime/text/2/definition': ('#a7ec21', False, False),
              'sublime/text/2/comment':    ('#ffffff', False, False),
              'sublime/text/2/string':     ('#ece47e', False, False),
              'sublime/text/2/number':     ('#c48cff', False, False),
              'sublime/text/2/instance':   ('#cfbfad', False, False),
              # ---- Sublime Text Monokai Extended (Eclipse color theme) ----
              'sublime/te/mo/ex/name':        "Sublime Text Monokai Extended",
              #      Name                       Color     Bold  Italic
              'sublime/te/mo/ex/background':  "#222222",
              'sublime/te/mo/ex/currentline': "#2f2f2f",
              'sublime/te/mo/ex/currentcell': "#222222",
              'sublime/te/mo/ex/occurence':   "#000000",
              'sublime/te/mo/ex/ctrlclick':   "#ffffff",
              'sublime/te/mo/ex/sideareas':   "#2f2f2f",
              'sublime/te/mo/ex/matched_p':   "#cfbfad",
              'sublime/te/mo/ex/unmatched_p': "#cc9900",
              'sublime/te/mo/ex/normal':     ('#cfbfad', False, False),
              'sublime/te/mo/ex/keyword':    ('#ff007f', False, False),
              'sublime/te/mo/ex/builtin':    ('#52e3f6', False, False),
              'sublime/te/mo/ex/definition': ('#a7ec21', False, False),
              'sublime/te/mo/ex/comment':    ('#ffffff', False, False),
              'sublime/te/mo/ex/string':     ('#ece47e', False, False),
              'sublime/te/mo/ex/number':     ('#c48cff', False, False),
              'sublime/te/mo/ex/instance':   ('#cfbfad', False, False),
              # ---- Sunburst (Eclipse color theme) ----
              'sunburst/name':        "Sunburst",
              #      Name               Color     Bold  Italic
              'sunburst/background':  "#000000",
              'sunburst/currentline': "#2f2f2f",
              'sunburst/currentcell': "#000000",
              'sunburst/occurence':   "#5a5a5a",
              'sunburst/ctrlclick':   "#a8a8a8",
              'sunburst/sideareas':   "#2f2f2f",
              'sunburst/matched_p':   "#f9f9f9",
              'sunburst/unmatched_p': "#ddf0ff",
              'sunburst/normal':     ('#f9f9f9', False, False),
              'sunburst/keyword':    ('#ea9c77', False, False),
              'sunburst/builtin':    ('#f9f9f9', False, False),
              'sunburst/definition': ('#f9f9f9', False, False),
              'sunburst/comment':    ('#a8a8a8', False, True),
              'sunburst/string':     ('#76ba53', False, False),
              'sunburst/number':     ('#f9f9f9', False, False),
              'sunburst/instance':   ('#4b9ce9', False, False),
              # ---- Tango (Eclipse color theme) ----
              'tango/name':        "Tango",
              #      Name            Color     Bold  Italic
              'tango/background':  "#ffffff",
              'tango/currentline': "#eeeeee",
              'tango/currentcell': "#ffffff",
              'tango/occurence':   "#efefef",
              'tango/ctrlclick':   "#05314d",
              'tango/sideareas':   "#eeeeee",
              'tango/matched_p':   "#000000",
              'tango/unmatched_p': "#eeeeee",
              'tango/normal':     ('#000000', False, False),
              'tango/keyword':    ('#688046', False, False),
              'tango/builtin':    ('#37550d', False, False),
              'tango/definition': ('#444444', False, False),
              'tango/comment':    ('#17608f', False, False),
              'tango/string':     ('#92679a', False, False),
              'tango/number':     ('#801f91', False, False),
              'tango/instance':   ('#566874', False, False),
              # ---- Vibrant Ink (Eclipse color theme) ----
              'vibrant/ink/name':        "Vibrant Ink",
              #      Name                  Color     Bold  Italic
              'vibrant/ink/background':  "#191919",
              'vibrant/ink/currentline': "#222220",
              'vibrant/ink/currentcell': "#191919",
              'vibrant/ink/occurence':   "#616161",
              'vibrant/ink/ctrlclick':   "#8c3fc8",
              'vibrant/ink/sideareas':   "#222220",
              'vibrant/ink/matched_p':   "#ffffff",
              'vibrant/ink/unmatched_p': "#414c3b",
              'vibrant/ink/normal':     ('#ffffff', False, False),
              'vibrant/ink/keyword':    ('#ec691e', False, False),
              'vibrant/ink/builtin':    ('#9cf828', False, False),
              'vibrant/ink/definition': ('#f7c527', False, False),
              'vibrant/ink/comment':    ('#8146a2', False, False),
              'vibrant/ink/string':     ('#477488', False, False),
              'vibrant/ink/number':     ('#477488', False, False),
              'vibrant/ink/instance':   ('#357a8f', False, False),
              # ---- Wombat (Eclipse color theme) ----
              'wombat/name':        "Wombat",
              #      Name             Color     Bold  Italic
              'wombat/background':  "#242424",
              'wombat/currentline': "#656565",
              'wombat/currentcell': "#242424",
              'wombat/occurence':   "#616161",
              'wombat/ctrlclick':   "#b3b5af",
              'wombat/sideareas':   "#656565",
              'wombat/matched_p':   "#f6f3e8",
              'wombat/unmatched_p': "#898941",
              'wombat/normal':     ('#f6f3e8', False, False),
              'wombat/keyword':    ('#8ac6f2', False, False),
              'wombat/builtin':    ('#cae682', False, False),
              'wombat/definition': ('#f3f6ee', False, False),
              'wombat/comment':    ('#99968b', False, False),
              'wombat/string':     ('#95e454', False, False),
              'wombat/number':     ('#f08080', False, False),
              'wombat/instance':   ('#cae682', False, False)
             }),
            ('lsp-server', {
                'python': {
                    'index': 0,
                    'cmd': 'pyls',
                    'args': '--host %(host)s --port %(port)s --tcp',
                    'host': '127.0.0.1',
                    'port': 2087,
                    'external': False,
                    'configurations': {
                        'pyls': {
                            'configurationSources': [
                                "pycodestyle", "pyflakes"],
                            'plugins': {
                                'pycodestyle': {
                                    'enabled': True,
                                    'exclude': [],
                                    'filename': [],
                                    'select': [],
                                    'ignore': [],
                                    'hangClosing': False,
                                    'maxLineLength': 79
                                },
                                'pyflakes': {
                                    'enabled': True
                                },
                                'yapf': {
                                    'enabled': False
                                },
                                'pydocstyle': {
                                    'enabled': False,
                                    'convention': 'pep257',
                                    'addIgnore': [],
                                    'addSelect': [],
                                    'ignore': [],
                                    'select': [],
                                    'match': "(?!test_).*\\.py",
                                    'matchDir': '[^\\.].*',
                                },
                                'rope': {
                                    'extensionModules': None,
                                    'ropeFolder': []
                                },
                                'rope_completion': {
                                    'enabled': False
                                },
                                'jedi_completion': {
                                    'enabled': True
                                },
                                'jedi_hover': {
                                    'enabled': True
                                },
                                'jedi_references': {
                                    'enabled': True
                                },
                                'jedi_signature_help': {
                                    'enabled': True
                                },
                                'jedi_symbols': {
                                    'enabled': True,
                                    'all_scopes': True
                                },
                                'mccabe': {
                                    'enabled': False,
                                    'threshold': 15
                                },
                                'preload': {
                                    'enabled': True,
                                    'modules': []
                                }
                            },

                        }
                    }
                }
            })
            ]


# =============================================================================
# Config instance
# =============================================================================
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    or if you want to *rename* options, then you need to do a MAJOR update in
#    version, e.g. from 3.0.0 to 4.0.0
# 3. You don't need to touch this value if you're just adding a new option
CONF_VERSION = '47.0.0'

# Main configuration instance
try:
    CONF = UserConfig('spyder', defaults=DEFAULTS, load=True,
                      version=CONF_VERSION, subfolder=SUBFOLDER, backup=True,
                      raw_mode=True)
except Exception:
    CONF = UserConfig('spyder', defaults=DEFAULTS, load=False,
                      version=CONF_VERSION, subfolder=SUBFOLDER, backup=True,
                      raw_mode=True)

# Removing old .spyder.ini location:
old_location = osp.join(get_home_dir(), '.spyder.ini')
if osp.isfile(old_location):
    os.remove(old_location)
