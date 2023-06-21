# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Projects main widget."""

# Standard library imports
from collections import OrderedDict
import configparser
import logging
import os
import os.path as osp
import pathlib
import shutil

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QMessageBox, QVBoxLayout, QWidget)

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.base import (
    get_home_dir, get_project_config_folder, running_under_pytest)
from spyder.plugins.completion.api import (
    CompletionRequestTypes, FileChangeType)
from spyder.plugins.completion.decorators import (
    class_register, handles, request)
from spyder.plugins.explorer.api import DirViewActions
from spyder.plugins.projects.api import (
    BaseProjectType, EmptyProject, WORKSPACE)
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.plugins.projects.widgets.projectexplorer import (
    ProjectExplorerTreeWidget)
from spyder.utils import encoding
from spyder.utils.misc import getcwd_or_home


# For logging
logger = logging.getLogger(__name__)


# ---- Constants
# -----------------------------------------------------------------------------
class ProjectExplorerOptionsMenuSections:
    Main = 'main'


class ProjectsActions:
    NewProject = 'new_project_action'
    OpenProject = 'open_project_action'
    CloseProject = 'close_project_action'
    DeleteProject = 'delete_project_action'
    ClearRecentProjects = 'clear_recent_projects_action'
    MaxRecent = 'max_recent_action'


class ProjectsMenuSubmenus:
    RecentProjects = 'recent_projects'


class RecentProjectsMenuSections:
    Recent = 'recent_section'
    Extras = 'extras_section'


# ---- Main widget
# -----------------------------------------------------------------------------
@class_register
class ProjectExplorerWidget(PluginMainWidget):
    """Project Explorer"""

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted when a file is requested to be opened.

    Parameters
    ----------
    directory: str
        The path to the requested file.
    """

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

    sig_save_open_files_requested = Signal()
    """
    This signal is emitted to request saving the list of open files in the
    editor.
    """

    sig_restart_console_requested = Signal()
    """This signal is emitted to request restarting the IPython console."""

    sig_broadcast_notification_requested = Signal(str, dict)
    """
    This signal is emitted to request that the Completions plugin broadcast
    a notification.

    Parameters
    ----------
    method: str
        Method name to broadcast.
    params: dict
        Parameters of the notification.
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin=plugin, parent=parent)

        # Attributes from conf
        self.name_filters = self.get_conf('name_filters')
        self.show_hscrollbar = self.get_conf('show_hscrollbar')

        # Main attributes
        self.recent_projects = self._get_valid_recent_projects(
            self.get_conf('recent_projects', [])
        )
        self._project_types = OrderedDict()
        self.current_active_project = None
        self.latest_project = None
        self.completions_available = False

        # Tree widget
        self.treewidget = ProjectExplorerTreeWidget(self, self.show_hscrollbar)
        self.treewidget.setup()
        self.treewidget.setup_view()
        self.treewidget.hide()
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)

        # Empty widget to show when there's no active project
        self.emptywidget = ProjectExplorerTreeWidget(self)

        # Watcher
        self.watcher = WorkspaceWatcher(self)
        self.watcher.connect_signals(self)

        # Signals
        self.sig_project_loaded.connect(self._update_explorer)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.emptywidget)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)
        self.setMinimumWidth(200)

        # Initial setup
        self._setup_project(self.get_active_project_path())

    # ---- PluginMainWidget API
    # -------------------------------------------------------------------------
    def get_title(self):
        return _("Projects")

    def setup(self):
        """Setup the widget."""
        # Create default actions
        self.create_action(
            ProjectsActions.NewProject,
            text=_("New Project..."),
            triggered=self.create_new_project)

        self.create_action(
            ProjectsActions.OpenProject,
            text=_("Open Project..."),
            triggered=lambda v: self.open_project())

        self.close_project_action = self.create_action(
            ProjectsActions.CloseProject,
            text=_("Close Project"),
            triggered=self.close_project)

        self.delete_project_action = self.create_action(
            ProjectsActions.DeleteProject,
            text=_("Delete Project"),
            triggered=self.delete_project)

        self.clear_recent_projects_action = self.create_action(
            ProjectsActions.ClearRecentProjects,
            text=_("Clear this list"),
            triggered=self.clear_recent_projects)

        self.max_recent_action = self.create_action(
            ProjectsActions.MaxRecent,
            text=_("Maximum number of recent projects..."),
            triggered=self.change_max_recent_projects)

        self.recent_project_menu = self.create_menu(
            ProjectsMenuSubmenus.RecentProjects,
            _("Recent Projects")
        )
        self.recent_project_menu.aboutToShow.connect(self._setup_menu_actions)
        self._setup_menu_actions()

        # Add some DirView actions to the Options menu for easy access.
        menu = self.get_options_menu()
        hidden_action = self.get_action(DirViewActions.ToggleHiddenFiles)
        single_click_action = self.get_action(DirViewActions.ToggleSingleClick)

        for action in [hidden_action, single_click_action]:
            self.add_item_to_menu(
                action,
                menu=menu,
                section=ProjectExplorerOptionsMenuSections.Main)

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    @Slot()
    def create_new_project(self):
        """Create new project."""
        self._unmaximize()

        dlg = ProjectDialog(self, project_types=self.get_project_types())
        result = dlg.exec_()
        data = dlg.project_data
        root_path = data.get("root_path", None)
        project_type = data.get("project_type", EmptyProject.ID)

        if result:
            logger.debug(f'Creating a project at {root_path}')
            self.create_project(root_path, project_type_id=project_type)
            dlg.close()

    def create_project(self, root_path, project_type_id=EmptyProject.ID):
        """Create a new project."""
        project_types = self.get_project_types()
        if project_type_id in project_types:
            project_type_class = project_types[project_type_id]
            project_type = project_type_class(
                root_path=root_path,
                parent_plugin=project_type_class._PARENT_PLUGIN,
            )

            created_succesfully, message = project_type.create_project()
            if not created_succesfully:
                QMessageBox.warning(self, "Project creation", message)
                shutil.rmtree(root_path, ignore_errors=True)
                return

            self.sig_project_created.emit(root_path, project_type_id)
            self.open_project(path=root_path, project_type=project_type)
        else:
            if not running_under_pytest():
                QMessageBox.critical(
                    self,
                    _('Error'),
                    _("<b>{}</b> is not a registered Spyder project "
                      "type!").format(project_type_id)
                )

    def open_project(self, path=None, project_type=None, restart_console=True,
                     save_previous_files=True, workdir=None):
        """Open the project located in `path`."""
        self._unmaximize()

        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(
                parent=self,
                caption=_("Open project"),
                basedir=basedir
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

        # This makes the path have a uniform representation in all OSes. For
        # instance, it always uses backslashes as separators on Windows.
        path = str(pathlib.Path(path))

        logger.debug(f'Opening project located at {path}')

        if project_type is None:
            project_type_class = self._load_project_type_class(path)
            project_type = project_type_class(
                root_path=path,
                parent_plugin=project_type_class._PARENT_PLUGIN,
            )

        if self.current_active_project is None:
            # A project was not open before
            if save_previous_files:
                self.sig_save_open_files_requested.emit()

            self.set_conf('last_working_dir', getcwd_or_home(),
                          section='editor')

            if self.get_conf('visible_if_project_open'):
                self.show_widget()
        else:
            # We are switching projects
            filenames = self.get_plugin()._get_open_filenames()
            if filenames is not None:
                self.set_project_filenames(filenames)

            # TODO: Don't emit sig_project_closed when we support
            # multiple workspaces.
            self.sig_project_closed.emit(self.current_active_project.root_path)
            self.watcher.stop()

        self.current_active_project = project_type
        self.latest_project = project_type
        self._add_to_recent(path)

        self.set_conf('current_project_path', self.get_active_project_path())

        self._setup_menu_actions()

        if workdir and osp.isdir(workdir):
            self.sig_project_loaded.emit(workdir)
        else:
            self.sig_project_loaded.emit(path)

        self.watcher.start(path)

        if restart_console:
            self.sig_restart_console_requested.emit()

        open_successfully, message = project_type.open_project()
        if not open_successfully:
            QMessageBox.warning(self, "Project open", message)

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self.current_active_project:
            path = self.current_active_project.root_path

            self._unmaximize()
            filenames = self.get_plugin()._get_open_filenames()
            if filenames is not None:
                self.set_project_filenames(filenames)

            closed_sucessfully, message = (
                self.current_active_project.close_project())
            if not closed_sucessfully:
                QMessageBox.warning(self, "Project close", message)
                return

            self.current_active_project = None
            self.set_conf('current_project_path', None)
            self._setup_menu_actions()

            self.sig_project_closed.emit(path)
            self.sig_project_closed[bool].emit(True)

            # Hide pane.
            self.set_conf('visible_if_project_open', self.isVisible())
            self.toggle_view(False)

            self._clear()
            self.sig_restart_console_requested.emit()
            self.watcher.stop()

    def delete_project(self):
        """
        Delete the current project without deleting the files in the directory.
        """
        if self.current_active_project:
            self._unmaximize()
            path = self.current_active_project.root_path

            buttons = QMessageBox.Yes | QMessageBox.No
            answer = QMessageBox.warning(
                self,
                _("Delete"),
                _("Do you really want to delete the <b>{filename}</b> project?"
                  "<br><br>"
                  "<b>Note:</b> This action will only delete the project. "
                  "Its files are going to be preserved on disk."
                  ).format(filename=osp.basename(path)),
                buttons
            )

            if answer == QMessageBox.Yes:
                try:
                    self.close_project()
                    shutil.rmtree(osp.join(path, '.spyproject'))
                except OSError as error:
                    QMessageBox.critical(
                        self,
                        _("Project Explorer"),
                        _("<b>Unable to delete <i>{varpath}</i></b>"
                          "<br><br>The error message was:<br>{error}"
                          ).format(varpath=path, error=str(error))
                    )

                # Remove path from the recent_projects list
                try:
                    self.recent_projects.remove(path)
                except ValueError:
                    pass

    def clear_recent_projects(self):
        """Clear the list of recent projects"""
        self.recent_projects = []
        self.set_conf('recent_projects', self.recent_projects)
        self._setup_menu_actions()

    def change_max_recent_projects(self):
        """Change max recent projects entries."""

        max_projects, valid = QInputDialog.getInt(
            self,
            _('Projects'),
            _('Maximum number of recent projects'),
            self.get_conf('max_recent_projects'),
            1,
            35
        )

        if valid:
            self.set_conf('max_recent_projects', max_projects)

            # This will reduce the number of projects shown in
            # recent_projects_menu according to the new number selected by the
            # user.
            if max_projects < len(self.recent_projects):
                self.recent_projects = self._get_valid_recent_projects(
                    self.recent_projects)[:max_projects]

    def reopen_last_project(self):
        """
        Reopen the active project when Spyder was closed last time, if any
        """
        current_project_path = self.get_conf('current_project_path',
                                             default=None)

        # Needs a safer test of project existence!
        if (
            current_project_path and
            self.is_valid_project(current_project_path)
        ):
            cli_options = self.get_plugin().get_command_line_options()
            self.open_project(
                path=current_project_path,
                restart_console=True,
                save_previous_files=False,
                workdir=cli_options.working_directory
            )
            self._load_config()

    def get_project_filenames(self):
        """Get the list of recent filenames of a project"""
        recent_files = []
        if self.current_active_project:
            recent_files = self.current_active_project.get_recent_files()
        elif self.latest_project:
            recent_files = self.latest_project.get_recent_files()
        return recent_files

    def set_project_filenames(self, filenames):
        """Set the list of open file names in a project."""
        if (
            self.current_active_project
            and self.is_valid_project(self.current_active_project.root_path)
        ):
            self.current_active_project.set_recent_files(filenames)

    def is_valid_project(self, path):
        """Check if a directory is a valid Spyder project"""
        spy_project_dir = osp.join(path, '.spyproject')
        return osp.isdir(path) and osp.isdir(spy_project_dir)

    def is_invalid_active_project(self):
        """Handle an invalid active project."""
        try:
            path = self.get_active_project_path()
        except AttributeError:
            return

        if bool(path):
            if not self.is_valid_project(path):
                if path:
                    QMessageBox.critical(
                        self,
                        _('Error'),
                        _("<b>{}</b> is no longer a valid Spyder project! "
                          "Since it is the current active project, it will "
                          "be closed automatically.").format(path)
                    )

                self.close_project()

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
        """Return available registered project types."""
        return self._project_types

    def get_active_project_path(self):
        """Get path of the active project"""
        if self.current_active_project:
            return self.current_active_project.root_path

    def save_config(self):
        """
        Save configuration: opened projects & tree widget state.

        Also save whether dock widget is visible if a project is open.
        """
        self.set_conf(
            'recent_projects',
            self._get_valid_recent_projects(self.recent_projects)
        )
        self.set_conf('expanded_state', self.treewidget.get_expanded_state())
        self.set_conf('scrollbar_position',
                      self.treewidget.get_scrollbar_position())
        if self.current_active_project:
            self.set_conf('visible_if_project_open', self.isVisible())

    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_conf('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.treewidget.set_scrollbar_position(scrollbar_pos)

    def show_widget(self):
        """Show this widget"""
        self.toggle_view(True)
        self.setVisible(True)
        self.raise_()
        self.update()

    # ---- Public API for the LSP
    # -------------------------------------------------------------------------
    def start_workspace_services(self):
        """Enable LSP workspace functionality."""
        self.completions_available = True
        if self.current_active_project:
            path = self.get_active_project_path()
            self.notify_project_open(path)

    def stop_workspace_services(self):
        """Disable LSP workspace functionality."""
        self.completions_available = False

    def emit_request(self, method, params, requires_response):
        """Send request/notification/response to all LSP servers."""
        params['requires_response'] = requires_response
        params['response_instance'] = self
        self.sig_broadcast_notification_requested.emit(method, params)

    @Slot(str, dict)
    def handle_response(self, method, params):
        """Method dispatcher for LSP requests."""
        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)

    @request(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    @Slot(str, bool)
    def file_created(self, src_file, is_dir):
        """Notify LSP server about file creation."""
        if is_dir:
            return

        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.CREATED
            }]
        }
        return params

    @Slot(str, str, bool)
    @request(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    def file_moved(self, src_file, dest_file, is_dir):
        """Notify LSP server about a file that is moved."""
        # LSP specification only considers file updates
        if is_dir:
            return

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

    @request(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    @Slot(str, bool)
    def file_deleted(self, src_file, is_dir):
        """Notify LSP server about file deletion."""
        if is_dir:
            return

        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.DELETED
            }]
        }
        return params

    @request(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
             requires_response=False)
    @Slot(str, bool)
    def file_modified(self, src_file, is_dir):
        """Notify LSP server about file modification."""
        if is_dir:
            return

        params = {
            'params': [{
                'file': src_file,
                'kind': FileChangeType.CHANGED
            }]
        }
        return params

    @request(method=CompletionRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_open(self, path):
        """Notify LSP server about project path availability."""
        params = {
            'folder': path,
            'instance': self,
            'kind': 'addition'
        }
        return params

    @request(method=CompletionRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_close(self, path):
        """Notify LSP server to unregister project path."""
        params = {
            'folder': path,
            'instance': self,
            'kind': 'deletion'
        }
        return params

    @handles(CompletionRequestTypes.WORKSPACE_APPLY_EDIT)
    @request(method=CompletionRequestTypes.WORKSPACE_APPLY_EDIT,
             requires_response=False)
    def handle_workspace_edit(self, params):
        """Apply edits to multiple files and notify server about success."""
        edits = params['params']
        response = {
            'applied': False,
            'error': 'Not implemented',
            'language': edits['language']
        }
        return response

    # ---- Private API
    # -------------------------------------------------------------------------
    def _set_project_dir(self, directory):
        """Set the project directory"""
        if directory is not None:
            self.treewidget.set_root_path(osp.dirname(directory))
            self.treewidget.set_folder_names([osp.basename(directory)])
        self.treewidget.setup_project_view()

        index = self.treewidget.get_index(directory)
        if index is not None:
            self.treewidget.setExpanded(self.treewidget.get_index(directory),
                                        True)

    def _clear(self):
        """Show an empty view"""
        self.treewidget.hide()
        self.emptywidget.show()

    def _setup_project(self, directory):
        """Setup project"""
        self.emptywidget.hide()
        self.treewidget.show()

        # Setup the directory shown by the tree
        self._set_project_dir(directory)

    def _unmaximize(self):
        """Unmaximize the currently maximized plugin, if not self."""
        if self.get_plugin().main:
            self.sig_unmaximize_plugin_requested[object].emit(
                self.get_plugin()
            )

    def _load_project_type_class(self, path):
        """
        Load a project type class from the config project folder directly.

        Notes
        -----
        This is done directly, since using the EmptyProject would rewrite the
        value in the constructor. If the project found has not been registered
        as a valid project type, the EmptyProject type will be returned.

        Returns
        -------
        spyder.plugins.projects.api.BaseProjectType
            Loaded project type class.
        """
        fpath = osp.join(
            path, get_project_config_folder(), 'config', WORKSPACE + ".ini")

        project_type_id = EmptyProject.ID
        if osp.isfile(fpath):
            config = configparser.ConfigParser()

            # Catch any possible error when reading the workspace config file.
            # Fixes spyder-ide/spyder#17621
            try:
                config.read(fpath, encoding='utf-8')
            except Exception:
                pass

            # This is necessary to catch an error for projects created in
            # Spyder 4 or older versions.
            # Fixes spyder-ide/spyder#17097
            try:
                project_type_id = config[WORKSPACE].get(
                    "project_type", EmptyProject.ID)
            except Exception:
                pass

        EmptyProject._PARENT_PLUGIN = self.get_plugin()
        project_types = self.get_project_types()
        project_type_class = project_types.get(project_type_id, EmptyProject)
        return project_type_class

    def _add_to_recent(self, project):
        """
        Add an entry to recent projetcs

        We only maintain the list of the 10 most recent projects
        """
        if project not in self.recent_projects:
            self.recent_projects.insert(0, project)

        if len(self.recent_projects) > self.get_conf('max_recent_projects'):
            self.recent_projects.pop(-1)

    def _setup_menu_actions(self):
        """Setup and update the menu actions."""
        self.recent_project_menu.clear_actions()

        if self.recent_projects:
            for project in self.recent_projects:
                if self.is_valid_project(project):
                    if os.name == 'nt':
                        name = project
                    else:
                        name = project.replace(get_home_dir(), '~')

                    try:
                        action = self.get_action(name)
                    except KeyError:
                        action = self.create_action(
                            name,
                            text=name,
                            icon=self.create_icon('project'),
                            triggered=self._build_opener(project),
                        )

                    self.add_item_to_menu(
                        action,
                        menu=self.recent_project_menu,
                        section=RecentProjectsMenuSections.Recent)

        for item in [
                self.clear_recent_projects_action,
                self.max_recent_action]:
            self.add_item_to_menu(
                item,
                menu=self.recent_project_menu,
                section=RecentProjectsMenuSections.Extras)

        self._update_project_actions()
        self.recent_project_menu._render()

    def _build_opener(self, project):
        """Build function opening passed project"""
        def opener(*args, **kwargs):
            self.open_project(path=project)
        return opener

    def _update_project_actions(self):
        """Update actions of the Projects menu"""
        if self.recent_projects:
            self.clear_recent_projects_action.setEnabled(True)
        else:
            self.clear_recent_projects_action.setEnabled(False)

        active = bool(self.get_active_project_path())
        self.close_project_action.setEnabled(active)
        self.delete_project_action.setEnabled(active)

    def _load_config(self):
        """Load configuration: opened projects & tree widget state"""
        expanded_state = self.get_conf('expanded_state', None)

        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if isinstance(expanded_state, str):
            expanded_state = None
        if expanded_state is not None:
            self.treewidget.set_expanded_state(expanded_state)

    def _update_explorer(self, _unused):
        """Update explorer tree"""
        self._setup_project(self.get_active_project_path())

    def _get_valid_recent_projects(self, recent_projects):
        """
        Get the list of valid recent projects.

        Parameters
        ----------
        recent_projects: list
            List of recent projects as filesystem paths.
        """
        valid_projects = [
            p for p in recent_projects if self.is_valid_project(p)
        ]

        return valid_projects


# =============================================================================
# Tests
# =============================================================================
class ProjectExplorerTest(QWidget):
    def __init__(self, directory=None):
        QWidget.__init__(self)
        self.CONF_SECTION = 'project_explorer'
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(None, self, self)
        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))
        self.explorer._setup_project(self.directory)
        vlayout.addWidget(self.explorer)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file_requested.connect(self.label1.setText)

        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = ProjectExplorerTest()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
