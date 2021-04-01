# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Third party imports
from qtpy.QtCore import Qt, QSize, QTimer, Signal
from qtpy.QtGui import QFont, QIcon
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import create_waitspinner


class StatusBarWidget(QWidget, SpyderWidgetMixin):
    """
    Base class for status bar widgets.

    These widgets consist by default of an icon, a label and a spinner,
    which are organized from left to right on that order.

    You can also add any other QWidget to this layout by setting the
    CUSTOM_WIDGET_CLASS class attribute. It'll be put between the label
    and the spinner.
    """

    ID = None
    """
    Unique string widget identifier.
    """

    CUSTOM_WIDGET_CLASS = None
    """
    Custom widget class to add to the default layout.
    """

    sig_clicked = Signal()
    """
    This signal is emmitted when the widget is clicked.
    """

    def __init__(self, parent=None, show_icon=True, show_label=True,
                 show_spinner=False):
        """
        Base class for status bar widgets.

        These are composed of the following widgets, which are arranged
        in a QHBoxLayout from left to right:

        * Icon
        * Label
        * Custom QWidget
        * Spinner

        Parameters
        ----------
        show_icon: bool
            Show an icon in the widget.
        show_label: bool
            Show a label in the widget.
        show_spinner: bool
            Show a spinner.

        Notes
        -----
        1. To use an icon, you need to redefine the ``get_icon`` method.
        2. To use a label, you need to call ``set_value``.
        """
        super().__init__(parent, class_parent=parent)
        self._parent = parent

        self.show_icon = show_icon
        self.show_label = show_label
        self.show_spinner = show_spinner

        self.value = None
        self.label_icon = None
        self.label_value = None
        self.spinner = None
        self.custom_widget = None

        self.set_layout()
        self.setStyleSheet(self._stylesheet())

    def set_layout(self):
        """Set layout for default widgets."""
        # Icon
        if self.show_icon:
            self._icon = self.get_icon()
            self._pixmap = None
            self._icon_size = QSize(16, 16)  # Should this be adjustable?
            self.label_icon = QLabel()
            self.set_icon()

        # Label
        if self.show_label:
            self.label_value = QLabel()
            self.set_value('')

            # See spyder-ide/spyder#9044.
            self.text_font = QFont(QFont().defaultFamily(),
                                   weight=QFont.Normal)
            self.label_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.label_value.setFont(self.text_font)

        # Custom widget
        if self.CUSTOM_WIDGET_CLASS:
            if not issubclass(self.CUSTOM_WIDGET_CLASS, QWidget):
                raise SpyderAPIError(
                    'Any custom status widget must subclass QWidget!'
                )
            self.custom_widget = self.CUSTOM_WIDGET_CLASS(self._parent)

        # Spinner
        if self.show_spinner:
            self.spinner = create_waitspinner(size=14, parent=self)
            self.spinner.hide()

        # Layout setup
        layout = QHBoxLayout(self)
        layout.setSpacing(0)  # Reduce space between icon and label
        if self.show_icon:
            layout.addWidget(self.label_icon)
        if self.show_label:
            layout.addWidget(self.label_value)
        if self.custom_widget:
            layout.addWidget(self.custom_widget)
        if self.show_spinner:
            layout.addWidget(self.spinner)

        layout.addSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignVCenter)

        # Setup
        self.update_tooltip()

    # ---- Status bar widget API
    def set_icon(self):
        """Set the icon for the status bar widget."""
        if self.label_icon:
            icon = self._icon
            self.label_icon.setVisible(icon is not None)
            if icon is not None and isinstance(icon, QIcon):
                self._pixmap = icon.pixmap(self._icon_size)
                self.label_icon.setPixmap(self._pixmap)

    def set_value(self, value):
        """Set formatted text value."""
        if self.label_value:
            self.value = value
            self.label_value.setText(value)

    def update_tooltip(self):
        """Update tooltip for widget."""
        tooltip = self.get_tooltip()
        if tooltip:
            if self.label_value:
                self.label_value.setToolTip(tooltip)
            if self.label_icon:
                self.label_icon.setToolTip(tooltip)
            self.setToolTip(tooltip)

    def mouseReleaseEvent(self, event):
        """Override Qt method to allow for click signal."""
        super(StatusBarWidget, self).mousePressEvent(event)
        self.sig_clicked.emit()

    # ---- API to be defined by user
    def get_tooltip(self):
        """Return the widget tooltip text."""
        return ''

    def get_icon(self):
        """Return the widget tooltip text."""
        return None

    def _stylesheet(self):
        stylesheet = ("QToolTip {{background-color: {background_color};"
                      "color: {color};"
                      "border: none}}").format(
                      background_color=QStylePalette.COLOR_ACCENT_2,
                      color=QStylePalette.COLOR_TEXT_1
                      )
        return stylesheet


class BaseTimerStatus(StatusBarWidget):
    """
    Base class for status bar widgets that update based on timers.
    """

    def __init__(self, parent=None):
        """Base class for status bar widgets that update based on timers."""
        self.timer = None  # Needs to come before parent call
        super().__init__(parent)
        self._interval = 2000

        # Widget setup
        fm = self.label_value.fontMetrics()
        self.label_value.setMinimumWidth(fm.width('000%'))

        # Setup
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(self._interval)

    # ---- Qt API
    def setVisible(self, value):
        """Override Qt method to stops timers if widget is not visible."""
        if self.timer is not None:
            if value:
                self.timer.start(self._interval)
            else:
                self.timer.stop()
        super(BaseTimerStatus, self).setVisible(value)

    # ---- BaseTimerStatus widget API
    def update_status(self):
        """Update status label widget, if widget is visible."""
        if self.isVisible():
            self.label_value.setText(self.get_value())

    def set_interval(self, interval):
        """Set timer interval (ms)."""
        self._interval = interval
        if self.timer is not None:
            self.timer.setInterval(interval)

    # ---- API to be defined by user
    def get_value(self):
        """Return formatted text value."""
        raise NotImplementedError
