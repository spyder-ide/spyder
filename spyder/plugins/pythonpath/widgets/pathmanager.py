# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder path manager."""

# Standard library imports
from collections import OrderedDict
import os
import os.path as osp
import sys

# Third party imports
from qtpy import PYQT5
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout,
                            QListWidget, QListWidgetItem, QMessageBox,
                            QVBoxLayout, QLabel)

# Local imports
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.pythonpath.utils import check_path, get_system_pythonpath
from spyder.utils.environ import get_user_env, set_user_env
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.stylesheet import PANES_TOOLBAR_STYLESHEET


class PathManagerToolbuttons:
    MoveTop = 'move_top'
    MoveUp = 'move_up'
    MoveDown = 'move_down'
    MoveToBottom = 'move_to_bottom'
    AddPath = 'add_path'
    RemovePath = 'remove_path'
    ExportPaths = 'export_paths'


class PathManager(QDialog, SpyderWidgetMixin):
    """Path manager dialog."""

    redirect_stdio = Signal(bool)
    sig_path_changed = Signal(object)

    # This is required for our tests
    CONF_SECTION = 'pythonpath_manager'

    def __init__(self, parent, path=None, project_path=None,
                 not_active_path=None, sync=True):
        """Path manager dialog."""
        if PYQT5:
            super().__init__(parent, class_parent=parent)
        else:
            QDialog.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        assert isinstance(path, (tuple, type(None)))

        # Match buttons style with the rest of Spyder
        self.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))

        self.path = path or ()
        self.project_path = project_path or ()
        self.not_active_path = not_active_path or ()
        self.last_path = getcwd_or_home()
        self.original_path_dict = None
        self.system_path = ()
        self.user_path = []

        # This is necessary to run our tests
        if self.path:
            self.update_paths(system_path=get_system_pythonpath())

        # Widgets
        self.add_button = None
        self.remove_button = None
        self.movetop_button = None
        self.moveup_button = None
        self.movedown_button = None
        self.movebottom_button = None
        self.export_button = None
        self.user_header = None
        self.project_header = None
        self.system_header = None
        self.headers = []
        self.selection_widgets = []
        self.right_buttons = self._setup_right_toolbar()
        self.listwidget = QListWidget(self)
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)

        # Widget setup
        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(ima.icon('pythonpath'))
        self.resize(500, 400)
        self.export_button.setVisible(os.name == 'nt' and sync)

        # Description
        description = QLabel(
            _("The paths listed below will be passed to IPython consoles and "
              "the Python language server as additional locations to search "
              "for Python modules.")
        )
        description.setWordWrap(True)

        # Buttons layout
        buttons_layout = QVBoxLayout()
        self._add_buttons_to_layout(self.right_buttons, buttons_layout)
        buttons_layout.addStretch(1)

        # Middle layout
        middle_layout = QHBoxLayout()
        middle_layout.addWidget(self.listwidget)
        middle_layout.addLayout(buttons_layout)

        # Widget layout
        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addSpacing(12)
        layout.addLayout(middle_layout)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        # Signals
        self.listwidget.currentRowChanged.connect(lambda x: self.refresh())
        self.listwidget.itemChanged.connect(lambda x: self.refresh())
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Setup
        self.setup()

    def _add_buttons_to_layout(self, widgets, layout):
        """Helper to add buttons to its layout."""
        for widget in widgets:
            layout.addWidget(widget)

    def _setup_right_toolbar(self):
        """Create top toolbar and actions."""
        self.movetop_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveTop,
            text=_("Move path to the top"),
            icon=self.create_icon('2uparrow'),
            triggered=lambda: self.move_to(absolute=0))
        self.moveup_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveUp,
            tip=_("Move path up"),
            icon=self.create_icon('1uparrow'),
            triggered=lambda: self.move_to(relative=-1))
        self.movedown_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveDown,
            tip=_("Move path down"),
            icon=self.create_icon('1downarrow'),
            triggered=lambda: self.move_to(relative=1))
        self.movebottom_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveToBottom,
            text=_("Move path to the bottom"),
            icon=self.create_icon('2downarrow'),
            triggered=lambda: self.move_to(absolute=1))
        self.add_button = self.create_toolbutton(
            PathManagerToolbuttons.AddPath,
            tip=_('Add path'),
            icon=self.create_icon('edit_add'),
            triggered=lambda x: self.add_path())
        self.remove_button = self.create_toolbutton(
            PathManagerToolbuttons.RemovePath,
            tip=_('Remove path'),
            icon=self.create_icon('editclear'),
            triggered=lambda x: self.remove_path())
        self.export_button = self.create_toolbutton(
            PathManagerToolbuttons.ExportPaths,
            icon=self.create_icon('fileexport'),
            triggered=self.export_pythonpath,
            tip=_("Export to PYTHONPATH environment variable"))

        self.selection_widgets = [self.movetop_button, self.moveup_button,
                                  self.movedown_button, self.movebottom_button]
        return (
            [self.add_button, self.remove_button] +
            self.selection_widgets + [self.export_button]
        )

    def _create_item(self, path):
        """Helper to create a new list item."""
        item = QListWidgetItem(path)
        item.setIcon(ima.icon('DirClosedIcon'))

        if path in self.project_path:
            item.setFlags(Qt.NoItemFlags | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
        elif path in self.not_active_path:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
        else:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)

        return item

    def _create_header(self, text):
        """Create a header for a given path section."""
        header = QListWidgetItem(text)

        # Header is centered and it can't be selected
        header.setTextAlignment(Qt.AlignHCenter)
        header.setFlags(Qt.ItemIsEnabled)

        # Make header appear in bold
        font = header.font()
        font.setBold(True)
        header.setFont(font)

        return header

    @property
    def editable_bottom_row(self):
        """Maximum bottom row count that is editable."""
        bottom_row = 0

        if self.project_header:
            bottom_row += len(self.project_path) + 1
        if self.user_header:
            bottom_row += len(self.user_path)

        return bottom_row

    @property
    def editable_top_row(self):
        """Maximum top row count that is editable."""
        top_row = 0

        if self.project_header:
            top_row += len(self.project_path) + 1
        if self.user_header:
            top_row += 1

        return top_row

    def setup(self):
        """Populate list widget."""
        self.listwidget.clear()
        self.headers.clear()
        self.project_header = None
        self.user_header = None
        self.system_header = None

        # Project path
        if self.project_path:
            self.project_header = self._create_header(_("Project path"))
            self.headers.append(self.project_header)
            self.listwidget.addItem(self.project_header)

            for path in self.project_path:
                item = self._create_item(path)
                self.listwidget.addItem(item)

        # Paths added by the user
        if self.user_path:
            self.user_header = self._create_header(_("User paths"))
            self.headers.append(self.user_header)
            self.listwidget.addItem(self.user_header)

            for path in self.user_path:
                item = self._create_item(path)
                self.listwidget.addItem(item)

        # System path
        if self.system_path:
            self.system_header = self._create_header(_("System PYTHONPATH"))
            self.headers.append(self.system_header)
            self.listwidget.addItem(self.system_header)

            for path in self.system_path:
                item = self._create_item(path)
                self.listwidget.addItem(item)

        self.listwidget.setCurrentRow(0)
        self.original_path_dict = self.get_path_dict()
        self.refresh()

    @Slot()
    def export_pythonpath(self):
        """
        Export to PYTHONPATH environment variable
        Only apply to: current user.
        """
        answer = QMessageBox.question(
            self,
            _("Export"),
            _("This will export Spyder's path list to the "
              "<b>PYTHONPATH</b> environment variable for the current user, "
              "allowing you to run your Python modules outside Spyder "
              "without having to configure sys.path. "
              "<br><br>"
              "Do you want to clear the contents of PYTHONPATH before "
              "adding Spyder's path list?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if answer == QMessageBox.Cancel:
            return

        env = get_user_env()

        # This doesn't include the project path because it's a transient
        # directory, i.e. only used in Spyder and during specific
        # circumstances.
        active_path = [k for k, v in self.get_path_dict().items() if v]

        if answer == QMessageBox.Yes:
            ppath = active_path
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]

            ppath = [p for p in ppath if p not in active_path]
            ppath = ppath + active_path

        os.environ['PYTHONPATH'] = os.pathsep.join(ppath)

        # Update widget so changes are reflected on it immediately
        self.update_paths(system_path=tuple(ppath))
        self.set_conf('system_path', tuple(ppath))
        self.setup()

        env['PYTHONPATH'] = list(ppath)
        set_user_env(env, parent=self)

    def get_path_dict(self, project_path=False):
        """
        Return an ordered dict with the path entries as keys and the active
        state as the value.

        If `project_path` is True, its entries are also included.
        """
        odict = OrderedDict()
        for row in range(self.listwidget.count()):
            item = self.listwidget.item(row)
            path = item.text()
            if item not in self.headers:
                if path in self.project_path and not project_path:
                    continue
                odict[path] = item.checkState() == Qt.Checked
        return odict

    def get_user_path(self):
        """Get current user path as displayed on listwidget."""
        user_path = []
        for row in range(self.listwidget.count()):
            item = self.listwidget.item(row)
            path = item.text()
            if item not in self.headers:
                if path not in (self.project_path + self.system_path):
                    user_path.append(path)
        return user_path

    def update_paths(self, path=None, not_active_path=None, system_path=None):
        """Update path attributes."""
        if path is not None:
            self.path = path
        if not_active_path is not None:
            self.not_active_path = not_active_path
        if system_path is not None:
            self.system_path = system_path

        previous_system_path = self.get_conf('system_path', ())
        self.user_path = [
            path for path in self.path
            if path not in (self.system_path + previous_system_path)
        ]

    def refresh(self):
        """Refresh toolbar widgets."""
        current_item = self.listwidget.currentItem()
        enabled = current_item is not None
        for widget in self.selection_widgets:
            widget.setEnabled(enabled)

        # Main variables
        row = self.listwidget.currentRow()
        disable_widgets = []

        # Move up/top disabled for less than top editable item.
        if row <= self.editable_top_row:
            disable_widgets.extend([self.movetop_button, self.moveup_button])

        # Move down/bottom disabled for bottom item
        if row == self.editable_bottom_row:
            disable_widgets.extend([self.movebottom_button,
                                    self.movedown_button])

        # Disable almost all buttons on headers or system PYTHONPATH
        if current_item in self.headers or row > self.editable_bottom_row:
            disable_widgets.extend(
                [self.movetop_button, self.moveup_button,
                 self.movebottom_button, self.movedown_button]
            )

        for widget in disable_widgets:
            widget.setEnabled(False)

        # Enable remove button only for user paths
        self.remove_button.setEnabled(
            not current_item in self.headers
            and (self.editable_top_row <= row <= self.editable_bottom_row)
        )

        self.export_button.setEnabled(self.listwidget.count() > 0)

        # Ok button only enabled if actual changes occur
        self.button_ok.setEnabled(
            self.original_path_dict != self.get_path_dict())

    @Slot()
    def add_path(self, directory=None):
        """
        Add path to list widget.

        If `directory` is provided, the folder dialog is overridden.
        """
        if directory is None:
            self.redirect_stdio.emit(False)
            directory = getexistingdirectory(self, _("Select directory"),
                                             self.last_path)
            self.redirect_stdio.emit(True)
            if not directory:
                return

        directory = osp.abspath(directory)
        self.last_path = directory

        if directory in self.get_path_dict():
            item = self.listwidget.findItems(directory, Qt.MatchExactly)[0]
            item.setCheckState(Qt.Checked)
            answer = QMessageBox.question(
                self,
                _("Add path"),
                _("This directory is already included in the list."
                  "<br> "
                  "Do you want to move it to the top of it?"),
                QMessageBox.Yes | QMessageBox.No)

            if answer == QMessageBox.Yes:
                item = self.listwidget.takeItem(self.listwidget.row(item))
                self.listwidget.insertItem(1, item)
                self.listwidget.setCurrentRow(1)
        else:
            if check_path(directory):
                if not self.user_header:
                    self.user_header = self._create_header(_("User paths"))
                    self.headers.append(self.user_header)

                # Add header if not visible
                if self.listwidget.row(self.user_header) < 0:
                    if self.editable_top_row > 0:
                        header_row = self.editable_top_row - 1
                    else:
                        header_row = 0
                    self.listwidget.insertItem(header_row,
                                               self.user_header)

                # Add new path
                item = self._create_item(directory)
                self.listwidget.insertItem(self.editable_top_row, item)
                self.listwidget.setCurrentRow(self.editable_top_row)

                self.user_path.insert(0, directory)
            else:
                answer = QMessageBox.warning(
                    self,
                    _("Add path"),
                    _("This directory cannot be added to the path!"
                      "<br><br>"
                      "If you want to set a different Python interpreter, "
                      "please go to <tt>Preferences > Main interpreter</tt>"
                      "."),
                    QMessageBox.Ok)

        # Widget moves to back and loses focus on macOS,
        # see spyder-ide/spyder#20808
        if sys.platform == 'darwin':
            self.activateWindow()
            self.raise_()
            self.setFocus()

        self.refresh()

    @Slot()
    def remove_path(self, force=False):
        """
        Remove path from list widget.

        If `force` is True, the message box is overridden.
        """
        if self.listwidget.currentItem():
            if not force:
                answer = QMessageBox.warning(
                    self,
                    _("Remove path"),
                    _("Do you really want to remove the selected path?"),
                    QMessageBox.Yes | QMessageBox.No)

            if force or answer == QMessageBox.Yes:
                # Remove current item from user_path
                item = self.listwidget.currentItem()
                self.user_path.remove(item.text())

                # Remove selected item from view
                self.listwidget.takeItem(self.listwidget.currentRow())

                # Remove user header if there are no more user paths
                if len(self.user_path) == 0:
                    self.listwidget.takeItem(
                        self.listwidget.row(self.user_header))

                # Refresh widget
                self.refresh()

    def move_to(self, absolute=None, relative=None):
        """Move items of list widget."""
        index = self.listwidget.currentRow()
        if absolute is not None:
            if absolute:
                new_index = self.editable_bottom_row
            else:
                new_index = self.editable_top_row
        else:
            new_index = index + relative

        new_index = max(1, min(self.editable_bottom_row, new_index))
        item = self.listwidget.takeItem(index)
        self.listwidget.insertItem(new_index, item)
        self.listwidget.setCurrentRow(new_index)

        self.user_path = self.get_user_path()
        self.refresh()

    def current_row(self):
        """Returns the current row of the list."""
        return self.listwidget.currentRow()

    def set_current_row(self, row):
        """Set the current row of the list."""
        self.listwidget.setCurrentRow(row)

    def row_check_state(self, row):
        """Return the checked state for item in row."""
        item = self.listwidget.item(row)
        return item.checkState()

    def set_row_check_state(self, row, value):
        """Set the current checked state for item in row."""
        item = self.listwidget.item(row)
        item.setCheckState(value)

    def count(self):
        """Return the number of items."""
        return self.listwidget.count()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def _update_system_path(self):
        """
        Request to update path values on main window if current and previous
        system paths are different.
        """
        if self.system_path != self.get_conf('system_path', default=()):
            self.sig_path_changed.emit(self.get_path_dict())
        self.set_conf('system_path', self.system_path)

    def accept(self):
        """Override Qt method."""
        path_dict = self.get_path_dict()
        if self.original_path_dict != path_dict:
            self.sig_path_changed.emit(path_dict)
        super().accept()

    def reject(self):
        self._update_system_path()
        super().reject()

    def closeEvent(self, event):
        self._update_system_path()
        super().closeEvent(event)


def test():
    """Run path manager test."""
    from spyder.utils.qthelpers import qapplication

    _ = qapplication()
    dlg = PathManager(
        None,
        path=tuple(sys.path[:1]),
        project_path=tuple(sys.path[-2:]),
    )

    def callback(path_dict):
        sys.stdout.write(str(path_dict))

    dlg.sig_path_changed.connect(callback)
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()
