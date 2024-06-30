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
from typing import Any, Optional, Dict

# Third party imports
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QIcon, QImage, QPainter, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import (
    QApplication, QMainWindow, QSizePolicy, QToolBar, QWidget, QToolButton
)

# Local imports
from spyder.api.config.mixins import (
    SpyderConfigurationAccessor,
    SpyderConfigurationObserver
)
from spyder.api.exceptions import SpyderAPIError
from spyder.api.shortcuts import SpyderShortcutsMixin
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.toolbars import SpyderToolbar
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.qthelpers import create_action, create_toolbutton
from spyder.utils.registries import (
    ACTION_REGISTRY, MENU_REGISTRY, TOOLBAR_REGISTRY, TOOLBUTTON_REGISTRY)
from spyder.utils.stylesheet import PANES_TOOLBAR_STYLESHEET


class SpyderToolButtonMixin:
    """
    Provide methods to create, add and get toolbuttons.
    """

    def create_toolbutton(self, name, text=None, icon=None,
                          tip=None, toggled=None, triggered=None,
                          autoraise=True, text_beside_icon=False,
                          section=None, option=None, register=True):
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
            register_toolbutton=register
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
                            before=None, before_section=None):
        """
        If you provide a `before` action, the action will be placed before this
        one, so the section option will be ignored, since the action will now
        be placed in the same section as the `before` action.
        """
        toolbar.add_item(action_or_widget, section=section, before=before,
                         before_section=before_section)

    def create_stretcher(self, id_=None):
        """
        Create a stretcher widget to be used in a Qt toolbar.
        """
        stretcher = QWidget(self)
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if id_ is not None:
            stretcher.ID = id_
        return stretcher

    def create_toolbar(
        self,
        name: str,
        register: bool = True
    ) -> SpyderToolbar:
        """
        Create a Spyder toolbar.

        Parameters
        ----------
        name: str
            Name of the toolbar to create.
        register: bool
            Whether to register the toolbar in the global registry.
        """
        toolbar = SpyderToolbar(self, name)
        toolbar.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))
        if register:
            TOOLBAR_REGISTRY.register_reference(
                toolbar, name, self.PLUGIN_NAME, self.CONTEXT_NAME
            )
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

    def _create_menu(
        self,
        menu_id: str,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        icon: Optional[QIcon] = None,
        reposition: Optional[bool] = True,
        register: bool = True,
        min_width: Optional[int] = None,
        MenuClass=SpyderMenu
    ) -> SpyderMenu:
        """
        Create a SpyderMenu or a subclass of it.

        Notes
        -----
        * This method must only be used directly to generate a menu that is a
          subclass of SpyderMenu.
        * Refer to the documentation for `SpyderMenu` to learn about its args.
        """
        if register:
            menus = getattr(self, '_menus', None)
            if menus is None:
                self._menus = OrderedDict()

            if menu_id in self._menus:
                raise SpyderAPIError(
                    'Menu name "{}" already in use!'.format(menu_id)
                )

        menu = MenuClass(
            parent=self if parent is None else parent,
            menu_id=menu_id,
            title=title,
            min_width=min_width,
            reposition=reposition
        )

        if icon is not None:
            menu.menuAction().setIconVisibleInMenu(True)
            menu.setIcon(icon)

        if register:
            MENU_REGISTRY.register_reference(
                menu, menu_id, self.PLUGIN_NAME, self.CONTEXT_NAME
            )
            self._menus[menu_id] = menu

        return menu

    def create_menu(
        self,
        menu_id: str,
        title: Optional[str] = None,
        icon: Optional[QIcon] = None,
        reposition: Optional[bool] = True,
        register: bool = True
    ) -> SpyderMenu:
        """
        Create a menu for Spyder.

        Parameters
        ----------
        menu_id: str
            Unique str identifier for the menu.
        title: str or None
            Localized text string for the menu.
        icon: QIcon or None
            Icon to use for the menu.
        reposition: bool, optional (default True)
            Whether to vertically reposition the menu due to its padding.
        register: bool
            Whether to register the menu in the global registry.

        Returns
        -------
        SpyderMenu
            The created menu.
        """
        return self._create_menu(
            menu_id=menu_id,
            title=title,
            icon=icon,
            reposition=reposition,
            register=register
        )

    def get_menu(
        self,
        name: str,
        context: Optional[str] = None,
        plugin: Optional[str] = None
    ) -> SpyderMenu:
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
            menu registry.
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
                      toggled=None, triggered=None, data=None,
                      shortcut_context=None,
                      context=Qt.WidgetWithChildrenShortcut, initial=None,
                      register_shortcut=False, section=None, option=None,
                      parent=None, register_action=True, overwrite=False,
                      context_name=None, menurole=None):
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
        data: Any
            Data to be set on the action.
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
        register_action: bool, optional
            If True, the action will be registered and searchable.
            The default value is `True`.
        overwrite: bool, optional
            If True, in case of action overwriting no warning will be shown.
            The default value is `False`
        context_name: Optional[str]
            Name of the context that holds the action in case of registration.
            The combination of `name` and `context_name` is unique so trying
            to register an action with the same `name` and `context_name` will
            cause a warning unless `overwrite` is set to `True`.
        menurole: QAction.MenuRole, optional
            Menu role for the action (it only has effect on macOS).

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
            data=data,
            context=context,
            section=section,
            option=option,
            id_=name,
            plugin=self.PLUGIN_NAME,
            context_name=(
                self.CONTEXT_NAME if context_name is None else context_name),
            register_action=register_action,
            overwrite=overwrite,
            menurole=menurole
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
            action registry.
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


class SpyderWidgetMixin(
    SpyderActionMixin,
    SpyderConfigurationObserver,
    SpyderMenuMixin,
    SpyderToolbarMixin,
    SpyderToolButtonMixin,
    SpyderShortcutsMixin,
):
    """
    Basic functionality for all Spyder widgets and Qt items.

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


class SpyderMainWindowMixin:
    """
    Mixin with additional functionality for the QMainWindow's used in Spyder.
    """

    def _is_on_visible_screen(self: QMainWindow):
        """Detect if the window is placed on a visible screen."""
        x, y = self.geometry().x(), self.geometry().y()
        qapp = QApplication.instance()
        current_screen = qapp.screenAt(QPoint(x, y))

        if current_screen is None:
            return False
        else:
            return True

    def move_to_primary_screen(self: QMainWindow):
        """Move the window to the primary screen if necessary."""
        if self._is_on_visible_screen():
            return

        qapp = QApplication.instance()
        primary_screen_geometry = qapp.primaryScreen().availableGeometry()
        x, y = primary_screen_geometry.x(), primary_screen_geometry.y()

        if self.isMaximized():
            self.showNormal()

        self.move(QPoint(x, y))

        # With this we want to maximize only the Spyder main window and not the
        # plugin ones, which usually are not maximized.
        if not hasattr(self, 'is_window_widget'):
            self.showMaximized()


class SvgToScaledPixmap(SpyderConfigurationAccessor):
    """
    Mixin to transform an SVG to a QPixmap that is scaled according to the
    factor set by users in Preferences.
    """

    def svg_to_scaled_pixmap(self, svg_file, rescale=None, in_package=True):
        """
        Transform svg to a QPixmap that is scaled according to the factor set
        by users in Preferences.

        Parameters
        ----------
        svg_file: str
            Name of or path to the svg file.
        rescale: float, optional
            Rescale pixmap according to a factor between 0 and 1.
        in_package: bool, optional
            Get svg from the `images` folder in the Spyder package.
        """
        if in_package:
            image_path = get_image_path(svg_file)

        if self.get_conf('high_dpi_custom_scale_factor', section='main'):
            scale_factors = self.get_conf(
                'high_dpi_custom_scale_factors',
                section='main'
            )
            scale_factor = float(scale_factors.split(":")[0])
        else:
            scale_factor = 1

        # Get width and height
        pm = QPixmap(image_path)
        width = pm.width()
        height = pm.height()

        # Rescale but preserving aspect ratio
        if rescale is not None:
            aspect_ratio = width / height
            width = int(width * rescale)
            height = int(width / aspect_ratio)

        # Paint image using svg renderer
        image = QImage(
            int(width * scale_factor), int(height * scale_factor),
            QImage.Format_ARGB32_Premultiplied
        )
        image.fill(0)
        painter = QPainter(image)
        renderer = QSvgRenderer(image_path)
        renderer.render(painter)
        painter.end()

        # This is also necessary to make the image look good for different
        # scale factors
        if scale_factor > 1.0:
            image.setDevicePixelRatio(scale_factor)

        # Create pixmap out of image
        final_pm = QPixmap.fromImage(image)
        final_pm = final_pm.copy(
            0, 0, int(width * scale_factor), int(height * scale_factor)
        )

        return final_pm
