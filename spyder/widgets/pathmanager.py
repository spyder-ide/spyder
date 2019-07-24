# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder path manager"""

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import sys

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout,
                            QListWidget, QListWidgetItem, QMessageBox,
                            QVBoxLayout, QCheckBox)

# Local imports
from spyder.config.base import _
from spyder.utils.misc import getcwd_or_home
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_toolbutton
from spyder.py3compat import PY2


class PathManager(QDialog):
    redirect_stdio = Signal(bool)

    def __init__(self, parent=None, pathlist=None, ro_pathlist=None,
                 not_active_pathlist=None, sync=True):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        assert isinstance(pathlist, list)
        self.pathlist = pathlist
        if not_active_pathlist is None:
            not_active_pathlist = []
        self.not_active_pathlist = not_active_pathlist
        if ro_pathlist is None:
            ro_pathlist = []
        self.ro_pathlist = ro_pathlist

        self.last_path = getcwd_or_home()

        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(ima.icon('pythonpath'))
        self.resize(500, 300)

        self.selection_widgets = []

        layout = QVBoxLayout()
        self.setLayout(layout)

        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        self.toolbar_widgets1 = self.setup_top_toolbar(top_layout)

        self.listwidget = QListWidget(self)
        self.listwidget.currentRowChanged.connect(self.refresh)
        self.listwidget.itemChanged.connect(self.update_not_active_pathlist)
        layout.addWidget(self.listwidget)

        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)
        self.sync_button = None
        self.toolbar_widgets2 = self.setup_bottom_toolbar(bottom_layout, sync)

        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Close)
        bbox.rejected.connect(self.reject)
        bottom_layout.addWidget(bbox)

        self.update_list()
        self.refresh()

    @property
    def active_pathlist(self):
        return [path for path in self.pathlist
                if path not in self.not_active_pathlist]

    def _add_widgets_to_layout(self, layout, widgets):
        layout.setAlignment(Qt.AlignLeft)
        for widget in widgets:
            layout.addWidget(widget)

    def setup_top_toolbar(self, layout):
        toolbar = []
        movetop_button = create_toolbutton(self,
                                    text=_("Move to top"),
                                    icon=ima.icon('2uparrow'),
                                    triggered=lambda: self.move_to(absolute=0),
                                    text_beside_icon=True)
        toolbar.append(movetop_button)
        moveup_button = create_toolbutton(self,
                                    text=_("Move up"),
                                    icon=ima.icon('1uparrow'),
                                    triggered=lambda: self.move_to(relative=-1),
                                    text_beside_icon=True)
        toolbar.append(moveup_button)
        movedown_button = create_toolbutton(self,
                                    text=_("Move down"),
                                    icon=ima.icon('1downarrow'),
                                    triggered=lambda: self.move_to(relative=1),
                                    text_beside_icon=True)
        toolbar.append(movedown_button)
        movebottom_button = create_toolbutton(self,
                                    text=_("Move to bottom"),
                                    icon=ima.icon('2downarrow'),
                                    triggered=lambda: self.move_to(absolute=1),
                                    text_beside_icon=True)
        toolbar.append(movebottom_button)
        self.selection_widgets.extend(toolbar)
        self._add_widgets_to_layout(layout, toolbar)
        return toolbar

    def setup_bottom_toolbar(self, layout, sync=True):
        toolbar = []
        add_button = create_toolbutton(self, text=_('Add path'),
                                       icon=ima.icon('edit_add'),
                                       triggered=self.add_path,
                                       text_beside_icon=True)
        toolbar.append(add_button)
        remove_button = create_toolbutton(self, text=_('Remove path'),
                                          icon=ima.icon('edit_remove'),
                                          triggered=self.remove_path,
                                          text_beside_icon=True)
        toolbar.append(remove_button)
        self.selection_widgets.append(remove_button)
        self._add_widgets_to_layout(layout, toolbar)
        layout.addStretch(1)
        if os.name == 'nt' and sync:
            self.sync_button = create_toolbutton(self,
                  text=_("Synchronize..."),
                  icon=ima.icon('fileimport'), triggered=self.synchronize,
                  tip=_("Synchronize Spyder's path list with PYTHONPATH "
                              "environment variable"),
                  text_beside_icon=True)
            layout.addWidget(self.sync_button)
        return toolbar

    @Slot()
    def synchronize(self):
        """
        Synchronize Spyder's path list with PYTHONPATH environment variable
        Only apply to: current user, on Windows platforms
        """
        answer = QMessageBox.question(self, _("Synchronize"),
            _("This will synchronize Spyder's path list with "
                    "<b>PYTHONPATH</b> environment variable for current user, "
                    "allowing you to run your Python modules outside Spyder "
                    "without having to configure sys.path. "
                    "<br>Do you want to clear contents of PYTHONPATH before "
                    "adding Spyder's path list?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if answer == QMessageBox.Cancel:
            return
        elif answer == QMessageBox.Yes:
            remove = True
        else:
            remove = False
        from spyder.utils.environ import (get_user_env, set_user_env,
                                          listdict2envdict)
        env = get_user_env()
        if remove:
            ppath = self.active_pathlist+self.ro_pathlist
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]
            ppath = [path for path in ppath
                     if path not in (self.active_pathlist+self.ro_pathlist)]
            ppath.extend(self.active_pathlist+self.ro_pathlist)
        env['PYTHONPATH'] = ppath
        set_user_env(listdict2envdict(env), parent=self)

    def get_path_list(self):
        """Return path list (does not include the read-only path list)"""
        return self.pathlist

    def update_not_active_pathlist(self, item):
        path = item.text()
        if bool(item.checkState()) is True:
            self.remove_from_not_active_pathlist(path)
        else:
            self.add_to_not_active_pathlist(path)

    def add_to_not_active_pathlist(self, path):
        if path not in self.not_active_pathlist:
            self.not_active_pathlist.append(path)

    def remove_from_not_active_pathlist(self, path):
        if path in self.not_active_pathlist:
            self.not_active_pathlist.remove(path)

    def update_list(self):
        """Update path list"""
        self.listwidget.clear()
        for name in self.pathlist+self.ro_pathlist:
            item = QListWidgetItem(name)
            item.setIcon(ima.icon('DirClosedIcon'))
            if name in self.ro_pathlist:
                item.setFlags(Qt.NoItemFlags | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
            elif name in self.not_active_pathlist:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
            self.listwidget.addItem(item)
        self.refresh()

    def refresh(self, row=None):
        """Refresh widget"""
        for widget in self.selection_widgets:
            widget.setEnabled(self.listwidget.currentItem() is not None)
        not_empty = self.listwidget.count() > 0
        if self.sync_button is not None:
            self.sync_button.setEnabled(not_empty)

    def move_to(self, absolute=None, relative=None):
        index = self.listwidget.currentRow()
        if absolute is not None:
            if absolute:
                new_index = len(self.pathlist)-1
            else:
                new_index = 0
        else:
            new_index = index + relative
        new_index = max(0, min(len(self.pathlist)-1, new_index))
        path = self.pathlist.pop(index)
        self.pathlist.insert(new_index, path)
        self.update_list()
        self.listwidget.setCurrentRow(new_index)

    @Slot()
    def remove_path(self):
        answer = QMessageBox.warning(self, _("Remove path"),
            _("Do you really want to remove selected path?"),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.pathlist.pop(self.listwidget.currentRow())
            self.remove_from_not_active_pathlist(
                    self.listwidget.currentItem().text())
            self.update_list()

    @Slot()
    def add_path(self):
        self.redirect_stdio.emit(False)
        directory = getexistingdirectory(self, _("Select directory"),
                                         self.last_path)
        self.redirect_stdio.emit(True)
        if directory:
            is_unicode = False
            if PY2:
                try:
                    directory.decode('ascii')
                except UnicodeEncodeError:
                    is_unicode = True
                if is_unicode:
                    QMessageBox.warning(self, _("Add path"),
                                        _("You are using Python 2 and the path"
                                          " selected has Unicode characters. "
                                          "The new path will not be added."),
                                        QMessageBox.Ok)
                    return
            directory = osp.abspath(directory)
            self.last_path = directory
            if directory in self.pathlist:
                item = self.listwidget.findItems(directory, Qt.MatchExactly)[0]
                item.setCheckState(Qt.Checked)
                answer = QMessageBox.question(
                            self, _("Add path"),
                            _("This directory is already included in Spyder "
                              "path list.<br>Do you want to move it to the "
                              "top of the list?"),
                            QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.Yes:
                    self.pathlist.remove(directory)
                else:
                    return
            self.pathlist.insert(0, directory)
            self.update_list()


def test():
    """Run path manager test"""
    from spyder.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore
    test = PathManager(None, pathlist=sys.path[:-10],
                       ro_pathlist=sys.path[-10:])
    test.exec_()
    print(test.get_path_list())  # spyder: test-skip


if __name__ == "__main__":
    test()
