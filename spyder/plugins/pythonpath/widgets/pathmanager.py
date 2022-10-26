# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder path manager."""

# Standard library imports
from __future__ import print_function
from collections import OrderedDict
import os
import os.path as osp
import re
import sys

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout,
                            QListWidget, QListWidgetItem, QMessageBox,
                            QVBoxLayout, QLabel)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import _
from spyder.utils.environ import get_user_env, set_user_env
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton


class PathManager(QDialog, SpyderConfigurationAccessor):
    """Path manager dialog."""
    CONF_SECTION = 'pythonpath_manager'

    redirect_stdio = Signal(bool)
    sig_path_changed = Signal(object)

    def __init__(self, parent, path=None, project_path=None,
                 not_active_path=None, sync=True):
        """Path manager dialog."""
        super(PathManager, self).__init__(parent)
        assert isinstance(path, (tuple, type(None)))

        self.path = path or ()
        self.project_path = project_path or ()
        self.not_active_path = not_active_path or ()
        self.last_path = getcwd_or_home()
        self.original_path_dict = None

        # System and user paths
        self.system_path = self._get_system_path()
        previous_system_path = self.get_conf('system_path', ())

        self.user_path = [
            path for path in self.path
            if path not in (self.system_path + previous_system_path)
        ]

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
        self.top_toolbar_widgets = self._setup_top_toolbar()
        self.bottom_toolbar_widgets = self._setup_bottom_toolbar()
        self.listwidget = QListWidget(self)
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)

        # Widget setup
        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(ima.icon('pythonpath'))
        self.resize(500, 400)
        self.export_button.setVisible(os.name == 'nt' and sync)

        # Layouts
        description = QLabel(
            _("The paths listed below will be passed to IPython consoles and "
              "the Python language server as additional locations to search "
              "for Python modules.")
        )
        description.setWordWrap(True)
        top_layout = QHBoxLayout()
        self._add_widgets_to_layout(self.top_toolbar_widgets, top_layout)

        bottom_layout = QHBoxLayout()
        self._add_widgets_to_layout(self.bottom_toolbar_widgets,
                                    bottom_layout)
        bottom_layout.addWidget(self.bbox)

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addLayout(top_layout)
        layout.addWidget(self.listwidget)
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        # Signals
        self.listwidget.currentRowChanged.connect(lambda x: self.refresh())
        self.listwidget.itemChanged.connect(lambda x: self.refresh())
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Setup
        self.setup()

    def _add_widgets_to_layout(self, widgets, layout):
        """Helper to add toolbar widgets to top and bottom layout."""
        layout.setAlignment(Qt.AlignLeft)
        for widget in widgets:
            if widget is None:
                layout.addStretch(1)
            else:
                layout.addWidget(widget)

    def _setup_top_toolbar(self):
        """Create top toolbar and actions."""
        self.movetop_button = create_toolbutton(
            self,
            text=_("Move to top"),
            icon=ima.icon('2uparrow'),
            triggered=lambda: self.move_to(absolute=0),
            text_beside_icon=True)
        self.moveup_button = create_toolbutton(
            self,
            text=_("Move up"),
            icon=ima.icon('1uparrow'),
            triggered=lambda: self.move_to(relative=-1),
            text_beside_icon=True)
        self.movedown_button = create_toolbutton(
            self,
            text=_("Move down"),
            icon=ima.icon('1downarrow'),
            triggered=lambda: self.move_to(relative=1),
            text_beside_icon=True)
        self.movebottom_button = create_toolbutton(
            self,
            text=_("Move to bottom"),
            icon=ima.icon('2downarrow'),
            triggered=lambda: self.move_to(absolute=1),
            text_beside_icon=True)

        toolbar = [self.movetop_button, self.moveup_button,
                   self.movedown_button, self.movebottom_button]
        self.selection_widgets.extend(toolbar)
        return toolbar

    def _setup_bottom_toolbar(self):
        """Create bottom toolbar and actions."""
        self.add_button = create_toolbutton(
            self,
            text=_('Add path'),
            icon=ima.icon('edit_add'),
            triggered=lambda x: self.add_path(),
            text_beside_icon=True)
        self.remove_button = create_toolbutton(
            self,
            text=_('Remove path'),
            icon=ima.icon('edit_remove'),
            triggered=lambda x: self.remove_path(),
            text_beside_icon=True)
        self.export_button = create_toolbutton(
            self,
            text=_("Export"),
            icon=ima.icon('fileexport'),
            triggered=self.export_pythonpath,
            tip=_("Export to PYTHONPATH environment variable"),
            text_beside_icon=True)

        return [self.add_button, self.remove_button, self.export_button]

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

    def _create_user_header(self):
        """Create header for user added paths"""
        if not self.user_header:
            self.user_header = self._create_header(_("User paths"))
            self.headers.append(self.user_header)

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
                if not self.check_path(path):
                    continue
                item = self._create_item(path)
                self.listwidget.addItem(item)

        self.listwidget.setCurrentRow(0)
        self.original_path_dict = self.get_path_dict()
        self.refresh()

    def _get_system_path(self):
        """Add paths from PYTHONPATH environment variable."""
        env = get_user_env()
        env_pypath = env.get('PYTHONPATH', [])

        if not isinstance(env_pypath, list):
            env_pypath = [env_pypath]

        return tuple(reversed(env_pypath))

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

        # Includes read only paths
        active_path = [k for k, v in self.get_path_dict(True).items() if v]

        if answer == QMessageBox.Yes:
            ppath = active_path
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]

            ppath = [p for p in ppath if p not in active_path]
            ppath = ppath + active_path

        os.environ['PYTHONPATH'] = os.pathsep.join(ppath)

        env['PYTHONPATH'] = list(ppath)
        set_user_env(env, parent=self)

    def get_path_dict(self, read_only=False):
        """
        Return an ordered dict with the path entries as keys and the active
        state as the value.

        If `read_only` is True, the read_only entries are also included.
        """
        odict = OrderedDict()
        for row in range(self.listwidget.count()):
            item = self.listwidget.item(row)
            path = item.text()
            if item not in self.headers:
                if path in self.project_path and not read_only:
                    continue
                odict[path] = item.checkState() == Qt.Checked
        return odict

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

    def check_path(self, path):
        """Check that the path is not a [site|dist]-packages folder."""
        if os.name == 'nt':
            pat = re.compile(r'.*lib/(?:site|dist)-packages.*')
        else:
            pat = re.compile(r'.*lib/python.../(?:site|dist)-packages.*')

        path_norm = path.replace('\\', '/')
        return pat.match(path_norm) is None

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
            if self.check_path(directory):
                self._create_user_header()

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

        Notes
        -----
        This is here until we have a proper plugin, which should make things
        like this easier to handle.
        """
        if self.system_path != self.get_conf('system_path'):
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
