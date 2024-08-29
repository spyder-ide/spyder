# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Helper classes to get and set shortcuts in Spyder.
"""

# Standard library imports
from typing import Callable, Optional

# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QShortcut, QWidget

# Local imports
from spyder.config.manager import CONF


class SpyderShortcutsMixin:
    """Provide methods to get, set and register shortcuts."""

    def get_shortcut(
        self,
        name: str,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
    ) -> str:
        """
        Get a shortcut sequence stored under the given name and context.

        Parameters
        ----------
        name: str
            Key identifier under which the shortcut is stored.
        context: Optional[str]
            Name of the shortcut context.
        plugin: Optional[str]
            Name of the plugin where the shortcut is defined.

        Returns
        -------
        shortcut: str
            Key sequence of the shortcut.

        Raises
        ------
        configparser.NoOptionError
            If the context does not exist in the configuration.
        """
        context = self.CONF_SECTION if context is None else context
        return CONF.get_shortcut(context, name, plugin_name)

    def set_shortcut(
        self,
        shortcut: str,
        name: str,
        context: Optional[str] = None,
        plugin_name: Optional[str] = None,
    ):
        """
        Set a shortcut sequence with a given name and context.

        Parameters
        ----------
        shortcut: str
            Key sequence of the shortcut.
        name: str
            Key identifier under which the shortcut is stored.
        context: Optional[str]
            Name of the shortcut context.
        plugin: Optional[str]
            Name of the plugin where the shortcut is defined.

        Raises
        ------
        configparser.NoOptionError
            If the context does not exist in the configuration.
        """
        context = self.CONF_SECTION if context is None else context
        return CONF.set_shortcut(context, name, shortcut, plugin_name)

    def register_shortcut_for_widget(
        self,
        name: str,
        triggered: Callable,
        widget: Optional[QWidget] = None,
        context: Optional[str] = None,
    ):
        """
        Register a shortcut for a widget that inherits this mixin.

        Parameters
        ----------
        name: str
            Key identifier under which the shortcut is stored.
        triggered: Callable
            Callable (i.e. function or method) that will be triggered by the
            shortcut.
        widget: Optional[QWidget]
            Widget to which register this shortcut. By default we register it
            to the one that calls this method.
        context: Optional[str]
            Name of the context (plugin) where the shortcut is defined. By
            default we use the widget's CONF_SECTION.
        """
        context = self.CONF_SECTION if context is None else context
        widget = self if widget is None else widget

        keystr = self.get_shortcut(name, context)
        qsc = QShortcut(QKeySequence(keystr), widget)
        qsc.activated.connect(triggered)
        qsc.setContext(Qt.WidgetWithChildrenShortcut)
