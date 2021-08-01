# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Plugin

It handles closing, opening and switching among projetcs and also
updating the file tree explorer associated with a project
"""

# Standard library imports
import configparser
import os
import os.path as osp
import shutil
import functools
from collections import OrderedDict

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QInputDialog, QMessageBox

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.config.base import (get_home_dir, get_project_config_folder,
                                running_under_pytest)
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.plugins.mainmenu.api import ApplicationMenus, ProjectsMenuSections
from spyder.plugins.projects.api import (BaseProjectType, EmptyProject,
                                         WORKSPACE)
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher
from spyder.plugins.projects.widgets.main_widget import ProjectExplorerWidget
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.plugins.completion.api import (
    CompletionRequestTypes, FileChangeType, WorkspaceUpdateKind)
from spyder.plugins.completion.decorators import (
    request, handles, class_register)

# Localization
_ = get_translation("spyder")


class ProjectsMenuSubmenus:
    RecentProjects = 'recent_projects'


class ProjectsActions:
    NewProject = 'new_project_action'
    OpenProject = 'open_project_action'
    CloseProject = 'close_project_action'
    DeleteProject = 'delete_project_action'
    ClearRecentProjects = 'clear_recent_projects_action'
    MaxRecent = 'max_recent_action'


class RecentProjectsMenuSections:
    Recent = 'recent_section'
    Extras = 'extras_section'


@class_register
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
    sig_project_created = Signal(str, str, object)
    """
    This signal is emitted to request the Projects plugin the creation of a
    project.

    Parameters
    ----------
    project_path: str
        Location of project.
    project_type: str
        Type of project as defined by project types.
    project_packages: object
        Package to install. Currently not in use.
    """

    sig_project_loaded = Signal(object)
    """
    This signal is emitted when a project is loaded.

    Parameters
    ----------
    project_path: object
        Loaded project path.
    """

    sig_project_closed = Signal((object,), (bool,))
    """
    This signal is emitted when a project is closed.

    Parameters
    ----------
    project_path: object
        Closed project path (signature 1).
    close_project: bool
        This is emitted only when closing a project but not when switching
        between projects (signature 2).
    """

    sig_pythonpath_changed = Signal()
    """
    This signal is emitted when the Python path has changed.
    """

    def __init__(self, parent=None, configuration=None):
        """Initialization."""
        super().__init__(parent, configuration)
        self.recent_projects = self.get_conf('recent_projects', [])
        self.current_active_project = None
        self.latest_project = None
        self.watcher = WorkspaceWatcher(self)
        self.completions_available = False
        self.get_widget().setup_project(self.get_active_project_path())
        self.watcher.connect_signals(self)
        self._project_types = OrderedDict()

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Project")

    def get_description(self):
        return _("Create Spyder projects and manage their files.")

    def get_icon(self):
        return self.create_icon('project')

    def on_initialize(self):
        """Register plugin in Spyder's main window"""
        widget = self.get_widget()
        treewidget = widget.treewidget

        self.ipyconsole = None
        self.editor = None
        self.completions = None

        treewidget.sig_delete_project.connect(self.delete_project)
        treewidget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        self.sig_switch_to_plugin_requested.connect(
            lambda plugin, check: self.show_explorer())
        self.sig_project_loaded.connect(self.update_explorer)

        if self.main:
            widget.sig_open_file_requested.connect(self.main.open_file)
            self.main.project_path = self.get_pythonpath(at_start=True)
            self.sig_project_loaded.connect(
                lambda v: self.main.set_window_title())
            self.sig_project_closed.connect(
                lambda v: self.main.set_window_title())
            self.main.restore_scrollbar_position.connect(
                self.restore_scrollbar_position)
            self.sig_pythonpath_changed.connect(self.main.pythonpath_changed)

        self.register_project_type(self, EmptyProject)
        self.setup()

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        self.editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()
        treewidget = widget.treewidget

        treewidget.sig_open_file_requested.connect(self.editor.load)
        treewidget.sig_removed.connect(self.editor.removed)
        treewidget.sig_tree_removed.connect(self.editor.removed_tree)
        treewidget.sig_renamed.connect(self.editor.renamed)
        treewidget.sig_tree_renamed.connect(self.editor.renamed_tree)
        treewidget.sig_module_created.connect(self.editor.new)
        treewidget.sig_file_created.connect(
            lambda t: self.editor.new(text=t))

        self.sig_project_loaded.connect(
            lambda v: self.editor.setup_open_files())
        self.sig_project_closed[bool].connect(
            lambda v: self.editor.setup_open_files())
        self.editor.set_projects(self)
        self.sig_project_loaded.connect(
            lambda v: self.editor.set_current_project_path(v))
        self.sig_project_closed.connect(
            lambda v: self.editor.set_current_project_path())

    @on_plugin_available(plugin=Plugins.Completions)
    def on_completions_available(self):
        self.completions = self.get_plugin(Plugins.Completions)

        # TODO: This is not necessary anymore due to us starting workspace
        # services in the editor. However, we could restore it in the future.
        # completions.sig_language_completions_available.connect(
        #     lambda settings, language:
        #         self.start_workspace_services())
        self.completions.sig_stop_completions.connect(
            self.stop_workspace_services)
        self.sig_project_loaded.connect(
            functools.partial(self.completions.project_path_update,
                              update_kind=WorkspaceUpdateKind.ADDITION,
                              instance=self))
        self.sig_project_closed.connect(
            functools.partial(self.completions.project_path_update,
                              update_kind=WorkspaceUpdateKind.DELETION,
                              instance=self))

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        self.ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        widget = self.get_widget()
        treewidget = widget.treewidget

        treewidget.sig_open_interpreter_requested.connect(
            self.ipyconsole.create_client_from_path)
        treewidget.sig_run_requested.connect(
            lambda fname:
            self.ipyconsole.run_script(
                fname, osp.dirname(fname), '', False, False, False, True,
                False)
        )

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        new_project_action = self.get_action(ProjectsActions.NewProject)
        open_project_action = self.get_action(ProjectsActions.OpenProject)

        projects_menu = main_menu.get_application_menu(
            ApplicationMenus.Projects)
        projects_menu.aboutToShow.connect(self.is_invalid_active_project)

        main_menu.add_item_to_application_menu(
            new_project_action,
            menu=projects_menu,
            section=ProjectsMenuSections.New)

        for item in [open_project_action, self.close_project_action,
                     self.delete_project_action]:
            main_menu.add_item_to_application_menu(
                item,
                menu=projects_menu,
                section=ProjectsMenuSections.Open)

        main_menu.add_item_to_application_menu(
            self.recent_project_menu,
            menu=projects_menu,
            section=ProjectsMenuSections.Extras)

    def setup(self):
        """Setup the plugin actions."""
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

        self.recent_project_menu = self.get_widget().create_menu(
            ProjectsMenuSubmenus.RecentProjects,
            _("Recent Projects")
        )
        self.recent_project_menu.aboutToShow.connect(self.setup_menu_actions)
        self.setup_menu_actions()

    def setup_menu_actions(self):
        """Setup and update the menu actions."""
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
                            icon=ima.icon('project'),
                            triggered=self.build_opener(project),
                        )
                    self.get_widget().add_item_to_menu(
                        action,
                        menu=self.recent_project_menu,
                        section=RecentProjectsMenuSections.Recent)

        for item in [self.clear_recent_projects_action,
                     self.max_recent_action]:
            self.get_widget().add_item_to_menu(
                item,
                menu=self.recent_project_menu,
                section=RecentProjectsMenuSections.Extras)
        self.update_project_actions()

    def update_project_actions(self):
        """Update actions of the Projects menu"""
        if self.recent_projects:
            self.clear_recent_projects_action.setEnabled(True)
        else:
            self.clear_recent_projects_action.setEnabled(False)

        active = bool(self.get_active_project_path())
        self.close_project_action.setEnabled(active)
        self.delete_project_action.setEnabled(active)

    def on_close(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        return True

    def unmaximize(self):
        """Unmaximize the currently maximized plugin, if not self."""
        if self.main:
            if (self.main.last_plugin is not None and
                    self.main.last_plugin._ismaximized and
                    self.main.last_plugin is not self):
                self.main.maximize_dockwidget()

    def build_opener(self, project):
        """Build function opening passed project"""
        def opener(*args, **kwargs):
            self.open_project(path=project)
        return opener

    # ------ Public API -------------------------------------------------------
    @Slot()
    def create_new_project(self):
        """Create new project."""
        self.unmaximize()
        dlg = ProjectDialog(self.get_widget(),
                            project_types=self.get_project_types())
        result = dlg.exec_()
        data = dlg.project_data
        root_path = data.get("root_path", None)
        project_type = data.get("project_type", EmptyProject.ID)

        if result:
            self._create_project(root_path, project_type_id=project_type)
            dlg.close()

    def _create_project(self, root_path, project_type_id=EmptyProject.ID,
                        packages=None):
        """Create a new project."""
        project_types = self.get_project_types()
        if project_type_id in project_types:
            project_type_class = project_types[project_type_id]
            project = project_type_class(
                root_path=root_path,
                parent_plugin=project_type_class._PARENT_PLUGIN,
            )

            created_succesfully, message = project.create_project()
            if not created_succesfully:
                QMessageBox.warning(
                    self.get_widget(), "Project creation", message)
                shutil.rmtree(root_path, ignore_errors=True)
                return

            # TODO: In a subsequent PR return a value and emit based on that
            self.sig_project_created.emit(root_path, project_type_id, packages)
            self.open_project(path=root_path, project=project)
        else:
            if not running_under_pytest():
                QMessageBox.critical(
                    self.get_widget(),
                    _('Error'),
                    _("<b>{}</b> is not a registered Spyder project "
                      "type!").format(project_type_id)
                )

    def open_project(self, path=None, project=None, restart_consoles=True,
                     save_previous_files=True, workdir=None):
        """Open the project located in `path`."""
        self.unmaximize()
        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(parent=self.get_widget(),
                                        caption=_("Open project"),
                                        basedir=basedir)
            path = encoding.to_unicode_from_fs(path)
            if not self.is_valid_project(path):
                if path:
                    QMessageBox.critical(
                        self.get_widget(),
                        _('Error'),
                        _("<b>%s</b> is not a Spyder project!") % path,
                    )
                return
        else:
            path = encoding.to_unicode_from_fs(path)
        if project is None:
            project_type_class = self._load_project_type_class(path)
            project = project_type_class(
                root_path=path,
                parent_plugin=project_type_class._PARENT_PLUGIN,
            )

        # A project was not open before
        if self.current_active_project is None:
            if save_previous_files and self.editor is not None:
                self.editor.save_open_files()

            if self.editor is not None:
                self.set_conf('last_working_dir', getcwd_or_home(),
                              section='editor')

            if self.get_conf('visible_if_project_open'):
                self.show_explorer()
        else:
            # We are switching projects
            if self.editor is not None:
                self.set_project_filenames(self.editor.get_open_filenames())

            # TODO: Don't emit sig_project_closed when we support
            # multiple workspaces.
            self.sig_project_closed.emit(
                self.current_active_project.root_path)
            self.watcher.stop()

        self.current_active_project = project
        self.latest_project = project
        self.add_to_recent(path)

        self.set_conf('current_project_path', self.get_active_project_path())

        self.setup_menu_actions()
        if workdir and osp.isdir(workdir):
            self.sig_project_loaded.emit(workdir)
        else:
            self.sig_project_loaded.emit(path)
        self.sig_pythonpath_changed.emit()
        self.watcher.start(path)

        if restart_consoles:
            self.restart_consoles()

        open_successfully, message = project.open_project()
        if not open_successfully:
            QMessageBox.warning(self.get_widget(), "Project open", message)

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self.current_active_project:
            self.unmaximize()
            if self.editor is not None:
                self.set_project_filenames(
                    self.editor.get_open_filenames())
            path = self.current_active_project.root_path
            closed_sucessfully, message = (
                self.current_active_project.close_project())
            if not closed_sucessfully:
                QMessageBox.warning(
                    self.get_widget(), "Project close", message)

            self.current_active_project = None
            self.set_conf('current_project_path', None)
            self.setup_menu_actions()

            self.sig_project_closed.emit(path)
            self.sig_project_closed[bool].emit(True)
            self.sig_pythonpath_changed.emit()

            # Hide pane.
            self.set_conf('visible_if_project_open',
                          self.get_widget().isVisible())
            self.toggle_view(False)

            self.get_widget().clear()
            self.restart_consoles()
            self.watcher.stop()

    def delete_project(self):
        """
        Delete the current project without deleting the files in the directory.
        """
        if self.current_active_project:
            self.unmaximize()
            path = self.current_active_project.root_path
            buttons = QMessageBox.Yes | QMessageBox.No
            answer = QMessageBox.warning(
                self.get_widget(),
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
                        self.get_widget(),
                        _("Project Explorer"),
                        _("<b>Unable to delete <i>{varpath}</i></b>"
                          "<br><br>The error message was:<br>{error}"
                          ).format(varpath=path, error=to_text_string(error)))

    def clear_recent_projects(self):
        """Clear the list of recent projects"""
        self.recent_projects = []
        self.set_conf('recent_projects', self.recent_projects)
        self.setup_menu_actions()

    def change_max_recent_projects(self):
        """Change max recent projects entries."""

        mrf, valid = QInputDialog.getInt(
            self.get_widget(),
            _('Projects'),
            _('Maximum number of recent projects'),
            self.get_conf('max_recent_projects'),
            1,
            35)

        if valid:
            self.set_conf('max_recent_projects', mrf)

    def get_active_project(self):
        """Get the active project"""
        return self.current_active_project

    def reopen_last_project(self):
        """
        Reopen the active project when Spyder was closed last time, if any
        """
        current_project_path = self.get_conf('current_project_path',
                                             default=None)

        # Needs a safer test of project existence!
        if (current_project_path and
                self.is_valid_project(current_project_path)):
            self.open_project(path=current_project_path,
                              restart_consoles=False,
                              save_previous_files=False)
            self.load_config()

    def get_project_filenames(self):
        """Get the list of recent filenames of a project"""
        recent_files = []
        if self.current_active_project:
            recent_files = self.current_active_project.get_recent_files()
        elif self.latest_project:
            recent_files = self.latest_project.get_recent_files()
        return recent_files

    def set_project_filenames(self, recent_files):
        """Set the list of open file names in a project"""
        if (self.current_active_project
                and self.is_valid_project(
                        self.current_active_project.root_path)):
            self.current_active_project.set_recent_files(recent_files)

    def get_active_project_path(self):
        """Get path of the active project"""
        active_project_path = None
        if self.current_active_project:
            active_project_path = self.current_active_project.root_path
        return active_project_path

    def get_pythonpath(self, at_start=False):
        """Get project path as a list to be added to PYTHONPATH"""
        if at_start:
            current_path = self.get_conf('current_project_path',
                                         default=None)
        else:
            current_path = self.get_active_project_path()
        if current_path is None:
            return []
        else:
            return [current_path]

    def get_last_working_dir(self):
        """Get the path of the last working directory"""
        return self.get_conf(
            'last_working_dir', section='editor', default=getcwd_or_home())

    def save_config(self):
        """
        Save configuration: opened projects & tree widget state.

        Also save whether dock widget is visible if a project is open.
        """
        self.set_conf('recent_projects', self.recent_projects)
        self.set_conf('expanded_state',
                      self.get_widget().treewidget.get_expanded_state())
        self.set_conf('scrollbar_position',
                      self.get_widget().treewidget.get_scrollbar_position())
        if self.current_active_project:
            self.set_conf('visible_if_project_open',
                          self.get_widget().isVisible())

    def load_config(self):
        """Load configuration: opened projects & tree widget state"""
        expanded_state = self.get_conf('expanded_state', None)
        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if is_text_string(expanded_state):
            expanded_state = None
        if expanded_state is not None:
            self.get_widget().treewidget.set_expanded_state(expanded_state)

    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_conf('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.get_widget().treewidget.set_scrollbar_position(scrollbar_pos)

    def update_explorer(self):
        """Update explorer tree"""
        self.get_widget().setup_project(self.get_active_project_path())

    def show_explorer(self):
        """Show the explorer"""
        if self.get_widget() is not None:
            self.toggle_view(True)
            self.get_widget().setVisible(True)
            self.get_widget().raise_()
            self.get_widget().update()

    def restart_consoles(self):
        """Restart consoles when closing, opening and switching projects"""
        if self.ipyconsole is not None:
            self.ipyconsole.restart()

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
                        self.get_widget(),
                        _('Error'),
                        _("<b>{}</b> is no longer a valid Spyder project! "
                          "Since it is the current active project, it will "
                          "be closed automatically.").format(path)
                    )
                self.close_project()

    def add_to_recent(self, project):
        """
        Add an entry to recent projetcs

        We only maintain the list of the 10 most recent projects
        """
        if project not in self.recent_projects:
            self.recent_projects.insert(0, project)
        if len(self.recent_projects) > self.get_conf('max_recent_projects'):
            self.recent_projects.pop(-1)

    def start_workspace_services(self):
        """Enable LSP workspace functionality."""
        self.completions_available = True
        if self.current_active_project:
            path = self.get_active_project_path()
            self.notify_project_open(path)

    def stop_workspace_services(self, _language):
        """Disable LSP workspace functionality."""
        self.completions_available = False

    def emit_request(self, method, params, requires_response):
        """Send request/notification/response to all LSP servers."""
        params['requires_response'] = requires_response
        params['response_instance'] = self
        if self.completions:
            self.completions.broadcast_notification(method, params)

    @Slot(str, dict)
    def handle_response(self, method, params):
        """Method dispatcher for LSP requests."""
        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)

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

    # --- New API:
    # ------------------------------------------------------------------------
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
            config.read(fpath)
            project_type_id = config[WORKSPACE].get(
                "project_type", EmptyProject.ID)

        EmptyProject._PARENT_PLUGIN = self
        project_types = self.get_project_types()
        project_type_class = project_types.get(project_type_id, EmptyProject)
        return project_type_class

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
            Project types dictionary. Keys are project type IDs and values
            are project type classes.
        """
        return self._project_types
