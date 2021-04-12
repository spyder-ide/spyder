# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Layout Plugin API.
"""

# Standard libray imports
import copy

# Third party imports
from qtpy.QtCore import QRectF, Qt
from qtpy.QtWidgets import (QGridLayout, QPlainTextEdit, QWidget)

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation


# Localization
_ = get_translation("spyder")


class BaseGridLayoutType:
    """
    A base layout type to create custom layouts for Spyder panes.

    The API for this plugin is a subset of a QGridLayout, so the same
    concepts, like row, column, spans and stretches apply.

    Notes
    -----
    See: https://doc.qt.io/qt-5/qgridlayout.html
    """

    ID = None
    """Unique string identifier for the layout."""

    def __init__(self, parent_plugin):
        self.plugin = parent_plugin
        self._plugin = parent_plugin
        self._areas = []
        self._area_rects = []
        self._column_stretchs = {}
        self._row_stretchs = {}
        self._default_added = False
        self._default_area = None
        self._visible_areas = []
        self._rows = 0
        self._cols = 0
        self._plugin_ids = []

    # --- Private API
    # ------------------------------------------------------------------------
    def _check_layout_validity(self):
        """
        Check the current layout is a valid one.
        """
        self._visible_areas = []
        # Check ID
        if self.ID is None:
            raise SpyderAPIError("A Layout must define an `ID` class "
                                 "attribute!")

        # Check name
        self.get_name()

        # All layouts need to add at least 1 area
        if not self._areas:
            raise SpyderAPIError("A Layout must define add least one area!")

        default_areas = []
        area_zero_zero = False

        for area in self._areas:
            default_areas.append(area["default"])
            if area["default"]:
                self._default_area = area

            self._visible_areas.append(area["visible"])

            if area_zero_zero and area["row"] == 0 and area["column"] == 0:
                raise SpyderAPIError(
                    "Multiple areas defined their row and column as 0!")

            if area["row"] == 0 and area["column"] == 0:
                area_zero_zero = True

            if not set(area["hidden_plugin_ids"]) <= set(area["plugin_ids"]):
                raise SpyderAPIError(
                    "At least 1 hidden plugin id is not being specified "
                    "in the area plugin ids list!\n SpyderLayout: {}\n "
                    "hidden_plugin_ids: {}\n"
                    "plugin_ids: {}".format(self.get_name(),
                                            area["hidden_plugin_ids"],
                                            area["plugin_ids"]))

        # Check that there is at least 1 visible!
        if not any(self._visible_areas):
            raise SpyderAPIError("At least 1 area must be `visible`")

        # Check that there is only 1 `default` area!
        if not any(default_areas):
            raise SpyderAPIError("Only 1 area can be the `default`!")

        # Check one area has row zero and column zero
        if not area_zero_zero:
            raise SpyderAPIError(
                "1 area needs to be specified with row 0 and column 0!")

        # Check Area
        self._check_area()

    def _check_area(self):
        """
        Check if the current layout added areas cover the entire rectangle.

        Rectangle given by the extreme points for the added areas.
        """
        self._area_rects = []
        height = self._rows + 1
        area_float_rects = []
        delta = 0.0001
        for index, area in enumerate(self._areas):
            # These areas are used with a small delta to ensure if they are
            # next to each other they will not overlap.
            rectf = QRectF()
            rectf.setLeft(area["column"] + delta)
            rectf.setRight(area["column"] + area["col_span"] - delta)
            rectf.setTop(height - area["row"] - delta)
            rectf.setBottom(height - area["row"] - area["row_span"] + delta)
            rectf.index = index
            rectf.plugin_ids = area["plugin_ids"]
            area_float_rects.append(rectf)

            # These areas are used to calculate the actual total area
            rect = QRectF()
            rect.setLeft(area["column"])
            rect.setRight(area["column"] + area["col_span"])
            rect.setTop(height - area["row"])
            rect.setBottom(height - area["row"] - area["row_span"])
            rect.index = index
            rect.plugin_ids = area["plugin_ids"]

            self._area_rects.append(rect)

        # Check if areas are overlapping!
        for rect_1 in area_float_rects:
            for rect_2 in area_float_rects:
                if rect_1.index != rect_2.index:
                    if rect_1.intersects(rect_2):
                        raise SpyderAPIError(
                            "Area with plugins {0} is overlapping area "
                            "with plugins {1}".format(rect_1.plugin_ids,
                                                      rect_2.plugin_ids))

        # Check the total area (using corner points) versus the sum of areas
        total_area = 0
        tops = []
        rights = []
        for index, rect in enumerate(self._area_rects):
            tops.append(rect.top())
            rights.append(rect.right())
            area = abs(rect.width() * rect.height())
            total_area += area
            self._areas[index]["area"] = area

        if total_area != max(rights)*max(tops):
            raise SpyderAPIError(
                "Areas are not covering the entire section!\n"
                "Either an area is missing or col_span/row_span are "
                "not correctly set!"
            )

    # --- SpyderGridLayout API
    # ------------------------------------------------------------------------
    def get_name(self):
        """
        Return the layout localized name.

        Returns
        -------
        str
            Localized name of the layout.

        Notes
        -----
        This is a method to be able to update localization without a restart.
        """
        raise NotImplementedError("A layout must define a `get_name` method!")

    # --- Public API
    # ------------------------------------------------------------------------
    def add_area(self,
                 plugin_ids,
                 row,
                 column,
                 row_span=1,
                 col_span=1,
                 default=False,
                 visible=True,
                 hidden_plugin_ids=[]):
        """
        Add a new area and `plugin_ids` that will populate it to the layout.

        The area will start at row, column spanning row_pan rows and
        column_span columns.

        Parameters
        ----------
        plugin_ids: list
            List of plugin ids that will be in the area
        row: int
            Initial row where the area starts
        column: int
            Initial column where the area starts
        row_span: int, optional
            Number of rows that the area covers
        col_span: int, optional
            Number of columns the area covers
        default: bool, optiona
            Defines an area as the default one, i.e all other plugins that where
            not passed in the `plugins_ids` will be added to the default area.
            By default is False.
        visible: bool, optional
            Defines if the area is visible when setting up the layout.
            Default is True.

        Notes
        -----
        See: https://doc.qt.io/qt-5/qgridlayout.html
        """
        if self._default_added and default:
            raise SpyderAPIError("A default location has already been "
                                 "defined!")

        self._plugin_ids += plugin_ids
        self._rows = max(row, self._rows)
        self._cols = max(column, self._cols)
        self._default_added = default
        self._column_stretchs[column] = 1
        self._row_stretchs[row] = 1
        self._areas.append(
            dict(
                plugin_ids=plugin_ids,
                row=row,
                column=column,
                row_span=row_span,
                col_span=col_span,
                default=default,
                visible=visible,
                hidden_plugin_ids=hidden_plugin_ids,
            )
        )

    def set_column_stretch(self, column, stretch):
        """
        Set the factor of column to stretch.

        The stretch factor is relative to the other columns in this grid.
        Columns with a higher stretch factor take more of the available space.

        Parameters
        ----------
        column: int
            The column number. The first column is number 0.
        stretch: int
            Column stretch factor.

        Notes
        -----
        See: https://doc.qt.io/qt-5/qgridlayout.html
        """
        self._column_stretchs[column] = stretch

    def set_row_stretch(self, row, stretch):
        """
        Set the factor of row to stretch.

        The stretch factor is relative to the other rows in this grid.
        Rows with a higher stretch factor take more of the available space.

        Parameters
        ----------
        row: int
            The row number. The first row is number 0.
        stretch: int
            Row stretch factor.

        Notes
        -----
        See: https://doc.qt.io/qt-5/qgridlayout.html
        """
        self._row_stretchs[row] = stretch

    def preview_layout(self, show_hidden_areas=False):
        """
        Show the layout with placeholder texts using a QWidget.
        """
        from spyder.utils.qthelpers import qapplication

        app = qapplication()
        widget = QWidget()
        layout = QGridLayout()
        for area in self._areas:
            label = QPlainTextEdit()
            label.setReadOnly(True)
            label.setPlainText("\n".join(area["plugin_ids"]))
            if area["visible"] or show_hidden_areas:
                layout.addWidget(
                    label,
                    area["row"],
                    area["column"],
                    area["row_span"],
                    area["col_span"],
                )

            # label.setVisible(area["visible"])
            if area["default"]:
                label.setStyleSheet(
                    "QPlainTextEdit {background-color: #ff0000;}")

            if not area["visible"]:
                label.setStyleSheet(
                    "QPlainTextEdit {background-color: #eeeeee;}")

        for row, stretch in self._row_stretchs.items():
            layout.setRowStretch(row, stretch)

        for col, stretch in self._column_stretchs.items():
            layout.setColumnStretch(col, stretch)

        widget.setLayout(layout)
        widget.showMaximized()
        app.exec_()

    def set_main_window_layout(self, main_window, dockable_plugins):
        """
        Set the given mainwindow layout.

        First validate the current layout definition, then clear the mainwindow
        current layout and finally calculate and set the new layout.
        """

        # Define plugins assigned to areas, all the available plugins and
        # initial docks for each area
        all_plugin_ids = []

        # Before applying a new layout all plugins need to be hidden
        for plugin in dockable_plugins:
            all_plugin_ids.append(plugin.NAME)
            plugin.toggle_view(False)

        # Add plugins without an area assigned to the default area and made
        # them hidden. Deep copy needed since test can run multiple times with
        # the same Mainwindow instance when using the 'main_window' fixture
        patched_default_area = copy.deepcopy(self._default_area)
        unassgined_plugin_ids = list(
            set(self._plugin_ids) ^ set(all_plugin_ids))
        patched_default_area["plugin_ids"] += unassgined_plugin_ids
        patched_default_area["hidden_plugin_ids"] += unassgined_plugin_ids

        patched_areas = [
            patched_default_area if area["default"] else area
            for area in self._areas]

        # Define initial dock for each area
        docks = {}
        for area in patched_areas:
            current_area = area
            plugin_id = current_area["plugin_ids"][0]
            plugin = main_window.get_plugin(plugin_id, error=False)
            if plugin:
                dock = plugin.dockwidget
                docks[(current_area["row"], current_area["column"])] = dock
                dock.area = area["area"]
                dock.col_span = area["col_span"]
                dock.row_span = area["row_span"]
                plugin.toggle_view(area["visible"])

        # Define base layout (distribution of dockwidgets
        # following defined areas)
        layout_data = []

        # Find dock splits in the horizontal direction
        direction = Qt.Horizontal
        for row in range(0, self._rows + 1):
            dock = None
            for col in range(0, self._cols + 1):
                key = (row, col)
                if key in docks:
                    if dock is None:
                        dock = docks[key]
                    else:
                        layout_data.append(
                            (1/docks[key].area,
                             key,
                             dock,
                             docks[key],
                             direction))
                        dock = docks[key]

                    main_window.addDockWidget(
                        Qt.LeftDockWidgetArea, dock, direction)

        # Find dock splits in the vertical direction
        direction = Qt.Vertical
        for col in range(0, self._cols + 1):
            dock = None
            for row in range(0, self._rows + 1):
                key = (row, col)
                if key in docks:
                    if dock is None:
                        dock = docks[key]
                    else:
                        layout_data.append(
                            (1/docks[key].area,
                             key,
                             dock,
                             docks[key],
                             direction))
                        dock = docks[key]

        # We sort based on the inverse of the area, then the row and then
        # the column. This allows to make the dock splits in the right order.
        sorted_data = sorted(layout_data, key=lambda x: (x[0], x[1]))
        for area, key, first, second, direction in sorted_data:
            main_window.splitDockWidget(first, second, direction)

        plugins_to_tabify = []
        for area in patched_areas:
            area_visible = area["visible"]
            base_plugin = main_window.get_plugin(
                area["plugin_ids"][0], error=False)
            if base_plugin:
                plugin_ids = area["plugin_ids"][1:]
                hidden_plugin_ids = area["hidden_plugin_ids"]
                for plugin_id in plugin_ids:
                    current_plugin = main_window.get_plugin(
                        plugin_id, error=False)
                    if current_plugin:
                        if (plugin_id in unassgined_plugin_ids and
                                hasattr(current_plugin, 'TABIFY')):
                            plugins_to_tabify.append(
                                (current_plugin, base_plugin))
                        else:
                            main_window.tabify_plugins(
                                base_plugin, current_plugin)
                            if plugin_id not in hidden_plugin_ids:
                                current_plugin.toggle_view(area_visible)
                            else:
                                current_plugin.toggle_view(False)

                # Raise front widget per area
                if area["visible"]:
                    base_plugin.dockwidget.show()
                    base_plugin.dockwidget.raise_()

        # try to use the TABIFY attribute to add the plugin to the layout.
        # Otherwise use the default area base plugin
        for plugin, base_plugin in plugins_to_tabify:
            if not main_window.tabify_plugin(plugin):
                main_window.tabify_plugins(base_plugin, plugin)
            current_plugin.toggle_view(False)

        column_docks = []
        column_stretches = []
        for key, dock in docks.items():
            for col, stretch in self._column_stretchs.items():
                if key[1] == col and dock.col_span == 1:
                    column_docks.append(dock)
                    column_stretches.append(stretch)

        row_docks = []
        row_stretches = []
        for key, dock in docks.items():
            for row, stretch in self._row_stretchs.items():
                if key[0] == row and dock.row_span == 1:
                    row_docks.append(dock)
                    row_stretches.append(stretch)

        main_window.showMaximized()
        main_window.resizeDocks(column_docks, column_stretches, Qt.Horizontal)
        main_window.resizeDocks(row_docks, row_stretches, Qt.Vertical)
