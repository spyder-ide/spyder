# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Plugin.

It handles closing, opening and switching among projetcs and als updating the
file tree explorer associated with a project.
"""

# Standard library imports
import functools
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.menus import ApplicationMenus
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.completion.manager.api import WorkspaceUpdateKind
from spyder.plugins.projects.api import ProjectsMenuSections
from spyder.plugins.projects.project_types import EmptyProject
from spyder.plugins.projects.widgets.main_widget import (
    ProjectExplorerWidget, ProjectExplorerWidgetActions,
    ProjectExplorerWidgetMenus)

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Projects(SpyderDockablePlugin):
    """Projects plugin."""

    NAME = 'project_explorer'
    REQUIRES = [Plugins.CodeCompletion, Plugins.Explorer]
    OPTIONAL = [Plugins.Editor, Plugins.IPythonConsole]
    WIDGET_CLASS = ProjectExplorerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        "single_click_to_open": ("explorer", "single_click_to_open"),
    }

    # --- Signals
    # ------------------------------------------------------------------------
    sig_project_created = Signal(str, str, object)
    """
    This signal is emitted to inform a project has been  created.

    Parameters
    ----------
    project_path: str
        Location of project.
    project_type: str
        Type of project as defined by project types.
    project_packages: object
        Package to install. Currently not in use.
    """

    sig_project_opened = Signal(object)
    """
    This signal is emitted to inform a project has been opened.

    Parameters
    ----------
    project: object
        Project object.
    """

    sig_project_closed = Signal(object)
    """
    This signal is emitted to inform a project has been closed.

    Parameters
    ----------
    project: object
        Project object.
    """

    sig_project_deleted = Signal(object)
    """
    This signal is emitted to inform a project has been deleted.

    Parameters
    ----------
    project: object
        Project object.
    """

    # --- Explorer
    sig_file_deleted = Signal(str)
    """
    This signal is emitted when a file is deleted.
    Parameters
    ----------
    path: str
        Deleted file path.
    """

    sig_file_renamed = Signal(str, str)
    """
    This signal is emitted when a file is renamed.
    Parameters
    ----------
    old_path: str
        Old path for renamed file.
    new_path: str
        New path for renamed file.
    """

    sig_folder_deleted = Signal(str)
    """
    This signal is emitted when a folder is deleted.
    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_folder_renamed = Signal(str)
    """
    This signal is emitted when a folder is renamed.
    Parameters
    ----------
    path: str
        Folder to remove.
    """
    
    sig_folder_opened = Signal(str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The path to the directory opened.
    Notes
    -----
    This will update the current working directory.
    """

    sig_file_externally_opened = Signal(str)
    """
    This signal is emitted when a file is open outside Spyder for edition.

    Parameters
    ----------
    path: str
        File path opened externally for edition.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_new_file_requested = Signal()
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_open_interpreter_requested = Signal(str)
    """
    This signal is emitted to request opening an interpreter with the given
    path as working directory.

    Parameters
    ----------
    path: str
        Path to use as working directory of interpreter.
    """

    # --- FIXME:
    # ------------------------------------------------------------------------
    sig_pythonpath_changed = Signal()
    """"""

    # --- Consoles
    sig_restart_consoles_requested = Signal()
    """
    This signal is emitted to request a console restart.
    """

    sig_create_module_requested = Signal(str)
    sig_externally_opened = Signal(str)

    # ----- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Projects")

    def get_description(self):
        return _("Create new projects to organize your workflows.")

    def get_icon(self):
        return self.create_icon("project")

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        # completions = self.get_plugin(Plugins.CodeCompletion)
        completions = None
        explorer = self.get_plugin(Plugins.Explorer)
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Expose widget signals at the plugin level
        widget.sig_project_created.connect(self.sig_project_created)
        widget.sig_project_opened.connect(self.sig_project_opened)
        widget.sig_project_closed.connect(self.sig_project_closed)
        widget.sig_project_deleted.connect(self.sig_project_deleted)
        
        widget.sig_externally_opened.connect(self.sig_file_externally_opened)
        widget.sig_file_deleted.connect(self.sig_file_deleted)
        widget.sig_file_renamed.connect(self.sig_file_renamed)
        widget.sig_folder_deleted.connect(self.sig_folder_deleted)
        widget.sig_folder_renamed.connect(self.sig_folder_renamed)
        widget.sig_create_module_requested.connect(
            self.sig_create_module_requested)
        widget.sig_new_file_requested.connect(self.sig_new_file_requested)
        widget.sig_run_requested.connect(self.sig_run_requested)
        widget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)
        widget.sig_restart_consoles_requested.connect(
            self.sig_restart_consoles_requested)

        # Completions manager connections
        if completions:
            self.sig_project_opened.connect(
                functools.partial(completions.project_path_update,
                                update_kind=WorkspaceUpdateKind.ADDITION))
            self.sig_project_opened.connect(
                lambda project: self.sig_update_title_requested(project.name))

            self.sig_project_closed.connect(
                functools.partial(completions.project_path_update,
                                update_kind=WorkspaceUpdateKind.DELETION))
            self.sig_project_closed.connect(
                lambda project: self.sig_update_title_requested(""))

            self.sig_broadcast_notification.connect(
                completions.broadcast_notification)

        # File explorer connection to keep single click to open files in sync
        explorer.sig_option_changed.connect(
            lambda option, value: self.apply_conf({option: value}))

        # Editor connections
        if editor:
            self.sig_externally_opened.connect(editor.load)
            self.sig_file_deleted.connect(editor.removed)
            self.sig_file_renamed.connect(editor.renamed)
            self.sig_folder_deleted.connect(editor.removed_tree)
            self.sig_folder_renamed.connect(editor.renamed_tree)
            self.sig_create_module_requested.connect(editor.new)
            self.sig_new_file_requested.connect(
                lambda t: editor.new(text=t))

        # IPython Console connections
        if ipyconsole:
            self.sig_restart_consoles_requested.connect(ipyconsole.restart)
            self.sig_open_interpreter_requested.connect(
                ipyconsole.create_client_from_path)
            self.sig_run_requested.connect(
                lambda fname: ipyconsole.run_script(
                    fname,
                    osp.dirname(fname),
                    '',
                    False,
                    False,
                    False,
                    True,
                    False,
                )
            )

        # FIXME: Why?
        widget.sig_file_opened.connect(self.main.open_file)

        # New project connections. Order matters!
        # Handled by working dir
        # self.sig_project_loaded.connect(
        #     lambda v: self.main.workingdirectory.chdir(v))
        # TODO: Add a mechanism to update the title?
        # self.sig_project_loaded.connect(
        #     lambda v: self.main.set_window_title())
        # TODO: Change to use constants
        # FIXME: How to do this better?
        # self.sig_project_loaded.connect(
        #     lambda v: self.main.editor.setup_open_files())

        # FIXME: The working directory should know what to do when closing a
        # project
        # self.sig_project_closed.connect(
        #     lambda v: self.main.editor.setup_open_files())

        # Python path ones!
        # self.main.pythonpath_changed()
        # self.main.restore_scrollbar_position.connect(
        #                                        self.restore_scrollbar_position)
        # self.sig_pythonpath_changed.connect(self.main.pythonpath_changed)

        # FIXME: Why???
        # self.main.editor.set_projects(self)

        # Add items to application menu
        projects_menu = self.get_application_menu(ApplicationMenus.Projects)
        recent_projects_menu = widget.get_menu(
            ProjectExplorerWidgetMenus.RecentProjects)
        for item, section in [
                (ProjectExplorerWidgetActions.Create,
                 ProjectsMenuSections.New),
                (ProjectExplorerWidgetActions.Open,
                 ProjectsMenuSections.New),
                (ProjectExplorerWidgetActions.Delete,
                 ProjectsMenuSections.Open),
                (ProjectExplorerWidgetActions.Close,
                 ProjectsMenuSections.Open),
                (recent_projects_menu,
                 ProjectsMenuSections.Recent)]:
            self.add_item_to_application_menu(item, projects_menu, section)

        # Refresh the menu prior to open
        recent_projects_menu.aboutToShow.connect(widget.update_actions)

        # Register default project types
        self.register_project_type(self, EmptyProject)

    def on_close(self, cancelable=False):
        widget = self.get_widget()
        # FIXME: really needed?
        widget.save_config()
        widget.closing_widget()
        return True

    def on_mainwindow_visible(self, cancelable=False):
        self._reopen_last_project()

    # --- Public API
    # ------------------------------------------------------------------------
    def _unmaximize(self):
        """Unmaximize the currently maximized plugin."""
        # FIXME:
        if (self.main.last_plugin is not None and
                self.main.last_plugin._ismaximized and
                self.main.last_plugin is not self):
            self.main.maximize_dockwidget()

    def _reopen_last_project(self):
        """
        Reopen the active project when Spyder was closed last time, if any.
        """
        current_project_path = self.get_conf_option('current_project_path')
        widget = self.get_widget()

        if (current_project_path
                and widget.is_valid_project(current_project_path)):
            widget.open_project(
                path=current_project_path,
                restart_consoles=False,
                save_previous_files=False,
            )
            # FIXME:
            widget.load_config()

    # --- Public API
    # ------------------------------------------------------------------------
    def create_project(self):
        """
        Create a new project.

        Returns
        -------
        project_type_instance: spyder.plugins.projects.api.BaseProjectType
            The project type instance.
        """
        self._unmaximize()
        return self.get_widget().create_project()

    def open_project(self, path):
        """
        Open project located on `path`.

        Parameters
        ----------
        path: str
            Path to project root folder.

        Returns
        -------
        project_type_instance: spyder.plugins.projects.api.BaseProjectType
            The project type instance.
        """
        self._unmaximize()
        return self.get_widget().open_project(path=path)

    def close_project(self):
        """
        Close current active project.
        """
        # self._unmaximize()
        self.get_widget().close_project()

    def delete_project(self):
        """
        Delete current active project.
        """
        # self._unmaximize()
        self.get_widget().delete_project()

    def register_project_type(self, parent_plugin, project_type):
        """
        Register a new project type.

        Parameters
        ----------
        parent_plugin: spyder.plugins.api.plugins.SpyderPluginV2
            The parent plugin instance making the project type registration.
        project_type: spyder.plugins.projects.api.BaseProjectType
            Project type to register.
        """
        self.get_widget().register_project_type(parent_plugin, project_type)

    def get_active_project_path(self):
        """Get path of the active project."""
        return self.get_widget().get_active_project_path()

    def get_project_types(self):
        """
        Return available registered project types.

        Returns
        -------
        dict
            Project types dictionary.
        """
        return self.get_widget().get_project_types()

    def change_max_recent_projects(self, value=None):
        """
        Change the maximum number of recent projects entries.

        Parameters
        ----------
        value: int or None, optional
            Value to use. If no value is provided an input dialog is used.
        """
        self.get_widget().change_max_recent_projects(value)

    # FIXME:
    def get_pythonpath(self, at_start=False):
        return self.get_widget().get_pythonpath(at_start=at_start)

    def reopen_last_project(self):
        pass

    def get_active_project(self):
        return self.get_widget().get_active_project()
