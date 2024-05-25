# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline Explorer Plugin."""

# Third party imports
from qtpy.QtCore import Qt, Slot

# Local imports
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.plugins.outlineexplorer.main_widget import OutlineExplorerWidget


class OutlineExplorer(SpyderDockablePlugin):
    NAME = 'outline_explorer'
    CONF_SECTION = 'outline_explorer'
    REQUIRES = [Plugins.Completions, Plugins.Editor]
    OPTIONAL = []

    CONF_FILE = False
    WIDGET_CLASS = OutlineExplorerWidget

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name() -> str:
        """Return widget title."""
        return _('Outline Explorer')

    @staticmethod
    def get_description() -> str:
        """Return the description of the outline explorer widget."""
        return _("Explore functions, classes and methods in open files. Note "
                 "that if you disable the 'Completion and linting' plugin, "
                 "this one won't work.")

    @classmethod
    def get_icon(cls):
        """Return the outline explorer icon."""
        return cls.create_icon('outline_explorer')

    def on_initialize(self):
        if self.main:
            self.main.restore_scrollbar_position.connect(
                self._restore_scrollbar_position)
        self.sig_mainwindow_state_changed.connect(
            self._on_mainwindow_state_changed)

    @on_plugin_available(plugin=Plugins.Completions)
    def on_completions_available(self):
        completions = self.get_plugin(Plugins.Completions)

        completions.sig_language_completions_available.connect(
            self.start_symbol_services)
        completions.sig_stop_completions.connect(
            self.stop_symbol_services)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.sig_open_files_finished.connect(
            self.update_all_editors)
        widget.edit_goto.connect(editor.load_edit_goto)
        widget.edit.connect(editor.load_edit)

    @on_plugin_teardown(plugin=Plugins.Completions)
    def on_completions_teardown(self):
        completions = self.get_plugin(Plugins.Completions)

        completions.sig_language_completions_available.disconnect(
            self.start_symbol_services)
        completions.sig_stop_completions.disconnect(
            self.stop_symbol_services)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.sig_open_files_finished.disconnect(
            self.update_all_editors)
        widget.edit_goto.disconnect(editor.load_edit_goto)
        widget.edit.disconnect(editor.load_edit)

    # ----- Private API
    # -------------------------------------------------------------------------
    @Slot(object)
    def _on_mainwindow_state_changed(self, window_state):
        """Actions to take when the main window has changed its state."""
        if window_state == Qt.WindowMinimized:
            # There's no need to update the treewidget when the plugin is
            # minimized.
            self.get_widget().change_tree_visibility(False)
        else:
            self.get_widget().change_tree_visibility(True)

    def _restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_conf('scrollbar_position', None)
        explorer = self.get_widget()
        if scrollbar_pos is not None:
            explorer.treewidget.set_scrollbar_position(scrollbar_pos)

    # ----- Public API
    # -------------------------------------------------------------------------
    @Slot(dict, str)
    def start_symbol_services(self, capabilities, language):
        """Enable LSP symbols functionality."""
        explorer = self.get_widget()
        symbol_provider = capabilities.get('documentSymbolProvider', False)
        if symbol_provider:
            explorer.start_symbol_services(language)

    def stop_symbol_services(self, language):
        """Disable LSP symbols functionality."""
        explorer = self.get_widget()
        explorer.stop_symbol_services(language)

    def update_all_editors(self):
        """Update all editors with an associated LSP server."""
        explorer = self.get_widget()
        explorer.update_all_editors()

    def get_supported_languages(self):
        """List of languages with symbols support."""
        return self.get_widget().get_supported_languages()
