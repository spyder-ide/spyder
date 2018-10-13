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
from qtconsole.styles import dark_color

# Local imports
from spyder.config.base import get_image_path
from spyder.config.main import CONF
from spyder.config.gui import get_color_scheme
import qtawesome as qta

# Main color for a dark theme
MAIN_LIGHT_COLOR = 'white'

_resource = {
    'directory': osp.join(osp.dirname(osp.realpath(__file__)), '../fonts'),
    'loaded': False,
}

_qtaargs = {
    'log':                     [('fa.file-text-o',), {}],
    'configure':               [('fa.wrench',), {}],
    'bold':                    [('fa.bold',), {}],
    'italic':                  [('fa.italic',), {}],
    'genprefs':                [('fa.cogs',), {}],
    'exit':                    [('fa.power-off',), {}],
    'run_small':               [('fa.play',), {'color': 'green'}],
    'stop':                    [('fa.stop',), {'color': 'darkred'}],
    'syspath':                 [('fa.cogs',), {}],
    'font':                    [('fa.font',), {}],
    'keyboard':                [('fa.keyboard-o',), {}],
    'eyedropper':              [('fa.eyedropper',), {}],
    'tooloptions':             [('fa.cog',), {'color': '#333333'}],
    'edit24':                  [('fa.edit',), {}],
    'edit':                    [('fa.edit',), {}],
    'filenew':                 [('fa.file-o',), {}],
    'fileopen':                [('fa.folder-open',), {}],
    'revert':                  [('fa.undo',), {}],
    'filesave':                [('fa.save',), {}],
    'save_all':                [('fa.save', 'fa.save'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6}, {'offset': (0.2, 0.2), 'scale_factor': 0.6}]}],
    'filesaveas':              [('fa.save', 'fa.pencil'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6}, {'offset': (0.2, 0.2), 'scale_factor': 0.6}]}],
    'print':                   [('fa.print',), {}],
    'fileclose':               [('fa.close',), {}],
    'filecloseall':            [('fa.close', 'fa.close', 'fa.close'), {'options': [{'scale_factor': 0.6, 'offset': (0.3, -0.3)},  {'scale_factor': 0.6, 'offset': (-0.3, -0.3)}, {'scale_factor': 0.6, 'offset': (0.3, 0.3)}]}],
    'breakpoint_big':          [('fa.circle',), {'color': 'darkred'} ],
    'breakpoint_cond_big':     [('fa.question-circle',), {'color': 'darkred'},],
    'debug':                   [('spyder.debug',), {'color': '#3775a9'}],
    'arrow-step-over':         [('spyder.step-forward',), {'color': '#3775a9'}],
    'arrow-continue':          [('spyder.continue',), {'color': '#3775a9'}],
    'arrow-step-in':           [('spyder.step-into',), {'color': '#3775a9'}],
    'arrow-step-out':          [('spyder.step-out',), {'color': '#3775a9'}],
    'stop_debug':              [('fa.stop',), {'color': '#3775a9'}],
    'run':                     [('fa.play',), {'color': 'green'}],
    'run_settings':            [('fa.wrench', 'fa.play'), {'options': [{'offset':(0.0, -0.1)}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_again':               [('fa.repeat', 'fa.play'), {'options': [{'offset':(0.0, -0.1)}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_selection':           [('spyder.run-selection',), {}],
    'run_cell':                [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                {'options': [{'color': '#fff683'}, {}, {'color': 'green'}]}],
    'run_cell_advance':        [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play', 'spyder.cell-next'),
                                {'options': [{'color': '#fff683'}, {}, {'color': 'green'}, {'color': 'red'}]}],
    'todo_list':               [('fa.th-list', 'fa.check'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'color': '#3775a9', 'color_disabled': '#748fa6'}]}],
    'wng_list':                [('fa.th-list', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'prev_wng':                [('fa.arrow-left', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'next_wng':                [('fa.arrow-right', 'fa.warning'), {'options': [{'color': '999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'last_edit_location':      [('fa.caret-up',), {}],
    'prev_cursor':             [('fa.hand-o-left',), {}],
    'next_cursor':             [('fa.hand-o-right',), {}],
    'comment':                 [('fa.comment',), {}],
    'indent':                  [('fa.indent',), {}],
    'unindent':                [('fa.outdent',), {}],
    'gotoline':                [('fa.sort-numeric-asc',), {}],
    'error':                   [('fa.times-circle',), {'color': 'darkred'}],
    'warning':                 [('fa.warning',), {'color': 'orange'}],
    'todo':                    [('fa.check',), {'color': '#3775a9'}],
    'ipython_console':         [('spyder.ipython-logo-alt',), {}],
    'ipython_console_t':       [('spyder.ipython-logo-alt',), {'color':'gray'}],
    'python':                  [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'pythonpath':              [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'terminated':              [('fa.circle',), {}],
    'cmdprompt':               [('fa.terminal',), {}],
    'cmdprompt_t':             [('fa.terminal',), {'color':'gray'}],
    'console':                 [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'findf':                   [('fa.file-o', 'fa.search'), {'options': [{'scale_factor': 1.0}, {'scale_factor': 0.6}]}],
    'history24':               [('fa.history',), {}],
    'history':                 [('fa.history',), {}],
    'help':                    [('fa.question-circle',), {}],
    'lock':                    [('fa.lock',), {}],
    'lock_open':               [('fa.unlock-alt',), {}],
    'outline_explorer':        [('spyder.treeview',), {}],
    'project_expanded':        [('fa.plus',), {}],
    'dictedit':                [('fa.th-list',), {}],
    'previous':                [('fa.arrow-left',), {}],
    'next':                    [('fa.arrow-right',), {}],
    'set_workdir':             [('fa.check',), {}],
    'up':                      [('fa.arrow-up',), {}],
    'down':                    [('fa.arrow-down',), {}],
    'filesaveas2':             [('fa.save', 'fa.close'), {'options': [{'scale_factor': 0.8, 'offset': (-0.1, -0.1)}, {'offset': (0.2, 0.2)}]}],   # save_session_action
    'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': '#414141'}, {'color': '#fafafa'}, {'color': '#ee0000'}]}],
    'find':                    [('fa.search',), {}],
    'findnext':                [('fa.search', 'fa.long-arrow-down'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0)}, {'offset': (-0.3, 0.0)}]}],
    'findprevious':            [('fa.search', 'fa.long-arrow-up'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0)}, {'offset': (-0.3, 0.0)}]}],
    'replace':                 [('fa.exchange',), {}],
    'undo':                    [('fa.undo',), {}],
    'redo':                    [('fa.repeat',), {}],
    'restart':                 [('fa.repeat',), {'çolor': '#3775a9'}],
    'editcopy':                [('fa.copy',), {}],
    'editcut':                 [('fa.scissors',), {}],
    'editpaste':               [('fa.clipboard',), {}],
    'editdelete':              [('fa.eraser',), {}],
    'editclear':               [('fa.times',), {}],
    'selectall':               [('spyder.text-select-all',), {}],
    'pythonpath_mgr':          [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'exit':                    [('fa.power-off',), {'color': 'darkred'}],
    'advanced':                [('fa.gear',), {}],
    'bug':                     [('fa.bug',), {}],
    'maximize':                [('spyder.maximize-pane',), {}],
    'unmaximize':              [('spyder.minimize-pane',), {}],
    'window_nofullscreen':     [('spyder.inward',), {}],
    'window_fullscreen':       [('fa.arrows-alt',), {}],
    'MessageBoxWarning':       [('fa.warning',), {}],
    'arredit':                 [('fa.table',), {}],
    'zoom_out':                [('fa.search-minus',), {}],
    'zoom_in':                 [('fa.search-plus',), {}],
    'home':                    [('fa.home',), {}],
    'find':                    [('fa.search',), {}],
    'plot':                    [('fa.line-chart',), {}],
    'hist':                    [('fa.bar-chart',), {}],
    'imshow':                  [('fa.image',), {}],
    'insert':                  [('fa.sign-in',), {}],
    'rename':                  [('fa.pencil',), {}],
    'edit_add':                [('fa.plus',), {}],
    'edit_remove':             [('fa.minus',), {}],
    'browse_tab':              [('fa.folder-o',), {}],
    'filelist':                [('fa.list',), {}],
    'newwindow':               [('spyder.window',), {}],
    'versplit':                [('spyder.rows',), {}],
    'horsplit':                [('fa.columns',), {}],
    'close_panel':             [('fa.close',), {}],
    'class':                   [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'method':                  [('spyder.circle-letter-m',), {'color':'#7ea67e'}],
    'function':                [('spyder.circle-letter-f',), {'color':'orange'}],
    'blockcomment':            [('spyder.circle-hash',), {'color':'grey'}],
    'cell':                    [('spyder.circle-percent',), {'color':'red'}],
    'fromcursor':              [('fa.hand-o-right',), {}],
    'filter':                  [('fa.filter',), {}],
    'folder_new':              [('fa.folder-o', 'fa.plus'), {'options': [{}, {'scale_factor': 0.5, 'offset': (0.0, 0.1)}]}],
    'package_new':             [('fa.folder-o', 'spyder.python-logo'), {'options': [{'offset': (0.0, -0.125)}, {'offset': (0.0, 0.125)}]}],
    'vcs_commit':              [('fa.check',), {'color': 'green'}],
    'vcs_browse':              [('fa.search',), {'color': 'green'}],
    'kill':                    [('fa.warning',), {}],
    'reload':                  [('fa.repeat',), {}],
    'auto_reload':             [('fa.repeat', 'fa.clock-o'), {'options': [{'scale_factor': 0.75, 'offset': (-0.1, -0.1)}, {'scale_factor': 0.5, 'offset': (0.25, 0.25)}]}],
    'fileimport':              [('fa.download',), {}],
    'environ':                 [('fa.th-list',), {}],
    'options_less':            [('fa.minus-square',), {}],
    'options_more':            [('fa.plus-square',), {}],
    'ArrowDown':               [('fa.arrow-circle-down',), {}],
    'ArrowUp':                 [('fa.arrow-circle-up',), {}],
    'ArrowBack':               [('fa.arrow-circle-left',), {}],
    'ArrowForward':            [('fa.arrow-circle-right',), {}],
    'DialogApplyButton':       [('fa.check',), {}],
    'DialogCloseButton':       [('fa.close',), {}],
    'DirClosedIcon':           [('fa.folder-o',), {}],
    'DialogHelpButton':        [('fa.life-ring',), {'color': 'darkred'}],
    'MessageBoxInformation':   [('fa.info',), {'color': '3775a9'}],
    'DirOpenIcon':             [('fa.folder-open',), {}],
    'FileIcon':                [('fa.file-o',), {}],
    'ExcelFileIcon':           [('fa.file-excel-o',), {}],
    'WordFileIcon':            [('fa.file-word-o',), {}],
    'PowerpointFileIcon':      [('fa.file-powerpoint-o',), {}],
    'PDFIcon':                 [('fa.file-pdf-o',), {}],
    'AudioFileIcon':           [('fa.file-audio-o',), {}],
    'ImageFileIcon':           [('fa.file-image-o',), {}],
    'ArchiveFileIcon':         [('fa.file-archive-o',), {}],
    'VideoFileIcon':           [('fa.file-video-o',), {}],
    'TextFileIcon':            [('fa.file-text-o',), {}],
    'project':                 [('fa.folder-open-o',), {}],
    'DriveHDIcon':             [('fa.hdd-o',), {}],
    'arrow':                   [('fa.arrow-right',), {}],
    'collapse':                [('spyder.inward',), {}],
    'expand':                  [('fa.arrows-alt',), {}],
    'restore':                 [('fa.level-up',), {}],
    'collapse_selection':      [('fa.minus-square-o',), {}],
    'expand_selection':        [('fa.plus-square-o',), {}],
    'copywop':                 [('fa.terminal',), {}],
    'editpaste':               [('fa.paste',), {}],
    'editcopy':                [('fa.copy',), {}],
    'edit':                    [('fa.edit',), {}],
    'convention':              [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'refactor':                [('spyder.circle-letter-r',), {'color':'#3775a9'}],
    '2uparrow':                [('fa.angle-double-up',), {}],
    '1uparrow':                [('fa.angle-up',), {}],
    '2downarrow':              [('fa.angle-double-down',), {}],
    '1downarrow':              [('fa.angle-down',), {}],
    # --- Autocompletion type icons --------------
    'attribute':               [('spyder.circle-letter-a',), {'color': 'magenta'}],
    'module':                  [('spyder.circle-letter-m',), {'color': '#daa520'}],
    'class':                   [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'method':                  [('spyder.circle-letter-m',), {'color':'#7ea67e'}],
    'function':                [('spyder.circle-letter-f',), {'color':'orange'}],
    'blockcomment':            [('spyder.circle-hash',), {'color':'grey'}],
    'cell':                    [('spyder.circle-percent',), {'color':'red'}],
    'no_match':                [('fa.circle',), {'color': 'gray'}],
    'github':                  [('fa.github',), {'color': 'black'}],
    # --- Spyder Tour --------------------------------------------------------
    'tour.close':              [('fa.close',), {}],
    'tour.home':               [('fa.fast-backward',), {}],
    'tour.previous':           [('fa.backward',), {}],
    'tour.next':               [('fa.forward',), {}],
    'tour.end':                [('fa.fast-forward',), {}],
    # --- Third party plugins ------------------------------------------------
    'profiler':                [('fa.clock-o',), {}],
    'pylint':                  [('fa.search', 'fa.check'), {'options': [{}, {'offset': (0.125, 0.125), 'color': 'orange'}]}],
    'condapackages':           [('fa.archive',), {}],
    'spyder.example':          [('fa.eye',), {}],
    'spyder.autopep8':         [('fa.eye',), {}],
    'spyder.memory_profiler':  [('fa.eye',), {}],
    'spyder.line_profiler':    [('fa.eye',), {}],
    'symbol_find':             [('fa.at',), {}],
    'folding.arrow_right_off': [('fa.caret-right',), {'color': 'gray'}],
    'folding.arrow_right_on':  [('fa.caret-right',), {}],
    'folding.arrow_down_off':  [('fa.caret-down',), {'color': 'gray'}],
    'folding.arrow_down_on':   [('fa.caret-down',), {}],
    'lspserver':               [('fa.server',), {}],
    'dependency_ok':           [('fa.check',), {}],
    'dependency_warning':      [('fa.warning',), {'color': 'orange'}],
    'dependency_error':        [('fa.warning',), {'color': 'darkred'}],
}

_qtaargsdark = {
    'log':                     [('fa.file-text-o',), {'color': MAIN_LIGHT_COLOR}],
    'configure':               [('fa.wrench',), {'color': MAIN_LIGHT_COLOR}],
    'bold':                    [('fa.bold',), {'color': MAIN_LIGHT_COLOR}],
    'italic':                  [('fa.italic',), {'color': MAIN_LIGHT_COLOR}],
    'genprefs':                [('fa.cogs',), {'color': MAIN_LIGHT_COLOR}],
    'exit':                    [('fa.power-off',), {'color': MAIN_LIGHT_COLOR}],
    'run_small':               [('fa.play',), {'color': 'green'}],
    'stop':                    [('fa.stop',), {'color': 'darkred'}],
    'syspath':                 [('fa.cogs',), {'color': MAIN_LIGHT_COLOR}],
    'font':                    [('fa.font',), {'color': MAIN_LIGHT_COLOR}],
    'keyboard':                [('fa.keyboard-o',), {'color': MAIN_LIGHT_COLOR}],
    'eyedropper':              [('fa.eyedropper',), {'color': MAIN_LIGHT_COLOR}],
    'tooloptions':             [('fa.cog',), {'color': '#333333'}],
    'edit24':                  [('fa.edit',), {'color': MAIN_LIGHT_COLOR}],
    'edit':                    [('fa.edit',), {'color': MAIN_LIGHT_COLOR}],
    'filenew':                 [('fa.file-o',), {'color': MAIN_LIGHT_COLOR}],
    'fileopen':                [('fa.folder-open',), {'color': MAIN_LIGHT_COLOR}],
    'revert':                  [('fa.undo',), {'color': MAIN_LIGHT_COLOR}],
    'filesave':                [('fa.save',), {'color': MAIN_LIGHT_COLOR}],
    'save_all':                [('fa.save', 'fa.save'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': MAIN_LIGHT_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': MAIN_LIGHT_COLOR}]}],
    'filesaveas':              [('fa.save', 'fa.pencil'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': MAIN_LIGHT_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': MAIN_LIGHT_COLOR}]}],
    'print':                   [('fa.print',), {'color': MAIN_LIGHT_COLOR}],
    'fileclose':               [('fa.close',), {'color': MAIN_LIGHT_COLOR}],
    'filecloseall':            [('fa.close', 'fa.close', 'fa.close'), {'options': [{'scale_factor': 0.6, 'offset': (0.3, -0.3), 'color': MAIN_LIGHT_COLOR},  {'scale_factor': 0.6, 'offset': (-0.3, -0.3), 'color': MAIN_LIGHT_COLOR}, {'scale_factor': 0.6, 'offset': (0.3, 0.3), 'color': MAIN_LIGHT_COLOR}]}],
    'breakpoint_big':          [('fa.circle',), {'color': 'darkred'} ],
    'breakpoint_cond_big':     [('fa.question-circle',), {'color': 'darkred'},],
    'debug':                   [('spyder.debug',), {'color': '#3775a9'}],
    'arrow-step-over':         [('spyder.step-forward',), {'color': '#3775a9'}],
    'arrow-continue':          [('spyder.continue',), {'color': '#3775a9'}],
    'arrow-step-in':           [('spyder.step-into',), {'color': '#3775a9'}],
    'arrow-step-out':          [('spyder.step-out',), {'color': '#3775a9'}],
    'stop_debug':              [('fa.stop',), {'color': '#3775a9'}],
    'run':                     [('fa.play',), {'color': 'green'}],
    'run_settings':            [('fa.wrench', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': MAIN_LIGHT_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_again':               [('fa.repeat', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': MAIN_LIGHT_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
    'run_selection':           [('spyder.run-selection',), {'color': MAIN_LIGHT_COLOR}],
    'run_cell':                [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                {'options': [{'color': '#fff683'}, {'color': MAIN_LIGHT_COLOR}, {'color': 'green'}]}],
    'run_cell_advance':        [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play', 'spyder.cell-next'),
                                {'options': [{'color': '#fff683'}, {'color': MAIN_LIGHT_COLOR,}, {'color': 'green'}, {'color': 'red'}]}],
    'todo_list':               [('fa.th-list', 'fa.check'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'color': '#3775a9', 'color_disabled': '#748fa6'}]}],
    'wng_list':                [('fa.th-list', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'prev_wng':                [('fa.arrow-left', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'next_wng':                [('fa.arrow-right', 'fa.warning'), {'options': [{'color': '999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
    'last_edit_location':      [('fa.caret-up',), {'color': MAIN_LIGHT_COLOR}],
    'prev_cursor':             [('fa.hand-o-left',), {'color': MAIN_LIGHT_COLOR}],
    'next_cursor':             [('fa.hand-o-right',), {'color': MAIN_LIGHT_COLOR}],
    'comment':                 [('fa.comment',), {'color': MAIN_LIGHT_COLOR}],
    'indent':                  [('fa.indent',), {'color': MAIN_LIGHT_COLOR}],
    'unindent':                [('fa.outdent',), {'color': MAIN_LIGHT_COLOR}],
    'gotoline':                [('fa.sort-numeric-asc',), {'color': MAIN_LIGHT_COLOR}],
    'error':                   [('fa.times-circle',), {'color': 'darkred'}],
    'warning':                 [('fa.warning',), {'color': 'orange'}],
    'todo':                    [('fa.check',), {'color': '#3775a9'}],
    'ipython_console':         [('spyder.ipython-logo-alt',), {'color': MAIN_LIGHT_COLOR}],
    'ipython_console_t':       [('spyder.ipython-logo-alt',), {'color':'gray'}],
    'python':                  [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'pythonpath':              [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'terminated':              [('fa.circle',), {'color': MAIN_LIGHT_COLOR}],
    'cmdprompt':               [('fa.terminal',), {'color': MAIN_LIGHT_COLOR}],
    'cmdprompt_t':             [('fa.terminal',), {'color':'gray'}],
    'console':                 [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'findf':                   [('fa.file-o', 'fa.search'), {'options': [{'scale_factor': 1.0, 'color': MAIN_LIGHT_COLOR}, {'scale_factor': 0.6, 'color': MAIN_LIGHT_COLOR}]}],
    'history24':               [('fa.history',), {'color': MAIN_LIGHT_COLOR}],
    'history':                 [('fa.history',), {'color': MAIN_LIGHT_COLOR}],
    'help':                    [('fa.question-circle',), {'color': MAIN_LIGHT_COLOR}],
    'lock':                    [('fa.lock',), {'color': MAIN_LIGHT_COLOR}],
    'lock_open':               [('fa.unlock-alt',), {'color': MAIN_LIGHT_COLOR}],
    'outline_explorer':        [('spyder.treeview',), {'color': MAIN_LIGHT_COLOR}],
    'project_expanded':        [('fa.plus',), {'color': MAIN_LIGHT_COLOR}],
    'dictedit':                [('fa.th-list',), {'color': MAIN_LIGHT_COLOR}],
    'previous':                [('fa.arrow-left',), {'color': MAIN_LIGHT_COLOR}],
    'next':                    [('fa.arrow-right',), {'color': MAIN_LIGHT_COLOR}],
    'set_workdir':             [('fa.check',), {'color': MAIN_LIGHT_COLOR}],
    'up':                      [('fa.arrow-up',), {'color': MAIN_LIGHT_COLOR}],
    'down':                    [('fa.arrow-down',), {'color': MAIN_LIGHT_COLOR}],
    'filesaveas2':             [('fa.save', 'fa.close'), {'options': [{'scale_factor': 0.8, 'offset': (-0.1, -0.1), 'color': MAIN_LIGHT_COLOR}, {'offset': (0.2, 0.2), 'color': MAIN_LIGHT_COLOR}]}],   # save_session_action
    'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': '#414141'}, {'color': '#fafafa'}, {'color': '#ee0000'}]}],
    'find':                    [('fa.search',), {'color': MAIN_LIGHT_COLOR}],
    'findnext':                [('fa.search', 'fa.long-arrow-down'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': MAIN_LIGHT_COLOR}, {'offset': (-0.3, 0.0), 'color': MAIN_LIGHT_COLOR}]}],
    'findprevious':            [('fa.search', 'fa.long-arrow-up'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': MAIN_LIGHT_COLOR}, {'offset': (-0.3, 0.0), 'color': MAIN_LIGHT_COLOR}]}],
    'replace':                 [('fa.exchange',), {'color': MAIN_LIGHT_COLOR}],
    'undo':                    [('fa.undo',), {'color': MAIN_LIGHT_COLOR}],
    'redo':                    [('fa.repeat',), {'color': MAIN_LIGHT_COLOR}],
    'restart':                 [('fa.repeat',), {'çolor': '#3775a9'}],
    'editcopy':                [('fa.copy',), {'color': MAIN_LIGHT_COLOR}],
    'editcut':                 [('fa.scissors',), {'color': MAIN_LIGHT_COLOR}],
    'editpaste':               [('fa.clipboard',), {'color': MAIN_LIGHT_COLOR}],
    'editdelete':              [('fa.eraser',), {'color': MAIN_LIGHT_COLOR}],
    'editclear':               [('fa.times',), {'color': MAIN_LIGHT_COLOR}],
    'selectall':               [('spyder.text-select-all',), {'color': MAIN_LIGHT_COLOR}],
    'pythonpath_mgr':          [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
    'exit':                    [('fa.power-off',), {'color': 'darkred'}],
    'advanced':                [('fa.gear',), {'color': MAIN_LIGHT_COLOR}],
    'bug':                     [('fa.bug',), {'color': MAIN_LIGHT_COLOR}],
    'maximize':                [('spyder.maximize-pane',), {'color': MAIN_LIGHT_COLOR}],
    'unmaximize':              [('spyder.minimize-pane',), {'color': MAIN_LIGHT_COLOR}],
    'window_nofullscreen':     [('spyder.inward',), {'color': MAIN_LIGHT_COLOR}],
    'window_fullscreen':       [('fa.arrows-alt',), {'color': MAIN_LIGHT_COLOR}],
    'MessageBoxWarning':       [('fa.warning',), {'color': MAIN_LIGHT_COLOR}],
    'arredit':                 [('fa.table',), {'color': MAIN_LIGHT_COLOR}],
    'zoom_out':                [('fa.search-minus',), {'color': MAIN_LIGHT_COLOR}],
    'zoom_in':                 [('fa.search-plus',), {'color': MAIN_LIGHT_COLOR}],
    'home':                    [('fa.home',), {'color': MAIN_LIGHT_COLOR}],
    'find':                    [('fa.search',), {'color': MAIN_LIGHT_COLOR}],
    'plot':                    [('fa.line-chart',), {'color': MAIN_LIGHT_COLOR}],
    'hist':                    [('fa.bar-chart',), {'color': MAIN_LIGHT_COLOR}],
    'imshow':                  [('fa.image',), {'color': MAIN_LIGHT_COLOR}],
    'insert':                  [('fa.sign-in',), {'color': MAIN_LIGHT_COLOR}],
    'rename':                  [('fa.pencil',), {'color': MAIN_LIGHT_COLOR}],
    'edit_add':                [('fa.plus',), {'color': MAIN_LIGHT_COLOR}],
    'edit_remove':             [('fa.minus',), {'color': MAIN_LIGHT_COLOR}],
    'browse_tab':              [('fa.folder-o',), {'color': MAIN_LIGHT_COLOR}],
    'filelist':                [('fa.list',), {'color': MAIN_LIGHT_COLOR}],
    'newwindow':               [('spyder.window',), {'color': MAIN_LIGHT_COLOR}],
    'versplit':                [('spyder.rows',), {'color': MAIN_LIGHT_COLOR}],
    'horsplit':                [('fa.columns',), {'color': MAIN_LIGHT_COLOR}],
    'close_panel':             [('fa.close',), {'color': MAIN_LIGHT_COLOR}],
    'class':                   [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'method':                  [('spyder.circle-letter-m',), {'color':'#7ea67e'}],
    'function':                [('spyder.circle-letter-f',), {'color':'orange'}],
    'blockcomment':            [('spyder.circle-hash',), {'color':'grey'}],
    'cell':                    [('spyder.circle-percent',), {'color':'red'}],
    'fromcursor':              [('fa.hand-o-right',), {'color': MAIN_LIGHT_COLOR}],
    'filter':                  [('fa.filter',), {'color': MAIN_LIGHT_COLOR}],
    'folder_new':              [('fa.folder-o', 'fa.plus'), {'options': [{'color': MAIN_LIGHT_COLOR}, {'scale_factor': 0.5, 'offset': (0.0, 0.1), 'color': MAIN_LIGHT_COLOR}]}],
    'package_new':             [('fa.folder-o', 'spyder.python-logo'), {'options': [{'offset': (0.0, -0.125), 'color': MAIN_LIGHT_COLOR}, {'offset': (0.0, 0.125), 'color': MAIN_LIGHT_COLOR}]}],
    'vcs_commit':              [('fa.check',), {'color': 'green'}],
    'vcs_browse':              [('fa.search',), {'color': 'green'}],
    'kill':                    [('fa.warning',), {'color': MAIN_LIGHT_COLOR}],
    'reload':                  [('fa.repeat',), {'color': MAIN_LIGHT_COLOR}],
    'auto_reload':             [('fa.repeat', 'fa.clock-o'), {'options': [{'scale_factor': 0.75, 'offset': (-0.1, -0.1), 'color': MAIN_LIGHT_COLOR}, {'scale_factor': 0.5, 'offset': (0.25, 0.25), 'color': MAIN_LIGHT_COLOR}]}],
    'fileimport':              [('fa.download',), {'color': MAIN_LIGHT_COLOR}],
    'environ':                 [('fa.th-list',), {'color': MAIN_LIGHT_COLOR}],
    'options_less':            [('fa.minus-square',), {'color': MAIN_LIGHT_COLOR}],
    'options_more':            [('fa.plus-square',), {'color': MAIN_LIGHT_COLOR}],
    'ArrowDown':               [('fa.arrow-circle-down',), {'color': MAIN_LIGHT_COLOR}],
    'ArrowUp':                 [('fa.arrow-circle-up',), {'color': MAIN_LIGHT_COLOR}],
    'ArrowBack':               [('fa.arrow-circle-left',), {'color': MAIN_LIGHT_COLOR}],
    'ArrowForward':            [('fa.arrow-circle-right',), {'color': MAIN_LIGHT_COLOR}],
    'DialogApplyButton':       [('fa.check',), {'color': MAIN_LIGHT_COLOR}],
    'DialogCloseButton':       [('fa.close',), {'color': MAIN_LIGHT_COLOR}],
    'DirClosedIcon':           [('fa.folder-o',), {'color': MAIN_LIGHT_COLOR}],
    'DialogHelpButton':        [('fa.life-ring',), {'color': 'darkred'}],
    'MessageBoxInformation':   [('fa.info',), {'color': '3775a9'}],
    'DirOpenIcon':             [('fa.folder-open',), {'color': MAIN_LIGHT_COLOR}],
    'FileIcon':                [('fa.file-o',), {'color': MAIN_LIGHT_COLOR}],
    'ExcelFileIcon':           [('fa.file-excel-o',), {'color': MAIN_LIGHT_COLOR}],
    'WordFileIcon':            [('fa.file-word-o',), {'color': MAIN_LIGHT_COLOR}],
    'PowerpointFileIcon':      [('fa.file-powerpoint-o',), {'color': MAIN_LIGHT_COLOR}],
    'PDFIcon':                 [('fa.file-pdf-o',), {'color': MAIN_LIGHT_COLOR}],
    'AudioFileIcon':           [('fa.file-audio-o',), {'color': MAIN_LIGHT_COLOR}],
    'ImageFileIcon':           [('fa.file-image-o',), {'color': MAIN_LIGHT_COLOR}],
    'ArchiveFileIcon':         [('fa.file-archive-o',), {'color': MAIN_LIGHT_COLOR}],
    'VideoFileIcon':           [('fa.file-video-o',), {'color': MAIN_LIGHT_COLOR}],
    'TextFileIcon':            [('fa.file-text-o',), {'color': MAIN_LIGHT_COLOR}],
    'project':                 [('fa.folder-open-o',), {'color': MAIN_LIGHT_COLOR}],
    'DriveHDIcon':             [('fa.hdd-o',), {'color': MAIN_LIGHT_COLOR}],
    'arrow':                   [('fa.arrow-right',), {'color': MAIN_LIGHT_COLOR}],
    'collapse':                [('spyder.inward',), {'color': MAIN_LIGHT_COLOR}],
    'expand':                  [('fa.arrows-alt',), {'color': MAIN_LIGHT_COLOR}],
    'restore':                 [('fa.level-up',), {'color': MAIN_LIGHT_COLOR}],
    'collapse_selection':      [('fa.minus-square-o',), {'color': MAIN_LIGHT_COLOR}],
    'expand_selection':        [('fa.plus-square-o',), {'color': MAIN_LIGHT_COLOR}],
    'copywop':                 [('fa.terminal',), {'color': MAIN_LIGHT_COLOR}],
    'editpaste':               [('fa.paste',), {'color': MAIN_LIGHT_COLOR}],
    'editcopy':                [('fa.copy',), {'color': MAIN_LIGHT_COLOR}],
    'edit':                    [('fa.edit',), {'color': MAIN_LIGHT_COLOR}],
    'convention':              [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'refactor':                [('spyder.circle-letter-r',), {'color':'#3775a9'}],
    '2uparrow':                [('fa.angle-double-up',), {'color': MAIN_LIGHT_COLOR}],
    '1uparrow':                [('fa.angle-up',), {'color': MAIN_LIGHT_COLOR}],
    '2downarrow':              [('fa.angle-double-down',), {'color': MAIN_LIGHT_COLOR}],
    '1downarrow':              [('fa.angle-down',), {'color': MAIN_LIGHT_COLOR}],
    # --- Autocompletion type icons --------------
    'attribute':               [('spyder.circle-letter-a',), {'color': 'magenta'}],
    'module':                  [('spyder.circle-letter-m',), {'color': '#daa520'}],
    'class':                   [('spyder.circle-letter-c',), {'color':'#3775a9'}],
    'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c'}],
    'method':                  [('spyder.circle-letter-m',), {'color':'#7ea67e'}],
    'function':                [('spyder.circle-letter-f',), {'color':'orange'}],
    'blockcomment':            [('spyder.circle-hash',), {'color':'grey'}],
    'cell':                    [('spyder.circle-percent',), {'color':'red'}],
    'no_match':                [('fa.circle',), {'color': 'gray'}],
    'github':                  [('fa.github',), {'color': MAIN_LIGHT_COLOR}],
    # --- Spyder Tour --------------------------------------------------------
    'tour.close':              [('fa.close',), {'color': MAIN_LIGHT_COLOR}],
    'tour.home':               [('fa.fast-backward',), {'color': MAIN_LIGHT_COLOR}],
    'tour.previous':           [('fa.backward',), {'color': MAIN_LIGHT_COLOR}],
    'tour.next':               [('fa.forward',), {'color': MAIN_LIGHT_COLOR}],
    'tour.end':                [('fa.fast-forward',), {'color': MAIN_LIGHT_COLOR}],
    # --- Third party plugins ------------------------------------------------
    'profiler':                [('fa.clock-o',), {'color': MAIN_LIGHT_COLOR}],
    'pylint':                  [('fa.search', 'fa.check'), {'options': [{'color': MAIN_LIGHT_COLOR}, {'offset': (0.125, 0.125), 'color': 'orange'}]}],
    'condapackages':           [('fa.archive',), {'color': MAIN_LIGHT_COLOR}],
    'spyder.example':          [('fa.eye',), {'color': MAIN_LIGHT_COLOR}],
    'spyder.autopep8':         [('fa.eye',), {'color': MAIN_LIGHT_COLOR}],
    'spyder.memory_profiler':  [('fa.eye',), {'color': MAIN_LIGHT_COLOR}],
    'spyder.line_profiler':    [('fa.eye',), {'color': MAIN_LIGHT_COLOR}],
    'symbol_find':             [('fa.at',), {'color': MAIN_LIGHT_COLOR}],
    'folding.arrow_right_off': [('fa.caret-right',), {'color': 'gray'}],
    'folding.arrow_right_on':  [('fa.caret-right',), {'color': MAIN_LIGHT_COLOR}],
    'folding.arrow_down_off':  [('fa.caret-down',), {'color': 'gray'}],
    'folding.arrow_down_on':   [('fa.caret-down',), {'color': MAIN_LIGHT_COLOR}],
    'lspserver':               [('fa.server',), {'color': MAIN_LIGHT_COLOR}],
    'dependency_ok':           [('fa.check',), {'color': MAIN_LIGHT_COLOR}],
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
    theme = CONF.get('main', 'icon_theme')
    color_theme = CONF.get('color_schemes', 'color_theme')
    color_scheme = CONF.get('color_schemes', 'selected')
    if theme == 'spyder 3':
        if not _resource['loaded']:
            qta.load_font('spyder', 'spyder.ttf', 'spyder-charmap.json',
                          directory=_resource['directory'])
            _resource['loaded'] = True
        if color_theme == 'dark':
            args, kwargs = _qtaargsdark[name]
        elif color_theme == 'automatic':
            color_scheme = get_color_scheme(color_scheme)
            fon_c, fon_fw, fon_fs = color_scheme['normal']
            font_color = fon_c
            if not dark_color(font_color):
                args, kwargs = _qtaargsdark[name]
            else:
                args, kwargs = _qtaargs[name]
        else:
            args, kwargs = _qtaargs[name]
        return qta.icon(*args, **kwargs)
    elif theme == 'spyder 2':
        icon = get_icon(name + '.png', resample=resample)
        if icon_path:
            icon_path = osp.join(icon_path, name + '.png')
            if osp.isfile(icon_path):
                icon = QIcon(icon_path)
        return icon if icon is not None else QIcon()
