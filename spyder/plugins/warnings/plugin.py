# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""Warnings/errors Plugin."""


# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.api.plugins import SpyderPluginWidget

from .widgets.warninggui import WarningWidget


class Warnings(SpyderPluginWidget):
    """Warnings/errors list"""
    CONF_SECTION = 'warnings'

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.warnings = WarningWidget(self, options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.warnings)
        self.setLayout(layout)

        # Follow editorstacks tab change
        self.main.editor.sig_editor_focus_changed.connect(self.update_data)
        # Follow updated code anaylsis
        editorstack = self.main.editor.get_current_editorstack()
        editorstack.update_code_analysis_actions.connect(self.update_data)
        self.update_data()

    # ----- SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Warnings/errors")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('wng_list', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.warnings.warningtable

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.warnings.edit_goto.connect(self.main.editor.load)

        self.add_dockwidget()

        list_action = create_action(self, _("List warnings/errors"),
                                    triggered=self.show)
        list_action.setEnabled(True)
        self.main.editor.pythonfile_dependent_actions += [list_action]

    def show(self):
        """Show the warnings dockwidget"""
        self.switch_to_plugin()

    @Slot()
    def update_data(self):
        """Update table"""
        editor = self.main.editor.get_current_editor()
        results = editor.get_current_warnings(complete=True)
        filename = self.main.editor.get_current_filename()
        self.warnings.set_data(results, filename)
