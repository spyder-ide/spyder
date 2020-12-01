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
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.menus import ApplicationMenus
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.config.base import _
from spyder.plugins.pylint.confpage import PylintConfigPage
from spyder.plugins.pylint.main_widget import (PylintWidget,
                                               PylintWidgetActions)
from spyder.plugins.pylint.rule_ignorer import RuleIgnorer
from spyder.utils.programs import is_module_installed

# Localization
_ = get_translation("spyder")


class Pylint(SpyderDockablePlugin):
    NAME = "pylint"
    WIDGET_CLASS = PylintWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = PylintConfigPage
    REQUIRES = [Plugins.Editor]
    OPTIONAL = [Plugins.Projects]
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
        path = osp.join(self.get_path(), self.IMG_PATH)
        return self.create_icon("pylint", path=path)

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        # Expose widget signals at the plugin level
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        widget.sig_start_analysis_requested.connect(
            lambda: self.start_code_analysis())

        widget.sig_edit_ignore_rule.connect(self.ignore_rule)

        # Connect to Editor
        widget.sig_edit_goto_requested.connect(editor.load)
        editor.sig_editor_focus_changed.connect(self._set_filename)

        # Connect to projects
        projects = self.get_plugin(Plugins.Projects)
        if projects:
            projects.sig_project_loaded.connect(
                lambda value: widget.change_option("project_dir", value))
            projects.sig_project_closed.connect(
                lambda value: widget.change_option("project_dir", None))

        # Add action to application menus
        pylint_act = self.get_action(PylintWidgetActions.RunCodeAnalysis)
        pylint_act.setEnabled(is_module_installed("pylint"))

        source_menu = self.get_application_menu(ApplicationMenus.Source)
        self.add_item_to_application_menu(pylint_act, menu=source_menu)

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
            if self.get_conf_option("save_before", True) and not editor.save():
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

    def ignore_rule(self, filename, lineno, ruleid):
        """ Ignoring a pylint rule will:
            -> load the file
            -> add the pylint ignore comment
            -> save the file
            -> rerun the code analysis

            Some considerations to have in mind:
                - If the last code analysis run does not match with what is on
                the file, there are chances that the pylint ignore comment is
                being added in a line that does not match the intention of the
                user. So is responsibility of the user to rerun the code
                analysis if they change the code, before adding a ignore rule.

                - When the user re-run a code analysis we are not blocking the
                widget, so they can still use the ignore feature when a code
                analysis is running. This means that for big files the code
                analysis could take some time and if the user successively use
                the feature without waiting for the code analysis to finish
                this could cause the same that is described in the previous
                item.
        """
        self.main.editor.load(filename)
        RuleIgnorer(self.main.editor.get_current_editor()).ignore_rule_in_line(
            ruleid, lineno)
        self.main.editor.save()
        self.get_widget().start_code_analysis()
