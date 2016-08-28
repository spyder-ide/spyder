# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer Plugin"""

# Standard library imports
import os

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.plugins import SpyderPluginMixin
from spyder.py3compat import is_text_string, getcwd
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_action, get_icon
from spyder.widgets.projects.explorer import ProjectExplorerWidget
from spyder.widgets.projects.projectdialog import ProjectDialog
from spyder.widgets.projects.type.python import PythonProject


class ProjectExplorer(ProjectExplorerWidget, SpyderPluginMixin):
    """Project explorer plugin"""
    CONF_SECTION = 'project_explorer'

    open_terminal = Signal(str)
    open_interpreter = Signal(str)
    pythonpath_changed = Signal()
    create_module = Signal(str)
    edit = Signal(str)
    removed = Signal(str)
    removed_tree = Signal(str)
    renamed = Signal(str, str)
    redirect_stdio = Signal(bool)

    # Path, project type, packages
    sig_project_created = Signal(object, object, object)
    sig_project_loaded = Signal(object)  # project folder path
    sig_project_closed = Signal(object)  # project folder path

    def __init__(self, parent=None):
        ProjectExplorerWidget.__init__(self, parent=parent,
                    name_filters=self.get_option('name_filters'),
                    show_all=self.get_option('show_all', False),
                    show_hscrollbar=self.get_option('show_hscrollbar'))
        SpyderPluginMixin.__init__(self, parent)

        self.recent_projects = self.get_option('recent_projects', default=[])
        self.current_active_project = None
        self.latest_project = None

        # Initialize plugin
        self.initialize_plugin()

        self.treewidget.header().hide()
        self.load_config()
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("Project")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        self.new_project_action = create_action(self,
                                    _("New Project..."),
                                    triggered=self.create_new_project)
        self.open_project_action = create_action(self,
                                    _("Open Project"),
                                    triggered=lambda v: self.open_project())
        self.open_project_new_window_action =\
            create_action(self, _("Open Project in New Window"),
                          triggered=self.open_project_in_new_window)
        self.close_project_action = create_action(self,
                                    _("Close Project"),
                                    triggered=self.close_project)
        self.clear_recent_projects_action =\
            create_action(self, _("Clear this list"),
                          triggered=self.clear_recent_projects)
        self.edit_project_preferences_action =\
            create_action(self, _("Project Preferences"),
                          triggered=self.edit_project_preferences)

        self.recent_project_menu = QMenu(_("Recent Projects"), self)

        self.main.projects_menu_actions += [self.new_project_action,
                                            None,
                                            self.open_project_action,
                                            self.close_project_action,
                                            None,
                                            self.recent_project_menu]

        self.setup_menu_actions()
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.pythonpath_changed()
        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.pythonpath_changed.connect(self.main.pythonpath_changed)
        self.create_module.connect(self.main.editor.new)
        self.edit.connect(self.main.editor.load)
        self.removed.connect(self.main.editor.removed)
        self.removed_tree.connect(self.main.editor.removed_tree)
        self.renamed.connect(self.main.editor.renamed)
        self.main.editor.set_projectexplorer(self)
        self.main.add_dockwidget(self)

        self.sig_open_file.connect(self.main.open_file)

        # New project connections. Order matters!
        self.sig_project_loaded.connect(lambda v: self.main.workingdirectory.chdir(v))
        self.sig_project_loaded.connect(lambda v: self.main.update_window_title())
        self.sig_project_loaded.connect(lambda v: self.main.editor.setup_open_files())
        self.sig_project_closed[object].connect(lambda v: self.main.workingdirectory.chdir(self.get_last_working_dir()))
        self.sig_project_closed.connect(lambda v: self.main.update_window_title())
        self.sig_project_closed.connect(lambda v: self.main.editor.setup_open_files())
        self.recent_project_menu.aboutToShow.connect(self.setup_menu_actions)

    def refresh_plugin(self):
        """Refresh project explorer widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        self.closing_widget()
        return True
        
    #------ Public API ---------------------------------------------------------
    def setup_menu_actions(self):
        """Setup and update the menu actions."""
        self.recent_project_menu.clear()
        self.recent_projects_actions = []
        if self.recent_projects:
            for project in self.recent_projects:
                if os.path.isdir(project):
                    action = create_action(
                        self,
                        _(project),
                        triggered=lambda v, path=project: self.open_project(path=path))
                    self.recent_projects_actions.append(action)
            self.recent_projects_actions += [None, self.clear_recent_projects_action]
        else:
            self.recent_projects_actions = [self.clear_recent_projects_action]
        add_actions(self.recent_project_menu, self.recent_projects_actions)
        self.update_project_actions()

    def update_project_actions(self):
        """ """
        if self.recent_projects:
            self.clear_recent_projects_action.setEnabled(True)
        else:
            self.clear_recent_projects_action.setEnabled(False)

        active = bool(self.get_active_project_path())
        self.close_project_action.setEnabled(active)
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
        dlg = ProjectDialog(self)
        dlg.sig_project_creation_requested.connect(self._create_project)
        dlg.sig_project_creation_requested.connect(self.sig_project_created)
        if dlg.exec_():
            pass
#        if self.dockwidget.isHidden():
#            self.dockwidget.show()
#        self.dockwidget.raise_()
#        if not self.treewidget.new_project():
#            # Notify dockwidget to schedule a repaint
#            self.dockwidget.update()

    def _create_project(self, path, ptype, packages):
        """Create a new project."""
        self.open_project(path=path)
        self.setup_menu_actions()
        if path not in self.recent_projects:
            self.recent_projects.insert(0, path)

    def open_project(self, path=None):
        """ """
        if path is None:
            basedir = get_home_dir()
            path = getexistingdirectory(parent=self,
                                        caption=_("Open project"),
                                        basedir=basedir)

        # TODO: Check that is a valid spyder project

        # A project was not open before
        if self.current_active_project is None:
            self.main.editor.save_open_files()
            self.main.editor.set_option('last_working_dir', getcwd())
            
        self.current_active_project = PythonProject(path)
        self.latest_project = PythonProject(path)
        self.set_option('current_project_path', self.get_active_project_path())
        self.setup_menu_actions()
        self.sig_project_loaded.emit(path)

    def open_project_in_new_window(self):
        """ """

    def close_project(self):
        """ """
        if self.current_active_project:
            path = self.current_active_project.root_path
            self.set_project_filenames(self.main.editor.get_open_filenames())
            self.current_active_project = None
            self.set_option('current_project_path', None)
            self.setup_menu_actions()
            self.sig_project_closed.emit(path)

    def clear_recent_projects(self):
        """ """
        self.recent_projects = []
        self.setup_menu_actions()

    def get_active_project(self):
        return self.current_active_project

    def setup_projects(self):
        current_project_path = self.get_option('current_project_path', default=None)

        # Needs a safer test of project existence!
        if current_project_path and os.path.isdir(current_project_path):
            self.open_project(path=current_project_path)

    def get_project_filenames(self):
        recent_files = []
        if self.current_active_project:
            recent_files = self.current_active_project.get_recent_files()     
        elif self.latest_project:
            recent_files = self.latest_project.get_recent_files()     
        return recent_files

    def set_project_filenames(self, recent_files):
        if self.current_active_project:
            self.current_active_project.set_recent_files(recent_files)

    def get_active_project_path(self):
        active_project_path = None
        if self.current_active_project:
            active_project_path = self.current_active_project.root_path
        return active_project_path

    def get_last_working_dir(self):
        return self.main.editor.get_option('last_working_dir',
                                           default=getcwd())

    def save_config(self):
        """Save configuration: opened projects & tree widget state"""
        self.set_option('recent_projects', self.recent_projects)
        self.set_option('expanded_state', self.treewidget.get_expanded_state())
        self.set_option('scrollbar_position',
                        self.treewidget.get_scrollbar_position())
        
    def load_config(self):
        """Load configuration: opened projects & tree widget state"""
        expanded_state = self.get_option('expanded_state', None)
        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if is_text_string(expanded_state):
            expanded_state = None
        if expanded_state is not None:
            self.treewidget.set_expanded_state(expanded_state)
        
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_option('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.treewidget.set_scrollbar_position(scrollbar_pos)
