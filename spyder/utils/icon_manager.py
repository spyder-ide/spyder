# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QStyle, QWidget

# Local imports
from spyder.config.base import get_image_path
from spyder.config.main import CONF
from spyder.config.gui import is_dark_interface
import qtawesome as qta


if is_dark_interface():
    MAIN_FG_COLOR = 'white'
else:
    MAIN_FG_COLOR = 'black'


LANGUAGE_ICONS = {
    '.c': 'CFileIcon',
    '.h': 'CFileIcon',
    '.cc': 'CppFileIcon',
    '.hh': 'CppFileIcon',
    '.cpp': 'CppFileIcon',
    '.cxx': 'CppFileIcon',
    '.c++': 'CppFileIcon',
    '.hpp': 'CppFileIcon',
    '.hxx': 'CppFileIcon',
    '.h++': 'CppFileIcon',
    '.cs': 'CsharpFileIcon',
    '.asmx': 'CsharpFileIcon',
    '.py': 'PythonFileIcon',
    '.py3': 'PythonFileIcon',
    '.pyx': 'PythonFileIcon',
    '.pyw': 'PythonFileIcon',
    '.java': 'JavaFileIcon',
    '.jav': 'JavaFileIcon',
    '.j': 'JavaFileIcon',
    '.js': 'JavascriptFileIcon',
    '.r': 'RFileIcon',
    '.rnw': 'RFileIcon',
    '.rmd': 'RFileIcon',
    '.swift': 'SwiftFileIcon',
    '.csv': 'GridFileIcon',
    '.tsv': 'GridFileIcon',
    '.bat': 'WindowsFileIcon',
    '.psl': 'PowershellFileIcon',
    '.sh': 'DollarFileIcon',
    '.md': 'MarkdownFileIcon',
    '.json': 'JsonFileIcon',
    '.html': 'CodeFileIcon',
    '.css': 'CodeFileIcon',
    '.yml': 'ExclamationFileIcon',
    '.yaml': 'ExclamationFileIcon',
    '.xml': 'CodeFileIcon'
}

_resource = {
    'directory': osp.join(osp.dirname(osp.realpath(__file__)), '../fonts'),
    'loaded': False,
}

_qtaargs = {
    'format_letter_case':      [('mdi.format-letter-case',), {'color': MAIN_FG_COLOR}],
    'regex':                   [('mdi.regex',), {'color': MAIN_FG_COLOR}],
    'log':                     [('fa.file-text-o',), {'color': MAIN_FG_COLOR}],
    'configure':               [('fa.wrench',), {'color': MAIN_FG_COLOR}],
    'bold':                    [('fa.bold',), {'color': MAIN_FG_COLOR}],
    'italic':                  [('fa.italic',), {'color': MAIN_FG_COLOR}],
    'genprefs':                [('fa.cogs',), {'color': MAIN_FG_COLOR}],
    'exit':                    [('fa.power-off',), {'color': MAIN_FG_COLOR}],
    'run_small':               [('fa.play',), {'color': 'green'}],
    'stop':                    [('fa.stop',), {'color': 'darkred'}],
    'syspath':                 [('fa.cogs',), {'color': MAIN_FG_COLOR}],
    'font':                    [('fa.font',), {'color': MAIN_FG_COLOR}],
    'keyboard':                [('fa.keyboard-o',), {'color': MAIN_FG_COLOR}],
    'eyedropper':              [('fa.eyedropper',), {'color': MAIN_FG_COLOR}],
    'tooloptions':             [('fa.cog',), {'color': '#333333'}],
    'edit24':                  [('fa.edit',), {'color': MAIN_FG_COLOR}],
    'edit':                    [('fa.edit',), {'color': MAIN_FG_COLOR}],
    'filenew':                 [('fa.file-o',), {'color': MAIN_FG_COLOR}],
    'fileopen':                [('fa.folder-open',), {'color': MAIN_FG_COLOR}],
    'revert':                  [('fa.undo',), {'color': MAIN_FG_COLOR}],
    'filesave':                [('fa.save',), {'color': MAIN_FG_COLOR}],
    'save_all':                [('fa.save', 'fa.save'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': MAIN_FG_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': MAIN_FG_COLOR}]}],
    'filesaveas':              [('fa.save', 'fa.pencil'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': MAIN_FG_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': MAIN_FG_COLOR}]}],
    'print':                   [('fa.print',), {'color': MAIN_FG_COLOR}],
    'fileclose':               [('fa.close',), {'color': MAIN_FG_COLOR}],
    'filecloseall':            [('fa.close', 'fa.close', 'fa.close'), {'options': [{'scale_factor': 0.6, 'offset': (0.3, -0.3), 'color': MAIN_FG_COLOR},  {'scale_factor': 0.6, 'offset': (-0.3, -0.3), 'color': MAIN_FG_COLOR}, {'scale_factor': 0.6, 'offset': (0.3, 0.3), 'color': MAIN_FG_COLOR}]}],
    'breakpoint_big':          [('fa.circle',), {'color': 'darkred'} ],
    'breakpoint_cond_big':     [('fa.question-circle',), {'color': 'darkred'},],
    'debug':                   [('spyder.debug',), {'color': '#3775a9'}],
    'arrow-step-over':         [('spyder.step-forward',), {'color': '#3775a9'}],
    'arrow-continue':          [('spyder.continue',), {'color': '#3775a9'}],
    'arrow-step-in':           [('spyder.step-into',), {'color': '#3775a9'}],
    'arrow-step-out':          [('spyder.step-out',), {'color': '#3775a9'}],
    'stop_debug':              [('fa.stop',), {'color': '#3775a9'}],
    'run':                     [('fa.play',), {'color': 'green'}],
    'run_settings':            [('fa.wrench', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': MAIN_FG_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_again':               [('fa.repeat', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': MAIN_FG_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_selection':           [('spyder.run-selection',), {'color': MAIN_FG_COLOR}],
    'run_cell':                [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                {'options': [{'color': '#fff683'}, {'color': MAIN_FG_COLOR}, {'color': 'green'}]}],
    'run_cell_advance':        [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play', 'spyder.cell-next'),
                                {'options': [{'color': '#fff683'}, {'color': MAIN_FG_COLOR,}, {'color': 'green'}, {'color': 'red'}]}],
    'todo_list':               [('fa.th-list', 'fa.check'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'color': '#3775a9', 'color_disabled': '#748fa6'}]}],
    'wng_list':                [('fa.th-list', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'prev_wng':                [('fa.arrow-left', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'next_wng':                [('fa.arrow-right', 'fa.warning'), {'options': [{'color': '999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'last_edit_location':      [('fa.caret-up',), {'color': MAIN_FG_COLOR}],
    'prev_cursor':             [('fa.hand-o-left',), {'color': MAIN_FG_COLOR}],
    'next_cursor':             [('fa.hand-o-right',), {'color': MAIN_FG_COLOR}],
    'comment':                 [('fa.comment',), {'color': MAIN_FG_COLOR}],
    'indent':                  [('fa.indent',), {'color': MAIN_FG_COLOR}],
    'unindent':                [('fa.outdent',), {'color': MAIN_FG_COLOR}],
    'gotoline':                [('fa.sort-numeric-asc',), {'color': MAIN_FG_COLOR}],
    'error':                   [('fa.times-circle',), {'color': 'darkred'}],
    'warning':                 [('fa.warning',), {'color': 'orange'}],
    'todo':                    [('fa.exclamation',), {'color': '#3775a9'}],
    'ipython_console':         [('spyder.ipython-logo-alt',), {'color': MAIN_FG_COLOR}],
    'ipython_console_t':       [('spyder.ipython-logo-alt',), {'color':'gray'}],
    'python':                  [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'pythonpath':              [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'terminated':              [('fa.circle',), {'color': MAIN_FG_COLOR}],
    'cmdprompt':               [('fa.terminal',), {'color': MAIN_FG_COLOR}],
    'cmdprompt_t':             [('fa.terminal',), {'color':'gray'}],
    'console':                 [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'findf':                   [('fa.file-o', 'fa.search'), {'options': [{'scale_factor': 1.0, 'color': MAIN_FG_COLOR}, {'scale_factor': 0.6, 'color': MAIN_FG_COLOR}]}],
    'history24':               [('fa.history',), {'color': MAIN_FG_COLOR}],
    'history':                 [('fa.history',), {'color': MAIN_FG_COLOR}],
    'help':                    [('fa.question-circle',), {'color': MAIN_FG_COLOR}],
    'lock':                    [('fa.lock',), {'color': MAIN_FG_COLOR}],
    'lock_open':               [('fa.unlock-alt',), {'color': MAIN_FG_COLOR}],
    'outline_explorer':        [('spyder.treeview',), {'color': MAIN_FG_COLOR}],
    'project_expanded':        [('fa.plus',), {'color': MAIN_FG_COLOR}],
    'dictedit':                [('fa.th-list',), {'color': MAIN_FG_COLOR}],
    'previous':                [('fa.arrow-left',), {'color': MAIN_FG_COLOR}],
    'next':                    [('fa.arrow-right',), {'color': MAIN_FG_COLOR}],
    'set_workdir':             [('fa.check',), {'color': MAIN_FG_COLOR}],
    'up':                      [('fa.arrow-up',), {'color': MAIN_FG_COLOR}],
    'down':                    [('fa.arrow-down',), {'color': MAIN_FG_COLOR}],
    'filesaveas2':             [('fa.save', 'fa.close'), {'options': [{'scale_factor': 0.8, 'offset': (-0.1, -0.1), 'color': MAIN_FG_COLOR}, {'offset': (0.2, 0.2), 'color': MAIN_FG_COLOR}]}],   # save_session_action
    'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': '#414141'}, {'color': '#fafafa'}, {'color': '#ee0000'}]}],
    'find':                    [('fa.search',), {'color': MAIN_FG_COLOR}],
    'findnext':                [('fa.search', 'fa.long-arrow-down'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': MAIN_FG_COLOR}, {'offset': (-0.3, 0.0), 'color': MAIN_FG_COLOR}]}],
    'findprevious':            [('fa.search', 'fa.long-arrow-up'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': MAIN_FG_COLOR}, {'offset': (-0.3, 0.0), 'color': MAIN_FG_COLOR}]}],
    'replace':                 [('fa.exchange',), {'color': MAIN_FG_COLOR}],
    'undo':                    [('fa.undo',), {'color': MAIN_FG_COLOR}],
    'redo':                    [('fa.repeat',), {'color': MAIN_FG_COLOR}],
    'restart':                 [('fa.repeat',), {'çolor': '#3775a9'}],
    'editcopy':                [('fa.copy',), {'color': MAIN_FG_COLOR}],
    'editcut':                 [('fa.scissors',), {'color': MAIN_FG_COLOR}],
    'editpaste':               [('fa.clipboard',), {'color': MAIN_FG_COLOR}],
    'editdelete':              [('fa.eraser',), {'color': MAIN_FG_COLOR}],
    'editclear':               [('fa.times',), {'color': MAIN_FG_COLOR}],
    'selectall':               [('spyder.text-select-all',), {'color': MAIN_FG_COLOR}],
    'pythonpath_mgr':          [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'exit':                    [('fa.power-off',), {'color': 'darkred'}],
    'advanced':                [('fa.gear',), {'color': MAIN_FG_COLOR}],
    'bug':                     [('fa.bug',), {'color': MAIN_FG_COLOR}],
    'maximize':                [('spyder.maximize-pane',), {'color': MAIN_FG_COLOR}],
    'unmaximize':              [('spyder.minimize-pane',), {'color': MAIN_FG_COLOR}],
    'window_nofullscreen':     [('spyder.inward',), {'color': MAIN_FG_COLOR}],
    'window_fullscreen':       [('fa.arrows-alt',), {'color': MAIN_FG_COLOR}],
    'MessageBoxWarning':       [('fa.warning',), {'color': MAIN_FG_COLOR}],
    'arredit':                 [('fa.table',), {'color': MAIN_FG_COLOR}],
    'zoom_out':                [('fa.search-minus',), {'color': MAIN_FG_COLOR}],
    'zoom_in':                 [('fa.search-plus',), {'color': MAIN_FG_COLOR}],
    'home':                    [('fa.home',), {'color': MAIN_FG_COLOR}],
    'find':                    [('fa.search',), {'color': MAIN_FG_COLOR}],
    'plot':                    [('fa.line-chart',), {'color': MAIN_FG_COLOR}],
    'hist':                    [('fa.bar-chart',), {'color': MAIN_FG_COLOR}],
    'imshow':                  [('fa.image',), {'color': MAIN_FG_COLOR}],
    'insert':                  [('fa.sign-in',), {'color': MAIN_FG_COLOR}],
    'rename':                  [('fa.pencil',), {'color': MAIN_FG_COLOR}],
    'edit_add':                [('fa.plus',), {'color': MAIN_FG_COLOR}],
    'edit_remove':             [('fa.minus',), {'color': MAIN_FG_COLOR}],
    'browse_tab':              [('fa.folder-o',), {'color': MAIN_FG_COLOR}],
    'filelist':                [('fa.list',), {'color': MAIN_FG_COLOR}],
    'newwindow':               [('spyder.window',), {'color': MAIN_FG_COLOR}],
    'versplit':                [('spyder.rows',), {'color': MAIN_FG_COLOR}],
    'horsplit':                [('fa.columns',), {'color': MAIN_FG_COLOR}],
    'close_panel':             [('fa.close',), {'color': MAIN_FG_COLOR}],
    'class':                   [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'method':                  [('spyder.circle-letter-m',), {'color':'#7ea67e'}],
    'function':                [('spyder.circle-letter-f',), {'color':'orange'}],
    'blockcomment':            [('spyder.circle-hash',), {'color':'grey'}],
    'cell':                    [('spyder.circle-percent',), {'color':'red'}],
    'fromcursor':              [('fa.hand-o-right',), {'color': MAIN_FG_COLOR}],
    'filter':                  [('fa.filter',), {'color': MAIN_FG_COLOR}],
    'folder_new':              [('fa.folder-o', 'fa.plus'), {'options': [{'color': MAIN_FG_COLOR}, {'scale_factor': 0.5, 'offset': (0.0, 0.1), 'color': MAIN_FG_COLOR}]}],
    'package_new':             [('fa.folder-o', 'spyder.python-logo'), {'options': [{'offset': (0.0, -0.125), 'color': MAIN_FG_COLOR}, {'offset': (0.0, 0.125), 'color': MAIN_FG_COLOR}]}],
    'vcs_commit':              [('fa.check',), {'color': 'green'}],
    'vcs_browse':              [('fa.search',), {'color': 'green'}],
    'kill':                    [('fa.warning',), {'color': MAIN_FG_COLOR}],
    'reload':                  [('fa.repeat',), {'color': MAIN_FG_COLOR}],
    'auto_reload':             [('fa.repeat', 'fa.clock-o'), {'options': [{'scale_factor': 0.75, 'offset': (-0.1, -0.1), 'color': MAIN_FG_COLOR}, {'scale_factor': 0.5, 'offset': (0.25, 0.25), 'color': MAIN_FG_COLOR}]}],
    'fileimport':              [('fa.download',), {'color': MAIN_FG_COLOR}],
    'environ':                 [('fa.th-list',), {'color': MAIN_FG_COLOR}],
    'options_less':            [('fa.minus-square',), {'color': MAIN_FG_COLOR}],
    'options_more':            [('fa.plus-square',), {'color': MAIN_FG_COLOR}],
    'ArrowDown':               [('fa.arrow-circle-down',), {'color': MAIN_FG_COLOR}],
    'ArrowUp':                 [('fa.arrow-circle-up',), {'color': MAIN_FG_COLOR}],
    'ArrowBack':               [('fa.arrow-circle-left',), {'color': MAIN_FG_COLOR}],
    'ArrowForward':            [('fa.arrow-circle-right',), {'color': MAIN_FG_COLOR}],
    'DialogApplyButton':       [('fa.check',), {'color': MAIN_FG_COLOR}],
    'DialogCloseButton':       [('fa.close',), {'color': MAIN_FG_COLOR}],
    'DirClosedIcon':           [('fa.folder-o',), {'color': MAIN_FG_COLOR}],
    'DialogHelpButton':        [('fa.life-ring',), {'color': 'darkred'}],
    'MessageBoxInformation':   [('fa.info',), {'color': MAIN_FG_COLOR}],
    'DirOpenIcon':             [('fa.folder-open',), {'color': MAIN_FG_COLOR}],
    'FileIcon':                [('fa.file-o',), {'color': MAIN_FG_COLOR}],
    'ExcelFileIcon':           [('fa.file-excel-o',), {'color': MAIN_FG_COLOR}],
    'WordFileIcon':            [('fa.file-word-o',), {'color': MAIN_FG_COLOR}],
    'PowerpointFileIcon':      [('fa.file-powerpoint-o',), {'color': MAIN_FG_COLOR}],
    'PDFIcon':                 [('fa.file-pdf-o',), {'color': MAIN_FG_COLOR}],
    'AudioFileIcon':           [('fa.file-audio-o',), {'color': MAIN_FG_COLOR}],
    'ImageFileIcon':           [('fa.file-image-o',), {'color': MAIN_FG_COLOR}],
    'ArchiveFileIcon':         [('fa.file-archive-o',), {'color': MAIN_FG_COLOR}],
    'VideoFileIcon':           [('fa.file-video-o',), {'color': MAIN_FG_COLOR}],
    'TextFileIcon':            [('fa.file-text-o',), {'color': MAIN_FG_COLOR}],
    'CFileIcon':               [('mdi.language-c',), {'color': MAIN_FG_COLOR}],
    'CppFileIcon':             [('mdi.language-cpp',), {'color': MAIN_FG_COLOR}],
    'CsharpFileIcon':          [('mdi.language-csharp',), {'color': MAIN_FG_COLOR}],
    'PythonFileIcon':          [('mdi.language-python',), {'color': MAIN_FG_COLOR}],
    'JavaFileIcon':            [('mdi.language-java',), {'color': MAIN_FG_COLOR}],
    'JavascriptFileIcon':      [('mdi.language-javascript',), {'color': MAIN_FG_COLOR}],
    'RFileIcon':               [('mdi.language-r',), {'color': MAIN_FG_COLOR}],
    'SwiftFileIcon':           [('mdi.language-swift',), {'color': MAIN_FG_COLOR}],
    'GridFileIcon':            [('mdi.grid',), {'color': MAIN_FG_COLOR}],
    'WindowsFileIcon':         [('mdi.windows',), {'color': MAIN_FG_COLOR}],
    'PowershellFileIcon':      [('mdi.powershell',), {'color': MAIN_FG_COLOR}],
    'DollarFileIcon':          [('fa5s.file-invoice-dollar',), {'color': MAIN_FG_COLOR}],
    'MarkdownFileIcon':        [('mdi.markdown',), {'color': MAIN_FG_COLOR}],
    'JsonFileIcon':            [('mdi.json',), {'color': MAIN_FG_COLOR}],
    'ExclamationFileIcon':     [('mdi.exclamation',), {'color': MAIN_FG_COLOR}],
    'CodeFileIcon':             [('mdi.xml',), {'color': MAIN_FG_COLOR}],
    'project':                 [('fa.folder-open-o',), {'color': MAIN_FG_COLOR}],
    'DriveHDIcon':             [('fa.hdd-o',), {'color': MAIN_FG_COLOR}],
    'arrow':                   [('fa.arrow-right',), {'color': MAIN_FG_COLOR}],
    'collapse':                [('spyder.inward',), {'color': MAIN_FG_COLOR}],
    'expand':                  [('fa.arrows-alt',), {'color': MAIN_FG_COLOR}],
    'restore':                 [('fa.level-up',), {'color': MAIN_FG_COLOR}],
    'collapse_selection':      [('fa.minus-square-o',), {'color': MAIN_FG_COLOR}],
    'expand_selection':        [('fa.plus-square-o',), {'color': MAIN_FG_COLOR}],
    'copywop':                 [('fa.terminal',), {'color': MAIN_FG_COLOR}],
    'editpaste':               [('fa.paste',), {'color': MAIN_FG_COLOR}],
    'editcopy':                [('fa.copy',), {'color': MAIN_FG_COLOR}],
    'edit':                    [('fa.edit',), {'color': MAIN_FG_COLOR}],
    'convention':              [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'refactor':                [('spyder.circle-letter-r',), {'color':'#3775a9'}],
    '2uparrow':                [('fa.angle-double-up',), {'color': MAIN_FG_COLOR}],
    '1uparrow':                [('fa.angle-up',), {'color': MAIN_FG_COLOR}],
    '2downarrow':              [('fa.angle-double-down',), {'color': MAIN_FG_COLOR}],
    '1downarrow':              [('fa.angle-down',), {'color': MAIN_FG_COLOR}],
    # --- Autocompletion type icons --------------
    'attribute':               [('mdi.alpha-a-box',), {'color': 'magenta', 'scale_factor': 1.3}],
    'module':                  [('mdi.alpha-m-box',), {'color': '#daa520', 'scale_factor': 1.3}],
    'class':                   [('mdi.alpha-c-box',), {'color':'#3775a9', 'scale_factor': 1.3}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c', 'scale_factor': 1.1}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c', 'scale_factor': 1.1}],
    'method':                  [('mdi.alpha-m-box',), {'color':'#7ea67e', 'scale_factor': 1.3}],
    'function':                [('mdi.alpha-f-box',), {'color':'orange', 'scale_factor': 1.3}],
    'blockcomment':            [('fa5s.hashtag',), {'color':'grey'}],
    'cell':                    [('mdi.percent',), {'color':'red'}],
    'no_match':                [('fa.circle',), {'color': 'gray'}],
    'github':                  [('fa.github',), {'color': MAIN_FG_COLOR}],
    # --- Spyder Tour --------------------------------------------------------
    'tour.close':              [('fa.close',), {'color': MAIN_FG_COLOR}],
    'tour.home':               [('fa.fast-backward',), {'color': MAIN_FG_COLOR}],
    'tour.previous':           [('fa.backward',), {'color': MAIN_FG_COLOR}],
    'tour.next':               [('fa.forward',), {'color': MAIN_FG_COLOR}],
    'tour.end':                [('fa.fast-forward',), {'color': MAIN_FG_COLOR}],
    # --- Third party plugins ------------------------------------------------
    'profiler':                [('fa.clock-o',), {'color': MAIN_FG_COLOR}],
    'pylint':                  [('fa.search', 'fa.check'), {'options': [{'color': MAIN_FG_COLOR}, {'offset': (0.125, 0.125), 'color': 'orange'}]}],
    'condapackages':           [('fa.archive',), {'color': MAIN_FG_COLOR}],
    'spyder.example':          [('fa.eye',), {'color': MAIN_FG_COLOR}],
    'spyder.autopep8':         [('fa.eye',), {'color': MAIN_FG_COLOR}],
    'spyder.memory_profiler':  [('fa.eye',), {'color': MAIN_FG_COLOR}],
    'spyder.line_profiler':    [('fa.eye',), {'color': MAIN_FG_COLOR}],
    'symbol_find':             [('fa.at',), {'color': MAIN_FG_COLOR}],
    'folding.arrow_right_off': [('fa.caret-right',), {'color': 'gray'}],
    'folding.arrow_right_on':  [('fa.caret-right',), {'color': MAIN_FG_COLOR}],
    'folding.arrow_down_off':  [('fa.caret-down',), {'color': 'gray'}],
    'folding.arrow_down_on':   [('fa.caret-down',), {'color': MAIN_FG_COLOR}],
    'lspserver':               [('fa.server',), {'color': MAIN_FG_COLOR}],
    'dependency_ok':           [('fa.check',), {'color': MAIN_FG_COLOR}],
    'dependency_warning':      [('fa.warning',), {'color': 'orange'}],
    'dependency_error':        [('fa.warning',), {'color': 'darkred'}],
}


def get_std_icon(name, size=None):
    """Get standard platform icon
    Call 'show_std_icons()' for details"""
    if not name.startswith('SP_'):
        name = 'SP_' + name
    icon = QWidget().style().standardIcon(getattr(QStyle, name))
    if size is None:
        return icon
    else:
        return QIcon(icon.pixmap(size, size))


def get_icon(name, default=None, resample=False):
    """Return image inside a QIcon object.

    default: default image name or icon
    resample: if True, manually resample icon pixmaps for usual sizes
    (16, 24, 32, 48, 96, 128, 256). This is recommended for QMainWindow icons
    created from SVG images on non-Windows platforms due to a Qt bug (see
    Issue 1314).
    """

    icon_path = get_image_path(name, default=None)
    if icon_path is not None:
        icon = QIcon(icon_path)
    elif isinstance(default, QIcon):
        icon = default
    elif default is None:
        try:
            icon = get_std_icon(name[:-4])
        except AttributeError:
            icon = QIcon(get_image_path(name, default))
    else:
        icon = QIcon(get_image_path(name, default))
    if resample:
        icon0 = QIcon()
        for size in (16, 24, 32, 48, 96, 128, 256, 512):
            icon0.addPixmap(icon.pixmap(size, size))
        return icon0
    else:
        return icon


def icon(name, resample=False, icon_path=None):
    theme = CONF.get('appearance', 'icon_theme')
    if theme == 'spyder 3':
        if not _resource['loaded']:
            qta.load_font('spyder', 'spyder.ttf', 'spyder-charmap.json',
                          directory=_resource['directory'])
            _resource['loaded'] = True
        args, kwargs = _qtaargs[name]
        return qta.icon(*args, **kwargs)
    elif theme == 'spyder 2':
        icon = get_icon(name + '.png', resample=resample)
        if icon_path:
            icon_path = osp.join(icon_path, name + '.png')
            if osp.isfile(icon_path):
                icon = QIcon(icon_path)
        return icon if icon is not None else QIcon()
