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
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton


class PathManager(QDialog):
    """Path manager dialog."""
    redirect_stdio = Signal(bool)
    sig_path_changed = Signal(object)

    def __init__(self, parent, paths=None, read_only_paths=None, sync=True):
        """Path manager dialog."""
        super(PathManager, self).__init__(parent)
        assert isinstance(paths, (OrderedDict, type(None)))

        self.paths = paths or OrderedDict()
        self.read_only_paths = read_only_paths or ()
        self.last_path = getcwd_or_home()
        self.original_path_dict = None

        # Widgets
        self.add_button = None
        self.remove_button = None
        self.movetop_button = None
        self.moveup_button = None
        self.movedown_button = None
        self.movebottom_button = None
        self.import_button = None
        self.export_button = None
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
        self.resize(500, 400)
        self.import_button.setVisible(sync)
        self.export_button.setVisible(os.name == 'nt' and sync)

        # Layouts
        description = QLabel(
            _("The paths listed below will be passed to IPython consoles and "
              "the language server as additional locations to search for "
              "Python modules.<br><br>"
              "Any paths in your system <tt>PYTHONPATH</tt> environment "
              "variable can be imported here if you'd like to use them.")
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
        self.import_button = create_toolbutton(
            self,
            text=_("Import"),
            icon=ima.icon('fileimport'),
            triggered=self.import_pythonpath,
            tip=_("Import from PYTHONPATH environment variable"),
            text_beside_icon=True)
        self.export_button = create_toolbutton(
            self,
            text=_("Export"),
            icon=ima.icon('fileexport'),
            triggered=self.export_pythonpath,
            tip=_("Export to PYTHONPATH environment variable"),
            text_beside_icon=True)

        return [self.add_button, self.remove_button, self.import_button,
                self.export_button]

    def _create_item(self, path, read_only=False, active=True):
        """Helper to create a new list item."""
        item = QListWidgetItem(path)
        item.setIcon(ima.icon('DirClosedIcon'))

        if read_only:
            item.setFlags(Qt.NoItemFlags | Qt.ItemIsUserCheckable)
        else:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

        if active:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)

        return item

    @property
    def editable_bottom_row(self):
        """Maximum bottom row count that is editable."""
        read_only_count = len(self.read_only_paths)
        max_row = self.listwidget.count() - read_only_count - 1
        return max_row

    def setup(self):
        """Populate list widget."""
        self.listwidget.clear()
        for path, active in self.paths.items():
            item = self._create_item(path, active=active)
            self.listwidget.addItem(item)
        for path in self.read_only_paths:
            item = self._create_item(path, read_only=True)
            self.listwidget.addItem(item)
        self.listwidget.setCurrentRow(0)
        self.original_path_dict = self.get_path_dict()
        self.refresh()

    @Slot()
    def import_pythonpath(self):
        """Import from PYTHONPATH environment variable"""
        env_pypath = os.environ.get('PYTHONPATH', '')

        if env_pypath:
            env_pypath = env_pypath.split(os.pathsep)

            dlg = QDialog(self)
            dlg.setWindowTitle(_("PYTHONPATH"))
            dlg.setWindowIcon(ima.icon('pythonpath'))
            dlg.setAttribute(Qt.WA_DeleteOnClose)
            dlg.setMinimumWidth(400)

            label = QLabel("The following paths from your PYTHONPATH "
                           "environment variable will be imported.")
            listw = QListWidget(dlg)
            listw.addItems(env_pypath)

            bbox = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            bbox.accepted.connect(dlg.accept)
            bbox.rejected.connect(dlg.reject)

            layout = QVBoxLayout()
            layout.addWidget(label)
            layout.addWidget(listw)
            layout.addWidget(bbox)
            dlg.setLayout(layout)

            if dlg.exec():
                spy_pypath = self.get_path_dict()
                n = len(spy_pypath)

                for path in reversed(env_pypath):
                    if (path in spy_pypath) or not self.check_path(path):
                        continue
                    item = self._create_item(path)
                    self.listwidget.insertItem(n, item)

                self.refresh()
        else:
            QMessageBox.information(
                self,
                _("PYTHONPATH"),
                _("Your <tt>PYTHONPATH</tt> environment variable is empty, so "
                  "there is nothing to import."),
                QMessageBox.Ok
            )

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
            if bool(item.flags() & Qt.ItemIsEnabled) or read_only:
                odict[item.text()] = item.checkState() == Qt.Checked

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

        self.remove_button.setEnabled(self.listwidget.count()
                                      - len(self.read_only_paths))
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
        paths=OrderedDict({p: True for p in sys.path[4:-2]}),
        read_only_paths=tuple(sys.path[-2:]),
    )

    def callback(path_dict):
        sys.stdout.write(
            '\n'.join([f'{k} : {v}' for k, v in path_dict.items()])
        )
        sys.stdout.write('\n')

    dlg.sig_path_changed.connect(callback)
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()
