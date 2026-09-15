# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline Explorer Plugin."""

# Standard library plugins
import functools
import sys

# Third party imports
import lsprotocol.types as lsp
from qtpy.QtCore import Qt, Slot

# Local imports
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.plugins.mainmenu.api import ApplicationMenus, FileMenuSections
from spyder.plugins.outlineexplorer.main_widget import (
    OutlineExplorerActions,
    OutlineExplorerWidget,
)


class OutlineExplorer(SpyderDockablePlugin):
    NAME = 'outline_explorer'
    CONF_SECTION = 'outline_explorer'
    REQUIRES = [Plugins.Completions, Plugins.Editor, Plugins.MainMenu]
    OPTIONAL = [Plugins.Switcher]
    TABIFY = [Plugins.Projects]

    CONF_FILE = False
    WIDGET_CLASS = OutlineExplorerWidget

    _SWITCHER_MODE = "@"

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name() -> str:
        """Return widget title."""
        return _('Outline Explorer')

    @staticmethod
    def get_description() -> str:
        """Return the description of the outline explorer widget."""
        return _("Explore functions, classes and methods in open files.")

    @classmethod
    def get_icon(cls):
        """Return the outline explorer icon."""
        return cls.create_icon('outline_explorer')

    def on_initialize(self):
        self._editor = None
        self._switcher = None
        self._symbol_finder_action = None

        if self.main:
            self.main.restore_scrollbar_position.connect(
                self._restore_scrollbar_position
            )

        self.sig_mainwindow_state_changed.connect(
            self._on_mainwindow_state_changed
        )

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
        self._editor = editor = self.get_plugin(Plugins.Editor)

        editor.sig_open_files_finished.connect(
            self.update_all_editors)
        widget.edit_goto.connect(editor.load_edit_goto)
        widget.edit.connect(editor.load_edit)

        # Reconnect open CodeEditors if the plugin is reenabled
        if not self.is_app_starting:
            for editorstack in editor.get_editorstacks():
                # Editor windows have their own Outline, so stacks in them
                # don't need to be reconnected to this one.
                if editorstack.new_window:
                    continue

                # Register proxy editors
                for finfo in editorstack.data:
                    oe_proxy = finfo.editor.oe_proxy
                    if oe_proxy is not None:
                        self.get_widget().register_editor(oe_proxy)

            # Restart symbol services (active LSPs are saved in the Editor main
            # widget)
            for (
                language,
                capabilities,
            ) in editor.get_widget().completion_capabilities.items():
                self.start_symbol_services(capabilities, language)

            # Get an editorstack in the main window
            current_editorstack = editor.get_current_editorstack()
            if current_editorstack.new_window:
                current_editorstack = editor.get_editorstacks()[0]

            # Set proxy of current editor to update the Outline contents
            # automatically (otherwise it's necessary to give focus to the
            # Editor)
            current_proxy = current_editorstack.get_current_editor().oe_proxy
            if current_proxy is not None:
                self.get_widget().set_current_editor(
                    current_proxy, update=True, clear=False
                )

            # Update symbols for all open CodeEditors
            self.update_all_editors()

    @on_plugin_available(plugin=Plugins.Switcher)
    def on_switcher_available(self):
        self._switcher = self.get_plugin(Plugins.Switcher)
        self._switcher.add_mode(
            self._SWITCHER_MODE, _('Go to symbol in current file')
        )

        self._switcher.sig_mode_selected.connect(self._handle_switcher_modes)
        self._switcher.sig_item_selected.connect(
             self._handle_switcher_selection
        )
        self._switcher.sig_item_changed.connect(
            self._handle_switcher_item_change
        )

        # This action can only be created when the Switcher is enabled.
        # Otherwise, it won't do anything.
        self._symbol_finder_action = self.create_action(
            OutlineExplorerActions.SymbolFinderAction,
            _('Symbol finder...'),
            icon=self.create_icon('symbol_find'),
            tip=_('Search for symbols in the current file'),
            triggered=functools.partial(
                self._switcher.open_switcher, mode=self._SWITCHER_MODE
            ),
            register_shortcut=True,
            context=Qt.ApplicationShortcut,
            shortcut_context="_",
        )

        self._add_symbol_finder_action_to_menu()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_mainmenu_available(self):
        self._add_symbol_finder_action_to_menu()

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

        self._editor = None

    @on_plugin_teardown(plugin=Plugins.Switcher)
    def on_switcher_teardown(self):
        self._switcher.remove_mode(self._SWITCHER_MODE)

        self._switcher.sig_mode_selected.disconnect(
            self._handle_switcher_modes
        )
        self._switcher.sig_item_selected.disconnect(
             self._handle_switcher_selection
        )
        self._switcher.sig_item_changed.disconnect(
            self._handle_switcher_item_change
        )

        self._remove_symbol_finder_action()

        self._switcher = None
        self._symbol_finder_action = None

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_mainmenu_teardown(self):
        self._remove_symbol_finder_action()

    def on_close(self, cancelable: bool = False):
        if self.main:
            self.main.restore_scrollbar_position.disconnect(
                self._restore_scrollbar_position
            )

        self.sig_mainwindow_state_changed.disconnect(
            self._on_mainwindow_state_changed
        )

        # This is needed to stop showing symbols in the switcher when the
        # plugin is disabled on the fly
        if not self.is_app_closing:
            for language in self.get_supported_languages():
                self.stop_symbol_services(language)

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

    def _set_toggle_view_action_state(self):
        """Set state of the toogle view action."""
        self.get_widget().blockSignals(True)
        if self.get_widget().is_visible:
            self.get_widget().toggle_view_action.setChecked(True)
        else:
            self.get_widget().toggle_view_action.setChecked(False)
        self.get_widget().blockSignals(False)

    def _handle_switcher_modes(self, mode):
        if mode == self._SWITCHER_MODE:
            self.get_widget().create_symbol_switcher()

    def _handle_switcher_selection(self, item, mode, search_text):
        if mode == self._SWITCHER_MODE:
            data = item.get_data()
            line_number = data['line_number']
            self._editor.get_current_editorstack().go_to_line(int(line_number))

            self._switcher.hide()
            self._switcher.set_search_text('')

    def _handle_switcher_item_change(self, current):
        """Handle item selection change."""
        mode = self._switcher.get_mode()

        if mode == self._SWITCHER_MODE and current is not None:
            data = current.get_data()
            if isinstance(data, dict):
                self._editor.get_current_editorstack().go_to_line(
                    int(data['line_number'])
                )

    def _add_symbol_finder_action_to_menu(self):
        if self._symbol_finder_action is None:
            return

        if sys.platform == 'darwin':
            before_section = FileMenuSections.Navigation
        else:
            before_section = FileMenuSections.Restart

        mainmenu = self.get_plugin(Plugins.MainMenu, error=False)
        if mainmenu:
            mainmenu.add_item_to_application_menu(
                self._symbol_finder_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Switcher,
                before_section=before_section,
                render=not self.is_app_starting,
            )

    def _remove_symbol_finder_action(self):
        if self._symbol_finder_action is None:
            return

        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            self._symbol_finder_action, menu_id=ApplicationMenus.File,
        )

        self.delete_action(OutlineExplorerActions.SymbolFinderAction)
        self._symbol_finder_action = None

    # ----- Public API
    # -------------------------------------------------------------------------
    @Slot(dict, str)
    def start_symbol_services(
        self, capabilities: lsp.ServerCapabilities, language
    ):
        """Enable LSP symbols functionality."""
        explorer = self.get_widget()
        symbol_provider = capabilities.document_symbol_provider
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

    def dock_with_maximized_editor(self):
        """
        Actions to take when the plugin is docked next to the editor when the
        latter is maximized.
        """
        self.get_widget().in_maximized_editor = True
        if self.get_conf('show_with_maximized_editor'):
            self.main.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            # This width is enough to show all buttons in the main toolbar
            max_width = 360

            # Give an appropiate width to the Outline
            editor = self.get_plugin(Plugins.Editor)
            self.main.resizeDocks(
                [editor.dockwidget, self.dockwidget],
                # We set main_window.width() // 7 as the min width for the
                # Outline because it's not too wide for small screens.
                [self.main.width(), min(self.main.width() // 7, max_width)],
                Qt.Horizontal
            )

        self._set_toggle_view_action_state()

    def hide_from_maximized_editor(self):
        """
        Actions to take when the plugin is hidden after the editor is
        unmaximized.
        """
        self.get_widget().in_maximized_editor = False
        self._set_toggle_view_action_state()
