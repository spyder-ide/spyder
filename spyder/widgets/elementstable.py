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
from qtpy.QtWidgets import (
    QAbstractItemView, QCheckBox, QHBoxLayout, QTableView, QWidget)

# Local imports
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.widgets.helperwidgets import HTMLDelegate


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


class ElementsTable(QTableView):

    def __init__(self, parent, elements, with_icons=False, with_widgets=False):
        QTableView.__init__(self, parent)
        self.with_widgets = with_widgets

        # Set model and item delegate.
        title_font_size = self.horizontalHeader().font().pointSize() + 1
        self.model = ElementsModel(
            self, elements, title_font_size, with_icons, with_widgets
        )
        self.setModel(self.model)
        self.setItemDelegate(HTMLDelegate(self, margin=9))

        # Adjust columns size
        self.resizeColumnsToContents()

        if with_widgets:
            # Get the width that Qt gives to the widgets column, so that we can
            # resize the text column afterwards.
            self._widget_column_width = self.horizontalHeader().sectionSize(
                ElementsTableColumns.Widgets)

        self.horizontalHeader().setStretchLastSection(True)

        # Adjust rows size
        self.resizeRowsToContents()

        # Hide headers
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Set icons size
        if with_icons:
            self.setIconSize(QSize(32, 32))

        # Hide grid to only paint horizontal lines
        self.setShowGrid(False)

        # Add widgets
        if with_widgets:
            for i in range(len(elements)):
                layout = QHBoxLayout()
                layout.addWidget(elements[i]['widget'])
                layout.setAlignment(Qt.AlignHCenter)

                container_widget = QWidget(self)
                container_widget.setLayout(layout)

                self.setIndexWidget(
                    self.model.index(i, ElementsTableColumns.Widgets),
                    container_widget
                )

        # Set selection behavior
        self.setSelectionMode(QAbstractItemView.NoSelection)

        # Set stylesheet
        self.setStyleSheet(self._stylesheet)

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()
        css["QTableView::item"].setValues(
            borderBottom=f"1px solid {QStylePalette.COLOR_BACKGROUND_4}",
        )

        return css.toString()

    def showEvent(self, event):
        # Resize text column if necessary
        if self.with_widgets:
            text_column_width = (
                self.horizontalHeader().size().width() -
                self._widget_column_width
            )

            self.horizontalHeader().resizeSection(
                ElementsTableColumns.Text, text_column_width
            )

        super().showEvent(event)


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
