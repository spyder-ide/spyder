# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder combobox widgets.

Use these widgets for any combobox you want to add to Spyder.
"""

# Standard library imports
import sys

# Third-party imports
import qstylizer.style
from qtpy import PYQT5, PYQT6
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QColor, QPainter, QFontMetrics
from qtpy.QtWidgets import (
    QComboBox,
    QFontComboBox,
    QFrame,
    QLineEdit,
    QListView,
    QProxyStyle,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionFrame,
)
from superqt.utils import qdebounced

# Local imports
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, WIN


class _SpyderComboBoxProxyStyle(QProxyStyle):
    """Style proxy to adjust qdarkstyle issues."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ComboBox_Popup:
            # Disable combobox popup top & bottom areas.
            # See spyder-ide/spyder#9682.
            # Taken from https://stackoverflow.com/a/21019371
            return 0

        return QProxyStyle.styleHint(self, hint, option, widget, returnData)


class _SpyderComboBoxDelegate(QStyledItemDelegate):
    """
    Delegate to make separators color follow our theme.

    Adapted from https://stackoverflow.com/a/33464045/438386
    """

    def __init__(self, parent, elide_mode=None):
        super().__init__(parent)
        self._elide_mode = elide_mode

    def paint(self, painter, option, index):
        data = index.data(Qt.AccessibleDescriptionRole)
        if data and data == "separator":
            painter.setPen(QColor(SpyderPalette.COLOR_BACKGROUND_6))
            painter.drawLine(
                option.rect.left() + AppStyle.MarginSize,
                option.rect.center().y(),
                option.rect.right() - AppStyle.MarginSize,
                option.rect.center().y()
            )
            return

        if self._elide_mode is not None:
            option.textElideMode = self._elide_mode

        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        data = index.data(Qt.AccessibleDescriptionRole)
        if data and data == "separator":
            return QSize(0, 3 * AppStyle.MarginSize)

        return super().sizeHint(option, index)


class _SpyderComboBoxLineEdit(QLineEdit):
    """Lineedit used for comboboxes."""

    sig_mouse_clicked = Signal()

    def __init__(self, parent, editable, elide_mode=None):
        super().__init__(parent)
        self._editable = editable
        self._elide_mode = elide_mode
        self._focus_in = False

        # Fix style issues
        css = qstylizer.style.StyleSheet()
        css.QLineEdit.setValues(
            # These are necessary on Windows to prevent some ugly visual
            # glitches.
            backgroundColor="transparent",
            border="none",
            padding="0px",
            # Make text look centered for short comboboxes
            paddingRight=f"-{3 if WIN else 2}px"
        )

        self.setStyleSheet(css.toString())

    def mouseReleaseEvent(self, event):
        if not self._editable:
            # Emit a signal to display the popup afterwards
            self.sig_mouse_clicked.emit()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self._editable:
            # Avoid selecting the lineedit text with double clicks
            pass
        else:
            super().mouseDoubleClickEvent(event)

    def focusInEvent(self, event):
        self._focus_in = True
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._focus_in = False
        super().focusOutEvent(event)

    def paintEvent(self, event):
        if self._elide_mode is not None and not self._focus_in:
            # This code is taken for the most part from the
            # AmountEdit.paintEvent method, part of the Electrum project. See
            # the Electrum entry in our NOTICE.txt file for the details.
            # Licensed under the MIT license.
            painter = QPainter(self)
            option = QStyleOptionFrame()
            self.initStyleOption(option)

            text_rect = self.style().subElementRect(
                QStyle.SE_LineEditContents, option, self
            )

            # Neded so the text is placed correctly according to our style
            text_rect.adjust(2, 0, 0, 0)

            fm = QFontMetrics(self.font())
            text = fm.elidedText(
                self.text(), self._elide_mode, text_rect.width()
            )

            color = (
                SpyderPalette.COLOR_TEXT_1
                if self.isEnabled()
                else SpyderPalette.COLOR_DISABLED
            )
            painter.setPen(QColor(color))
            painter.drawText(
                text_rect, int(Qt.AlignLeft | Qt.AlignVCenter), text
            )

            return

        super().paintEvent(event)


class _SpyderComboBoxView(QListView):
    """Listview used for comboboxes"""

    sig_current_item_changed = Signal(object)

    def currentChanged(self, current, previous):
        # This covers selecting a different item with the keyboard or when
        # hovering with the mouse over the list.
        self.sig_current_item_changed.emit(current)
        super().currentChanged(current, previous)


class _SpyderComboBoxMixin:
    """Mixin with the basic style and functionality for our comboboxes."""

    sig_item_in_popup_changed = Signal(str)
    """
    This signal is emitted when an item in the combobox popup (i.e. dropdown)
    has changed.

    Parameters
    ----------
    item: str
        Item text
    """

    sig_popup_is_hidden = Signal()
    """
    This signal is emitted when the combobox popup (i.e. dropdown) is hidden.
    """

    def __init__(self):

        # Style
        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

        style = _SpyderComboBoxProxyStyle(None)
        style.setParent(self)
        self.setStyle(style)

        # Report when the current item in the dropdown has changed
        view = _SpyderComboBoxView(self)
        view.sig_current_item_changed.connect(self._on_item_changed)
        self.setView(view)

    def contextMenuEvent(self, event):
        # Prevent showing context menu for editable comboboxes because it's
        # added automatically by Qt. That means the menu is not built using our
        # API and it's not localized.
        pass

    @qdebounced(timeout=100)
    def _on_item_changed(self, index):
        if index.isValid():
            self.sig_item_in_popup_changed.emit(index.data())

    def _generate_stylesheet(self):
        """Base stylesheet for Spyder comboboxes."""
        css = qstylizer.style.StyleSheet()

        # Make our comboboxes have a uniform height
        css.QComboBox.setValues(
            minHeight=f'{AppStyle.ComboBoxMinHeight}em'
        )

        # Add top and bottom padding to the inner contents of comboboxes
        css["QComboBox QAbstractItemView"].setValues(
            paddingTop=f"{AppStyle.MarginSize + 1}px",
            paddingBottom=f"{AppStyle.MarginSize + 1}px"
        )

        # Add margin and padding to combobox items
        css["QComboBox QAbstractItemView::item"].setValues(
            marginLeft=f"{AppStyle.MarginSize}px",
            marginRight=f"{AppStyle.MarginSize}px",
            padding=f"{AppStyle.MarginSize}px"
        )

        # Make color of hovered combobox items match the one used in other
        # Spyder widgets
        css["QComboBox QAbstractItemView::item:selected:active"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_3,
        )

        return css


class SpyderComboBox(QComboBox, _SpyderComboBoxMixin):
    """Default combobox widget for Spyder."""

    def __init__(self, parent=None, items_elide_mode=None):
        """
        Default combobox widget for Spyder.

        Parameters
        ----------
        parent: QWidget, optional
            The combobox parent.
        items_elide_mode: Qt.TextElideMode, optional
            Elide mode for the combobox items.
        """
        if PYQT5 or PYQT6:
            super().__init__(parent)
        else:
            QComboBox.__init__(self, parent)
            _SpyderComboBoxMixin.__init__(self)

        self.is_editable = None
        self._is_shown = False
        self._is_popup_shown = False

        # This is necessary to have more fine-grained control over the style of
        # our comboboxes with css, e.g. to add more padding between its items.
        # See https://stackoverflow.com/a/33464045/438386 for the details.
        self.setItemDelegate(
            _SpyderComboBoxDelegate(self, elide_mode=items_elide_mode)
        )

    def showEvent(self, event):
        """Adjustments when the widget is shown."""

        if not self._is_shown:
            if not self.isEditable():
                self.is_editable = False
                self.setLineEdit(_SpyderComboBoxLineEdit(self, editable=False))

                # This is necessary to make Qt position the popup widget below
                # the combobox for non-editable ones.
                # Solution from https://stackoverflow.com/a/45191141/438386
                self.setEditable(True)
                self.lineEdit().setReadOnly(True)

                # Show popup when the lineEdit is clicked, which is the default
                # behavior for non-editable comboboxes in Qt.
                self.lineEdit().sig_mouse_clicked.connect(self.showPopup)
            else:
                self.is_editable = True

            self._is_shown = True

        super().showEvent(event)

    def showPopup(self):
        """Adjustments when the popup is shown."""
        super().showPopup()

        if sys.platform == "darwin":
            # Reposition popup to display it in the right place.
            # Solution from https://forum.qt.io/post/349517
            popup = self.findChild(QFrame)
            popup.move(popup.x() - 3, popup.y() + 4)

            # Adjust width to match the lineEdit one.
            if not self._is_popup_shown:
                popup.setFixedWidth(popup.width() + 2)
                self._is_popup_shown = True
        else:
            # Make borders straight to make popup feel as part of the combobox.
            # This doesn't work reliably on Mac.
            self._css.QComboBox.setValues(
                borderBottomLeftRadius="0px",
                borderBottomRightRadius="0px",
            )

            self.setStyleSheet(self._css.toString())

    def hidePopup(self):
        """Adjustments when the popup is hidden."""
        super().hidePopup()
        self.sig_popup_is_hidden.emit()

        if not sys.platform == "darwin":
            # Make borders rounded when popup is not visible. This doesn't work
            # reliably on Mac.
            self._css.QComboBox.setValues(
                borderBottomLeftRadius=SpyderPalette.SIZE_BORDER_RADIUS,
                borderBottomRightRadius=SpyderPalette.SIZE_BORDER_RADIUS,
            )

            self.setStyleSheet(self._css.toString())


class SpyderComboBoxWithIcons(SpyderComboBox):
    """"Combobox widget for Spyder when its items have icons."""

    def __init__(self, parent=None, items_elide_mode=None):
        """"
        Combobox widget for Spyder when its items have icons.

        Parameters
        ----------
        parent: QWidget, optional
            The combobox parent.
        items_elide_mode: Qt.TextElideMode, optional
            Elide mode for the combobox items.
        """
        super().__init__(parent, items_elide_mode)

        # Padding is not necessary because icons give items enough of it.
        self._css["QComboBox QAbstractItemView::item"].setValues(
            padding="0px"
        )

        self.setStyleSheet(self._css.toString())


class SpyderFontComboBox(QFontComboBox, _SpyderComboBoxMixin):

    def __init__(self, parent=None):
        if PYQT5 or PYQT6:
            super().__init__(parent)
        else:
            QFontComboBox.__init__(self, parent)
            _SpyderComboBoxMixin.__init__(self)

        # Avoid font name eliding because it confuses users.
        # Fixes spyder-ide/spyder#22683
        self.setItemDelegate(
            _SpyderComboBoxDelegate(self, elide_mode=Qt.ElideNone)
        )

        # Elide selected font name in case it's too long
        self.setLineEdit(
            _SpyderComboBoxLineEdit(
                self, editable=True, elide_mode=Qt.ElideMiddle
            )
        )

        # Adjust popup width to contents.
        self.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )

    def showPopup(self):
        """Adjustments when the popup is shown."""
        super().showPopup()

        if sys.platform == "darwin":
            popup = self.findChild(QFrame)
            popup.move(popup.x() - 3, popup.y() + 4)

    def hidePopup(self):
        super().hidePopup()
        self.sig_popup_is_hidden.emit()
