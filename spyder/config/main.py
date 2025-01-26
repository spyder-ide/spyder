# -*- coding: utf-8 -*-

#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder configuration options.

Note: Leave this file free of Qt related imports, so that it can be used to
quickly load a user config file.
"""

import os
import sys

# Local import
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.config.base import CHECK_ALL, EXCLUDED_NAMES
from spyder.config.utils import IMPORT_EXT
from spyder.config.appearance import APPEARANCE
from spyder.plugins.editor.utils.findtasks import TASKS_PATTERN
from spyder.utils.introspection.module_completion import PREFERRED_MODULES


# =============================================================================
# Main constants
# =============================================================================
# Find in files exclude patterns
EXCLUDE_PATTERNS = ['*.csv, *.dat, *.log, *.tmp, *.bak, *.orig']

# Extensions that should be visible in Spyder's file/project explorers
SHOW_EXT = ['.py', '.ipynb', '.dat', '.pdf', '.png', '.svg', '.md', '.yml',
            '.yaml']

# Extensions supported by Spyder (Editor or Variable explorer)
USEFUL_EXT = IMPORT_EXT + SHOW_EXT

# Name filters for file/project explorers (excluding files without extension)
NAME_FILTERS = ['README', 'INSTALL', 'LICENSE', 'CHANGELOG']
NAME_FILTERS += ['*' + _ext for _ext in USEFUL_EXT if _ext not in NAME_FILTERS]

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
              'mac_open_file': False,
              'normal_screen_resolution': True,
              'high_dpi_scaling': False,
              'high_dpi_custom_scale_factor': False,
              'high_dpi_custom_scale_factors': '1.5',
              'vertical_tabs': False,
              'prompt_on_exit': False,
              'panes_locked': True,
              'window/size': (1260, 740),
              'window/position': (10, 10),
              'window/is_maximized': True,
              'window/is_fullscreen': False,
              'use_custom_margin': True,
              'custom_margin': 0,
              'use_custom_cursor_blinking': False,
              'show_internal_errors': True,
              'cursor/width': 2,
              'completion/size': (300, 180),
              'report_error/remember_token': False,
              'show_dpi_message': True,
              }),
            ('update_manager',
             {
              'check_updates_on_startup': True,
              'check_stable_only': True,
              }),
            ('toolbar',
             {
              'enable': True,
              'toolbars_visible': True,
              'last_visible_toolbars': [
                  ApplicationToolbars.File,
                  ApplicationToolbars.Run,
                  ApplicationToolbars.Debug,
                  ApplicationToolbars.Main,
                  ApplicationToolbars.WorkingDirectory,
              ],
              'last_toolbars': [],
             }),
            ('statusbar',
             {
              'show_status_bar': True,
              'memory_usage/enable': True,
              'memory_usage/timeout': 2000,
              'cpu_usage/enable': False,
              'cpu_usage/timeout': 2000,
              'clock/enable': False,
              'clock/timeout': 1000,
              }),
            ('pythonpath_manager',
             {
              'spyder_pythonpath': [],
              }),
            ('quick_layouts',
             {
              'place_holder': '',
              'names': [],
              'order': [],
              'active': [],
              'ui_names': []
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
              'last_envs': {}
              }),
            ('ipython_console',
             {
              'show_banner': True,
              'completion_type': 0,
              'show_calltips': True,
              'ask_before_closing': False,
              'show_reset_namespace_warning': True,
              'buffer_size': 500,
              'pylab': True,
              'pylab/autoload': False,
              'pylab/backend': 'inline',
              'pylab/inline/figure_format': 'png',
              'pylab/inline/resolution': 144,
              'pylab/inline/width': 6,
              'pylab/inline/height': 4,
              'pylab/inline/fontsize': 10.0,
              'pylab/inline/bottom': 0.11,
              'pylab/inline/bbox_inches': True,
              'startup/run_lines': '',
              'startup/use_run_file': False,
              'startup/run_file': '',
              'greedy_completer': False,
              'jedi_completer': False,
              'autocall': 0,
              'autoreload': True,
              'symbolic_math': False,
              'in_prompt': '',
              'out_prompt': '',
              'show_elapsed_time': False,
              'ask_before_restart': True,
              # This is True because there are libraries like Pyomo
              # that generate a lot of Command Prompts while running,
              # and that's extremely annoying for Windows users.
              'hide_cmd_windows': True,
              }),
            ('variable_explorer',
             {
              'check_all': CHECK_ALL,
              'dataframe_format': '.6g',  # No percent sign to avoid problems
                                          # with ConfigParser's interpolation
              'excluded_names': EXCLUDED_NAMES,
              'exclude_private': True,
              'exclude_uppercase': False,
              'exclude_capitalized': False,
              'exclude_unsupported': False,
              'exclude_callables_and_modules': True,
              'truncate': True,
              'minmax': False,
              'show_callable_attributes': True,
              'show_special_attributes': False,
              'filter_on': True
             }),
            ('debugger',
             {
              'exclude_internal': True,
              'pdb_prevent_closing': True,
              'pdb_ignore_lib': False,
              'pdb_execute_events': True,
              'pdb_use_exclamation_mark': True,
              'pdb_stop_first_line': True,
              'editor_debugger_panel': True,
              'breakpoints_table_visible': False,
             }),
            ('run',
             {
              'save_all_before_run': True,
              'run_cell_copy': False,
             }),
            ('plots',
             {
              'mute_inline_plotting': True,
              'show_plot_outline': False,
             }),
            ('editor',
             {
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
              'code_folding': True,
              'show_code_folding_warning': True,
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
              'multicursor_support': True,
              'tab_always_indent': False,
              'intelligent_backspace': True,
              'automatic_completions': True,
              'automatic_completions_after_chars': 1,
              'completions_hint': True,
              'completions_hint_after_ms': 500,
              'underline_errors': False,
              'highlight_current_line': True,
              'highlight_current_cell': True,
              'occurrence_highlighting': True,
              'occurrence_highlighting/timeout': 1500,
              'always_remove_trailing_spaces': False,
              'add_newline': False,
              'always_remove_trailing_newlines': False,
              'show_tab_bar': True,
              'show_class_func_dropdown': False,
              'max_recent_files': 20,
              'onsave_analysis': False,
              'autosave_enabled': True,
              'autosave_interval': 60,
              'docstring_type': 'Numpydoc',
              'strip_trailing_spaces_on_modify': False,
              'show_outline_in_editor_window': True,
              }),
            ('historylog',
             {
              'enable': True,
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
              'plain_mode': False,
              'rich_mode': True,
              'show_source': False,
              'locked': False,
              }),
            ('onlinehelp',
             {
              'enable': True,
              'zoom_factor': .8,
              'handle_links': False,
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
              'follow_cursor': True,
              'display_variables': False,
              'show_with_maximized_editor': True,
              }),
            ('preferences',
             {
              'enable': True,
              'dialog_size': (
                  (1010, 725) if MAC else ((900, 670) if WIN else (950, 690))
              ),
              }),
            ('project_explorer',
             {
              'name_filters': NAME_FILTERS,
              'show_all': True,
              'show_hscrollbar': True,
              'max_recent_projects': 10,
              'visible_if_project_open': True,
              'date_column': False,
              'single_click_to_open': False,
              'show_hidden': True,
              'size_column': False,
              'type_column': False,
              'date_column': False
              }),
            ('explorer',
             {
              'enable': True,
              'name_filters': NAME_FILTERS,
              'show_hidden': False,
              'single_click_to_open': False,
              'size_column': False,
              'type_column': False,
              'date_column': True
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
              'more_options': False,
              'case_sensitive': False,
              'exclude_case_sensitive': False,
              'max_results': 1000,
              }),
            ('completions',
             {
               'enable': True,
               'enable_code_snippets': True,
               'completions_wait_for_ms': 200,
               'enabled_providers': {},
               'provider_configuration': {},
               'request_priorities': {}
             }),
            ('profiler',
             {
              'enable': True,
              }),
            ('pylint',
             {
              'enable': True,
              'history_filenames': [],
              'max_entries': 30,
              'project_dir': None,
              }),
            ('workingdir',
             {
              'working_dir_history': 20,
              'console/use_project_or_home_directory': False,
              'console/use_cwd': True,
              'console/use_fixed_directory': False,
              'startup/use_project_or_home_directory': True,
              'startup/use_fixed_directory': False,
              }),
            ('tours',
             {
              'enable': True,
              'show_tour_message': True,
             }),
            ('shortcuts',
             {
              # -- Application --
              '_/close pane': "Shift+Ctrl+F4",
              '_/lock unlock panes': "Shift+Ctrl+F5",
              '_/use next layout': "Shift+Alt+PgDown",
              '_/use previous layout': "Shift+Alt+PgUp",
              '_/maximize pane': "Ctrl+Alt+Shift+M",
              '_/fullscreen mode': "F11",
              '_/save current layout': "Shift+Alt+S",
              '_/layout preferences': "Shift+Alt+P",
              '_/spyder documentation': "F1",
              '_/restart': "Shift+Alt+R",
              '_/quit': "Ctrl+Q",
              '_/run': "F5",
              '_/configure': "Ctrl+F6",
              '_/re-run last script': "F6",
              # -- Switch to plugin --
              '_/switch to help': "Ctrl+Shift+H",
              '_/switch to outline_explorer': "Ctrl+Shift+O",
              '_/switch to editor': "Ctrl+Shift+E",
              '_/switch to historylog': "Ctrl+Shift+L",
              '_/switch to onlinehelp': "",
              '_/switch to project_explorer': "Ctrl+Shift+P",
              '_/switch to ipython_console': "Ctrl+Shift+I",
              '_/switch to variable_explorer': "Ctrl+Shift+V",
              '_/switch to find_in_files': "Ctrl+Shift+F",
              '_/switch to explorer': "Ctrl+Shift+X",
              '_/switch to plots': "Ctrl+Shift+J" if MAC else "Ctrl+Shift+G",
              '_/switch to pylint': "Ctrl+Shift+C",
              '_/switch to profiler': "Ctrl+Shift+R",
              '_/switch to debugger': "Ctrl+Shift+D",
              # -- Find/replace --
              'find_replace/find text': "Ctrl+F",
              'find_replace/find next': "Ctrl+G" if MAC else "F3",
              'find_replace/find previous': (
                  "Ctrl+Shift+G" if MAC else "Shift+F3"),
              'find_replace/replace text': "Ctrl+R",
              'find_replace/hide find and replace': "Escape",
              # -- Editor --
              'editor/code completion': CTRL+'+Space',
              'editor/duplicate line up': CTRL + "+Alt+PgUp",
              'editor/duplicate line down': CTRL + "+Alt+PgDown",
              'editor/delete line': 'Ctrl+D',
              'editor/transform to uppercase': 'Ctrl+Shift+U',
              'editor/transform to lowercase': 'Ctrl+U',
              'editor/indent': 'Ctrl+]',
              'editor/unindent': 'Ctrl+[',
              'editor/move line up': "Alt+Up",
              'editor/move line down': "Alt+Down",
              'editor/go to new line': "Ctrl+Shift+Return",
              'editor/go to definition': "F3" if MAC else "Ctrl+G",
              'editor/toggle comment': "Ctrl+1",
              'editor/create_new_cell': "Ctrl+2",
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
              'editor/inspect current object': 'Ctrl+I',
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
              'editor/previous cursor position': "Alt+Left",
              'editor/next cursor position': "Alt+Right",
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
              'editor/run selection and advance': "F9",
              'editor/run selection up to line': 'Shift+F9',
              'editor/run selection from line': 'Alt+F9',
              'editor/go to next cell': 'Ctrl+Down',
              'editor/go to previous cell': 'Ctrl+Up',
              'editor/re-run cell': 'Alt+Return',
              'editor/scroll line down': '',
              'editor/scroll line up': '',
              'editor/split vertically': "Ctrl+{",
              'editor/split horizontally': "Ctrl+_",
              'editor/close split panel': "Alt+Shift+W",
              'editor/docstring': "Ctrl+Alt+D",
              'editor/autoformatting': "Ctrl+Alt+I",
              'editor/show in external file explorer': '',
              'editor/enter array inline': "Ctrl+Alt+M",
              'editor/enter array table': "Ctrl+M",
              'editor/run cell in debugger': 'Alt+Shift+Return',
              'editor/run selection in debugger': CTRL + '+F9',
              'editor/add cursor up': 'Alt+Shift+Up',
              'editor/add cursor down': 'Alt+Shift+Down',
              'editor/clear extra cursors': 'Esc',
              # -- Internal console --
              'internal_console/inspect current object': "Ctrl+I",
              'internal_console/clear shell': "Ctrl+L",
              'internal_console/clear line': "Shift+Escape",
              # -- Pylint --
              'pylint/run file in pylint': "F8",
              # -- Profiler --
              'profiler/run file in profiler': "F10",
              # -- Switcher --
              '_/file switcher': 'Ctrl+P',
              '_/symbol finder': 'Ctrl+Alt+P',
              # -- IPython console --
              'ipython_console/new tab': "Ctrl+T",
              'ipython_console/reset namespace': "Ctrl+Alt+R",
              'ipython_console/restart kernel': "Ctrl+.",
              'ipython_console/inspect current object': "Ctrl+I",
              'ipython_console/clear shell': "Ctrl+L",
              'ipython_console/clear line': "Shift+Escape",
              'ipython_console/enter array inline': "Ctrl+Alt+M",
              'ipython_console/enter array table': "Ctrl+M",
              # -- Variable explorer --
              'variable_explorer/copy': 'Ctrl+C',
              'variable_explorer/search': 'Ctrl+F',
              'variable_explorer/refresh': 'Ctrl+R',
              # -- Debugger --
              '_/run file in debugger': "Ctrl+F5",
              '_/debug current line': "Ctrl+F10",
              '_/debug continue': "Ctrl+F12",
              '_/debug step into': "Ctrl+F11",
              '_/debug step return': "Ctrl+Shift+F11",
              '_/debug stop': "Ctrl+Shift+F12",
              'debugger/refresh': 'Ctrl+R',
              'debugger/search': 'Ctrl+F',
              'debugger/toggle breakpoint': 'F12',
              'debugger/toggle conditional breakpoint': 'Shift+F12',
              'debugger/show breakpoint table': "",
              # -- Plots --
              'plots/copy': 'Ctrl+C',
              'plots/previous figure': 'Ctrl+PgUp',
              'plots/next figure': 'Ctrl+PgDown',
              'plots/save': 'Ctrl+S',
              'plots/save all': 'Alt+Shift+S',
              'plots/close': 'Ctrl+W',
              'plots/close all': 'Alt+Shift+W',
              'plots/zoom in': "Ctrl++",
              'plots/zoom out': "Ctrl+-",
              'plots/auto fit': "Ctrl+0",
              # -- Files --
              'explorer/copy file': 'Ctrl+C',
              'explorer/paste file': 'Ctrl+V',
              'explorer/copy absolute path': 'Alt+Shift+C',
              'explorer/copy relative path': 'Alt+Shift+D',
              # -- Projects --
              'project_explorer/copy file': 'Ctrl+C',
              'project_explorer/paste file': 'Ctrl+V',
              'project_explorer/copy absolute path': 'Alt+Shift+C',
              'project_explorer/copy relative path': 'Alt+Shift+D',
              # -- Find --
              'find_in_files/find in files': 'Alt+Shift+F',
              }),
            ('appearance', APPEARANCE),
            ]


NAME_MAP = {
    # Empty container object means use the rest of defaults
    'spyder': [],
    # Splitting these files makes sense for projects, we might as well
    # apply the same split for the app global config
    # These options change on spyder startup or are tied to a specific OS,
    # not good for version control
    'transient': [
        ('main', [
            'completion/size',
            'crash',
            'current_version',
            'historylog_filename',
            'window/position',
            'window/size',
            'window/state',
            ]
         ),
        ('editor', [
            'autosave_mapping',
            'bookmarks',
            'filenames',
            'layout_settings',
            'recent_files',
            'splitter_state',
            'file_uuids'
            ]
         ),
        ('explorer', [
            'file_associations',
        ]),
        ('find_in_files', [
            'path_history'
            'search_text',
            'exclude_index',
            'search_in_index',
            ]
         ),
        ('main_interpreter', [
            'custom_interpreters_list',
            'custom_interpreter',
            'executable',
            'last_envs',
             ]
         ),
        ('onlinehelp', [
            'zoom_factor',
             ]
         ),
        ('outline_explorer', [
            'expanded_state',
            'scrollbar_position',
            ],
         ),
        ('preferences', [
            'dialog_size',
            ],
         ),
        ('project_explorer', [
            'current_project_path',
            'expanded_state',
            'recent_projects',
            'max_recent_projects',
            'scrollbar_position',
          ]
         ),
        ('pythonpath_manager', []),
        ('quick_layouts', []), # Empty list means use all options
        ('run', [
            'breakpoints',
            'configurations',
            'default/wdir/fixed_directory',
            'last_used_parameters',
            'parameters'
          ]
         ),
        ('workingdir', [
            'console/fixed_directory',
            'startup/fixed_directory',
          ]
         ),
        ('pylint', [
          'history_filenames',
          ]
         ),
    ]
}


# =============================================================================
# Config version
# =============================================================================
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    or if you want to *rename* options, then you need to do a MAJOR update in
#    version, e.g. from 3.0.0 to 4.0.0
# 3. You don't need to touch this value if you're just adding a new option
CONF_VERSION = '86.0.0'
