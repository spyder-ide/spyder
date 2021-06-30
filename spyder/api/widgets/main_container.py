# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main container widget.

SpyderPluginV2 plugins must provide a CONTAINER_CLASS attribute that is a
subclass of PluginMainContainer, if they provide additional widgets like
status bar widgets or toolbars.
"""

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget

from spyder.api.widgets.mixins import SpyderToolbarMixin, SpyderWidgetMixin


class PluginMainContainer(QWidget, SpyderWidgetMixin, SpyderToolbarMixin):
    """
    Spyder plugin main container class.

    This class handles a non-dockable widget to be able to contain, parent and
    store references to other widgets, like status bar widgets, toolbars,
    context menus, etc.

    Notes
    -----
    All Spyder non dockable plugins can define a plugin container that must
    subclass this.
    """

    CONTEXT_NAME = None
    """
    This optional attribute defines the context name under which actions,
    toolbars, toolbuttons and menus should be registered on the
    Spyder global registry.

    If actions, toolbars, toolbuttons or menus belong to the global scope of
    the plugin, then this attribute should have a `None` value.
    """

    # --- Signals
    # ------------------------------------------------------------------------
    sig_free_memory_requested = Signal()
    """
    This signal can be emitted to request the main application to garbage
    collect deleted objects.
    """

    sig_quit_requested = Signal()
    """
    This signal can be emitted to request the main application to quit.
    """

    sig_restart_requested = Signal()
    """
    This signal can be emitted to request the main application to restart.
    """

    sig_redirect_stdio_requested = Signal(bool)
    """
    This signal can be emitted to request the main application to redirect
    standard output/error when using Open/Save/Browse dialogs within widgets.

    Parameters
    ----------
    enable: bool
        Enable/Disable standard input/output redirection.
    """

    sig_exception_occurred = Signal(dict)
    """
    This signal can be emitted to report an exception handled by this widget.

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The expected keys are:
        >>> error_data= {
            "text": str,
            "is_traceback": bool,
            "repo": str,
            "title": str,
            "label": str,
            "steps": str,
        }

    Notes
    -----
    The `is_traceback` key indicates if `text` contains plain text or a
    Python error traceback.

    The `title` and `repo` keys indicate how the error data should
    customize the report dialog and Github error submission.

    The `label` and `steps` keys allow customizing the content of the
    error dialog.
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(parent=parent, class_parent=plugin)

        # Attributes
        # --------------------------------------------------------------------
        self._name = name
        self._plugin = plugin
        self._parent = parent

        # Attribute used to access the action, toolbar, toolbutton and menu
        # registries
        self.PLUGIN_NAME = name

        # Widget setup
        # A PluginMainContainer inherits from QWidget so it can be a parent
        # for the widgets it contains. Since it is a QWidget it will occupy a
        # physical space on the screen and may cast "shadow" on the top left
        # of the main window. To prevent this we ensure the widget has zero
        # width and zero height.
        # See: spyder-ide/spyder#13547
        self.setMaximumWidth(0)
        self.setMaximumHeight(0)

    # --- API: methods to define or override
    # ------------------------------------------------------------------------
    def setup(self):
        """
        Create actions, widgets, add to menu and other setup requirements.
        """
        raise NotImplementedError(
            'A PluginMainContainer subclass must define a `setup` method!')

    def update_actions(self):
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the self.create_action method.
        """
        raise NotImplementedError(
            'A PluginMainContainer subclass must define a `update_actions` '
            'method!')