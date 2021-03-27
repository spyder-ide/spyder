# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API Mixins.
"""

# Standard library imports
from typing import Any, Optional, Dict

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QSizePolicy, QToolBar, QWidget, QToolButton

# Local imports
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets.menus import SpyderMenu
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import create_action, create_toolbutton
from spyder.utils.registries import (
    ACTION_REGISTRY, MENU_REGISTRY, TOOLBAR_REGISTRY, TOOLBUTTON_REGISTRY)


class SpyderToolButtonMixin:
    """
    Provide methods to create, add and get toolbuttons.
    """

    def create_toolbutton(self, name, text=None, icon=None,
                          tip=None, toggled=None, triggered=None,
                          autoraise=True, text_beside_icon=False,
                          section=None, option=None):
        """
        Create a Spyder toolbutton.
        """
        if toggled and not callable(toggled):
            toggled = lambda value: None

        if toggled is not None:
            if section is None and option is not None:
                section = self.CONF_SECTION

        toolbutton = create_toolbutton(
            self,
            text=text,
            shortcut=None,
            icon=icon,
            tip=tip,
            toggled=toggled,
            triggered=triggered,
            autoraise=autoraise,
            text_beside_icon=text_beside_icon,
            section=section,
            option=option,
            id_=name,
            plugin=self.PLUGIN_NAME,
            context_name=self.CONTEXT_NAME,
            register_toolbutton=True
        )
        toolbutton.name = name

        if toggled:
            if section is not None and option is not None:
                value = CONF.get(section, option)
                toolbutton.setChecked(value)

        return toolbutton

    def get_toolbutton(self, name: str, context: Optional[str] = None,
                       plugin: Optional[str] = None) -> QToolButton:
        """
        Return toolbutton by name, plugin and context.

        Parameters
        ----------
        name: str
            Name of the toolbutton to retrieve.
        context: Optional[str]
            Widget or context identifier under which the toolbutton was stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the toolbutton was defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        toolbutton: QToolButton
            The corresponding toolbutton stored under the given `name`,
            `context` and `plugin`.

        Raises
        ------
        KeyError
            If either of `name`, `context` or `plugin` keys do not exist in the
            toolbutton registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBUTTON_REGISTRY.get_reference(name, plugin, context)

    def get_toolbuttons(self, context: Optional[str] = None,
                        plugin: Optional[str] = None) -> Dict[str, QToolButton]:
        """
        Return all toolbuttons defined by a context on a given plugin.

        Parameters
        ----------
        context: Optional[str]
            Widget or context identifier under which the toolbuttons were
            stored. If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the toolbuttons were defined.
            If None, then `PLUGIN_NAME` is used.

        Returns
        -------
        toolbuttons: Dict[str, QToolButton]
            A dictionary that maps string keys to their corresponding
            toolbuttons.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBUTTON_REGISTRY.get_references(plugin, context)


class SpyderToolbarMixin:
    """
    Provide methods to create, add and get toolbars.
    """

    def add_item_to_toolbar(self, action_or_widget, toolbar, section=None,
                            before=None):
        """
        If you provide a `before` action, the action will be placed before this
        one, so the section option will be ignored, since the action will now
        be placed in the same section as the `before` action.
        """
        toolbar.add_item(action_or_widget, section=section, before=before)

    def create_stretcher(self):
        """
        Create a stretcher widget to be used in a Qt toolbar.
        """
        stretcher = QWidget()
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return stretcher

    def create_toolbar(self, name: str) -> QToolBar:
        """
        Create a Spyder toolbar.
        """
        toolbar = QToolBar(self)
        TOOLBAR_REGISTRY.register_reference(
            toolbar, name, self.PLUGIN_NAME, self.CONTEXT_NAME)
        return toolbar

    def get_toolbar(self, name: str, context: Optional[str] = None,
                    plugin: Optional[str] = None) -> QToolBar:
        """
        Return toolbar by name, plugin and context.

        Parameters
        ----------
        name: str
            Name of the toolbar to retrieve.
        context: Optional[str]
            Widget or context identifier under which the toolbar was stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the toolbar was defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        toolbar: QToolBar
            The corresponding toolbar stored under the given `name`, `context`
            and `plugin`.

        Raises
        ------
        KeyError
            If either of `name`, `context` or `plugin` keys do not exist in the
            toolbar registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBAR_REGISTRY.get_reference(name, plugin, context)

    def get_toolbars(self, context: Optional[str] = None,
                     plugin: Optional[str] = None) -> Dict[str, QToolBar]:
        """
        Return all toolbars defined by a context on a given plugin.

        Parameters
        ----------
        context: Optional[str]
            Widget or context identifier under which the toolbars were stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the toolbars were defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        toolbars: Dict[str, QToolBar]
            A dictionary that maps string keys to their corresponding toolbars.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBAR_REGISTRY.get_references(plugin, context)


class SpyderMenuMixin:
    """
    Provide methods to create, add and get menus.

    This mixin uses a custom menu object that allows for the creation of
    sections in a simple way.
    """

    def add_item_to_menu(self, action_or_menu, menu, section=None,
                         before=None):
        """
        Add a SpyderAction or a QWidget to the menu.
        """
        if not isinstance(menu, SpyderMenu):
            raise SpyderAPIError('Menu must be an instance of SpyderMenu!')

        menu.add_action(action_or_menu, section=section, before=before)

    def create_menu(self, name, text=None, icon=None):
        """
        Create a menu.

        Parameters
        ----------
        name: str
            Unique str identifier.
        text: str or None
            Localized text string.
        icon: QIcon or None
            Icon to use for the menu.

        Return: QMenu
            Return the created menu.
        """
        from spyder.api.widgets.menus import SpyderMenu

        menu = SpyderMenu(parent=self, title=text)
        if icon is not None:
            menu.menuAction().setIconVisibleInMenu(True)
            menu.setIcon(icon)

        MENU_REGISTRY.register_reference(
            menu, name, self.PLUGIN_NAME, self.CONTEXT_NAME)
        return menu

    def get_menu(self, name: str, context: Optional[str] = None,
                 plugin: Optional[str] = None) -> SpyderMenu:
        """
        Return a menu by name, plugin and context.

        Parameters
        ----------
        name: str
            Name of the menu to retrieve.
        context: Optional[str]
            Widget or context identifier under which the menu was stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the menu was defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        menu: SpyderMenu
            The corresponding menu stored under the given `name`, `context`
            and `plugin`.

        Raises
        ------
        KeyError
            If either of `name`, `context` or `plugin` keys do not exist in the
            toolbar registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return MENU_REGISTRY.get_reference(name, plugin, context)

    def get_menus(self, context: Optional[str] = None,
                  plugin: Optional[str] = None) -> Dict[str, SpyderMenu]:
        """
        Return all menus defined by a context on a given plugin.

        Parameters
        ----------
        context: Optional[str]
            Widget or context identifier under which the menus were stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the menus were defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        menus: Dict[str, SpyderMenu]
            A dictionary that maps string keys to their corresponding menus.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return MENU_REGISTRY.get_references(plugin, context)


class SpyderActionMixin:
    """
    Provide methods to create, add and get actions in a unified way.

    This mixin uses a custom action object.
    """

    def _update_action_state(self, action_name, value):
        """
        This allows to update the state of a togglable action without emitting
        signals.

        This is useful when the global application configuration changes and
        we need to propagate the current state of an action based on those
        changes
        """
        self.blockSignals(True)
        try:
            self.get_action(action_name).setChecked(value)
        except SpyderAPIError:
            pass
        self.blockSignals(False)

    # Comment: The word `context` is used for two different concepts.
    # On one side it refers to a Qt widget shortcut context and on the
    # other it refers to a section of the configuration (or the widget
    # name where it is applied).
    def create_action(self, name, text, icon=None, icon_text='', tip=None,
                      toggled=None, triggered=None, shortcut_context=None,
                      context=Qt.WidgetWithChildrenShortcut, initial=None,
                      register_shortcut=False, section=None, option=None,
                      parent=None):
        """
        name: str
            unique identifiable name for the action
        text: str
           Localized text for the action
        icon: QIcon,
            Icon for the action when applied to menu or toolbutton.
        icon_text: str
            Icon for text in toolbars. If True, this will also disable
            the tooltip on this toolbutton if part of a toolbar.
        tip: str
            Tooltip to define for action on menu or toolbar.
        toggled: Optional[Union[Callable, bool]]
            If True, then the action modifies the configuration option on the
            section specified. Otherwise, it should be a callable to use
            when toggling this action. If None, then the action does not
            behave like a checkbox.
        triggered: callable
            The callable to use when triggering this action.
        shortcut_context: str
            Set the `str` context of the shortcut.
        context: Qt.ShortcutContext
            Set the context for the shortcut.
        initial: object
            Sets the initial state of a togglable action. This does not emit
            the toggled signal.
        section: Optional[str]
            Name of the configuration section whose option is going to be
            modified. If None, and `option` is not None, then it defaults to
            the class `CONF_SECTION` attribute.
        option: ConfigurationKey
            Name of the configuration option whose value is reflected and
            affected by the action.
        register_shortcut: bool, optional
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.
        parent: QWidget (None)
            Define the parent of the widget. Use `self` if not provided.

        Notes
        -----
        There is no need to set shortcuts right now. We only create actions
        with this (and similar methods) and these are then exposed as possible
        shortcuts on plugin registration in the main window with the
        register_shortcut argument.

        If icon_text is True, this will also disable the tooltip.

        If a shortcut is found in the default config then it is assigned,
        otherwise it's left blank for the user to define one for it.
        """
        if triggered is None and toggled is None:
            raise SpyderAPIError(
                'Action must provide the toggled or triggered parameters!'
            )

        if parent is None:
            parent = self

        if toggled and not callable(toggled):
            toggled = lambda value: None

        if toggled is not None:
            if section is None and option is not None:
                section = self.CONF_SECTION

        action = create_action(
            parent,
            text=text,
            icon=icon,
            tip=tip,
            toggled=toggled,
            triggered=triggered,
            context=context,
            section=section,
            option=option,
            id_=name,
            plugin=self.PLUGIN_NAME,
            context_name=self.CONTEXT_NAME,
            register_action=True
        )
        action.name = name
        if icon_text:
            action.setIconText(icon_text)

        action.text_beside_icon = bool(icon_text)
        action.shortcut_context = shortcut_context
        action.register_shortcut = register_shortcut
        action.tip = tip

        if initial is not None:
            if toggled:
                action.setChecked(initial)
            elif triggered:
                raise SpyderAPIError(
                    'Initial values can only apply to togglable actions!')
        else:
            if toggled:
                if section is not None and option is not None:
                    value = CONF.get(section, option)
                    action.setChecked(value)

        return action

    def get_action(self, name: str, context: Optional[str] = None,
                   plugin: Optional[str] = None) -> Any:
        """
        Return an action by name, context and plugin.

        Parameters
        ----------
        name: str
            Name of the action to retrieve.
        context: Optional[str]
            Widget or context identifier under which the action was stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the action was defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        action: SpyderAction
            The corresponding action stored under the given `name`, `context`
            and `plugin`.

        Raises
        ------
        KeyError
            If either of `name`, `context` or `plugin` keys do not exist in the
            toolbar registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context

        return ACTION_REGISTRY.get_reference(name, plugin, context)

    def get_actions(self, context: Optional[str] = None,
                    plugin: Optional[str] = None) -> dict:
        """
        Return all actions defined by a context on a given plugin.

        Parameters
        ----------
        context: Optional[str]
            Widget or context identifier under which the actions were stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the actions were defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        actions: Dict[str, SpyderAction]
            A dictionary that maps string keys to their corresponding actions.

        Notes
        -----
        1. Actions should be created once. Creating new actions on menu popup
           is *highly* discouraged.
        2. Actions can be created directly on a PluginMainWidget or
           PluginMainContainer subclass. Child widgets can also create
           actions, but they need to subclass SpyderWidgetMixin.
        3. PluginMainWidget or PluginMainContainer will collect any actions
           defined in subwidgets (if defined) and expose them in the
           get_actions method at the plugin level.
        4. Any action created this way is now exposed as a possible shortcut
           automatically without manual shortcut registration.
           If an option is found in the config system then it is assigned,
           otherwise it's left with an empty shortcut.
        5. There is no need to override this method.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return ACTION_REGISTRY.get_references(plugin, context)

    def update_actions(self, options):
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the `create_action` method.
        """
        raise NotImplementedError('')


class SpyderWidgetMixin(SpyderActionMixin, SpyderMenuMixin,
                        SpyderConfigurationObserver, SpyderToolButtonMixin):
    """
    Basic functionality for all Spyder widgets and Qt items.

    This mixin does not include toolbar handling as that is limited to the
    application with the coreui plugin or the PluginMainWidget for dockable
    plugins.

    This provides a simple management of widget options, as well as Qt helpers
    for defining the actions a widget provides.
    """

    # Plugin name identifier used to store actions, toolbars, toolbuttons
    # and menus
    PLUGIN_NAME = None

    # Context name used to store actions, toolbars, toolbuttons and menus
    CONTEXT_NAME = None

    def __init__(self, class_parent=None):
        for attr in ['CONF_SECTION', 'PLUGIN_NAME']:
            if getattr(self, attr, None) is None:
                if hasattr(class_parent, attr):
                    # Inherit class_parent CONF_SECTION/PLUGIN_NAME value
                    setattr(self, attr, getattr(class_parent, attr))

        super().__init__()

    @staticmethod
    def create_icon(name):
        """
        Create an icon by name using the spyder Icon manager.
        """
        return ima.icon(name)

    def update_style(self):
        """
        Update stylesheet and style of the widget.

        This method will be called recursively on all widgets on theme change.
        """
        pass

    def update_translation(self):
        """
        Update localization of the widget.

        This method will be called recursively on all widgets on language
        change.
        """
        pass
