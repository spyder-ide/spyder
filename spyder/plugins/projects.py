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

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMenu, QMessageBox, QVBoxLayout

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_action, MENU_SEPARATOR
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.projects.explorer import ProjectExplorerWidget
from spyder.widgets.projects.projectdialog import ProjectDialog
from spyder.widgets.projects import EmptyProject


class Projects(SpyderPluginWidget):
    """Projects plugin."""

    CONF_SECTION = 'project_explorer'
    pythonpath_changed = Signal()
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
                            options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.explorer)
        self.setLayout(layout)

        self.recent_projects = self.get_option('recent_projects', default=[])
        self.current_active_project = None
        self.latest_project = None

        self.editor = None
        self.workingdirectory = None

        # Initialize plugin
        self.initialize_plugin()
        self.explorer.setup_project(self.get_active_project_path())

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Project explorer")

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
                                    triggered=self.explorer.delete_project)
        self.clear_recent_projects_action =\
            create_action(self, _("Clear this list"),
                          triggered=self.clear_recent_projects)
        self.edit_project_preferences_action =\
            create_action(self, _("Project Preferences"),
                          triggered=self.edit_project_preferences)
        self.recent_project_menu = QMenu(_("Recent Projects"), self)

        self.main.projects_menu_actions += [self.new_project_action,
                                            MENU_SEPARATOR,
                                            self.open_project_action,
                                            self.close_project_action,
                                            self.delete_project_action,
                                            MENU_SEPARATOR,
                                            self.recent_project_menu,
                                            self.toggle_view_action]

        self.setup_menu_actions()
        return []

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.editor = self.main.editor
        self.workingdirectory = self.main.workingdirectory
        ipyconsole = self.main.ipyconsole
        treewidget = self.explorer.treewidget

        self.main.add_dockwidget(self)
        self.explorer.sig_open_file.connect(self.main.open_file)

        treewidget.sig_edit.connect(self.editor.load)
        treewidget.sig_removed.connect(self.editor.removed)
        treewidget.sig_removed_tree.connect(self.editor.removed_tree)
        treewidget.sig_renamed.connect(self.editor.renamed)
        treewidget.sig_create_module.connect(self.editor.new)
        treewidget.sig_new_file.connect(
            lambda t: self.main.editor.new(text=t))
        treewidget.sig_open_interpreter.connect(
            ipyconsole.create_client_from_path)
        treewidget.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        treewidget.sig_run.connect(
            lambda fname:
            ipyconsole.run_script(fname, osp.dirname(fname), '', False, False,
                                  False, True))

        # New project connections. Order matters!
        self.sig_project_loaded.connect(
            lambda v: self.workingdirectory.chdir(v))
        self.sig_project_loaded.connect(
            lambda v: self.main.update_window_title())
        self.sig_project_loaded.connect(
            lambda v: self.editor.setup_open_files())
        self.sig_project_loaded.connect(self.update_explorer)
        self.sig_project_closed[object].connect(
            lambda v: self.workingdirectory.chdir(self.get_last_working_dir()))
        self.sig_project_closed.connect(
            lambda v: self.main.update_window_title())
        self.sig_project_closed.connect(
            lambda v: self.editor.setup_open_files())
        self.recent_project_menu.aboutToShow.connect(self.setup_menu_actions)

        self.main.pythonpath_changed()
        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.pythonpath_changed.connect(self.main.pythonpath_changed)
        self.editor.set_projects(self)

    def refresh_plugin(self):
        """Refresh project explorer widget"""
        pass

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        self.explorer.closing_widget()
        return True

    #------ Public API ---------------------------------------------------------
    def setup_menu_actions(self):
        """Setup and update the menu actions."""
        self.recent_project_menu.clear()
        self.recent_projects_actions = []
        if self.recent_projects:
            for project in self.recent_projects:
                if self.is_valid_project(project):
                    name = project.replace(get_home_dir(), '~')
                    action = create_action(self,
                        name,
                        icon = ima.icon('project'),
                        triggered=lambda v, path=project: self.open_project(path=path))
                    self.recent_projects_actions.append(action)
                else:
                    self.recent_projects.remove(project)
            self.recent_projects_actions += [None,
                                             self.clear_recent_projects_action]
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
        self.edit_project_preferences_action.setEnabled(active)

    def edit_project_preferences(self):
        """Edit Spyder active project preferences"""
        from spyder.widgets.projects.configdialog import ProjectPreferences
        if self.project_active:
            active_project = self.project_list[0]
            dlg = ProjectPreferences(self, active_project)
#            dlg.size_change.connect(self.set_project_prefs_size)
#            if self.projects_prefs_dialog_size is not None:
#                dlg.resize(self.projects_prefs_dialog_size)
            dlg.show()
#        dlg.check_all_settings()
#        dlg.pages_widget.currentChanged.connect(self.__preference_page_changed)
            dlg.exec_()

    @Slot()
    def create_new_project(self):
        """Create new project"""
        active_project = self.current_active_project
        dlg = ProjectDialog(self)
        dlg.sig_project_creation_requested.connect(self._create_project)
        dlg.sig_project_creation_requested.connect(self.sig_project_created)
        if dlg.exec_():
            pass
            if active_project is None:
                self.show_explorer()
            self.pythonpath_changed.emit()
            self.restart_consoles()

    def _create_project(self, path):
        """Create a new project."""
        self.open_project(path=path)
        self.setup_menu_actions()
        self.add_to_recent(path)

    def open_project(self, path=None, restart_consoles=True,
                     save_previous_files=True):
        """Open the project located in `path`"""
        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(parent=self,
                                        caption=_("Open project"),
                                        basedir=basedir)
            if not self.is_valid_project(path):
                if path:
                    QMessageBox.critical(self, _('Error'),
                                _("<b>%s</b> is not a Spyder project!") % path)
                return
            else:
                self.add_to_recent(path)

        # A project was not open before
        if self.current_active_project is None:
            if save_previous_files:
                self.editor.save_open_files()
            self.editor.set_option('last_working_dir', getcwd_or_home())
            self.show_explorer()
        else: # we are switching projects
            self.set_project_filenames(self.editor.get_open_filenames())

        self.current_active_project = EmptyProject(path)
        self.latest_project = EmptyProject(path)
        self.set_option('current_project_path', self.get_active_project_path())
        self.setup_menu_actions()
        self.sig_project_loaded.emit(path)
        self.pythonpath_changed.emit()
        if restart_consoles:
            self.restart_consoles()

    def close_project(self):
        """
        Close current project and return to a window without an active
        project
        """
        if self.current_active_project:
            path = self.current_active_project.root_path
            self.set_project_filenames(self.editor.get_open_filenames())
            self.current_active_project = None
            self.set_option('current_project_path', None)
            self.setup_menu_actions()
            self.sig_project_closed.emit(path)
            self.pythonpath_changed.emit()
            self.dockwidget.close()
            self.explorer.clear()
            self.restart_consoles()

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
        if self.current_active_project:
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
        return self.editor.get_option('last_working_dir',
                                      default=getcwd_or_home())

    def save_config(self):
        """Save configuration: opened projects & tree widget state"""
        self.set_option('recent_projects', self.recent_projects)
        self.set_option('expanded_state',
                        self.explorer.treewidget.get_expanded_state())
        self.set_option('scrollbar_position',
                        self.explorer.treewidget.get_scrollbar_position())

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
        if self.dockwidget.isHidden():
            self.dockwidget.show()
        self.dockwidget.raise_()
        self.dockwidget.update()

    def restart_consoles(self):
        """Restart consoles when closing, opening and switching projects"""
        self.main.ipyconsole.restart()

    def is_valid_project(self, path):
        """Check if a directory is a valid Spyder project"""
        spy_project_dir = osp.join(path, '.spyproject')
        if osp.isdir(path) and osp.isdir(spy_project_dir):
            return True
        else:
            return False

    def add_to_recent(self, project):
        """
        Add an entry to recent projetcs

        We only maintain the list of the 10 most recent projects
        """
        if project not in self.recent_projects:
            self.recent_projects.insert(0, project)
            self.recent_projects = self.recent_projects[:10]
