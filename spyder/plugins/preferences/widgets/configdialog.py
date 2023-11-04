# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Third party imports
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtGui import QFontMetricsF
from qtpy.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QListView,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget)
from superqt.utils import qdebounced, signals_blocked

# Local imports
from spyder.api.config.fonts import SpyderFontType, SpyderFontsMixin
from spyder.config.base import _, load_lang_conf
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.utils.stylesheet import (
    AppStyle, MAC, PREFERENCES_TABBAR_STYLESHEET, WIN)


class PageScrollArea(QScrollArea):
    """Scroll area for preference pages."""

    def widget(self):
        """Return the page widget inside the scroll area."""
        return super().widget().page


class ConfigDialog(QDialog, SpyderFontsMixin):
    """Preferences dialog."""

    # Signals
    check_settings = Signal()
    sig_size_changed = Signal(QSize)
    sig_reset_preferences_requested = Signal()

    # Constants
    ITEMS_MARGIN = 2 * AppStyle.MarginSize
    ITEMS_PADDING = (
        AppStyle.MarginSize if (MAC or WIN) else 2 * AppStyle.MarginSize
    )
    CONTENTS_WIDTH = 230 if MAC else (200 if WIN else 240)
    ICON_SIZE = 20
    MIN_WIDTH = 940 if MAC else (875 if WIN else 920)
    MIN_HEIGHT = 700 if MAC else (660 if WIN else 670)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        # Attributes
        self.main = parent
        self.items_font = self.get_font(
            SpyderFontType.Interface, font_size_delta=1
        )
        self._is_shown = False
        self._separators = []

        # Size
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        # Widgets
        self.pages_widget = QStackedWidget(self)
        self.contents_widget = QListWidget(self)
        self.button_reset = QPushButton(_('Reset to defaults'))

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply |
                                QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)
        self.ok_btn = bbox.button(QDialogButtonBox.Ok)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(_('Preferences'))
        self.setWindowIcon(ima.icon('configure'))

        # Widgets setup
        self.pages_widget.setMinimumWidth(600)

        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(3)
        self.contents_widget.setCurrentRow(0)
        self.contents_widget.setObjectName('configdialog-contents')
        self.contents_widget.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.contents_widget.setFixedWidth(self.CONTENTS_WIDTH)

        # Don't show horizontal scrollbar because it doesn't look good. Instead
        # we show tooltips if the text doesn't fit in contents_widget width.
        self.contents_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)

        # Layout
        contents_and_pages_layout = QGridLayout()
        contents_and_pages_layout.addWidget(self.contents_widget, 0, 0)
        contents_and_pages_layout.addWidget(self.pages_widget, 0, 1)
        contents_and_pages_layout.setContentsMargins(0, 0, 0, 0)
        contents_and_pages_layout.setColumnStretch(0, 1)
        contents_and_pages_layout.setColumnStretch(1, 3)
        contents_and_pages_layout.setHorizontalSpacing(0)

        btnlayout = QHBoxLayout()
        btnlayout.addWidget(self.button_reset)
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        layout = QVBoxLayout()
        layout.addLayout(contents_and_pages_layout)
        layout.addSpacing(3)
        layout.addLayout(btnlayout)

        self.setLayout(layout)

        # Stylesheet
        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

        # Signals and slots
        self.button_reset.clicked.connect(self.sig_reset_preferences_requested)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
            self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)

        # Ensures that the config is present on spyder first run
        CONF.set('main', 'interface_language', load_lang_conf())

    # ---- Public API
    # -------------------------------------------------------------------------
    def get_current_index(self):
        """Return current page index"""
        return self.contents_widget.currentRow()

    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)

    def get_page(self, index=None):
        """Return page widget"""
        if index is None:
            page = self.pages_widget.currentWidget()
        else:
            page = self.pages_widget.widget(index)

        # Not all pages are config pages (e.g. separators have a simple QWidget
        # as their config page). So, we need to check for this.
        if page and hasattr(page, 'widget'):
            return page.widget()

    def get_index_by_name(self, name):
        """Return page index by CONF_SECTION name."""
        for idx in range(self.pages_widget.count()):
            page = self.get_page(idx)

            # This is the case for separators
            if page is None:
                continue

            try:
                # New API
                section = page.plugin.NAME
            except AttributeError:
                section = page.CONF_SECTION

            if section == name:
                return idx
        else:
            return None

    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            configpage = self.get_page()
            if not configpage.is_valid():
                return
            configpage.apply_changes()

    def current_page_changed(self, index):
        widget = self.get_page(index)
        self.apply_btn.setVisible(widget.apply_callback is not None)
        self.apply_btn.setEnabled(widget.is_modified)

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
        self.contents_widget.setItemWidget(item, hline)

        # This is necessary to keep in sync the contents_widget and
        # pages_widget indexes.
        self.pages_widget.addWidget(QWidget(self))

        # Save separators to perform certain operations only on them
        self._separators.append(hline)

    def add_page(self, page):
        # Signals
        self.check_settings.connect(page.check_settings)
        page.show_this_page.connect(lambda row=self.contents_widget.count():
                                    self.contents_widget.setCurrentRow(row))
        page.apply_button_enabled.connect(self.apply_btn.setEnabled)

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
        scrollarea.setObjectName('configdialog-scrollarea')
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(container)
        self.pages_widget.addWidget(scrollarea)

        # Add plugin entry item to contents widget
        item = QListWidgetItem(self.contents_widget)
        item.setText(page.get_name())
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        # In case a plugin doesn't have an icon
        try:
            item.setIcon(page.get_icon())
        except TypeError:
            pass

        # Set font for items
        item.setFont(self.items_font)

    def check_all_settings(self):
        """This method is called to check all configuration page settings
        after configuration dialog has been shown"""
        self.check_settings.emit()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    @Slot()
    def accept(self):
        """Reimplement Qt method"""
        for index in range(self.pages_widget.count()):
            configpage = self.get_page(index)

            # This can be the case for separators, which doesn't have a config
            # page.
            if configpage is None:
                continue

            if not configpage.is_valid():
                return

            configpage.apply_changes()

        QDialog.accept(self)

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

            self._css['QListView#configdialog-contents::item'].setValues(
                margin=item_margin
            )

            self.setStyleSheet(self._css.toString())

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

    def _generate_stylesheet(self):
        """Generate stylesheet for this widget as a qstylizer object."""
        # Use the tabbar stylesheet as the base one and extend it.
        tabs_stylesheet = PREFERENCES_TABBAR_STYLESHEET.get_copy()
        css = tabs_stylesheet.get_stylesheet()

        # Set style of contents area
        css['QListView#configdialog-contents'].setValues(
            padding=f'{self.ITEMS_MARGIN}px 0px',
            backgroundColor=QStylePalette.COLOR_BACKGROUND_2,
            border=f'1px solid {QStylePalette.COLOR_BACKGROUND_2}',
        )

        # Remove border color on focus of contents area
        css['QListView#configdialog-contents:focus'].setValues(
            border=f'1px solid {QStylePalette.COLOR_BACKGROUND_2}',
        )

        # Add margin and padding for items in contents area
        css['QListView#configdialog-contents::item'].setValues(
            padding=f'{self.ITEMS_PADDING}px',
            margin=f'0px {self.ITEMS_MARGIN}px'
        )

        # Set border radius and background color for hover, active and inactive
        # states of items
        css['QListView#configdialog-contents::item:hover'].setValues(
            borderRadius=f'{QStylePalette.SIZE_BORDER_RADIUS}',
        )

        for state in ['item:selected:active', 'item:selected:!active']:
            css[f'QListView#configdialog-contents::{state}'].setValues(
                borderRadius=f'{QStylePalette.SIZE_BORDER_RADIUS}',
                backgroundColor=QStylePalette.COLOR_BACKGROUND_4
            )

        # Remove border of all scroll areas for pages
        css['QScrollArea#configdialog-scrollarea'].setValues(
            border='0px',
        )

        return css

    @qdebounced(timeout=40)
    def _on_resize_event(self):
        """Method to run when Qt emits a resize event."""
        self._add_tooltips()
        self._adjust_items_margin()
        self._adjust_separators_width()
        self.sig_size_changed.emit(self.size())
