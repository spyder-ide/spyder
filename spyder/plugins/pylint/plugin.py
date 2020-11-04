# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


"""Pylint Code Analysis Plugin."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QInputDialog, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils import icon_manager as ima
from spyder.utils.programs import is_module_installed
from spyder.utils.qthelpers import create_action, MENU_SEPARATOR
from spyder.plugins.pylint.confpage import (PylintConfigPage,
                                            MAX_HISTORY_ENTRIES,
                                            MIN_HISTORY_ENTRIES,
                                            DEFAULT_HISTORY_ENTRIES)
from spyder.plugins.pylint.widgets.pylintgui import PylintWidget


if is_dark_interface():
    MAIN_TEXT_COLOR = 'white'
    MAIN_PREVRATE_COLOR = 'white'
else:
    MAIN_TEXT_COLOR = '#444444'
    MAIN_PREVRATE_COLOR = '#666666'


class Pylint(SpyderPluginWidget):
    """Python source code analysis based on pylint."""

    CONF_SECTION = 'pylint'
    CONFIGWIDGET_CLASS = PylintConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    def __init__(self, parent=None):
        super().__init__(parent)

        max_entries = self.get_option('max_entries', DEFAULT_HISTORY_ENTRIES)
        self.pylint = PylintWidget(self, max_entries=max_entries,
                                   options_button=self.options_button,
                                   text_color=MAIN_TEXT_COLOR,
                                   prevrate_color=MAIN_PREVRATE_COLOR,
                                   top_max_entries=MAX_HISTORY_ENTRIES)

        layout = QVBoxLayout()
        layout.addWidget(self.pylint)
        self.setLayout(layout)

        # Add history_action to treewidget context menu
        history_action = create_action(self, _("History..."),
                                       None, ima.icon('history'),
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.pylint.treewidget.common_actions += (None, history_action)

        # Follow editorstacks tab change
        self.main.editor.sig_editor_focus_changed.connect(self.set_filename)

        # Used by Analyze button to check if file should be saved and start
        # analysis
        self.pylint.start_analysis.connect(self.run_pylint_from_analyze_button)

    # ------ SpyderPluginWidget API -------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Code Analysis")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('pylint', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.pylint.treewidget

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return self.pylint.treewidget.get_menu_actions()

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.pylint.treewidget.sig_edit_goto.connect(self.main.editor.load)
        self.pylint.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        self.add_dockwidget()

        pylint_act = create_action(self, _("Run code analysis"),
                                   triggered=self.run_pylint)
        pylint_act.setEnabled(is_module_installed('pylint'))
        self.register_shortcut(pylint_act, context="Pylint",
                               name="Run analysis")

        self.main.source_menu_actions += [MENU_SEPARATOR, pylint_act]
        self.main.editor.pythonfile_dependent_actions += [pylint_act]

    def refresh_plugin(self):
        """Refresh pylint widget"""
        self.pylint.remove_obsolete_items()

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # The history depth option will be applied at
        # next Spyder startup, which is soon enough
        self.pylint.change_history_limit(self.get_option('max_entries'))

    def closing_plugin(self, cancelable=False):
        """Handle actions when the plugin is closing."""
        self.pylint.save_history()
        return True

    # ----- Public API --------------------------------------------------------
    @Slot()
    def change_history_depth(self):
        """Change history max entries."""
        dialog.setWindowTitle(_('History'))
        dialog.setLabelText(_('Maximum entries'))
        dialog.setInputMode(QInputDialog.IntInput)
        dialog.setIntRange(MIN_HISTORY_ENTRIES, MAX_HISTORY_ENTRIES)
        dialog.setIntStep(1)
        dialog.setIntValue(self.get_option('max_entries'))

        # Connect slot
        dialog.intValueSelected.connect(
            lambda value: self.set_history_limit(value))

        dialog.show()

    def set_history_limit(self, value):
        """Set history limit."""
        self.set_option('max_entries', value)
        self.pylint.change_history_limit(value)

    def get_filename(self):
        """Get current filename in combobox."""
        return self.pylint.get_filename()

    @Slot()
    def set_filename(self):
        """Set filename without code analysis."""
        self.pylint.set_filename(self.main.editor.get_current_filename())

    @Slot()
    def run_pylint(self):
        """Run pylint code analysis"""
        if (self.get_option('save_before', True)
                and not self.main.editor.save()):
            return
        self.switch_to_plugin()
        self.analyze(self.main.editor.get_current_filename())

    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget:
            self.switch_to_plugin()
        self.pylint.analyze(filename)

    @Slot()
    def run_pylint_from_analyze_button(self):
        """
        See if file should and can be saved and run pylint code analysis.

        Does not check that file name is valid etc, so should only be used for
        Analyze button.
        """
        if (self.get_option('save_before', True)
                and not self.main.editor.save()):
            return
        self.pylint.start()
