import os

from pathlib import Path
# Third party imports
from qtpy.QtGui import QIcon, QPainter, QPalette, QPixmap
from qtpy.QtCore import Qt, QDir, QFileInfo, QModelIndex, QRect, QSize, Signal, Slot, QStringListModel
from qtpy.QtWidgets import QCompleter, QFrame, QFileDialog, QFileIconProvider, QHBoxLayout, QLineEdit, QListView, QMenu, QToolBar, QToolButton, QWidget, QWidgetAction



TRANSP_ICON_SIZE = 40, 40

class BreadcrumbAddressBar(QFrame):
    """Windows Explorer-like address bar"""
    listdir_error = Signal(Path)  # failed to list a directory
    path_error = Signal(Path)  # entered path does not exist
    path_selected = Signal(Path)
    open_dir = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.file_ico_prov = QFileIconProvider()
        self.fs_model = FilenameModel('dirs', icon_provider=self.get_icon)

        pal = self.palette()
        pal.setColor(QPalette.Background,
                     pal.color(QPalette.Base))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFrameShape(self.StyledPanel)
        self.layout().setContentsMargins(4, 0, 0, 0)
        self.layout().setSpacing(0)

        # Edit presented path textually
        self.line_address = QLineEdit(self)
        self.line_address.setFrame(False)
        self.line_address.hide()
        self.line_address.keyPressEvent_super = self.line_address.keyPressEvent
        self.line_address.keyPressEvent = self.line_address_keyPressEvent
        self.line_address.focusOutEvent = self.line_address_focusOutEvent
        self.line_address.contextMenuEvent_super = self.line_address.contextMenuEvent
        self.line_address.contextMenuEvent = self.line_address_contextMenuEvent
        layout.addWidget(self.line_address)
        # Add QCompleter to address line
        completer = self.init_completer(self.line_address, self.fs_model)
        completer.activated.connect(self.set_path)

        # Container for `btn_crumbs_hidden`, `crumbs_panel`, `switch_space`
        self.crumbs_container = QWidget(self)
        crumbs_cont_layout = QHBoxLayout(self.crumbs_container)
        crumbs_cont_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_cont_layout.setSpacing(0)
        layout.addWidget(self.crumbs_container)

        # Hidden breadcrumbs menu button
        self.btn_crumbs_hidden = QToolButton(self)
        self.btn_crumbs_hidden.setAutoRaise(True)
        self.btn_crumbs_hidden.setPopupMode(QToolButton.InstantPopup)
        self.btn_crumbs_hidden.setArrowType(Qt.LeftArrow)
        self.btn_crumbs_hidden.setStyleSheet("QToolButton::menu-indicator {"
                                             "image: none;}")
        self.btn_crumbs_hidden.setMinimumSize(self.btn_crumbs_hidden.minimumSizeHint())
        self.btn_crumbs_hidden.hide()
        crumbs_cont_layout.addWidget(self.btn_crumbs_hidden)
        menu = QMenu(self.btn_crumbs_hidden)  # FIXME:
        menu.aboutToShow.connect(self._hidden_crumbs_menu_show)
        self.btn_crumbs_hidden.setMenu(menu)

        # Container for breadcrumbs
        self.crumbs_panel = QWidget(self)
        crumbs_layout = LeftHBoxLayout(self.crumbs_panel)
        crumbs_layout.widget_state_changed.connect(self.crumb_hide_show)
        crumbs_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_layout.setSpacing(0)
        crumbs_cont_layout.addWidget(self.crumbs_panel)

        # Clicking on empty space to the right puts the bar into edit mode
        self.switch_space = QWidget(self)
        # s_policy = self.switch_space.sizePolicy()
        # s_policy.setHorizontalStretch(1)
        # self.switch_space.setSizePolicy(s_policy)
        self.switch_space.mouseReleaseEvent = self.switch_space_mouse_up
        # crumbs_cont_layout.addWidget(self.switch_space)
        crumbs_layout.set_space_widget(self.switch_space)

        self.btn_browse = QToolButton(self)
        self.btn_browse.setAutoRaise(True)
        self.btn_browse.setText("...")
        self.btn_browse.setToolTip("Browse for folder")
        self.btn_browse.clicked.connect(self._browse_for_folder)
        layout.addWidget(self.btn_browse)

        self.setMaximumHeight(self.line_address.height())  # FIXME:

        self.ignore_resize = False
        self.path_ = None
        self.set_path(Path())

    @staticmethod
    def init_completer(edit_widget, model):
        "Init QCompleter to work with filesystem"
        completer = QCompleter(edit_widget)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(model)
        # Optimize performance https://stackoverflow.com/a/33454284/1119602
        popup = completer.popup()
        popup.setUniformItemSizes(True)
        popup.setLayoutMode(QListView.Batched)
        edit_widget.setCompleter(completer)
        edit_widget.textEdited.connect(model.setPathPrefix)
        return completer

    def get_icon(self, path: (str, Path)):
        "Path -> QIcon"
        fileinfo = QFileInfo(str(path))
        dat = self.file_ico_prov.icon(fileinfo)
        if fileinfo.isHidden():
            pmap = QPixmap(*TRANSP_ICON_SIZE)
            pmap.fill(Qt.transparent)
            painter = QPainter(pmap)
            painter.setOpacity(0.5)
            dat.paint(painter, 0, 0, *TRANSP_ICON_SIZE)
            painter.end()
            dat = QIcon(pmap)
        return dat

    def line_address_contextMenuEvent(self, event):
        self.line_address_context_menu_flag = True
        self.line_address.contextMenuEvent_super(event)

    def line_address_focusOutEvent(self, event):
        if getattr(self, 'line_address_context_menu_flag', False):
            self.line_address_context_menu_flag = False
            return  # do not cancel edit on context menu
        self._cancel_edit()

    def _hidden_crumbs_menu_show(self):
        "SLOT: fill menu with hidden breadcrumbs list"
        menu = self.sender()
        menu.clear()
        # hid_count = self.crumbs_panel.layout().count_hidden()
        for i in reversed(list(self.crumbs_panel.layout().widgets('hidden'))):
            action = menu.addAction(self.get_icon(i.path), i.text())
            action.path = i.path
            action.triggered.connect(self.set_path)

    def _browse_for_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choose folder", str(self.path()))
        if path:
            self.set_path(path)

    def line_address_keyPressEvent(self, event):
        "Actions to take after a key press in text address field"
        if event.key() == Qt.Key_Escape:
            self._cancel_edit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.set_path(self.line_address.text())
            self._show_address_field(False)
        # elif event.text() == os.path.sep:  # FIXME: separator cannot be pasted
        #     print('fill completer data here')
        #     paths = [str(i) for i in
        #              Path(self.line_address.text()).iterdir() if i.is_dir()]
        #     self.completer.model().setStringList(paths)
        else:
            self.line_address.keyPressEvent_super(event)

    def _clear_crumbs(self):
        layout = self.crumbs_panel.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _insert_crumb(self, path):
        btn = QToolButton(self.crumbs_panel)
        btn.setAutoRaise(True)
        btn.setPopupMode(btn.MenuButtonPopup)
        # FIXME: C:\ has no name. Use rstrip on Windows only?
        crumb_text = path.name or str(path).upper().rstrip(os.path.sep)
        btn.setText(crumb_text)
        btn.path = path
        btn.clicked.connect(self.crumb_clicked)
        menu = MenuListView(btn)
        menu.aboutToShow.connect(self.crumb_menu_show)
        menu.setModel(self.fs_model)
        menu.clicked.connect(self.crumb_menuitem_clicked)
        menu.activated.connect(self.crumb_menuitem_clicked)
        btn.setMenu(menu)
        self.crumbs_panel.layout().insertWidget(0, btn)
        btn.setMinimumSize(btn.minimumSizeHint())  # fixed size breadcrumbs
        sp = btn.sizePolicy()
        sp.setVerticalPolicy(sp.Minimum)
        btn.setSizePolicy(sp)
        # print(self._check_space_width(btn.minimumWidth()))
        # print(btn.size(), btn.sizeHint(), btn.minimumSizeHint())

    def crumb_menuitem_clicked(self, index):
        "SLOT: breadcrumb menu item was clicked"
        self.set_path(index.data(Qt.EditRole))

    def crumb_clicked(self):
        "SLOT: breadcrumb was clicked"
        self.set_path(self.sender().path)

    def crumb_menu_show(self):
        "SLOT: fill subdirectory list on menu open"
        menu = self.sender()
        self.fs_model.setPathPrefix(str(menu.parent().path) + os.path.sep)

    def set_path(self, path=None):
        """
        Set path displayed in this BreadcrumbsAddressBar
        Returns `False` if path does not exist or permission error.
        Can be used as a SLOT: `sender().path` is used if `path` is `None`)
        """
        path, emit_err = Path(path or self.sender().path), None
        try:  # C: -> C:\, folder\..\folder -> folder
            path = path.resolve()
        except PermissionError:
            emit_err = self.listdir_error
        if not path.exists():
            emit_err = self.path_error
        self._cancel_edit()  # exit edit mode
        if emit_err:  # permission error or path does not exist
            emit_err.emit(path)
            return False
        self._clear_crumbs()
        self.path_ = path
        self.line_address.setText(str(path))
        self._insert_crumb(path)
        while path.parent != path:
            path = path.parent
            self._insert_crumb(path)
        self.path_selected.emit(path)
        return True

    def _cancel_edit(self):
        "Set edit line text back to current path and switch to view mode"
        self.line_address.setText(str(self.path()))  # revert path
        self._show_address_field(False)  # switch back to breadcrumbs view

    def path(self):
        "Get path displayed in this BreadcrumbsAddressBar"
        return self.path_

    def switch_space_mouse_up(self, event):
        "EVENT: switch_space mouse clicked"
        if event.button() != Qt.LeftButton:  # left click only
            return
        self._show_address_field(True)

    def _show_address_field(self, b_show):
        "Show text address field"
        if b_show:
            self.crumbs_container.hide()
            self.line_address.show()
            self.line_address.setFocus()
            self.line_address.selectAll()
        else:
            self.line_address.hide()
            self.crumbs_container.show()

    def crumb_hide_show(self, widget, state:bool):
        "SLOT: a breadcrumb is hidden/removed or shown"
        layout = self.crumbs_panel.layout()
        if layout.count_hidden() > 0:
            self.btn_crumbs_hidden.show()
        else:
            self.btn_crumbs_hidden.hide()

    def minimumSizeHint(self):
        # print(self.layout().minimumSize().width())
        return QSize(150, self.line_address.height())

class FilenameModel(QStringListModel):
    """
    Model used by QCompleter for file name completions.
    Constructor options:
    `filter_` (None, 'dirs') - include all entries or folders only
    `fs_engine` ('qt', 'pathlib') - enumerate files using `QDir` or `pathlib`
    `icon_provider` (func, 'internal', None) - a function which gets path
                                               and returns QIcon
    """
    def __init__(self, filter_=None, fs_engine='qt', icon_provider='internal'):
        super().__init__()
        self.current_path = None
        self.fs_engine = fs_engine
        self.filter = filter_
        if icon_provider == 'internal':
            self.icons = QFileIconProvider()
            self.icon_provider = self.get_icon
        else:
            self.icon_provider = icon_provider

    def data(self, index, role):
        "Get names/icons of files"
        default = super().data(index, role)
        if role == Qt.DecorationRole and self.icon_provider:
            # self.setData(index, dat, role)
            return self.icon_provider(super().data(index, Qt.DisplayRole))
        if role == Qt.DisplayRole:
            return Path(default).name
        return default

    def get_icon(self, path):
        "Internal icon provider"
        return self.icons.icon(QFileInfo(path))

    def get_file_list(self, path):
        "List entries in `path` directory"
        lst = None
        if self.fs_engine == 'pathlib':
            lst = self.sort_paths([i for i in path.iterdir()
                                   if self.filter != 'dirs' or i.is_dir()])
        elif self.fs_engine == 'qt':
            qdir = QDir(str(path))
            qdir.setFilter(qdir.NoDotAndDotDot | qdir.Hidden |
                (qdir.Dirs if self.filter == 'dirs' else qdir.AllEntries))
            names = qdir.entryList(sort=QDir.DirsFirst |
                                   QDir.LocaleAware)
            lst = [str(path / i) for i in names]
        return lst

    @staticmethod
    def sort_paths(paths):
        "Windows-Explorer-like filename sorting (for 'pathlib' engine)"
        dirs, files = [], []
        for i in paths:
            if i.is_dir():
                dirs.append(str(i))
            else:
                files.append(str(i))
        return sorted(dirs, key=str.lower) + sorted(files, key=str.lower)

    def setPathPrefix(self, prefix):
        path = Path(prefix)
        if not prefix.endswith(os.path.sep):
            path = path.parent
        if path == self.current_path:
            return  # already listed
        if not path.exists():
            return  # wrong path
        self.setStringList(self.get_file_list(path))
        self.current_path = path


class MenuListView(QMenu):
    """
    QMenu with QListView.
    Supports `activated`, `clicked`, `setModel`.
    """
    max_visible_items = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listview = lv = QListView()
        lv.setFrameShape(lv.NoFrame)
        lv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pal = lv.palette()
        pal.setColor(pal.Base, self.palette().color(pal.Window))
        lv.setPalette(pal)

        act_wgt = QWidgetAction(self)
        act_wgt.setDefaultWidget(lv)
        self.addAction(act_wgt)

        self.activated = lv.activated
        self.clicked = lv.clicked
        self.setModel = lv.setModel

        lv.sizeHint = self.size_hint
        lv.minimumSizeHint = self.size_hint
        lv.mousePressEvent = lambda event: None  # skip
        lv.mouseMoveEvent = self.mouse_move_event
        lv.setMouseTracking(True)  # receive mouse move events
        lv.leaveEvent = self.mouse_leave_event
        lv.mouseReleaseEvent = self.mouse_release_event
        lv.keyPressEvent = self.key_press_event
        lv.setFocusPolicy(Qt.NoFocus)  # no focus rect
        lv.setFocus()

        self.last_index = QModelIndex()  # selected index

    def key_press_event(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.last_index.isValid():
                self.activated.emit(self.last_index)
            self.close()
        elif key == Qt.Key_Escape:
            self.close()
        elif key in (Qt.Key_Down, Qt.Key_Up):
            model = self.listview.model()
            row_from, row_to = 0, model.rowCount()-1
            if key == Qt.Key_Down:
                row_from, row_to = row_to, row_from
            if not self.last_index or self.last_index.row() == row_from:
                index = model.index(row_to, 0)
            else:
                shift = 1 if key == Qt.Key_Down else -1
                index = model.index(self.last_index.row()+shift, 0)
            self.listview.setCurrentIndex(index)
            self.last_index = index

    def mouse_move_event(self, event):
        self.listview.clearSelection()
        self.last_index = self.listview.indexAt(event.pos())

    def mouse_leave_event(self, event):
        self.listview.clearSelection()
        self.last_index = QModelIndex()

    def mouse_release_event(self, event):
        "When item is clicked w/ left mouse button close menu, emit `clicked`"
        if event.button() == Qt.LeftButton:
            if self.last_index.isValid():
                self.clicked.emit(self.last_index)
            self.close()

    def size_hint(self):
        lv = self.listview
        width = lv.sizeHintForColumn(0)
        width += lv.verticalScrollBar().sizeHint().width()
        if isinstance(self.parent(), QToolButton):
            width = max(width, self.parent().width())
        visible_rows = min(self.max_visible_items, lv.model().rowCount())
        return QSize(width, visible_rows * lv.sizeHintForRow(0))

class LeftHBoxLayout(QHBoxLayout):
    '''
    Left aligned horizontal layout.
    Hides items similar to Windows Explorer address bar.
    '''
    # Signal is emitted when an item is hidden/shown or removed with `takeAt`
    widget_state_changed = Signal(object, bool)

    def __init__(self, parent=None, minimal_space=0.1):
        super().__init__(parent)
        self.first_visible = 0
        self.set_space_widget()
        self.set_minimal_space(minimal_space)

    def set_space_widget(self, widget=None, stretch=1):
        """
        Set widget to be used to fill empty space to the right
        If `widget`=None the stretch item is used (by default)
        """
        super().takeAt(self.count())
        if widget:
            super().addWidget(widget, stretch)
        else:
            self.addStretch(stretch)

    def space_widget(self):
        "Widget used to fill free space"
        return self[self.count()]

    def setGeometry(self, rc:QRect):
        "`rc` - layout's rectangle w/o margins"
        super().setGeometry(rc)  # perform the layout
        min_sp = self.minimal_space()
        if min_sp < 1:  # percent
            min_sp *= rc.width()
        free_space = self[self.count()].geometry().width() - min_sp
        if free_space < 0 and self.count_visible() > 1:  # hide more items
            widget = self[self.first_visible].widget()
            widget.hide()
            self.first_visible += 1
            self.widget_state_changed.emit(widget, False)
        elif free_space > 0 and self.count_hidden():  # show more items
            widget = self[self.first_visible-1].widget()
            w_width = widget.width() + self.spacing()
            if w_width <= free_space:  # enough space to show next item
                # setGeometry is called after show
                QTimer.singleShot(0, widget.show)
                self.first_visible -= 1
                self.widget_state_changed.emit(widget, True)

    def count_visible(self):
        "Count of visible widgets"
        return self.count(visible=True)

    def count_hidden(self):
        "Count of hidden widgets"
        return self.count(visible=False)

    def minimumSize(self):
        margins = self.contentsMargins()
        return QSize(margins.left() + margins.right(),
                            margins.top() + 24 + margins.bottom())

    def addWidget(self, widget, stretch=0, alignment=None):
        "Append widget to layout, make its width fixed"
        # widget.setMinimumSize(widget.minimumSizeHint())  # FIXME:
        super().insertWidget(self.count(), widget, stretch,
                             alignment or Qt.Alignment(0))

    def count(self, visible=None):
        "Count of items in layout: `visible`=True|False(hidden)|None(all)"
        cnt = super().count() - 1  # w/o last stretchable item
        if visible is None:  # all items
            return cnt
        if visible:  # visible items
            return cnt - self.first_visible
        return self.first_visible  # hidden items

    def widgets(self, state='all'):
        "Iterate over child widgets"
        for i in range(self.first_visible if state=='visible' else 0,
                       self.first_visible if state=='hidden' else self.count()
                       ):
            yield self[i].widget()

    def set_minimal_space(self, value):
        """
        Set minimal size of space area to the right:
        [0.0, 1.0) - % of the full width
        [1, ...) - size in pixels
        """
        self._minimal_space = value
        self.invalidate()

    def minimal_space(self):
        "See `set_minimal_space`"
        return self._minimal_space

    def __getitem__(self, index):
        "`itemAt` slices wrapper"
        if index < 0:
            index = self.count() + index
        return self.itemAt(index)

    def takeAt(self, index):
        "Return an item at the specified `index` and remove it from layout"
        if index < self.first_visible:
            self.first_visible -= 1
        item = super().takeAt(index)
        self.widget_state_changed.emit(item.widget(), False)
        return item