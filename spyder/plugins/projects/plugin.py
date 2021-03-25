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
import os.path as osp
import shutil
import functools
from collections import OrderedDict

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QInputDialog, QMenu, QMessageBox, QVBoxLayout

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.api.plugins import Plugins, SpyderPluginWidget
from spyder.config.base import (get_home_dir, get_project_config_folder,
                                running_under_pytest)
from spyder.config.manager import CONF
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import add_actions, create_action, MENU_SEPARATOR
from spyder.utils.misc import getcwd_or_home
from spyder.plugins.projects.api import (BaseProjectType, EmptyProject,
                                         WORKSPACE)
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher
from spyder.plugins.projects.widgets.explorer import ProjectExplorerWidget
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.plugins.completion.api import (
    CompletionRequestTypes, FileChangeType, WorkspaceUpdateKind)
from spyder.plugins.completion.decorators import (
    request, handles, class_register)


# Localization
_ = get_translation("spyder")


@class_register
class Projects(SpyderPluginWidget):
    """Projects plugin."""

    CONF_SECTION = 'project_explorer'
    CONF_FILE = False

    # This is required for the new API
    NAME = 'project_explorer'
    REQUIRES = []
    OPTIONAL = [Plugins.Completions, Plugins.IPythonConsole, Plugins.Explorer]

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
    sig_project_closed = Signal(object)
    sig_pythonpath_changed = Signal()

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.explorer = ProjectExplorerWidget(
            self,
            name_filters=self.get_option('name_filters'),
            show_hscrollbar=self.get_option('show_hscrollbar'),
            options_button=self.options_button,
            single_click_to_open=CONF.get('explorer', 'single_click_to_open'),
        )

        layout = QVBoxLayout()
        layout.addWidget(self.explorer)
        self.setLayout(layout)

        self.recent_projects = self.get_option('recent_projects', default=[])
        self.current_active_project = None
        self.latest_project = None
        self.watcher = WorkspaceWatcher(self)
        self.completions_available = False
        self.explorer.setup_project(self.get_active_project_path())
        self.watcher.connect_signals(self)
        self._project_types = OrderedDict()

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Project")

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.explorer.treewidget

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        self.new_project_action = create_action(self,
                                    _("New Project..."),
                                    triggered=self.create_new_project)
        self.open_project_action = create_action(self,
                                    _("Open Project..."),
                                    triggered=lambda v: self.open_project())
        self.close_project_action = create_action(self,
                                    _("Close Project"),
                                    triggered=self.close_project)
        self.delete_project_action = create_action(self,
                                    _("Delete Project"),
                                    triggered=self.delete_project)
        self.clear_recent_projects_action = create_action(
            self,
            _("Clear this list"),
            triggered=self.clear_recent_projects)
        self.recent_project_menu = QMenu(_("Recent Projects"), self)

        self.max_recent_action = create_action(
            self,
            _("Maximum number of recent projects..."),
            triggered=self.change_max_recent_projects)

        if self.main is not None:
            self.main.projects_menu_actions += [self.new_project_action,
                                                MENU_SEPARATOR,
                                                self.open_project_action,
                                                self.close_project_action,
                                                self.delete_project_action,
                                                MENU_SEPARATOR,
                                                self.recent_project_menu,
                                                self._toggle_view_action]

        self.setup_menu_actions()
        return []

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        ipyconsole = self.main.ipyconsole
        treewidget = self.explorer.treewidget
        lspmgr = self.main.completions

        self.add_dockwidget()
        self.explorer.sig_open_file_requested.connect(self.main.open_file)

        treewidget.sig_delete_project.connect(self.delete_project)
        treewidget.sig_open_file_requested.connect(self.main.editor.load)
        treewidget.sig_removed.connect(self.main.editor.removed)
        treewidget.sig_tree_removed.connect(self.main.editor.removed_tree)
        treewidget.sig_renamed.connect(self.main.editor.renamed)
        treewidget.sig_tree_renamed.connect(self.main.editor.renamed_tree)
        treewidget.sig_module_created.connect(self.main.editor.new)
        treewidget.sig_file_created.connect(
            lambda t: self.main.editor.new(text=t))
        treewidget.sig_open_interpreter_requested.connect(
            ipyconsole.create_client_from_path)
        treewidget.sig_redirect_stdio_requested.connect(
            self.main.redirect_internalshell_stdio)
        treewidget.sig_run_requested.connect(
            lambda fname:
            ipyconsole.run_script(fname, osp.dirname(fname), '', False, False,
                                  False, True, False))

        # TODO: This is not necessary anymore due to us starting workspace
        # services in the editor. However, we could restore it in the future.
        #lspmgr.sig_language_completions_available.connect(
        #    lambda settings, language:
        #        self.start_workspace_services())
        lspmgr.sig_stop_completions.connect(self.stop_workspace_services)

        # New project connections. Order matters!
        self.sig_project_loaded.connect(
            lambda path:
            self.main.workingdirectory.chdir(
                directory=path,
                sender_plugin=self
            )
        )
        self.sig_project_loaded.connect(
            lambda v: self.main.set_window_title())
        self.sig_project_loaded.connect(
            functools.partial(lspmgr.project_path_update,
                              update_kind=WorkspaceUpdateKind.ADDITION,
                              instance=self))
        self.sig_project_loaded.connect(
            lambda v: self.main.editor.setup_open_files())
        self.sig_project_loaded.connect(self.update_explorer)
        self.sig_project_loaded.connect(
            lambda v: self.main.outlineexplorer.update_all_editors())
        self.sig_project_closed[object].connect(
            lambda path:
            self.main.workingdirectory.chdir(
                directory=self.get_last_working_dir(),
                sender_plugin=self
            )
        )
        self.sig_project_closed.connect(
            lambda v: self.main.set_window_title())
        self.sig_project_closed.connect(
            functools.partial(lspmgr.project_path_update,
                              update_kind=WorkspaceUpdateKind.DELETION,
                              instance=self))
        self.sig_project_closed.connect(
            lambda v: self.main.editor.setup_open_files())
        self.sig_project_closed.connect(
            lambda v: self.main.outlineexplorer.update_all_editors())
        self.recent_project_menu.aboutToShow.connect(self.setup_menu_actions)

        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.sig_pythonpath_changed.connect(self.main.pythonpath_changed)
        self.main.editor.set_projects(self)

        self.sig_project_loaded.connect(
            lambda v: self.main.editor.set_current_project_path(v))
        self.sig_project_closed.connect(
            lambda v: self.main.editor.set_current_project_path())

        # Connect to file explorer to keep single click to open files in sync
        # TODO: Remove this once projects is migrated
        CONF.observe_configuration(self, 'explorer', 'single_click_to_open')
        self.register_project_type(self, EmptyProject)

    def on_configuration_change(self, option, section, value):
        """Set single click to open files and directories."""
        if option == 'single_click_to_open':
            self.explorer.treewidget.set_single_click_to_open(value)

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        self.explorer.closing_widget()
        return True

    def unmaximize(self):
        """Unmaximize the currently maximized plugin, if not self."""
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
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        # TODO: Uncomment for Spyder 5
        # self.tabify(self.main.explorer)

    def setup_menu_actions(self):
        """Setup and update the menu actions."""
        self.recent_project_menu.clear()
        self.recent_projects_actions = []
        if self.recent_projects:
            for project in self.recent_projects:
                if self.is_valid_project(project):
                    name = project.replace(get_home_dir(), '~')
                    action = create_action(
                        self,
                        name,
                        icon=ima.icon('project'),
                        triggered=self.build_opener(project),
                    )
                    self.recent_projects_actions.append(action)
                else:
                    self.recent_projects.remove(project)
            self.recent_projects_actions += [
                None,
                self.clear_recent_projects_action,
                self.max_recent_action
            ]
        else:
            self.recent_projects_actions = [self.clear_recent_projects_action,
                                            self.max_recent_action]
        add_actions(self.recent_project_menu, self.recent_projects_actions)
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

    @Slot()
    def create_new_project(self):
        """Create new project."""
        self.unmaximize()
        active_project = self.current_active_project
        dlg = ProjectDialog(self, project_types=self.get_project_types())
        result = dlg.exec_()
        data = dlg.project_data
        root_path = data.get("root_path", None)
        project_type = data.get("project_type", EmptyProject.ID)

        if result:
            # A project was not open before
            if active_project is None:
                if self.get_option('visible_if_project_open'):
                    self.show_explorer()
            else:
                # We are switching projects.
                # TODO: Don't emit sig_project_closed when we support
                # multiple workspaces.
                self.sig_project_closed.emit(active_project.root_path)

            self._create_project(root_path, project_type_id=project_type)
            self.sig_pythonpath_changed.emit()
            self.restart_consoles()
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
                QMessageBox.warning(self, "Project creation", message)
                shutil.rmtree(root_path, ignore_errors=True)
                return

            # TODO: In a subsequent PR return a value and emit based on that
            self.sig_project_created.emit(root_path, project_type_id, packages)
            self.open_project(path=root_path, project=project)
        else:
            if not running_under_pytest():
                QMessageBox.critical(
                    self,
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
            path = getexistingdirectory(parent=self,
                                        caption=_("Open project"),
                                        basedir=basedir)
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
            project_type_class = self._load_project_type_class(path)
            project = project_type_class(
                root_path=path,
                parent_plugin=project_type_class._PARENT_PLUGIN,
            )

        # A project was not open before
        if self.current_active_project is None:
            if save_previous_files and self.main.editor is not None:
                self.main.editor.save_open_files()

            if self.main.editor is not None:
                self.main.editor.set_option('last_working_dir',
                                            getcwd_or_home())

            if self.get_option('visible_if_project_open'):
                self.show_explorer()
        else:
            # We are switching projects
            if self.main.editor is not None:
                self.set_project_filenames(
                    self.main.editor.get_open_filenames())

            # TODO: Don't emit sig_project_closed when we support
            # multiple workspaces.
            self.sig_project_closed.emit(
                self.current_active_project.root_path)

        self.current_active_project = project
        self.latest_project = project
        self.add_to_recent(path)

        self.set_option('current_project_path', self.get_active_project_path())

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
            QMessageBox.warning(self, "Project open", message)

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self.current_active_project:
            self.unmaximize()
            if self.main.editor is not None:
                self.set_project_filenames(
                    self.main.editor.get_open_filenames())
            path = self.current_active_project.root_path
            closed_sucessfully, message = (
                self.current_active_project.close_project())
            if not closed_sucessfully:
                QMessageBox.warning(self, "Project close", message)

            self.current_active_project = None
            self.set_option('current_project_path', None)
            self.setup_menu_actions()

            self.sig_project_closed.emit(path)
            self.sig_pythonpath_changed.emit()

            if self.dockwidget is not None:
                self.set_option('visible_if_project_open',
                                self.dockwidget.isVisible())
                self.dockwidget.close()

            self.explorer.clear()
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
                          ).format(varpath=path, error=to_text_string(error)))

    def clear_recent_projects(self):
        """Clear the list of recent projects"""
        self.recent_projects = []
        self.setup_menu_actions()

    def change_max_recent_projects(self):
        """Change max recent projects entries."""

        mrf, valid = QInputDialog.getInt(
            self,
            _('Projects'),
            _('Maximum number of recent projects'),
            self.get_option('max_recent_projects'),
            1,
            35)

        if valid:
            self.set_option('max_recent_projects', mrf)

    def get_active_project(self):
        """Get the active project"""
        return self.current_active_project

    def reopen_last_project(self):
        """
        Reopen the active project when Spyder was closed last time, if any
        """
        current_project_path = self.get_option('current_project_path',
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
            current_path = self.get_option('current_project_path',
                                           default=None)
        else:
            current_path = self.get_active_project_path()
        if current_path is None:
            return []
        else:
            return [current_path]

    def get_last_working_dir(self):
        """Get the path of the last working directory"""
        return self.main.editor.get_option('last_working_dir',
                                           default=getcwd_or_home())

    def save_config(self):
        """
        Save configuration: opened projects & tree widget state.

        Also save whether dock widget is visible if a project is open.
        """
        self.set_option('recent_projects', self.recent_projects)
        self.set_option('expanded_state',
                        self.explorer.treewidget.get_expanded_state())
        self.set_option('scrollbar_position',
                        self.explorer.treewidget.get_scrollbar_position())
        if self.current_active_project and self.dockwidget:
            self.set_option('visible_if_project_open',
                            self.dockwidget.isVisible())

    def load_config(self):
        """Load configuration: opened projects & tree widget state"""
        expanded_state = self.get_option('expanded_state', None)
        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if is_text_string(expanded_state):
            expanded_state = None
        if expanded_state is not None:
            self.explorer.treewidget.set_expanded_state(expanded_state)

    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_option('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.explorer.treewidget.set_scrollbar_position(scrollbar_pos)

    def update_explorer(self):
        """Update explorer tree"""
        self.explorer.setup_project(self.get_active_project_path())

    def show_explorer(self):
        """Show the explorer"""
        if self.dockwidget is not None:
            if self.dockwidget.isHidden():
                self.dockwidget.show()
            self.dockwidget.raise_()
            self.dockwidget.update()

    def restart_consoles(self):
        """Restart consoles when closing, opening and switching projects"""
        if self.main.ipyconsole is not None:
            self.main.ipyconsole.restart()

    def is_valid_project(self, path):
        """Check if a directory is a valid Spyder project"""
        spy_project_dir = osp.join(path, '.spyproject')
        return osp.isdir(path) and osp.isdir(spy_project_dir)

    def add_to_recent(self, project):
        """
        Add an entry to recent projetcs

        We only maintain the list of the 10 most recent projects
        """
        if project not in self.recent_projects:
            self.recent_projects.insert(0, project)
        if len(self.recent_projects) > self.get_option('max_recent_projects'):
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
        self.main.completions.broadcast_notification(method, params)

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

    # TODO: To be removed after migration
    def get_plugin(self, plugin_name):
        """
        Return a plugin instance by providing the plugin's NAME.
        """
        PLUGINS = self.main._PLUGINS
        if plugin_name in PLUGINS:
            return PLUGINS[plugin_name]
