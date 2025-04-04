# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

# Standard library imports
from functools import lru_cache
import logging
from typing import Any, Callable, Optional

# Third-party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QAbstractItemView, QActionGroup, QHeaderView, QTableWidget, QTreeView,
    QTreeWidget
)

# Local imports
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _

logger = logging.getLogger(__name__)


# Toggle mixin
class ToggleColumnMixIn(SpyderWidgetMixin):
    """
    Adds actions to a QTableView that can show/hide columns
    by right clicking on the header
    """
    def add_header_context_menu(self, checked=None, checkable=None,
                                enabled=None):
        """
        Adds the context menu from using header information

        checked can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the checked value from the dictionary.
        The corresponding column will be hidden if checked is False.

        checkable can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the checkable value from the dictionary.

        enabled can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the enabled value from the dictionary.
        """
        checked = checked if checked is not None else {}
        checkable = checkable if checkable is not None else {}
        enabled = enabled if enabled is not None else {}

        horizontal_header = self._horizontal_header()
        horizontal_header.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.toggle_column_actions_group = QActionGroup(self)
        self.toggle_column_actions_group.setExclusive(False)
        self.__toggle_functions = []  # for keeping references

        for col in range(horizontal_header.count()):
            column_label = self.model().headerData(col, Qt.Horizontal,
                                                   Qt.DisplayRole)
            logger.debug("Adding: col {}: {}".format(col, column_label))
            func = self.__make_show_column_function(col)
            is_checked = checked.get(
                column_label,
                not horizontal_header.isSectionHidden(col)
            )
            action = self.create_action(
                name=f'show_{column_label}_column',
                text=str(column_label),
                tip=_("Shows or hides the {} column").format(column_label),
                toggled=func,
                initial=is_checked,
                parent=self.toggle_column_actions_group
            )
            action.setCheckable(checkable.get(column_label, True))
            action.setEnabled(enabled.get(column_label, True))
            self.__toggle_functions.append(func)  # keep reference
            horizontal_header.addAction(action)
            horizontal_header.setSectionHidden(col, not is_checked)

    def get_header_context_menu_actions(self):
        """Returns the actions of the context menu of the header."""
        return self._horizontal_header().actions()

    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.horizontalHeader()

    def __make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.setColumnHidden(column_idx,
                                                           not checked)
        return show_column

    def read_view_settings(self, key, settings=None, reset=False):
        """
        Reads the persistent program settings

        :param reset: If True, the program resets to its default settings
        :returns: True if the header state was restored, otherwise returns
                  False
        """
        logger.debug("Reading view settings for: {}".format(key))
        header_restored = False
        # TODO: Implement settings management
#        if not reset:
#            if settings is None:
#                settings = get_qsettings()
#            horizontal_header = self._horizontal_header()
#            header_data = settings.value(key)
#            if header_data:
#                header_restored = horizontal_header.restoreState(header_data)
#
#            # update actions
#            for col, action in enumerate(horizontal_header.actions()):
#                is_checked = not horizontal_header.isSectionHidden(col)
#                action.setChecked(is_checked)

        return header_restored

    def write_view_settings(self, key, settings=None):
        """Writes the view settings to the persistent store."""
        logger.debug("Writing view settings for: {}".format(key))
#       TODO: Settings management
#        if settings is None:
#            settings = get_qsettings()
#        settings.setValue(key, self._horizontal_header().saveState())


class ToggleColumnTableWidget(QTableWidget, ToggleColumnMixIn):
    """
    A QTableWidget where right clicking on the header allows the user
    to show/hide columns.
    """
    pass


class ToggleColumnTreeWidget(QTreeWidget, ToggleColumnMixIn):
    """
    A QTreeWidget where right clicking on the header allows the user to
    show/hide columns.
    """
    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.header()


class ToggleColumnTreeView(QTreeView, ToggleColumnMixIn):
    """
    A QTreeView where right clicking on the header allows the user to
    show/hide columns.
    """
    # Dummy conf section to avoid a warning
    CONF_SECTION = ""

    def __init__(
        self,
        namespacebrowser=None,
        data_function: Optional[Callable[[], Any]] = None,
        readonly=False
    ):
        QTreeView.__init__(self)
        self.readonly = readonly
        from spyder.plugins.variableexplorer.widgets.collectionsdelegate \
            import ToggleColumnDelegate
        self.delegate = ToggleColumnDelegate(
            self, namespacebrowser, data_function
        )
        self.setItemDelegate(self.delegate)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.expanded.connect(self.resize_columns_to_contents)
        self.collapsed.connect(self.resize_columns_to_contents)

        # Dummy attribute to be compatible with BaseTableView
        self.hovered_row = -1

    @Slot()
    def resize_columns_to_contents(self):
        """Resize all the columns to its contents."""
        self._horizontal_header().resizeSections(QHeaderView.ResizeToContents)

    @lru_cache(maxsize=1)
    def selected_rows(self):
        """Dummy method to be compatible with BaseTableView."""
        return set()

    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.header()
