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
import functools
from collections import OrderedDict
import types
from typing import Any

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QSizePolicy, QToolBar, QWidget

# Local imports
from spyder.api.config.mixins import (
    SpyderConfigurationObserver, SpyderConfigurationAccessor)
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets.menus import SpyderMenu
from spyder.config.types import ConfigurationKey
from spyder.config.manager import CONF
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action, create_toolbutton


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
        toolbuttons = getattr(self, '_toolbuttons', None)
        if toolbuttons is None:
            self._toolbuttons = OrderedDict()

        if name in self._toolbuttons:
            raise SpyderAPIError(
                'Tool button name "{}" already in use!'.format(name)
            )

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
            option=option
        )
        toolbutton.name = name

        if toggled:
            if section is not None and option is not None:
                value = CONF.get(section, option)
                toolbutton.setChecked(value)

        self._toolbuttons[name] = toolbutton
        return toolbutton

    def get_toolbutton(self, name):
        """
        Return toolbutton by name.
        """
        toolbuttons = getattr(self, '_toolbuttons', None)
        if toolbuttons is None:
            self._toolbuttons = OrderedDict()

        if name in self._toolbuttons:
            raise SpyderAPIError(
                'Tool button name "{0}" not found! Available names are: {1}'
                ''.format(name, list(self._toolbuttons.keys()))
            )

        return self._toolbuttons[name]

    def get_toolbuttons(self):
        """
        Return all toolbuttons.
        """
        toolbuttons = getattr(self, '_toolbuttons', None)
        if toolbuttons is None:
            self._toolbuttons = OrderedDict()

        return self._toolbuttons


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

    def create_toolbar(self, name):
        """
        Create a Spyder toolbar.
        """
        toolbars = getattr(self, '_toolbars', None)
        if toolbars is None:
            self._toolbars = OrderedDict()

        if name in self._toolbars:
            raise SpyderAPIError('Toolbar "{}" already created!'.format(name))

        toolbar = QToolBar(self)
        self._toolbars[name] = toolbar
        return toolbar

    def get_toolbar(self, name):
        """
        Return toolbar by name.
        """
        toolbars = getattr(self, '_toolbars', None)
        if toolbars is None:
            self._toolbars = OrderedDict()

        if name not in self._toolbars:
            raise SpyderAPIError('Toolbar "{}" not found!'.format(name))

        return self._toolbars[name]

    def get_toolbars(self):
        """
        Return all toolbars.
        """
        toolbars = getattr(self, '_toolbars', None)
        if toolbars is None:
            self._toolbars = OrderedDict()

        return self._toolbars


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

        menus = getattr(self, '_menus', None)
        if menus is None:
            self._menus = OrderedDict()

        if name in self._menus:
            raise SpyderAPIError(
                'Menu name "{}" already in use!'.format(name)
            )

        menu = SpyderMenu(parent=self, title=text)
        if icon is not None:
            menu.menuAction().setIconVisibleInMenu(True)
            menu.setIcon(icon)

        self._menus[name] = menu
        return menu

    def get_menu(self, name):
        """
        Return name for menu.
        """
        menus = getattr(self, '_menus', None)
        if menus is None:
            self._menus = OrderedDict()

        if name not in self._menus:
            raise SpyderAPIError(
                'Invalid menu name, valid names are: {}'.format(
                    list(self._menus.keys()))
            )

        return self._menus.get(name)

    def get_menus(self, name):
        """
        Return menus dictionary.
        """
        menus = getattr(self, '_menus', None)
        if menus is None:
            self._menus = OrderedDict()

        return self._menus


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
        actions = getattr(self, '_actions', None)
        if actions is None:
            self._actions = OrderedDict()

        if triggered is None and toggled is None:
            raise SpyderAPIError(
                'Action must provide the toggled or triggered parameters!'
            )

        # Check name
        if name in self._actions:
            raise SpyderAPIError(
                'Action name "{}" already in use!'.format(name)
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
            option=option
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

        self._actions[name] = action
        return action

    def get_action(self, name):
        """
        Return an action by name.
        """
        actions = getattr(self, '_actions', None)
        if actions is None:
            self._actions = OrderedDict()

        if name not in self._actions:
            raise SpyderAPIError(
                'Inavlid action name "{0}", valid names are: {1}'.format(
                    name, list(self._actions.keys()))
            )

        return self._actions.get(name)

    def get_actions(self):
        """
        Return all actions defined by the widget.

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
        actions = getattr(self, '_actions', None)
        if actions is None:
            self._actions = OrderedDict()

        return self._actions

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
    def __init__(self, class_parent=None):
        if getattr(self, 'CONF_SECTION', None) is None:
            if hasattr(class_parent, 'CONF_SECTION'):
                # Inherit class_parent CONF_SECTION value
                self.CONF_SECTION = class_parent.CONF_SECTION
        super().__init__()

    @staticmethod
    def create_icon(name, image_file=False):
        """
        Create an icon by name using the spyder Icon manager.
        """
        if image_file:
            icon = ima.get_icon(name)
        else:
            icon = ima.icon(name)
        return icon

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
