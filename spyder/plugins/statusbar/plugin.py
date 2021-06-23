# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status bar plugin.
"""

# Third-party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import running_under_pytest
from spyder.plugins.statusbar.confpage import StatusBarConfigPage
from spyder.plugins.statusbar.container import StatusBarContainer


# Localization
_ = get_translation('spyder')


class StatusBarWidgetPosition:
    Left = 0
    Right = -1


class StatusBar(SpyderPluginV2):
    """Status bar plugin."""

    NAME = 'statusbar'
    REQUIRES = [Plugins.Preferences]
    CONTAINER_CLASS = StatusBarContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = StatusBarConfigPage

    STATUS_WIDGETS = {}
    EXTERNAL_RIGHT_WIDGETS = {}
    EXTERNAL_LEFT_WIDGETS = {}
    INTERNAL_WIDGETS = {}
    INTERNAL_WIDGETS_IDS = {
        'clock_status', 'cpu_status', 'memory_status', 'read_write_status',
        'eol_status', 'encoding_status', 'cursor_position_status',
        'vcs_status', 'interpreter_status', 'lsp_status', 'kite_status'}

    # ---- SpyderPluginV2 API
    def get_name(self):
        return _('Status bar')

    def get_icon(self):
        return self.create_icon('statusbar')

    def get_description(self):
        return _('Provide Core user interface management')

    def register(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

        # --- Status widgets
        self.add_status_widget(self.mem_status, StatusBarWidgetPosition.Right)
        self.add_status_widget(self.cpu_status, StatusBarWidgetPosition.Right)
        self.add_status_widget(
            self.clock_status, StatusBarWidgetPosition.Right)

    def after_container_creation(self):
        container = self.get_container()
        container.sig_show_status_bar_requested.connect(
            self.show_status_bar
        )

    # ---- Public API
    def add_status_widget(self, widget, position=StatusBarWidgetPosition.Left):
        """
        Add status widget to main application status bar.

        Parameters
        ----------
        widget: StatusBarWidget
            Widget to be added to the status bar.
        position: int
            Position where the widget will be added given the members of the
            StatusBarWidgetPosition enum.
        """
        # Check widget class
        if not isinstance(widget, StatusBarWidget):
            raise SpyderAPIError(
                'Any status widget must subclass StatusBarWidget!'
            )

        # Check ID
        id_ = widget.ID
        if id_ is None:
            raise SpyderAPIError(
                f"Status widget `{repr(widget)}` doesn't have an identifier!"
            )

        # Check it was not added before
        if id_ in self.STATUS_WIDGETS and not running_under_pytest():
            raise SpyderAPIError(f'Status widget `{id_}` already added!')

        if id_ in self.INTERNAL_WIDGETS_IDS:
            self.INTERNAL_WIDGETS[id_] = widget
        elif position == StatusBarWidgetPosition.Right:
            self.EXTERNAL_RIGHT_WIDGETS[id_] = widget
        else:
            self.EXTERNAL_LEFT_WIDGETS[id_] = widget

        self.STATUS_WIDGETS[id_] = widget
        self._statusbar.setStyleSheet('QStatusBar::item {border: None;}')

        if position == StatusBarWidgetPosition.Right:
            self._statusbar.addPermanentWidget(widget)
        else:
            self._statusbar.insertPermanentWidget(
                StatusBarWidgetPosition.Left, widget)
        self._statusbar.layout().setContentsMargins(0, 0, 0, 0)
        self._statusbar.layout().setSpacing(0)

    def remove_status_widget(self, id_):
        """
        Remove widget from status bar.

        Parameters
        ----------
        id_: str
            String identifier for the widget.
        """
        try:
            widget = self.get_status_widget(id_)
            self.STATUS_WIDGETS.pop(id_)
            self._statusbar.removeWidget(widget)
        except RuntimeError:
            # This can happen if the widget was already removed (tests fail
            # without this).
            pass

    def get_status_widget(self, id_):
        """
        Return an application status widget by name.

        Parameters
        ----------
        id_: str
            String identifier for the widget.
        """
        if id_ in self.STATUS_WIDGETS:
            return self.STATUS_WIDGETS[id_]
        else:
            raise SpyderAPIError(f'Status widget "{id_}" not found!')

    def get_status_widgets(self):
        """Return all status widgets."""
        return list(self.STATUS_WIDGETS.keys())

    def remove_status_widgets(self):
        """Remove all status widgets."""
        for w in self.get_status_widgets():
            self.remove_status_widget(w)

    @Slot(bool)
    def show_status_bar(self, value):
        """
        Show/hide status bar.

        Parameters
        ----------
        value: bool
            Decide whether to show or hide the status bar.
        """
        self._statusbar.setVisible(value)

    # ---- Default status widgets
    @property
    def mem_status(self):
        return self.get_container().mem_status

    @property
    def cpu_status(self):
        return self.get_container().cpu_status

    @property
    def clock_status(self):
        return self.get_container().clock_status

    # ---- Private API
    @property
    def _statusbar(self):
        """Reference to main window status bar."""
        return self._main.statusBar()

    def _organize_status_widgets(self):
        """
        Organize the status bar widgets once the application is loaded.
        """
        # Desired organization
        internal_layout = [
            'clock_status', 'cpu_status', 'memory_status', 'read_write_status',
            'eol_status', 'encoding_status', 'cursor_position_status',
            'vcs_status', 'interpreter_status', 'lsp_status', 'kite_status']
        external_left = list(self.EXTERNAL_LEFT_WIDGETS.keys())

        # Remove all widgets from the statusbar, except the external right
        for id_ in self.INTERNAL_WIDGETS:
            self._statusbar.removeWidget(self.INTERNAL_WIDGETS[id_])

        for id_ in self.EXTERNAL_LEFT_WIDGETS:
            self._statusbar.removeWidget(self.EXTERNAL_LEFT_WIDGETS[id_])

        # Add the internal widgets in the desired layout
        for id_ in internal_layout:
            # This is needed in the case kite is installed but not enabled
            if id_ in self.INTERNAL_WIDGETS:
                self._statusbar.insertPermanentWidget(
                    StatusBarWidgetPosition.Left, self.INTERNAL_WIDGETS[id_])
                self.INTERNAL_WIDGETS[id_].setVisible(True)

        # Add the external left widgets
        for id_ in external_left:
            self._statusbar.insertPermanentWidget(
                StatusBarWidgetPosition.Left, self.EXTERNAL_LEFT_WIDGETS[id_])
            self.EXTERNAL_LEFT_WIDGETS[id_].setVisible(True)

    def before_mainwindow_visible(self):
        """Perform actions before the mainwindow is visible"""
        # Organize widgets in the expected order
        self._statusbar.setVisible(False)
        self._organize_status_widgets()
