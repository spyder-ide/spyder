# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Configuration dialog for projects"""

from qtpy.QtWidgets import QGroupBox, QVBoxLayout

from spyder.config.base import _
from spyder.plugins.configdialog import ConfigDialog, GeneralConfigPage
from spyder.utils.qthelpers import get_icon
from spyder.config.user import NoDefault
from spyder.widgets.projects import EmptyProject
from spyder.widgets.projects.config import (WORKSPACE, VCS, ENCODING,
                                            CODESTYLE)


class ProjectPreferences(ConfigDialog):
    """ """
    def __init__(self, parent, project):
        super(ProjectPreferences, self).__init__()

        self._main = parent
        self._project = project
        self._project_preferences = [WorkspaceConfigPage] #, VersionConfigPage]

        self.setWindowTitle(_("Project preferences"))
        self.setWindowIcon(get_icon("configure.png"))

        self.setup_dialog()

    def setup_dialog(self):
        """ """
        # Move to spyder.py
#        dlg = ConfigDialog(self)
#        dlg.size_change.connect(self.set_prefs_size)
#        if self.prefs_dialog_size is not None:
#            dlg.resize(self.prefs_dialog_size)
        for PrefPageClass in self._project_preferences:
            widget = PrefPageClass(self, self._main, self._project)
            widget.initialize()
            self.add_page(widget)


class ProjectConfigPage(GeneralConfigPage):
    """General config page that redefines the configuration accessors."""
    CONF_SECTION = None
    NAME = None
    ICON = None

    def __init__(self, parent, main, project):
        self._project = project
        self._conf_files = project.get_conf_files()
        self._conf = self._conf_files[self.CONF_SECTION]

        GeneralConfigPage.__init__(self, parent, main)

    def set_option(self, option, value):
        """ """
        CONF = self._conf
        CONF.set(self.CONF_SECTION, option, value)

    def get_option(self, option, default=NoDefault):
        """" """
        CONF = self._conf
        return CONF.get(self.CONF_SECTION, option, default)


class WorkspaceConfigPage(ProjectConfigPage):
    CONF_SECTION = WORKSPACE
    NAME = _("General")
    ICON = "genprefs.png"

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Workspace
        interface_group = QGroupBox(_("Interface"))
        restore_data_box = newcb(_("Restore data on startup"),
                                 'restore_data_on_startup')
        save_data_box = newcb(_("Save data on exit"),
                              'save_data_on_exit')
        save_history_box = newcb(_("Save history"),
                                 'save_history')
        save_non_project_box = newcb(_("Save non project files opened"),
                                     'save_non_project_files')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(restore_data_box)
        interface_layout.addWidget(save_data_box)
        interface_layout.addWidget(save_history_box)
        interface_layout.addWidget(save_non_project_box)
        interface_group.setLayout(interface_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(interface_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def apply_settings(self, options):
        """ """
        pass  # TODO:
        #self.main.apply_settings()


class CodeConfigPage(ProjectConfigPage):
    CONF_SECTION = CODESTYLE
    NAME = _("Code")
    ICON = "genprefs.png"

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Workspace
        interface_group = QGroupBox(_("Workspace"))
        restore_data_box = newcb(_("Restore data on startup"),
                                 'restore_data_on_startup')
        save_data_box = newcb(_("Save data on exit"),
                              'save_data_on_exit')
        save_history_box = newcb(_("Save history"),
                                 'save_history')
        save_non_project_box = newcb(_("Save non project files opened"),
                                     'save_non_project_files')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(restore_data_box)
        interface_layout.addWidget(save_data_box)
        interface_layout.addWidget(save_history_box)
        interface_layout.addWidget(save_non_project_box)
        interface_group.setLayout(interface_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(interface_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def apply_settings(self, options):
        """ """
        print('applied')
        #self.main.apply_settings()


class VersionConfigPage(ProjectConfigPage):
    CONF_SECTION = VCS
    NAME = _("Version control")
    ICON = "genprefs.png"

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Workspace
        vcs_group = QGroupBox(_("Version control"))
        use_version_control = newcb(_("Use version control"),
                                    'use_version_control')

        styles = ['git', 'hg']
        choices = list(zip(styles, [style.lower() for style in styles]))
        vcs_combo = self.create_combobox(_('Version control system'), choices,
                                         'version_control_system',
                                         default='git')

        vcs_layout = QVBoxLayout()
        vcs_layout.addWidget(use_version_control)
        vcs_layout.addWidget(vcs_combo)
        vcs_group.setLayout(vcs_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(vcs_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def apply_settings(self, options):
        """ """
        print('applied')
        #self.main.apply_settings()


if __name__ == "__main__":
    import os.path as osp
    import tempfile
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    proj_dir = tempfile.mkdtemp() + osp.sep + '.spyproject'
    proj = EmptyProject(proj_dir)
    dlg = ProjectPreferences(None, proj)
    dlg.show()
    app.exec_()
