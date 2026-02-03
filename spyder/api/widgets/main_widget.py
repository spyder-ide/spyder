# -----------------------------------------------------------------------------
# Copyright (c) 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Main plugin widget.

SpyderDockablePlugin plugins must provide a WIDGET_CLASS attribute that is a
subclass of PluginMainWidget.
"""

from __future__ import annotations

# Standard library imports
import logging
from collections import OrderedDict
from typing import TYPE_CHECKING

# Third party imports
from qtpy import PYSIDE2
from qtpy.QtCore import QByteArray, QSize, Qt, Signal, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.widgets import PluginMainWidgetActions, PluginMainWidgetWidgets
from spyder.api.widgets.auxiliary_widgets import (
    MainCornerWidget,
    SpyderWindowWidget,
)
from spyder.api.widgets.menus import (
    OptionsMenuSections,
    PluginMainWidgetMenus,
    PluginMainWidgetOptionsMenu,
)
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.api.widgets.toolbars import MainWidgetToolbar
from spyder.utils.qthelpers import create_waitspinner, qbytearray_to_str
from spyder.utils.registries import ACTION_REGISTRY, TOOLBAR_REGISTRY
from spyder.utils.stylesheet import (
    AppStyle,
    APP_STYLESHEET,
    PANES_TABBAR_STYLESHEET,
    PANES_TOOLBAR_STYLESHEET,
)
from spyder.widgets.dock import DockTitleBar, SpyderDockWidget
from spyder.widgets.emptymessage import EmptyMessageWidget
from spyder.widgets.tabs import Tabs

if TYPE_CHECKING:
    from qtpy.QtGui import QCloseEvent, QFocusEvent
    from qtpy.QWidget import QLayout

    import spyder.app.mainwindow  # For MainWindow
    import spyder.utils.qthelpers  # For SpyderAction
    import spyder.widgets.dock  # For SpyderDockWidget

    from spyder.api.plugins import SpyderPluginV2

# Logging
logger = logging.getLogger(__name__)


class PluginMainWidget(QWidget, SpyderWidgetMixin):
    """
    Spyder plugin main widget class.

    This class handles both a dockwidget pane and a floating window widget
    (undocked pane).

    .. note::

        All :class:`~spyder.api.plugins.SpyderDockablePlugin`\\s define a
        main widget that must be a subclass of this class.

    Notes
    -----
    This widget is a subclass of :class:`QWidget` that consists of a single
    central widget and a set of toolbars stacked above it.

    The toolbars are not movable nor floatable and must occupy the entire
    horizontal space available for the plugin. This mean that toolbars must be
    stacked vertically and cannot be placed horizontally next to each other.
    """

    # ---- Attributes
    # -------------------------------------------------------------------------
    ENABLE_SPINNER: bool = False
    """
    Enable/disable showing a progress spinner on the top right of the toolbar.

    If ``True``, an extra space will be added to the toolbar (even if the
    spinner is not moving) to avoid items jumping to the left/right when
    the spinner appears. If ``False`` no extra space will be added.

    The spinner is shown to the left of the Options (hamburger) menu.

    Plugins that provide actions that take time should make this ``True`` and
    use the :meth:`start_spinner`/:meth:`stop_spinner` methods accordingly.

    Examples
    --------
    The :guilabel:`Find in Files` plugin (:mod:`spyder.plugins.findinfiles`
    is an example of a core plugin that uses it.
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

    MARGIN_TOP: int = 0
    """
    Adjust the widget's top margin in integer pixels.
    """

    SHOW_MESSAGE_WHEN_EMPTY: bool = False
    """
    Enable or (by default) disable showing a message when the widget is empty.

    .. note ::

        If ``True``, you need to set at least the :attr:`MESSAGE_WHEN_EMPTY`
        attribute as well.

    Examples
    --------
    The :guilabel:`Find in Files` plugin is an example of a core plugin
    that uses it.
    """

    MESSAGE_WHEN_EMPTY: str | None = None
    """
    The main message, as a string, that will be shown when the widget is empty.

    Must be set to a string  when :attr:`SHOW_MESSAGE_WHEN_EMPTY` is ``True``,
    and has no effect if that attribute is ``False``.

    Examples
    --------
    The :guilabel:`Find in Files` plugin is an example of a core plugin
    that uses it.
    """

    IMAGE_WHEN_EMPTY: str | None = None
    """
    Name of or path to an SVG image to show when the widget is empty.

    If ``None`` (the default), no image is shown.

    Only shown when :attr:`SHOW_MESSAGE_WHEN_EMPTY` is set to ``True``.

    .. note ::

        This needs to be an SVG file so that it can be rendered correctly
        on high-resolution screens.

    Examples
    --------
    The :guilabel:`Find in Files` plugin is an example of a core plugin
    that uses it.
    """

    DESCRIPTION_WHEN_EMPTY: str | None = None
    """
    Additional text shown below the main message when the widget is empty.

    If ``None`` (the default), no additional text is shown.

    Only shown when :attr:`SHOW_MESSAGE_WHEN_EMPTY` is set to ``True``,
    and shown below :attr:`MESSAGE_WHEN_EMPTY`.

    Examples
    --------
    The :guilabel:`Find in Files` plugin is an example of a core plugin
    that uses it.
    """

    SET_LAYOUT_WHEN_EMPTY: bool = True
    """
    Use a vertical layout for the stack holding the empty and content widgets.

    Set this to ``False`` if you need to use a more complex layout in
    your widget; ``True`` is the default behavior.

    Examples
    --------
    The :guilabel:`Debugger` plugin is an example of a core plugin
    that uses it.
    """

    # ---- Signals
    # -------------------------------------------------------------------------
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

    sig_toggle_view_changed: Signal = Signal(bool)
    """
    Signal to report that visibility of a dockable plugin has changed.

    This is triggered by checking/unchecking the entry for a pane in the
    :menuselection:`Window --> Panes` menu.

    Parameters
    ----------
    visible: bool
        Whether the widget has been shown (``True``) or hidden (``False``).
    """

    sig_update_ancestor_requested: Signal = Signal()
    """
    Notify the main window that a child widget needs its ancestor updated.
    """

    sig_unmaximize_plugin_requested: Signal = Signal((), (object,))
    """
    Request the main window unmaximize the currently maximized plugin, if any.

    If emitted without arguments, it'll unmaximize any plugin.

    Parameters
    ----------
    plugin_instance: spyder.api.plugins.SpyderDockablePlugin
        Unmaximize current plugin only if it is not ``plugin_instance``.
    """

    sig_focus_status_changed: Signal = Signal(bool)
    """
    Signal to report a change in the focus state of this widget.

    Parameters
    ----------
    status: bool
        ``True`` if the widget is now focused; ``False`` if it is not.
    """

    def __init__(
        self,
        name: str,
        plugin: SpyderPluginV2,
        parent: spyder.app.mainwindow.MainWindow | None = None,
    ) -> None:
        """
        Create a new main widget for a plugin.

        The widget is created automatically by Spyder, and is not intended
        to be instantiated manually.

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

        Raises
        ------
        SpyderAPIError
            If :attr:`SHOW_MESSAGE_WHEN_EMPTY` is set to ``True`` but
            :attr:`MESSAGE_WHEN_EMPTY` is not set to a non-empty string.
        """
        if not PYSIDE2:
            super().__init__(parent=parent, class_parent=plugin)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=plugin)

        # Attributes
        # --------------------------------------------------------------------
        self._is_tab = False
        self._name = name
        self._plugin = plugin
        self._parent = parent
        self._default_margins = None
        self.is_visible: bool | None = None
        self.dock_action: spyder.utils.qthelpers.SpyderAction | None = None
        self.undock_action: spyder.utils.qthelpers.SpyderAction | None = None
        self.close_action: spyder.utils.qthelpers.SpyderAction | None = None
        self._toolbars_already_rendered = False
        self._is_maximized = False

        self.PLUGIN_NAME: str = name
        """
        Plugin name in the action, toolbar, toolbutton & menu registries.

        Usually the same as
        :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`,
        but may be different from :attr:`CONTEXT_NAME`.
        """

        # We create our toggle action instead of using the one that comes with
        # dockwidget because it was not possible to raise and focus the plugin
        self.toggle_view_action: spyder.utils.qthelpers.SpyderAction | None = (
            None
        )
        self._toolbars = OrderedDict()
        self._auxiliary_toolbars = OrderedDict()

        # Widgets
        # --------------------------------------------------------------------
        self.windowwidget: SpyderWindowWidget | None = None
        self.dockwidget: spyder.widgets.dock.SpyderDockWidget | None = None
        self._icon = QIcon()
        self._spinner = None
        self._stack = None
        self._content_widget = None
        self._pane_empty = None

        if self.ENABLE_SPINNER:
            self._spinner = create_waitspinner(
                size=16, parent=self, name=PluginMainWidgetWidgets.Spinner
            )

        self._corner_widget = MainCornerWidget(
            parent=self,
            name=PluginMainWidgetWidgets.CornerWidget,
        )
        self._corner_widget.ID = "main_corner"

        self._main_toolbar = MainWidgetToolbar(
            parent=self,
            title=_("Main widget toolbar"),
        )
        self._main_toolbar.ID = "main_toolbar"

        TOOLBAR_REGISTRY.register_reference(
            self._main_toolbar,
            self._main_toolbar.ID,
            self.PLUGIN_NAME,
            self.CONTEXT_NAME,
        )

        self._corner_toolbar = MainWidgetToolbar(
            parent=self,
            title=_("Main widget corner toolbar"),
        )
        self._corner_toolbar.ID = "corner_toolbar"

        TOOLBAR_REGISTRY.register_reference(
            self._corner_toolbar,
            self._corner_toolbar.ID,
            self.PLUGIN_NAME,
            self.CONTEXT_NAME,
        )

        self._corner_toolbar.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self._options_menu = self._create_menu(
            PluginMainWidgetMenus.Options,
            title=_("Options menu"),
            MenuClass=PluginMainWidgetOptionsMenu,
        )

        # Margins
        # --------------------------------------------------------------------
        # These margins are necessary to give some space between the widgets
        # inside this one and the window separator and borders.
        self._margin_right = AppStyle.MarginSize
        self._margin_bottom = AppStyle.MarginSize
        if not self.get_conf("vertical_tabs", section="main"):
            self._margin_left = AppStyle.MarginSize
        else:
            self._margin_left = 0

        # Layout
        # --------------------------------------------------------------------
        self._main_layout = QVBoxLayout()
        self._toolbars_layout = QVBoxLayout()
        self._main_toolbar_layout = QHBoxLayout()

        self._toolbars_layout.setContentsMargins(
            self._margin_left, 0, self._margin_right, 0
        )
        self._toolbars_layout.setSpacing(0)
        self._main_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self._main_toolbar_layout.setSpacing(0)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Add inititals layouts
        self._main_toolbar_layout.addWidget(self._main_toolbar, stretch=10000)
        self._main_toolbar_layout.addWidget(self._corner_toolbar, stretch=1)
        self._toolbars_layout.addLayout(self._main_toolbar_layout)
        self._main_layout.addLayout(self._toolbars_layout, stretch=1)

        # Create a stacked layout when the widget displays an empty message
        if self.SHOW_MESSAGE_WHEN_EMPTY and self.get_conf(
            "show_message_when_panes_are_empty", section="main"
        ):
            if not self.MESSAGE_WHEN_EMPTY:
                raise SpyderAPIError(
                    "You need to provide a message to show when the widget is "
                    "empty"
                )

            self._pane_empty = EmptyMessageWidget(
                self,
                self.IMAGE_WHEN_EMPTY,
                self.MESSAGE_WHEN_EMPTY,
                self.DESCRIPTION_WHEN_EMPTY,
                adjust_on_resize=True,
            )

            self._stack = QStackedWidget(self)
            self._stack.addWidget(self._pane_empty)

            if self.SET_LAYOUT_WHEN_EMPTY:
                layout = QVBoxLayout()
                layout.addWidget(self._stack)
                self.setLayout(layout)

    # ---- Private Methods
    # -------------------------------------------------------------------------
    def _setup(self) -> None:
        """
        Setup default actions, create options menu, and connect signals.
        """
        # Tabs
        children = self.findChildren(Tabs)
        if children:
            for child in children:
                self._is_tab = True
                # For widgets that use tabs, we add the corner widget using
                # the setCornerWidget method.
                child.setCornerWidget(self._corner_widget)
                self._corner_widget.setStyleSheet(str(PANES_TABBAR_STYLESHEET))
                break

        self._options_button = self.create_toolbutton(
            PluginMainWidgetWidgets.OptionsToolButton,
            text=_("Options"),
            icon=self.create_icon("tooloptions"),
        )

        self.add_corner_widget(self._options_button)

        if self.ENABLE_SPINNER:
            self.add_corner_widget(self._spinner)

        # Widget setup
        # --------------------------------------------------------------------
        self._main_toolbar.setVisible(not self._is_tab)
        self._corner_toolbar.setVisible(not self._is_tab)
        self._options_button.setPopupMode(QToolButton.InstantPopup)

        # Create default widget actions
        self.dock_action = self.create_action(
            name=PluginMainWidgetActions.DockPane,
            text=_("Dock"),
            tip=_("Dock the pane"),
            icon=self.create_icon("dock"),
            triggered=self.dock_window,
        )
        self.lock_unlock_action = self.create_action(
            name=PluginMainWidgetActions.LockUnlockPosition,
            text=_("Move"),
            tip=_("Unlock to move pane to another position"),
            icon=self.create_icon("drag_dock_widget"),
            triggered=self.lock_unlock_position,
        )
        self.undock_action = self.create_action(
            name=PluginMainWidgetActions.UndockPane,
            text=_("Undock"),
            tip=_("Undock the pane"),
            icon=self.create_icon("undock"),
            triggered=self.create_window,
        )
        self.close_action = self.create_action(
            name=PluginMainWidgetActions.ClosePane,
            text=_("Close"),
            tip=_("Close the pane"),
            icon=self.create_icon("close_pane"),
            triggered=self.close_dock,
        )
        # We use this instead of the QDockWidget.toggleViewAction
        self.toggle_view_action = self.create_action(
            name="switch to " + self._name,
            text=self.get_title(),
            toggled=lambda checked: self.toggle_view(checked),
            context=Qt.WidgetWithChildrenShortcut,
            shortcut_context="_",
        )

        for item in [
            self.lock_unlock_action,
            self.undock_action,
            self.dock_action,
            self.close_action,
        ]:
            self.add_item_to_menu(
                item,
                self._options_menu,
                section=OptionsMenuSections.Bottom,
            )

        self._options_button.setMenu(self._options_menu)
        self._options_menu.aboutToShow.connect(self._update_actions)

        # For widgets that do not use tabs, we add the corner widget to the
        # corner toolbar
        if not self._is_tab:
            self.add_item_to_toolbar(
                self._corner_widget,
                toolbar=self._corner_toolbar,
                section="corner",
            )
            self._corner_widget.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))

        # Update title
        self.setWindowTitle(self.get_title())

    def _update_actions(self) -> None:
        """
        Refresh Options menu.
        """
        show_dock_actions = self.windowwidget is None
        self.undock_action.setVisible(show_dock_actions)
        self.lock_unlock_action.setVisible(show_dock_actions)
        self.dock_action.setVisible(not show_dock_actions)

        # Widget setup
        self.update_actions()

    @Slot(bool)
    def _on_top_level_change(self, top_level: bool) -> None:
        """
        Actions to perform when a plugin is undocked to be moved.
        """
        self.undock_action.setDisabled(top_level)

        # Change the cursor shape when dragging
        if top_level:
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        else:
            QApplication.restoreOverrideCursor()

    @Slot(bool)
    def _on_title_bar_shown(self, visible: bool) -> None:
        """
        Actions to perform when the title bar is shown/hidden.
        """
        if visible:
            self.lock_unlock_action.setText(_("Lock"))
            self.lock_unlock_action.setIcon(self.create_icon("lock_open"))
            for method_name in ["setToolTip", "setStatusTip"]:
                method = getattr(self.lock_unlock_action, method_name)
                method(_("Lock pane to the current position"))
        else:
            self.lock_unlock_action.setText(_("Move"))
            self.lock_unlock_action.setIcon(
                self.create_icon("drag_dock_widget")
            )
            for method_name in ["setToolTip", "setStatusTip"]:
                method = getattr(self.lock_unlock_action, method_name)
                method(_("Unlock to move pane to another position"))

    # ---- Public Qt overridden methods
    # -------------------------------------------------------------------------
    def setLayout(self, layout: QLayout) -> None:
        """
        Set layout for the widget.
        """
        self._main_layout.addLayout(layout, stretch=1000000)
        super().setLayout(self._main_layout)
        layout.setContentsMargins(
            self._margin_left,
            self.MARGIN_TOP,
            self._margin_right,
            self._margin_bottom,
        )
        layout.setSpacing(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle closing the widget.

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

    def focusInEvent(self, event: QFocusEvent) -> None:
        """
        Handle the widget gaining focus.

        Parameters
        ----------
        event : QFocusEvent
            The focus event object.

        Returns
        -------
        None
        """
        self.sig_focus_status_changed.emit(True)
        self.on_focus_in()
        return super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """
        Handle the widget losing focus.

        Parameters
        ----------
        event : QFocusEvent
            The focus event object.

        Returns
        -------
        None
        """
        self.sig_focus_status_changed.emit(False)
        self.on_focus_out()
        return super().focusOutEvent(event)

    # ---- Public methods to use
    # -------------------------------------------------------------------------
    def get_plugin(self) -> SpyderPluginV2:
        """
        Return the parent plugin of this widget.

        Returns
        -------
        SpyderPluginV2
            The parent plugin of this widget.
        """
        return self._plugin

    def get_action(
        self, name: str, context: str | None = None, plugin: str | None = None
    ) -> spyder.utils.qthelpers.SpyderAction:
        """
        Return an action by name, context and plugin.

        Parameters
        ----------
        name: str
            Identifier of the action to retrieve.
        context: str | None, optional
            Context identifier under which the action was stored.
            If ``None``, the default, then the
            :attr:`CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the action was defined.
            If ``None``, the default, then the
            :attr:`~spyder.api.widgets.mixins.SpyderWidgetMixin.PLUGIN_NAME`
            attribute is used instead.

        Returns
        -------
        spyder.utils.qthelpers.SpyderAction
            The corresponding action stored under the given ``name``,
             ``context`` and ``plugin``.

        Raises
        ------
        KeyError
            If the combination of ``name``, ``context`` and ``plugin`` keys
            does not exist in the action registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context

        return ACTION_REGISTRY.get_reference(name, plugin, context)

    def add_corner_widget(
        self,
        action_or_widget: spyder.utils.qthelpers.SpyderAction | QWidget,
        before: spyder.utils.qthelpers.SpyderAction | QWidget | None = None,
    ) -> None:
        """
        Add a widget to the corner toolbar.

        By default, widgets are added to the left of the last toolbar item.
        Corner widgets provide an options menu button and a spinner so any
        additional widgets will be placed the left of the spinner, if visible
        (unless ``before`` is set).

        Parameters
        ----------
        widget : spyder.utils.qthelpers.SpyderAction | QWidget
            The action or widget to add to the toolbar.
        before : spyder.utils.qthelpers.SpyderAction | QWidget | None, optional
            The action or widget to add ``widget`` before (to the right of).
            If ``None`` (the default), the widget will be added to the left
            of the left-most widget.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If either ``widget`` or ``before`` lacks a ``name`` attribute;
            a widget with the same ``name`` as ``widget`` was already added;
            a widget with ``before.name`` has not been added previously; or
            the first widget added is not the options (hamburger) menu widget.
        """
        self._corner_widget.add_widget(action_or_widget, before=before)

    def get_corner_widget(
        self, name: str
    ) -> spyder.utils.qthelpers.SpyderAction | QWidget | None:
        """
        Return a widget by its unique ID (i.e. its ``name`` attribute).

        Parameters
        ----------
        name : str
            The ``name`` attribute of the widget to return.

        Returns
        -------
        QWidget | None
            The widget object corresponding to ``name``, or ``None``
            if a widget with that ``name`` does not exist.
        """
        return self._corner_widget.get_widget(name)

    def start_spinner(self) -> None:
        """
        Start the default status spinner.

        Returns
        -------
        None
        """
        if self.ENABLE_SPINNER:
            self._spinner.start()

    def stop_spinner(self) -> None:
        """
        Stop the default status spinner.

        Returns
        -------
        None
        """
        if self.ENABLE_SPINNER:
            self._spinner.stop()

    def create_toolbar(self, toolbar_id: str) -> MainWidgetToolbar:
        """
        Create and add an auxiliary toolbar to the top of the plugin.

        Parameters
        ----------
        toolbar_id: str
            The unique identifier name of this toolbar.

        Returns
        -------
        MainWidgetToolbar
            The auxiliary toolbar object that was created.
        """
        toolbar = MainWidgetToolbar(parent=self)
        toolbar.ID = toolbar_id

        TOOLBAR_REGISTRY.register_reference(
            toolbar, toolbar_id, self.PLUGIN_NAME, self.CONTEXT_NAME
        )

        self._auxiliary_toolbars[toolbar_id] = toolbar
        self._toolbars_layout.addWidget(toolbar)

        return toolbar

    def get_options_menu(self) -> PluginMainWidgetOptionsMenu:
        """
        Return the options ("hamburger") menu for this widget.

        Returns
        -------
        PluginMainWidgetOptionsMenu
            The options ("hamburger") menu widget.
        """
        return self._options_menu

    def get_options_menu_button(self) -> QToolButton:
        """
        Return the options menu button for this widget.

        Returns
        -------
        QToolButton
            The button widget for the plugin options ("hamburger") menu.
        """
        return self._options_button

    def get_main_toolbar(self) -> MainWidgetToolbar:
        """
        Return the main toolbar of this widget.

        Returns
        -------
        MainWidgetToolbar
            The main toolbar of the widget that contains the options button.
        """
        return self._main_toolbar

    def get_auxiliary_toolbars(self) -> OrderedDict[MainWidgetToolbar]:
        """
        Return the auxiliary toolbars of this widget.

        Returns
        -------
        OrderedDict[MainWidgetToolbar]
            A dictionary with toolbar IDs as keys and their corresponding
            auxiliary toolbar widgets as values.
        """
        return self._auxiliary_toolbars

    def set_icon_size(self, icon_size: int) -> None:
        """
        Set the icon size of this widget's toolbars.

        Parameters
        ----------
        iconsize: int
            An integer corresponding to the size in pixels to which the icons
            of the plugin's toolbars need to be set.
        """
        self._icon_size = icon_size
        self._main_toolbar.set_icon_size(QSize(icon_size, icon_size))

    def show_status_message(self, message: str, timeout: int) -> None:
        """
        Show a message in the Spyder status bar.

        Parameters
        ----------
        message: str
            The message to display in the status bar.
        timeout: int
            The amount of time, in milliseconds, to display the message.
            If ``0``, the default, the message will be shown until a plugin
            calls :meth:`!show_status_message` again.

        Returns
        -------
        None
        """
        status_bar = self.statusBar()
        if status_bar.isVisible():
            status_bar.showMessage(message, timeout)

    def get_focus_widget(self) -> PluginMainWidget:
        """
        Get the widget to give focus to.

        This is called when this widget's dockwidget is raised to the top.

        Returns
        -------
        QWidget
            The widget to give focus to.
        """
        return self

    def update_margins(self, margin=None):
        """
        Update the margins of this widget's central widget.

        Parameters
        ----------
        margin: int | None
            The margins to use for the central widget, or ``None`` for the
            default margins.

        Returns
        -------
        None
        """
        layout = self.layout()
        if self._default_margins is None:
            self._default_margins = layout.getContentsMargins()

        if margin is not None:
            layout.setContentsMargins(margin, margin, margin, margin)
        else:
            layout.setContentsMargins(*self._default_margins)

    def update_title(self) -> None:
        """
        Update this widget's dockwidget title.

        Returns
        -------
        None
        """
        if self.dockwidget is not None:
            widget = self.dockwidget
        elif self.windowwidget is not None:
            widget = self.undocked_window
        else:
            return

        widget.setWindowTitle(self.get_title())

    def set_name(self, name: str) -> None:
        """
        Set this widget's name.

        .. note::

            Normally, this is set to the same as the plugin's name,
            :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`.

        Parameters
        ----------
        name : str
            The name to set.

        Returns
        -------
        None
        """
        self._name = name

    def get_name(self) -> str:
        """
        Return this widget's name.

        By default, the same as the plugin's name,
        :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`.

        Returns
        -------
        str
            The name of the widget, and normally the plugin as well.
        """
        return self._name

    def set_icon(self, icon: QIcon) -> None:
        """
        Set this widget's icon.

        Parameters
        ----------
        icon : QIcon
            The icon object to set as the widget's icon.

        Returns
        -------
        None
        """
        self._icon = icon

    def get_icon(self) -> QIcon:
        """
        Get this widget's icon.

        Returns
        -------
        QIcon
            The widget's icon object.
        """
        return self._icon

    def render_toolbars(self) -> None:
        """
        Render all toolbars of this widget.

        .. caution::

            This action can only be performed once.

        Returns
        -------
        None
        """
        # if not self._toolbars_already_rendered:
        self._main_toolbar.render()
        self._corner_toolbar.render()
        for __, toolbar in self._auxiliary_toolbars.items():
            toolbar.render()

            # self._toolbars_already_rendered = True

    # ---- For widgets with an empty message
    # -------------------------------------------------------------------------
    def set_content_widget(
        self, widget: QWidget, add_to_stack: bool = True
    ) -> None:
        """
        When there is an empty message, set the widget for actual content,

        Parameters
        ----------
        widget: QWidget
            Widget to set as the widget with actual (non-empty) content.
        add_to_stack: bool, optional
            Whether to add this widget to stacked widget that holds the empty
            message.

        Returns
        -------
        None
        """
        self._content_widget = widget

        if self._stack is not None:
            if add_to_stack:
                self._stack.addWidget(self._content_widget)
        else:
            # This is necessary to automatically set a layout for Find or the
            # Profiler when the user disables empty messages in Preferences.
            if self.SET_LAYOUT_WHEN_EMPTY:
                layout = QVBoxLayout()
                layout.addWidget(self._content_widget)
                self.setLayout(layout)

    def show_content_widget(self) -> None:
        """
        Show the widget that displays actual content instead of the empty one.

        Returns
        -------
        None
        """
        if (
            self._stack is not None
            and self._content_widget is not None
            and self._stack.indexOf(self._content_widget) != -1
        ):
            self._stack.setCurrentWidget(self._content_widget)

    def show_empty_message(self) -> None:
        """
        Show the empty message widget.

        Returns
        -------
        None
        """
        if self.SHOW_MESSAGE_WHEN_EMPTY and self.get_conf(
            "show_message_when_panes_are_empty", section="main"
        ):
            self._stack.setCurrentWidget(self._pane_empty)

    # ---- SpyderWindowWidget handling
    # -------------------------------------------------------------------------
    @Slot()
    def create_window(self) -> None:
        """
        Create an undocked window containing this widget.

        Returns
        -------
        None
        """
        logger.debug(f"Undocking plugin {self._name}")

        # Widgets
        self.windowwidget = window = SpyderWindowWidget(self)

        # If the close corner button is used
        self.windowwidget.sig_closed.connect(self.close_window)

        # Widget setup
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.setCentralWidget(self)
        window.setWindowIcon(self.get_icon())
        window.setWindowTitle(self.get_title())
        window.resize(self.size())

        # Restore window geometry
        geometry = self.get_conf("window_geometry", default="")
        if geometry:
            try:
                window.restoreGeometry(
                    QByteArray().fromHex(str(geometry).encode("utf-8"))
                )

                # Move to the primary screen if the window is not placed in a
                # visible location.
                window.move_to_primary_screen()
            except Exception:
                pass

        # Dock widget setup
        if self.dockwidget:
            self.dockwidget.setFloating(False)
            self.dockwidget.setVisible(False)

        self.set_ancestor(window)
        self._update_actions()
        window.show()

    @Slot()
    def dock_window(self) -> None:
        """
        Dock an undocked window with this widget back to the main window.

        Returns
        -------
        None
        """
        logger.debug(f"Docking window of plugin {self._name}")

        # Reset undocked state
        self.set_conf("window_was_undocked_before_hiding", False)

        # This avoids trying to close the window twice: once when calling
        # _close_window below and the other when Qt calls the closeEvent of
        # windowwidget
        self.windowwidget.blockSignals(True)

        # Close window
        self._close_window(switch_to_plugin=True)

        # Make plugin visible on main window
        self.dockwidget.setVisible(True)
        self.dockwidget.raise_()

    @Slot()
    def close_window(self) -> None:
        """
        Close undocked window when clicking on the close window button.

        This can either dock or hide the window, depending on whether the
        user hid the window before:

        * The default behavior is to dock the window, so that new users can
          experiment with the dock/undock functionality without surprises.
        * If the user closes the window by clicking on the :guilabel:`Close`
          action in the widget's options ("hamburger") menu or by
          going to the :menuselection:`Window --> Panes` menu,
          then we will hide it when they click on the close button again.
          That gives users the ability to show/hide panes without
          docking/undocking them first.

        Returns
        -------
        None
        """
        if self.get_conf("window_was_undocked_before_hiding", default=False):
            self.close_dock()
        else:
            self.dock_window()

    def _close_window(
        self, save_undocked: bool = False, switch_to_plugin: bool = True
    ) -> None:
        """
        Helper function to close the undocked window with different parameters.

        Parameters
        ----------
        save_undocked : bool, optional
            ``True`` if the window state (size and position) should be saved.
            If ``False``, the default, don't persist the window state.
        switch_to_plugin : bool, optional
            Whether to switch to the plugin after closing the window.
            If ``True`` (the default), will switch to the plugin.

        Returns
        -------
        None
        """
        if self.windowwidget is not None:
            # Save window geometry to restore it when undocking the plugin
            # again.
            geometry = self.windowwidget.saveGeometry()
            self.set_conf("window_geometry", qbytearray_to_str(geometry))

            # Save undocking state if requested
            if save_undocked:
                self.set_conf("undocked_on_window_close", True)

            # Fixes spyder-ide/spyder#10704
            self.__unsafe_window = self.windowwidget
            self.__unsafe_window.deleteLater()
            self.windowwidget.close()
            self.windowwidget = None

            # These actions can appear disabled when 'Dock' action is pressed
            self.undock_action.setDisabled(False)
            self.close_action.setDisabled(False)

            if self.dockwidget is not None:
                self.sig_update_ancestor_requested.emit()
                if switch_to_plugin:
                    # This is necessary to restore the main window layout when
                    # there's a maximized plugin on it when the user requests
                    # to dock back this plugin.
                    self.get_plugin().switch_to_plugin()

                self.dockwidget.setWidget(self)
                self._update_actions()
        else:
            # Reset undocked state
            self.set_conf("undocked_on_window_close", False)

    # ---- SpyderDockwidget handling
    # -------------------------------------------------------------------------
    def change_visibility(
        self, enable: bool, force_focus: bool | None = None
    ) -> None:
        """
        Raise this widget to the foreground, and/or grab its focus.

        Parameters
        ----------
        state : bool
            Whether the widget is being raised to the foreground
            (``True``) or set as not in the foreground (``False``).
            The latter does not actually send it to the background, but
            does configure it for not being actively shown (e.g. it disables
            its empty pane widget, if any).
        force_focus : bool | None, optional
            If ``True``, always give the widget keyboard focus when
            raising or un-raising it with this method. If ``None``, only give
            it focus when showing, not hiding (setting ``state`` to ``True``),
            and only if
            :attr:`SpyderDockablePlugin.RAISE_AND_FOCUS <spyder.api.plugins.SpyderDockablePlugin.RAISE_AND_FOCUS>`
            is ``True``. If ``False``, the default, don't give it focus
            regardless.

        Returns
        -------
        None
        """
        if self.dockwidget is None:
            return

        if enable:
            # Avoid double trigger of visibility change
            self.dockwidget.blockSignals(True)
            self.dockwidget.raise_()
            self.dockwidget.blockSignals(False)

        raise_and_focus = getattr(self, "RAISE_AND_FOCUS", None)

        if force_focus is None:
            if raise_and_focus and enable:
                focus_widget = self.get_focus_widget()
                if focus_widget:
                    focus_widget.setFocus()
        elif force_focus is True:
            focus_widget = self.get_focus_widget()
            if focus_widget:
                focus_widget.setFocus()
        elif force_focus is False:
            pass

        # If the widget is undocked, it's always visible
        self.is_visible = enable or (self.windowwidget is not None)

        if (
            self.SHOW_MESSAGE_WHEN_EMPTY
            and self.get_conf(
                "show_message_when_panes_are_empty", section="main"
            )
            # We need to do this validation to prevent errors after changing
            # the option above in Preferences and restarting Spyder.
            and self._pane_empty is not None
        ):
            self._pane_empty.set_visibility(self.is_visible)

        # TODO: Pending on plugin migration that uses this
        # if getattr(self, 'DISABLE_ACTIONS_WHEN_HIDDEN', None):
        #     for __, action in self.get_actions().items():
        #         action.setEnabled(is_visible)

    def toggle_view(self, checked: bool) -> None:
        """
        Show or hide this widget in the Spyder interface.

        Used to show or hide it from the from the
        :menuselection:`Window --> Panes` menu.

        Parameters
        ----------
        value : bool
            Whether to show (``True``) or hide (``False``) this widget.

        Returns
        -------
        None

        Notes
        -----
        If you need to attach some functionality when this changes, use
        :attr:`sig_toggle_view_changed`. For an example, please see
        :mod:`spyder.plugins.onlinehelp.widgets`.
        """
        if not self.dockwidget:
            return

        # To check if the plugin needs to be undocked at the end
        undock = False

        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            self.is_visible = True

            # We need to undock the plugin if that was its state before
            # toggling its visibility.
            if (
                # Don't run this while the window is being created to not
                # affect setting up the layout at startup.
                not self._plugin.main.is_setting_up
                and self.get_conf(
                    "window_was_undocked_before_hiding", default=False
                )
            ):
                undock = True
        else:
            if self.windowwidget is not None:
                logger.debug(f"Closing window of plugin {self._name}")

                # This avoids trying to close the window twice: once when
                # calling _close_window below and the other when Qt calls the
                # closeEvent of windowwidget
                self.windowwidget.blockSignals(True)

                # Dock plugin if it's undocked before hiding it.
                self._close_window(switch_to_plugin=False)

                # Save undocked state to restore it afterwards.
                self.set_conf("window_was_undocked_before_hiding", True)

            self.dockwidget.hide()
            self.is_visible = False

        # Update toggle view status, if needed, without emitting signals.
        if self.toggle_view_action.isChecked() != checked:
            self.blockSignals(True)
            self.toggle_view_action.setChecked(checked)
            self.blockSignals(False)

        self.sig_toggle_view_changed.emit(checked)

        logger.debug(
            f"Plugin {self._name} is now {'visible' if checked else 'hidden'}"
        )

        if undock:
            # We undock the plugin at this point so that the Window menu is
            # updated correctly.
            self.create_window()

    def create_dockwidget(
        self, mainwindow: spyder.app.mainwindow.MainWindow
    ) -> tuple[spyder.widgets.dock.SpyderDockWidget, Qt.DockWidgetArea]:
        """
        Add this widget to the parent Spyder main window as a dock widget.

        Parameters
        ----------
        mainwindow : spyder.app.mainwindow.MainWindow
            The main window to set as the dockwidget's parent.

        Returns
        -------
        spyder.widgets.dock.SpyderDockWidget
            The newly created dock widget.
        Qt.DockWidgetArea
            The area of the window the dockwidget is placed in.
        """
        # Creating dock widget
        title = self.get_title()
        self.dockwidget = dock = SpyderDockWidget(title, mainwindow)

        # Setup
        dock.setObjectName(self.__class__.__name__ + "_dw")
        dock.setWidget(self)

        # Signals
        dock.visibilityChanged.connect(self.change_visibility)
        dock.topLevelChanged.connect(self._on_top_level_change)
        dock.sig_title_bar_shown.connect(self._on_title_bar_shown)

        return (dock, dock.LOCATION)

    @Slot()
    def close_dock(self) -> None:
        """
        Close the dockwidget.

        Returns
        -------
        None
        """
        logger.debug(f"Hiding plugin {self._name}")
        self.toggle_view_action.setChecked(False)

    def lock_unlock_position(self) -> None:
        """
        Show/hide title bar to move/lock this widget's position.

        Returns
        -------
        None
        """
        if isinstance(self.dockwidget.titleBarWidget(), DockTitleBar):
            self.dockwidget.remove_title_bar()
        else:
            self.dockwidget.set_title_bar()

    def get_maximized_state(self) -> bool:
        """
        Get this widget's maximized state.

        Returns
        -------
        bool
            ``True`` if the widget is maximized, ``False`` otherwise.
        """
        return self._is_maximized

    def set_maximized_state(self, state: bool) -> None:
        """
        Set the attribute that holds this widget's maximized state.

        Parameters
        ----------
        state: bool
            ``True`` to set the widget as maximized, ``False`` set it as not
            maximized.

        Returns
        -------
        None
        """
        self._is_maximized = state

    # ---- API: methods to define or override
    # ------------------------------------------------------------------------
    def get_title(self) -> str:
        """
        Return the title that will be displayed on dockwidgets or windows.

        Returns
        -------
        str
            This dockwidget's tab/window title.

        Raises
        ------
        NotImplementedError
            If the main widget subclass doesn't define a ``get_title`` method.
        """
        raise NotImplementedError("PluginMainWidget must define `get_title`!")

    def set_ancestor(self, ancestor: QWidget) -> None:
        """
        Update the ancestor/parent of child widgets when undocking.

        Parameters
        ----------
        ancestor: QWidget
            The window widget to set as a parent of this one.

        Returns
        -------
        None
        """
        pass

    def setup(self) -> None:
        """
        Create widget actions, add to menus and perform other setup steps.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            If the main widget subclass doesn't define a ``setup`` method.
        """
        raise NotImplementedError(
            f"{type(self)} must define a `setup` method!"
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
            "A PluginMainWidget subclass must define an `update_actions` "
            f"method! Hint: {type(self)} should implement `update_actions`"
        )

    def on_close(self) -> None:
        """
        Perform actions before the widget is closed.

        Does nothing by default; intended to be overridden for widgets
        that need to perform actions on close.

        .. warning::

            This method **must** only operate on local attributes.

        Returns
        -------
        None
        """
        pass

    def on_focus_in(self) -> None:
        """
        Perform actions when the widget receives focus.

        Does nothing by default; intended to be overridden for widgets
        that need to perform actions on gaining focus.

        Returns
        -------
        None
        """
        pass

    def on_focus_out(self) -> None:
        """
        Perform actions when the widget loses focus.

        Does nothing by default; intended to be overridden for widgets
        that need to perform actions on loosing focus.

        Returns
        -------
        None
        """
        pass


def _run_test() -> None:
    # Third party imports
    from qtpy.QtWidgets import QHBoxLayout, QTableWidget, QMainWindow

    # Local imports
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    main = QMainWindow()
    widget = PluginMainWidget("test", main)
    widget.get_title = lambda x=None: "Test title"
    widget._setup()
    layout = QHBoxLayout()
    layout.addWidget(QTableWidget())
    widget.setLayout(layout)
    widget.start_spinner()
    dock, location = widget.create_dockwidget(main)
    main.addDockWidget(location, dock)
    main.setStyleSheet(str(APP_STYLESHEET))
    main.show()
    app.exec_()


if __name__ == "__main__":
    _run_test()
