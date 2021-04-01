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
from spyder.utils.palette import QStylePalette, SpyderPalette
import qtawesome as qta


class IconManager():
    """Class that manages all the icons."""
    def __init__(self):
        self.MAIN_FG_COLOR = SpyderPalette.ICON_1
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
            'log':                     [('mdi.file-document',), {'color': self.MAIN_FG_COLOR}],
            'configure':               [('mdi.wrench',), {'color': self.MAIN_FG_COLOR, 'rotated': 90}],
            'bold':                    [('mdi.format-bold',), {'color': self.MAIN_FG_COLOR}],
            'italic':                  [('mdi.format-italic',), {'color': self.MAIN_FG_COLOR}],
            'run_small':               [('mdi.play',), {'color': SpyderPalette.ICON_3}],
            'stop':                    [('mdi.stop',), {'color': SpyderPalette.COLOR_ERROR_1}],
            'keyboard':                [('mdi.keyboard',), {'color': self.MAIN_FG_COLOR}],
            'eyedropper':              [('mdi.eyedropper',), {'color': self.MAIN_FG_COLOR}],
            'tooloptions':             [('mdi.menu',), {'color': self.MAIN_FG_COLOR}],
            'filenew':                 [('mdi.file',), {'color': self.MAIN_FG_COLOR}],
            'fileopen':                [('mdi.folder-open',), {'color': self.MAIN_FG_COLOR}],
            'revert':                  [('mdi.undo',), {'color': self.MAIN_FG_COLOR}],
            'filesave':                [('mdi.content-save',), {'color': self.MAIN_FG_COLOR}],
            'save_all':                [('mdi.content-save-all',), {'color': self.MAIN_FG_COLOR}],
            'filesaveas':              [('mdi.content-save-edit',), {'color': self.MAIN_FG_COLOR}],
            'print':                   [('mdi.printer',), {'color': self.MAIN_FG_COLOR}],
            'fileclose':               [('mdi.close',), {'color': self.MAIN_FG_COLOR}],
            'breakpoint_transparent':  [('mdi.checkbox-blank-circle',), {'color': SpyderPalette.COLOR_ERROR_1, 'opacity': 0.75, 'scale_factor': 0.9}],
            'breakpoint_big':          [('mdi.checkbox-blank-circle',), {'color': SpyderPalette.ICON_4, 'scale_factor': 0.9} ],
            'breakpoint_cond_big':     [('mdi.help-circle',), {'color': SpyderPalette.ICON_4, 'scale_factor': 0.9},],
            'breakpoints':             [('mdi.dots-vertical',), {'color': self.MAIN_FG_COLOR}],
            'arrow_debugger':          [('mdi.arrow-right-bold',), {'color': SpyderPalette.ICON_2, 'scale_factor': 1.5}],
            'debug':                   [('mdi.step-forward-2',), {'color': SpyderPalette.ICON_2}],
            'arrow-step-over':         [('mdi.debug-step-over',), {'color': SpyderPalette.ICON_2}],
            'arrow-continue':          [('mdi.fast-forward',), {'color': SpyderPalette.ICON_2}],
            'arrow-step-in':           [('mdi.debug-step-into',), {'color': SpyderPalette.ICON_2}],
            'arrow-step-out':          [('mdi.debug-step-out',), {'color': SpyderPalette.ICON_2}],
            'stop_debug':              [('mdi.stop',), {'color': SpyderPalette.ICON_2}],
            'run':                     [('mdi.play',), {'color': SpyderPalette.ICON_3}],
            'todo_list':               [('mdi.check-bold',), {'color': self.MAIN_FG_COLOR}],
            'wng_list':                [('mdi.alert',), {'options': [{'color': SpyderPalette.COLOR_WARN_2, 'color_disabled': QStylePalette.COLOR_TEXT_4}]}],
            'prev_wng':                [('mdi.arrow-left',), {'options': [{'color': SpyderPalette.ICON_1, 'color_disabled': QStylePalette.COLOR_TEXT_4}]}],
            'next_wng':                [('mdi.arrow-right',), {'options': [{'color': SpyderPalette.ICON_1, 'color_disabled': QStylePalette.COLOR_TEXT_4}]}],
            'prev_cursor':             [('mdi.hand-pointing-left',), {'color': self.MAIN_FG_COLOR}],
            'next_cursor':             [('mdi.hand-pointing-right',), {'color': self.MAIN_FG_COLOR}],
            'comment':                 [('mdi.comment-text-outline',), {'color': self.MAIN_FG_COLOR}],
            'indent':                  [('mdi.format-indent-decrease',), {'color': self.MAIN_FG_COLOR}],
            'unindent':                [('mdi.format-indent-increase',), {'color': self.MAIN_FG_COLOR}],
            'toggle_lowercase':        [('mdi.format-letter-case-lower',), {'color': self.MAIN_FG_COLOR}],
            'toggle_uppercase':        [('mdi.format-letter-case-upper',), {'color': self.MAIN_FG_COLOR}],
            'gotoline':                [('mdi.format-line-spacing',), {'color': self.MAIN_FG_COLOR}],
            'error':                   [('mdi.close-circle',), {'color': SpyderPalette.COLOR_ERROR_1}],
            'warning':                 [('mdi.alert',), {'color': SpyderPalette.COLOR_WARN_2}],
            'information':             [('mdi.information-outline',), {'color': SpyderPalette.GROUP_9}],
            'hint':                    [('mdi.lightbulb',), {'color': SpyderPalette.GROUP_9}],
            'todo':                    [('mdi.check-bold',), {'color': SpyderPalette.GROUP_9}],
            'ipython_console':         [('mdi.console',), {'color': self.MAIN_FG_COLOR}],
            'python':                  [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': SpyderPalette.PYTHON_LOGO_UP}, {'color': SpyderPalette.PYTHON_LOGO_DOWN}]}],
            'pythonpath':              [('spyder.python-logo-up', 'spyder.python-logo-down'), {'options': [{'color': SpyderPalette.PYTHON_LOGO_UP}, {'color': SpyderPalette.PYTHON_LOGO_DOWN}]}],
            'findf':                   [('mdi.file-find',), {'color': self.MAIN_FG_COLOR}],
            'history':                 [('mdi.history',), {'color': self.MAIN_FG_COLOR}],
            'help':                    [('mdi.help-circle',), {'color': self.MAIN_FG_COLOR}],
            'lock':                    [('mdi.lock',), {'color': self.MAIN_FG_COLOR}],
            'lock_open':               [('mdi.lock-open',), {'color': self.MAIN_FG_COLOR}],
            'outline_explorer':        [('mdi.file-tree',), {'color': self.MAIN_FG_COLOR}],
            'dictedit':                [('mdi.view-list',), {'color': self.MAIN_FG_COLOR}],
            'previous':                [('mdi.arrow-left-bold',), {'color': self.MAIN_FG_COLOR}],
            'next':                    [('mdi.arrow-right-bold',), {'color': self.MAIN_FG_COLOR}],
            'up':                      [('mdi.arrow-up-bold',), {'color': self.MAIN_FG_COLOR}],
            'spyder':                  [('spyder.spyder-logo-background', 'spyder.spyder-logo-web', 'spyder.spyder-logo-snake'),  {'options': [{'color': SpyderPalette.SPYDER_LOGO_BACKGROUND}, {'color': SpyderPalette.SPYDER_LOGO_WEB}, {'color': SpyderPalette.SPYDER_LOGO_SNAKE}]}],
            'find':                    [('mdi.magnify',), {'color': self.MAIN_FG_COLOR}],
            'replace':                 [('mdi.find-replace',), {'color': self.MAIN_FG_COLOR}],
            'undo':                    [('mdi.undo',), {'color': self.MAIN_FG_COLOR}],
            'redo':                    [('mdi.redo',), {'color': self.MAIN_FG_COLOR}],
            'refresh':                 [('mdi.refresh',), {'color': self.MAIN_FG_COLOR}],
            'restart':                 [('mdi.reload',), {'color': self.MAIN_FG_COLOR}],
            'editcopy':                [('mdi.content-copy',), {'color': self.MAIN_FG_COLOR}],
            'editcut':                 [('mdi.content-cut',), {'color': self.MAIN_FG_COLOR}],
            'editclear':               [('mdi.delete',), {'color': self.MAIN_FG_COLOR}],
            'selectall':               [('mdi.select-all',), {'color': self.MAIN_FG_COLOR}],
            'exit':                    [('mdi.power',), {'color': SpyderPalette.COLOR_ERROR_1}],
            'advanced':                [('mdi.package-variant',), {'color': self.MAIN_FG_COLOR}],
            'bug':                     [('mdi.bug',), {'color': self.MAIN_FG_COLOR}],
            'window_nofullscreen':     [('mdi.arrow-collapse-all',), {'color': self.MAIN_FG_COLOR}],
            'window_fullscreen':       [('mdi.arrow-expand-all',), {'color': self.MAIN_FG_COLOR}],
            'MessageBoxWarning':       [('mdi.alert',), {'color': self.MAIN_FG_COLOR}],
            'arredit':                 [('mdi.table-edit',), {'color': self.MAIN_FG_COLOR}],
            'home':                    [('mdi.home',), {'color': self.MAIN_FG_COLOR}],
            'plot':                    [('mdi.chart-line',), {'color': self.MAIN_FG_COLOR}],
            'hist':                    [('mdi.chart-histogram',), {'color': self.MAIN_FG_COLOR}],
            'imshow':                  [('mdi.image',), {'color': self.MAIN_FG_COLOR}],
            'insert':                  [('mdi.login',), {'color': self.MAIN_FG_COLOR}],
            'rename':                  [('mdi.rename-box',), {'color': self.MAIN_FG_COLOR}],
            'move':                    [('mdi.file-move',), {'color': self.MAIN_FG_COLOR}],
            'edit_add':                [('mdi.plus',), {'color': self.MAIN_FG_COLOR}],
            'edit_remove':             [('mdi.minus',), {'color': self.MAIN_FG_COLOR}],
            'browse_tab':              [('mdi.tab',), {'color': self.MAIN_FG_COLOR}],
            'filelist':                [('mdi.view-list',), {'color': self.MAIN_FG_COLOR}],
            'newwindow':               [('mdi.window-maximize',), {'color': self.MAIN_FG_COLOR}],
            'close_panel':             [('mdi.close-box-outline',), {'color': self.MAIN_FG_COLOR}],
            'fromcursor':              [('mdi.cursor-pointer',), {'color': self.MAIN_FG_COLOR, 'rotated': 90}],
            'filter':                  [('mdi.filter',), {'color': self.MAIN_FG_COLOR}],
            'folder_new':              [('mdi.folder-plus',), {'color': self.MAIN_FG_COLOR}],
            'vcs_commit':              [('mdi.source-commit',), {'color': SpyderPalette.ICON_3}],
            'vcs_browse':              [('mdi.source-repository',), {'color': SpyderPalette.ICON_3}],
            'fileimport':              [('mdi.download',), {'color': self.MAIN_FG_COLOR}],
            'options_less':            [('mdi.minus-box',), {'color': self.MAIN_FG_COLOR}],
            'options_more':            [('mdi.plus-box',), {'color': self.MAIN_FG_COLOR}],
            'ArrowDown':               [('mdi.arrow-down-bold-circle',), {'color': self.MAIN_FG_COLOR}],
            'ArrowUp':                 [('mdi.arrow-up-bold-circle',), {'color': self.MAIN_FG_COLOR}],
            'ArrowBack':               [('mdi.arrow-left-bold-circle',), {'color': self.MAIN_FG_COLOR}],
            'ArrowForward':            [('mdi.arrow-right-bold-circle',), {'color': self.MAIN_FG_COLOR}],
            'DialogApplyButton':       [('mdi.check',), {'color': self.MAIN_FG_COLOR}],
            'DialogCloseButton':       [('mdi.close',), {'color': self.MAIN_FG_COLOR}],
            'DirClosedIcon':           [('mdi.folder',), {'color': self.MAIN_FG_COLOR}],
            'DialogHelpButton':        [('mdi.lifebuoy',), {'color': self.MAIN_FG_COLOR}],
            'VideoIcon':               [('mdi.video',), {'color': self.MAIN_FG_COLOR}],
            'MessageBoxInformation':   [('mdi.information',), {'color': self.MAIN_FG_COLOR}],
            'DirOpenIcon':             [('mdi.folder-open',), {'color': self.MAIN_FG_COLOR}],
            'FileIcon':                [('mdi.file',), {'color': self.MAIN_FG_COLOR}],
            'ExcelFileIcon':           [('mdi.file-excel',), {'color': self.MAIN_FG_COLOR}],
            'WordFileIcon':            [('mdi.file-word',), {'color': self.MAIN_FG_COLOR}],
            'PowerpointFileIcon':      [('mdi.file-powerpoint',), {'color': self.MAIN_FG_COLOR}],
            'PDFIcon':                 [('mdi.file-pdf',), {'color': self.MAIN_FG_COLOR}],
            'AudioFileIcon':           [('mdi.file-music',), {'color': self.MAIN_FG_COLOR}],
            'ImageFileIcon':           [('mdi.file-image',), {'color': self.MAIN_FG_COLOR}],
            'VideoFileIcon':           [('mdi.file-video',), {'color': self.MAIN_FG_COLOR}],
            'TextFileIcon':            [('mdi.file-document',), {'color': self.MAIN_FG_COLOR}],
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
            'DollarFileIcon':          [('mdi.currency-usd',), {'color': self.MAIN_FG_COLOR}],
            'MarkdownFileIcon':        [('mdi.markdown',), {'color': self.MAIN_FG_COLOR}],
            'JsonFileIcon':            [('mdi.json',), {'color': self.MAIN_FG_COLOR}],
            'ExclamationFileIcon':     [('mdi.exclamation',), {'color': self.MAIN_FG_COLOR}],
            'CodeFileIcon':             [('mdi.xml',), {'color': self.MAIN_FG_COLOR}],
            'project':                 [('mdi.folder-open',), {'color': self.MAIN_FG_COLOR}],
            'arrow':                   [('mdi.arrow-right-bold',), {'color': self.MAIN_FG_COLOR}],
            'collapse':                [('mdi.collapse-all',), {'color': self.MAIN_FG_COLOR}],
            'expand':                  [('mdi.expand-all',), {'color': self.MAIN_FG_COLOR}],
            'restore':                 [('mdi.subdirectory-arrow-right',), {'color': self.MAIN_FG_COLOR, 'rotated': 270}],
            'collapse_selection':      [('mdi.minus-box',), {'color': self.MAIN_FG_COLOR}],
            'expand_selection':        [('mdi.plus-box',), {'color': self.MAIN_FG_COLOR}],
            'copywop':                 [('mdi.console-line',), {'color': self.MAIN_FG_COLOR}],
            'editpaste':               [('mdi.content-paste',), {'color': self.MAIN_FG_COLOR}],
            'edit':                    [('mdi.pencil',), {'color': self.MAIN_FG_COLOR}],
            'convention':              [('mdi.alpha-c-circle',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'refactor':                [('mdi.alpha-r-circle',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            '2uparrow':                [('mdi.chevron-double-up',), {'color': self.MAIN_FG_COLOR}],
            '1uparrow':                [('mdi.chevron-up',), {'color': self.MAIN_FG_COLOR}],
            '2downarrow':              [('mdi.chevron-double-down',), {'color': self.MAIN_FG_COLOR}],
            '1downarrow':              [('mdi.chevron-down',), {'color': self.MAIN_FG_COLOR}],
            'undock':                  [('mdi.open-in-new',), {'color': self.MAIN_FG_COLOR}],
            'close_pane':              [('mdi.window-close',), {'color': self.MAIN_FG_COLOR}],
            # --- Autocompletion/document symbol type icons --------------
            'keyword':                 [('mdi.alpha-k-box',), {'color': SpyderPalette.GROUP_9, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'color':                   [('mdi.alpha-c-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'enum':                    [('mdi.alpha-e-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'value':                   [('mdi.alpha-v-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'constant':                [('mdi.alpha-c-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'unit':                    [('mdi.alpha-u-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'text':                    [('mdi.alpha-t-box',), {'color': SpyderPalette.GROUP_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'file':                    [('mdi.alpha-f-box',), {'color': SpyderPalette.GROUP_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'snippet':                 [('mdi.alpha-s-box',), {'color': SpyderPalette.GROUP_11, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'attribute':               [('mdi.alpha-a-box',), {'color': SpyderPalette.GROUP_12, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'reference':               [('mdi.alpha-r-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'variable':                [('mdi.alpha-v-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'field':                   [('mdi.alpha-a-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'property':                [('mdi.alpha-p-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'module':                  [('mdi.alpha-m-box',), {'color': SpyderPalette.GROUP_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'namespace':               [('mdi.alpha-n-box',), {'color': SpyderPalette.GROUP_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'package':                 [('mdi.alpha-p-box',), {'color': SpyderPalette.GROUP_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'class':                   [('mdi.alpha-c-box',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'interface':               [('mdi.alpha-i-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'string':                  [('mdi.alpha-s-box',), {'color': SpyderPalette.GROUP_9, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'number':                  [('mdi.alpha-n-box',), {'color': SpyderPalette.GROUP_9, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'boolean':                 [('mdi.alpha-b-box',), {'color': SpyderPalette.GROUP_12, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'array':                   [('mdi.alpha-a-box',), {'color': SpyderPalette.GROUP_9, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'object':                  [('mdi.alpha-o-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'key':                     [('mdi.alpha-k-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'class':                   [('mdi.alpha-c-box',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'null':                    [('mdi.alpha-n-box',), {'color': SpyderPalette.GROUP_12, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'enum_member':             [('mdi.alpha-e-box',), {'color': SpyderPalette.COLOR_ERROR_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'struct':                  [('mdi.alpha-s-box',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'event':                   [('mdi.alpha-e-box',), {'color': SpyderPalette.COLOR_WARN_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'operator':                [('mdi.alpha-o-box',), {'color': SpyderPalette.COLOR_WARN_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'type_parameter':          [('mdi.alpha-t-box',), {'color': SpyderPalette.COLOR_WARN_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'private2':                [('mdi.eye-off',), {'color': SpyderPalette.COLOR_ERROR_3, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'private1':                [('mdi.eye-off',), {'color': SpyderPalette.COLOR_ERROR_3, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'method':                  [('mdi.alpha-m-box',), {'color': SpyderPalette.ICON_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'constructor':             [('mdi.alpha-c-box',), {'color': SpyderPalette.ICON_5, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'function':                [('mdi.alpha-f-box',), {'color': SpyderPalette.COLOR_WARN_3, 'scale_factor': self.BIG_ATTR_FACTOR}],
            'blockcomment':            [('mdi.pound',), {'color': SpyderPalette.ICON_2, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'cell':                    [('mdi.percent',), {'color':SpyderPalette.GROUP_9, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'no_match':                [('mdi.checkbox-blank-circle',), {'color': SpyderPalette.GROUP_3, 'scale_factor': self.SMALL_ATTR_FACTOR}],
            'github':                  [('mdi.github',), {'color': self.MAIN_FG_COLOR}],
            # --- Spyder Tour --------------------------------------------------------
            'tour.close':              [('mdi.close',), {'color': self.MAIN_FG_COLOR}],
            'tour.home':               [('mdi.skip-backward',), {'color': self.MAIN_FG_COLOR}],
            'tour.previous':           [('mdi.skip-previous',), {'color': self.MAIN_FG_COLOR}],
            'tour.next':               [('mdi.skip-next',), {'color': self.MAIN_FG_COLOR}],
            'tour.end':                [('mdi.skip-forward',), {'color': self.MAIN_FG_COLOR}],
            # --- Third party plugins ------------------------------------------------
            'profiler':                [('mdi.timer-outline',), {'color': self.MAIN_FG_COLOR}],
            'condapackages':           [('mdi.archive',), {'color': self.MAIN_FG_COLOR}],
            'spyder.example':          [('mdi.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.autopep8':         [('mdi.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.memory_profiler':  [('mdi.eye',), {'color': self.MAIN_FG_COLOR}],
            'spyder.line_profiler':    [('mdi.eye',), {'color': self.MAIN_FG_COLOR}],
            'symbol_find':             [('mdi.at',), {'color': self.MAIN_FG_COLOR}],
            'folding.arrow_right_off': [('mdi.menu-right',), {'color': SpyderPalette.GROUP_3}],
            'folding.arrow_right_on':  [('mdi.menu-right',), {'color': self.MAIN_FG_COLOR}],
            'folding.arrow_down_off':  [('mdi.menu-down',), {'color': SpyderPalette.GROUP_3}],
            'folding.arrow_down_on':   [('mdi.menu-down',), {'color': self.MAIN_FG_COLOR}],
            'lspserver':               [('mdi.code-tags-check',), {'color': self.MAIN_FG_COLOR}],
            'dependency_ok':           [('mdi.check',), {'color': self.MAIN_FG_COLOR}],
            'dependency_warning':      [('mdi.alert',), {'color': SpyderPalette.COLOR_WARN_2}],
            'dependency_error':        [('mdi.alert',), {'color': SpyderPalette.COLOR_ERROR_1}],
            'broken_image':            [('mdi.image-broken-variant',), {'color': self.MAIN_FG_COLOR}],
            # --- Status bar --------------------------------------------------------
            'code_fork':               [('mdi.source-fork',), {'color': self.MAIN_FG_COLOR}],
            'statusbar':               [('mdi.dock-bottom',), {'color': self.MAIN_FG_COLOR}],
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


MAIN_FG_COLOR = ima.MAIN_FG_COLOR
