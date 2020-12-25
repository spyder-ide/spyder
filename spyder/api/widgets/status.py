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
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import create_waitspinner


class StatusBarWidget(QWidget, SpyderWidgetMixin):
    """Status bar widget base."""

    ID = None
    """
    Unique string widget identifier.
    """

    sig_option_changed = Signal(str, object)
    """
    This signal is required when widgets need to change options in
    Spyder's config system.
    """

    sig_clicked = Signal()
    """
    This signal is emmitted when the widget is clicked.
    """

    def __init__(self, parent=None, spinner=False):
        """Status bar widget base."""
        super().__init__(parent)

        # Variables
        self.value = None
        self._parent = parent

        # Widget
        self._icon = self.get_icon()
        self._pixmap = None
        self._icon_size = QSize(16, 16)  # Should this be adjustable?
        self.label_icon = QLabel()
        self.label_value = QLabel()
        self.spinner = None
        if spinner:
            self.spinner = create_waitspinner(size=14, parent=self)

        # Layout setup
        layout = QHBoxLayout(self)
        layout.setSpacing(0)  # Reduce space between icon and label
        layout.addWidget(self.label_icon)
        layout.addWidget(self.label_value)
        if spinner:
            layout.addWidget(self.spinner)
            self.spinner.hide()
        if is_dark_interface():
            layout.addSpacing(0)
        else:
            layout.addSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Widget setup
        self.set_icon()

        # See spyder-ide/spyder#9044.
        self.text_font = QFont(QFont().defaultFamily(), weight=QFont.Normal)
        self.label_value.setAlignment(Qt.AlignRight)
        self.label_value.setFont(self.text_font)

        # Setup
        self.set_value('')
        self.update_tooltip()

    # ---- Status bar widget API
    def set_icon(self):
        """Set the icon for the status bar widget."""
        icon = self._icon
        self.label_icon.setVisible(icon is not None)
        if icon is not None and isinstance(icon, QIcon):
            self._pixmap = icon.pixmap(self._icon_size)
            self.label_icon.setPixmap(self._pixmap)

    def set_value(self, value):
        """Set formatted text value."""
        self.value = value
        self.label_value.setText(value)

    def update_tooltip(self):
        """Update tooltip for widget."""
        tooltip = self.get_tooltip()
        if tooltip:
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


class BaseTimerStatus(StatusBarWidget):
    """Status bar widget base for widgets that update based on timers."""

    def __init__(self, parent=None):
        """Status bar widget base for widgets that update based on timers."""
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
