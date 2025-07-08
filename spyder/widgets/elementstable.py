# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Table widget to display a set of elements with title, description, icon and an
associated widget.
"""

# Standard library imports
import re
import sys
from typing import List, Optional, TypedDict

# Third-party imports
import qstylizer.style
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QAbstractItemView, QCheckBox, QHBoxLayout, QWidget
from superqt.utils import qdebounced

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.helperwidgets import (
    CustomSortFilterProxy,
    HoverRowsTableView,
    HTMLDelegate,
)


class Element(TypedDict):
    """Spec for elements that can be displayed in ElementsTable."""

    title: str
    """Element title"""

    title_color: Optional[str]
    """Color (in hex format) used for the title text (optional)"""

    description: str
    """Element description"""

    description_color: Optional[str]
    """Color (in hex format) used for the description text (optional)"""

    additional_info: Optional[str]
    """
    Additional info that needs to be displayed in a separate column (optional)
    """

    additional_info_color: Optional[str]
    """
    Color (in hex format) used for the additional info text (optional)
    """

    icon: Optional[QIcon]
    """Element icon (optional)"""

    widget: Optional[QWidget]
    """
    Element widget, e.g. a checkbox or radio button associated to the element
    (optional)
    """


class ElementsModel(QAbstractTableModel, SpyderFontsMixin):

    def __init__(
        self,
        parent: QWidget,
        elements: List[Element],
        with_description: bool,
        with_icons: bool,
        with_additional_info: bool,
        with_widgets: bool,
    ):
        QAbstractTableModel.__init__(self)

        self.elements = elements
        self.with_description = with_description
        self.with_icons = with_icons

        # Number of columns
        self.n_columns = 1

        # Index corresponding to columns. The 'title' column is always expected
        self.columns = {'title': 0}

        # Extra columns
        if with_additional_info:
            self.n_columns += 1
            self.columns['additional_info'] = 1

        if with_widgets:
            self.n_columns += 1

            if self.n_columns == 3:
                self.columns['widgets'] = 2
            else:
                self.columns['widgets'] = 1

    # ---- Qt overrides
    # -------------------------------------------------------------------------
    def data(self, index, role=Qt.DisplayRole):

        element = self.elements[index.row()]

        if role == Qt.DisplayRole:
            if index.column() == self.columns['title']:
                return self.get_title_repr(element)
            elif index.column() == self.columns.get('additional_info'):
                return self.get_info_repr(element)
            else:
                return None
        elif role == Qt.DecorationRole and self.with_icons:
            if index.column() == self.columns['title']:
                return element['icon']
            else:
                return None

        return None

    def rowCount(self, index=QModelIndex()):
        return len(self.elements)

    def columnCount(self, index=QModelIndex()):
        return self.n_columns

    # ---- Own methods
    # -------------------------------------------------------------------------
    def get_title_repr(self, element: Element) -> str:
        text_color = SpyderPalette.COLOR_TEXT_1

        if self.with_description:
            if element.get("description_color"):
                description_color = element["title_color"]
            else:
                description_color = text_color

            description = (
                f'<tr><td><span style="color:{description_color}">'
                f'{element["description"]}'
                f'</span></td></tr>'
            )
        else:
            description = ""

        title_font_size = self.get_font(
            SpyderFontType.Interface, font_size_delta=1
        ).pointSize()

        if element.get("title_color"):
            title_color = element["title_color"]
        else:
            title_color = text_color

        title_style = (
            f"color:{title_color}; font-size:{title_font_size}pt"
            if self.with_description
            else f"color:{title_color}"
        )

        return (
            f'<table cellspacing="0" cellpadding="3">'
            # Title
            f'<tr><td><span style="{title_style}">'
            f'{element["title"]}'
            f'</span></td></tr>'
            # Description
            f'{description}'
            f'</table>'
        )

    def get_info_repr(self, element: Element) -> str:
        if element.get('additional_info'):
            additional_info = f' {element["additional_info"]}'
        else:
            return ''

        if element.get("additional_info_color"):
            additional_info_style = f'color:{element["additional_info_color"]}'
        else:
            additional_info_style = f'color:{SpyderPalette.COLOR_TEXT_1}'

        return (
            f'<span style="{additional_info_style}">'
            f'{additional_info}'
            f'</span>'
        )

    def clear_elements(self):
        self.beginRemoveRows(QModelIndex(), 0, self.rowCount())
        self.elements = []
        self.endRemoveRows()

    def replace_elements(self, elements: List[Element]):
        # The -1 is necessary to add exactly the number present in `elements`
        # (including the 0 index). Otherwise, spurious rows are added by Qt.
        self.beginInsertRows(QModelIndex(), 0, len(elements) - 1)
        self.elements = elements
        self.endInsertRows()


class SortElementsFilterProxy(CustomSortFilterProxy):

    FUZZY = False

    # ---- Public API
    # -------------------------------------------------------------------------
    def filter_row(self, row_num, text=None):
        # Use the pattern set by set_filter if no text is passed. Otherwise
        # use `text` as pattern
        if text is None:
            pattern = self.pattern
        else:
            pattern = re.compile(f".*{text}.*", re.IGNORECASE)

        element = self.sourceModel().elements[row_num]

        # A title is always available
        r_title = re.search(pattern, element["title"])

        # Description and additional info are optional
        if element.get("description"):
            r_description = re.search(pattern, element["description"])
        else:
            r_description = None

        if element.get("additional_info"):
            r_additional_info = re.search(
                pattern, element["additional_info"]
            )
        else:
            r_additional_info = None

        if (
            r_title is None
            and r_description is None
            and r_additional_info is None
        ):
            return False
        else:
            return True

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def sourceModel(self) -> ElementsModel:
        # To get better code completions
        return super().sourceModel()

    def filterAcceptsRow(self, row_num: int, parent: QModelIndex) -> bool:
        if self.parent()._with_widgets:
            # We don't filter rows using this method when the table has widgets
            # because they are deleted by Qt.
            return True
        else:
            return self.filter_row(row_num)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        # left and right are indexes from the source model. So this simply
        # preserves its ordering
        row_left = left.row()
        row_right = right.row()

        if row_left > row_right:
            return True
        else:
            return False


class ElementsTable(HoverRowsTableView):

    def __init__(
        self,
        parent: Optional[QWidget],
        highlight_hovered_row: bool = True,
        add_padding_around_widgets: bool = False,
    ):
        HoverRowsTableView.__init__(self, parent, custom_delegate=True)

        # To highlight the hovered row
        self._highlight_hovered_row = highlight_hovered_row

        # To add padding around widgets. This is necessary in case widgets are
        # too small, e.g. when they are checkboxes or radiobuttons.
        self._add_padding_around_widgets = add_padding_around_widgets

        # To keep a reference to the table's elements
        self.elements: List[Element] | None = None

        # To keep track of the current row widget (e.g. a checkbox) in order to
        # change its background color when its row is hovered.
        self._current_row = -1
        self._current_row_widget = None

        # To make adjustments when the widget is shown
        self._is_shown = False

        # To use these widths where necessary
        self._info_column_width = 0
        self._widgets_column_width = 0

    # ---- Public API
    # -------------------------------------------------------------------------
    def setup_elements(
        self, elements: List[Element], set_layout: bool = False
    ):
        """Setup a list of Elements in the table."""
        self.elements = elements

        # Check for additional features
        self._with_description = self._with_feature('description')
        self._with_icons = self._with_feature('icon')
        self._with_additional_info = self._with_feature('additional_info')
        self._with_widgets = self._with_feature('widget')

        # This is used to paint the entire row's background color when its
        # hovered.
        if self._highlight_hovered_row:
            self.sig_hover_index_changed.connect(self._on_hover_index_changed)

        # Set models
        self.model = ElementsModel(
            self,
            self.elements,
            self._with_description,
            self._with_icons,
            self._with_additional_info,
            self._with_widgets
        )

        self.proxy_model = SortElementsFilterProxy(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSortRole(Qt.UserRole)
        self.setModel(self.proxy_model)

        # Adjustments for the title column
        title_delegate = HTMLDelegate(
            self,
            margin=(
                3 * AppStyle.MarginSize
                if self._with_description
                else 2 * AppStyle.MarginSize
            ),
            wrap_text=True
        )
        self.setItemDelegateForColumn(
            self.model.columns['title'], title_delegate
        )
        if self._highlight_hovered_row:
            self.sig_hover_index_changed.connect(
                 title_delegate.on_hover_index_changed
            )

        # Adjustments for the additional info column
        if self._with_additional_info:
            info_delegate = HTMLDelegate(
                self,
                margin=(
                    3 * AppStyle.MarginSize
                    if self._with_description
                    else 2 * AppStyle.MarginSize
                ),
                align_vcenter=True
            )
            self.setItemDelegateForColumn(
                self.model.columns['additional_info'], info_delegate
            )
            if self._highlight_hovered_row:
                self.sig_hover_index_changed.connect(
                     info_delegate.on_hover_index_changed
                )

            self._compute_info_column_width()

        # Adjustments for the widgets column
        if self._with_widgets:
            widgets_delegate = HTMLDelegate(self, margin=0)
            self.setItemDelegateForColumn(
                self.model.columns['widgets'], widgets_delegate
            )
            if self._highlight_hovered_row:
                self.sig_hover_index_changed.connect(
                     widgets_delegate.on_hover_index_changed
                )

            self._add_widgets()

        # Make last column take the available space to the right, if necessary
        stretch_last_column = True
        if self._with_widgets and not self._with_additional_info:
            stretch_last_column = False
        self.horizontalHeader().setStretchLastSection(stretch_last_column)

        # Hide headers
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Set icons size
        if self._with_icons:
            self.setIconSize(QSize(32, 32))

        # Hide grid to only paint horizontal lines with css
        self.setShowGrid(False)

        # Set selection behavior
        self.setSelectionMode(QAbstractItemView.NoSelection)

        # Set stylesheet
        self._set_stylesheet()

        if set_layout:
            self._set_layout()

    def replace_elements(
        self, elements: List[Element], clear_first: bool = True
    ):
        """
        Replace current elements by new ones.

        Parameters
        ----------
        elements: List[Element]
            Elements that will be replaced.
        clear_first: bool
            Whether the table should be cleared before adding the new elements
        """
        if clear_first:
            self.clear_elements()

        self.elements = elements
        self.model.replace_elements(elements)
        if self._with_widgets:
            self._add_widgets()

        self._set_layout()

    def clear_elements(self):
        """Clear all elements to leave the table empty."""
        self.model.clear_elements()
        self._current_row_widget = None

    @qdebounced(timeout=200)
    def do_find(self, text: str):
        """
        Filter rows that match `text` in their title, description or additional
        info.

        Parameters
        ----------
        text: str
            Text to filter rows with.
        """
        if self._with_widgets:
            # We need to do this when the table has widgets because it seems Qt
            # deletes all filtered rows, which deletes their widgets too. So,
            # they are unavailable to be displayed again when the filter is
            # reset.
            for i in range(len(self.elements)):
                filter_row = self.proxy_model.filter_row(i, text)
                self.setRowHidden(i, not filter_row)
        else:
            # This is probably more efficient, so we use it if there are no
            # widgets
            self.proxy_model.set_filter(text)

        self._set_layout()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _on_hover_index_changed(self, index):
        """Actions to take when the index that is hovered has changed."""
        row = self.proxy_model.mapToSource(index).row()

        if row != self._current_row:
            self._current_row = row

            if self._with_widgets:
                # Remove background color of previous row widget
                if self._current_row_widget is not None:
                    self._current_row_widget.setStyleSheet("")

                # Set background for the new row widget
                new_row_widget = self.elements[row]["row_widget"]
                new_row_widget.setStyleSheet(
                    f"background-color: {SpyderPalette.COLOR_BACKGROUND_3}"
                )

                # Set new current row widget
                self._current_row_widget = new_row_widget

    def _set_stylesheet(self, leave=False):
        """Set stylesheet when entering or leaving the widget."""
        css = qstylizer.style.StyleSheet()
        bgcolor = SpyderPalette.COLOR_BACKGROUND_1 if leave else "transparent"

        css["QTableView::item"].setValues(
            borderBottom=f"1px solid {SpyderPalette.COLOR_BACKGROUND_4}",
            paddingLeft=f"{2 * AppStyle.MarginSize}px",
            paddingRight=(
                f"{AppStyle.MarginSize + 1}px"
                if not self._add_padding_around_widgets
                else "0px"
            ),
            backgroundColor=bgcolor
        )

        self.setStyleSheet(css.toString())

    def _set_layout(self):
        """
        Set rows and columns layout.

        This is necessary to make the table look good at different sizes.
        """
        # We need to make these extra adjustments for Mac so that the last
        # column is not too close to the right border
        extra_width = 0
        if sys.platform == 'darwin':
            if self.verticalScrollBar().isVisible():
                extra_width = (
                    AppStyle.MacScrollBarWidth +
                    (15 if self._with_widgets else 5)
                )
            else:
                extra_width = 10 if self._with_widgets else 5

        # Resize title column so that the table fits into the available
        # horizontal space.
        self._compute_info_column_width()
        self._compute_widgets_column_width()
        if self._info_column_width > 0 or self._widgets_column_width > 0:
            title_column_width = (
                self.horizontalHeader().size().width() -
                (self._info_column_width + self._widgets_column_width +
                 extra_width)
            )

            self.horizontalHeader().resizeSection(
                self.model.columns['title'], title_column_width
            )

        # Resize rows. This is done because wrapping text in HTMLDelegate's
        # changes row heights in unpredictable ways.
        self.resizeRowsToContents()

    _set_layout_debounced = qdebounced(_set_layout, timeout=40)
    """
    Debounced version of _set_layout.

    Notes
    -----
    * We need a different version of _set_layout so that we can use the regular
      one in showEvent. That way users won't experience a visual glitch when
      the widget is rendered for the first time.
    * We use this version in resizeEvent, where that is not a problem.
    """

    def _with_feature(self, feature_name: str) -> bool:
        """Check if it's necessary to build the table with `feature_name`."""
        return len([e for e in self.elements if e.get(feature_name)]) > 0

    def _compute_info_column_width(self):
        if self._with_additional_info:
            # This is necessary to get the right width
            self.resizeColumnsToContents()

            self._info_column_width = self.horizontalHeader().sectionSize(
                self.model.columns['additional_info']
            )

    def _compute_widgets_column_width(self):
        if self._with_widgets:
            # This is necessary to get the right width
            self.resizeColumnsToContents()

            # We add 10 pixels to the width computed by Qt so that the widgets
            # are not so close to the right border of the table, which doesn't
            # look good.
            extra_width = 10
            if self._with_widgets and not self._with_additional_info:
                # In this case the extra width is added by the widget's
                # container layout to prevent the row separator not to end in
                # the table's right border.
                extra_width = 0

            self._widgets_column_width = (
                self.horizontalHeader().sectionSize(
                    self.model.columns["widgets"]
                )
                + extra_width
            )

    def _add_widgets(self):
        """Add element widgets to the table."""
        for i in range(len(self.elements)):
            layout = QHBoxLayout()

            if self._add_padding_around_widgets:
                layout.setContentsMargins(
                    3 * AppStyle.MarginSize,
                    3 * AppStyle.MarginSize,
                    # We add 10 pixels to the right when there's no additional
                    # info, so that the widgets are not so close to the border
                    # of the table.
                    3 * AppStyle.MarginSize
                    + (10 if not self._with_additional_info else 0),
                    3 * AppStyle.MarginSize,
                )
                layout.addWidget(self.elements[i]['widget'])
                layout.setAlignment(Qt.AlignHCenter)
            else:
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.elements[i]['widget'])

                # Widgets are the last column, so we prefer widgets to be
                # aligned to the right border of the table.
                layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            container_widget = QWidget(self)
            container_widget.setLayout(layout)

            # This key is not accounted for in Element because it's only
            # used internally, so it doesn't need to provided in a list of
            # Element's.
            self.elements[i]['row_widget'] = container_widget

            self.setIndexWidget(
                self.proxy_model.index(i, self.model.columns['widgets']),
                container_widget
            )

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        if not self._is_shown:
            if self.elements is not None:
                self._compute_widgets_column_width()
                self._set_layout()

            # To not run the adjustments above every time the widget is shown
            self._is_shown = True

        super().showEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

        # Clear background color painted on hovered row widget
        if self._current_row_widget is not None:
            self._current_row_widget.setStyleSheet('')
        self._set_stylesheet(leave=True)

    def enterEvent(self, event):
        super().enterEvent(event)

        # Restore background color that's going to be painted on hovered row
        if self._current_row_widget is not None:
            self._current_row_widget.setStyleSheet(
                f"background-color: {SpyderPalette.COLOR_BACKGROUND_3}"
            )
        self._set_stylesheet()

    def resizeEvent(self, event):
        # Notes
        # -----
        # * This is necessary to readjust the layout when the parent widget is
        #   resized.
        # * We skip this when there's a single element because the table is not
        #   rendered as expected. In that case it's necessary to call
        #   set_layout directly.
        if self.elements is not None and len(self.elements) > 1:
            self._set_layout_debounced()
        super().resizeEvent(event)


def test_elements_table():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # noqa

    elements_with_title = [
        {'title': 'IPython console', 'description': 'Execute code'},
        {'title': 'Help', 'description': 'Look for help'}
    ]

    table = ElementsTable(None, elements_with_title)
    table.show()

    elements_with_icons = [
        {'title': 'IPython console', 'description': 'Execute code',
         'icon': ima.icon('ipython_console')},
        {'title': 'Help', 'description': 'Look for help',
         'icon': ima.icon('help')}
    ]

    table_with_icons = ElementsTable(None, elements_with_icons)
    table_with_icons.show()

    elements_with_widgets = [
        {'title': 'IPython console', 'description': 'Execute code',
         'icon': ima.icon('ipython_console'), 'widget': QCheckBox()},
        {'title': 'Help', 'description': 'Look for help',
         'icon': ima.icon('help'), 'widget': QCheckBox()}
    ]

    table_with_widgets = ElementsTable(None, elements_with_widgets)
    table_with_widgets.show()

    elements_with_info = [
        {'title': 'IPython console', 'description': 'Execute code',
         'icon': ima.icon('ipython_console'), 'widget': QCheckBox(),
         'additional_info': 'Core plugin'},
        {'title': 'Help', 'description': 'Look for help',
         'icon': ima.icon('help'), 'widget': QCheckBox()}
    ]

    table_with_widgets_and_icons = ElementsTable(None, elements_with_info)
    table_with_widgets_and_icons.show()

    app.exec_()


if __name__ == '__main__':
    test_elements_table()
