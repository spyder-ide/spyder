# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Spyder path manager"""

from __future__ import print_function

from spyderlib.qt.QtGui import (QDialog, QListWidget, QDialogButtonBox,
                                QVBoxLayout, QHBoxLayout, QMessageBox,
                                QListWidgetItem)
from spyderlib.qt.QtCore import Qt, SIGNAL, SLOT
from spyderlib.qt.compat import getexistingdirectory

import os
import sys
import os.path as osp

# Local imports
from spyderlib.utils.qthelpers import get_icon, get_std_icon, create_toolbutton
from spyderlib.baseconfig import _
from spyderlib.py3compat import getcwd


class PathManager(QDialog):
    def __init__(self, parent=None, pathlist=None, ro_pathlist=None, sync=True):
        QDialog.__init__(self, parent)
        
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        assert isinstance(pathlist, list)
        self.pathlist = pathlist
        if ro_pathlist is None:
            ro_pathlist = []
        self.ro_pathlist = ro_pathlist
        
        self.last_path = getcwd()
        
        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(get_icon('pythonpath.png'))
        self.resize(500, 300)
        
        self.selection_widgets = []
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        self.toolbar_widgets1 = self.setup_top_toolbar(top_layout)

        self.listwidget = QListWidget(self)
        self.connect(self.listwidget, SIGNAL("currentRowChanged(int)"),
                     self.refresh)
        layout.addWidget(self.listwidget)

        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)
        self.sync_button = None
        self.toolbar_widgets2 = self.setup_bottom_toolbar(bottom_layout, sync)        
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Close)
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        bottom_layout.addWidget(bbox)
        
        self.update_list()
        self.refresh()
        
    def _add_widgets_to_layout(self, layout, widgets):
        layout.setAlignment(Qt.AlignLeft)
        for widget in widgets:
            layout.addWidget(widget)
        
    def setup_top_toolbar(self, layout):
        toolbar = []
        movetop_button = create_toolbutton(self,
                                    text=_("Move to top"),
                                    icon=get_icon('2uparrow.png'),
                                    triggered=lambda: self.move_to(absolute=0),
                                    text_beside_icon=True)
        toolbar.append(movetop_button)
        moveup_button = create_toolbutton(self,
                                    text=_("Move up"),
                                    icon=get_icon('1uparrow.png'),
                                    triggered=lambda: self.move_to(relative=-1),
                                    text_beside_icon=True)
        toolbar.append(moveup_button)
        movedown_button = create_toolbutton(self,
                                    text=_("Move down"),
                                    icon=get_icon('1downarrow.png'),
                                    triggered=lambda: self.move_to(relative=1),
                                    text_beside_icon=True)
        toolbar.append(movedown_button)
        movebottom_button = create_toolbutton(self,
                                    text=_("Move to bottom"),
                                    icon=get_icon('2downarrow.png'),
                                    triggered=lambda: self.move_to(absolute=1),
                                    text_beside_icon=True)
        toolbar.append(movebottom_button)
        self.selection_widgets.extend(toolbar)
        self._add_widgets_to_layout(layout, toolbar)
        return toolbar
    
    def setup_bottom_toolbar(self, layout, sync=True):
        toolbar = []
        add_button = create_toolbutton(self, text=_("Add path"),
                                       icon=get_icon('edit_add.png'),
                                       triggered=self.add_path,
                                       text_beside_icon=True)
        toolbar.append(add_button)
        remove_button = create_toolbutton(self, text=_("Remove path"),
                                          icon=get_icon('edit_remove.png'),
                                          triggered=self.remove_path,
                                          text_beside_icon=True)
        toolbar.append(remove_button)
        self.selection_widgets.append(remove_button)
        self._add_widgets_to_layout(layout, toolbar)
        layout.addStretch(1)
        if os.name == 'nt' and sync:
            self.sync_button = create_toolbutton(self,
                  text=_("Synchronize..."),
                  icon=get_icon('synchronize.png'), triggered=self.synchronize,
                  tip=_("Synchronize Spyder's path list with PYTHONPATH "
                              "environment variable"),
                  text_beside_icon=True)
            layout.addWidget(self.sync_button)
        return toolbar
    
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
        from spyderlib.utils.environ import (get_user_env, set_user_env,
                                             listdict2envdict)
        env = get_user_env()
        if remove:
            ppath = self.pathlist+self.ro_pathlist
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]
            ppath = [path for path in ppath
                     if path not in (self.pathlist+self.ro_pathlist)]
            ppath.extend(self.pathlist+self.ro_pathlist)
        env['PYTHONPATH'] = ppath
        set_user_env( listdict2envdict(env), parent=self )
        
    def get_path_list(self):
        """Return path list (does not include the read-only path list)"""
        return self.pathlist
        
    def update_list(self):
        """Update path list"""
        self.listwidget.clear()
        for name in self.pathlist+self.ro_pathlist:
            item = QListWidgetItem(name)
            item.setIcon(get_std_icon('DirClosedIcon'))
            if name in self.ro_pathlist:
                item.setFlags(Qt.NoItemFlags)
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
        
    def remove_path(self):
        answer = QMessageBox.warning(self, _("Remove path"),
            _("Do you really want to remove selected path?"),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.pathlist.pop(self.listwidget.currentRow())
            self.update_list()
    
    def add_path(self):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = getexistingdirectory(self, _("Select directory"),
                                         self.last_path)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if directory:
            directory = osp.abspath(directory)
            self.last_path = directory
            if directory in self.pathlist:
                answer = QMessageBox.question(self, _("Add path"),
                    _("This directory is already included in Spyder path "
                            "list.<br>Do you want to move it to the top of "
                            "the list?"),
                    QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.Yes:
                    self.pathlist.remove(directory)
                else:
                    return
            self.pathlist.insert(0, directory)
            self.update_list()


def test():
    """Run path manager test"""
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore
    test = PathManager(None, sys.path[:-10], sys.path[-10:])
    test.exec_()
    print(test.get_path_list())

if __name__ == "__main__":
    test()
