# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Toolbar Container.
"""

# Standard library imports
from collections import OrderedDict
from spyder.utils.qthelpers import SpyderAction
from typing import Optional, Union, Tuple, Dict, List

# Third party imports
from qtpy.QtCore import QSize, Slot
from qtpy.QtWidgets import QAction, QWidget
from qtpy import PYSIDE2

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.utils import get_class_values
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.registries import TOOLBAR_REGISTRY


# Type annotations
ToolbarItem = Union[SpyderAction, QWidget]
ItemInfo = Tuple[ToolbarItem, Optional[str], Optional[str], Optional[str]]


class ToolbarMenus:
    ToolbarsMenu = "toolbars_menu"


class ToolbarsMenuSections:
    Main = "main_section"
    Secondary = "secondary_section"


class ToolbarActions:
    ShowToolbars = "show toolbars"


class QActionID(QAction):
    """Wrapper class around QAction that allows to set/get an identifier."""
    @property
    def action_id(self):
        return self._action_id

    @action_id.setter
    def action_id(self, act):
        self._action_id = act


class ToolbarContainer(PluginMainContainer):
    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent=parent)

        self._APPLICATION_TOOLBARS = OrderedDict()
        self._ADDED_TOOLBARS = OrderedDict()
        self._toolbarslist = []
        self._visible_toolbars = []
        self._ITEMS_QUEUE = {}  # type: Dict[str, List[ItemInfo]]

    # ---- Private Methods
    # ------------------------------------------------------------------------
    def _save_visible_toolbars(self):
        """Save the name of the visible toolbars in the options."""
        toolbars = []
        for toolbar in self._visible_toolbars:
            toolbars.append(toolbar.objectName())

        self.set_conf('last_visible_toolbars', toolbars)

    def _get_visible_toolbars(self):
        """Collect the visible toolbars."""
        toolbars = []
        for toolbar in self._toolbarslist:
            if (toolbar.toggleViewAction().isChecked()
                    and toolbar not in toolbars):
                toolbars.append(toolbar)

        self._visible_toolbars = toolbars

    @Slot()
    def _show_toolbars(self):
        """Show/Hide toolbars."""
        value = not self.get_conf("toolbars_visible")
        self.set_conf("toolbars_visible", value)
        if value:
            self._save_visible_toolbars()
        else:
            self._get_visible_toolbars()

        for toolbar in self._visible_toolbars:
            toolbar.setVisible(value)

        self.update_actions()

    def _add_missing_toolbar_elements(self, toolbar, toolbar_id):
        if toolbar_id in self._ITEMS_QUEUE:
            pending_items = self._ITEMS_QUEUE.pop(toolbar_id)
            for item, section, before, before_section in pending_items:
                toolbar.add_item(item, section=section, before=before,
                                 before_section=before_section)

    # ---- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self):
        self.show_toolbars_action = self.create_action(
            ToolbarActions.ShowToolbars,
            text=_("Show toolbars"),
            triggered=self._show_toolbars
        )

        self.toolbars_menu = self.create_menu(
            ToolbarMenus.ToolbarsMenu,
            _("Toolbars"),
        )
        self.toolbars_menu.setObjectName('checkbox-padding')

    def update_actions(self):
        visible_toolbars = self.get_conf("toolbars_visible")
        if visible_toolbars:
            text = _("Hide toolbars")
            tip = _("Hide toolbars")
        else:
            text = _("Show toolbars")
            tip = _("Show toolbars")

        self.show_toolbars_action.setText(text)
        self.show_toolbars_action.setToolTip(tip)
        self.toolbars_menu.setEnabled(visible_toolbars)

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_application_toolbar(
            self, toolbar_id: str, title: str) -> ApplicationToolbar:
        """
        Create an application toolbar and add it to the main window.

        Parameters
        ----------
        toolbar_id: str
            The toolbar unique identifier string.
        title: str
            The localized toolbar title to be displayed.

        Returns
        -------
        spyder.api.widgets.toolbar.ApplicationToolbar
            The created application toolbar.
        """
        if toolbar_id in self._APPLICATION_TOOLBARS:
            raise SpyderAPIError(
                'Toolbar with ID "{}" already added!'.format(toolbar_id))

        toolbar = ApplicationToolbar(self, title)
        toolbar.ID = toolbar_id
        toolbar.setObjectName(toolbar_id)

        TOOLBAR_REGISTRY.register_reference(
            toolbar, toolbar_id, self.PLUGIN_NAME, self.CONTEXT_NAME)
        self._APPLICATION_TOOLBARS[toolbar_id] = toolbar

        self._add_missing_toolbar_elements(toolbar, toolbar_id)
        return toolbar

    def add_application_toolbar(self, toolbar, mainwindow=None):
        """
        Add toolbar to application toolbars.

        Parameters
        ----------
        toolbar: spyder.api.widgets.toolbars.ApplicationToolbar
            The application toolbar to add to the `mainwindow`.
        mainwindow: QMainWindow
            The main application window.
        """
        # Check toolbar class
        if not isinstance(toolbar, ApplicationToolbar):
            raise SpyderAPIError(
                'Any toolbar must subclass ApplicationToolbar!'
            )

        # Check ID
        toolbar_id = toolbar.ID
        if toolbar_id is None:
            raise SpyderAPIError(
                f"Toolbar `{repr(toolbar)}` doesn't have an identifier!"
            )

        if toolbar_id in self._ADDED_TOOLBARS:
            raise SpyderAPIError(
                'Toolbar with ID "{}" already added!'.format(toolbar_id))

        # TODO: Make the icon size adjustable in Preferences later on.
        iconsize = 24
        toolbar.setIconSize(QSize(iconsize, iconsize))
        toolbar.setObjectName(toolbar_id)

        self._ADDED_TOOLBARS[toolbar_id] = toolbar
        self._toolbarslist.append(toolbar)

        if mainwindow:
            mainwindow.addToolBar(toolbar)

        self._add_missing_toolbar_elements(toolbar, toolbar_id)

    def remove_application_toolbar(self, toolbar_id: str, mainwindow=None):
        """
        Remove toolbar from application toolbars.

        Parameters
        ----------
        toolbar: str
            The application toolbar to remove from the `mainwindow`.
        mainwindow: QMainWindow
            The main application window.
        """

        if toolbar_id not in self._ADDED_TOOLBARS:
            raise SpyderAPIError(
                'Toolbar with ID "{}" is not in the main window'.format(
                    toolbar_id))

        toolbar = self._ADDED_TOOLBARS.pop(toolbar_id)
        self._toolbarslist.remove(toolbar)

        if mainwindow:
            mainwindow.removeToolBar(toolbar)

    def add_item_to_application_toolbar(self,
                                        item: ToolbarItem,
                                        toolbar_id: Optional[str] = None,
                                        section: Optional[str] = None,
                                        before: Optional[str] = None,
                                        before_section: Optional[str] = None,
                                        omit_id: bool = False):
        """
        Add action or widget `item` to given application toolbar `section`.

        Parameters
        ----------
        item: SpyderAction or QWidget
            The item to add to the `toolbar`.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `toolbar`.
        before: str or None
            Make the item appear before another given item.
        before_section: str or None
            Make the item defined section appear before another given section
            (the section must be already defined).
        omit_id: bool
            If True, then the toolbar will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Spyder 4 plugins. Default: False
        """
        if toolbar_id not in self._APPLICATION_TOOLBARS:
            pending_items = self._ITEMS_QUEUE.get(toolbar_id, [])
            pending_items.append((item, section, before, before_section))
            self._ITEMS_QUEUE[toolbar_id] = pending_items
        else:
            toolbar = self.get_application_toolbar(toolbar_id)
            toolbar.add_item(item, section=section, before=before,
                             before_section=before_section, omit_id=omit_id)

    def remove_item_from_application_toolbar(self, item_id: str,
                                             toolbar_id: Optional[str] = None):
        """
        Remove action or widget from given application toolbar by id.

        Parameters
        ----------
        item: str
            The item to remove from the `toolbar`.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        """
        if toolbar_id not in self._APPLICATION_TOOLBARS:
            raise SpyderAPIError(
                '{} is not a valid toolbar_id'.format(toolbar_id))

        toolbar = self.get_application_toolbar(toolbar_id)
        toolbar.remove_item(item_id)

    def get_application_toolbar(self, toolbar_id: str) -> ApplicationToolbar:
        """
        Return an application toolbar by toolbar_id.

        Parameters
        ----------
        toolbar_id: str
            The toolbar unique string identifier.

        Returns
        -------
        spyder.api.widgets.toolbars.ApplicationToolbar
            The application toolbar.
        """
        if toolbar_id not in self._APPLICATION_TOOLBARS:
            raise SpyderAPIError(
                'Application toolbar "{0}" not found! '
                'Available toolbars are: {1}'.format(
                    toolbar_id,
                    list(self._APPLICATION_TOOLBARS.keys())
                )
            )

        return self._APPLICATION_TOOLBARS[toolbar_id]

    def get_application_toolbars(self):
        """
        Return all created application toolbars.

        Returns
        -------
        list
            The list of all the added application toolbars.
        """
        return self._toolbarslist

    def save_last_visible_toolbars(self):
        """Save the last visible toolbars state in our preferences."""
        if self.get_conf("toolbars_visible"):
            self._get_visible_toolbars()
        self._save_visible_toolbars()

    def load_last_visible_toolbars(self):
        """Load the last visible toolbars from our preferences."""
        toolbars_names = self.get_conf('last_visible_toolbars')
        toolbars_visible = self.get_conf("toolbars_visible")

        if toolbars_names:
            toolbars_dict = {}
            for toolbar in self._toolbarslist:
                toolbars_dict[toolbar.objectName()] = toolbar

            toolbars = []
            for name in toolbars_names:
                if name in toolbars_dict:
                    toolbars.append(toolbars_dict[name])

            self._visible_toolbars = toolbars
        else:
            self._get_visible_toolbars()

        for toolbar in self._visible_toolbars:
            toolbar.setVisible(toolbars_visible)

        self.update_actions()

    def create_toolbars_menu(self):
        """
        Populate the toolbars menu inside the view application menu.
        """
        main_section = ToolbarsMenuSections.Main
        secondary_section = ToolbarsMenuSections.Secondary
        default_toolbars = get_class_values(ApplicationToolbars)

        for toolbar_id, toolbar in self._ADDED_TOOLBARS.items():
            if toolbar:
                action = toolbar.toggleViewAction()
                if not PYSIDE2:
                    # Modifying __class__ of a QObject created by C++ [1] seems
                    # to invalidate the corresponding Python object when PySide
                    # is used (changing __class__ of a QObject created in
                    # Python seems to work).
                    #
                    # [1] There are Qt functions such as
                    # QToolBar.toggleViewAction(), QToolBar.addAction(QString)
                    # and QMainWindow.addToolbar(QString), which return a
                    # pointer to an already existing QObject.
                    action.__class__ = QActionID
                action.action_id = f'toolbar_{toolbar_id}'
                section = (
                    main_section
                    if toolbar_id in default_toolbars
                    else secondary_section
                )

                self.add_item_to_menu(
                    action,
                    menu=self.toolbars_menu,
                    section=section,
                )
