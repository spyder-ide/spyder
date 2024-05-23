# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Proxy Model."""

# Third party imports
from qtpy.QtCore import QSortFilterProxyModel, Qt


class SwitcherProxyModel(QSortFilterProxyModel):
    """A proxy model to perform sorting on the scored items."""

    def __init__(self, parent=None):
        """Proxy model to perform sorting on the scored items."""
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)
        self.__filter_by_score = False

    def set_filter_by_score(self, value):
        """
        Set whether the items should be filtered by their score result.

        Parameters
        ----------
        value : bool
           Indicates whether the items should be filtered by their
           score result.
        """
        self.__filter_by_score = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Override Qt method to filter items by their score result."""
        item = self.sourceModel().item(source_row)
        if self.__filter_by_score is False or item.is_action_item():
            return True
        else:
            return not item.get_score() == -1

    def sortBy(self, attr):
        """Override Qt method."""
        self.__sort_by = attr
        self.invalidate()
        self.sort(0, Qt.AscendingOrder)

    def lessThan(self, left, right):
        """Override Qt method."""
        left_item = self.sourceModel().itemFromIndex(left)
        right_item = self.sourceModel().itemFromIndex(right)

        # Check for attribute, otherwise, check for data
        if (
            hasattr(left_item, self.__sort_by)
            and getattr(left_item, self.__sort_by) is not None
            and hasattr(right_item, self.__sort_by)
            and getattr(right_item, self.__sort_by) is not None
        ):
            left_data = getattr(left_item, self.__sort_by)
            right_data = getattr(right_item, self.__sort_by)
            return left_data < right_data

        return super().lessThan(left, right)
