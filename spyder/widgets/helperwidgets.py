# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Helper widgets.
"""

# Standard imports
from __future__ import annotations
import re
import textwrap
from typing import Callable

# Third party imports
import qtawesome as qta
import qstylizer.style
from qtpy import PYQT5
from qtpy.QtCore import (
    QEvent,
    QPoint,
    QRegularExpression,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtGui import (
    QAbstractTextDocumentLayout,
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QRegularExpressionValidator,
    QTextDocument,
)
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QLineEdit,
    QMessageBox,
    QSpacerItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionFrame,
    QStyleOptionViewItem,
    QTableView,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
    QFrame,
    QItemDelegate,
)

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.widgets.mixins import SvgToScaledPixmap
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.stringmatching import get_search_regex
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle


# Valid finder chars. To be improved
VALID_ACCENT_CHARS = "ÁÉÍOÚáéíúóàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛäëïöüÄËÏÖÜñÑ"
VALID_FINDER_CHARS = r"[A-Za-z\s{0}]".format(VALID_ACCENT_CHARS)


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
    """
    With this delegate, a QListWidgetItem or a QTableItem can render HTML.

    Taken from https://stackoverflow.com/a/5443112/2399799
    """

    def __init__(self, parent, margin=0, wrap_text=False, align_vcenter=False):
        super(HTMLDelegate, self).__init__(parent)
        self._margin = margin
        self._wrap_text = wrap_text
        self._hovered_row = -1
        self._align_vcenter = align_vcenter

    def _prepare_text_document(self, option, index):
        # This logic must be shared between paint and sizeHint for consistency
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setDocumentMargin(self._margin)
        doc.setHtml(options.text)
        if self._wrap_text:
            # The -25 here is used to avoid the text to go totally up to the
            # right border of the widget that contains the delegate, which
            # doesn't look good.
            doc.setTextWidth(option.rect.width() - 25)

        return options, doc

    def on_hover_index_changed(self, index):
        """
        This can be used by a widget that inherits from HoverRowsTableView to
        connect its sig_hover_index_changed signal to this method to paint an
        entire row when it's hovered.
        """
        self._hovered_row = index.row()

    def paint(self, painter, option, index):
        options, doc = self._prepare_text_document(option, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())
        options.text = ""

        # This paints the entire row associated to the delegate when it's
        # hovered and the table that holds it informs it what's the current
        # row (see HoverRowsTableView for an example).
        if index.row() == self._hovered_row:
            painter.fillRect(
                options.rect, QColor(SpyderPalette.COLOR_BACKGROUND_3)
            )

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
            if options.widget.files_list:
                painter.translate(textRect.topLeft() + QPoint(4, 4))
            else:
                painter.translate(textRect.topLeft() + QPoint(2, 4))
        else:
            if not self._align_vcenter:
                painter.translate(textRect.topLeft() + QPoint(0, -3))

        # Center text vertically if requested.
        # Take from https://stackoverflow.com/a/32911270/438386
        if self._align_vcenter:
            doc.setTextWidth(option.rect.width())
            offset_y = (option.rect.height() - doc.size().height()) / 2
            painter.translate(options.rect.x(), options.rect.y() + offset_y)
            doc.drawContents(painter)

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

        return QSize(int(doc.idealWidth()), int(doc.size().height()))


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
            paddingLeft=f"{AppStyle.MarginSize}px",
            paddingRight=f"{padding}px",
            # This is necessary to correctly center the text
            paddingTop="0px",
            paddingBottom="0px",
            # Prevent jitter when giving focus to the line edit
            marginLeft=f"-{2 if self._focus_in else 0}px",
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
            painter.setPen(QColor(SpyderPalette.COLOR_TEXT_1))
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

            painter.drawPixmap(w, 1, pixmap)

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


class ClearLineEdit(QLineEdit):
    """QLineEdit with a clear button."""

    def __init__(self, parent, reposition_button=False):
        super().__init__(parent)

        # Add button to clear text inside the line edit.
        self.clear_action = QAction(self)
        self.clear_action.setIcon(ima.icon('clear_text'))
        self.clear_action.setToolTip(_('Clear text'))
        self.clear_action.triggered.connect(self.clear)
        self.addAction(self.clear_action, QLineEdit.TrailingPosition)

        # Button that corresponds to the clear_action above
        self.clear_button = self.findChildren(QToolButton)[0]

        # Hide clear_action by default because lineEdit is empty when the
        # combobox is created, so it doesn't make sense to show it.
        self.clear_action.setVisible(False)

        # Signals
        self.textChanged.connect(self._on_text_changed)

        # Event filter
        if reposition_button:
            self.installEventFilter(self)

    def _on_text_changed(self, text):
        """Actions to take when text has changed on the line edit widget."""
        if text:
            self.clear_action.setVisible(True)
        else:
            self.clear_action.setVisible(False)

    def eventFilter(self, widget, event):
        """
        Event filter for this widget used to reduce the space between
        clear_button and the right border of the line edit.
        """
        if event.type() == QEvent.Paint:
            self.clear_button.move(self.width() - 22, self.clear_button.y())

        return super().eventFilter(widget, event)


class FinderLineEdit(ClearLineEdit):

    sig_hide_requested = Signal()
    sig_find_requested = Signal()

    def __init__(self, parent, regex_base=None, key_filter_dict=None):
        super().__init__(parent)
        self.key_filter_dict = key_filter_dict

        self._combobox = SpyderComboBox(self)
        self._is_shown = False

        if regex_base is not None:
            # Widget setup
            regex = QRegularExpression(regex_base + "{100}")
            self.setValidator(QRegularExpressionValidator(regex))

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
            super().keyPressEvent(event)

    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            height = self._combobox.size().height()
            self._combobox.hide()

            # Only set a min width so it grows with the parent's width.
            self.setMinimumWidth(AppStyle.FindMinWidth)

            # Set a fixed height so that it looks the same as our comboboxes.
            self.setMinimumHeight(height)
            self.setMaximumHeight(height)

            self._is_shown = True

        super().showEvent(event)


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
        finder_layout.addStretch()
        finder_layout.setContentsMargins(
            2 * AppStyle.MarginSize,
            AppStyle.MarginSize,
            2 * AppStyle.MarginSize,
            0
        )
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


class PaneEmptyWidget(QFrame, SvgToScaledPixmap, SpyderFontsMixin):
    """Widget to show a pane/plugin functionality description."""

    def __init__(
        self,
        parent,
        icon_filename,
        text=None,
        description=None,
        top_stretch: int = 1,
        middle_stretch: int = 1,
        bottom_stretch: int = 0,
        spinner: bool = False,
    ):
        super().__init__(parent)

        # Attributes
        self._is_shown = False
        self._spin = None

        interface_font_size = self.get_font(
            SpyderFontType.Interface).pointSize()

        # Image (icon)
        image_label = QLabel(self)
        image_label.setPixmap(
            self.svg_to_scaled_pixmap(icon_filename, rescale=0.8)
        )
        image_label.setAlignment(Qt.AlignCenter)
        image_label_qss = qstylizer.style.StyleSheet()
        image_label_qss.QLabel.setValues(border="0px")
        image_label.setStyleSheet(image_label_qss.toString())

        # Main text
        if text is not None:
            text_label = QLabel(text, parent=self)
            text_label.setAlignment(Qt.AlignCenter)
            text_label.setWordWrap(True)
            text_label_qss = qstylizer.style.StyleSheet()
            text_label_qss.QLabel.setValues(
                fontSize=f"{interface_font_size + 5}pt", border="0px"
            )
            text_label.setStyleSheet(text_label_qss.toString())

        # Description text
        if description is not None:
            description_label = QLabel(description, parent=self)
            description_label.setAlignment(Qt.AlignCenter)
            description_label.setWordWrap(True)
            description_label_qss = qstylizer.style.StyleSheet()
            description_label_qss.QLabel.setValues(
                fontSize=f"{interface_font_size}pt",
                backgroundColor=SpyderPalette.COLOR_OCCURRENCE_3,
                border="0px",
                padding="20px",
            )
            description_label.setStyleSheet(description_label_qss.toString())

        # Setup layout
        pane_empty_layout = QVBoxLayout()

        # Add the top stretch
        pane_empty_layout.addStretch(top_stretch)

        # add the image_lebel (icon)
        pane_empty_layout.addWidget(image_label)

        # Display spinner if requested
        if spinner:
            spin_widget = qta.IconWidget()
            self._spin = qta.Spin(spin_widget, interval=3, autostart=False)
            spin_icon = qta.icon(
                "mdi.loading",
                color=ima.MAIN_FG_COLOR,
                animation=self._spin
            )

            spin_widget.setIconSize(QSize(32, 32))
            spin_widget.setIcon(spin_icon)
            spin_widget.setStyleSheet(image_label_qss.toString())
            spin_widget.setAlignment(Qt.AlignCenter)

            pane_empty_layout.addWidget(spin_widget)
            pane_empty_layout.addItem(QSpacerItem(20, 20))

        # If text, display text and stretch
        if text is not None:
            pane_empty_layout.addWidget(text_label)
            pane_empty_layout.addStretch(middle_stretch)

        # If description, display description
        if description is not None:
            pane_empty_layout.addWidget(description_label)

        pane_empty_layout.addStretch(bottom_stretch)
        pane_empty_layout.setContentsMargins(20, 0, 20, 20)
        self.setLayout(pane_empty_layout)

        # Setup border style
        self.setFocusPolicy(Qt.StrongFocus)
        self._apply_stylesheet(False)

    # ---- Public methods
    # -------------------------------------------------------------------------
    def setup(self, *args, **kwargs):
        """
        This method is needed when using this widget to show a "no connected
        console" message in plugins that inherit from ShellConnectMainWidget.
        """
        pass

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            self._start_spinner()
            self._is_shown = True

        super().showEvent(event)

    def hideEvent(self, event):
        """Adjustments when the widget is hidden."""
        self._stop_spinner()
        self._is_shown = False
        super().hideEvent(event)

    def focusInEvent(self, event):
        self._apply_stylesheet(True)
        super().focusOutEvent(event)

    def focusOutEvent(self, event):
        self._apply_stylesheet(False)
        super().focusOutEvent(event)

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _apply_stylesheet(self, focus):
        if focus:
            border_color = SpyderPalette.COLOR_ACCENT_3
        else:
            border_color = SpyderPalette.COLOR_BACKGROUND_4

        qss = qstylizer.style.StyleSheet()
        qss.QFrame.setValues(
            border=f'1px solid {border_color}',
            margin='0px',
            padding='0px',
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS
        )

        self.setStyleSheet(qss.toString())

    def _start_spinner(self):
        """
        Start spinner when requested, in case the widget has one (it's stopped
        by default).
        """
        if self._spin is not None:
            self._spin.start()

    def _stop_spinner(self):
        """Stop spinner when requested, in case the widget has one."""
        if self._spin is not None:
            self._spin.stop()


class HoverRowsTableView(QTableView):
    """QTableView subclass that can highlight an entire row when hovered."""

    sig_hover_index_changed = Signal(object)
    """
    This is emitted when the index that is currently hovered has changed.

    Parameters
    ----------
    index: object
        QModelIndex that has changed on hover.
    """

    def __init__(self, parent, custom_delegate=False):
        QTableView.__init__(self, parent)

        # For mouseMoveEvent
        self.setMouseTracking(True)

        # To remove background color for the hovered row when the mouse is not
        # over the widget.
        css = qstylizer.style.StyleSheet()
        css["QTableView::item"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_1
        )
        self._stylesheet = css.toString()

        if not custom_delegate:
            self._set_delegate()

    # ---- Qt methods
    def mouseMoveEvent(self, event):
        self._inform_hover_index_changed(event)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        self._inform_hover_index_changed(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.setStyleSheet(self._stylesheet)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.setStyleSheet("")

    # ---- Private methods
    def _inform_hover_index_changed(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            self.sig_hover_index_changed.emit(index)
            self.viewport().update()

    def _set_delegate(self):
        """
        Set a custom item delegate that can highlight the current row when
        hovered.
        """

        class HoverRowDelegate(QItemDelegate):

            def __init__(self, parent):
                super().__init__(parent)
                self._hovered_row = -1

            def on_hover_index_changed(self, index):
                self._hovered_row = index.row()

            def paint(self, painter, option, index):
                # This paints the entire row associated to the delegate when
                # it's hovered.
                if index.row() == self._hovered_row:
                    painter.fillRect(
                        option.rect, QColor(SpyderPalette.COLOR_BACKGROUND_3)
                    )

                super().paint(painter, option, index)

        self.setItemDelegate(HoverRowDelegate(self))
        self.sig_hover_index_changed.connect(
            self.itemDelegate().on_hover_index_changed
        )


class TipWidget(QLabel):
    """Icon widget to show information as a tooltip when clicked."""

    def __init__(
        self,
        tip_text: str,
        icon: QIcon,
        hover_icon: QIcon,
        size: int | None = None,
        wrap_text: bool = False
    ):
        super().__init__()

        if wrap_text:
            tip_text = '\n'.join(textwrap.wrap(tip_text, 50))
        self.tip_text = tip_text

        size = size if size is not None else AppStyle.ConfigPageIconSize
        self.icon = icon.pixmap(QSize(size, size))
        self.hover_icon = hover_icon.pixmap(QSize(size, size))

        # Timer to show the tip if users don't click on the widget
        self.tip_timer = QTimer(self)
        self.tip_timer.setInterval(300)
        self.tip_timer.setSingleShot(True)
        self.tip_timer.timeout.connect(self.show_tip)

        self.setPixmap(self.icon)
        self.setFixedWidth(size + 3)
        self.setFixedHeight(size + 3)

    def show_tip(self):
        """Show tooltip"""
        if not QToolTip.isVisible():
            QToolTip.showText(
                self.mapToGlobal(QPoint(self.width(), 15)),
                self.tip_text,
                self
            )

    def enterEvent(self, event):
        """
        Change cursor shape and set hover icon when the mouse is on the widget.
        """
        self.setCursor(Qt.PointingHandCursor)
        self.setPixmap(self.hover_icon)
        self.tip_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide tooltip and restore icon when the mouse leaves the widget."""
        QToolTip.hideText()
        self.setPixmap(self.icon)
        self.tip_timer.stop()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        """Show tooltip when the widget is clicked."""
        self.show_tip()


class ValidationLineEdit(QLineEdit):
    """Lineedit that validates its contents in focus out."""

    sig_focus_out = Signal(str)

    def __init__(
        self,
        validate_callback: Callable,
        validate_reason: str,
        text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(text, parent)

        # Attributes
        self._validate_callback = validate_callback
        self._validate_reason = validate_reason
        self._is_show = False

        # Action to signal that text is not valid
        self.error_action = QAction(self)
        self.error_action.setIcon(ima.icon("error"))
        self.addAction(self.error_action, QLineEdit.TrailingPosition)

        # Signals
        self.sig_focus_out.connect(self._validate)

    def focusOutEvent(self, event):
        if self.text():
            self.sig_focus_out.emit(self.text())
        else:
            self.error_action.setVisible(False)
        super().focusOutEvent(event)

    def focusInEvent(self, event):
        self.error_action.setVisible(False)
        super().focusInEvent(event)

    def showEvent(self, event):
        if not self._is_show:
            self.error_action.setVisible(False)
            self._is_show = True
        super().showEvent(event)

    def _validate(self, text):
        if not self._validate_callback(text):
            self.error_action.setVisible(True)
            self.error_action.setToolTip(self._validate_reason)


def test_msgcheckbox():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # noqa
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
