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
import logging
from typing import Dict, List, Optional, Tuple, Union

# Third party imports
from qtpy.QtCore import QSize, Slot
from qtpy.QtWidgets import QAction, QWidget
from qtpy import PYSIDE2

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.utils import get_class_values
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.config.base import DEV
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.qthelpers import SpyderAction
from spyder.utils.registries import ACTION_REGISTRY, TOOLBAR_REGISTRY


# Logging
logger = logging.getLogger(__name__)

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
        self._toolbarslist: list[ApplicationToolbar] = []
        self._visible_toolbars: list[ApplicationToolbar] = []
        self._ITEMS_QUEUE: Dict[str, List[ItemInfo]] = {}

    # ---- Private Methods
    # ------------------------------------------------------------------------
    def _save_visible_toolbars(self):
        """Save the name of the visible toolbars in the options."""
        toolbars = []
        for toolbar in self._visible_toolbars:
            toolbars.append(toolbar.objectName())

        self.set_conf('last_visible_toolbars', toolbars)

    def _set_visible_toolbars(self):
        """Set the current visible toolbars in an attribute."""
        toolbars = []
        for toolbar in self._toolbarslist:
            if (
                toolbar.toggleViewAction().isChecked()
                and toolbar not in toolbars
            ):
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
            self._set_visible_toolbars()

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
        self,
        toolbar_id: str,
        title: str
    ) -> ApplicationToolbar:
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
                'Toolbar with ID "{}" already added!'.format(toolbar_id)
            )

        toolbar = ApplicationToolbar(self, toolbar_id, title)
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

        # Add toolbar to registry and add it to the app toolbars dict
        TOOLBAR_REGISTRY.register_reference(
            toolbar, toolbar_id, self.PLUGIN_NAME, self.CONTEXT_NAME
        )
        self._APPLICATION_TOOLBARS[toolbar_id] = toolbar

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

    def add_item_to_application_toolbar(
        self,
        item: ToolbarItem,
        toolbar_id: Optional[str] = None,
        section: Optional[str] = None,
        before: Optional[str] = None,
        before_section: Optional[str] = None,
        omit_id: bool = False
    ):
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

    def remove_item_from_application_toolbar(
        self,
        item_id: str,
        toolbar_id: Optional[str] = None
    ):
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

    def get_application_toolbars(self) -> Dict[str, ApplicationToolbar]:
        """
        Return all created application toolbars.

        Returns
        -------
        dict
            The dict of all the added application toolbars.
        """
        return self._APPLICATION_TOOLBARS

    def load_application_toolbars(self):
        """Load application toolbars at startup."""
        app_toolbars = self.get_application_toolbars()

        # Get internal and external toolbars
        internal_toolbars = get_class_values(ApplicationToolbars)
        external_toolbars = [
            toolbar_id
            for toolbar_id in app_toolbars.keys()
            if toolbar_id not in internal_toolbars
        ]

        # Default order for internal toolbars
        internal_toolbars_order = [
            ApplicationToolbars.File,
            ApplicationToolbars.Run,
            ApplicationToolbars.Debug,
            ApplicationToolbars.Main,
        ]

        # Check we didn't leave out any internal toolbar from the order above
        if DEV:
            if (
                (set(internal_toolbars) - set(internal_toolbars_order))
                != {ApplicationToolbars.WorkingDirectory}
            ):
                missing_toolbars = (
                    set(internal_toolbars)
                    - set(internal_toolbars_order)
                    - {ApplicationToolbars.WorkingDirectory}
                )

                raise SpyderAPIError(
                    f"The internal toolbar(s) {missing_toolbars} are not "
                    f"listed in the ordering of toolbars that is set below. "
                    f"Please add them to fix this error"
                )

        # Reorganize toolbars only if this is the first time Spyder starts or
        # new toolbars were added
        last_toolbars = self.get_conf("last_toolbars")
        if (
            not last_toolbars
            or set(last_toolbars) != set(app_toolbars.keys())
        ):
            logger.debug("Reorganize application toolbars")

            # We need to remove all toolbars first to organize them in the way
            # we want
            for toolbar in self._toolbarslist:
                self._plugin.main.removeToolBar(toolbar)

            # Add toolbars with the working directory to the right because it's
            # not clear where it ends, so users can have a hard time finding a
            # new toolbar in the interface if it's placed next to it.
            toolbars_order = internal_toolbars_order + external_toolbars
            for toolbar_id in (
                toolbars_order
                + [ApplicationToolbars.WorkingDirectory]
            ):
                toolbar = app_toolbars[toolbar_id]
                self._plugin.main.addToolBar(toolbar)
                toolbar.render()
        else:
            logger.debug("Render application toolbars")

            for toolbar in self._toolbarslist:
                toolbar.render()

    def save_last_toolbars(self):
        """Save the last available toolbars when the app is closed."""
        logger.debug("Saving current application toolbars")

        toolbars = []
        for toolbar in self._toolbarslist:
            toolbars.append(toolbar.objectName())

        self.set_conf('last_toolbars', toolbars)

    def save_last_visible_toolbars(self):
        """Save the last visible toolbars in our preferences."""
        if self.get_conf("toolbars_visible"):
            self._set_visible_toolbars()
        self._save_visible_toolbars()

    def load_last_visible_toolbars(self):
        """Load the last visible toolbars saved in our config system."""
        toolbars_names = self.get_conf('last_visible_toolbars')
        toolbars_visible = self.get_conf("toolbars_visible")

        # This is necessary to discard toolbars that were available in the last
        # session but are not on this one.
        visible_toolbars = []
        for name in toolbars_names:
            if name in self._APPLICATION_TOOLBARS:
                visible_toolbars.append(self._APPLICATION_TOOLBARS[name])

        # Update visible toolbars
        self._visible_toolbars = visible_toolbars

        # Show visible/hidden toolbars
        for toolbar in self._toolbarslist:
            if toolbar in self._visible_toolbars:
                toolbar.setVisible(toolbars_visible)
                toolbar.toggleViewAction().setChecked(toolbars_visible)
            else:
                toolbar.setVisible(False)
                toolbar.toggleViewAction().setChecked(False)

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

                # This is necessary to show the same visible toolbars both in
                # MainWindow and EditorMainWindow.
                action.triggered.connect(self.save_last_visible_toolbars)

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

                # Register action
                id_ = f'toggle_view_{toolbar_id}'
                action.action_id = id_

                ACTION_REGISTRY.register_reference(
                    action,
                    id_,
                    self._plugin.NAME
                )

                # Add action to menu
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
