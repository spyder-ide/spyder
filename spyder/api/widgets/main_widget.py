# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main plugin widget.

SpyderDockablePlugin plugins must provide a WIDGET_CLASS attribute that is a
subclass of PluginMainWidget.
"""

# Standard library imports
from collections import OrderedDict
import os
import sys
import textwrap
from typing import Optional

# Third party imports
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QHBoxLayout, QSizePolicy, QToolButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.api.widgets.auxiliary_widgets import (MainCornerWidget,
                                                  SpyderWindowWidget)
from spyder.api.widgets.menus import (MainWidgetMenu, OptionsMenuSections,
                                      PluginMainWidgetMenus)
from spyder.api.widgets.mixins import SpyderToolbarMixin, SpyderWidgetMixin
from spyder.api.widgets.toolbars import MainWidgetToolbar
from spyder.utils.qthelpers import create_waitspinner, set_menu_icons
from spyder.utils.registries import (
    ACTION_REGISTRY, TOOLBAR_REGISTRY, MENU_REGISTRY)
from spyder.utils.stylesheet import (
    APP_STYLESHEET, PANES_TABBAR_STYLESHEET, PANES_TOOLBAR_STYLESHEET)
from spyder.widgets.dock import SpyderDockWidget
from spyder.widgets.tabs import Tabs

# Localization
_ = get_translation('spyder')


class PluginMainWidgetWidgets:
    CornerWidget = 'corner_widget'
    MainToolbar = 'main_toolbar_widget'
    OptionsToolButton = 'options_button_widget'
    Spinner = 'spinner_widget'


class PluginMainWidgetActions:
    ClosePane = 'close_pane'
    DockPane = 'dock_pane'
    UndockPane = 'undock_pane'


class PluginMainWidget(QWidget, SpyderWidgetMixin, SpyderToolbarMixin):
    """
    Spyder plugin main widget class.

    This class handles both a dockwidget pane and a floating window widget
    (undocked pane).

    Notes
    -----
    All Spyder dockable plugins define a main widget that must subclass this.

    This widget is a subclass of QMainWindow that consists of a single,
    central widget and a set of toolbars that are stacked above or below
    that widget.

    The toolbars are not moveable nor floatable and must occupy the entire
    horizontal space available for the plugin. This mean that toolbars must be
    stacked vertically and cannot be placed horizontally next to each other.
    """

    # --- Attributes
    # ------------------------------------------------------------------------
    ENABLE_SPINNER = False
    """
    This attribute enables/disables showing a spinner on the top right to the
    left of the corner menu widget (Hamburguer menu).

    Plugins that provide actions that take time should make this `True` and
    use accordingly with the `start_spinner`/`stop_spinner` methods.

    The Find in files plugin is an example of a core plugin that uses it.

    Parameters
    ----------
    ENABLE_SPINNER: bool
        If `True` an extra space will be added to the toolbar (even if the
        spinner is not moving) to avoid items jumping to the left/right when
        the spinner appears. If `False` no extra space will be added. Default
        is False.
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

    sig_toggle_view_changed = Signal(bool)
    """
    This action is emitted to inform the visibility of a dockable plugin
    has changed.

    This is triggered by checking/unchecking the entry for a pane in the
    `View > Panes` menu.

    Parameters
    ----------
    visible: bool
        New visibility of the dockwidget.
    """

    sig_update_ancestor_requested = Signal()
    """
    This signal is emitted to inform the main window that a child widget
    needs its ancestor to be updated.
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(parent=parent, class_parent=plugin)

        # Attributes
        # --------------------------------------------------------------------
        self._is_tab = False
        self._name = name
        self._plugin = plugin
        self._parent = parent
        self._default_margins = None
        self.is_maximized = None
        self.is_visible = None
        self.dock_action = None
        self.undock_action = None
        self.close_action = None
        self._toolbars_already_rendered = False

        # Attribute used to access the action, toolbar, toolbutton and menu
        # registries
        self.PLUGIN_NAME = name

        # We create our toggle action instead of using the one that comes with
        # dockwidget because it was not possible to raise and focus the plugin
        self.toggle_view_action = None
        self._toolbars = OrderedDict()
        self._auxiliary_toolbars = OrderedDict()

        # Widgets
        # --------------------------------------------------------------------
        self.windowwidget = None
        self.dockwidget = None
        self._icon = QIcon()
        self._spinner = None

        if self.ENABLE_SPINNER:
            self._spinner = create_waitspinner(size=16, parent=self)

        self._corner_widget = MainCornerWidget(
            parent=self,
            name=PluginMainWidgetWidgets.CornerWidget,
        )

        self._main_toolbar = MainWidgetToolbar(
            parent=self,
            title=_("Main widget toolbar"),
        )
        self._main_toolbar.ID = 'main_toolbar'

        TOOLBAR_REGISTRY.register_reference(
            self._main_toolbar, self._main_toolbar.ID,
            self.PLUGIN_NAME, self.CONTEXT_NAME)

        self._corner_toolbar = MainWidgetToolbar(
            parent=self,
            title=_("Main widget corner toolbar"),
        )
        self._corner_toolbar.ID = 'corner_toolbar',

        TOOLBAR_REGISTRY.register_reference(
            self._corner_toolbar, self._corner_toolbar.ID,
            self.PLUGIN_NAME, self.CONTEXT_NAME)

        self._corner_toolbar.setSizePolicy(QSizePolicy.Minimum,
                                           QSizePolicy.Expanding)
        self._options_menu = self.create_menu(
            PluginMainWidgetMenus.Options,
            title=_('Options menu'),
        )

        # Layout
        # --------------------------------------------------------------------
        # These margins are necessary to give some space between the widgets
        # inside this widget and the window vertical separator.
        self._margin_left = 1
        self._margin_right = 1

        self._main_layout = QVBoxLayout()
        self._toolbars_layout = QVBoxLayout()
        self._main_toolbar_layout = QHBoxLayout()

        self._toolbars_layout.setContentsMargins(
            self._margin_left, 0, self._margin_right, 0)
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

    # --- Private Methods
    # ------------------------------------------------------------------------
    def _setup(self):
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
            text=_('Options'),
            icon=self.create_icon('tooloptions'),
        )

        self.add_corner_widget(
            PluginMainWidgetWidgets.OptionsToolButton,
            self._options_button,
        )
        if self.ENABLE_SPINNER:
            self.add_corner_widget(
                PluginMainWidgetWidgets.Spinner,
                self._spinner,
            )

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
            icon=self.create_icon('dock'),
            triggered=self.close_window,
        )
        self.undock_action = self.create_action(
            name=PluginMainWidgetActions.UndockPane,
            text=_("Undock"),
            tip=_("Undock the pane"),
            icon=self.create_icon('undock'),
            triggered=self.create_window,
        )
        self.close_action = self.create_action(
            name=PluginMainWidgetActions.ClosePane,
            text=_("Close"),
            tip=_("Close the pane"),
            icon=self.create_icon('close_pane'),
            triggered=self.close_dock,
        )
        # We use this instead of the QDockWidget.toggleViewAction
        self.toggle_view_action = self.create_action(
            name='switch to ' + self._name,
            text=self.get_title(),
            toggled=lambda checked: self.toggle_view(checked),
            context=Qt.WidgetWithChildrenShortcut,
            shortcut_context='_',
        )

        bottom_section = OptionsMenuSections.Bottom
        for item in [self.undock_action, self.close_action, self.dock_action]:
            self.add_item_to_menu(
                item,
                self._options_menu,
                section=bottom_section,
            )

        self._options_button.setMenu(self._options_menu)
        self._options_menu.aboutToShow.connect(self._update_actions)

        # Hide icons in Mac plugin menus
        if sys.platform == 'darwin':
            self._options_menu.aboutToHide.connect(
                lambda menu=self._options_menu: set_menu_icons(menu, False))

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
        self._update_style()

    def _update_style(self):
        """
        Update style of the widget.
        """
        qss = r"""
            QToolButton::menu-indicator {
                image: none;
            }
            QToolButton {
                margin: 0px;
            }
            """
        self._options_button.setStyleSheet(textwrap.dedent(qss))

    def _update_actions(self):
        """
        Refresh Options menu.
        """
        show_dock_actions = self.windowwidget is None
        self.undock_action.setVisible(show_dock_actions)
        self.close_action.setVisible(show_dock_actions)
        self.dock_action.setVisible(not show_dock_actions)

        if sys.platform == 'darwin':
            try:
                set_menu_icons(
                    self.get_menu(PluginMainWidgetMenus.Options), True)
            except KeyError:
                # Prevent unexpected errors on the test suite.
                pass

        # Widget setup
        # --------------------------------------------------------------------
        self.update_actions()
        self._update_style()

    @Slot(bool)
    def _on_top_level_change(self, top_level):
        """
        Actions to perform when a plugin is undocked to be moved.
        """
        self.undock_action.setDisabled(top_level)

    # --- Public Qt overriden methods
    # ------------------------------------------------------------------------
    def setLayout(self, layout):
        """
        Set layout of the main widget of this plugin.
        """
        self._main_layout.addLayout(layout, stretch=1000000)
        super().setLayout(self._main_layout)
        layout.setContentsMargins(self._margin_left, 0, self._margin_right, 0)
        layout.setSpacing(0)

    # --- Public methods to use
    # ------------------------------------------------------------------------
    def get_plugin(self):
        """
        Return the parent plugin.
        """
        return self._plugin

    def get_action(self, name, context: Optional[str] = None,
                   plugin: Optional[str] = None):
        """
        Return action by name.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context

        return ACTION_REGISTRY.get_reference(name, plugin, context)

    def add_corner_widget(self, widget_id, widget, before=None):
        """
        Add widget to corner, that is to the left of the last added widget.

        Parameters
        ----------
        widget_id: str
            Unique name of the widget.
        widget: QWidget
            Any QWidget to add in the corner widget.
        before: QWidget
            Insert the widget before this widget.

        Notes
        -----
        By default widgets are added to the left of the last corner widget.

        The central widget provides an options menu button and a spinner so any
        additional widgets will be placed to the left of the spinner,
        if visible.
        """
        self._corner_widget.add_widget(widget_id, widget)

    def get_corner_widget(self, name):
        """
        Return the a widget inside the corner widget by name.

        Parameters
        ----------
        name: str
            Unique name of the widget.
        """
        return self._corner_widget.get_widget(name)

    def start_spinner(self):
        """
        Start default status spinner.
        """
        if self.ENABLE_SPINNER:
            self._spinner.start()

    def stop_spinner(self):
        """
        Stop default status spinner.
        """
        if self.ENABLE_SPINNER:
            self._spinner.stop()

    def create_toolbar(self, toolbar_id):
        """
        Create and add an auxiliary toolbar to the top of the plugin.

        Parameters
        ----------
        toolbar_id: str
            Unique toolbar string identifier.

        Returns
        -------
        SpyderPluginToolbar
            The auxiliary toolbar that was created and added to the plugin
            interface.
        """
        toolbar = MainWidgetToolbar(parent=self)
        toolbar.ID = toolbar_id

        TOOLBAR_REGISTRY.register_reference(
            toolbar, toolbar_id, self.PLUGIN_NAME, self.CONTEXT_NAME)

        self._auxiliary_toolbars[toolbar_id] = toolbar
        self._toolbars_layout.addWidget(toolbar)

        return toolbar

    def create_menu(self, menu_id, title='', icon=None):
        """
        Override SpyderMenuMixin method to use a different menu class.

        Parameters
        ----------
        menu_id: str
            Unique toolbar string identifier.
        title: str
            Toolbar localized title.
        icon: QIcon or None
            Icon to use for the menu.

        Returns
        -------
        MainWidgetMenu
            The main widget menu.
        """
        menus = getattr(self, '_menus', None)
        if menus is None:
            self._menus = OrderedDict()

        if menu_id in self._menus:
            raise SpyderAPIError(
                'Menu name "{}" already in use!'.format(menu_id)
            )

        menu = MainWidgetMenu(parent=self, title=title)
        menu.ID = menu_id

        MENU_REGISTRY.register_reference(
            menu, menu.ID, self.PLUGIN_NAME, self.CONTEXT_NAME)

        if icon is not None:
            menu.menuAction().setIconVisibleInMenu(True)
            menu.setIcon(icon)

        self._menus[menu_id] = menu
        return menu

    def get_options_menu(self):
        """
        Return the main options menu of the widget.
        """
        return self._options_menu

    def get_options_menu_button(self):
        """
        Return the main options menu button of the widget.
        """
        return self._options_button

    def get_main_toolbar(self):
        """
        Return the main toolbar of the plugin.

        Returns
        -------
        QToolBar
            The main toolbar of the widget that contains the options button.
        """
        return self._main_toolbar

    def get_auxiliary_toolbars(self):
        """
        Return the auxiliary toolbars of the plugin.

        Returns
        -------
        OrderedDict
            A dictionary of wirh toolbar IDs as keys and auxiliary toolbars as
            values.
        """
        return self._auxiliary_toolbars

    def set_icon_size(self, icon_size):
        """
        Set the icon size of the plugin's toolbars.

        Parameters
        ----------
        iconsize: int
            An integer corresponding to the size in pixels to which the icons
            of the plugin's toolbars need to be set.
        """
        self._icon_size = icon_size
        self._main_toolbar.set_icon_size(QSize(icon_size, icon_size))

    def show_status_message(self, message, timeout):
        """
        Show a status message in the Spyder widget.
        """
        status_bar = self.statusBar()
        if status_bar.isVisible():
            status_bar.showMessage(message, timeout)

    def get_focus_widget(self):
        """
        Get the widget to give focus to.

        Returns
        -------
        QWidget
            QWidget to give focus to.

        Notes
        -----
        This is applied when the plugin's dockwidget is raised to the top.
        """
        return self

    def update_margins(self, margin=None):
        """
        Update central widget margins.
        """
        layout = self.layout()
        if self._default_margins is None:
            self._default_margins = layout.getContentsMargins()

        if margin is not None:
            layout.setContentsMargins(margin, margin, margin, margin)
        else:
            layout.setContentsMargins(*self._default_margins)

    def update_title(self):
        """
        Update title of dockwidget or plugin window.
        """
        if self.dockwidget is not None:
            widget = self.dockwidget
        elif self.windowwidget is not None:
            widget = self.undocked_window
        else:
            return

        widget.setWindowTitle(self.get_title())

    def set_name(self, name):
        """
        Set widget name (plugin.NAME).
        """
        self._name = name

    def get_name(self):
        """
        Return widget name (plugin.NAME).
        """
        return self._name

    def set_icon(self, icon):
        """
        Set widget icon.
        """
        self._icon = icon

    def get_icon(self):
        """
        Return widget icon.
        """
        return self._icon

    def render_toolbars(self):
        """
        Render all the toolbars of the widget.

        Notes
        -----
        This action can only be performed once.
        """
        # if not self._toolbars_already_rendered:
        self._main_toolbar._render()
        self._corner_toolbar._render()
        for __, toolbar in self._auxiliary_toolbars.items():
            toolbar._render()

            # self._toolbars_already_rendered = True

    # --- SpyderDockwidget handling ------------------------------------------
    # ------------------------------------------------------------------------
    @Slot()
    def create_window(self):
        """
        Create a QMainWindow instance containing this SpyderWidget.
        """
        # Widgets
        self.windowwidget = window = SpyderWindowWidget(self)

        # If the close corner button is used
        self.windowwidget.sig_closed.connect(self.close_window)

        # Wigdet setup
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.setCentralWidget(self)
        window.setWindowIcon(self.get_icon())
        window.setWindowTitle(self.get_title())
        window.resize(self.size())

        if self.dockwidget:
            self.dockwidget.setFloating(False)
            self.dockwidget.setVisible(False)

        self.set_ancestor(window)
        self._update_actions()
        window.sig_closed.connect(self.close_window)
        window.show()

    @Slot()
    def close_window(self):
        """
        Close QMainWindow instance that contains this SpyderWidget.
        """
        if self.windowwidget is not None:
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
                self.dockwidget.setWidget(self)
                self.dockwidget.setVisible(True)
                self.dockwidget.raise_()
                self._update_actions()

    def change_visibility(self, enable, force_focus=None):
        """
        Dock widget visibility has changed.
        """
        is_visible = not self.is_visible

        if self.dockwidget is None:
            return

        if enable:
            # Avoid double trigger of visibility change
            self.dockwidget.blockSignals(True)
            self.dockwidget.raise_()
            self.dockwidget.blockSignals(False)

        raise_and_focus = getattr(self, 'RAISE_AND_FOCUS', None)

        if force_focus is None:
            if raise_and_focus or not is_visible:
                focus_widget = self.get_focus_widget()
                if focus_widget:
                    focus_widget.setFocus()
        elif force_focus is True:
            focus_widget = self.get_focus_widget()
            if focus_widget:
                focus_widget.setFocus()
        elif force_focus is False:
            pass

        self.is_visible = enable

        # TODO: Pending on plugin migration that uses this
        # if getattr(self, 'DISABLE_ACTIONS_WHEN_HIDDEN', None):
        #     for __, action in self.get_actions().items():
        #         action.setEnabled(is_visible)

    def toggle_view(self, checked):
        """
        Toggle dockwidget's visibility when its entry is selected in
        the menu `View > Panes`.

        Parameters
        ----------
        checked: bool
            Is the entry in `View > Panes` checked or not?

        Notes
        -----
        If you need to attach some functionality when this changes, use
        sig_toggle_view_changed. For an example, please see
        `spyder/plugins/ipythonconsole/plugin.py`
        """
        if not self.dockwidget:
            return

        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            self.is_visible = True
        else:
            self.dockwidget.hide()
            self.is_visible = False

        # Update toggle view status, if needed, without emitting signals.
        if self.toggle_view_action.isChecked() != checked:
            self.blockSignals(True)
            self.toggle_view_action.setChecked(checked)
            self.blockSignals(False)

        self.sig_toggle_view_changed.emit(checked)

    def create_dockwidget(self, mainwindow):
        """
        Add to parent QMainWindow as a dock widget.
        """
        # Creating dock widget
        title = self.get_title()
        self.dockwidget = dock = SpyderDockWidget(title, mainwindow)

        # Setup
        dock.setObjectName(self.__class__.__name__ + '_dw')
        dock.setWidget(self)

        # Signals
        dock.visibilityChanged.connect(self.change_visibility)
        dock.topLevelChanged.connect(self._on_top_level_change)

        return (dock, dock.LOCATION)

    @Slot()
    def close_dock(self):
        """
        Close the dockwidget.
        """
        self.toggle_view(False)

    # --- API: methods to define or override
    # ------------------------------------------------------------------------
    def get_title(self):
        """
        Return the title that will be displayed on dockwidget or window title.
        """
        raise NotImplementedError('PluginMainWidget must define `get_title`!')

    def set_ancestor(self, ancestor):
        """
        Needed to update the ancestor/parent of child widgets when undocking.
        """
        pass

    def setup(self):
        """
        Create widget actions, add to menu and other setup requirements.
        """
        raise NotImplementedError(
            'A PluginMainWidget subclass must define a `setup` '
            'method!')

    def update_actions(self):
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the self.create_action method.
        """
        raise NotImplementedError(
            'A PluginMainWidget subclass must define an `update_actions` '
            f'method! Hint: {type(self)} should implement `update_actions`')


def run_test():
    # Third party imports
    from qtpy.QtWidgets import QHBoxLayout, QTableWidget, QMainWindow

    # Local imports
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    main = QMainWindow()
    widget = PluginMainWidget('test', main)
    widget.get_title = lambda x=None: 'Test title'
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


if __name__ == '__main__':
    run_test()
