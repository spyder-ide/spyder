# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Main container widget for non-dockable Spyder plugins.

:class:`~spyder.api.plugins.SpyderPluginV2` plugins must provide a
:attr:`~spyder.api.plugins.SpyderPluginV2.CONTAINER_CLASS` attribute that is
a subclass of :class:`PluginMainContainer`, if they have additional widgets
like status bar items or toolbars.
"""

from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third party imports
from qtpy import PYSIDE2
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget

# Local imports
from spyder.api.widgets.mixins import SpyderWidgetMixin

if TYPE_CHECKING:
    from qtpy.QtGui import QCloseEvent

    import spyder.app.mainwindow
    from spyder.api.plugins import SpyderPluginV2


class PluginMainContainer(QWidget, SpyderWidgetMixin):
    """
    Main container widget class for non-dockable Spyder plugins.

    This class is used by non-dockable plugins to be able to contain, parent
    and store references to other widgets, like status bar widgets, toolbars,
    context menus, etc.

    .. important::

        If a Spyder non-dockable plugins defines a
        :attr:`~spyder.api.plugins.SpyderPluginV2.CONTAINER_CLASS`
        it must inherit from this class, :class`PluginMainContainer`.
    """

    CONTEXT_NAME: str | None = None
    """
    The name under which to store actions, toolbars, toolbuttons and menus.

    This optional attribute defines the context name under which actions,
    toolbars, toolbuttons and menus should be registered in the
    Spyder global registry.

    If those elements belong to the global scope of the plugin, then this
    attribute should have a ``None`` value, which will use the plugin's name as
    the context scope.
    """

    # ---- Signals
    # ------------------------------------------------------------------------
    sig_free_memory_requested: Signal = Signal()
    """
    Signal to request the main application garbage-collect deleted objects.
    """

    sig_quit_requested: Signal = Signal()
    """
    Signal to request the main Spyder application quit.
    """

    sig_restart_requested: Signal = Signal()
    """
    Signal to request the main Spyder application quit and restart itself.
    """

    sig_redirect_stdio_requested: Signal = Signal(bool)
    """
    Request the main app redirect standard out/error within file pickers.

    This will redirect :data:`~sys.stdin`, :data:`~sys.stdout`, and
    :data:`~sys.stderr` when using :guilabel:`Open`, :guilabel:`Save`,
    and :guilabel:`Browse` dialogs within a plugin's widgets.

    Parameters
    ----------
    enable: bool
        Enable (``True``) or disable (``False``) standard input/output
        redirection.
    """

    sig_exception_occurred: Signal = Signal(dict)
    """
    Signal to report an exception from a plugin.

    Parameters
    ----------
    error_data: dict[str, str | bool]
        The dictionary containing error data. The expected keys are:

        .. code-block:: python

            error_data = {
                "text": str,
                "is_traceback": bool,
                "repo": str,
                "title": str,
                "label": str,
                "steps": str,
            }

        The ``is_traceback`` key indicates if ``text`` contains plain text or a
        Python error traceback.

        The ``title`` and ``repo`` keys indicate how the error data should
        customize the report dialog and GitHub error submission.

        The ``label`` and ``steps`` keys allow customizing the content of the
        error dialog.
    """

    sig_unmaximize_plugin_requested: Signal = Signal((), (object,))
    """
    Request the main window unmaximize the currently maximized plugin, if any.

    If emitted without arguments, it'll unmaximize any plugin.

    Parameters
    ----------
    plugin_instance: SpyderDockablePlugin
        Unmaximize current plugin only if it is not ``plugin_instance``.
    """

    def __init__(
        self,
        name: str,
        plugin: SpyderPluginV2,
        parent: spyder.app.mainwindow.MainWindow | None = None,
    ) -> None:
        """
        Create a new container class for a plugin.
        
        This method is not meant to be overridden by container subclasses.
        Use the :meth:`setup` method instead to instantiate the widgets that
        this one will contain.

        Parameters
        ----------
        name : str
            The name of the plugin, i.e. the
            :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`.
        plugin : SpyderPluginV2
            The plugin object this is to be the container class of.
        parent : spyder.app.mainwindow.MainWindow | None, optional
            The container's parent widget, normally the Spyder main window.
            By default (``None``), no parent widget (used for testing).

        Returns
        -------
        None
        """
        if not PYSIDE2:
            super().__init__(parent=parent, class_parent=plugin)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=plugin)

        # ---- Attributes
        # --------------------------------------------------------------------
        self._name = name
        self._plugin = plugin
        self._parent = parent

        self.PLUGIN_NAME: str = name
        """
        Plugin name in the action, toolbar, toolbutton & menu registries.

        Usually the same as
        :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`,
        but may be different from :attr:`CONTEXT_NAME`.
        """

        # Widget setup
        # A PluginMainContainer inherits from QWidget so it can be a parent
        # for the widgets it contains. Since it is a QWidget it will occupy a
        # physical space on the screen and may cast "shadow" on the top left
        # of the main window. To prevent this we ensure the widget has zero
        # width and zero height.
        # See: spyder-ide/spyder#13547
        self.setMaximumWidth(0)
        self.setMaximumHeight(0)

    # ---- Public Qt overridden methods
    # -------------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle closing this container widget.

        Parameters
        ----------
        event : QCloseEvent
            The event object closing this widget.

        Returns
        -------
        None
        """
        self.on_close()
        super().closeEvent(event)

    # ---- API: methods to define or override
    # ------------------------------------------------------------------------
    def setup(self) -> None:
        """
        Create widgets, toolbars and menus, and perform other setup steps.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            If the container subclass doesn't define a ``setup`` method.
        """
        raise NotImplementedError(
            "A PluginMainContainer subclass must define a `setup` method!"
        )

    def update_actions(self) -> None:
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the
        :meth:`~spyder.api.widgets.mixins.SpyderActionMixin.create_action`
        method.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            If the subclass doesn't define an ``update_actions`` method.
        """
        raise NotImplementedError(
            "A PluginMainContainer subclass must define a `update_actions` "
            "method!"
        )

    def on_close(self) -> None:
        """
        Perform actions before the container widget is closed.

        Does nothing by default; intended to be overridden for widgets
        that need to perform actions on close.

        .. warning::

            This method **must** only operate on local attributes.

        Returns
        -------
        None
        """
        pass
