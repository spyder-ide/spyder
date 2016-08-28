# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import re
import shutil
import xml.etree.ElementTree as ElementTree

# Third party imports
from qtpy import PYQT5
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QFileInfo, Qt, Signal, Slot
from qtpy.QtWidgets import (QAbstractItemView, QFileIconProvider, QHBoxLayout,
                            QHeaderView, QInputDialog, QLabel, QLineEdit,
                            QMessageBox, QPushButton, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, get_image_path, STDERR
from spyder.py3compat import getcwd, pickle, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import misc
from spyder.utils.qthelpers import create_action, get_icon
from spyder.widgets.explorer import FilteredDirView, fixpath, listdir
from spyder.widgets.formlayout import fedit
from spyder.widgets.pathmanager import PathManager


class IconProvider(QFileIconProvider):
    """Project tree widget icon provider"""
    def __init__(self, treeview):
        super(IconProvider, self).__init__()
        self.treeview = treeview
        
    @Slot(int)
    @Slot(QFileInfo)
    def icon(self, icontype_or_qfileinfo):
        """Reimplement Qt method"""
        if isinstance(icontype_or_qfileinfo, QFileIconProvider.IconType):
            return super(IconProvider, self).icon(icontype_or_qfileinfo)
        else:
            qfileinfo = icontype_or_qfileinfo
            fname = osp.normpath(to_text_string(qfileinfo.absoluteFilePath()))
            if osp.isdir(fname):
                return ima.icon('DirOpenIcon')
            else:
                return ima.icon('FileIcon')


class ExplorerTreeWidget(FilteredDirView):
    """Explorer tree widget"""

    def __init__(self, parent, show_hscrollbar=True):
        FilteredDirView.__init__(self, parent)
        self.fsmodel.modelReset.connect(self.reset_icon_provider)
        self.reset_icon_provider()
        self.last_folder = None
        self.setSelectionMode(FilteredDirView.ExtendedSelection)
        self.setHeaderHidden(True)
        self.show_hscrollbar = show_hscrollbar

        # Enable drag & drop events
        self.setDragEnabled(True)
        self.setDragDropMode(FilteredDirView.DragDrop)

    #------DirView API---------------------------------------------------------
    def setup_view(self):
        """Setup view"""
        FilteredDirView.setup_view(self)

    def create_context_menu_actions(self):
        """Reimplement DirView method"""
        return FilteredDirView.create_context_menu_actions(self)

    def setup_common_actions(self):
        """Setup context menu common actions"""
        actions = FilteredDirView.setup_common_actions(self)

        # Toggle horizontal scrollbar
        hscrollbar_action = create_action(self, _("Show horizontal scrollbar"),
                                          toggled=self.toggle_hscrollbar)
        hscrollbar_action.setChecked(self.show_hscrollbar)
        self.toggle_hscrollbar(self.show_hscrollbar)

        return actions + [hscrollbar_action]

    #------Public API----------------------------------------------------------
    @Slot(bool)
    def toggle_hscrollbar(self, checked):
        """Toggle horizontal scrollbar"""
        self.parent_widget.sig_option_changed.emit('show_hscrollbar', checked)
        self.show_hscrollbar = checked
        self.header().setStretchLastSection(not checked)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        if PYQT5:
            self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        else:
            self.header().setResizeMode(QHeaderView.ResizeToContents)

    def reset_icon_provider(self):
        """Reset file system model icon provider
        The purpose of this is to refresh files/directories icons"""
        self.fsmodel.setIconProvider(IconProvider(self))

    def get_pythonpath(self):
        """Return global PYTHONPATH (for all opened projects"""
        # FIXME!!
        return []
    
    def show_properties(self, fnames):
        """Show properties"""
        pathlist = sorted(fnames)
        dirlist = [path for path in pathlist if osp.isdir(path)]
        for path in pathlist[:]:
            for folder in dirlist:
                if path != folder and path.startswith(folder):
                    pathlist.pop(pathlist.index(path))
        files, lines = 0, 0
        for path in pathlist:
            f, l = misc.count_lines(path)
            files += f
            lines += l
        QMessageBox.information(self, _("Project Explorer"),
                                _("Statistics on source files only:<br>"
                                  "(Python, Cython, IPython, Enaml,"
                                  "C/C++, Fortran)<br><br>"
                                  "<b>%s</b> files.<br>"
                                  "<b>%s</b> lines of code."
                                  ) % (str(files), str(lines)))
            
    #---- Internal drag & drop
    def dragMoveEvent(self, event):
        """Reimplement Qt method"""
        index = self.indexAt(event.pos())
        if index:
            dst = self.get_filename(index)
            if osp.isdir(dst):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Reimplement Qt method"""
        event.ignore()
        action = event.dropAction()
        if action not in (Qt.MoveAction, Qt.CopyAction):
            return
        
#        # QTreeView must not remove the source items even in MoveAction mode:
#        event.setDropAction(Qt.CopyAction)
        
        dst = self.get_filename(self.indexAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [to_text_string(url.toString())
                    for url in event.mimeData().urls()]
        if len(src_list) > 1:
            buttons = QMessageBox.Yes|QMessageBox.YesAll| \
                      QMessageBox.No|QMessageBox.NoAll|QMessageBox.Cancel
        else:
            buttons = QMessageBox.Yes|QMessageBox.No
        for src in src_list:
            if src == dst:
                continue
            dst_fname = osp.join(dst, osp.basename(src))
            if osp.exists(dst_fname):
                if yes_to_all is not None or no_to_all is not None:
                    if no_to_all:
                        continue
                elif osp.isfile(dst_fname):
                    answer = QMessageBox.warning(self, _('Project explorer'),
                              _('File <b>%s</b> already exists.<br>'
                                'Do you want to overwrite it?') % dst_fname,
                              buttons)
                    if answer == QMessageBox.No:
                        continue
                    elif answer == QMessageBox.Cancel:
                        break
                    elif answer == QMessageBox.YesAll:
                        yes_to_all = True
                    elif answer == QMessageBox.NoAll:
                        no_to_all = True
                        continue
                else:
                    QMessageBox.critical(self, _('Project explorer'),
                                         _('Folder <b>%s</b> already exists.'
                                           ) % dst_fname, QMessageBox.Ok)
                    event.setDropAction(Qt.CopyAction)
                    return
            try:
                if action == Qt.CopyAction:
                    if osp.isfile(src):
                        shutil.copy(src, dst)
                    else:
                        shutil.copytree(src, dst)
                else:
                    if osp.isfile(src):
                        misc.move_file(src, dst)
                    else:
                        shutil.move(src, dst)
                    self.parent_widget.removed.emit(src)
            except EnvironmentError as error:
                if action == Qt.CopyAction:
                    action_str = _('copy')
                else:
                    action_str = _('move')
                QMessageBox.critical(self, _("Project Explorer"),
                                     _("<b>Unable to %s <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (action_str, src,
                                            to_text_string(error)))


class ProjectExplorerWidget(QWidget):
    """Project Explorer"""
    sig_option_changed = Signal(str, object)
    sig_open_file = Signal(str)
    pythonpath_changed = Signal()

    def __init__(self, parent, name_filters=['*.py', '*.pyw'],
                 show_all=False, show_hscrollbar=True):
        QWidget.__init__(self, parent)
        self.treewidget = None
        self.setup_layout(name_filters, show_all, show_hscrollbar)
        
    def setup_layout(self, name_filters, show_all, show_hscrollbar):
        """Setup project explorer widget layout"""

        self.treewidget = ExplorerTreeWidget(self, show_hscrollbar=show_hscrollbar)
        self.treewidget.setup(name_filters=name_filters, show_all=show_all)
        self.treewidget.setup_view()

        # FIXME!!
        self.treewidget.set_root_path(osp.dirname(osp.abspath(__file__)))
        self.treewidget.set_folder_names(['variableexplorer'])
        self.treewidget.setup_project_view()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

    def check_for_io_errors(self):
        """Check for I/O errors that may occured when loading/saving 
        projects or the workspace itself and warn the user"""
        self.treewidget.check_for_io_errors()

    def closing_widget(self):
        """Perform actions before widget is closed"""
        pass

    def get_pythonpath(self):
        """Return PYTHONPATH"""
        return self.treewidget.get_pythonpath()


#==============================================================================
# Tests
#==============================================================================
class Test(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(None, show_all=True)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file.connect(self.label1.setText)
        
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.explorer.sig_option_changed.connect(
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = Test()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
