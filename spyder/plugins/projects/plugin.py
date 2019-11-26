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
import os.path as osp
import shutil
import functools

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMenu, QMessageBox, QVBoxLayout

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.config.manager import CONF
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_action, MENU_SEPARATOR
from spyder.utils.misc import getcwd_or_home
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher
from spyder.plugins.projects.widgets.explorer import ProjectExplorerWidget
from spyder.plugins.projects.widgets.projectdialog import ProjectDialog
from spyder.plugins.projects.projecttypes import EmptyProject
from spyder.plugins.completion.languageserver import (
    LSPRequestTypes, FileChangeType)
from spyder.plugins.completion.decorators import (
    request, handles, class_register)


@class_register
class Projects(SpyderPluginWidget):
    """Projects plugin."""

    CONF_SECTION = 'project_explorer'
    CONF_FILE = False
    sig_pythonpath_changed = Signal()
    sig_project_created = Signal(object, object, object)
    sig_project_loaded = Signal(object)
    sig_project_closed = Signal(object)

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.explorer = ProjectExplorerWidget(
            self,
            name_filters=self.get_option('name_filters'),
            show_all=self.get_option('show_all'),
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
        self.clear_recent_projects_action =\
            create_action(self, _("Clear this list"),
                          triggered=self.clear_recent_projects)
        self.recent_project_menu = QMenu(_("Recent Projects"), self)

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
        self.explorer.sig_open_file.connect(self.main.open_file)
        self.register_widget_shortcuts(treewidget)

        treewidget.sig_delete_project.connect(self.delete_project)
        treewidget.sig_edit.connect(self.main.editor.load)
        treewidget.sig_removed.connect(self.main.editor.removed)
        treewidget.sig_removed_tree.connect(self.main.editor.removed_tree)
        treewidget.sig_renamed.connect(self.main.editor.renamed)
        treewidget.sig_renamed_tree.connect(self.main.editor.renamed_tree)
        treewidget.sig_create_module.connect(self.main.editor.new)
        treewidget.sig_new_file.connect(
            lambda t: self.main.editor.new(text=t))
        treewidget.sig_open_interpreter.connect(
            ipyconsole.create_client_from_path)
        treewidget.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        treewidget.sig_run.connect(
            lambda fname:
            ipyconsole.run_script(fname, osp.dirname(fname), '', False, False,
                                  False, True, False))

        # New project connections. Order matters!
        self.sig_project_loaded.connect(
            lambda v: self.main.workingdirectory.chdir(v))
        self.sig_project_loaded.connect(
            lambda v: self.main.set_window_title())
        self.sig_project_loaded.connect(
            functools.partial(lspmgr.project_path_update,
                              update_kind='addition'))
        self.sig_project_loaded.connect(
            lambda v: self.main.editor.setup_open_files())
        self.sig_project_loaded.connect(self.update_explorer)
        self.sig_project_closed[object].connect(
            lambda v: self.main.workingdirectory.chdir(
                self.get_last_working_dir()))
        self.sig_project_closed.connect(
            lambda v: self.main.set_window_title())
        self.sig_project_closed.connect(
            functools.partial(lspmgr.project_path_update,
                              update_kind='deletion'))
        self.sig_project_closed.connect(
            lambda v: self.main.editor.setup_open_files())
        self.recent_project_menu.aboutToShow.connect(self.setup_menu_actions)

        self.main.pythonpath_changed()
        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.sig_pythonpath_changed.connect(self.main.pythonpath_changed)
        self.main.editor.set_projects(self)

        # Connect to file explorer to keep single click to open files in sync
        self.main.explorer.fileexplorer.sig_option_changed.connect(
            self.set_single_click_to_open
        )

    def set_single_click_to_open(self, option, value):
        """Set single click to open files and directories."""
        if option == 'single_click_to_open':
            self.explorer.treewidget.set_single_click_to_open(value)

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        self.explorer.closing_widget()
        return True

    def switch_to_plugin(self):
        """Switch to plugin."""
        # Unmaxizime currently maximized plugin
        if (self.main.last_plugin is not None and
                self.main.last_plugin._ismaximized and
                self.main.last_plugin is not self):
            self.main.maximize_dockwidget()

        # Show plugin only if it was already visible
        if self.get_option('visible_if_project_open'):
            if not self._toggle_view_action.isChecked():
                self._toggle_view_action.setChecked(True)
            self._visibility_changed(True)

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
            ]
        else:
            self.recent_projects_actions = [self.clear_recent_projects_action]
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
        """Create new project"""
        self.switch_to_plugin()
        active_project = self.current_active_project
        dlg = ProjectDialog(self)
        dlg.sig_project_creation_requested.connect(self._create_project)
        dlg.sig_project_creation_requested.connect(self.sig_project_created)
        if dlg.exec_():
            if (active_project is None
                    and self.get_option('visible_if_project_open')):
                self.show_explorer()
            self.sig_pythonpath_changed.emit()
            self.restart_consoles()

    def _create_project(self, path):
        """Create a new project."""
        self.open_project(path=path)

    def open_project(self, path=None, restart_consoles=True,
                     save_previous_files=True):
        """Open the project located in `path`"""
        self.notify_project_open(path)
        self.switch_to_plugin()
        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(parent=self,
                                        caption=_("Open project"),
                                        basedir=basedir)
            path = encoding.to_unicode_from_fs(path)
            if not self.is_valid_project(path):
                if path:
                    QMessageBox.critical(self, _('Error'),
                                _("<b>%s</b> is not a Spyder project!") % path)
                return
        else:
            path = encoding.to_unicode_from_fs(path)

        self.add_to_recent(path)

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

        project = EmptyProject(path)
        self.current_active_project = project
        self.latest_project = project
        self.set_option('current_project_path', self.get_active_project_path())

        self.setup_menu_actions()
        self.sig_project_loaded.emit(path)
        self.sig_pythonpath_changed.emit()
        self.watcher.start(path)

        if restart_consoles:
            self.restart_consoles()

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self.current_active_project:
            self.switch_to_plugin()
            if self.main.editor is not None:
                self.set_project_filenames(
                    self.main.editor.get_open_filenames())
            path = self.current_active_project.root_path
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
            self.notify_project_close(path)

    def delete_project(self):
        """
        Delete the current project without deleting the files in the directory.
        """
        if self.current_active_project:
            self.switch_to_plugin()
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
        if current_project_path and \
          self.is_valid_project(current_project_path):
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
            self.recent_projects = self.recent_projects[:10]

    def register_lsp_server_settings(self, settings):
        """Enable LSP workspace functions."""
        self.completions_available = True
        if self.current_active_project:
            path = self.get_active_project_path()
            self.notify_project_open(path)

    def stop_lsp_services(self):
        """Disable LSP workspace functions."""
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
    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
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

    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
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

    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
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

    @request(method=LSPRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE,
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

    @request(method=LSPRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_open(self, path):
        """Notify LSP server about project path availability."""
        params = {
            'folder': path,
            'instance': self,
            'kind': 'addition'
        }
        return params

    @request(method=LSPRequestTypes.WORKSPACE_FOLDERS_CHANGE,
             requires_response=False)
    def notify_project_close(self, path):
        """Notify LSP server to unregister project path."""
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
        """Apply edits to multiple files and notify server about success."""
        edits = params['params']
        response = {
            'applied': False,
            'error': 'Not implemented',
            'language': edits['language']
        }
        return response
