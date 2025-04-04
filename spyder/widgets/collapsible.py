# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Collapsible widget to hide and show child widgets."""

import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QPushButton
from superqt import QCollapsible

from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle


class CollapsibleWidget(QCollapsible):
    """Collapsible widget to hide and show child widgets."""

    def __init__(self, parent=None, title=""):
        super().__init__(title=title, parent=parent)

        # Align widget to the left to text before or after it (don't know why
        # this is necessary).
        self.layout().setContentsMargins(5, 0, 0, 0)

        # Remove spacing between toggle button and contents area
        self.layout().setSpacing(0)

        # Set icons
        self.setCollapsedIcon(ima.icon("collapsed"))
        self.setExpandedIcon(ima.icon("expanded"))

        # To change the style only of these widgets
        self._toggle_btn.setObjectName("collapsible-toggle")
        self.content().setObjectName("collapsible-content")

        # Add padding to the inside content
        self.content().layout().setContentsMargins(
            *((AppStyle.InnerContentPadding,) * 4)
        )

        # Set stylesheet
        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

        # Signals
        self.toggled.connect(self._on_toggled)

        # Set our properties for the toggle button
        self._set_toggle_btn_properties()

    def set_content_bottom_margin(self, bottom_margin):
        """Set bottom margin of the content area to `bottom_margin`."""
        margins = self.content().layout().contentsMargins()
        margins.setBottom(bottom_margin)
        self.content().layout().setContentsMargins(margins)

    def set_content_right_margin(self, right_margin):
        """Set right margin of the content area to `right_margin`."""
        margins = self.content().layout().contentsMargins()
        margins.setRight(right_margin)
        self.content().layout().setContentsMargins(margins)

    def _generate_stylesheet(self):
        """Generate base stylesheet for this widget."""
        css = qstylizer.style.StyleSheet()

        # --- Style for the header button
        css["QPushButton#collapsible-toggle"].setValues(
            # Increase padding (the default one is too small).
            padding=f"{2 * AppStyle.MarginSize}px",
            # Make it a bit different from a default QPushButton to not drag
            # the same amount of attention to it.
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_3
        )

        # Make hover color match the change of background color above
        css["QPushButton#collapsible-toggle:hover"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_4,
        )

        # --- Style for the contents area
        css["QWidget#collapsible-content"].setValues(
            # Remove top border to make it appear attached to the header button
            borderTop="0px",
            # Add border to the other edges
            border=f'1px solid {SpyderPalette.COLOR_BACKGROUND_4}',
            # Add border radius to the bottom to make it match the style of our
            # other widgets.
            borderBottomLeftRadius=f'{SpyderPalette.SIZE_BORDER_RADIUS}',
            borderBottomRightRadius=f'{SpyderPalette.SIZE_BORDER_RADIUS}',
        )

        return css

    def _on_toggled(self, state):
        """Adjustments when the button is toggled."""
        if state:
            # Remove bottom rounded borders from the header when the widget is
            # expanded.
            self._css["QPushButton#collapsible-toggle"].setValues(
                borderBottomLeftRadius='0px',
                borderBottomRightRadius='0px',
            )
        else:
            # Restore bottom rounded borders to the header when the widget is
            # collapsed.
            self._css["QPushButton#collapsible-toggle"].setValues(
                borderBottomLeftRadius=f'{SpyderPalette.SIZE_BORDER_RADIUS}',
                borderBottomRightRadius=f'{SpyderPalette.SIZE_BORDER_RADIUS}',
            )

        self.setStyleSheet(self._css.toString())

    def _set_toggle_btn_properties(self):
        """Set properties for the toogle button."""

        def enter_event(event):
            self.setCursor(Qt.PointingHandCursor)
            super(QPushButton, self._toggle_btn).enterEvent(event)

        def leave_event(event):
            self.setCursor(Qt.ArrowCursor)
            super(QPushButton, self._toggle_btn).leaveEvent(event)

        self.toggleButton().enterEvent = enter_event
        self.toggleButton().leaveEvent = leave_event
