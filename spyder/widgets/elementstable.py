# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Table widget to display a set of elements with title, description, icon and an
associated widget.
"""

# Third-party imports
import qstylizer.style
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt
from qtpy.QtWidgets import QAbstractItemView, QCheckBox, QHBoxLayout, QWidget

# Local imports
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.widgets.helperwidgets import HoverRowsTableView, HTMLDelegate


class ElementsTableColumns:
    Text = 0
    Widgets = 1


class ElementsModel(QAbstractTableModel):

    def __init__(self, parent, elements, title_font_size, with_icons,
                 with_widgets):
        QAbstractTableModel.__init__(self)

        self.elements = elements
        self.with_icons = with_icons
        self.with_widgets = with_widgets

        text_color = QStylePalette.COLOR_TEXT_1
        self.title_style = f'color:{text_color}; font-size:{title_font_size}pt'
        self.description_style = f'color:{text_color}'

    # ---- Qt overrides
    # -------------------------------------------------------------------------
    def data(self, index, role=Qt.DisplayRole):

        element = self.elements[index.row()]

        if role == Qt.DisplayRole:
            if self.with_widgets:
                if index.column() == ElementsTableColumns.Text:
                    return self.get_html_representation(element)
            else:
                return self.get_html_representation(element)
        elif role == Qt.DecorationRole and self.with_icons:
            if self.with_widgets:
                if index.column() == ElementsTableColumns.Text:
                    return element['icon']
            else:
                return element['icon']

        return None

    def rowCount(self, index=QModelIndex()):
        return len(self.elements)

    def columnCount(self, index=QModelIndex()):
        if self.with_widgets:
            return 2
        else:
            return 1

    # ---- Own methods
    # -------------------------------------------------------------------------
    def get_html_representation(self, element):
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


class ElementsTable(HoverRowsTableView):

    def __init__(self, parent, elements, with_icons=False, with_widgets=False):
        HoverRowsTableView.__init__(self, parent)

        self.elements = elements
        self.with_widgets = with_widgets

        # To keep track of the current row widget (e.g. a checkbox) in order to
        # change its background color when its row is hovered.
        self._current_row = -1
        self._current_row_widget = None

        # To do adjustments when the widget is shown only once
        self._is_shown = False

        # Set model and item delegate.
        title_font_size = self.horizontalHeader().font().pointSize() + 1
        self.model = ElementsModel(
            self, elements, title_font_size, with_icons, with_widgets
        )
        self.setModel(self.model)
        self.setItemDelegate(HTMLDelegate(self, margin=9, wrap_text=True))

        # To paint the entire row's background color when its hovered.
        if with_widgets:
            self.sig_hover_index_changed.connect(self._on_hover_index_changed)
            self.sig_hover_index_changed.connect(
                self.itemDelegate().on_hover_index_changed
            )

        if with_widgets:
            # Adjust columns size. This is necessary for the next step
            self.resizeColumnsToContents()

            # Get the width that Qt gives to the widgets column, so that we can
            # resize the text column afterwards by substracting this value from
            # the horizontal header width.
            # Note: We add 15 pixels to the Qt width so that the widgets are
            # not so close to the right border of the table, which doesn't look
            # good.
            self._widget_column_width = self.horizontalHeader().sectionSize(
                ElementsTableColumns.Widgets) + 15

        self.horizontalHeader().setStretchLastSection(True)

        # Hide headers
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Set icons size
        if with_icons:
            self.setIconSize(QSize(32, 32))

        # Hide grid to only paint horizontal lines with css
        self.setShowGrid(False)

        # Add widgets
        if with_widgets:
            for i in range(len(elements)):
                layout = QHBoxLayout()
                layout.addWidget(elements[i]['widget'])
                layout.setAlignment(Qt.AlignHCenter)

                container_widget = QWidget(self)
                container_widget.setLayout(layout)
                elements[i]['row_widget'] = container_widget

                self.setIndexWidget(
                    self.model.index(i, ElementsTableColumns.Widgets),
                    container_widget
                )

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

            # Remove background color of previous row widget
            if self._current_row_widget is not None:
                self._current_row_widget.setStyleSheet("")

            # Set background for the new row widget
            new_row_widget = self.elements[row]["row_widget"]
            new_row_widget.setStyleSheet(
                f"background-color: {QStylePalette.COLOR_BACKGROUND_3}"
            )

            # Set new current row widget
            self._current_row_widget = new_row_widget

    def _set_stylesheet(self, leave=False):
        """Set stylesheet when entering or leaving the widget."""
        css = qstylizer.style.StyleSheet()
        bgcolor = QStylePalette.COLOR_BACKGROUND_1 if leave else "transparent"

        css["QTableView::item"].setValues(
            borderBottom=f"1px solid {QStylePalette.COLOR_BACKGROUND_4}",
            paddingLeft="5px",
            backgroundColor=bgcolor
        )

        self.setStyleSheet(css.toString())

    def _adjust_columns_and_rows_size(self):
        """
        This is necessary to make the table look good at different sizes.
        """
        # Resize text column so that the widgets one always has the same width
        if self.with_widgets:
            text_column_width = (
                self.horizontalHeader().size().width() -
                self._widget_column_width
            )

            self.horizontalHeader().resizeSection(
                ElementsTableColumns.Text, text_column_width
            )

        # Resize rows. This is done because wrapping text in HTMLDelegate
        # changes row heights in unpredictable ways.
        self.resizeRowsToContents()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        if not self._is_shown:
            self._adjust_columns_and_rows_size()

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
                f"background-color: {QStylePalette.COLOR_BACKGROUND_3}"
            )
        self._set_stylesheet()

    def resizeEvent(self, event):
        self._adjust_columns_and_rows_size()
        super().resizeEvent(event)


def test_elements_table():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # noqa

    elements = [
        {'title': 'IPython console', 'description': 'Execute code',
         'icon': ima.icon('ipython_console'), 'widget': QCheckBox()},
        {'title': 'Help', 'description': 'Look for help',
         'icon': ima.icon('help'), 'widget': QCheckBox()}
    ]

    table = ElementsTable(None, elements)
    table.show()

    table_with_icons = ElementsTable(None, elements, with_icons=True)
    table_with_icons.show()

    table_with_widgets = ElementsTable(None, elements, with_widgets=True)
    table_with_widgets.show()

    table_with_widgets_and_icons = ElementsTable(
        None, elements, with_icons=True, with_widgets=True)
    table_with_widgets_and_icons.show()

    app.exec_()


if __name__ == '__main__':
    test_elements_table()
