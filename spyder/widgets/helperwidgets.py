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
from qtpy.QtCore import (
    QPoint, QRegExp, QSize, QSortFilterProxyModel, Qt, Signal)
from qtpy.QtGui import (QAbstractTextDocumentLayout, QColor, QFontMetrics,
                        QPainter, QRegExpValidator, QTextDocument, QPixmap)
from qtpy.QtWidgets import (QApplication, QCheckBox, QLineEdit, QMessageBox,
                            QSpacerItem, QStyle, QStyledItemDelegate,
                            QStyleOptionFrame, QStyleOptionViewItem,
                            QToolButton, QToolTip, QVBoxLayout,
                            QWidget, QHBoxLayout, QLabel, QFrame)

# Local imports
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.stringmatching import get_search_regex
from spyder.utils.palette import QStylePalette, SpyderPalette
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.stylesheet import DialogStyle

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
    sig_hide_requested = Signal()
    sig_find_requested = Signal()

    def __init__(self, parent, regex_base=None, key_filter_dict=None):
        super(FinderLineEdit, self).__init__(parent)
        self.key_filter_dict = key_filter_dict

        if regex_base is not None:
            # Widget setup
            regex = QRegExp(regex_base + "{100}")
            self.setValidator(QRegExpValidator(regex))

    def keyPressEvent(self, event):
        """Qt and FilterLineEdit Override."""
        key = event.key()
        if self.key_filter_dict is not None and key in self.key_filter_dict:
            self.key_filter_dict[key]()
        elif key in [Qt.Key_Escape]:
            self.sig_hide_requested.emit()
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            self.sig_find_requested.emit()
        else:
            super(FinderLineEdit, self).keyPressEvent(event)


class FinderWidget(QWidget):
    sig_find_text = Signal(str)
    sig_hide_finder_requested = Signal()

    def __init__(self, parent, regex_base=None, key_filter_dict=None,
                 find_on_change=False):
        super().__init__(parent)
        # Parent is assumed to be a spyder widget
        self.text_finder = FinderLineEdit(
            self,
            regex_base=regex_base,
            key_filter_dict=key_filter_dict
        )
        self.text_finder.sig_find_requested.connect(self.do_find)
        if find_on_change:
            self.text_finder.textChanged.connect(self.do_find)
        self.text_finder.sig_hide_requested.connect(
            self.sig_hide_finder_requested)

        self.finder_close_button = QToolButton(self)
        self.finder_close_button.setIcon(ima.icon('DialogCloseButton'))
        self.finder_close_button.clicked.connect(
            self.sig_hide_finder_requested)

        finder_layout = QHBoxLayout()
        finder_layout.addWidget(self.finder_close_button)
        finder_layout.addWidget(self.text_finder)
        finder_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(finder_layout)
        self.setVisible(False)

    def do_find(self):
        """Send text."""
        text = self.text_finder.text()
        if not text:
            text = ''
        self.sig_find_text.emit(text)

    def set_visible(self, visible):
        """Set visibility of widget."""
        self.setVisible(visible)
        if visible:
            self.text_finder.setFocus()
            self.do_find()
        else:
            self.sig_find_text.emit("")


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


class PaneEmptyWidget(QFrame):
    """Widget to show a pane/plugin functionality description."""

    def __init__(self, parent, icon_filename, text, description):
        super().__init__(parent)
        # Image
        image_path = get_image_path(icon_filename)
        image = QPixmap(image_path)
        image_height = int(image.height() * 0.8)
        image_width = int(image.width() * 0.8)
        image = image.scaled(
            image_width, image_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        image_label = QLabel(self)
        image_label.setPixmap(image)
        image_label.setAlignment(Qt.AlignCenter)
        image_label_qss = qstylizer.style.StyleSheet()
        image_label_qss.QLabel.setValues(border="0px")
        image_label.setStyleSheet(image_label_qss.toString())

        # Main text
        text_label = QLabel(text, parent=self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label_qss = qstylizer.style.StyleSheet()
        text_label_qss.QLabel.setValues(
            fontSize=DialogStyle.ContentFontSize,
            border="0px"
        )
        text_label.setStyleSheet(text_label_qss.toString())

        # Description text
        description_label = QLabel(description, parent=self)
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)
        description_label_qss = qstylizer.style.StyleSheet()
        description_label_qss.QLabel.setValues(
            fontSize="10pt",
            backgroundColor=SpyderPalette.COLOR_OCCURRENCE_3,
            border="0px",
            padding="20px"
        )
        description_label.setStyleSheet(description_label_qss.toString())

        # Setup layout
        pane_empty_layout = QVBoxLayout()
        pane_empty_layout.addStretch(1)
        pane_empty_layout.addWidget(image_label)
        pane_empty_layout.addWidget(text_label)
        pane_empty_layout.addWidget(description_label)
        pane_empty_layout.addStretch(2)
        pane_empty_layout.setContentsMargins(10, 0, 10, 8)
        self.setLayout(pane_empty_layout)

        # Setup border style
        self.setFocusPolicy(Qt.StrongFocus)
        self._apply_stylesheet(False)

    def focusInEvent(self, event):
        self._apply_stylesheet(True)
        super().focusOutEvent(event)

    def focusOutEvent(self, event):
        self._apply_stylesheet(False)
        super().focusOutEvent(event)

    def _apply_stylesheet(self, focus):
        if focus:
            border_color = QStylePalette.COLOR_ACCENT_3
        else:
            border_color = QStylePalette.COLOR_BACKGROUND_4

        qss = qstylizer.style.StyleSheet()
        qss.QFrame.setValues(
            border=f'1px solid {border_color}',
            margin='5px 1px 0px 1px',
            padding='0px 0px 1px 0px',
            borderRadius='3px'
        )

        self.setStyleSheet(qss.toString())


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
