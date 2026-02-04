# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Released under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Mixin classes for the Spyder widget API.
"""

from __future__ import annotations

# Standard library imports
from collections import OrderedDict
from typing import Any, TYPE_CHECKING

# Third party imports
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QImage, QPainter, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import QApplication, QSizePolicy, QWidget

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.exceptions import SpyderAPIError
from spyder.api.shortcuts import SpyderShortcutsMixin
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.toolbars import SpyderToolbar
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.qthelpers import create_action, create_toolbutton
from spyder.utils.registries import (
    ACTION_REGISTRY,
    MENU_REGISTRY,
    TOOLBAR_REGISTRY,
    TOOLBUTTON_REGISTRY,
)
from spyder.utils.stylesheet import PANES_TOOLBAR_STYLESHEET
from spyder.utils.svg_colorizer import SVGColorize

if TYPE_CHECKING:
    from collections.abc import Callable

    from qtpy.QtCore import QObject
    from qtpy.QtGui import QIcon
    from qtpy.QtWidgets import QAction, QMainWindow, QToolButton

    import spyder.utils.qthelpers  # For SpyderAction
    import spyder.config.types  # For ConfigurationKey


class SpyderToolButtonMixin:
    """
    Provide methods to create, add and get toolbar buttons.
    """

    def create_toolbutton(
        self,
        name: str,
        text: str | None = None,
        icon: QIcon | str | None = None,
        tip: str | None = None,
        toggled: Callable[[Any], None] | bool | None = None,
        triggered: Callable[[], None] | None = None,
        autoraise: bool = True,
        text_beside_icon: bool = False,
        section: str | None = None,
        option: spyder.config.types.ConfigurationKey | None = None,
        register: bool = True,
    ) -> QToolButton:
        """
        Create a new Spyder toolbar button.

        Parameters
        ----------
        name: str
            Unique identifier for the toolbutton.
        text: str | None, optional
           Localized text for the toolbutton, displayed in the interface.
           If ``None``, the default, no text is shown.
        icon: QIcon | str | None, optional
            Icon name or object to use in the toolbutton.
            If ``None``, the default, no icon is shown.
        tip: str | None, optional
            Tooltip text for the toolbutton.
            If ``None`` (the default), no tooltip is shown.
        toggled: Callable[[Any], None] | bool | None, optional
            If ``None`` (default) then the button doesn't act like a checkbox.
            If ``True``, then the button modifies the configuration ``option``
            on the ``section`` specified (or the default
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` if
            ``section`` is not set). Otherwise, must be a callable,
            called when toggling this button. One of ``toggled`` and
            ``triggered`` must not be ``None``.
        triggered: Callable[[], None] | None, optional
            If a callable, will be called when triggering this button.
            Otherwise, if ``None`` (the default), this will not be a
            triggered button and ``toggled`` must be non-``None`` instead.
        autoraise : bool, optional
            If ``True`` (the default), the button will only draw a 3D frame
            when hovered over. If ``False``, will draw the button frame
            all the time.
        text_beside_icon : bool, optional
            If ``True``, the button text will be displayed beside the icon.
            If ``False`` (the default), will only show the icon.
        section: str | None, optional
            Name of the configuration section whose ``option`` is going to be
            modified. If ``None`` (the default) and ``option`` is not ``None``,
            then it defaults to the class'
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` attribute.
        option: spyder.config.types.ConfigurationKey | None, optional
            Name of the configuration option whose value is reflected and
            affected by the button. If ``None`` (the default), no option
            is associated with this button, e.g. for buttons that are
            ``triggered`` rather than ``toggled``.
        register_action: bool, optional
            If ``True`` (default) the action will be registered and searchable.
            If ``False``, the action will be created but not registered.

        Returns
        -------
        QToolButton
            The toolbar button object that was created.
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
            register_toolbutton=register,
        )
        toolbutton.name = name

        if toggled:
            if section is not None and option is not None:
                value = CONF.get(section, option)
                toolbutton.setChecked(value)

        return toolbutton

    def get_toolbutton(
        self,
        name: str,
        context: str | None = None,
        plugin: str | None = None,
    ) -> QToolButton:
        """
        Retrieve a toolbar button by name, context and plugin.

        Parameters
        ----------
        name: str
            Identifier of the toolbutton to retrieve.
        context: str | None, optional
            Context identifier under which the toolbutton was stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the toolbutton was defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        QToolButton
            The corresponding toolbutton widget stored under the given
            ``name``, ``context`` and ``plugin``.

        Raises
        ------
        KeyError
            If the combination of ``name``, ``context`` and ``plugin`` keys
            does not exist in the toolbutton registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBUTTON_REGISTRY.get_reference(name, plugin, context)

    def get_toolbuttons(
        self, context: str | None = None, plugin: str | None = None
    ) -> dict[str, QToolButton]:
        """
        Return all toolbar buttons defined by a context on a given plugin.

        Parameters
        ----------
        context: str | None, optional
            Context identifier under which the toolbuttons were stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the toolbuttons were defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        dict[str, QToolButton]
            A dictionary that maps identifier name keys to their corresponding
            toolbutton objects.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBUTTON_REGISTRY.get_references(plugin, context)


class SpyderToolbarMixin:
    """
    Provide methods to create, add and get toolbars.
    """

    def add_item_to_toolbar(
        self,
        action_or_widget: spyder.utils.qthelpers.SpyderAction | QWidget,
        toolbar: SpyderToolbar,
        section: str | None = None,
        before: str | None = None,
        before_section: str | None = None,
    ) -> None:
        """
        Add the given action or widget to this toolbar.

        Parameters
        ----------
        action_or_widget : spyder.utils.qthelpers.SpyderAction | QWidget
            The action or widget to add to the toolbar.
        toolbar : SpyderToolbar
            The toolbar object to add ``action_or_widget`` to.
        section: str | None, optional
            The section id in which to insert the ``action_or_widget``,
            or ``None`` (default) for no section.
        before: str | None, optional
            Make the ``action_or_widget`` appear before the action with the
            identifier ``before``. If ``None`` (default), add it to the end.
            If ``before`` is not ``None``, ``before_section`` will be ignored.
        before_section : str | None, optional
            Make the ``section`` appear prior to ``before_section``.
            If ``None`` (the default), add the section to the end.
            If you provide a ``before`` action, the new action will be placed
            before this one, so the section option will be ignored, since the
            action will now be placed in the same section as the ``before``
            action.

        Returns
        -------
        None
        """
        toolbar.add_item(
            action_or_widget,
            section=section,
            before=before,
            before_section=before_section,
        )

    def create_stretcher(self, id_: str | None = None) -> QWidget:
        """
        Create a stretcher widget to be used in a Spyder toolbar.

        Parameters
        ----------
        id_ : str | None, optional
            The identifier for the stretcher widget. If ``None`` (the default),
            no id will be set.

        Returns
        -------
        QWidget
            The created stretcher widget.
        """
        stretcher = QWidget(self)
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if id_ is not None:
            stretcher.ID = id_
        return stretcher

    def create_toolbar(
        self, name: str, register: bool = True
    ) -> SpyderToolbar:
        """
        Create a Spyder toolbar.

        Parameters
        ----------
        name: str
            Unique string identifier name of the toolbar to create.
        register: bool, optional
            If ``True`` (default), register the toolbar in the global registry.
            If ``False``, don't register it.

        Returns
        -------
        SpyderToolbar
            The created toolbar object.
        """
        toolbar = SpyderToolbar(self, name)
        toolbar.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))
        if register:
            TOOLBAR_REGISTRY.register_reference(
                toolbar, name, self.PLUGIN_NAME, self.CONTEXT_NAME
            )
        return toolbar

    def get_toolbar(
        self,
        name: str,
        context: str | None = None,
        plugin: str | None = None,
    ) -> SpyderToolbar:
        """
        Return toolbar by name, context and plugin.

        Parameters
        ----------
        name: str
            Identifier of the toolbar to retrieve.
        context: str | None, optional
            Context identifier under which the toolbar was stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the toolbar was defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        SpyderToolbar
            The corresponding toolbar widget stored under the given
            ``name``, ``context`` and ``plugin``.

        Raises
        ------
        KeyError
            If the combination of ``name``, ``context`` and ``plugin`` keys
            does not exist in the toolbar registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return TOOLBAR_REGISTRY.get_reference(name, plugin, context)

    def get_toolbars(
        self, context: str | None = None, plugin: str | None = None
    ) -> dict[str, SpyderToolbar]:
        """
        Return all toolbars defined by a context on a given plugin.

        Parameters
        ----------
        context: str | None, optional
            Context identifier under which the toolbars were stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the toolbars were defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        dict[str, SpyderToolbar]
            A dictionary that maps identifier name keys to their corresponding
            toolbar objects.
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

    def add_item_to_menu(
        self,
        action_or_menu: spyder.utils.qthelpers.SpyderAction | SpyderMenu,
        menu: SpyderMenu,
        section: str | None = None,
        before: str | None = None,
        before_section: str | None = None,
    ) -> None:
        """
        Add the given action or widget to the menu.

        Parameters
        ----------
        action_or_menu : spyder.utils.qthelpers.SpyderAction | SpyderMenu
            The action or submenu to add to the menu.
        menu : SpyderMenu
            The menu object to add ``action_or_menu`` to.
        section: str | None, optional
            The section id in which to insert the ``action_or_menu``,
            or ``None`` (default) for no section.
        before: str | None, optional
            Make the ``action_or_menu`` appear before the action with the
            identifier ``before``. If ``None`` (default), add it to the end.
            If ``before`` is not ``None``, ``before_section`` will be ignored.
        before_section : str | None, optional
            Make the ``section`` appear prior to ``before_section``.
            If ``None`` (the default), add the section to the end.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``menu`` is not an instance of
            :class:`~spyder.api.widgets.menus.SpyderMenu`.
        """
        if not isinstance(menu, SpyderMenu):
            raise SpyderAPIError("Menu must be an instance of SpyderMenu!")

        menu.add_action(
            action_or_menu,
            section=section,
            before=before,
            before_section=before_section,
        )

    def _create_menu(
        self,
        menu_id: str,
        parent: QWidget | None = None,
        title: str | None = None,
        icon: QIcon | None = None,
        reposition: bool = True,
        register: bool = True,
        min_width: int | None = None,
        MenuClass: type[SpyderMenu] = SpyderMenu,
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
            menus = getattr(self, "_menus", None)
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
            reposition=reposition,
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
        title: str | None = None,
        icon: QIcon | None = None,
        reposition: bool = True,
        register: bool = True,
    ) -> SpyderMenu:
        """
        Create a menu for Spyder.

        Parameters
        ----------
        menu_id: str
            Unique string identifier name for the menu to create.
        title: str | None, optional
            Localized title for the menu.
        icon: QIcon | None, optional
            Icon object to use for the menu.
        reposition: bool, optional
            If ``True`` (the default), vertically reposition the menu per
            its padding. If ``False``, don't reposition.
        register: bool, optional
            If ``True`` (default), register the menu in the global registry.
            If ``False``, don't register it.

        Returns
        -------
        SpyderMenu
            The created menu object.
        """
        return self._create_menu(
            menu_id=menu_id,
            title=title,
            icon=icon,
            reposition=reposition,
            register=register,
        )

    def get_menu(
        self,
        name: str,
        context: str | None = None,
        plugin: str | None = None,
    ) -> SpyderMenu:
        """
        Return a menu by name, context and plugin.

        Parameters
        ----------
        name: str
            Identifier of the menu to retrieve.
        context: str | None, optional
            Context identifier under which the menu was stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the menu was defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        SpyderMenu
            The corresponding menu widget stored under the given
            ``name``, ``context`` and ``plugin``.

        Raises
        ------
        KeyError
            If the combination of ``name``, ``context`` and ``plugin`` keys
            does not exist in the menu registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return MENU_REGISTRY.get_reference(name, plugin, context)

    def get_menus(
        self, context: str | None = None, plugin: str | None = None
    ) -> dict[str, SpyderMenu]:
        """
        Return all menus defined by a context on a given plugin.

        Parameters
        ----------
        context: str | None, optional
            Context identifier under which the menus were stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the menus were defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        dict[str, SpyderMenu]
            A dictionary that maps identifier name keys to their corresponding
            menu objects.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return MENU_REGISTRY.get_references(plugin, context)


class SpyderActionMixin:
    """
    Provide methods to create, add and get actions in a unified way.

    This mixin uses a custom action object.
    """

    def _update_action_state(self, action_name: str, value: bool) -> None:
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
    def create_action(
        self,
        name: str,
        text: str,
        icon: QIcon | str | None = None,
        icon_text: str = "",
        tip: str | None = None,
        toggled: Callable[[Any], None] | bool | None = None,
        triggered: Callable[[], None] | None = None,
        data: Any | None = None,
        shortcut: str | None = None,
        shortcut_context: str | None = None,
        context: Qt.ShortcutContext = Qt.WidgetWithChildrenShortcut,
        initial: bool | None = None,
        register_shortcut: bool = False,
        section: str | None = None,
        option: spyder.config.types.ConfigurationKey | None = None,
        parent: QWidget | None = None,
        register_action: bool = True,
        overwrite: bool = False,
        context_name: str | None = None,
        menurole: QAction.MenuRole | None = None,
    ) -> spyder.utils.qthelpers.SpyderAction:
        """
        Create a new Spyder-specialized :class:`QAction`.

        .. note::

            There is no need to set a shortcut when creating an action,
            unless it's a fixed (non-customizable) one. Otherwise, set the
            ``register_shortcut`` argument to ``True``. If the shortcut is
            found in the ``shortcuts`` config section of your plugin,
            then it'll be assigned; if not, it'll be left blank for the
            user to define it in Spyder :guilabel:`Preferences`.

        Parameters
        ----------
        name: str
            Unique identifier for the action.
        text: str
           Localized text for the action, displayed in the interface.
        icon: QIcon | str | None, optional
            Icon name or object for the action when used in menus/toolbuttons.
            If ``None``, the default, no icon is shown.
        icon_text: str, optional
            Descriptive text for the action's ``icon``. If a non-empty string
            is passed, this will also disable the tooltip on this toolbutton
            if part of a toolbar. If the empty string (``""``) (the default),
            no icon text is set and the tooltip will not be disabled.
        tip: str | None, optional
            Tooltip text for the action when used in menus or toolbars.
            If ``None`` (the default), no tooltip is shown.
        toggled: Callable[[Any], None] | bool | None, optional
            If ``None`` (default) then the action doesn't act like a checkbox.
            If ``True``, then the action modifies the configuration ``option``
            on the ``section`` specified (or the default
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` if
            ``section`` is not set). Otherwise, must be a callable,
            called when toggling this action. One of ``toggled`` and
            ``triggered`` must not be ``None``.
        triggered: Callable[[], None] | None, optional
            If a callable, will be called when triggering this action.
            Otherwise, if ``None`` (the default), this will not be a
            triggered action and ``toggled`` must be non-``None`` instead.
        data: Any | None, optional
            Arbitrary user data to be set on the action.
            If ``None``, the default, no custom data is set.
        shortcut: str | None, optional
            A fixed (not configurable) keyboard shortcut to use for the action,
            in cases where it is not practical for the user to configure the
            shortcut. If ``None`` (the default), no fixed shortcut is set.
            For a normal configurable shortcut, you instead need to set
            ``register_shortcut`` to ``True`` and list the shortcut
            as one of the plugin's configuration options.
            See :mod:`spyder.api.shortcuts` for more details.
        shortcut_context: str | None, optional
            The context name of the fixed ``shortcut``. ``None`` (the default)
            for no context or no shortcut. Use ``"_"`` for global shortcuts (
            i.e. that can be used anywhere in the application).
        context: Qt.ShortcutContext, optional
            Set the context object for the fixed shortcut.
            By default, ``Qt.WidgetWithChildrenShortcut``.
        initial: bool | None, optional
            Set the initial state of a togglable action. This does not emit
            the toggled signal. If ``None``, the default, no initial state.
        register_shortcut: bool, optional
            If ``True``, the main window will expose the shortcut in the
            Spyder :guilabel:`Preferences`. If ``False``, the default,
            the shortcut will not be registered.
        section: str | None, optional
            Name of the configuration section whose ``option`` is going to be
            modified. If ``None`` (the default) and ``option`` is not ``None``,
            then it defaults to the class'
            :attr:`~spyder.api.plugins.SpyderPluginV2.CONF_SECTION` attribute.
        option: spyder.config.types.ConfigurationKey | None, optional
            Name of the configuration option whose value is reflected and
            affected by the action. If ``None`` (the default), no option
            is associated with this action, e.g. for actions that are
            ``triggered`` rather than ``toggled``.
        parent: QWidget | None, optional
            The parent of this widget. If ``None``, the default, uses
            this instance object itself as the parent.
        register_action: bool, optional
            If ``True`` (default) the action will be registered and searchable.
            If ``False``, the action will be created but not registered.
        overwrite: bool, optional
            If ``False`` (the default) and this action overwrites another
            with the same ``name`` and ``context_name``, raise a warning.
            Set to ``True`` to disable this warning if intentionally
            overwriting another action.
        context_name: str | None, optional
            Name of the context that holds the action when registered.
            The combination of ``name`` and ``context_name`` must be unique,
            and registering an action with the same ``name`` & `context_name``
            will raise a warning by default unless ``overwrite`` is ``True``.
        menurole: QAction.MenuRole | None, optional
            Menu role for the action. Only has an effect on macOS.

        Returns
        -------
        spyder.utils.qthelpers.SpyderAction
            The Spyder action object that was created
            (a specialized :class:`QAction`).

        Raises
        ------
        SpyderAPIError
            If both ``triggered`` and ``toggled`` are ``None``, as at least one
            must be provided; or if both ``initial`` is ``True`` and
            ``triggered`` is not ``None``, as initial values can only apply to
            ``toggled`` actions.
        """
        if triggered is None and toggled is None:
            raise SpyderAPIError(
                "Action must provide the toggled or triggered parameters!"
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
            shortcut=shortcut,
            option=option,
            id_=name,
            plugin=self.PLUGIN_NAME,
            context_name=(
                self.CONTEXT_NAME if context_name is None else context_name
            ),
            register_action=register_action,
            overwrite=overwrite,
            menurole=menurole,
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
                    "Initial values can only apply to togglable actions!"
                )
        else:
            if toggled:
                if section is not None and option is not None:
                    value = CONF.get(section, option)
                    action.setChecked(value)

        return action

    def get_action(
        self,
        name: str,
        context: str | None = None,
        plugin: str | None = None,
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
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the action was defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        spyder.utils.qthelpers.SpyderAction
            The corresponding action widget stored under the given
            ``name``, ``context`` and ``plugin``.

        Raises
        ------
        KeyError
            If the combination of ``name``, ``context`` and ``plugin`` keys
            does not exist in the action registry.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context

        return ACTION_REGISTRY.get_reference(name, plugin, context)

    def get_actions(
        self, context: str | None = None, plugin: str | None = None
    ) -> dict[str, spyder.utils.qthelpers.SpyderAction]:
        """
        Return all actions defined by a context on a given plugin.

        Parameters
        ----------
        context: str | None, optional
            Context identifier under which the actions were stored.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.CONTEXT_NAME` attribute is used instead.
        plugin: str | None, optional
            Identifier of the plugin in which the actions were defined.
            If ``None``, the default, then the
            :attr:`~SpyderWidgetMixin.PLUGIN_NAME` attribute is used instead.

        Returns
        -------
        dict[str, spyder.utils.qthelpers.SpyderAction]
            A dictionary that maps identifier name keys to their corresponding
            action objects.

        Notes
        -----
        * Actions should only be created once. Creating new actions on menu
          popup is *highly* discouraged.
        * Actions can be created directly on a
          :class:`~spyder.api.widgets.main_widget.PluginMainWidget` or
          :class:`~spyder.api.widgets.main_container.PluginMainContainer`
          subclass. Child widgets can also create actions, but they need to
          subclass this class or :class:`SpyderWidgetMixin`.
        * :class:`~spyder.api.widgets.main_widget.PluginMainWidget` or
          :class:`~spyder.api.widgets.main_container.PluginMainContainer`
          will collect any actions defined in subwidgets (if defined)
          and expose them in the ``get_actions`` method at the plugin level.
        * There is no need to override this method.
        """
        plugin = self.PLUGIN_NAME if plugin is None else plugin
        context = self.CONTEXT_NAME if context is None else context
        return ACTION_REGISTRY.get_references(plugin, context)

    def update_actions(self) -> None:
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the :meth:`create_action`
        method.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            If this method is not implemented by the plugin, as is required.
        """
        raise NotImplementedError("")


class SpyderWidgetMixin(
    SpyderActionMixin,
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

    PLUGIN_NAME: str | None = None
    """
    Plugin name in the action, toolbar, toolbutton & menu registries.

    Usually the same as
    :attr:`SpyderPluginV2.NAME <spyder.api.plugins.SpyderPluginV2.NAME>`,
    but may be different from :attr:`CONTEXT_NAME`.
    """

    CONTEXT_NAME: str | None = None
    """
    The name under which to store actions, toolbars, toolbuttons and menus.

    This optional attribute defines the context name under which actions,
    toolbars, toolbuttons and menus should be registered in the
    Spyder global registry.

    If those elements belong to the global scope of the plugin, then this
    attribute should have a ``None`` value, which will use the plugin's name as
    the context scope
    """

    def __init__(
        self,
        class_parent: QObject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Add methods and attributes for most Spyder widgets.

        Parameters
        ----------
        class_parent : QObject | None, optional
            The parent object of this object's class, or ``None`` (default).
            Typically the plugin object.
        parent : QWidget | None, optional
            The parent widget of this one, or ``None`` (default).

        Returns
        -------
        None
        """
        for attr in ["CONF_SECTION", "PLUGIN_NAME"]:
            if getattr(self, attr, None) is None:
                if hasattr(class_parent, attr):
                    # Inherit class_parent CONF_SECTION/PLUGIN_NAME value
                    setattr(self, attr, getattr(class_parent, attr))

        super().__init__()

    @staticmethod
    def create_icon(name: str) -> QIcon:
        """
        Retrieve an icon from Spyder's icon manager.

        Parameters
        ----------
        name: str
            The name of the icon to retrieve.

        Returns
        -------
        QIcon
            The specified icon, as a :class:`QIcon` instance.
        """
        return ima.icon(name)

    def update_style(self) -> None:
        """
        Modify the interface styling used by the plugin.

        This must be reimplemented by plugins that need to adjust their style.

        Changing from the dark to the light interface theme might
        require specific styles or stylesheets to be applied. When
        the theme is changed by the user through our :guilabel:`Preferences`,
        this method will be called for all plugins.

        Returns
        -------
        None
        """
        pass

    def update_translation(self) -> None:
        """
        Update localization of the widget.

        This method will be called recursively on all widgets on language
        change.

        Returns
        -------
        None
        """
        pass


class SpyderMainWindowMixin:
    """
    Mixin with additional functionality for Spyder's :class:`QMainWindow`\\s.
    """

    def _is_on_visible_screen(self: QMainWindow) -> bool:
        """Detect if the window is placed on a visible screen."""
        x, y = self.geometry().x(), self.geometry().y()
        qapp = QApplication.instance()
        current_screen = qapp.screenAt(QPoint(x, y))

        if current_screen is None:
            return False
        else:
            return True

    def move_to_primary_screen(self: QMainWindow) -> None:
        """
        Move the window to the primary screen if necessary.

        Returns
        -------
        None
        """
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
        if not hasattr(self, "is_window_widget"):
            self.showMaximized()


class SvgToScaledPixmap(SpyderConfigurationAccessor):
    """
    Mixin to transform an SVG to a QPixmap.

    The resulting :class:`QPixmap` is scaled according to the scale factor
    set by users in Spyder's :guilabel:`Preferences`.
    """

    def svg_to_scaled_pixmap(
        self,
        svg_file: str,
        rescale: float | None = None,
        in_package: bool = True,
    ) -> QPixmap:
        """
        Transform an SVG to a QPixmap.

        The resulting :class:`QPixmap` is scaled according to the scale factor
        set by users in Spyder's :guilabel:`Preferences`. Uses Spyder's
        icon manager for proper colorization.

        Parameters
        ----------
        svg_file: str
            Name of or path to the SVG file to convert.
        rescale: float | None, optional
            Rescale pixmap according to a factor between 0 and 1.
            If ``None`` (default), will use the default scale factor.
        in_package: bool, optional
            If ``True`` (the default), get the SVG from the
            :file:`images` directory in the installed Spyder package.
            If ``False``, retrieve it from the specified file on disk.

        Returns
        -------
        QPixmap
            The converted rasterized image.
        """
        if in_package:
            image_path = get_image_path(svg_file)

        # Get user's DPI scale factor
        if self.get_conf("high_dpi_custom_scale_factor", section="main"):
            scale_factors = self.get_conf(
                "high_dpi_custom_scale_factors", section="main"
            )
            scale_factor = float(scale_factors.split(":")[0])
        else:
            scale_factor = 1

        # Check if the SVG has colorization classes before colorization
        should_colorize = False
        try:
            svg_paths_data = SVGColorize.get_colored_paths(
                image_path, ima.ICON_COLORS
            )
            if svg_paths_data and svg_paths_data.get("paths"):
                # Check if any of the paths have colorization classes
                # (not just default colors)
                paths = svg_paths_data.get("paths", [])
                for path in paths:
                    # If a path has a color that's not the default color,
                    # it means it has a colorization class
                    default_color = ima.ICON_COLORS.get(
                        "ICON_1", "#FF0000"  # Get default color from palette
                    )
                    if path.get("color") != default_color:
                        should_colorize = True
                        break
        except Exception:
            should_colorize = False

        # Try to use the icon manager for colorization only if SVG supports it
        if should_colorize:
            icon = ima.get_icon(svg_file)
            if icon and not icon.isNull():
                # Get the original SVG dimensions
                pm = QPixmap(image_path)
                width = pm.width()
                height = pm.height()

                # Apply rescale factor
                if rescale is not None:
                    aspect_ratio = width / height
                    width = int(width * rescale)
                    height = int(width / aspect_ratio)

                # Get a properly scaled pixmap from the icon
                # Use the maximum dimension to maintain aspect ratio
                max_dimension = max(
                    int(width * scale_factor), int(height * scale_factor)
                )
                return icon.pixmap(max_dimension, max_dimension)

        # Fallback to original method for icons without colorization classes.
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
            int(width * scale_factor),
            int(height * scale_factor),
            QImage.Format_ARGB32_Premultiplied,
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
