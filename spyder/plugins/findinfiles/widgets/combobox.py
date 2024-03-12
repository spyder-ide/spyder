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
from qtpy.QtWidgets import QMessageBox, QSizePolicy

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.utils.encoding import to_unicode_from_fs


# ---- Constants
# ----------------------------------------------------------------------------
class SearchInComboBoxItems:
    Cwd = 0
    Project = 1
    File = 2
    FirstSeparator = 3
    SelectAnotherDirectory = 4
    ClearList = 5
    SecondSeparator = 6
    ExternalPaths = 7

MAX_PATH_HISTORY = 15


# ---- Combobox
# ----------------------------------------------------------------------------
class SearchInComboBox(SpyderComboBox):
    """
    Non editable combo box handling the path locations of the FindOptions
    widget.
    """

    # Signals
    sig_redirect_stdio_requested = Signal(bool)

    def __init__(self, external_path_history=[], parent=None, id_=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setEditable(False)

        self.path = ''
        self.project_path = ''
        self.file_path = ''
        self.external_path = ''

        if id_ is not None:
            self.ID = id_

        self.addItem(_("Current working directory"))

        self.addItem(_("Project"))
        self.model().item(SearchInComboBoxItems.Project, 0).setEnabled(False)

        self.addItem(_("Current file").replace('&', ''))

        self.insertSeparator(SearchInComboBoxItems.FirstSeparator)

        self.addItem(_("Select another directory"))
        self.addItem(_("Clear the list of other directories"))

        self.insertSeparator(SearchInComboBoxItems.SecondSeparator)

        if external_path_history:
            for path in external_path_history:
                self.add_external_path(path)
        else:
            self.set_state_other_dirs_items(False)

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
        self.set_state_other_dirs_items(True)
        self.removeItem(self.findText(path))
        self.addItem(path)
        self.setItemData(self.count() - 1, path, Qt.ToolTipRole)

        while (
            self.count() >
            (MAX_PATH_HISTORY + SearchInComboBoxItems.ExternalPaths)
        ):
            self.removeItem(SearchInComboBoxItems.ExternalPaths)

    def get_external_paths(self):
        """Returns a list of the external paths listed in the combobox."""
        return [
            str(self.itemText(i))
            for i in range(SearchInComboBoxItems.ExternalPaths, self.count())
        ]

    def clear_external_paths(self):
        """Remove all the external paths listed in the combobox."""
        while self.count() > SearchInComboBoxItems.ExternalPaths:
            self.removeItem(SearchInComboBoxItems.ExternalPaths)
        self.set_state_other_dirs_items(False)

    def get_current_searchpath(self):
        """
        Returns the path corresponding to the currently selected item
        in the combobox.
        """
        idx = self.currentIndex()
        if idx == SearchInComboBoxItems.Cwd:
            return self.path
        elif idx == SearchInComboBoxItems.Project:
            return self.project_path
        elif idx == SearchInComboBoxItems.File:
            return self.file_path
        else:
            return self.external_path

    def set_current_searchpath_index(self, index):
        """Set the current index of this combo box."""
        if index is not None:
            index = min(index, self.count() - 1)
            if index in [SearchInComboBoxItems.ClearList,
                         SearchInComboBoxItems.SelectAnotherDirectory]:
                index = SearchInComboBoxItems.Cwd
        else:
            index = SearchInComboBoxItems.Cwd

        self.setCurrentIndex(index)

    def is_file_search(self):
        """Returns whether the current search path is a file."""
        if self.currentIndex() == SearchInComboBoxItems.File:
            return True
        else:
            return False

    @Slot()
    def path_selection_changed(self):
        """Handles when the current index of the combobox changes."""
        idx = self.currentIndex()
        if idx == SearchInComboBoxItems.SelectAnotherDirectory:
            external_path = self.select_directory()
            if len(external_path) > 0:
                self.add_external_path(external_path)
                self.setCurrentIndex(self.count() - 1)
            else:
                self.setCurrentIndex(SearchInComboBoxItems.Cwd)
        elif idx == SearchInComboBoxItems.ClearList:
            reply = QMessageBox.question(
                    self, _("Clear other directories"),
                    _("Do you want to clear the list of other directories?"),
                    QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.clear_external_paths()
            self.setCurrentIndex(SearchInComboBoxItems.Cwd)
        elif idx >= SearchInComboBoxItems.ExternalPaths:
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
            self.project_path = ''
            self.model().item(
                SearchInComboBoxItems.Project, 0
            ).setEnabled(False)
            if self.currentIndex() == SearchInComboBoxItems.Project:
                self.setCurrentIndex(SearchInComboBoxItems.Cwd)
        else:
            path = osp.abspath(path)
            self.project_path = path
            self.model().item(
                SearchInComboBoxItems.Project, 0
            ).setEnabled(True)

    def set_state_other_dirs_items(self, enabled):
        """
        Set the enabled/visible state of items that change when other
        directories are added/removed to/from the combobox.
        """
        # The second separator needs to be visible only when the user has added
        # other directories.
        self.view().setRowHidden(
            SearchInComboBoxItems.SecondSeparator, not enabled
        )

        # The ClearList item needs to be disabled if the user has not added
        # other directories
        self.model().item(
            SearchInComboBoxItems.ClearList, 0
        ).setEnabled(enabled)

    def eventFilter(self, widget, event):
        """Used to handle key events on the QListView of the combobox."""
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete:
            index = self.view().currentIndex().row()
            if index >= SearchInComboBoxItems.ExternalPaths:
                # Remove item and update the view.
                self.removeItem(index)
                self.showPopup()

                # Set the view selection so that it doesn't bounce around.
                new_index = min(self.count() - 1, index)
                if new_index < SearchInComboBoxItems.ExternalPaths:
                    new_index = SearchInComboBoxItems.Cwd
                    self.set_state_other_dirs_items(False)
                    self.hidePopup()

                self.view().setCurrentIndex(self.model().index(new_index, 0))
                self.setCurrentIndex(new_index)

            return True

        return super().eventFilter(widget, event)
