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
from collections import OrderedDict

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMenu, QSizePolicy, QToolBar, QWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets.menus import SpyderMenu
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)


class SpyderOptionMixin:
    """
    This mixin provides option handling tools for any widget that needs to
    track options, their state and methods to call on option change.

    These options will usually be tied to configuration options in the Spyder
    configuration files (e.g. spyder.ini). Some options might not be connected
    to configuration options, and in this case using DEFAULT_OPTIONS is
    prefered instead of using class attributes.
    """
    # EXAMPLE: {'option_1': value_1, 'option_2': value_2, ...}
    DEFAULT_OPTIONS = {}

    @staticmethod
    def _find_option_mixin_children(obj, all_children):
        """
        Find all children of `obj` that use SpyderOptionMixin recursively.

        `all_children` is a list on which to append the results.
        """
        children = obj.findChildren(SpyderOptionMixin)
        all_children.extend(children)

        if obj not in all_children:
            all_children.append(obj)

        for child in children:
            children = child.findChildren(SpyderOptionMixin)
            all_children.extend(children)

        return all_children

    def _check_options_dictionary_exist(self):
        """
        Helper method to check the options dictionary has been initialized.
        """
        options = getattr(self, '_options', None)
        if options is None:
            self._options = self.DEFAULT_OPTIONS

    def _check_options_exist(self, options):
        """
        Helper method to check that an option was defined in the
        DEFAULT_OPTIONS dictionary.
        """
        for option in options:
            if option not in self.DEFAULT_OPTIONS:
                raise SpyderAPIError(
                    'Option "{0}" has not been defined in the the widget '
                    'DEFAULT_OPTIONS attribute! Options are: '
                    '{1}'.format(option, self.DEFAULT_OPTIONS)
                )

    def _set_option(self, option, value, emit):
        """
        Helper method to set/change options with option to emit signal.
        """
        # Check if a togglable action exists with this name and update state
        try:
            action_name = 'toggle_{}_action'.format(option)
            self._update_action_state(action_name, value)
        except SpyderAPIError:
            pass

        self._check_options_dictionary_exist()
        if option in self.DEFAULT_OPTIONS:
            self._options[option] = value
            self.on_option_update(option, value)

            if emit:
                self.sig_option_changed.emit(option, value)
        else:
            raise SpyderAPIError(
                'Option "{}" has not been defined in the widget '
                'DEFAULT_OPTIONS attribute!'
                ''.format(option)
            )

    def get_option(self, option):
        """
        Return option for this widget.

        `option` must be defined in the DEFAULT_OPTIONS class attribute.
        """
        self._check_options_dictionary_exist()
        if option in self.DEFAULT_OPTIONS:
            return self._options[option]

        raise SpyderAPIError(
            'Option "{0}" has not been defined in the widget DEFAULT_OPTIONS '
            'attribute {1}'.format(option, self.DEFAULT_OPTIONS)
        )

    def get_options(self):
        """
        Return the current options dictionary.
        """
        self._check_options_dictionary_exist()
        return self._options

    def set_option(self, option, value):
        """
        Set option for this widget.

        `option` must be defined in the DEFAULT_OPTIONS class attribute.
        Setting an option will emit the sig_option_changed signal and will
        call the `on_option_update` method.
        """
        signal = getattr(self, 'sig_option_changed', None)
        if signal is None:
            raise SpyderAPIError(
                'A Spyder widget must define a '
                '"sig_option_changed = Signal(str, object)" signal!'
            )
        self._set_option(option, value, emit=True)

    def set_options(self, options):
        """
        Set options for this widget.

        `options` must be defined in the DEFAULT_OPTIONS class attribute.
        Setting each option will emit the sig_option_changed signal and will
        call the `on_option_update` method.

        This method will propagate the options on all children.
        """
        parent_and_children = self._find_option_mixin_children(self, [self])
        for child in parent_and_children:
            child_options = self.options_from_keys(options,
                                                   child.DEFAULT_OPTIONS)
            child._check_options_exist(child_options)

            for option, value in child_options.items():
                child.set_option(option, value)

    def change_option(self, option, value):
        """
        Change option for this widget.

        `option` must be defined in the DEFAULT_OPTIONS class attribute.
        Changing an option will call the `on_option_update` method.
        """
        self._set_option(option, value, emit=False)

    def change_options(self, options):
        """
        Change options for this widget.

        `options` must be defined in the DEFAULT_OPTIONS class attribute.
        Changing each option will call the `on_option_update` method.

        This method will propagate the options on all children.
        """
        parent_and_children = self._find_option_mixin_children(self, [self])
        for child in parent_and_children:
            child_options = self.options_from_keys(options,
                                                   child.DEFAULT_OPTIONS)
            child._check_options_exist(child_options)

            for option, value in child_options.items():
                child.change_option(option, value)

    def options_from_keys(self, options, keys):
        """
        Create an options dictionary that only contains given `keys`.
        """
        new_options = {}
        for option in keys:
            if option in options:
                new_options[option] = options[option]

        return new_options

    def on_option_update(self, option, value):
        """
        When an option is set or changed, this method is called.
        """
        raise NotImplementedError(
            'Widget must define a `on_option_update` method!')


class SpyderToolButtonMixin:
    """
    Provide methods to create, add and get toolbuttons.
    """

    def create_toolbutton(self, name, text=None, icon=None,
                          tip=None, toggled=None, triggered=None,
                          autoraise=True, text_beside_icon=False):
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
        )
        toolbutton.name = name
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


class SpyderToolBarMixin:
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

    def create_menu(self, name, text=None):
        """
        Create a menu.

        Parameters
        ----------
        name: str
            Unique str identifier.
        text: str
            Localized text string.

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
                      register_shortcut=True, parent=None):
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
        toggled: callable
            The callable to use when toggling this action
        triggered: callable
            The callable to use when triggering this action.
        shortcut_context: str
            Set the `str` context of the shortcut.
        context: Qt.ShortcutContext
            Set the context for the shortcut.
        initial: object
            Sets the initial state of a togglable action. This does not emit
            the toggled signal.
        register_shortcut: bool (True)
            If True, main window will expose the shortcut in Preferences.
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

        action = create_action(
            parent,
            text=text,
            icon=icon,
            tip=tip,
            toggled=toggled,
            triggered=triggered,
            context=context,
        )
        action.name = name
        if icon_text:
            action.setIconText(icon_text)

        action.text_beside_icon = bool(icon_text)
        action.shortcut_context = shortcut_context
        action.register_shortcut = register_shortcut

        if initial is not None:
            if toggled:
                self.blockSignals(True)
                action.setChecked(initial)
                self.blockSignals(False)
            elif triggered:
                raise SpyderAPIError(
                    'Initial values can only apply to togglable actions!')

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
                        SpyderOptionMixin, SpyderToolButtonMixin):
    """
    Basic functionality for all Spyder widgets and Qt items.

    This mixin does not include toolbar handling as that is limited to the
    application with the coreui plugin or the PluginMainWidget for dockable
    plugins.

    This provides a simple management of widget options, as well as Qt helpers
    for defining the actions a widget provides.
    """

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
