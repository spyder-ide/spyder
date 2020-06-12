# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer main widget."""

# Standard library imports
import configparser
import functools
import os.path as osp
import shutil
from collections import OrderedDict

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QHBoxLayout, QHeaderView,
                            QInputDialog, QLabel, QMessageBox,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainWidget
from spyder.config.base import (get_home_dir, get_project_config_folder,
                                running_under_pytest)
from spyder.plugins.completion.manager.api import (FileChangeType,
                                                   LSPRequestTypes)
from spyder.plugins.completion.manager.decorators import (class_register,
                                                          handles, request)
from spyder.plugins.projects.api import BaseProjectType
from spyder.plugins.projects.project_types import EmptyProject
from spyder.plugins.projects.utils.config import WORKSPACE
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher
from spyder.plugins.projects.widgets.explorer import ExplorerTreeWidget
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.utils import encoding, misc
from spyder.utils.misc import getcwd_or_home

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class ProjectExplorerWidgetActions:
    Create = 'create_project_action'
    Open = 'open_project_action'
    Close = 'close_project_action'
    Delete = 'delete_project_action'
    ClearRecent = 'clear_recent_projects_action'
    MaximumProjects = 'maximum_projects_action'


class ProjectExplorerWidgetMenus:
    RecentProjects = 'recent_projects_submenu'


# --- Widgets
# ----------------------------------------------------------------------------
@class_register
class ProjectExplorerWidget(PluginMainWidget):

    DEFAULT_OPTIONS = {
        'current_project_path': '',
        'expanded_state': '',
        'max_recent_projects': 10,
        'name_filters': [],
        'recent_projects': [],
        'scrollbar_position': '',
        'show_all': True,
        'horizontal_scrollbar': True,  # show_hscrollbar
        'single_click_to_open': False,
        'visible_if_project_open': '',
        'last_project': '',
    }

    # --- Signals
    # ------------------------------------------------------------------------
    sig_externally_opened = Signal(str)

    sig_project_created = Signal(str, str, object)
    """
    This signal is emitted to inform a project has been created.

    Parameters
    ----------
    project_instance: spyder.plugins.projects.api.BaseProjectType
        Project type instance.
    """

    sig_project_opened = Signal(object)
    """
    This signal is emitted to inform a project has been opened.

    Parameters
    ----------
    project_instance: spyder.plugins.projects.api.BaseProjectType
        Project type instance.
    """

    sig_project_closed = Signal(object)
    """
    This signal is emitted to inform a project has been closed.

    Parameters
    ----------
    project_instance: spyder.plugins.projects.api.BaseProjectType
        Project type instance.
    """

    sig_project_deleted = Signal(object)
    """
    This signal is emitted to inform a project has been deleted.

    Parameters
    ----------
    project_instance: spyder.plugins.projects.api.BaseProjectType
        Project type instance.
    """

    # --- Explorer Signals
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
        Deleted folder.
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

    # --- Completions
    sig_broadcast_notification = Signal(str, dict)
    """
    FIXME

    Parameters
    ----------
    FIXME: str
        FIXME
    FIXME: dict
        FIXME
    """

    # --- Consoles
    sig_restart_consoles_requested = Signal()
    """
    This signal is emitted to request a console restart.
    """

    # FIXME:
    sig_create_module_requested = Signal(str)
    sig_file_opened = Signal(str)

    def __init__(self, name=None, plugin=None, parent=None,
                 options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        self._completions_available = False
        self._current_active_project = None
        self._project_types = OrderedDict()

        # Widgets or objects
        self.watcher = WorkspaceWatcher(parent=self)
        self.treewidget = ExplorerTreeWidget(parent=self, options=options)

        # self.latest_project = None
        # name_filters=self.name_filters,
        # show_all=self.show_all,
        # single_click_to_open=False,

        # Widget setup
        # self.treewidget.setup(options)
        # self.treewidget.setup_view()
        # self.treewidget.hide()
        # self.setup_project(self.get_active_project_path())

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

        # Signals
        self.treewidget.sig_renamed.connect(self.sig_file_renamed)
        self.treewidget.sig_removed.connect(self.sig_file_deleted)
        self.treewidget.sig_removed_tree.connect(self.sig_folder_renamed)
        self.treewidget.sig_renamed_tree.connect(self.sig_folder_deleted)

        self.watcher.sig_file_created.connect(self.notify_file_created)
        self.watcher.sig_file_moved.connect(self.notify_file_moved)
        self.watcher.sig_file_deleted.connect(self.notify_file_deleted)
        self.watcher.sig_file_modified.connect(self.notify_file_modified)

    # --- PluginMainWidget
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Projects")

    def get_focus_widget(self):
        return self.treewidget

    def setup(self, options=DEFAULT_OPTIONS):
        self.create_action(
            ProjectExplorerWidgetActions.Create,
            text=_("New Project..."),
            triggered=self.create_project,
        )
        self.open_project_action = self.create_action(
            ProjectExplorerWidgetActions.Open,
            text=_("Open Project..."),
            triggered=lambda v: self.open_project(),
        )
        self.close_project_action =self. create_action(
            ProjectExplorerWidgetActions.Close,
            _("Close Project"),
            triggered=self.close_project,
        )
        self.delete_project_action = self.create_action(
            ProjectExplorerWidgetActions.Delete,
            text=_("Delete Project"),
            triggered=self.delete_project,
        )
        self.clear_recent_projects_action = self.create_action(
            ProjectExplorerWidgetActions.ClearRecent,
            text=_("Clear this list"),
            triggered=self.clear_recent_projects,
        )
        self.max_recent_action = self.create_action(
            ProjectExplorerWidgetActions.MaximumProjects,
            text=_("Maximum number of recent projects..."),
            triggered=self.change_max_recent_projects,
        )
        self.recent_project_menu = self.create_menu(
            ProjectExplorerWidgetMenus.RecentProjects,
            _("Recent Projects"),
        )

    def on_option_update(self, option, value):
        if option == 'single_click_to_open':
            self.treewidget.set_single_click_to_open(value)

    def update_actions(self):
        recent_projects_actions = []
        recent_projects = self.get_option('recent_projects').copy()
        if recent_projects:
            for project_path in recent_projects:
                if self.is_valid_project(project_path):
                    name = project_path.replace(get_home_dir(), '~')
                    try:
                        action = self.create_action(
                            name,
                            text=name,
                            icon=self.create_icon('project'),
                            triggered=lambda: self.open_project(project_path),
                            register_shortcut=False,
                        )
                    except SpyderAPIError:
                        # Action already exists
                        action = self.get_action(name)

                    recent_projects_actions.append(action)

        # Recreate the menu
        self.recent_project_menu.clear()
        for item in recent_projects_actions:
            self.add_item_to_menu(
                item,
                self.recent_project_menu,
                section='recent_section',
            )

        for item in [self.clear_recent_projects_action,
                     self.max_recent_action]:
            self.add_item_to_menu(
                item,
                self.recent_project_menu,
                section='bottom_section',
            )

        # Update project menu actions
        self.clear_recent_projects_action.setEnabled(
            bool(self.get_option('recent_projects')))
        active = bool(self.get_active_project_path())
        self.close_project_action.setEnabled(active)
        self.delete_project_action.setEnabled(active)

    # --- Private API
    # ------------------------------------------------------------------------
    def _add_to_recent(self, project_path):
        """
        Add an entry to recent projects.

        Parameters
        ----------
        project_path: str
            Path to project root folder.

        Notes
        -----
        The list only stores the `max_recent_projects` amount.
        """
        recent_projects = self.get_option('recent_projects').copy()
        if project_path not in recent_projects:
            recent_projects.insert(0, project_path)

        max_projects = self.get_option('max_recent_projects')
        self.set_option('recent_projects', recent_projects[:max_projects])

    def _create_project(self, root_path, project_type=EmptyProject.ID,
                        packages=None):
        """Create a new project."""
        project_types = self.get_project_types()
        if project_type in project_types:
            project_type_class = project_types[project_type]
            project = project_type_class(
                root_path, project_type_class._PARENT_PLUGIN)

            created_succesfully, message = project.create_project()
            if not created_succesfully:
                QMessageBox.warning(self, "Project creation", message)
                shutil.rmtree(root_path, ignore_errors=True)
                return

            # TODO: In a subsequent PR return a value and emit based on that
            self.sig_project_created.emit(root_path, project_type, packages)
            self.open_project(path=root_path, project=project)
        else:
            if not running_under_pytest():
                QMessageBox.critical(
                    self,
                    _('Error'),
                    _("<b>{}</b> is not a registered Spyder project "
                      "type!").format(project_type)
                )

    def _load_project_type(self, path):
        """
        Load a project type from the config project folder directly.

        Notes
        -----
        This is done directly, since using the EmptyProject would rewrite the
        value in the constructor.
        """
        fpath = osp.join(
            path, get_project_config_folder(), 'config', WORKSPACE + ".ini")

        project_type = EmptyProject.ID
        if osp.isfile(fpath):
            config = configparser.ConfigParser()
            config.read(fpath)
            project_type = config[WORKSPACE].get("project_type", EmptyProject.ID)

        return project_type

    # --- Public API
    # ------------------------------------------------------------------------
    @Slot()
    def create_project(self):
        """Create project."""
        active_project = self._current_active_project
        dlg = ProjectDialog(self, project_types=self.get_project_types())
        result = dlg.exec_()

        data = dlg.project_data
        root_path = data.get("root_path", None)
        project_type = data.get("project_type", EmptyProject.ID)

        if result:
            # A project was not open before
            if active_project is None:
                if self.get_option('visible_if_project_open'):
                    self.change_visibility(True)
            else:
                # We are switching projects.
                # TODO: Don't emit sig_project_closed when we support
                # multiple workspaces.
                self.sig_project_closed.emit(active_project.root_path)

            self._create_project(root_path, project_type=project_type)
            self.sig_pythonpath_changed.emit()
            self.sig_restart_consoles_requested.emit()
            dlg.close()

    def open_project(self, path=None, project=None, restart_consoles=True,
                     save_previous_files=True):
        """
        Open the project located in `path`.

        Parameters
        ----------
        path: str or None
            Root path of project. Default is `None`.
        project_instance: spyder.plugins.projects.api.BaseProjectType or None, optional
            Project type instance. Default is `None`.
        restart_consoles: bool, optional
            Request a console restart. Default is `True`.
        save_previous_files: bool, optional
            Save previous files. Default is `True`.

        """
        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(
                parent=self,
                caption=_("Open project"),
                basedir=basedir,
            )
            path = encoding.to_unicode_from_fs(path)

            if not self.is_valid_project(path):
                if path:
                    QMessageBox.critical(
                        self,
                        _('Error'),
                        _("<b>%s</b> is not a Spyder project!") % path,
                    )

                return
        else:
            path = encoding.to_unicode_from_fs(path)

        if project is None:
            project_type = self._load_project_type(path)
            project_types = self.get_project_types()
            if project_type in project_types:
                project = project_types[project_type](path, self)
            else:
                project = EmptyProject(path, self)

        # A project was not open before
        if self._current_active_project is None:
            # FIXME:
            if save_previous_files and self.main.editor is not None:
                self.main.editor.save_open_files()

            # FIXME:
            if self.main.editor is not None:
                self.main.editor.set_option('last_working_dir',
                                            getcwd_or_home())

            if self.get_option('visible_if_project_open'):
                self.change_visibility(True)
        else:
            # We are switching projects
            # FIXME:
            if self.main.editor is not None:
                self.set_project_filenames(
                    self.main.editor.get_open_filenames())

            # TODO: Don't emit sig_project_closed when we support
            # multiple workspaces.
            self.sig_project_closed.emit(
                self._current_active_project.root_path)

        self._current_active_project = project
        self.latest_project = project
        self.notify_project_open(path)
        self._add_to_recent(path)

        self.set_option('current_project_path', self.get_active_project_path())

        self.setup_menu_actions()
        self.sig_project_loaded.emit(path)
        self.sig_pythonpath_changed.emit()
        self.watcher.start(path)

        if restart_consoles:
            self.sig_restart_consoles_requested.emit()

        open_successfully, message = project.open_project()
        if not open_successfully:
            QMessageBox.warning(self, "Project open", message)

        return project

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self._current_active_project:
            # self.unmaximize()
            # FIXME:
            if self.main.editor is not None:
                self.set_project_filenames(
                    self.main.editor.get_open_filenames())

            path = self._current_active_project.root_path
            closed_sucessfully, message = (
                self._current_active_project.close_project())
            if not closed_sucessfully:
                QMessageBox.warning(self, "Project close", message)

            self._current_active_project = None
            self.set_option('current_project_path', None)
            self.setup_menu_actions()

            self.sig_project_closed.emit(path)
            self.sig_pythonpath_changed.emit()

            if self.dockwidget is not None:
                self.set_option('visible_if_project_open',
                                self.dockwidget.isVisible())
                self.dockwidget.close()

            self.explorer.clear()
            self.sig_restart_consoles_requested.emit()
            self.watcher.stop()
            self.notify_project_close(path)

    def delete_project(self):
        """
        Delete the current project without deleting the files in the directory.
        """
        if self._current_active_project:
            # self.unmaximize()
            path = self._current_active_project.root_path
            buttons = QMessageBox.Yes | QMessageBox.No
            answer = QMessageBox.warning(
                self,
                _("Delete"),
                _("Do you really want to delete <b>{filename}</b>?<br><br>"
                  "<b>Note:</b> This action will only delete the project. "
                  "Its files are going to be preserved on disk."
                  ).format(filename=osp.basename(path)),
                buttons)

            if answer == QMessageBox.Yes:
                try:
                    self.close_project()
                    shutil.rmtree(osp.join(path, '.spyproject'))
                except EnvironmentError as error:
                    QMessageBox.critical(
                        self,
                        _("Project Explorer"),
                        _("<b>Unable to delete <i>{varpath}</i></b>"
                          "<br><br>The error message was:<br>{error}"
                          ).format(varpath=path, error=str(error)))

    def is_valid_project(self, path):
        """
        Check if a directory is a valid Spyder project.

        Parameters
        ----------
        path: str
            Project location.

        Returns
        -------
        bool
            Return whether a project found at `path` is valid or not.
        """
        spy_project_dir = osp.join(path, '.spyproject')
        return osp.isdir(path) and osp.isdir(spy_project_dir)

    def clear_recent_projects(self):
        """Clear the list of recent projects."""
        self.set_option('recent_projects', [])
        self.update_actions()

    def change_max_recent_projects(self, value=None):
        """
        Change the maximum number of recent projects entries.

        Parameters
        ----------
        value: int or None, optional
            Value to use. If no value is provided an input dialog is used.
        """
        if value is None:
            value, valid = QInputDialog.getInt(
                self,
                _('Projects'),
                _('Maximum number of recent projects'),
                self.get_option('max_recent_projects'),
                1,
                35,
            )

        if valid:
            self.set_option('max_recent_projects', value)

    def get_active_project(self):
        """Get the active project."""
        return self._current_active_project

    # def load_project(self, project_path):
    #     """FIXME"""
    #     self.explorer.setup_project(project_path)

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
        if not issubclass(project_type, BaseProjectType):
            raise SpyderAPIError("A project type must subclass "
                                 "BaseProjectType!")

        project_id = project_type.ID
        if project_id in self._project_types:
            raise SpyderAPIError("A project type id '{}' has already been "
                                 "registered!".format(project_id))

        project_type._PARENT_PLUGIN = parent_plugin
        self._project_types[project_id] = project_type

    def get_project_types(self):
        """
        Return available registered project types.

        Returns
        -------
        dict
            Project types dictionary.
        """
        return self._project_types

    def get_project_filenames(self):
        """Get the list of recent filenames of a project."""
        recent_files = []
        if self._current_active_project:
            recent_files = self._current_active_project.get_recent_files()
        elif self.latest_project:
            recent_files = self.latest_project.get_recent_files()

        return recent_files

    def set_project_filenames(self, recent_files):
        """Set the list of open file names in a project"""
        if (self._current_active_project
                and self.is_valid_project(
                        self._current_active_project.root_path)):
            self._current_active_project.set_recent_files(recent_files)

    def get_active_project_path(self):
        """Get path of the active project."""
        active_project_path = None
        if self._current_active_project:
            active_project_path = self._current_active_project.root_path

        return active_project_path

    # def get_last_working_dir(self):
    #     """Get the path of the last working directory"""
    #     return self.main.editor.get_option('last_working_dir',
    #                                        default=getcwd_or_home())

    # def save_config(self):
    #     """
    #     Save configuration: opened projects & tree widget state.

    #     Also save whether dock widget is visible if a project is open.
    #     """
    #     self.set_option('recent_projects', self.recent_projects)
    #     self.set_option('expanded_state',
    #                     self.explorer.treewidget.get_expanded_state())
    #     self.set_option('scrollbar_position',
    #                     self.explorer.treewidget.get_scrollbar_position())
    #     if self._current_active_project and self.dockwidget:
    #         self.set_option('visible_if_project_open',
    #                         self.dockwidget.isVisible())

    # def load_config(self):
    #     """Load configuration: opened projects & tree widget state."""
    #     expanded_state = self.get_option('expanded_state', None)
    #     # Sometimes the expanded state option may be truncated in .ini file
    #     # (for an unknown reason), in this case it would be converted to a
    #     # string by 'userconfig':
    #     if isinstance(expanded_state, str):
    #         expanded_state = None
    #     if expanded_state is not None:
    #         self.explorer.treewidget.set_expanded_state(expanded_state)

    # def restore_scrollbar_position(self):
    #     """Restoring scrollbar position after main window is visible."""
    #     scrollbar_pos = self.get_option('scrollbar_position', None)
    #     if scrollbar_pos is not None:
    #         self.explorer.treewidget.set_scrollbar_position(scrollbar_pos)

    # def update_explorer(self):
    #     """Update explorer tree."""
    #     self.explorer.setup_project(self.get_active_project_path())

    # --- Completions
    def register_lsp_server_settings(self, settings):
        """Enable LSP workspace functions."""
        self._completions_available = True
        if self._current_active_project:
            path = self.get_active_project_path()
            self.notify_project_open(path)

    def stop_lsp_services(self):
        """Disable LSP workspace functions."""
        self._completions_available = False

    def emit_request(self, method, params, requires_response):
        """Send request/notification/response to all LSP servers."""
        params['requires_response'] = requires_response
        params['response_instance'] = self
        self.sig_broadcast_notification.emit(method, params)

    @Slot(str, dict)
    def handle_response(self, method, params):
        """Method dispatcher for LSP requests."""
        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)

    @Slot(str, str)
    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    def notify_file_moved(self, src_file, dest_file):
        """
        Notify LSP server about a file that is moved.

        Parameters
        ----------
        src_file: str
            The old file path.
        dest_file: str
            The new file path.
        """
        deletion_entry = {
            'file': src_file,
            'kind': FileChangeType.DELETED
        }

        addition_entry = {
            'file': dest_file,
            'kind': FileChangeType.CREATED
        }

        entries = [addition_entry, deletion_entry]
        params = {
            'params': entries
        }
        return params

    @Slot(str)
    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    def notify_file_created(self, src_file):
        """
        Notify LSP server about file creation.

        Parameters
        ----------
        src_file: str
            The created file path.
        """
        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.CREATED
            }]
        }
        return params

    @Slot(str)
    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    def notify_file_deleted(self, src_file):
        """
        Notify LSP server about file deletion.

        Parameters
        ----------
        src_file: str
            The deleted file path.
        """
        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.DELETED
            }]
        }
        return params

    @Slot(str)
    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    def notify_file_modified(self, src_file):
        """
        Notify LSP server about file modification.

        Parameters
        ----------
        src_file: str
            The modified file path.
        """
        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.CHANGED
            }]
        }
        return params

    @request(method=LSPRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_open(self, path):
        """
        Notify LSP server about project path availability.

        Parameters
        ----------
        path: str
            The root path of the opened project.
        """
        params = {
            'folder': path,
            'instance': self,
            'kind': 'addition'
        }
        return params

    @request(method=LSPRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_close(self, path):
        """
        Notify LSP server to unregister project path.

        Parameters
        ----------
        path: str
            The root path of the closed project.
        """
        params = {
            'folder': path,
            'instance': self,
            'kind': 'deletion'
        }
        return params

    @handles(LSPRequestTypes.WORKSPACE_APPLY_EDIT)
    @request(method=LSPRequestTypes.WORKSPACE_APPLY_EDIT,
             requires_response=False)
    def handle_workspace_edit(self, params):
        """
        Apply edits to multiple files and notify server about success.

        Parameters
        ----------
        params: dict
            Workspaces edit options.
        """
        edits = params['params']
        response = {
            'applied': False,
            'error': 'Not implemented',
            'language': edits['language']
        }
        return response

    # --- Python specific
    def get_pythonpath(self, at_start=False):
        """Get project path as a list to be added to PYTHONPATH."""
        if at_start:
            current_path = self.get_option('current_project_path')
        else:
            current_path = self.get_active_project_path()

        if current_path is None:
            return []
        else:
            return [current_path]


# ============================================================================
# Tests
# ============================================================================
class ProjectExplorerTest(QWidget):

    def __init__(self, directory=None):
        super().__init__()
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(self, show_all=True)
        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))
        self.explorer.setup_project(self.directory)
        vlayout.addWidget(self.explorer)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file.connect(self.label1.setText)

        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.explorer.sig_option_changed.connect(
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))


def test():
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    test = ProjectExplorerTest()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
