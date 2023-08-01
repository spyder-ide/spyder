# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QEvent, Qt, Signal, Slot
from qtpy.QtWidgets import QComboBox, QMessageBox, QSizePolicy

# Local imports
from spyder.api.translations import _
from spyder.utils.encoding import to_unicode_from_fs


# ---- Constants
# ----------------------------------------------------------------------------
CWD = 0
PROJECT = 1
FILE_PATH = 2
SELECT_OTHER = 4
CLEAR_LIST = 5
EXTERNAL_PATHS = 7
MAX_PATH_HISTORY = 15


# ---- Combobox
# ----------------------------------------------------------------------------
class SearchInComboBox(QComboBox):
    """
    Non editable combo box handling the path locations of the FindOptions
    widget.
    """

    # Signals
    sig_redirect_stdio_requested = Signal(bool)

    def __init__(self, external_path_history=[], parent=None, id_=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(_('Search directory'))
        self.setEditable(False)

        self.path = ''
        self.project_path = None
        self.file_path = None
        self.external_path = None

        if id_ is not None:
            self.ID = id_

        self.addItem(_("Current working directory"))
        ttip = ("Search in all files and directories present on the current"
                " Spyder path")
        self.setItemData(0, ttip, Qt.ToolTipRole)

        self.addItem(_("Project"))
        ttip = _("Search in all files and directories present on the"
                 " current project path (if opened)")
        self.setItemData(1, ttip, Qt.ToolTipRole)
        self.model().item(1, 0).setEnabled(False)

        self.addItem(_("File").replace('&', ''))
        ttip = _("Search in current opened file")
        self.setItemData(2, ttip, Qt.ToolTipRole)

        self.insertSeparator(3)

        self.addItem(_("Select other directory"))
        ttip = _("Search in other folder present on the file system")
        self.setItemData(4, ttip, Qt.ToolTipRole)

        self.addItem(_("Clear this list"))
        ttip = _("Clear the list of other directories")
        self.setItemData(5, ttip, Qt.ToolTipRole)

        self.insertSeparator(6)

        for path in external_path_history:
            self.add_external_path(path)

        self.currentIndexChanged.connect(self.path_selection_changed)
        self.view().installEventFilter(self)

    def add_external_path(self, path):
        """
        Adds an external path to the combobox if it exists on the file system.
        If the path is already listed in the combobox, it is removed from its
        current position and added back at the end. If the maximum number of
        paths is reached, the oldest external path is removed from the list.
        """
        if not osp.exists(path):
            return
        self.removeItem(self.findText(path))
        self.addItem(path)
        self.setItemData(self.count() - 1, path, Qt.ToolTipRole)
        while self.count() > MAX_PATH_HISTORY + EXTERNAL_PATHS:
            self.removeItem(EXTERNAL_PATHS)

    def get_external_paths(self):
        """Returns a list of the external paths listed in the combobox."""
        return [str(self.itemText(i))
                for i in range(EXTERNAL_PATHS, self.count())]

    def clear_external_paths(self):
        """Remove all the external paths listed in the combobox."""
        while self.count() > EXTERNAL_PATHS:
            self.removeItem(EXTERNAL_PATHS)

    def get_current_searchpath(self):
        """
        Returns the path corresponding to the currently selected item
        in the combobox.
        """
        idx = self.currentIndex()
        if idx == CWD:
            return self.path
        elif idx == PROJECT:
            return self.project_path
        elif idx == FILE_PATH:
            return self.file_path
        else:
            return self.external_path

    def set_current_searchpath_index(self, index):
        """Set the current index of this combo box."""
        if index is not None:
            index = min(index, self.count() - 1)
            index = CWD if index in [CLEAR_LIST, SELECT_OTHER] else index
        else:
            index = CWD

        self.setCurrentIndex(index)

    def is_file_search(self):
        """Returns whether the current search path is a file."""
        if self.currentIndex() == FILE_PATH:
            return True
        else:
            return False

    @Slot()
    def path_selection_changed(self):
        """Handles when the current index of the combobox changes."""
        idx = self.currentIndex()
        if idx == SELECT_OTHER:
            external_path = self.select_directory()
            if len(external_path) > 0:
                self.add_external_path(external_path)
                self.setCurrentIndex(self.count() - 1)
            else:
                self.setCurrentIndex(CWD)
        elif idx == CLEAR_LIST:
            reply = QMessageBox.question(
                    self, _("Clear other directories"),
                    _("Do you want to clear the list of other directories?"),
                    QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.clear_external_paths()
            self.setCurrentIndex(CWD)
        elif idx >= EXTERNAL_PATHS:
            self.external_path = str(self.itemText(idx))

    @Slot()
    def select_directory(self):
        """Select directory"""
        self.sig_redirect_stdio_requested.emit(False)
        directory = getexistingdirectory(
            self,
            _("Select directory"),
            self.path,
        )
        if directory:
            directory = to_unicode_from_fs(osp.abspath(directory))

        self.sig_redirect_stdio_requested.emit(True)
        return directory

    def set_project_path(self, path):
        """
        Sets the project path and disables the project search in the combobox
        if the value of path is None.
        """
        if path is None:
            self.project_path = None
            self.model().item(PROJECT, 0).setEnabled(False)
            if self.currentIndex() == PROJECT:
                self.setCurrentIndex(CWD)
        else:
            path = osp.abspath(path)
            self.project_path = path
            self.model().item(PROJECT, 0).setEnabled(True)

    def eventFilter(self, widget, event):
        """Used to handle key events on the QListView of the combobox."""
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete:
            index = self.view().currentIndex().row()
            if index >= EXTERNAL_PATHS:
                # Remove item and update the view.
                self.removeItem(index)
                self.showPopup()
                # Set the view selection so that it doesn't bounce around.
                new_index = min(self.count() - 1, index)
                new_index = 0 if new_index < EXTERNAL_PATHS else new_index
                self.view().setCurrentIndex(self.model().index(new_index, 0))
                self.setCurrentIndex(new_index)
            return True
        return QComboBox.eventFilter(self, widget, event)
