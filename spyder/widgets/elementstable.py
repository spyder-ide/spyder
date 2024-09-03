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
from spyder.widgets.helperwidgets import HoverRowsTableView, HTMLDelegate


class Element(TypedDict):
    """Spec for elements that can be displayed in ElementsTable."""

    title: str
    """Element title"""

    description: str
    """Element description"""

    additional_info: Optional[str]
    """
    Additional info that needs to be displayed in a separate column (optional)
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
        with_icons: bool,
        with_addtional_info: bool,
        with_widgets: bool,
    ):
        QAbstractTableModel.__init__(self)

        self.elements = elements
        self.with_icons = with_icons

        # Number of columns
        self.n_columns = 1

        # Index corresponding to columns. The 'title' column is always expected
        self.columns = {'title': 0}

        # Extra columns
        if with_addtional_info:
            self.n_columns += 1
            self.columns['additional_info'] = 1

        if with_widgets:
            self.n_columns += 1

            if self.n_columns == 3:
                self.columns['widgets'] = 2
            else:
                self.columns['widgets'] = 1

        # Text styles
        text_color = SpyderPalette.COLOR_TEXT_1
        title_font_size = self.get_font(
            SpyderFontType.Interface, font_size_delta=1).pointSize()

        self.title_style = f'color:{text_color}; font-size:{title_font_size}pt'
        self.additional_info_style = f'color:{SpyderPalette.COLOR_TEXT_4}'
        self.description_style = f'color:{text_color}'

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
        return (
            f'<table cellspacing="0" cellpadding="3">'
            # Title
            f'<tr><td><span style="{self.title_style}">'
            f'{element["title"]}'
            f'</span></td></tr>'
            # Description
            f'<tr><td><span style="{self.description_style}">'
            f'{element["description"]}'
            f'</span></td></tr>'
            f'</table>'
        )

    def get_info_repr(self, element: Element) -> str:
        if element.get('additional_info'):
            additional_info = f' {element["additional_info"]}'
        else:
            return ''

        return (
            f'<span style="{self.additional_info_style}">'
            f'{additional_info}'
            f'</span>'
        )


class ElementsTable(HoverRowsTableView):

    def __init__(self, parent: Optional[QWidget], elements: List[Element]):
        HoverRowsTableView.__init__(self, parent, custom_delegate=True)
        self.elements = elements

        # Check for additional features
        self._with_icons = self._with_feature('icon')
        self._with_addtional_info = self._with_feature('additional_info')
        self._with_widgets = self._with_feature('widget')

        # To keep track of the current row widget (e.g. a checkbox) in order to
        # change its background color when its row is hovered.
        self._current_row = -1
        self._current_row_widget = None

        # To make adjustments when the widget is shown
        self._is_shown = False

        # This is used to paint the entire row's background color when its
        # hovered.
        self.sig_hover_index_changed.connect(self._on_hover_index_changed)

        # Set model
        self.model = ElementsModel(
            self,
            self.elements,
            self._with_icons,
            self._with_addtional_info,
            self._with_widgets
        )
        self.setModel(self.model)

        # Adjustments for the title column
        title_delegate = HTMLDelegate(self, margin=9, wrap_text=True)
        self.setItemDelegateForColumn(
            self.model.columns['title'], title_delegate)
        self.sig_hover_index_changed.connect(
             title_delegate.on_hover_index_changed)

        # Adjustments for the additional info column
        self._info_column_width = 0
        if self._with_addtional_info:
            info_delegate = HTMLDelegate(self, margin=10, align_vcenter=True)
            self.setItemDelegateForColumn(
                self.model.columns['additional_info'], info_delegate)
            self.sig_hover_index_changed.connect(
                 info_delegate.on_hover_index_changed)

            # This is necessary to get this column's width below
            self.resizeColumnsToContents()

            self._info_column_width = self.horizontalHeader().sectionSize(
                self.model.columns['additional_info'])

        # Adjustments for the widgets column
        self._widgets_column_width = 0
        if self._with_widgets:
            widgets_delegate = HTMLDelegate(self, margin=0)
            self.setItemDelegateForColumn(
                self.model.columns['widgets'], widgets_delegate)
            self.sig_hover_index_changed.connect(
                 widgets_delegate.on_hover_index_changed)

            # This is necessary to get this column's width below
            self.resizeColumnsToContents()

            # Note: We add 15 pixels to the Qt width so that the widgets are
            # not so close to the right border of the table, which doesn't look
            # good.
            self._widgets_column_width = self.horizontalHeader().sectionSize(
                self.model.columns['widgets']) + 15

            # Add widgets
            for i in range(len(self.elements)):
                layout = QHBoxLayout()
                layout.addWidget(self.elements[i]['widget'])
                layout.setAlignment(Qt.AlignHCenter)

                container_widget = QWidget(self)
                container_widget.setLayout(layout)

                # This key is not accounted for in Element because it's only
                # used internally, so it doesn't need to provided in a list of
                # Element's.
                self.elements[i]['row_widget'] = container_widget

                self.setIndexWidget(
                    self.model.index(i, self.model.columns['widgets']),
                    container_widget
                )

        # Make last column take the available space to the right
        self.horizontalHeader().setStretchLastSection(True)

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

    # ---- Private API
    # -------------------------------------------------------------------------
    def _on_hover_index_changed(self, index):
        """Actions to take when the index that is hovered has changed."""
        row = index.row()

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
            paddingLeft="5px",
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

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        if not self._is_shown:
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
        # This is necessary to readjust the layout when the parent widget is
        # resized.
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
