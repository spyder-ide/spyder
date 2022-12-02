# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Helper widgets.
"""

# Standard imports
import re

# Third party imports
import qstylizer.style
from qtpy import PYQT5
from qtpy.QtCore import QPoint, QRegExp, QSize, QSortFilterProxyModel, Qt
from qtpy.QtGui import (QAbstractTextDocumentLayout, QColor, QFontMetrics,
                        QPainter, QRegExpValidator, QTextDocument, )
from qtpy.QtWidgets import (QApplication, QCheckBox, QLineEdit, QMessageBox,
                            QSpacerItem, QStyle, QStyledItemDelegate,
                            QStyleOptionFrame, QStyleOptionViewItem,
                            QToolButton, QToolTip, QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.stringmatching import get_search_regex
from spyder.utils.palette import QStylePalette

# Valid finder chars. To be improved
VALID_ACCENT_CHARS = "ÁÉÍOÚáéíúóàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛäëïöüÄËÏÖÜñÑ"
VALID_FINDER_CHARS = r"[A-Za-z\s{0}]".format(VALID_ACCENT_CHARS)


class HelperToolButton(QToolButton):
    """Subclasses QToolButton, to provide a simple tooltip on mousedown.
    """
    def __init__(self):
        QToolButton.__init__(self)
        self.setIcon(ima.get_std_icon('MessageBoxInformation'))
        style = """
            QToolButton {
              padding:0px;
              border-radius: 2px;
            }
            """
        self.setStyleSheet(style)

    def setToolTip(self, text):
        self._tip_text = text

    def toolTip(self):
        return self._tip_text

    def mousePressEvent(self, event):
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())),
                          self._tip_text)


class MessageCheckBox(QMessageBox):
    """
    A QMessageBox derived widget that includes a QCheckBox aligned to the right
    under the message and on top of the buttons.
    """
    def __init__(self, *args, **kwargs):
        super(MessageCheckBox, self).__init__(*args, **kwargs)

        self.setWindowModality(Qt.NonModal)
        self._checkbox = QCheckBox(self)

        # Set layout to include checkbox
        size = 9
        check_layout = QVBoxLayout()
        check_layout.addItem(QSpacerItem(size, size))
        check_layout.addWidget(self._checkbox, 0, Qt.AlignRight)
        check_layout.addItem(QSpacerItem(size, size))

        # Access the Layout of the MessageBox to add the Checkbox
        layout = self.layout()
        if PYQT5:
            layout.addLayout(check_layout, 1, 2)
        else:
            layout.addLayout(check_layout, 1, 1)

    # --- Public API
    # Methods to access the checkbox
    def is_checked(self):
        return self._checkbox.isChecked()

    def set_checked(self, value):
        return self._checkbox.setChecked(value)

    def set_check_visible(self, value):
        self._checkbox.setVisible(value)

    def is_check_visible(self):
        self._checkbox.isVisible()

    def checkbox_text(self):
        self._checkbox.text()

    def set_checkbox_text(self, text):
        self._checkbox.setText(text)


class HTMLDelegate(QStyledItemDelegate):
    """With this delegate, a QListWidgetItem or a QTableItem can render HTML.

    Taken from https://stackoverflow.com/a/5443112/2399799
    """

    def __init__(self, parent, margin=0):
        super(HTMLDelegate, self).__init__(parent)
        self._margin = margin

    def _prepare_text_document(self, option, index):
        # This logic must be shared between paint and sizeHint for consistency
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setDocumentMargin(self._margin)
        doc.setHtml(options.text)
        return options, doc

    def paint(self, painter, option, index):
        options, doc = self._prepare_text_document(option, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())
        options.text = ""

        # Note: We need to pass the options widget as an argument of
        # drawCrontol to make sure the delegate is painted with a style
        # consistent with the widget in which it is used.
        # See spyder-ide/spyder#10677.
        style.drawControl(QStyle.CE_ItemViewItem, options, painter,
                          options.widget)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        # Adjustments for the file switcher
        if hasattr(options.widget, 'files_list'):
            if style.objectName() in ['oxygen', 'qtcurve', 'breeze']:
                if options.widget.files_list:
                    painter.translate(textRect.topLeft() + QPoint(4, -9))
                else:
                    painter.translate(textRect.topLeft())
            else:
                if options.widget.files_list:
                    painter.translate(textRect.topLeft() + QPoint(4, 4))
                else:
                    painter.translate(textRect.topLeft() + QPoint(2, 4))
        else:
            painter.translate(textRect.topLeft() + QPoint(0, -3))

        # Type check: Prevent error in PySide where using
        # doc.documentLayout().draw() may fail because doc.documentLayout()
        # returns an object of type QtGui.QStandardItem (for whatever reason).
        docLayout = doc.documentLayout()
        if type(docLayout) is QAbstractTextDocumentLayout:
            docLayout.draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        __, doc = self._prepare_text_document(option, index)
        return QSize(round(doc.idealWidth()), round(doc.size().height() - 2))


class ItemDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        return QSize(doc.idealWidth(), doc.size().height())


class IconLineEdit(QLineEdit):
    """
    Custom QLineEdit that includes an icon representing a validation for its
    text and can also elide it.
    """

    def __init__(self, parent, elide_text=False, ellipsis_place=Qt.ElideLeft):
        super().__init__(parent)

        self.elide_text = elide_text
        self.ellipsis_place = ellipsis_place
        self._status = True
        self._status_set = True
        self._focus_in = False
        self._valid_icon = ima.icon('todo')
        self._invalid_icon = ima.icon('warning')
        self._set_icon = ima.icon('todo_list')
        self._refresh()
        self._paint_count = 0
        self._icon_visible = False

    def _refresh(self):
        """
        This makes space for the right validation icons after focus is given to
        the widget.
        """
        padding = self.height()
        if self.elide_text and not self._focus_in:
            padding = 0

        css = qstylizer.style.StyleSheet()
        css.QLineEdit.setValues(
            border='none',
            paddingRight=f"{padding}px"
        )

        self.setStyleSheet(css.toString())
        self.update()

    def hide_status_icon(self):
        """Show the status icon."""
        self._icon_visible = False
        self.repaint()
        self.update()

    def show_status_icon(self):
        """Hide the status icon."""
        self._icon_visible = True
        self.repaint()
        self.update()

    def update_status(self, value, value_set):
        """Update the status and set_status to update the icons to display."""
        self._status = value
        self._status_set = value_set
        self.repaint()
        self.update()

    def paintEvent(self, event):
        """
        Include a validation icon to the left of the line edit and elide text
        if requested.
        """
        # Elide text if requested.
        # See PR spyder-ide/spyder#20005 for context.
        if self.elide_text and not self._focus_in:
            # This code is taken for the most part from the
            # AmountEdit.paintEvent method, part of the Electrum project. See
            # the Electrum entry in our NOTICE.txt file for the details.
            # Licensed under the MIT license.
            painter = QPainter(self)
            option = QStyleOptionFrame()
            self.initStyleOption(option)
            text_rect = self.style().subElementRect(
                QStyle.SE_LineEditContents, option, self)
            text_rect.adjust(0, 0, -2, 0)
            fm = QFontMetrics(self.font())
            text = fm.elidedText(self.text(), self.ellipsis_place,
                                 text_rect.width())
            painter.setPen(QColor(QStylePalette.COLOR_TEXT_1))
            painter.drawText(text_rect, int(Qt.AlignLeft | Qt.AlignVCenter),
                             text)
            return

        super().paintEvent(event)
        painter = QPainter(self)
        rect = self.geometry()
        space = int((rect.height())/6)
        h = rect.height() - space
        w = rect.width() - h

        if self._icon_visible:
            if self._status and self._status_set:
                pixmap = self._set_icon.pixmap(h, h)
            elif self._status:
                pixmap = self._valid_icon.pixmap(h, h)
            else:
                pixmap = self._invalid_icon.pixmap(h, h)

            painter.drawPixmap(w, 2, pixmap)

        # Small hack to guarantee correct padding on Spyder start
        if self._paint_count < 5:
            self._paint_count += 1
            self._refresh()

    def focusInEvent(self, event):
        """Reimplemented to know when this widget has received focus."""
        self._focus_in = True
        self._refresh()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplemented to know when this widget has lost focus."""
        self._focus_in = False
        self._refresh()
        super().focusOutEvent(event)


class FinderLineEdit(QLineEdit):
    """QLineEdit for filtering listed elements in the parent widget."""

    def __init__(self, parent, callback=None, main=None,
                 regex_base=VALID_FINDER_CHARS):
        super(FinderLineEdit, self).__init__(parent)
        self._parent = parent
        self.main = main

        # Widget setup
        regex = QRegExp(regex_base + "{100}")
        self.setValidator(QRegExpValidator(regex))

        # Signals
        if callback:
            self.textChanged.connect(callback)

    def set_text(self, text):
        """Set the filter text."""
        text = text.strip()
        new_text = self.text() + text
        self.setText(new_text)

    def keyPressEvent(self, event):
        """
        Qt Override.

        The parent needs to implement the methods to handle focus on the
        next/previous row and a action over the selected element.

        This should be override.
        """
        key = event.key()
        if key in [Qt.Key_Up]:
            self._parent.previous_row()
        elif key in [Qt.Key_Down]:
            self._parent.next_row()
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            self._parent.selected_element()
        else:
            super(FinderLineEdit, self).keyPressEvent(event)


class CustomSortFilterProxy(QSortFilterProxyModel):
    """Custom column filter based on regex."""

    def __init__(self, parent=None):
        super(CustomSortFilterProxy, self).__init__(parent)
        self._parent = parent
        self.pattern = re.compile(r'')

    def set_filter(self, text):
        """Set regular expression for filter."""
        self.pattern = get_search_regex(text)
        if self.pattern and text:
            self._parent.setSortingEnabled(False)
        else:
            self._parent.setSortingEnabled(True)
        self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """Qt override.

        Reimplemented from base class to allow the use of custom filtering.
        """
        model = self.sourceModel()
        name = model.row(row_num).name
        r = re.search(self.pattern, name)

        if r is None:
            return False
        else:
            return True


def test_msgcheckbox():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    box = MessageCheckBox()
    box.setWindowTitle(_("Spyder updates"))
    box.setText("Testing checkbox")
    box.set_checkbox_text("Check for updates on startup?")
    box.setStandardButtons(QMessageBox.Ok)
    box.setDefaultButton(QMessageBox.Ok)
    box.setIcon(QMessageBox.Information)
    box.exec_()


if __name__ == '__main__':
    test_msgcheckbox()
