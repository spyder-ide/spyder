# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pylint Code Analysis Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot

# Local imports
from spyder.plugins.mainmenu.api import ApplicationMenus
from spyder.api.translations import get_translation
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.utils.programs import is_module_installed
from spyder.plugins.pylint.confpage import PylintConfigPage
from spyder.plugins.pylint.main_widget import (PylintWidget,
                                               PylintWidgetActions)


# Localization
_ = get_translation("spyder")


class PylintActions:
    AnalyzeCurrentFile = 'run analysis'


class Pylint(SpyderDockablePlugin):

    NAME = "pylint"
    WIDGET_CLASS = PylintWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = PylintConfigPage
    REQUIRES = [Plugins.Preferences, Plugins.Editor]
    OPTIONAL = [Plugins.MainMenu, Plugins.Projects]
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # --- Signals
    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    def get_name(self):
        return _("Code Analysis")

    def get_description(self):
        return _("Run Code Analysis.")

    def get_icon(self):
        return self.create_icon("pylint")

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        mainmenu = self.get_plugin(Plugins.MainMenu)
        preferences = self.get_plugin(Plugins.Preferences)

        preferences.register_plugin_preferences(self)

        # Expose widget signals at the plugin level
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        widget.sig_start_analysis_requested.connect(
            lambda: self.start_code_analysis())

        # Connect to Editor
        widget.sig_edit_goto_requested.connect(editor.load)
        editor.sig_editor_focus_changed.connect(self._set_filename)

        # Connect to projects
        projects = self.get_plugin(Plugins.Projects)
        if projects:
            projects.sig_project_loaded.connect(
                lambda value: widget.set_conf("project_dir", value))
            projects.sig_project_closed.connect(
                lambda value: widget.set_conf("project_dir", None))

        # Add action to application menus
        pylint_act = self.create_action(
            PylintActions.AnalyzeCurrentFile,
            text=_("Run code analysis"),
            tip=_("Run code analysis"),
            icon=self.create_icon("pylint"),
            triggered=lambda: self.start_code_analysis(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True
        )
        pylint_act.setEnabled(is_module_installed("pylint"))

        if mainmenu:
            source_menu = mainmenu.get_application_menu(
                ApplicationMenus.Source)
            mainmenu.add_item_to_application_menu(pylint_act, menu=source_menu)

        # TODO: use new API when editor has migrated
        self.main.editor.pythonfile_dependent_actions += [pylint_act]

    # --- Private API
    # ------------------------------------------------------------------------
    @Slot()
    def _set_filename(self):
        """
        Set filename without code analysis.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            self.get_widget().set_filename(editor.get_current_filename())

    # --- Public API
    # ------------------------------------------------------------------------
    def change_history_depth(self, value=None):
        """
        Change history maximum number of entries.

        Parameters
        ----------
        value: int or None, optional
            The valur to set  the maximum history depth. If no value is
            provided, an input dialog will be launched. Default is None.
        """
        self.get_widget().change_history_depth(value=value)

    def get_filename(self):
        """
        Get current filename in combobox.
        """
        return self.get_widget().get_filename()

    def start_code_analysis(self, filename=None):
        """
        Perform code analysis for given `filename`.

        If `filename` is None default to current filename in combobox.

        If this method is called while still running it will stop the code
        analysis.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            if self.get_conf("save_before", True) and not editor.save():
                return

        if filename is None:
            filename = self.get_widget().get_filename()

        self.switch_to_plugin(force_focus=True)
        self.get_widget().start_code_analysis(filename)

    def stop_code_analysis(self):
        """
        Stop the code analysis process.
        """
        self.get_widget().stop_code_analysis()
