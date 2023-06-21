# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Plugin

It handles closing, opening and switching among projects and also
updating the file tree explorer associated with a project.
"""

# Standard library imports
import logging
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import _
from spyder.config.base import is_conda_based_app
from spyder.plugins.completion.api import WorkspaceUpdateKind
from spyder.plugins.mainmenu.api import ApplicationMenus, ProjectsMenuSections
from spyder.plugins.projects.api import EmptyProject
from spyder.plugins.projects.widgets.main_widget import (
    ProjectsActions, ProjectExplorerWidget)
from spyder.utils.misc import getcwd_or_home


# Logging
logger = logging.getLogger(__name__)


class Projects(SpyderDockablePlugin):
    """Projects plugin."""

    NAME = 'project_explorer'
    CONF_SECTION = NAME
    CONF_FILE = False
    REQUIRES = []
    OPTIONAL = [Plugins.Completions, Plugins.IPythonConsole, Plugins.Editor,
                Plugins.MainMenu]
    WIDGET_CLASS = ProjectExplorerWidget

    # Signals
    sig_project_created = Signal(str, str)
    """
    This signal is emitted to request the Projects plugin the creation of a
    project.

    Parameters
    ----------
    project_path: str
        Location of project.
    project_type: str
        Type of project as defined by project types.
    """

    sig_project_loaded = Signal(str)
    """
    This signal is emitted when a project is loaded.

    Parameters
    ----------
    project_path: str
        Loaded project path.
    """

    sig_project_closed = Signal((str,), (bool,))
    """
    This signal is emitted when a project is closed.

    Parameters
    ----------
    project_path: str
        Closed project path (signature 1).
    close_project: bool
        This is emitted only when closing a project but not when switching
        between projects (signature 2).
    """

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Projects")

    def get_description(self):
        return _("Create Spyder projects and manage their files.")

    def get_icon(self):
        return self.create_icon('project')

    def on_initialize(self):
        """Register plugin in Spyder's main window"""
        widget = self.get_widget()
        treewidget = widget.treewidget
        self._completions = None

        # Emit public signals so that other plugins can connect to them
        widget.sig_project_created.connect(self.sig_project_created)
        widget.sig_project_closed.connect(self.sig_project_closed)
        widget.sig_project_loaded.connect(self.sig_project_loaded)

        treewidget.sig_delete_project.connect(self.delete_project)
        treewidget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        self.sig_switch_to_plugin_requested.connect(
            lambda plugin, check: self._show_main_widget())

        if self.main:
            widget.sig_open_file_requested.connect(self.main.open_file)
            widget.sig_project_loaded.connect(
                lambda v: self.main.set_window_title())
            widget.sig_project_closed.connect(
                lambda v: self.main.set_window_title())
            self.main.restore_scrollbar_position.connect(
                self.get_widget().restore_scrollbar_position)

        self.register_project_type(self, EmptyProject)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()
        treewidget = widget.treewidget

        editor.set_projects(self)

        treewidget.sig_open_file_requested.connect(editor.load)
        treewidget.sig_removed.connect(editor.removed)
        treewidget.sig_tree_removed.connect(editor.removed_tree)
        treewidget.sig_renamed.connect(editor.renamed)
        treewidget.sig_tree_renamed.connect(editor.renamed_tree)
        treewidget.sig_module_created.connect(editor.new)
        treewidget.sig_file_created.connect(self._new_editor)

        widget.sig_save_open_files_requested.connect(editor.save_open_files)
        widget.sig_project_loaded.connect(self._setup_editor_files)
        widget.sig_project_closed[bool].connect(self._setup_editor_files)
        widget.sig_project_loaded.connect(self._set_path_in_editor)
        widget.sig_project_closed.connect(self._unset_path_in_editor)

    @on_plugin_available(plugin=Plugins.Completions)
    def on_completions_available(self):
        self._completions = self.get_plugin(Plugins.Completions)
        widget = self.get_widget()

        # TODO: This is not necessary anymore due to us starting workspace
        # services in the editor. However, we could restore it in the future.
        # completions.sig_language_completions_available.connect(
        #     lambda settings, language:
        #         self.start_workspace_services())
        self._completions.sig_stop_completions.connect(
            self.stop_workspace_services)
        widget.sig_project_loaded.connect(self._add_path_to_completions)
        widget.sig_project_closed.connect(self._remove_path_from_completions)
        widget.sig_broadcast_notification_requested.connect(
            self._broadcast_notification)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        widget = self.get_widget()
        treewidget = widget.treewidget

        widget.sig_restart_console_requested.connect(ipyconsole.restart)
        treewidget.sig_open_interpreter_requested.connect(
            ipyconsole.create_client_from_path)
        treewidget.sig_run_requested.connect(self._run_file_in_ipyconsole)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        new_project_action = self.get_action(ProjectsActions.NewProject)
        open_project_action = self.get_action(ProjectsActions.OpenProject)
        close_project_action = self.get_action(ProjectsActions.CloseProject)
        delete_project_action = self.get_action(ProjectsActions.DeleteProject)

        projects_menu = main_menu.get_application_menu(
            ApplicationMenus.Projects)
        projects_menu.aboutToShow.connect(self._is_invalid_active_project)

        main_menu.add_item_to_application_menu(
            new_project_action,
            menu_id=ApplicationMenus.Projects,
            section=ProjectsMenuSections.New)

        for item in [open_project_action, close_project_action,
                     delete_project_action]:
            main_menu.add_item_to_application_menu(
                item,
                menu_id=ApplicationMenus.Projects,
                section=ProjectsMenuSections.Open)

        main_menu.add_item_to_application_menu(
            self.get_widget().recent_project_menu,
            menu_id=ApplicationMenus.Projects,
            section=ProjectsMenuSections.Extras)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()
        treewidget = widget.treewidget

        editor.set_projects(None)

        treewidget.sig_open_file_requested.disconnect(editor.load)
        treewidget.sig_removed.disconnect(editor.removed)
        treewidget.sig_tree_removed.disconnect(editor.removed_tree)
        treewidget.sig_renamed.disconnect(editor.renamed)
        treewidget.sig_tree_renamed.disconnect(editor.renamed_tree)
        treewidget.sig_module_created.disconnect(editor.new)
        treewidget.sig_file_created.disconnect(self._new_editor)

        widget.sig_save_open_files_requested.disconnect(editor.save_open_files)
        widget.sig_project_loaded.disconnect(self._setup_editor_files)
        widget.sig_project_closed[bool].disconnect(self._setup_editor_files)
        widget.sig_project_loaded.disconnect(self._set_path_in_editor)
        widget.sig_project_closed.disconnect(self._unset_path_in_editor)

    @on_plugin_teardown(plugin=Plugins.Completions)
    def on_completions_teardown(self):
        self._completions = self.get_plugin(Plugins.Completions)
        widget = self.get_widget()

        self._completions.sig_stop_completions.disconnect(
            self.stop_workspace_services)

        widget.sig_project_loaded.disconnect(self._add_path_to_completions)
        widget.sig_project_closed.disconnect(
            self._remove_path_from_completions)
        widget.sig_broadcast_notification_requested.disconnect(
            self._broadcast_notification)

        self._completions = None

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        widget = self.get_widget()
        treewidget = widget.treewidget

        widget.sig_restart_console_requested.disconnect(ipyconsole.restart)
        treewidget.sig_open_interpreter_requested.disconnect(
            ipyconsole.create_client_from_path)
        treewidget.sig_run_requested.disconnect(self._run_file_in_ipyconsole)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        main_menu.remove_application_menu(ApplicationMenus.Projects)

    def on_close(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.get_widget().save_config()
        self.get_widget().watcher.stop()
        return True

    def on_mainwindow_visible(self):
        # Open project passed on the command line or reopen last one.
        cli_options = self.get_command_line_options()
        initial_cwd = self._main.get_initial_working_directory()

        if cli_options.project is not None:
            logger.debug('Opening project from the command line')
            project = osp.normpath(
                osp.join(initial_cwd, cli_options.project)
            )
            self.open_project(
                project,
                workdir=cli_options.working_directory
            )
        else:
            logger.debug('Reopening project from last session')
            self.get_widget().reopen_last_project()

    # ---- Public API
    # -------------------------------------------------------------------------
    def create_project(self, path, project_type_id=EmptyProject.ID):
        """
        Create a new project.

        Parameters
        ----------
        path: str
            Filesystem path where the project will be created.
        project_type_id: str, optional
            Id for the project type. The default is 'empty-project-type'.
        packages: list, optional
            Package to install. Currently not in use.
        """
        self.get_widget().create_project(path, project_type_id)

    def open_project(self, path=None, project_type=None, restart_console=True,
                     save_previous_files=True, workdir=None):
        """
        Open the project located in a given path.

        Parameters
        ----------
        path: str
            Filesystem path where the project is located.
        project_type: spyder.plugins.projects.api.BaseProjectType, optional
            Project type class.
        restart_console: bool, optional
            Whether to restart the IPython console (i.e. close all consoles and
            reopen a single one) after opening the project. The default is
            True.
        save_previous_files: bool, optional
            Whether to save the list of previous open files in the editor
            before opening the project. The default is True.
        workdir: str, optional
            Working directory to set after opening the project. The default is
            None.
        """
        self.get_widget().open_project(
            path, project_type, restart_console, save_previous_files, workdir
        )

    def close_project(self):
        """
        Close current project and return to a window without an active project.
        """
        self.get_widget().close_project()

    def delete_project(self):
        """
        Delete the current project without deleting the files in the directory.
        """
        self.get_widget().delete_project()

    def get_active_project(self):
        """Get the active project."""
        return self.get_widget().current_active_project

    def get_project_filenames(self):
        """Get the list of recent filenames of a project."""
        return self.get_widget().get_project_filenames()

    def set_project_filenames(self, filenames):
        """
        Set the list of open file names in a project.

        Parameters
        ----------
        filenames: list of strings
            File names to save in the project config options.
        """
        self.get_widget().set_project_filenames(filenames)

    def get_active_project_path(self):
        """Get path of the active project."""
        return self.get_widget().get_active_project_path()

    def get_last_working_dir(self):
        """Get the path of the last working directory."""
        return self.get_conf(
            'last_working_dir', section='editor', default=getcwd_or_home()
        )

    def is_valid_project(self, path):
        """
        Check if a directory is a valid Spyder project.

        Parameters
        ----------
        path: str
            Filesystem path to the project.
        """
        return self.get_widget().is_valid_project(path)

    def start_workspace_services(self):
        """Enable LSP workspace functionality."""
        self.get_widget().start_workspace_services()

    def stop_workspace_services(self, _language):
        """Disable LSP workspace functionality."""
        self.get_widget().stop_workspace_services()

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

    def get_project_types(self):
        """
        Return available registered project types.

        Returns
        -------
        dict
            Project types dictionary. Keys are project type IDs and values
            are project type classes.
        """
        return self.get_widget().get_project_types()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _new_editor(self, text):
        editor = self.get_plugin(Plugins.Editor)
        editor.new(text=text)

    def _setup_editor_files(self, __unused):
        editor = self.get_plugin(Plugins.Editor)
        editor.setup_open_files()

    def _set_path_in_editor(self, path):
        editor = self.get_plugin(Plugins.Editor)
        editor.set_current_project_path(path)

    def _unset_path_in_editor(self, __unused):
        editor = self.get_plugin(Plugins.Editor)
        editor.set_current_project_path()

    def _add_path_to_completions(self, path):
        self._completions.project_path_update(
            path,
            update_kind=WorkspaceUpdateKind.ADDITION,
            instance=self.get_widget()
        )

    def _remove_path_from_completions(self, path):
        self._completions.project_path_update(
            path,
            update_kind=WorkspaceUpdateKind.DELETION,
            instance=self.get_widget()
        )

    def _run_file_in_ipyconsole(self, fname):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyconsole.run_script(
            filename=fname,
            wdir=osp.dirname(fname),
            current_client=False,
            clear_variables=True
        )

    def _show_main_widget(self):
        """Show the main widget."""
        if self.get_widget() is not None:
            self.get_widget().show_widget()

    def _get_open_filenames(self):
        editor = self.get_plugin(Plugins.Editor)
        if editor is not None:
            return editor.get_open_filenames()

    def _is_invalid_active_project(self):
        """Handle an invalid active project."""
        self.get_widget().is_invalid_active_project()

    def _broadcast_notification(self, method, params):
        self._completions.broadcast_notification(method, params)
