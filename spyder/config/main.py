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
from spyder.config.fonts import MEDIUM, MONOSPACE, SANS_SERIF, SMALL
from spyder.config.user import UserConfig
from spyder.config.utils import IMPORT_EXT
from spyder.plugins.editor.utils.findtasks import TASKS_PATTERN
from spyder.utils.introspection.module_completion import PREFERRED_MODULES


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
LINUX = sys.platform.startswith('linux')
CTRL = "Meta" if MAC else "Ctrl"


# Modules to be preloaded for Rope and Jedi
PRELOAD_MDOULES = ', '.join(PREFERRED_MODULES)


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
              'window/prefs_dialog_size': (1050, 530),
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
              'codecompletion/auto': False,
              'external_editor/path': 'SciTE',
              'external_editor/gotoline': '-goto:',
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
              'ask_before_restart': True,
              # This is True because there are libraries like Pyomo
              # that generate a lot of Command Prompts while running,
              # and that's extremely annoying for Windows users.
              'hide_cmd_windows': True
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
              'mute_inline_plotting': True,
              'show_plot_outline': False,
              'auto_fit_plotting': True
             }),
            ('editor',
             {
              'printer_header/font/family': SANS_SERIF,
              'printer_header/font/size': MEDIUM,
              'printer_header/font/italic': False,
              'printer_header/font/bold': False,
              'wrap': False,
              'wrapflag': True,
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
              'close_parentheses': True,
              'close_quotes': True,
              'add_colons': True,
              'auto_unindent': True,
              'indent_chars': '*    *',
              'tab_stop_width_spaces': 4,
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
              'onsave_analysis': False,
              'autosave_enabled': True,
              'autosave_interval': 60,
              'docstring_type': 'Numpydoc',
              'strip_trailing_spaces_on_modify': True,
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
              'single_click_to_open': False,
              }),
            ('find_in_files',
             {
              'enable': True,
              'supported_encodings': ["utf-8", "iso-8859-1", "cp1252"],
              'exclude': EXCLUDE_PATTERNS,
              'exclude_regexp': False,
              'search_text_regexp': False,
              'search_text': [''],
              'search_text_samples': [TASKS_PATTERN],
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
              '_/switch to plots': "Ctrl+Shift+G",
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
              'editor/go to previous file': CTRL + '+Shift+Tab',
              'editor/go to next file': CTRL + '+Tab',
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
              'editor/run cell': CTRL + '+Return',
              'editor/run cell and advance': 'Shift+Return',
              'editor/go to next cell': 'Ctrl+Down',
              'editor/go to previous cell': 'Ctrl+Up',
              'editor/re-run last cell': 'Alt+Return',
              'editor/split vertically': "Ctrl+{",
              'editor/split horizontally': "Ctrl+_",
              'editor/close split panel': "Alt+Shift+W",
              'editor/docstring': "Ctrl+Alt+D",
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
              # ---- In widgets/plots/figurebrowser.py ----
              'plots/copy': 'Ctrl+C',
              'plots/previous figure': 'Ctrl+PgUp',
              'plots/next figure': 'Ctrl+PgDown',
              # ---- In widgets/explorer ----
              'explorer/copy file': 'Ctrl+C',
              'explorer/paste file': 'Ctrl+V',
              'explorer/copy absolute path': 'Ctrl+Alt+C',
              'explorer/copy relative path': 'Ctrl+Alt+Shift+C',
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
              'rich_font/size': SMALL if (LINUX or WIN) else MEDIUM,
              'rich_font/italic': False,
              'rich_font/bold': False,
              'ui_theme': 'automatic',
              'names': ['emacs', 'idle', 'monokai', 'pydev', 'scintilla',
                        'spyder', 'spyder/dark', 'zenburn', 'solarized/light',
                        'solarized/dark'],
              'selected': 'spyder/dark',
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
              'spyder/dark/background':  "#19232D",
              'spyder/dark/currentline': "#3a424a",
              'spyder/dark/currentcell': "#17172d",
              'spyder/dark/occurrence':  "#509ea5",
              'spyder/dark/ctrlclick':   "#179ae0",
              'spyder/dark/sideareas':   "#222b35",
              'spyder/dark/matched_p':   "#0bbe0b",
              'spyder/dark/unmatched_p': "#ff4340",
              'spyder/dark/normal':     ('#ffffff', False, False),
              'spyder/dark/keyword':    ('#c670e0', False, False),
              'spyder/dark/builtin':    ('#fab16c', False, False),
              'spyder/dark/definition': ('#57d6e4', True, False),
              'spyder/dark/comment':    ('#999999', False, False),
              'spyder/dark/string':     ('#b0e686', False, True),
              'spyder/dark/number':     ('#faed5c', False, False),
              'spyder/dark/instance':   ('#ee6772', False, True),
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
              'solarized/dark/instance':   ('#b58900', False, True)
             }),
            ('lsp-server',
             {
              # This option is not used with the LSP server config
              # It is used to disable hover hints in the editor
              'enable_hover_hints': True,
              'code_completion': True,
              'jedi_definition': True,
              'jedi_definition/follow_imports': True,
              'jedi_signature_help': True,
              'preload_modules': PRELOAD_MDOULES,
              'pyflakes': True,
              'mccabe': False,
              'pycodestyle': False,
              'pycodestyle/filename': '',
              'pycodestyle/exclude': '',
              'pycodestyle/select': '',
              'pycodestyle/ignore': '',
              'pycodestyle/max_line_length': 79,
              'pydocstyle': False,
              'pydocstyle/convention': 'numpy',
              'pydocstyle/select': '',
              'pydocstyle/ignore': '',
              'pydocstyle/match': '(?!test_).*\\.py',
              'pydocstyle/match_dir': '[^\\.].*',
              'advanced/command_launch': 'pyls',
              'advanced/host': '127.0.0.1',
              'advanced/port': 2087,
              'advanced/external': False,
              'advanced/stdio': False
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
CONF_VERSION = '50.1.0'


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
