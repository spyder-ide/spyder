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
                            QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.py3compat import PY2
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton


class PathManager(QDialog):
    """Path manager dialog."""
    redirect_stdio = Signal(bool)
    sig_path_changed = Signal(object)

    def __init__(self, parent, path=None, read_only_path=None,
                 not_active_path=None, sync=True):
        """Path manager dialog."""
        super(PathManager, self).__init__(parent)
        assert isinstance(path, (tuple, None))

        self.path = path or ()
        self.read_only_path = read_only_path or ()
        self.not_active_path = not_active_path or ()
        self.last_path = getcwd_or_home()
        self.original_path_dict = None

        # Widgets
        self.add_button = None
        self.remove_button = None
        self.movetop_button = None
        self.moveup_button = None
        self.movedown_button = None
        self.movebottom_button = None
        self.sync_button = None
        self.selection_widgets = []
        self.top_toolbar_widgets = self._setup_top_toolbar()
        self.bottom_toolbar_widgets = self._setup_bottom_toolbar()
        self.listwidget = QListWidget(self)
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)

        # Widget setup
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(ima.icon('pythonpath'))
        self.resize(500, 300)
        self.sync_button.setVisible(os.name == 'nt' and sync)

        # Layouts
        top_layout = QHBoxLayout()
        self._add_widgets_to_layout(self.top_toolbar_widgets, top_layout)

        bottom_layout = QHBoxLayout()
        self._add_widgets_to_layout(self.bottom_toolbar_widgets,
                                    bottom_layout)
        bottom_layout.addWidget(self.bbox)

        layout = QVBoxLayout()
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
        self.sync_button = create_toolbutton(
            self,
            text=_("Synchronize..."),
            icon=ima.icon('fileimport'),
            triggered=self.synchronize,
            tip=_("Synchronize Spyder's path list with PYTHONPATH "
                  "environment variable"),
            text_beside_icon=True)

        self.selection_widgets.append(self.remove_button)
        return [self.add_button, self.remove_button, None, self.sync_button]

    def _create_item(self, path):
        """Helper to create a new list item."""
        item = QListWidgetItem(path)
        item.setIcon(ima.icon('DirClosedIcon'))

        if path in self.read_only_path:
            item.setFlags(Qt.NoItemFlags | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
        elif path in self.not_active_path:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
        else:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)

        return item

    @property
    def editable_bottom_row(self):
        """Maximum bottom row count that is editable."""
        read_only_count = len(self.read_only_path)
        if read_only_count == 0:
            max_row = self.listwidget.count() - 1
        else:
            max_row = self.listwidget.count() - read_only_count - 1
        return max_row

    def setup(self):
        """Populate list widget."""
        self.listwidget.clear()
        for path in self.path + self.read_only_path:
            item = self._create_item(path)
            self.listwidget.addItem(item)
        self.listwidget.setCurrentRow(0)
        self.original_path_dict = self.get_path_dict()
        self.refresh()

    @Slot()
    def synchronize(self):
        """
        Synchronize Spyder's path list with PYTHONPATH environment variable
        Only apply to: current user, on Windows platforms.
        """
        answer = QMessageBox.question(
            self,
            _("Synchronize"),
            _("This will synchronize Spyder's path list with "
              "<b>PYTHONPATH</b> environment variable for the current user, "
              "allowing you to run your Python modules outside Spyder "
              "without having to configure sys.path. "
              "<br>"
              "Do you want to clear contents of PYTHONPATH before "
              "adding Spyder's path list?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if answer == QMessageBox.Cancel:
            return
        elif answer == QMessageBox.Yes:
            remove = True
        else:
            remove = False

        from spyder.utils.environ import (get_user_env, listdict2envdict,
                                          set_user_env)
        env = get_user_env()

        # Includes read only paths
        active_path = tuple(k for k, v in self.get_path_dict(True).items()
                            if v)

        if remove:
            ppath = active_path
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]

            ppath = tuple(p for p in ppath if p not in active_path)
            ppath = ppath + active_path

        env['PYTHONPATH'] = list(ppath)
        set_user_env(listdict2envdict(env), parent=self)

    def get_path_dict(self, read_only=False):
        """
        Return an ordered dict with the path entries as keys and the active
        state as the value.

        If `read_only` is True, the read_only entries are also included.
        `read_only` entry refers to the project path entry.
        """
        odict = OrderedDict()
        for row in range(self.listwidget.count()):
            item = self.listwidget.item(row)
            path = item.text()
            if path in self.read_only_path and not read_only:
                continue
            odict[path] = item.checkState() == Qt.Checked
        return odict

    def refresh(self):
        """Refresh toolbar widgets."""
        enabled = self.listwidget.currentItem() is not None
        for widget in self.selection_widgets:
            widget.setEnabled(enabled)

        # Disable buttons based on row
        row = self.listwidget.currentRow()
        disable_widgets = []

        # Move up/top disabled for top item
        if row == 0:
            disable_widgets.extend([self.movetop_button, self.moveup_button])

        # Move down/bottom disabled for bottom item
        if row == self.editable_bottom_row:
            disable_widgets.extend([self.movebottom_button,
                                    self.movedown_button])
        for widget in disable_widgets:
            widget.setEnabled(False)

        self.sync_button.setEnabled(self.listwidget.count() > 0)

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

        If `directory` is provided, the folder dialog is overriden.
        """
        if directory is None:
            self.redirect_stdio.emit(False)
            directory = getexistingdirectory(self, _("Select directory"),
                                             self.last_path)
            self.redirect_stdio.emit(True)

        if PY2:
            is_unicode = False
            try:
                directory.decode('ascii')
            except (UnicodeEncodeError, UnicodeDecodeError):
                is_unicode = True

            if is_unicode:
                QMessageBox.warning(
                    self,
                    _("Add path"),
                    _("You are using Python 2 and the selected path has "
                      "Unicode characters."
                      "<br> "
                      "Therefore, this path will not be added."),
                    QMessageBox.Ok)
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
                self.listwidget.insertItem(0, item)
                self.listwidget.setCurrentRow(0)
        else:
            if self.check_path(directory):
                item = self._create_item(directory)
                self.listwidget.insertItem(0, item)
                self.listwidget.setCurrentRow(0)
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

        If `force` is True, the message box is overriden.
        """
        if self.listwidget.currentItem():
            if not force:
                answer = QMessageBox.warning(
                    self,
                    _("Remove path"),
                    _("Do you really want to remove the selected path?"),
                    QMessageBox.Yes | QMessageBox.No)

            if force or answer == QMessageBox.Yes:
                self.listwidget.takeItem(self.listwidget.currentRow())
                self.refresh()

    def move_to(self, absolute=None, relative=None):
        """Move items of list widget."""
        index = self.listwidget.currentRow()
        if absolute is not None:
            if absolute:
                new_index = self.listwidget.count() - 1
            else:
                new_index = 0
        else:
            new_index = index + relative

        new_index = max(0, min(self.editable_bottom_row, new_index))
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
        """Retunr the checked state for item in row."""
        item = self.listwidget.item(row)
        return item.checkState()

    def set_row_check_state(self, row, value):
        """Set the current checked state for item in row."""
        item = self.listwidget.item(row)
        item.setCheckState(value)

    def count(self):
        """Return the number of items."""
        return self.listwidget.count()

    def accept(self):
        """Override Qt method."""
        path_dict = self.get_path_dict()
        if self.original_path_dict != path_dict:
            self.sig_path_changed.emit(path_dict)
        super(PathManager, self).accept()


def test():
    """Run path manager test."""
    from spyder.utils.qthelpers import qapplication

    _ = qapplication()
    dlg = PathManager(
        None,
        path=tuple(sys.path[:-2]),
        read_only_path=tuple(sys.path[-2:]),
    )

    def callback(path_dict):
        sys.stdout.write(str(path_dict))

    dlg.sig_path_changed.connect(callback)
    dlg.exec_()


if __name__ == "__main__":
    test()
