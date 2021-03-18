# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os
import os.path as osp
import mimetypes as mime
import sys

# Third party imports
from qtpy.QtCore import QBuffer, QByteArray, Qt
from qtpy.QtGui import QIcon, QImage, QPixmap
from qtpy.QtWidgets import QStyle, QWidget

# Local imports
from spyder.config.manager import CONF
from spyder.config.gui import is_dark_interface
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.encoding import is_text_file
import qtawesome as qta


class IconManager():
    """Class that manages all the icons."""
    def __init__(self):
        self.MAIN_FG_COLOR = 'white' if is_dark_interface() else 'black'
        self.BIN_FILES = {x: 'ArchiveFileIcon' for x in [
            'zip', 'x-tar', 'x-7z-compressed', 'rar']}

        self.DOCUMENT_FILES = {
            'vnd.ms-powerpoint': 'PowerpointFileIcon',
            'vnd.openxmlformats-officedocument.'
            'presentationml.presentation': 'PowerpointFileIcon',
            'msword': 'WordFileIcon',
            'vnd.openxmlformats-officedocument.'
            'wordprocessingml.document': 'WordFileIcon',
            'vnd.ms-excel': 'ExcelFileIcon',
            'vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet': 'ExcelFileIcon',
            'pdf': 'PDFIcon'}

        self.OFFICE_FILES = {
            '.xlsx': 'ExcelFileIcon',
            '.docx': 'WordFileIcon',
            '.pptx': 'PowerpointFileIcon'}

        self.ICONS_BY_EXTENSION = {}

        # Magnification factors for attribute icons
        # per platform
        if sys.platform.startswith('linux'):
            self.BIG_ATTR_FACTOR = 1.0
            self.SMALL_ATTR_FACTOR = 0.9
        elif os.name == 'nt':
            self.BIG_ATTR_FACTOR = 1.1
            self.SMALL_ATTR_FACTOR = 1.0
        else:
            self.BIG_ATTR_FACTOR = 1.3
            self.SMALL_ATTR_FACTOR = 1.1

        # Icons for different programming language
        # extensions
        self.LANGUAGE_ICONS = {
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

        self._resource = {
            'directory': osp.join(
                osp.dirname(osp.realpath(__file__)), '../fonts'),
            'loaded': False,
        }

        self._qtaargs = {
            'environment':             [('mdi.cube-outline',), {'color': self.MAIN_FG_COLOR}],
            'drag-horizontal':         [('mdi.drag-horizontal',), {'color': self.MAIN_FG_COLOR}],
            'format_letter_case':      [('mdi.format-letter-case',), {'color': self.MAIN_FG_COLOR}],
            'regex':                   [('mdi.regex',), {'color': self.MAIN_FG_COLOR}],
            'log':                     [('fa.file-text-o',), {'color': self.MAIN_FG_COLOR}],
            'configure':               [('fa.wrench',), {'color': self.MAIN_FG_COLOR}],
            'bold':                    [('fa.bold',), {'color': self.MAIN_FG_COLOR}],
            'italic':                  [('fa.italic',), {'color': self.MAIN_FG_COLOR}],
            'genprefs':                [('fa.cogs',), {'color': self.MAIN_FG_COLOR}],
            'run_small':               [('fa.play',), {'color': 'green'}],
            'stop':                    [('fa.stop',), {'color': 'darkred'}],
            'syspath':                 [('fa.cogs',), {'color': self.MAIN_FG_COLOR}],
            'keyboard':                [('fa.keyboard-o',), {'color': self.MAIN_FG_COLOR}],
            'eyedropper':              [('fa.eyedropper',), {'color': self.MAIN_FG_COLOR}],
            'tooloptions':             [('fa.bars',), {'color': self.MAIN_FG_COLOR}],
            'filenew':                 [('fa.file-o',), {'color': self.MAIN_FG_COLOR}],
            'fileopen':                [('fa.folder-open',), {'color': self.MAIN_FG_COLOR}],
            'revert':                  [('fa.undo',), {'color': self.MAIN_FG_COLOR}],
            'filesave':                [('fa.save',), {'color': self.MAIN_FG_COLOR}],
            'save_all':                [('fa.save', 'fa.save'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': self.MAIN_FG_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': self.MAIN_FG_COLOR}]}],
            'filesaveas':              [('fa.save', 'fa.pencil'), {'options': [{'offset': (-0.2, -0.2), 'scale_factor': 0.6, 'color': self.MAIN_FG_COLOR}, {'offset': (0.2, 0.2), 'scale_factor': 0.6, 'color': self.MAIN_FG_COLOR}]}],
            'print':                   [('fa.print',), {'color': self.MAIN_FG_COLOR}],
            'fileclose':               [('fa.close',), {'color': self.MAIN_FG_COLOR}],
            'filecloseall':            [('fa.close', 'fa.close', 'fa.close'), {'options': [{'scale_factor': 0.6, 'offset': (0.3, -0.3), 'color': self.MAIN_FG_COLOR},  {'scale_factor': 0.6, 'offset': (-0.3, -0.3), 'color': self.MAIN_FG_COLOR}, {'scale_factor': 0.6, 'offset': (0.3, 0.3), 'color': self.MAIN_FG_COLOR}]}],
            'breakpoint_transparent':  [('fa.circle',), {'color': 'darkred', 'opacity': 0.75, 'scale_factor': 0.9}],
            'breakpoint_big':          [('fa.circle',), {'color': '#cc0000', 'scale_factor': 0.9} ],
            'breakpoint_cond_big':     [('fa.question-circle',), {'color': '#cc0000', 'scale_factor': 0.9},],
            'breakpoints':             [('mdi.dots-vertical',), {'color': self.MAIN_FG_COLOR}],
            'arrow_debugger':          [('mdi.arrow-right-bold',), {'color': '#3775a9', 'scale_factor': 2.0}],
            'debug':                   [('spyder.debug',), {'color': '#3775a9'}],
            'arrow-step-over':         [('spyder.step-forward',), {'color': '#3775a9'}],
            'arrow-continue':          [('spyder.continue',), {'color': '#3775a9'}],
            'arrow-step-in':           [('spyder.step-into',), {'color': '#3775a9'}],
            'arrow-step-out':          [('spyder.step-out',), {'color': '#3775a9'}],
            'stop_debug':              [('fa.stop',), {'color': '#3775a9'}],
            'run':                     [('fa.play',), {'color': 'green'}],
            'run_settings':            [('fa.wrench', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': self.MAIN_FG_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
            'run_again':               [('fa.repeat', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': self.MAIN_FG_COLOR}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
            'run_selection':           [('spyder.run-selection',), {'color': self.MAIN_FG_COLOR}],
            'run_cell':                [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                        {'options': [{'color': '#fff683'}, {'color': self.MAIN_FG_COLOR}, {'color': 'green'}]}],
            'debug_cell':              [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                        {'options': [{'color': '#fff683'}, {'color': self.MAIN_FG_COLOR}, {'color': '#3775a9'}]}],
            'run_cell_advance':        [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play', 'spyder.cell-next'),
                                        {'options': [{'color': '#fff683'}, {'color': self.MAIN_FG_COLOR,}, {'color': 'green'}, {'color': 'red'}]}],
            'todo_list':               [('fa.th-list', 'fa.check'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'color': '#3775a9', 'color_disabled': '#748fa6'}]}],
            'wng_list':                [('fa.th-list', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
            'prev_wng':                [('fa.arrow-left', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
            'next_wng':                [('fa.arrow-right', 'fa.warning'), {'options': [{'color': '#999999'}, {'offset': (0.0, 0.2), 'scale_factor': 0.75, 'color': 'orange', 'color_disabled': '#face7e'}]}],
            'last_edit_location':      [('fa.caret-up',), {'color': self.MAIN_FG_COLOR}],
            'prev_cursor':             [('fa.hand-o-left',), {'color': self.MAIN_FG_COLOR}],
            'next_cursor':             [('fa.hand-o-right',), {'color': self.MAIN_FG_COLOR}],
            'comment':                 [('fa.comment',), {'color': self.MAIN_FG_COLOR}],
            'indent':                  [('fa.indent',), {'color': self.MAIN_FG_COLOR}],
            'unindent':                [('fa.outdent',), {'color': self.MAIN_FG_COLOR}],
            'toggle_lowercase':        [('mdi.format-letter-case-lower',), {'color': self.MAIN_FG_COLOR}],
            'toggle_uppercase':        [('mdi.format-letter-case-upper',), {'color': self.MAIN_FG_COLOR}],
            'gotoline':                [('fa.sort-numeric-asc',), {'color': self.MAIN_FG_COLOR}],
            'error':                   [('fa.times-circle',), {'color': 'darkred'}],
            'warning':                 [('fa.warning',), {'color': 'orange'}],
            'information':             [('fa.info-circle',), {'color': '#3775a9'}],
            'hint':                    [('fa.lightbulb-o',), {'color': 'yellow'}],
            'todo':                    [('fa.exclamation',), {'color': '#3775a9'}],
            'ipython_console':         [('mdi.console',), {'color': self.MAIN_FG_COLOR}],
            'python':                  [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
            'pythonpath':              [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': '#3775a9'}, {'color': '#ffd444'}]}],
            'findf':                   [('fa.file-o', 'fa.search'), {'options': [{'scale_factor': 1.0, 'color': self.MAIN_FG_COLOR}, {'scale_factor': 0.6, 'color': self.MAIN_FG_COLOR}]}],
            'history':                 [('fa.history',), {'color': self.MAIN_FG_COLOR}],
            'help':                    [('fa.question-circle',), {'color': self.MAIN_FG_COLOR}],
            'lock':                    [('fa.lock',), {'color': self.MAIN_FG_COLOR}],
            'lock_open':               [('fa.unlock-alt',), {'color': self.MAIN_FG_COLOR}],
            'outline_explorer':        [('spyder.treeview',), {'color': self.MAIN_FG_COLOR}],
            'dictedit':                [('fa.th-list',), {'color': self.MAIN_FG_COLOR}],
            'previous':                [('fa.arrow-left',), {'color': self.MAIN_FG_COLOR}],
            'next':                    [('fa.arrow-right',), {'color': self.MAIN_FG_COLOR}],
            'up':                      [('fa.arrow-up',), {'color': self.MAIN_FG_COLOR}],
            'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': '#414141'}, {'color': '#fafafa'}, {'color': '#ee0000'}]}],
            'find':                    [('fa.search',), {'color': self.MAIN_FG_COLOR}],
            'findnext':                [('fa.search', 'fa.long-arrow-down'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': self.MAIN_FG_COLOR}, {'offset': (-0.3, 0.0), 'color': self.MAIN_FG_COLOR}]}],
            'findprevious':            [('fa.search', 'fa.long-arrow-up'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': self.MAIN_FG_COLOR}, {'offset': (-0.3, 0.0), 'color': self.MAIN_FG_COLOR}]}],
            'replace':                 [('fa.exchange',), {'color': self.MAIN_FG_COLOR}],
            'undo':                    [('fa.undo',), {'color': self.MAIN_FG_COLOR}],
            'redo':                    [('fa.repeat',), {'color': self.MAIN_FG_COLOR}],
            'refresh':                 [('mdi.refresh',), {'color': self.MAIN_FG_COLOR}],
            'restart':                 [('fa.repeat',), {'color': self.MAIN_FG_COLOR}],
            'editcopy':                [('fa.copy',), {'color': self.MAIN_FG_COLOR}],
            'editcut':                 [('fa.scissors',), {'color': self.MAIN_FG_COLOR}],
            'editdelete':              [('fa.eraser',), {'color': self.MAIN_FG_COLOR}],
            'editclear':               [('fa.times',), {'color': self.MAIN_FG_COLOR}],
            'selectall':               [('spyder.text-select-all',), {'color': self.MAIN_FG_COLOR}],
            'exit':                    [('fa.power-off',), {'color': 'darkred'}],
            'advanced':                [('fa.gear',), {'color': self.MAIN_FG_COLOR}],
            'bug':                     [('fa.bug',), {'color': self.MAIN_FG_COLOR}],
            'maximize':                [('spyder.maximize-pane',), {'color': self.MAIN_FG_COLOR}],
            'unmaximize':              [('spyder.minimize-pane',), {'color': self.MAIN_FG_COLOR}],
            'window_nofullscreen':     [('mdi.arrow-collapse-all',), {'color': self.MAIN_FG_COLOR}],
            'window_fullscreen':       [('mdi.arrow-expand-all',), {'color': self.MAIN_FG_COLOR}],
            'MessageBoxWarning':       [('fa.warning',), {'color': self.MAIN_FG_COLOR}],
            'arredit':                 [('fa.table',), {'color': self.MAIN_FG_COLOR}],
            'zoom_out':                [('fa.search-minus',), {'color': self.MAIN_FG_COLOR}],
            'zoom_in':                 [('fa.search-plus',), {'color': self.MAIN_FG_COLOR}],
            'home':                    [('fa.home',), {'color': self.MAIN_FG_COLOR}],
            'plot':                    [('fa.line-chart',), {'color': self.MAIN_FG_COLOR}],
            'hist':                    [('fa.bar-chart',), {'color': self.MAIN_FG_COLOR}],
            'imshow':                  [('fa.image',), {'color': self.MAIN_FG_COLOR}],
            'insert':                  [('fa.sign-in',), {'color': self.MAIN_FG_COLOR}],
            'rename':                  [('fa.pencil',), {'color': self.MAIN_FG_COLOR}],
            'edit_add':                [('fa.plus',), {'color': self.MAIN_FG_COLOR}],
            'edit_remove':             [('fa.minus',), {'color': self.MAIN_FG_COLOR}],
            'browse_tab':              [('mdi.tab',), {'color': self.MAIN_FG_COLOR}],
            'filelist':                [('fa.list',), {'color': self.MAIN_FG_COLOR}],
            'newwindow':               [('spyder.window',), {'color': self.MAIN_FG_COLOR}],
            'versplit':                [('spyder.rows',), {'color': self.MAIN_FG_COLOR}],
            'horsplit':                [('fa.columns',), {'color': self.MAIN_FG_COLOR}],
            'close_panel':             [('fa.close',), {'color': self.MAIN_FG_COLOR}],
            'fromcursor':              [('fa.hand-o-right',), {'color': self.MAIN_FG_COLOR}],
            'filter':                  [('fa.filter',), {'color': self.MAIN_FG_COLOR}],
            'folder_new':              [('fa.folder-o', 'fa.plus'), {'options': [{'color': self.MAIN_FG_COLOR}, {'scale_factor': 0.5, 'offset': (0.0, 0.1), 'color': self.MAIN_FG_COLOR}]}],
            'package_new':             [('fa.folder-o', 'spyder.python-logo'), {'options': [{'offset': (0.0, -0.125), 'color': self.MAIN_FG_COLOR}, {'offset': (0.0, 0.125), 'color': self.MAIN_FG_COLOR}]}],
            'vcs_commit':              [('fa.check',), {'color': 'green'}],
            'vcs_browse':              [('fa.search',), {'color': 'green'}],
            'kill':                    [('fa.warning',), {'color': self.MAIN_FG_COLOR}],
            'fileimport':              [('fa.download',), {'color': self.MAIN_FG_COLOR}],
            'environ':                 [('fa.th-list',), {'color': self.MAIN_FG_COLOR}],
            'options_less':            [('fa.minus-square',), {'color': self.MAIN_FG_COLOR}],
            'options_more':            [('fa.plus-square',), {'color': self.MAIN_FG_COLOR}],
            'ArrowDown':               [('fa.arrow-circle-down',), {'color': self.MAIN_FG_COLOR}],
            'ArrowUp':                 [('fa.arrow-circle-up',), {'color': self.MAIN_FG_COLOR}],
            'ArrowBack':               [('fa.arrow-circle-left',), {'color': self.MAIN_FG_COLOR}],
            'ArrowForward':            [('fa.arrow-circle-right',), {'color': self.MAIN_FG_COLOR}],
            'DialogApplyButton':       [('fa.check',), {'color': self.MAIN_FG_COLOR}],
            'DialogCloseButton':       [('fa.close',), {'color': self.MAIN_FG_COLOR}],
            'DirClosedIcon':           [('fa.folder-o',), {'color': self.MAIN_FG_COLOR}],
            'DialogHelpButton':        [('fa.life-ring',), {'color': 'darkred'}],
            'VideoIcon':               [('fa5s.video',), {'color': self.MAIN_FG_COLOR}],
            'MessageBoxInformation':   [('fa.info',), {'color': self.MAIN_FG_COLOR}],
            'DirOpenIcon':             [('fa.folder-open',), {'color': self.MAIN_FG_COLOR}],
            'FileIcon':                [('fa.file-o',), {'color': self.MAIN_FG_COLOR}],
            'ExcelFileIcon':           [('fa.file-excel-o',), {'color': self.MAIN_FG_COLOR}],
            'WordFileIcon':            [('fa.file-word-o',), {'color': self.MAIN_FG_COLOR}],
            'PowerpointFileIcon':      [('fa.file-powerpoint-o',), {'color': self.MAIN_FG_COLOR}],
            'PDFIcon':                 [('fa.file-pdf-o',), {'color': self.MAIN_FG_COLOR}],
            'AudioFileIcon':           [('fa.file-audio-o',), {'color': self.MAIN_FG_COLOR}],
            'ImageFileIcon':           [('fa.file-image-o',), {'color': self.MAIN_FG_COLOR}],
            'ArchiveFileIcon':         [('fa.file-archive-o',), {'color': self.MAIN_FG_COLOR}],
            'VideoFileIcon':           [('fa.file-video-o',), {'color': self.MAIN_FG_COLOR}],
            'TextFileIcon':            [('fa.file-text-o',), {'color': self.MAIN_FG_COLOR}],
            'CFileIcon':               [('mdi.language-c',), {'color': self.MAIN_FG_COLOR}],
            'CppFileIcon':             [('mdi.language-cpp',), {'color': self.MAIN_FG_COLOR}],
            'CsharpFileIcon':          [('mdi.language-csharp',), {'color': self.MAIN_FG_COLOR}],
            'PythonFileIcon':          [('mdi.language-python',), {'color': self.MAIN_FG_COLOR}],
            'JavaFileIcon':            [('mdi.language-java',), {'color': self.MAIN_FG_COLOR}],
            'JavascriptFileIcon':      [('mdi.language-javascript',), {'color': self.MAIN_FG_COLOR}],
            'RFileIcon':               [('mdi.language-r',), {'color': self.MAIN_FG_COLOR}],
            'SwiftFileIcon':           [('mdi.language-swift',), {'color': self.MAIN_FG_COLOR}],
            'GridFileIcon':            [('mdi.grid',), {'color': self.MAIN_FG_COLOR}],
            'WindowsFileIcon':         [('mdi.windows',), {'color': self.MAIN_FG_COLOR}],
            'PowershellFileIcon':      [('mdi.powershell',), {'color': self.MAIN_FG_COLOR}],
            'DollarFileIcon':          [('fa5s.file-invoice-dollar',), {'color': self.MAIN_FG_COLOR}],
            'MarkdownFileIcon':        [('mdi.markdown',), {'color': self.MAIN_FG_COLOR}],
            'JsonFileIcon':            [('mdi.json',), {'color': self.MAIN_FG_COLOR}],
            'ExclamationFileIcon':     [('mdi.exclamation',), {'color': self.MAIN_FG_COLOR}],
            'CodeFileIcon':             [('mdi.xml',), {'color': self.MAIN_FG_COLOR}],
            'project':                 [('fa.folder-open-o',), {'color': self.MAIN_FG_COLOR}],
            'DriveHDIcon':             [('fa.hdd-o',), {'color': self.MAIN_FG_COLOR}],
            'arrow':                   [('fa.arrow-right',), {'color': self.MAIN_FG_COLOR}],
            'collapse':                [('mdi.collapse-all',), {'color': self.MAIN_FG_COLOR}],
            'expand':                  [('mdi.expand-all',), {'color': self.MAIN_FG_COLOR}],
            'restore':                 [('fa.level-up',), {'color': self.MAIN_FG_COLOR}],
            'collapse_selection':      [('fa.minus-square-o',), {'color': self.MAIN_FG_COLOR}],
            'expand_selection':        [('fa.plus-square-o',), {'color': self.MAIN_FG_COLOR}],
            'copywop':                 [('fa.terminal',), {'color': self.MAIN_FG_COLOR}],
            'editpaste':               [('fa.paste',), {'color': self.MAIN_FG_COLOR}],
            'edit':                    [('fa.edit',), {'color': self.MAIN_FG_COLOR}],
            'convention':              [('mdi.alpha-c-box',), {'color': '#3775a9', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'refactor':                [('mdi.alpha-r-box',), {'color': '#3775a9', 'scale_factor': self.BIG_ATTR_FACTOR}],
            '2uparrow':                [('fa.angle-double-up',), {'color': self.MAIN_FG_COLOR}],
            '1uparrow':                [('fa.angle-up',), {'color': self.MAIN_FG_COLOR}],
            '2downarrow':              [('fa.angle-double-down',), {'color': self.MAIN_FG_COLOR}],
            '1downarrow':              [('fa.angle-down',), {'color': self.MAIN_FG_COLOR}],
            'undock':                  [('fa.external-link',), {'color': self.MAIN_FG_COLOR}],
            'dock':                    [('fa.caret-square-o-down',), {'color': self.MAIN_FG_COLOR}],
            'close_pane':              [('fa.window-close-o',), {'color': self.MAIN_FG_COLOR}],
            # --- Autocompletion/document symbol type icons --------------
            'keyword':                 [('mdi.alpha-k-box',), {'color': '#df2935', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'color':                   [('mdi.alpha-c-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'enum':                    [('mdi.alpha-e-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'value':                   [('mdi.alpha-v-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'constant':                [('mdi.alpha-c-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'unit':                    [('mdi.alpha-u-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'text':                    [('mdi.alpha-t-box',), {'color': 'gray', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'file':                    [('mdi.alpha-f-box',), {'color': 'gray', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'snippet':                 [('mdi.alpha-s-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'attribute':               [('mdi.alpha-a-box',), {'color': 'magenta', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'reference':               [('mdi.alpha-r-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'variable':                [('mdi.alpha-v-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'field':                   [('mdi.alpha-a-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'property':                [('mdi.alpha-p-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'module':                  [('mdi.alpha-m-box',), {'color': '#daa520', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'namespace':               [('mdi.alpha-n-box',), {'color': '#daa520', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'package':                 [('mdi.alpha-p-box',), {'color': '#daa520', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'class':                   [('mdi.alpha-c-box',), {'color':'#3775a9', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'interface':               [('mdi.alpha-i-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'string':                  [('mdi.alpha-s-box',), {'color': '#df2935', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'number':                  [('mdi.alpha-n-box',), {'color': '#df2935', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'boolean':                 [('mdi.alpha-b-box',), {'color': 'magenta', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'array':                   [('mdi.alpha-a-box',), {'color': '#df2935', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'object':                  [('mdi.alpha-o-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'key':                     [('mdi.alpha-k-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'class':                   [('mdi.alpha-c-box',), {'color':'#3775a9', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'null':                    [('mdi.alpha-n-box',), {'color': 'magenta', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'enum_member':             [('mdi.alpha-e-box',), {'color': '#e69c9c', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'struct':                  [('mdi.alpha-s-box',), {'color':'#3775a9', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'event':                   [('mdi.alpha-e-box',), {'color':'orange', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'operator':                [('mdi.alpha-o-box',), {'color':'orange', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'type_parameter':          [('mdi.alpha-t-box',), {'color':'orange', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'private2':                [('spyder.circle-underscore',), {'color':'#e69c9c', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'private1':                [('spyder.circle-underscore',), {'color':'#e69c9c', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'method':                  [('mdi.alpha-m-box',), {'color':'#7ea67e', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'constructor':             [('mdi.alpha-c-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'function':                [('mdi.alpha-f-box',), {'color':'orange', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'blockcomment':            [('fa5s.hashtag',), {'color':'grey', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'cell':                    [('mdi.percent',), {'color':'red', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'no_match':                [('fa.circle',), {'color': 'gray', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'github':                  [('fa.github',), {'color': self.MAIN_FG_COLOR}],
            # --- Spyder Tour --------------------------------------------------------
            'tour.close':              [('fa.close',), {'color': self.MAIN_FG_COLOR}],
            'tour.home':               [('fa.fast-backward',), {'color': self.MAIN_FG_COLOR}],
            'tour.previous':           [('fa.backward',), {'color': self.MAIN_FG_COLOR}],
            'tour.next':               [('fa.forward',), {'color': self.MAIN_FG_COLOR}],
            'tour.end':                [('fa.fast-forward',), {'color': self.MAIN_FG_COLOR}],
            # --- Third party plugins ------------------------------------------------
            'profiler':                [('fa.clock-o',), {'color': self.MAIN_FG_COLOR}],
            'pylint':                  [('fa.search', 'fa.check'), {'options': [{'color': self.MAIN_FG_COLOR}, {'offset': (0.125, 0.125), 'color': 'orange'}]}],
            'condapackages':           [('fa.archive',), {'color': self.MAIN_FG_COLOR}],
            'spyder.example':          [('fa.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.autopep8':         [('fa.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.memory_profiler':  [('fa.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.line_profiler':    [('fa.eye',), {'color': self.MAIN_FG_COLOR}],
            'symbol_find':             [('fa.at',), {'color': self.MAIN_FG_COLOR}],
            'folding.arrow_right_off': [('fa.caret-right',), {'color': 'gray'}],
            'folding.arrow_right_on':  [('fa.caret-right',), {'color': self.MAIN_FG_COLOR}],
            'folding.arrow_down_off':  [('fa.caret-down',), {'color': 'gray'}],
            'folding.arrow_down_on':   [('fa.caret-down',), {'color': self.MAIN_FG_COLOR}],
            'lspserver':               [('mdi.code-tags-check',), {'color': self.MAIN_FG_COLOR}],
            'dependency_ok':           [('fa.check',), {'color': self.MAIN_FG_COLOR}],
            'dependency_warning':      [('fa.warning',), {'color': 'orange'}],
            'dependency_error':        [('fa.warning',), {'color': 'darkred'}],
            'broken_image':            [('mdi.image-broken-variant',), {'color': self.MAIN_FG_COLOR}],
            # --- Status bar --------------------------------------------------------
            'code_fork':               [('fa.code-fork',), {'color': self.MAIN_FG_COLOR}],
            'statusbar':               [('mdi.dock-bottom',), {'color': self.MAIN_FG_COLOR}],
        }

    def get_std_icon(self, name, size=None):
        """Get standard platform icon
        Call 'show_std_icons()' for details"""
        if not name.startswith('SP_'):
            name = 'SP_' + name
        icon = QWidget().style().standardIcon(getattr(QStyle, name))
        if size is None:
            return icon
        else:
            return QIcon(icon.pixmap(size, size))

    def get_icon(self, name, resample=False):
        """Return image inside a QIcon object.

        default: default image name or icon
        resample: if True, manually resample icon pixmaps for usual sizes
        (16, 24, 32, 48, 96, 128, 256). This is recommended for QMainWindow icons
        created from SVG images on non-Windows platforms due to a Qt bug.
        See spyder-ide/spyder#1314.
        """
        icon_path = get_image_path(name)
        icon = QIcon(icon_path)
        if resample:
            icon0 = QIcon()
            for size in (16, 24, 32, 48, 96, 128, 256, 512):
                icon0.addPixmap(icon.pixmap(size, size))
            return icon0
        else:
            return icon

    def icon(self, name, scale_factor=None, resample=False):
        theme = CONF.get('appearance', 'icon_theme')
        if theme == 'spyder 3':
            try:
                # Try to load the icons from QtAwesome
                if not self._resource['loaded']:
                    qta.load_font('spyder', 'spyder.ttf', 'spyder-charmap.json',
                                directory=self._resource['directory'])
                    self._resource['loaded'] = True
                args, kwargs = self._qtaargs[name]
                if scale_factor is not None:
                    kwargs['scale_factor'] = scale_factor
                return qta.icon(*args, **kwargs)
            except KeyError:
                # Load custom icons
                icon = QIcon(self.get_icon(name))
                return icon if icon is not None else QIcon()
        elif theme == 'spyder 2':
            icon = get_icon(name, resample=resample)
            return icon if icon is not None else QIcon()

    def get_icon_by_extension_or_type(self, fname, scale_factor):
        """Return the icon depending on the file extension"""
        application_icons = {}
        application_icons.update(self.BIN_FILES)
        application_icons.update(self.DOCUMENT_FILES)

        basename = osp.basename(fname)
        __, extension = osp.splitext(basename.lower())
        mime_type, __ = mime.guess_type(basename)

        if osp.isdir(fname):
            extension = "Folder"

        if (extension, scale_factor) in self.ICONS_BY_EXTENSION:
            return self.ICONS_BY_EXTENSION[(extension, scale_factor)]

        if osp.isdir(fname):
            icon_by_extension = self.icon('DirOpenIcon', scale_factor)
        else:
            icon_by_extension = self.icon('binary')

            if extension in self.OFFICE_FILES:
                icon_by_extension = self.icon(
                    self.OFFICE_FILES[extension], scale_factor)

            elif extension in self.LANGUAGE_ICONS:
                icon_by_extension = self.icon(
                    self.LANGUAGE_ICONS[extension], scale_factor)
            else:
                if extension == '.ipynb':
                    icon_by_extension = self.icon('notebook')
                elif extension == '.tex':
                    icon_by_extension = self.icon('file_type_tex')
                elif is_text_file(fname):
                    icon_by_extension = self.icon('TextFileIcon', scale_factor)
                elif mime_type is not None:
                    try:
                        # Fix for spyder-ide/spyder#5080. Even though
                        # mimetypes.guess_type documentation states that
                        # the return value will be None or a tuple of
                        # the form type/subtype, in the Windows registry,
                        # .sql has a mimetype of text\plain
                        # instead of text/plain therefore mimetypes is
                        # returning it incorrectly.
                        file_type, bin_name = mime_type.split('/')
                    except ValueError:
                        file_type = None
                    if file_type is None:
                        icon_by_extension = self.icon('binary')
                    elif file_type == 'audio':
                        icon_by_extension = self.icon(
                            'AudioFileIcon', scale_factor)
                    elif file_type == 'video':
                        icon_by_extension = self.icon(
                            'VideoFileIcon', scale_factor)
                    elif file_type == 'image':
                        icon_by_extension = self.icon(
                            'ImageFileIcon', scale_factor)
                    elif file_type == 'application':
                        if bin_name in application_icons:
                            icon_by_extension = self.icon(
                                application_icons[bin_name], scale_factor)

        self.ICONS_BY_EXTENSION[(extension, scale_factor)] = icon_by_extension
        return icon_by_extension

    def base64_from_icon(self, icon_name, width, height):
        """Convert icon to base64 encoding."""
        icon_obj = self.icon(icon_name)
        return base64_from_icon_obj(icon_obj, width, height)

    def base64_from_icon_obj(self, icon_obj, width, height):
        """Convert icon object to base64 encoding."""
        image = QImage(icon_obj.pixmap(width, height).toImage())
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        image.save(buffer, "PNG")
        return byte_array.toBase64().data().decode()


ima = IconManager()


# -----------------------------------------------------------------------------
# TODO: Remove the following code once external plugins have been updated to
# the new icon manager.
# -----------------------------------------------------------------------------
def get_std_icon(name, size=None):
    return ima.get_std_icon(name, size=size)


def get_icon(name, resample=False):
    return ima.get_icon(name, resample=resample)


def icon(name, scale_factor=None, resample=False):
    return ima.icon(name, scale_factor=scale_factor, resample=resample)


def get_icon_by_extension_or_type(fname, scale_factor):
    return ima.get_icon_by_extension_or_type(fname, scale_factor)


def base64_from_icon(icon_name, width, height):
    return ima.base64_from_icon(icon_name, width, height)


def base64_from_icon_obj(icon_obj, width, height):
    return ima.base64_from_icon_obj(icon_obj, width, height)


MAIN_FG_COLOR = ima.MAIN_FG_COLOR
