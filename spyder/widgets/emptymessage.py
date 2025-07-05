# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget to show a friendly message when another one is empty.

It's used in combination with a QStackedWidget.
"""

from __future__ import annotations
import textwrap

import qstylizer.style
import qtawesome as qta
from qtpy.QtCore import QRect, QSize, Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import QFrame, QLabel, QSpacerItem, QVBoxLayout
from superqt.utils import qdebounced

from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.widgets.mixins import SvgToScaledPixmap
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette


class EmptyMessageWidget(QFrame, SvgToScaledPixmap, SpyderFontsMixin):
    """Widget to show a friendly message when another one is empty."""

    def __init__(
        self,
        parent,
        icon_filename: str | None = None,
        text: str | None = None,
        description: str | None = None,
        top_stretch: int = 1,
        middle_stretch: int = 1,
        bottom_stretch: int = 0,
        spinner: bool = False,
        adjust_on_resize: bool = False,
        highlight_on_focus_in: bool = True,
    ):
        super().__init__(parent)

        # Attributes
        self._description = description
        self._adjust_on_resize = adjust_on_resize
        self._highlight_on_focus_in = highlight_on_focus_in
        self._is_shown = False
        self._spin = None
        self._min_height = None
        self._is_visible = False

        # This is public so it can be overridden in subclasses
        self.css = qstylizer.style.StyleSheet()

        # This is necessary to make Qt reduce the size of all widgets on
        # vertical resizes
        if self._adjust_on_resize:
            self.setMinimumHeight(150)

        interface_font_size = self.get_font(
            SpyderFontType.Interface).pointSize()

        # Image (icon)
        self._image_label = None
        if icon_filename:
            self._image_label = QLabel(self)
            self._image_label.setPixmap(
                self.svg_to_scaled_pixmap(icon_filename, rescale=0.8)
            )
            self._image_label.setAlignment(Qt.AlignCenter)

            image_label_qss = qstylizer.style.StyleSheet()
            image_label_qss.QLabel.setValues(border="0px")
            self._image_label.setStyleSheet(image_label_qss.toString())

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
        self._description_label = None
        if self._description is not None:
            self._description_label = QLabel(self._description, parent=self)
            self._description_label.setAlignment(Qt.AlignCenter)
            self._description_label.setWordWrap(True)
            self._description_label.setScaledContents(True)

            description_label_qss = qstylizer.style.StyleSheet()
            description_label_qss.QLabel.setValues(
                fontSize=f"{interface_font_size}pt",
                backgroundColor=SpyderPalette.COLOR_OCCURRENCE_3,
                border="0px",
                padding="20px",
            )
            self._description_label.setStyleSheet(
                description_label_qss.toString()
            )

        # Setup layout
        pane_empty_layout = QVBoxLayout()

        # Add the top stretch
        pane_empty_layout.addStretch(top_stretch)

        # Add the image_label (icon)
        if icon_filename is not None:
            pane_empty_layout.addWidget(self._image_label)

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
        if self._description is not None:
            pane_empty_layout.addWidget(self._description_label)

        pane_empty_layout.addStretch(bottom_stretch)
        pane_empty_layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(pane_empty_layout)

        # Setup style
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

    def set_visibility(self, visible):
        """Adjustments when the widget's visibility changes."""
        self._is_visible = visible

        if self._adjust_on_resize and self._image_label is not None:
            if visible:
                if (
                    self._min_height is not None
                    and self.height() >= self._min_height
                ):
                    self._image_label.show()
            else:
                self._image_label.hide()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            self._start_spinner()
            self._is_shown = True

            if self._adjust_on_resize and self._min_height is None:
                self._min_height = self.minimumSizeHint().height()

        super().showEvent(event)

    def hideEvent(self, event):
        """Adjustments when the widget is hidden."""
        self._stop_spinner()
        self._is_shown = False
        super().hideEvent(event)

    def focusInEvent(self, event):
        if self._highlight_on_focus_in:
            self._apply_stylesheet(True)
        super().focusOutEvent(event)

    def focusOutEvent(self, event):
        if self._highlight_on_focus_in:
            self._apply_stylesheet(False)
        super().focusOutEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._adjust_on_resize:
            self._on_resize_event()

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _apply_stylesheet(self, focus):
        if focus:
            border_color = SpyderPalette.COLOR_ACCENT_3
        else:
            border_color = SpyderPalette.COLOR_BACKGROUND_4

        self.css.QFrame.setValues(
            border=f'1px solid {border_color}',
            margin='0px',
            padding='0px',
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS
        )

        self.setStyleSheet(self.css.toString())

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

    @qdebounced(timeout=30)
    def _on_resize_event(self):
        """Actions to take when widget is resized."""
        # Hide/show image label when necessary
        if self._image_label is not None:
            if (
                # This is necessary to prevent and error when the widget hasn't
                # been made visible yet.
                # Fixes spyder-ide/spyder#24280
                self._min_height is None
                # We need to do this validation because sometimes
                # minimumSizeHint doesn't give the right min_height in
                # showEvent (e.g. when adding an _ErroredMessageWidget to
                # plugins that are not visible).
                or self._min_height < self.minimumSizeHint().height()
            ):
                self._min_height = self.minimumSizeHint().height()

            if self.height() <= self._min_height:
                self._image_label.hide()
            else:
                if self._is_visible:
                    self._image_label.show()

        # Elide description when necessary
        if self._description is not None:
            metrics = QFontMetrics(self._description_label.font())

            # All margins are the same, so we only take the left one
            margin = self._description_label.contentsMargins().left()

            # Height of a single line of text
            text_line_height = metrics.height()

            # Allow a max of two lines of text in the description
            max_height = 2 * text_line_height + 2 * margin

            # Compute the width and height of the description text according to
            # max_height and the width of its label.
            # Solution taken from https://forum.qt.io/post/313343
            rect = metrics.boundingRect(
                # Rectangle in which the text needs to fit
                QRect(
                    0,
                    0,
                    self._description_label.width() - 2 * margin,
                    max_height,
                ),
                self._description_label.alignment() | Qt.TextWordWrap,
                self._description
            )

            # Elide text if it were to occupy more than two lines
            if rect.height() > 2 * text_line_height:
                # Replace description with elided text
                elided_text = metrics.elidedText(
                    self._description, Qt.ElideRight, rect.width()
                )
                self._description_label.setText(elided_text)

                # Show full description in tooltip
                self._description_label.setToolTip(
                    '\n'.join(textwrap.wrap(self._description, 50))
                )

                # This prevents flickering when the widget's width is
                # continuously reduced because Qt wraps the elided text
                self._description_label.setMaximumHeight(
                    text_line_height + 2 * margin
                )
            else:
                # Restore full description if there's enough space
                if "…" in self._description_label.text():
                    # Restore description
                    self._description_label.setText(self._description)

                    # No tooltip is necessary in this case
                    self._description_label.setToolTip("")

                    # Restore max height
                    self._description_label.setMaximumHeight(max_height)
