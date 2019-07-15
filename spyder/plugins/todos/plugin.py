# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""Todo Plugin."""


# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.api.plugins import SpyderPluginWidget

from .widgets.todogui import TodoWidget


class Todos(SpyderPluginWidget):
    """Todo list"""
    CONF_SECTION = 'todos'

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.todos = TodoWidget(self, options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.todos)
        self.setLayout(layout)

        self.todos.set_data()
        # Follow editorstacks tab change
        self.main.editor.sig_editor_focus_changed.connect(self.update_data)
        # Follow Todo list updates
        editorstack = self.main.editor.get_current_editorstack()
        editorstack.todo_results_changed.connect(self.update_data)

    # ----- SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Todos")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('todo_list', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.todos.todotable

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.todos.edit_goto.connect(self.main.editor.load)

        self.add_dockwidget()

        list_action = create_action(self, _("List todos"),
                                    triggered=self.show)
        list_action.setEnabled(True)
        self.main.editor.pythonfile_dependent_actions += [list_action]

    def show(self):
        """Show the todos dockwidget"""
        self.switch_to_plugin()

    def get_todo_list(self):
        editorstack = self.main.editor.get_current_editorstack()
        results = editorstack.get_todo_results()
        return results

    def get_filename(self):
        return self.main.editor.get_current_filename()

    def update_data(self):
        """Update table"""
        self.todos.set_data()
