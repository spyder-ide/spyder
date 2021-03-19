# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

# Standard library imports
from __future__ import print_function

import os.path as osp
import shutil

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView,
                            QLabel, QMessageBox, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.utils import misc
from spyder.utils.qthelpers import create_action, create_plugin_layout
from spyder.plugins.explorer.widgets.explorer import FilteredDirView


class ExplorerTreeWidget(FilteredDirView):
    """Explorer tree widget"""

    sig_delete_project = Signal()

    def __init__(self, parent, show_hscrollbar=True):
        FilteredDirView.__init__(self, parent)
        self.last_folder = None
        self.setSelectionMode(FilteredDirView.ExtendedSelection)
        self.show_hscrollbar = show_hscrollbar

        # Enable drag & drop events
        self.setDragEnabled(True)
        self.setDragDropMode(FilteredDirView.DragDrop)

    #------DirView API---------------------------------------------------------
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
        try:
            self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        except:  # support for qtpy<1.2.0
            self.header().setResizeMode(QHeaderView.ResizeToContents)

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

        # QTreeView must not remove the source items even in MoveAction mode:
        # event.setDropAction(Qt.CopyAction)

        dst = self.get_filename(self.indexAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [to_text_string(url.toString())
                    for url in event.mimeData().urls()]
        if len(src_list) > 1:
            buttons = QMessageBox.Yes|QMessageBox.YesToAll| \
                      QMessageBox.No|QMessageBox.NoToAll|QMessageBox.Cancel
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
                    elif answer == QMessageBox.YesToAll:
                        yes_to_all = True
                    elif answer == QMessageBox.NoToAll:
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
    @Slot()
    def delete(self, fnames=None):
        """Delete files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            if fname == self.proxymodel.path_list[0]:
                self.sig_delete_project.emit()
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break


class ProjectExplorerWidget(QWidget):
    """Project Explorer"""
    sig_option_changed = Signal(str, object)
    sig_open_file_requested = Signal(str)

    def __init__(self, parent, name_filters=[], show_hscrollbar=True,
                 options_button=None, single_click_to_open=False):
        # TODO: Remove once Projects is Migrated
        self.CONF_SECTION = parent.CONF_SECTION
        QWidget.__init__(self, parent)

        self.name_filters = name_filters
        self.show_hscrollbar = show_hscrollbar

        self.treewidget = ExplorerTreeWidget(self, self.show_hscrollbar)
        self.treewidget.setup()
        self.treewidget.setup_view()
        self.treewidget.hide()
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)

        self.emptywidget = ExplorerTreeWidget(self)

        if options_button:
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignLeft)
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)
            layout = create_plugin_layout(btn_layout)
        else:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.emptywidget)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

    def closing_widget(self):
        """Perform actions before widget is closed"""
        pass

    def set_project_dir(self, directory):
        """Set the project directory"""
        if directory is not None:
            self.treewidget.set_root_path(osp.dirname(directory))
            self.treewidget.set_folder_names([osp.basename(directory)])
        self.treewidget.setup_project_view()
        try:
            self.treewidget.setExpanded(self.treewidget.get_index(directory),
                                        True)
        except TypeError:
            pass

    def clear(self):
        """Show an empty view"""
        self.treewidget.hide()
        self.emptywidget.show()

    def setup_project(self, directory):
        """Setup project"""
        self.emptywidget.hide()
        self.treewidget.show()

        # Setup the directory shown by the tree
        self.set_project_dir(directory)


#==============================================================================
# Tests
#==============================================================================
class ProjectExplorerTest(QWidget):
    def __init__(self, directory=None):
        QWidget.__init__(self)
        self.CONF_SECTION = 'project_explorer'
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(self)
        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))
        self.explorer.setup_project(self.directory)
        vlayout.addWidget(self.explorer)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file_requested.connect(self.label1.setText)

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
    test = ProjectExplorerTest()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
