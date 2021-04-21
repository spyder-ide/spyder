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

# Third party imports
from qtpy.QtCore import QSize, Slot

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.utils import get_class_values
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.registries import TOOLBAR_REGISTRY


# Localization
_ = get_translation('spyder')


class ToolbarMenus:
    ToolbarsMenu = "toolbars_menu"


class ToolbarsMenuSections:
    Main = "main_section"
    Secondary = "secondary_section"


class ToolbarActions:
    ShowToolbars = "show toolbars"


class ToolbarContainer(PluginMainContainer):
    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent=parent)

        self._APPLICATION_TOOLBARS = OrderedDict()
        self._ADDED_TOOLBARS = OrderedDict()
        self._toolbarslist = []
        self._visible_toolbars = []

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
        if self.get_conf("toolbars_visible"):
            text = _("Hide toolbars")
            tip = _("Hide toolbars")
        else:
            text = _("Show toolbars")
            tip = _("Show toolbars")

        self.show_toolbars_action.setText(text)
        self.show_toolbars_action.setToolTip(tip)

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_application_toolbar(self, toolbar_id, title):
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

    def add_item_to_application_toolbar(self, item, toolbar=None, toolbar_id=None,
                                        section=None, before=None,
                                        before_section=None):
        """
        Add action or widget `item` to given application toolbar `section`.

        Parameters
        ----------
        item: SpyderAction or QWidget
            The item to add to the `toolbar`.
        toolbar: ApplicationToolbar or None
            Instance of a Spyder application toolbar.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `toolbar`.
        before: str or None
            Make the item appear before another given item.
        before_section: str or None
            Make the item defined section appear before another given section
            (the section must be already defined).

        Notes
        -----
        Must provide a `toolbar` or a `toolbar_id`.
        """
        if toolbar and toolbar_id:
            raise SpyderAPIError('Must provide only toolbar or toolbar_id!')

        if toolbar is None and toolbar_id is None:
            raise SpyderAPIError(
                'Must provide at least toolbar or toolbar_id!')

        if toolbar and not isinstance(toolbar, ApplicationToolbar):
            raise SpyderAPIError('Not an `ApplicationToolbar`!')

        if toolbar_id and toolbar_id not in self._APPLICATION_TOOLBARS:
            raise SpyderAPIError(
                '{} is not a valid toolbar_id'.format(toolbar_id))

        toolbar_id = toolbar_id if toolbar_id else toolbar.ID
        toolbar = toolbar if toolbar else self.get_application_toolbar(
            toolbar_id)

        toolbar.add_item(item, section=section, before=before,
                         before_section=before_section)

    def get_application_toolbar(self, toolbar_id):
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

    def load_last_visible_toolbars(self):
        """Load the last visible toolbars from our preferences.."""
        toolbars_names = self.get_conf('last_visible_toolbars')

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
