# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer main widget."""

from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QHBoxLayout

from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.translations import _
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerTreeWidget


# ---- Enums
# -----------------------------------------------------------------------------
class OutlineExplorerToolbuttons:
    GoToCursor = 'go_to_cursor'


class OutlineExplorerSections:
    Main = 'main_section'
    DisplayOptions = 'display_options'


class OutlineExplorerActions:
    GoToCursor = 'go_to_cursor'
    ShowFullPath = 'show_fullpath'
    ShowAllFiles = 'show_all_files'
    ShowSpecialComments = 'show_comments'
    GroupCodeCells = 'group_code_cells'
    DisplayVariables = 'display_variables'
    FollowCursor = 'follow_cursor'
    SortFiles = 'sort_files_alphabetically'


# ---- Main widget
# -----------------------------------------------------------------------------
class OutlineExplorerWidget(PluginMainWidget):
    """Class browser"""
    edit_goto = Signal(str, int, str)
    edit = Signal(str)
    is_visible = Signal()
    sig_update_configuration = Signal()

    ENABLE_SPINNER = True
    CONF_SECTION = 'outline_explorer'

    def __init__(self, name, plugin, parent=None, context=None):
        if context is not None:
            self.CONTEXT_NAME = context

        super().__init__(name, plugin, parent)

        self.treewidget = OutlineExplorerTreeWidget(self)
        self.treewidget.sig_display_spinner.connect(self.start_spinner)
        self.treewidget.sig_hide_spinner.connect(self.stop_spinner)
        self.treewidget.sig_update_configuration.connect(
            self.sig_update_configuration)

        self.treewidget.header().hide()

        layout = QHBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

    # ---- PluginMainWidget API
    # -------------------------------------------------------------------------
    def get_focus_widget(self):
        """Define the widget to focus."""
        return self.treewidget

    def get_title(self):
        """Return the title of the plugin tab."""
        return _("Outline")

    def setup(self):
        """Performs the setup of plugin's menu and actions."""
        # Toolbar buttons
        toolbar = self.get_main_toolbar()
        fromcursor_btn = self.create_toolbutton(
            OutlineExplorerToolbuttons.GoToCursor,
            icon=self.create_icon('fromcursor'),
            tip=_('Go to cursor position'),
            triggered=self.treewidget.go_to_cursor_position)

        for item in [fromcursor_btn,
                     self.treewidget.collapse_all_action,
                     self.treewidget.expand_all_action,
                     self.treewidget.restore_action,
                     self.treewidget.collapse_selection_action,
                     self.treewidget.expand_selection_action]:
            self.add_item_to_toolbar(item, toolbar=toolbar,
                                     section=OutlineExplorerSections.Main)

        # Actions
        fromcursor_act = self.create_action(
            OutlineExplorerActions.GoToCursor,
            text=_('Go to cursor position'),
            icon=self.create_icon('fromcursor'),
            triggered=self.treewidget.go_to_cursor_position)

        fullpath_act = self.create_action(
            OutlineExplorerActions.ShowFullPath,
            text=_('Show absolute path'),
            toggled=True,
            option='show_fullpath')

        allfiles_act = self.create_action(
            OutlineExplorerActions.ShowAllFiles,
            text=_('Show all files'),
            toggled=True,
            option='show_all_files')

        comment_act = self.create_action(
            OutlineExplorerActions.ShowSpecialComments,
            text=_('Show special comments'),
            toggled=True,
            option='show_comments')

        group_cells_act = self.create_action(
            OutlineExplorerActions.GroupCodeCells,
            text=_('Group code cells'),
            toggled=True,
            option='group_cells')

        display_variables_act = self.create_action(
            OutlineExplorerActions.DisplayVariables,
            text=_('Display variables and attributes'),
            toggled=True,
            option='display_variables'
        )

        follow_cursor_act = self.create_action(
            OutlineExplorerActions.FollowCursor,
            text=_('Follow cursor position'),
            toggled=True,
            option='follow_cursor'
        )

        sort_files_alphabetically_act = self.create_action(
            OutlineExplorerActions.SortFiles,
            text=_('Sort files alphabetically'),
            toggled=True,
            option='sort_files_alphabetically'
        )

        actions = [fullpath_act, allfiles_act, group_cells_act,
                   display_variables_act, follow_cursor_act, comment_act,
                   sort_files_alphabetically_act, fromcursor_act]

        option_menu = self.get_options_menu()
        for action in actions:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.DisplayOptions,
            )

    def update_actions(self):
        pass

    def change_visibility(self, enable, force_focus=None):
        """Reimplemented to tell treewidget what the visibility state is."""
        super().change_visibility(enable, force_focus)

        if self.windowwidget is not None:
            # When the plugin is undocked Qt changes its visibility to False,
            # probably because it's not part of the main window anymore. So, we
            # need to set the treewidget visibility to True for it to be
            # updated after writing new content in the editor.
            # Fixes spyder-ide/spyder#16634
            self.change_tree_visibility(True)
        else:
            self.change_tree_visibility(self.is_visible)

    def create_window(self):
        """
        Reimplemented to tell treewidget what the visibility of the undocked
        plugin is.
        """
        super().create_window()
        self.windowwidget.sig_window_state_changed.connect(
            self._handle_undocked_window_state)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_current_editor(self, editor, update, clear):
        if clear:
            self.remove_editor(editor)
        if editor is not None:
            self.treewidget.set_current_editor(editor, update)

    def remove_editor(self, editor):
        self.treewidget.remove_editor(editor)

    def register_editor(self, editor):
        self.treewidget.register_editor(editor)

    def file_renamed(self, editor, new_filename):
        self.treewidget.file_renamed(editor, new_filename)

    def start_symbol_services(self, language):
        """Enable LSP symbols functionality."""
        self.treewidget.start_symbol_services(language)

    def stop_symbol_services(self, language):
        """Disable LSP symbols functionality."""
        self.treewidget.stop_symbol_services(language)

    def update_all_editors(self):
        """Update all editors with an associated LSP server."""
        self.treewidget.update_all_editors()

    def get_supported_languages(self):
        """List of languages with symbols support."""
        return self.treewidget._languages

    def change_tree_visibility(self, is_visible):
        "Change treewidget's visibility."
        self.treewidget.change_visibility(is_visible)

    # ---- Private API
    # -------------------------------------------------------------------------
    @Slot(object)
    def _handle_undocked_window_state(self, window_state):
        """
        Change treewidget visibility when the plugin is undocked and its
        window state changes.
        """
        if window_state == Qt.WindowMinimized:
            # There's no need to update the treewidget when the plugin is
            # minimized.
            self.change_tree_visibility(False)
        else:
            self.change_tree_visibility(True)
