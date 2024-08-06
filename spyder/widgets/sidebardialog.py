# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import annotations
from typing import List, Type, Union

# Third party imports
import qstylizer.style
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QFontMetricsF, QIcon
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QListView,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget
)
from superqt.utils import qdebounced, signals_blocked

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import (
    AppStyle,
    MAC,
    PREFERENCES_TABBAR_STYLESHEET,
    WIN
)


class PageScrollArea(QScrollArea):
    """Scroll area for preference pages."""

    def widget(self):
        """Return the page widget inside the scroll area."""
        return super().widget().page


class SidebarPage(QWidget):
    """Base class for pages used in SidebarDialog's"""

    # Signals
    show_this_page = Signal()

    # Constants
    MAX_WIDTH = 620
    MIN_HEIGHT = 550

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        # Set dimensions
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

    def initialize(self):
        """Initialize page."""
        self.setup_page()

    def get_name(self):
        """Return page name."""
        raise NotImplementedError

    def get_icon(self):
        """Return page icon."""
        QIcon()

    def setup_page(self):
        """Setup widget to be shown in the page."""
        raise NotImplementedError

    @staticmethod
    def create_icon(name):
        """Create an icon by name using Spyder's icon manager."""
        return ima.icon(name)

    def sizeHint(self):
        """Default page size."""
        return QSize(self.MAX_WIDTH, self.MIN_HEIGHT)


class SidebarDialog(QDialog, SpyderFontsMixin):
    """Sidebar dialog."""

    # Constants
    ITEMS_MARGIN = 2 * AppStyle.MarginSize
    ITEMS_PADDING = (
        AppStyle.MarginSize if (MAC or WIN) else 2 * AppStyle.MarginSize
    )
    CONTENTS_WIDTH = 230 if MAC else (200 if WIN else 240)
    ICON_SIZE = 20
    PAGES_MINIMUM_WIDTH = 600

    # To be set by childs
    TITLE = ""
    ICON = QIcon()
    MIN_WIDTH = 800
    MIN_HEIGHT = 600
    PAGE_CLASSES: List[Type[SidebarPage]] = []

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        # ---- Attributes
        self.items_font = self.get_font(
            SpyderFontType.Interface, font_size_delta=1
        )
        self._is_shown = False
        self._separators = []
        self._active_pages = {}

        # ---- Size
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        # ---- Widgets
        self.pages_widget = QStackedWidget(self)
        self.contents_widget = QListWidget(self)
        buttons_box, buttons_layout = self.create_buttons()

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(self.TITLE)
        self.setWindowIcon(self.ICON)

        # ---- Widgets setup
        self.pages_widget.setMinimumWidth(self.PAGES_MINIMUM_WIDTH)

        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(3)
        self.contents_widget.setCurrentRow(0)
        self.contents_widget.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.contents_widget.setFixedWidth(self.CONTENTS_WIDTH)

        # Don't show horizontal scrollbar because it doesn't look good. Instead
        # we show tooltips if the text doesn't fit in contents_widget width.
        self.contents_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        # ---- Layout
        contents_and_pages_layout = QGridLayout()
        contents_and_pages_layout.addWidget(self.contents_widget, 0, 0)
        contents_and_pages_layout.addWidget(self.pages_widget, 0, 1)
        contents_and_pages_layout.setContentsMargins(0, 0, 0, 0)
        contents_and_pages_layout.setColumnStretch(0, 1)
        contents_and_pages_layout.setColumnStretch(1, 3)
        contents_and_pages_layout.setHorizontalSpacing(0)

        layout = QVBoxLayout()
        layout.addLayout(contents_and_pages_layout)
        layout.addSpacing(
            - (2 * AppStyle.MarginSize) if MAC else AppStyle.MarginSize
        )
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # ---- Stylesheet
        self.setStyleSheet(self._main_stylesheet)

        self._contents_css = self._generate_contents_stylesheet()
        self.contents_widget.setStyleSheet(self._contents_css.toString())

        self.contents_widget.verticalScrollBar().setStyleSheet(
            self._contents_scrollbar_stylesheet
        )

        # ---- Signals and slots
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
            self.pages_widget.setCurrentIndex)
        buttons_box.accepted.connect(self.accept)
        buttons_box.rejected.connect(self.reject)
        buttons_box.clicked.connect(self.button_clicked)

        # Add pages to the dialog
        self._add_pages()

        # Set index to the initial page
        if self.PAGE_CLASSES:
            self.set_current_index(0)

    # ---- Public API to be overridden by children
    # -------------------------------------------------------------------------
    def button_clicked(self, button):
        """Actions to perform after one of the dialog's buttons is clicked."""
        pass

    def current_page_changed(self, index):
        """Actions to perform after the current page in the dialog changes."""
        pass

    def create_buttons(self):
        """
        Create the buttons that will be displayed in the dialog.

        Override this method if you want different buttons in it.
        """
        bbox = SpyderDialogButtonBox(QDialogButtonBox.Ok)

        layout = QHBoxLayout()
        layout.addWidget(bbox)

        return bbox, layout

    # ---- Public API
    # -------------------------------------------------------------------------
    def get_current_index(self):
        """Return current page index"""
        return self.contents_widget.currentRow()

    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)

    def get_item(self, index: int | None = None) -> QListWidgetItem:
        """Get item on the left panel corresponding to `index`."""
        if index is None:
            index = self.get_current_index()
        return self.contents_widget.item(index)

    def get_page(
        self, index: int | None = None
    ) -> Union[QWidget, SidebarPage] | None:
        """Return page widget on the right panel corresponding to `index`."""
        if index is None:
            page = self.pages_widget.currentWidget()
        else:
            page = self.pages_widget.widget(index)

        # Not all pages are config pages (e.g. separators have a simple QWidget
        # as their config page). So, we need to check for this.
        if page and hasattr(page, 'widget'):
            return page.widget()

    def hide_page(self, index=None):
        """Hide page corresponding to `index`."""
        if index is None:
            index = self.get_current_index()
        self._active_pages[index] = False

        # Hide entry from contents_widget
        self.contents_widget.item(index).setHidden(True)

        # If the current page is not the first one (index=0), then we set as
        # the new current one the first active page before it.
        if index > 1:
            # With this we move backwards from index-1 up to 0 until we find
            # an active page.
            for i in range(index - 1, -1, -1):
                if self._active_pages.get(i):
                    self.set_current_index(i)
                    break
        elif index == 1:
            # If the current page is the second one, we set the first one as
            # current.
            self.set_current_index(0)

    def add_separator(self):
        """Add a horizontal line to separate different sections."""
        # Solution taken from https://stackoverflow.com/a/24819554/438386
        item = QListWidgetItem(self.contents_widget)
        item.setFlags(Qt.NoItemFlags)

        size = (
            AppStyle.MarginSize * 3 if (MAC or WIN)
            else AppStyle.MarginSize * 5
        )
        item.setSizeHint(QSize(size, size))

        hline = QFrame(self.contents_widget)
        hline.setFrameShape(QFrame.HLine)
        hline.setStyleSheet(self._separators_stylesheet)
        self.contents_widget.setItemWidget(item, hline)

        # This is necessary to keep in sync the contents_widget and
        # pages_widget indexes.
        self.pages_widget.addWidget(QWidget(self))

        # Save separators to perform certain operations only on them
        self._separators.append(hline)

    def add_page(self, page: SidebarPage, initialize: bool = True):
        """Add page instance to the dialog."""
        if initialize:
            page.initialize()

        page.show_this_page.connect(lambda row=self.contents_widget.count():
                                    self.contents_widget.setCurrentRow(row))

        # Container widget so that we can center the page
        layout = QHBoxLayout()
        layout.addWidget(page)
        layout.setAlignment(Qt.AlignHCenter)

        # The smaller margin to the right is necessary to compensate for the
        # space added by the vertical scrollbar
        layout.setContentsMargins(27, 27, 15, 27)

        container = QWidget(self)
        container.setLayout(layout)
        container.page = page

        # Add container to a scroll area in case the page contents don't fit
        # in the dialog
        scrollarea = PageScrollArea(self)
        scrollarea.setObjectName('sidebardialog-scrollarea')
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(container)
        self.pages_widget.addWidget(scrollarea)

        # Add plugin entry item to contents widget
        item = QListWidgetItem(self.contents_widget)
        item.setText(page.get_name())
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        # In case the page doesn't have an icon
        try:
            item.setIcon(page.get_icon())
        except TypeError:
            pass

        # Set font for items
        item.setFont(self.items_font)

        # Save which pages are active in case we need to hide some
        self._active_pages[self.contents_widget.count() - 1] = True

    def number_of_pages(self):
        """Get the number of pages in the dialog."""
        return self.pages_widget.count()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            self._add_tooltips()
            self._adjust_items_margin()

            self._is_shown = True

        super().showEvent(event)

        # This is necessary to paint the separators as expected when there
        # are elided items in contents_widget.
        with signals_blocked(self):
            height = self.height()
            self.resize(self.width(), height + 1)
            self.resize(self.width(), height - 1)

    def resizeEvent(self, event):
        """
        Reimplement Qt method to perform several operations when resizing.
        """
        QDialog.resizeEvent(self, event)
        self._on_resize_event()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _add_tooltips(self):
        """
        Check if it's necessary to add tooltips to the contents_widget items.
        """
        contents_width = self.contents_widget.width()
        metrics = QFontMetricsF(self.items_font)

        for i in range(self.contents_widget.count()):
            item = self.contents_widget.item(i)

            # Item width
            item_width = self.contents_widget.visualItemRect(item).width()

            # Set tooltip
            if item_width >= contents_width:
                item.setToolTip(item.text())
            else:
                # This covers the case when item_width is too close to
                # contents_width without the scrollbar being visible, which
                # can't be detected by Qt with the check above.
                scrollbar = self.contents_widget.verticalScrollBar()

                if scrollbar.isVisible():
                    if MAC:
                        # This is a crude heuristic to detect if we need to add
                        # tooltips on Mac. However, it's the best we can do
                        # (the approach for other OSes below ends up adding
                        # tooltips to all items) and it works for all our
                        # localized languages.
                        text_width = metrics.boundingRect(item.text()).width()
                        if text_width + 70 > item_width - 5:
                            item.setToolTip(item.text())
                    else:
                        if item_width > (contents_width - scrollbar.width()):
                            item.setToolTip(item.text())

    def _adjust_items_margin(self):
        """
        Adjust margins of contents_widget items depending on if its vertical
        scrollbar is visible.

        Notes
        -----
        We need to do this only in Mac because Qt doesn't account for the
        scrollbar width in most widgets.
        """
        if MAC:
            scrollbar = self.contents_widget.verticalScrollBar()
            extra_margin = (
                AppStyle.MacScrollBarWidth if scrollbar.isVisible() else 0
            )
            item_margin = (
                f'0px {self.ITEMS_MARGIN + extra_margin}px '
                f'0px {self.ITEMS_MARGIN}px'
            )

            self._contents_css['QListView::item'].setValues(
                margin=item_margin
            )

            self.contents_widget.setStyleSheet(self._contents_css.toString())

    def _adjust_separators_width(self):
        """
        Adjust the width of separators present in contents_widget depending on
        if its vertical scrollbar is visible.

        Notes
        -----
        We need to do this only in Mac because Qt doesn't set the widths
        correctly when there are elided items.
        """
        if MAC:
            scrollbar = self.contents_widget.verticalScrollBar()
            for sep in self._separators:
                if self.CONTENTS_WIDTH != 230:
                    raise ValueError(
                        "The values used here for the separators' width were "
                        "the ones reported by Qt for a contents_widget width "
                        "of 230px. Since this value changed, you need to "
                        "update them."
                    )

                # These are the values reported by Qt when CONTENTS_WIDTH = 230
                # and the interface language is English.
                if scrollbar.isVisible():
                    sep.setFixedWidth(188)
                else:
                    sep.setFixedWidth(204)

    @property
    def _main_stylesheet(self):
        """Main style for this widget."""
        # Use the preferences tabbar stylesheet as the base one and extend it.
        tabs_stylesheet = PREFERENCES_TABBAR_STYLESHEET.get_copy()
        css = tabs_stylesheet.get_stylesheet()

        # Remove border of all scroll areas for pages
        css['QScrollArea#sidebardialog-scrollarea'].setValues(
            border='0px',
        )

        # Add more spacing between QGroupBoxes than normal.
        css.QGroupBox.setValues(
            marginBottom='15px',
        )

        # Substract extra padding
        css["QToolTip"].setValues(
            paddingRight="-2px",
        )

        # Substract extra padding that comes from QLineEdit
        css["QLineEdit QToolTip"].setValues(
            padding="-2px -3px",
        )

        # This is necessary to correctly show disabled buttons in this kind of
        # dialogs (oddly QDarkstyle doesn't set this color as expected).
        css["QPushButton:disabled"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_4,
        )

        css["QPushButton:checked:disabled"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_6,
        )

        return css.toString()

    def _generate_contents_stylesheet(self):
        """Generate stylesheet for the contents widget"""
        css = qstylizer.style.StyleSheet()

        # This also sets the background color of the vertical scrollbar
        # associated to this widget
        css.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_2
        )

        # Main style
        css.QListView.setValues(
            padding=f'{self.ITEMS_MARGIN}px 0px',
            border=f'1px solid {SpyderPalette.COLOR_BACKGROUND_2}',
        )

        # Remove border color on focus
        css['QListView:focus'].setValues(
            border=f'1px solid {SpyderPalette.COLOR_BACKGROUND_2}',
        )

        # Add margin and padding for items
        css['QListView::item'].setValues(
            padding=f'{self.ITEMS_PADDING}px',
            margin=f'0px {self.ITEMS_MARGIN}px'
        )

        # Set border radius and background color for hover, active and inactive
        # states of items
        css['QListView::item:hover'].setValues(
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
        )

        for state in ['item:selected:active', 'item:selected:!active']:
            css[f'QListView::{state}'].setValues(
                borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
                backgroundColor=SpyderPalette.COLOR_BACKGROUND_4
            )

        return css

    @property
    def _contents_scrollbar_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # Give border a darker color to stand out over the background
        css.setValues(
            border=f"1px solid {SpyderPalette.COLOR_BACKGROUND_5}"
        )

        return css.toString()

    @property
    def _separators_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # This makes separators stand out better over the background
        css.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_5
        )

        return css.toString()

    @qdebounced(timeout=40)
    def _on_resize_event(self):
        """Method to run when Qt emits a resize event."""
        self._add_tooltips()
        self._adjust_items_margin()
        self._adjust_separators_width()

    def _add_pages(self):
        """Add pages to the dialog."""
        for PageClass in self.PAGE_CLASSES:
            page = PageClass(self)
            self.add_page(page)
