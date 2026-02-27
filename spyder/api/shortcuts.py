# -----------------------------------------------------------------------------
# Copyright (c) 2024- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Helper classes to get and set keyboard shortcuts in Spyder.
"""

from __future__ import annotations

# Standard library imports
import functools
from collections.abc import Callable

# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QShortcut, QWidget

# Local imports
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.config.manager import CONF
from spyder.plugins.shortcuts.utils import (
    ShortcutData,
    SHORTCUTS_FOR_WIDGETS_DATA,
)


class SpyderShortcutsMixin(SpyderConfigurationObserver):
    """Provide methods to get, set and register shortcuts for widgets."""

    def __init__(self) -> None:
        """Helper to get, set and register shortcuts for widgets."""
        super().__init__()

        # This is used to keep track of the widget shortcuts
        self._shortcuts: dict[(str, str), QShortcut] = {}

    def get_shortcut(
        self,
        name: str,
        context: str | None = None,
        plugin_name: str | None = None,
    ) -> str:
        """
        Get a shortcut sequence stored under the given name and context.

        Parameters
        ----------
        name: str
            The shortcut name (e.g. ``"run cell"``).
        context: str | None, optional
            Name of the shortcut context, e.g. ``"editor"`` for shortcuts
            that have effect when the :guilabel:`Editor` is focused or
            ``"_"`` for global shortcuts. If not set, the widget's
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` will
            be used as context.
        plugin_name: str | None, optional
            Name of the plugin where the shortcut is defined. Defaults to the
            context name; necessary for third-party plugins that have shortcuts
            with a context different from the plugin name.

        Returns
        -------
        shortcut: str
            Key sequence of the shortcut, e.g. ``"Ctrl+Enter"``.

        Raises
        ------
        configparser.NoOptionError
            If the shortcut does not exist in the configuration.
        """
        context = self.CONF_SECTION if context is None else context
        return CONF.get_shortcut(context, name, plugin_name)

    def set_shortcut(
        self,
        shortcut: str,
        name: str,
        context: str | None = None,
        plugin_name: str | None = None,
    ) -> None:
        """
        Set a shortcut sequence with a given name and context.

        Parameters
        ----------
        shortcut: str
            Key sequence of the shortcut, e.g. ``"Ctrl+Enter"``.
        name: str
            The shortcut name (e.g. ``"run cell"``).
        context: str | None, optional
            Name of the shortcut context, e.g. ``"editor"`` for shortcuts
            that have effect when the :guilabel:`Editor` is focused or
            ``"_"`` for global shortcuts. If not set, the widget's
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` will
            be used as context.
        plugin_name: str | None, optional
            Name of the plugin where the shortcut is defined. Defaults to the
            context name; necessary for third-party plugins that have shortcuts
            with a context different from the plugin name.

        Returns
        -------
        None

        Raises
        ------
        configparser.NoOptionError
            If the shortcut does not exist in the configuration.
        """
        context = self.CONF_SECTION if context is None else context
        CONF.set_shortcut(context, name, shortcut, plugin_name)

    def register_shortcut_for_widget(
        self,
        name: str,
        triggered: Callable,
        widget: QWidget | None = None,
        context: str | None = None,
        plugin_name: str | None = None,
    ) -> None:
        """
        Register a shortcut for a widget that inherits this mixin.

        Parameters
        ----------
        name: str
            The shortcut name (e.g. ``"run cell"``).
        triggered: Callable
            Callable (i.e. function or method) to be triggered by the shortcut.
        widget: QWidget, optional
            Widget to which this shortcut will be registered. If not set, the
            widget that calls this method will be used.
        context: str | None, optional
            Name of the shortcut context, e.g. ``"editor"`` for shortcuts
            that have effect when the :guilabel:`Editor` is focused or
            ``"_"`` for global shortcuts. If not set, the widget's
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` will
            be used as context.
        plugin_name: str | None, optional
            Name of the plugin where the shortcut is defined. Defaults to the
            context name; necessary for third-party plugins that have shortcuts
            with a context different from the plugin name.

        Returns
        -------
        None
        """
        context = self.CONF_SECTION if context is None else context
        widget = self if widget is None else widget

        # Name and context are saved in lowercase in our config system, so we
        # need to use them like that here.
        # Note: That's how the Python ConfigParser class saves options.
        name = name.lower()
        context = context.lower()

        # Register shortcurt for widget
        keystr = self.get_shortcut(name, context, plugin_name)
        self._register_shortcut(
            keystr, name, triggered, context, widget, plugin_name
        )

        # Add observer for shortcut so that it's updated when changed by users
        # in Preferences
        config_observer = functools.partial(
            self._register_shortcut,
            name=name,
            triggered=triggered,
            context=context,
            widget=widget,
            plugin_name=plugin_name,
        )

        self.add_configuration_observer(
            config_observer, option=f"{context}/{name}", section="shortcuts"
        )

        # Keep track of all widget shortcuts. This is necessary to show them in
        # Preferences.
        data = ShortcutData(
            qobject=None, name=name, context=context, plugin_name=plugin_name
        )
        if data not in SHORTCUTS_FOR_WIDGETS_DATA:
            SHORTCUTS_FOR_WIDGETS_DATA.append(data)

    def _register_shortcut(
        self,
        keystr: str,
        name: str,
        triggered: Callable,
        context: str,
        widget: QWidget,
        plugin_name: str | None,
    ) -> None:
        """
        Auxiliary function to register a shortcut for a widget.

        Parameters
        ----------
        keystr: str
            Key string for the shortcut, e.g. ``"Ctrl+Enter"``.
        name: str
            The shortcut name (e.g. ``"run cell"``).
        triggered: Callable
            Callable (i.e. function or method) to be triggered by the shortcut.
        context: str
            Name of the shortcut context, e.g. ``"editor"`` for shortcuts
            that have effect when the :guilabel:`Editor` is focused or
            ``"_"`` for global shortcuts.
        widget: QWidget
            Widget to which this shortcut will be registered.
        plugin_name: str | None
            Name of the plugin where the shortcut is defined.

        Returns
        -------
        None
        """
        # Disable current shortcut, if available
        current_shortcut = self._shortcuts.get((context, name, plugin_name))
        if current_shortcut:
            # Don't do the rest if we're trying to register the same shortcut
            # again. This happens at startup because shortcuts are registered
            # on widget creation and then the observer attached to the shortcut
            # tries to do it again after CONF.notify_all_observers() is called.
            if current_shortcut.key().toString() == keystr:
                return

            # Disable current shortcut to create a new one below
            current_shortcut.setEnabled(False)
            current_shortcut.deleteLater()
            self._shortcuts.pop((context, name, plugin_name))

        # Create a new shortcut
        new_shortcut = QShortcut(QKeySequence(keystr), widget)
        new_shortcut.activated.connect(triggered)
        new_shortcut.setContext(Qt.WidgetWithChildrenShortcut)

        # Save shortcut
        self._shortcuts[(context, name, plugin_name)] = new_shortcut
