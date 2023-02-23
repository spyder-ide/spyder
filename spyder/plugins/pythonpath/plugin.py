# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pythonpath manager plugin.
"""

from qtpy.QtCore import Signal

from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.application.api import ApplicationActions
from spyder.plugins.mainmenu.api import ApplicationMenus, ToolsMenuSections
from spyder.plugins.toolbar.api import ApplicationToolbars, MainToolbarSections
from spyder.plugins.pythonpath.container import (
    PythonpathActions, PythonpathContainer)


class PythonpathManager(SpyderPluginV2):
    """
    Pythonpath manager plugin.
    """

    NAME = "pythonpath_manager"
    REQUIRES = [Plugins.Toolbar, Plugins.MainMenu]
    OPTIONAL = [Plugins.Projects]
    CONTAINER_CLASS = PythonpathContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False

    sig_pythonpath_changed = Signal(object, object)
    """
    This signal is emitted when there is a change in the Pythonpath handled by
    Spyder.

    Parameters
    ----------
    old_path_dict: OrderedDict
        Previous Pythonpath ordered dictionary. Its keys correspond to the
        project, user and system paths declared by users or detected by Spyder,
        and its values are their state (i.e. True for enabled and False for
        disabled).

    new_path_dict: OrderedDict
        New Pythonpath dictionary.

    Notes
    -----
    It should be possible to simplify this by sending only the new path dict.
    However, that requires changes in Spyder-kernels.

    See Also
    --------
    :py:meth:`.PythonpathContainer._get_spyder_pythonpath_dict`
    """

    # ---- SpyderPluginV2 API
    @staticmethod
    def get_name():
        return _("PYTHONPATH manager")

    def get_description(self):
        return _("Manager of additional locations to search for Python "
                 "modules.")

    def get_icon(self):
        return self.create_icon('python')

    def on_initialize(self):
        container = self.get_container()
        container.sig_pythonpath_changed.connect(self.sig_pythonpath_changed)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        container = self.get_container()
        main_menu = self.get_plugin(Plugins.MainMenu)

        main_menu.add_item_to_application_menu(
            container.path_manager_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools,
            before=ApplicationActions.SpyderUserEnvVariables,
            before_section=ToolsMenuSections.External
        )

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.add_item_to_application_toolbar(
            container.path_manager_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection
        )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        main_menu.remove_item_from_application_menu(
            PythonpathActions.Manager,
            menu_id=ApplicationMenus.Tools,
        )

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.remove_item_from_application_toolbar(
            PythonpathActions.Manager,
            toolbar_id=ApplicationToolbars.Main
        )

    # ---- Public API
    def get_spyder_pythonpath(self):
        """Get Pythonpath paths handled by Spyder as a list."""
        return self.get_container().get_spyder_pythonpath()

    def show_path_manager(self):
        """Show Path manager dialog."""
        self.get_container().show_path_manager()

    @property
    def path_manager_dialog(self):
        return self.get_container().path_manager_dialog

    # ---- Private API
    def _on_project_loaded(self, path):
        self.get_container().update_active_project_path(path)

    def _on_project_closed(self, path):
        self.get_container().update_active_project_path(None)
