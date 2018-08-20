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
import qtawesome as qta


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
    'python_t':                [('spyder.python-logo',), {'color':'gray'}],
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
