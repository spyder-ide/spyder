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
            'environment':             [('mdi.cube-outline',), {'color': self.COLOR_ICON_1}],
            'drag-horizontal':         [('mdi.drag-horizontal',), {'color': self.COLOR_ICON_1}],
            'format_letter_case':      [('mdi.format-letter-case',), {'color': self.COLOR_ICON_1}],
            'regex':                   [('mdi.regex',), {'color': self.COLOR_ICON_1}],
            'log':                     [('mdi.file-document',), {'color': self.COLOR_ICON_1}],
            'configure':               [('mdi.wrench',), {'color': self.COLOR_ICON_1}],
            'bold':                    [('mdi.format-bold',), {'color': self.COLOR_ICON_1}],
            'italic':                  [('mdi.format-italic',), {'color': self.COLOR_ICON_1}],
            'genprefs':                [('fa.cogs',), {'color': self.COLOR_ICON_1}],
            'run_small':               [('mdi.play',), {'color': self.COLOR_ICON_3}],
            'stop':                    [('mdi.stop',), {'color': self.COLOR_ICON_1}],
            'syspath':                 [('fa.cogs',), {'color': self.COLOR_ICON_1}],
            'keyboard':                [('mdi.keyboard',), {'color': self.COLOR_ICON_1}],
            'eyedropper':              [('mdi.eyedropper',), {'color': self.COLOR_ICON_1}],
            'tooloptions':             [('mdi.menu',), {'color': self.COLOR_ICON_1}],
            'filenew':                 [('mdi.file',), {'color': self.COLOR_ICON_1}],
            'fileopen':                [('mdi.folder-open',), {'color': self.COLOR_ICON_1}],
            'revert':                  [('mdi.undo',), {'color': self.COLOR_ICON_1}],
            'filesave':                [('mdi.content-save',), {'color': self.COLOR_ICON_1}],
            'save_all':                [('mdi.content-save-all',), {'color': self.COLOR_ICON_1}],
            'filesaveas':              [('mdi.content-save-edit',), {'color': self.COLOR_ICON_1}],
            'print':                   [('mdi.printer',), {'color': self.COLOR_ICON_1}],
            'fileclose':               [('mdi.close',), {'color': self.COLOR_ICON_1}],
            'filecloseall':            [('mdi.close', 'fa.close', 'fa.close'), {'options': [{'scale_factor': 0.6, 'offset': (0.3, -0.3), 'color': self.COLOR_ICON_1},  {'scale_factor': 0.6, 'offset': (-0.3, -0.3), 'color': self.COLOR_ICON_1}, {'scale_factor': 0.6, 'offset': (0.3, 0.3), 'color': self.COLOR_ICON_1}]}],
            'breakpoint_transparent':  [('mdi.checkbox-blank-circle',), {'color': self.COLOR_ICON_4, 'opacity': 0.75, 'scale_factor': 0.9}],
            'breakpoint_big':          [('mdi.checkbox-blank-circle',), {'color': self.COLOR_ICON_4, 'scale_factor': 0.9} ],
            'breakpoint_cond_big':     [('mdi.help-circle',), {'color': self.COLOR_ICON_4, 'scale_factor': 0.9},],
            'breakpoints':             [('mdi.dots-vertical',), {'color': self.COLOR_ICON_1}],
            'arrow_debugger':          [('mdi.arrow-right-bold',), {'color': self.COLOR_ICON_2, 'scale_factor': 2.0}],
            'debug':                   [('mdi.step-forward',), {'color': self.COLOR_ICON_2}],
            'arrow-step-over':         [('mdi.debug-step-over',), {'color': self.COLOR_ICON_2}],
            'arrow-continue':          [('mdi.fast-forward',), {'color': self.COLOR_ICON_2}],
            'arrow-step-in':           [('mdi.debug-step-into',), {'color': self.COLOR_ICON_2}],
            'arrow-step-out':          [('mdi.debug-step-out',), {'color': self.COLOR_ICON_2}],
            'stop_debug':              [('mdi.stop',), {'color': self.COLOR_ICON_2}],
            'run':                     [('mdi.play',), {'color': self.COLOR_ICON_3}],
            'run_settings':            [('fa.wrench', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': self.COLOR_ICON_1}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
            'run_again':               [('fa.repeat', 'fa.play'), {'options': [{'offset':(0.0, -0.1), 'color': self.COLOR_ICON_1}, {'offset': (0.2, 0.125), 'color': 'green', 'scale_factor': 0.8}]}],
            'run_selection':           [('spyder.run-selection',), {'color': self.COLOR_ICON_1}],
            'run_cell':                [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                        {'options': [{'color': '#fff683'}, {'color': self.COLOR_ICON_1}, {'color': 'green'}]}],
            'debug_cell':              [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play'),
                                        {'options': [{'color': '#fff683'}, {'color': self.COLOR_ICON_1}, {'color': self.COLOR_ICON_2}]}],
            'run_cell_advance':        [('spyder.cell-code', 'spyder.cell-border', 'spyder.cell-play', 'spyder.cell-next'),
                                        {'options': [{'color': '#fff683'}, {'color': self.COLOR_ICON_1,}, {'color': 'green'}, {'color': 'red'}]}],
            'todo_list':               [('mdi.check-bold',), {'color': self.COLOR_ICON_1}],
            'wng_list':                [('mdi.alert',), {'color': self.COLOR_ICON_5}],
            'prev_wng':                [('mdi.arrow-left',), {'color': self.COLOR_ICON_1}],
            'next_wng':                [('mdi.arrow-right',), {'color': self.COLOR_ICON_1}],
            'last_edit_location':      [('fa.caret-up',), {'color': self.COLOR_ICON_1}],
            'prev_cursor':             [('mdi.hand-pointing-left',), {'color': self.COLOR_ICON_1}],
            'next_cursor':             [('mdi.hand-pointing-right',), {'color': self.COLOR_ICON_1}],
            'comment':                 [('mdi.comment-text-outline',), {'color': self.COLOR_ICON_1}],
            'indent':                  [('mdi.format-indent-decrease',), {'color': self.COLOR_ICON_1}],
            'unindent':                [('mdi.format-indent-increase',), {'color': self.COLOR_ICON_1}],
            'toggle_lowercase':        [('mdi.format-letter-case-lower',), {'color': self.COLOR_ICON_1}],
            'toggle_uppercase':        [('mdi.format-letter-case-upper',), {'color': self.COLOR_ICON_1}],
            'gotoline':                [('mdi.format-line-spacing',), {'color': self.COLOR_ICON_1}],
            'error':                   [('mdi.close-circle',), {'color': self.COLOR_ICON_4}],
            'warning':                 [('mdi.alert',), {'color': self.COLOR_ICON_5}],
            'information':             [('mdi.information-outline',), {'color': self.COLOR_ICON_2}],
            'hint':                    [('mdi.lightbulb',), {'color': self.COLOR_ICON_2}],
            'todo':                    [('mdi.check-bold',), {'color': self.COLOR_ICON_2}],
            'ipython_console':         [('mdi.console',), {'color': self.COLOR_ICON_1}],
            'python':                  [('mdi.language-python',), {'color': self.COLOR_ICON_1}],
            'pythonpath':              [('mdi.language-python',), {'color': self.COLOR_ICON_1}],
            'findf':                   [('mdi.file-find'), {'color': self.COLOR_ICON_1}],
            'history':                 [('mdi.history',), {'color': self.COLOR_ICON_1}],
            'help':                    [('mdi.help-circle',), {'color': self.COLOR_ICON_1}],
            'lock':                    [('mdi.lock',), {'color': self.COLOR_ICON_1}],
            'lock_open':               [('mdi.lock-open',), {'color': self.COLOR_ICON_1}],
            'outline_explorer':        [('mdi.file-tree',), {'color': self.COLOR_ICON_1}],
            'dictedit':                [('mdi.view-list',), {'color': self.COLOR_ICON_1}],
            'previous':                [('mdi.arrow-left-bold',), {'color': self.COLOR_ICON_1}],
            'next':                    [('mdi.arrow-right-bold',), {'color': self.COLOR_ICON_1}],
            'up':                      [('mdi.arrow-up-bold',), {'color': self.COLOR_ICON_1}],
            'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': '#414141'}, {'color': '#fafafa'}, {'color': '#ee0000'}]}],
            'find':                    [('mdi.magnify',), {'color': self.COLOR_ICON_1}],
            'findnext':                [('fa.search', 'fa.long-arrow-down'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': self.COLOR_ICON_1}, {'offset': (-0.3, 0.0), 'color': self.COLOR_ICON_1}]}],
            'findprevious':            [('fa.search', 'fa.long-arrow-up'), {'options':[{'scale_factor': 0.6, 'offset': (0.3, 0.0), 'color': self.COLOR_ICON_1}, {'offset': (-0.3, 0.0), 'color': self.COLOR_ICON_1}]}],
            'replace':                 [('mdi.find-replace',), {'color': self.COLOR_ICON_1}],
            'undo':                    [('mdi.undo',), {'color': self.COLOR_ICON_1}],
            'redo':                    [('mdi.redo',), {'color': self.COLOR_ICON_1}],
            'refresh':                 [('mdi.refresh',), {'color': self.COLOR_ICON_1}],
            'restart':                 [('fa.reload',), {'color': self.COLOR_ICON_1}],
            'editcopy':                [('mdi.content-copy',), {'color': self.COLOR_ICON_1}],
            'editcut':                 [('mdi.content-cut',), {'color': self.COLOR_ICON_1}],
            'editdelete':              [('fa.eraser',), {'color': self.COLOR_ICON_1}],
            'editclear':               [('mdi.delete',), {'color': self.COLOR_ICON_1}],
            'selectall':               [('mdi.select-all',), {'color': self.COLOR_ICON_1}],
            'exit':                    [('mdi.power',), {'color': self.COLOR_ICON_4}],
            'advanced':                [('mdi.package-variant',), {'color': self.COLOR_ICON_1}],
            'bug':                     [('mdi.bug',), {'color': self.COLOR_ICON_1}],
            'maximize':                [('spyder.maximize-pane',), {'color': self.COLOR_ICON_1}],
            'window_nofullscreen':     [('mdi.arrow-collapse-all',), {'color': self.COLOR_ICON_1}],
            'window_fullscreen':       [('mdi.arrow-expand-all',), {'color': self.COLOR_ICON_1}],
            'MessageBoxWarning':       [('mdi.alert',), {'color': self.COLOR_ICON_1}],
            'arredit':                 [('mdi.table-edit',), {'color': self.COLOR_ICON_1}],
            'zoom_out':                [('mdi.magnify-minus',), {'color': self.COLOR_ICON_1}],
            'zoom_in':                 [('mdi.magnify-plus',), {'color': self.COLOR_ICON_1}],
            'home':                    [('mdi.home',), {'color': self.COLOR_ICON_1}],
            'plot':                    [('mdi.chart-line',), {'color': self.COLOR_ICON_1}],
            'hist':                    [('mdi.chart-histogram',), {'color': self.COLOR_ICON_1}],
            'imshow':                  [('mdi.image',), {'color': self.COLOR_ICON_1}],
            'insert':                  [('mdi.log-in',), {'color': self.COLOR_ICON_1}],
            'rename':                  [('mdi.rename-box',), {'color': self.COLOR_ICON_1}],
            'edit_add':                [('mdi.plus',), {'color': self.COLOR_ICON_1}],
            'edit_remove':             [('mdi.minus',), {'color': self.COLOR_ICON_1}],
            'browse_tab':              [('mdi.tab',), {'color': self.COLOR_ICON_1}],
            'filelist':                [('mdi.view-list',), {'color': self.COLOR_ICON_1}],
            'newwindow':               [('mdi.window-maximize',), {'color': self.COLOR_ICON_1}],
            'versplit':                [('spyder.rows',), {'color': self.COLOR_ICON_1}],
            'horsplit':                [('fa.columns',), {'color': self.COLOR_ICON_1}],
            'close_panel':             [('mdi.close-box-outline',), {'color': self.COLOR_ICON_1}],
            'fromcursor':              [('mdi.cursor-pointer',), {'color': self.COLOR_ICON_1}],
            'filter':                  [('mdi.filter',), {'color': self.COLOR_ICON_1}],
            'folder_new':              [('mdi.folder-plus'), {'color': self.COLOR_ICON_1}]
            'package_new':             [('fa.folder-o', 'spyder.python-logo'), {'options': [{'offset': (0.0, -0.125), 'color': self.COLOR_ICON_1}, {'offset': (0.0, 0.125), 'color': self.COLOR_ICON_1}]}],
            'vcs_commit':              [('mdi.source-commit',), {'color': self.COLOR_ICON_3}],
            'vcs_browse':              [('mdi.source-repository',), {'color': self.COLOR_ICON_3}],
            'fileimport':              [('mdi.download',), {'color': self.COLOR_ICON_1}],
            'environ':                 [('fa.th-list',), {'color': self.COLOR_ICON_1}],
            'options_less':            [('mdi.minus-box',), {'color': self.COLOR_ICON_1}],
            'options_more':            [('mdi.plus-box',), {'color': self.COLOR_ICON_1}],
            'ArrowDown':               [('mdi.arrow-down-bold-circle',), {'color': self.COLOR_ICON_1}],
            'ArrowUp':                 [('mdi.arrow-up-bold-circle',), {'color': self.COLOR_ICON_1}],
            'ArrowBack':               [('mdi.arrow-left-bold-circle',), {'color': self.COLOR_ICON_1}],
            'ArrowForward':            [('mdi.arrow-right-bold-circle',), {'color': self.COLOR_ICON_1}],
            'DialogApplyButton':       [('mdi.check',), {'color': self.COLOR_ICON_1}],
            'DialogCloseButton':       [('mdi.close',), {'color': self.COLOR_ICON_1}],
            'DirClosedIcon':           [('mdi.folder',), {'color': self.COLOR_ICON_1}],
            'DialogHelpButton':        [('mdi.life-buoy',), {'color': self.COLOR_ICON_4}],
            'VideoIcon':               [('mdi.video',), {'color': self.COLOR_ICON_1}],
            'MessageBoxInformation':   [('mdi.information',), {'color': self.COLOR_ICON_1}],
            'DirOpenIcon':             [('mdi.folder-open',), {'color': self.COLOR_ICON_1}],
            'FileIcon':                [('mdi.file',), {'color': self.COLOR_ICON_1}],
            'ExcelFileIcon':           [('mdi.file-excel',), {'color': self.COLOR_ICON_1}],
            'WordFileIcon':            [('mdi.file-word',), {'color': self.COLOR_ICON_1}],
            'PowerpointFileIcon':      [('mdi.file-powerpoint',), {'color': self.COLOR_ICON_1}],
            'PDFIcon':                 [('mdi.file-pdf',), {'color': self.COLOR_ICON_1}],
            'AudioFileIcon':           [('mdi.file-music',), {'color': self.COLOR_ICON_1}],
            'ImageFileIcon':           [('mdi.file-image',), {'color': self.COLOR_ICON_1}],
            'ArchiveFileIcon':         [('fa.file-archive-o',), {'color': self.COLOR_ICON_1}],
            'VideoFileIcon':           [('mdi.file-video',), {'color': self.COLOR_ICON_1}],
            'TextFileIcon':            [('mdi.file-document',), {'color': self.COLOR_ICON_1}],
            'CFileIcon':               [('mdi.language-c',), {'color': self.COLOR_ICON_1}],
            'CppFileIcon':             [('mdi.language-cpp',), {'color': self.COLOR_ICON_1}],
            'CsharpFileIcon':          [('mdi.language-csharp',), {'color': self.COLOR_ICON_1}],
            'PythonFileIcon':          [('mdi.language-python',), {'color': self.COLOR_ICON_1}],
            'JavaFileIcon':            [('mdi.language-java',), {'color': self.COLOR_ICON_1}],
            'JavascriptFileIcon':      [('mdi.language-javascript',), {'color': self.COLOR_ICON_1}],
            'RFileIcon':               [('mdi.language-r',), {'color': self.COLOR_ICON_1}],
            'SwiftFileIcon':           [('mdi.language-swift',), {'color': self.COLOR_ICON_1}],
            'GridFileIcon':            [('mdi.grid',), {'color': self.COLOR_ICON_1}],
            'WindowsFileIcon':         [('mdi.windows',), {'color': self.COLOR_ICON_1}],
            'PowershellFileIcon':      [('mdi.powershell',), {'color': self.COLOR_ICON_1}],
            'DollarFileIcon':          [('mdi.currency-usd',), {'color': self.COLOR_ICON_1}],
            'MarkdownFileIcon':        [('mdi.markdown',), {'color': self.COLOR_ICON_1}],
            'JsonFileIcon':            [('mdi.json',), {'color': self.COLOR_ICON_1}],
            'ExclamationFileIcon':     [('mdi.exclamation',), {'color': self.COLOR_ICON_1}],
            'CodeFileIcon':             [('mdi.xml',), {'color': self.COLOR_ICON_1}],
            'project':                 [('mdi.folder-open',), {'color': self.COLOR_ICON_1}],
            'arrow':                   [('mdi.arrow-right-bold',), {'color': self.COLOR_ICON_1}],
            'collapse':                [('mdi.collapse-all',), {'color': self.COLOR_ICON_1}],
            'expand':                  [('mdi.expand-all',), {'color': self.COLOR_ICON_1}],
            'restore':                 [('mdi.subdirectory-arrow-right',), {'color': self.COLOR_ICON_1, 'rotate': (90)}],
            'collapse_selection':      [('mdi.minus-box',), {'color': self.COLOR_ICON_1}],
            'expand_selection':        [('mdi.plus-box',), {'color': self.COLOR_ICON_1}],
            'copywop':                 [('mdi.console-line',), {'color': self.COLOR_ICON_1}],
            'editpaste':               [('mdi.content-paste',), {'color': self.COLOR_ICON_1}],
            'edit':                    [('mdi.pencil',), {'color': self.COLOR_ICON_1}],
            'convention':              [('mdi.alpha-c-circle',), {'color': self.COLOR_ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'refactor':                [('mdi.alpha-r-circle',), {'color': self.COLOR_ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            '2uparrow':                [('mdi.chevron-double-up',), {'color': self.COLOR_ICON_1}],
            '1uparrow':                [('mdi.chevron-up',), {'color': self.COLOR_ICON_1}],
            '2downarrow':              [('mdi.chevron-double-down',), {'color': self.COLOR_ICON_1}],
            '1downarrow':              [('mdi.chevron-down',), {'color': self.COLOR_ICON_1}],
            'undock':                  [('mdi.open-in-new',), {'color': self.COLOR_ICON_1}],
            'dock':                    [('fa.caret-square-o-down',), {'color': self.COLOR_ICON_1}],
            'close_pane':              [('mdi.window-close',), {'color': self.COLOR_ICON_1}],
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
            'private2':                [('mdi.eye-off',), {'color': self.COLOR_ICON_2, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'private1':                [('mdi.eye-off',), {'color':, self.COLOR_ICON_2, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'method':                  [('mdi.alpha-m-box',), {'color':'#7ea67e', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'constructor':             [('mdi.alpha-c-box',), {'color': 'yellow', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'function':                [('mdi.alpha-f-box',), {'color':'orange', 'scale_factor': self.BIG_ATTR_FACTOR}],
            'blockcomment':            [('mdi.pound',), {'color': self.COLOR_ICON_1, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'cell':                    [('mdi.percent',), {'color':'red', 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'no_match':                [('mdi.checkbox-blank-circle',), {'color': self.COLOR_ICON_1, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'github':                  [('mdi.github-circle',), {'color': self.COLOR_ICON_1}],
            # --- Spyder Tour --------------------------------------------------------
            'tour.close':              [('mdi.close',), {'color': self.COLOR_ICON_1}],
            'tour.home':               [('mdi.skip-backward',), {'color': self.COLOR_ICON_1}],
            'tour.previous':           [('mdi.skip-previous',), {'color': self.COLOR_ICON_1}],
            'tour.next':               [('mdi.skip-next',), {'color': self.COLOR_ICON_1}],
            'tour.end':                [('mdi.skip-forward',), {'color': self.COLOR_ICON_1}],
            # --- Third party plugins ------------------------------------------------
            'profiler':                [('mdi.timer',), {'color': self.COLOR_ICON_1}],
            'pylint':                  [('fa.search', 'fa.check'), {'options': [{'color': self.COLOR_ICON_1}, {'offset': (0.125, 0.125), 'color': 'orange'}]}],
            'condapackages':           [('mdi.archive',), {'color': self.COLOR_ICON_1}],
            'spyder.example':          [('mdi.eye',), {'color': self.COLOR_ICON_1}],
            'spyder.autopep8':         [('mdi.eye',), {'color': self.COLOR_ICON_1}],
            'spyder.memory_profiler':  [('mdi.eye',), {'color': self.COLOR_ICON_1}],
            'spyder.line_profiler':    [('mdi.eye',), {'color': self.COLOR_ICON_1}],
            'symbol_find':             [('mdi.at',), {'color': self.COLOR_ICON_1}],
            'folding.arrow_right_off': [('mdi.menu-right',), {'color': 'gray'}],
            'folding.arrow_right_on':  [('mdi.menu-right',), {'color': self.COLOR_ICON_1}],
            'folding.arrow_down_off':  [('mdi.menu-down',), {'color': 'gray'}],
            'folding.arrow_down_on':   [('mdi.menu-down',), {'color': self.COLOR_ICON_1}],
            'lspserver':               [('mdi.code-tags-check',), {'color': self.COLOR_ICON_1}],
            'dependency_ok':           [('mdi.check',), {'color': self.COLOR_ICON_1}],
            'dependency_warning':      [('mdi.alert',), {'color': self.COLOR_ICON_5}],
            'dependency_error':        [('mdi.alert',), {'color': self.COLOR_ICON_4}],
            'broken_image':            [('mdi.image-broken-variant',), {'color': self.COLOR_ICON_1}],
            # --- Status bar --------------------------------------------------------
            'code_fork':               [('mdi.source-fork',), {'color': self.COLOR_ICON_1}],
            'statusbar':               [('mdi.dock-bottom',), {'color': self.COLOR_ICON_1}],
        }

    def get_std_icon(self, name, size=None):
        """Get standard platform icon."""
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
            icon = self.get_icon(name, resample=resample)
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


COLOR_ICON_1 = ima.COLOR_ICON_1
