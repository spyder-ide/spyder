# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Plugin"""

import logging
import sys

from qtpy.QtCore import Signal

from spyder.api.fonts import SpyderFontType
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.translations import _
from spyder.plugins.editor.api.run import (
    SelectionContextModificator,
    ExtraAction
)
from spyder.plugins.editor.confpage import EditorConfigPage
from spyder.plugins.editor.widgets.main_widget import (
    EditorMainWidget,
    EditorWidgetActions
)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus,
    EditMenuSections,
    FileMenuSections,
    SearchMenuSections,
    SourceMenuSections
)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.run.api import RunContext


logger = logging.getLogger(__name__)


class Editor(SpyderDockablePlugin):
    """
    Editor plugin.
    """

    NAME = 'editor'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [
        Plugins.Completions,
        Plugins.Debugger,
        Plugins.IPythonConsole,
        Plugins.MainMenu,
        Plugins.Projects,
        Plugins.OutlineExplorer,
        Plugins.Run,
        Plugins.StatusBar,
        Plugins.Switcher,
        Plugins.Toolbar
    ]
    WIDGET_CLASS = EditorMainWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = EditorConfigPage
    CONF_FILE = False

    # ---- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str)
    """
    This signal is emitted when the editor changes the current directory.

    Parameters
    ----------
    new_working_directory: str
        The new working directory path.

    Notes
    -----
    This option is available on the options menu of the editor plugin
    """

    sig_file_opened_closed_or_updated = Signal(str, str)
    """
    This signal is emitted when a file is opened, closed or updated,
    including switching among files.

    Parameters
    ----------
    filename: str
        Name of the file that was opened, closed or updated.
    language: str
        Name of the programming language of the file that was opened,
        closed or updated.
    """

    # This signal is fired for any focus change among all editor stacks
    sig_editor_focus_changed = Signal()

    sig_help_requested = Signal(dict)
    """
    This signal is emitted to request help on a given object `name`.

    Parameters
    ----------
    help_data: dict
        Dictionary required by the Help pane to render a docstring.

    Examples
    --------
    >>> help_data = {
        'obj_text': str,
        'name': str,
        'argspec': str,
        'note': str,
        'docstring': str,
        'force_refresh': bool,
        'path': str,
    }

    See Also
    --------
    :py:meth:spyder.plugins.editor.widgets.editorstack.EditorStack.send_to_help
    """

    sig_open_files_finished = Signal()
    """
    This signal is emitted when the editor finished to open files.
    """

    sig_codeeditor_created = Signal(object)
    """
    This signal is emitted when a codeeditor is created.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

    sig_codeeditor_deleted = Signal(object)
    """
    This signal is emitted when a codeeditor is closed.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

    sig_codeeditor_changed = Signal(object)
    """
    This signal is emitted when the current codeeditor changes.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Editor')

    @staticmethod
    def get_description():
        return _(
            "Edit Python, Markdown, Cython and many other types of text files."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon('edit')

    def on_initialize(self):
        widget = self.get_widget()

        # ---- Help related signals
        widget.sig_help_requested.connect(self.sig_help_requested)

        # ---- General signals
        widget.starting_long_process.connect(self.before_long_process)
        widget.ending_long_process.connect(self.after_long_process)
        widget.sig_dir_opened.connect(self.sig_dir_opened)
        widget.sig_file_opened_closed_or_updated.connect(
            self.sig_file_opened_closed_or_updated
        )
        widget.sig_open_files_finished.connect(self.sig_open_files_finished)

        # ---- CodeEditor related signals
        widget.sig_codeeditor_created.connect(self.sig_codeeditor_created)
        widget.sig_codeeditor_deleted.connect(self.sig_codeeditor_deleted)
        widget.sig_codeeditor_changed.connect(self.sig_codeeditor_changed)
        widget.sig_editor_focus_changed.connect(self.sig_editor_focus_changed)

        # ---- Plugin related signals
        widget.sig_switch_to_plugin_requested.connect(
            lambda: self.switch_to_plugin(force_focus=True)
        )

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        # Add status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)
        widget = self.get_widget()
        statusbar.add_status_widget(widget.readwrite_status)
        statusbar.add_status_widget(widget.eol_status)
        statusbar.add_status_widget(widget.encoding_status)
        statusbar.add_status_widget(widget.cursorpos_status)
        statusbar.add_status_widget(widget.vcs_status)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        # Remove status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)
        widget = self.get_widget()
        statusbar.remove_status_widget(widget.readwrite_status.ID)
        statusbar.remove_status_widget(widget.eol_status.ID)
        statusbar.remove_status_widget(widget.encoding_status.ID)
        statusbar.remove_status_widget(widget.cursorpos_status.ID)
        statusbar.remove_status_widget(widget.vcs_status.ID)

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        widget = self.get_widget()
        run = self.get_plugin(Plugins.Run)

        widget.sig_editor_focus_changed_uuid.connect(
            run.switch_focused_run_configuration
        )
        widget.sig_register_run_configuration_provider_requested.connect(
            lambda supported_extensions:
                run.register_run_configuration_provider(
                    self.NAME, supported_extensions
                )
        )
        widget.sig_deregister_run_configuration_provider_requested.connect(
            lambda unsupported_extensions:
                run.deregister_run_configuration_provider(
                    self.NAME, unsupported_extensions
                )
        )

        # This is necessary to register run configs that were added before Run
        # is available
        for extension in widget.supported_run_extensions:
            run.register_run_configuration_provider(self.NAME, [extension])

        # Buttons creation
        run.create_run_button(
            RunContext.Cell,
            _("Run cell"),
            icon=self.create_icon('run_cell'),
            tip=_("Run current cell"),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_toolbar=True,
            add_to_menu=True
        )
        run.create_run_button(
            RunContext.Cell,
            _("Run cell and advance"),
            icon=self.create_icon('run_cell_advance'),
            tip=_("Run current cell and go to the next one"),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_toolbar=True,
            add_to_menu=True,
            extra_action_name=ExtraAction.Advance
        )
        run.create_run_button(
            RunContext.Cell,
            _("Re-run last cell"),
            tip=_("Re run last cell "),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu=True,
            re_run=True
        )
        run.create_run_button(
            RunContext.Selection,
            _("Run &selection or current line"),
            icon=self.create_icon('run_selection'),
            tip=_("Run selection or current line"),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_toolbar=True,
            add_to_menu=True,
            extra_action_name=ExtraAction.Advance,
        )
        run.create_run_button(
            RunContext.Selection,
            _("Run &to line"),
            tip=_("Run selection up to the current line"),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_toolbar=False,
            add_to_menu=True,
            context_modificator=SelectionContextModificator.ToLine
        )
        run.create_run_button(
            RunContext.Selection,
            _("Run &from line"),
            tip=_("Run selection from the current line"),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_toolbar=False,
            add_to_menu=True,
            context_modificator=SelectionContextModificator.FromLine
        )

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        widget = self.get_widget()
        run = self.get_plugin(Plugins.Run)
        run.deregister_run_configuration_provider(
            self.NAME, widget.supported_run_extensions
        )
        run.destroy_run_button(RunContext.Cell)
        run.destroy_run_button(
            RunContext.Cell,
            extra_action_name=ExtraAction.Advance
        )
        run.destroy_run_button(RunContext.Cell, re_run=True)
        run.destroy_run_button(
            RunContext.Selection,
            extra_action_name=ExtraAction.Advance
        )
        run.destroy_run_button(
            RunContext.Selection,
            context_modificator=SelectionContextModificator.ToLine
        )
        run.destroy_run_button(
            RunContext.Selection,
            context_modificator=SelectionContextModificator.FromLine
        )

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_mainmenu_available(self):
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)
        # ---- File menu ----
        # Print
        print_actions = [
            widget.print_preview_action,
            widget.print_action,
        ]
        for print_action in print_actions:
            mainmenu.add_item_to_application_menu(
                print_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Print,
                before_section=FileMenuSections.Close
            )

        # Close
        close_actions = [
            widget.close_action,
            widget.close_all_action
        ]
        for close_action in close_actions:
            mainmenu.add_item_to_application_menu(
                close_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Close,
                before_section=FileMenuSections.Restart
            )

        # Navigation
        if sys.platform == 'darwin':
            tab_navigation_actions = [
                widget.go_to_previous_file_action,
                widget.go_to_next_file_action
            ]
            for tab_navigation_action in tab_navigation_actions:
                mainmenu.add_item_to_application_menu(
                    tab_navigation_action,
                    menu_id=ApplicationMenus.File,
                    section=FileMenuSections.Navigation,
                    before_section=FileMenuSections.Restart
                )

        # Open section
        open_actions = [
            widget.open_action,
            widget.open_last_closed_action,
            widget.recent_file_menu,
        ]
        for open_action in open_actions:
            mainmenu.add_item_to_application_menu(
                open_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Open,
                before_section=FileMenuSections.Save
            )

        # Save section
        save_actions = [
            widget.save_action,
            widget.save_all_action,
            widget.save_as_action,
            widget.save_copy_as_action,
            widget.revert_action,
        ]
        for save_action in save_actions:
            mainmenu.add_item_to_application_menu(
                save_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Save,
                before_section=FileMenuSections.Print
            )

        # New Section
        mainmenu.add_item_to_application_menu(
            widget.new_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.New,
            before_section=FileMenuSections.Open
        )

        # ---- Edit menu ----
        edit_menu = mainmenu.get_application_menu(ApplicationMenus.Edit)
        edit_menu.aboutToShow.connect(widget.update_edit_menu)

        # UndoRedo section
        for action in [widget.undo_action, widget.redo_action]:
            mainmenu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.Edit,
                section=EditMenuSections.UndoRedo,
                before_section=EditMenuSections.Editor
            )

        # Copy section
        for action in [
                widget.cut_action, widget.copy_action, widget.paste_action,
                widget.selectall_action]:
            mainmenu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.Edit,
                section=EditMenuSections.Copy,
                before_section=EditMenuSections.Editor
            )

        # Editor section
        for edit_item in widget.edit_menu_actions:
            mainmenu.add_item_to_application_menu(
                edit_item,
                menu_id=ApplicationMenus.Edit,
                section=EditMenuSections.Editor
            )

        # ---- Search menu ----
        search_menu = mainmenu.get_application_menu(ApplicationMenus.Search)
        search_menu.aboutToShow.connect(widget.update_search_menu)

        for search_item in widget.search_menu_actions:
            mainmenu.add_item_to_application_menu(
                search_item,
                menu_id=ApplicationMenus.Search,
                section=SearchMenuSections.FindInText,
                before_section=SearchMenuSections.FindInFiles
            )

        # ---- Source menu ----
        source_menu = mainmenu.get_application_menu(
            ApplicationMenus.Source
        )
        source_menu.aboutToShow.connect(widget.refresh_formatter_name)

        # Cursor section
        source_menu_cursor_actions = [
            widget.previous_edit_cursor_action,
            widget.previous_cursor_action,
            widget.next_cursor_action,
        ]
        for cursor_item in source_menu_cursor_actions:
            mainmenu.add_item_to_application_menu(
                cursor_item,
                menu_id=ApplicationMenus.Source,
                section=SourceMenuSections.Cursor,
                before_section=SourceMenuSections.Formatting
            )

        # Formatting section
        source_menu_formatting_actions = [
            widget.eol_menu,
            widget.trailingspaces_action,
            widget.fixindentation_action,
            widget.formatting_action
        ]
        for formatting_item in source_menu_formatting_actions:
            mainmenu.add_item_to_application_menu(
                formatting_item,
                menu_id=ApplicationMenus.Source,
                section=SourceMenuSections.Formatting,
                before_section=SourceMenuSections.CodeAnalysis
            )

        # Options section
        source_menu_option_actions = widget.checkable_actions.values()
        for option_item in source_menu_option_actions:
            mainmenu.add_item_to_application_menu(
                option_item,
                menu_id=ApplicationMenus.Source,
                section=SourceMenuSections.Options,
                before_section=SourceMenuSections.Linting
            )

        # Linting section
        source_menu_linting_actions = [
            widget.todo_list_action,
            widget.warning_list_action,
            widget.previous_warning_action,
            widget.next_warning_action,
        ]
        for linting_item in source_menu_linting_actions:
            mainmenu.add_item_to_application_menu(
                linting_item,
                menu_id=ApplicationMenus.Source,
                section=SourceMenuSections.Linting,
                before_section=SourceMenuSections.Cursor
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_mainmenu_teardown(self):
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)
        # ---- File menu ----
        # Print
        print_actions = [
            widget.print_preview_action,
            widget.print_action,
        ]
        for print_action in print_actions:
            mainmenu.remove_item_from_application_menu(
                print_action,
                menu_id=ApplicationMenus.File
            )

        # Close
        close_actions = [
            widget.close_action,
            widget.close_all_action
        ]
        for close_action in close_actions:
            mainmenu.remove_item_from_application_menu(
                close_action,
                menu_id=ApplicationMenus.File
            )

        # Navigation
        if sys.platform == 'darwin':
            tab_navigation_actions = [
                widget.go_to_previous_file_action,
                widget.go_to_next_file_action
            ]
            for tab_navigation_action in tab_navigation_actions:
                mainmenu.remove_item_from_application_menu(
                    tab_navigation_action,
                    menu_id=ApplicationMenus.File
                )

        # Open section
        open_actions = [
            widget.open_action,
            widget.open_last_closed_action,
            widget.recent_file_menu,
        ]
        for open_action in open_actions:
            mainmenu.remove_item_from_application_menu(
                open_action,
                menu_id=ApplicationMenus.File
            )

        # Save section
        save_actions = [
            widget.save_action,
            widget.save_all_action,
            widget.save_as_action,
            widget.save_copy_as_action,
            widget.revert_action,
        ]
        for save_action in save_actions:
            mainmenu.remove_item_from_application_menu(
                save_action,
                menu_id=ApplicationMenus.File
            )

        # New Section
        mainmenu.remove_item_from_application_menu(
            widget.new_action,
            menu_id=ApplicationMenus.File
        )

        # ---- Edit menu ----
        edit_menu = mainmenu.get_application_menu(ApplicationMenus.Edit)
        edit_menu.aboutToShow.disconnect(widget.update_edit_menu)

        # UndoRedo section
        for action in [widget.undo_action, widget.redo_action]:
            mainmenu.remove_item_from_application_menu(
                action,
                menu_id=ApplicationMenus.Edit
            )

        # Copy section
        for action in [
                widget.cut_action, widget.copy_action, widget.paste_action,
                widget.selectall_action]:
            mainmenu.remove_item_from_application_menu(
                action,
                menu_id=ApplicationMenus.Edit
            )

        # Editor section
        for edit_item in widget.edit_menu_actions:
            mainmenu.remove_item_from_application_menu(
                edit_item,
                menu_id=ApplicationMenus.Edit
            )

        # ---- Search menu ----
        search_menu = mainmenu.get_application_menu(ApplicationMenus.Search)
        search_menu.aboutToShow.disconnect(widget.update_search_menu)

        for search_item in widget.search_menu_actions:
            mainmenu.remove_item_from_application_menu(
                search_item,
                menu_id=ApplicationMenus.Search
            )

        # ---- Source menu ----
        source_menu = mainmenu.get_application_menu(
            ApplicationMenus.Source
        )
        source_menu.aboutToShow.disconnect(widget.refresh_formatter_name)

        # Cursor section
        source_menu_cursor_actions = [
            widget.previous_edit_cursor_action,
            widget.previous_cursor_action,
            widget.next_cursor_action,
        ]
        for cursor_item in source_menu_cursor_actions:
            mainmenu.remove_item_from_application_menu(
                cursor_item,
                menu_id=ApplicationMenus.Source
            )

        # Formatting section
        source_menu_formatting_actions = [
            widget.eol_menu,
            widget.trailingspaces_action,
            widget.fixindentation_action,
            widget.formatting_action
        ]
        for formatting_item in source_menu_formatting_actions:
            mainmenu.remove_item_from_application_menu(
                formatting_item,
                menu_id=ApplicationMenus.Source
            )

        # Options section
        source_menu_option_actions = widget.checkable_actions.values()
        for option_item in source_menu_option_actions:
            mainmenu.remove_item_from_application_menu(
                option_item,
                menu_id=ApplicationMenus.Source
            )

        # Linting section
        source_menu_linting_actions = [
            widget.todo_list_action,
            widget.warning_list_action,
            widget.previous_warning_action,
            widget.next_warning_action,
        ]
        for linting_item in source_menu_linting_actions:
            mainmenu.remove_item_from_application_menu(
                linting_item,
                menu_id=ApplicationMenus.Source
            )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        widget = self.get_widget()
        toolbar = self.get_plugin(Plugins.Toolbar)
        file_toolbar_actions = [
            widget.new_action,
            widget.open_action,
            widget.save_action,
            widget.save_all_action,
            widget.create_new_cell
        ]
        for file_toolbar_action in file_toolbar_actions:
            toolbar.add_item_to_application_toolbar(
                file_toolbar_action,
                toolbar_id=ApplicationToolbars.File,
            )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        file_toolbar_actions = [
            EditorWidgetActions.NewFile,
            EditorWidgetActions.OpenFile,
            EditorWidgetActions.SaveFile,
            EditorWidgetActions.SaveAll,
            EditorWidgetActions.NewCell
        ]
        for file_toolbar_action_id in file_toolbar_actions:
            toolbar.remove_item_from_application_toolbar(
                file_toolbar_action_id,
                toolbar_id=ApplicationToolbars.File,
            )

    @on_plugin_available(plugin=Plugins.Completions)
    def on_completions_available(self):
        widget = self.get_widget()
        completions = self.get_plugin(Plugins.Completions)

        widget.sig_after_configuration_update_requested.connect(
            completions.after_configuration_update
        )
        self.sig_file_opened_closed_or_updated.connect(
            completions.file_opened_closed_or_updated
        )

        completions.sig_language_completions_available.connect(
            widget.register_completion_capabilities)
        completions.sig_open_file.connect(widget.load)
        completions.sig_stop_completions.connect(
            widget.stop_completion_services)

    @on_plugin_teardown(plugin=Plugins.Completions)
    def on_completions_teardown(self):
        widget = self.get_widget()
        completions = self.get_plugin(Plugins.Completions)

        widget.sig_after_configuration_update_requested.disconnect(
            completions.after_configuration_update
        )
        self.sig_file_opened_closed_or_updated.disconnect(
            completions.file_opened_closed_or_updated
        )

        completions.sig_language_completions_available.disconnect(
            widget.register_completion_capabilities)
        completions.sig_open_file.disconnect(widget.load)
        completions.sig_stop_completions.disconnect(
            widget.stop_completion_services)

    @on_plugin_available(plugin=Plugins.OutlineExplorer)
    def on_outlineexplorer_available(self):
        widget = self.get_widget()
        outline = self.get_plugin(Plugins.OutlineExplorer)
        outline_widget = outline.get_widget()

        widget.set_outlineexplorer(outline_widget)

    @on_plugin_teardown(plugin=Plugins.OutlineExplorer)
    def on_outlinexplorer_teardown(self):
        self.get_widget().set_outlineexplorer(None)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_available(self):
        widget = self.get_widget()
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        ipyconsole.register_spyder_kernel_call_handler(
            'cell_count', widget.handle_cell_count
        )
        ipyconsole.register_spyder_kernel_call_handler(
            'current_filename', widget.handle_current_filename
        )
        ipyconsole.register_spyder_kernel_call_handler(
            'get_file_code', widget.handle_get_file_code
        )
        ipyconsole.register_spyder_kernel_call_handler(
            'run_cell', widget.handle_run_cell
        )

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        ipyconsole.unregister_spyder_kernel_call_handler('cell_count')
        ipyconsole.unregister_spyder_kernel_call_handler('current_filename')
        ipyconsole.unregister_spyder_kernel_call_handler('get_file_code')
        ipyconsole.unregister_spyder_kernel_call_handler('run_cell')

    @on_plugin_available(plugin=Plugins.Switcher)
    def on_switcher_available(self):
        switcher = self.get_plugin(Plugins.Switcher)
        self.get_widget().set_switcher(switcher)

    @on_plugin_teardown(plugin=Plugins.Switcher)
    def on_switcher_teardown(self):
        self.get_widget().set_switcher(None)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font(SpyderFontType.Monospace)
        self.get_widget().update_font(font)

    def on_mainwindow_visible(self):
        widget = self.get_widget()
        widget.restore_scrollbar_position()

    def can_close(self):
        editorstack = self.get_widget().editorstacks[0]
        return editorstack.save_if_changed(cancelable=True)

    def on_close(self, cancelable=False):
        widget = self.get_widget()

        if not self.get_widget().get_active_project_path():
            filenames = widget.get_filenames()
            self.set_conf('filenames', filenames)

    # ---- Public API
    # ------------------------------------------------------------------------
    def get_codeeditor_for_filename(self, filename):
        """
        Get `CodeEditor` instance associated with the given filename.

        Parameters
        ----------
        filename : str
            File path associated with a CodeEditor instance.

        Returns
        -------
        spyder.plugins.editor.codeeditor.CodeEditor
            `CodeEditor` associated with the given filename.
        """
        return self.get_widget().get_editor(filename)

    def refresh(self):
        """
        Refresh main widget.
        """
        self.get_widget().refresh()

    def load(self, *args, **kwargs):
        """
        Load a file or a group of files.

        Parameters
        ----------
        filenames: Optional[list]
            Filenames to load.
        goto: Optional[int]
            If goto is not None, it represents a line to go to. Used alongside
            `start_column` and `end_column`. Alternatively, the first match of
            `word` is used as a position.
        word: Optional[str]
            The `word` to use to set the cursor position when using `goto`.
        editorwindow: Optional[spyder.plugins.editor.widgets.window.EditorMainWindow]  # noqa
            Load in the given editorwindow (useful when clicking in the Outline
            explorer with multiple editor windows).
        processevents: Optional[bool]
            Determines if `processEvents()` should be called at the end of this
            method (set to `False` to prevent keyboard events from creeping
            through to the editor while debugging).
        start_column: Optional[int]
            The start position in the line (goto)
        end_column: Optional[int]
            The length (so that the end position is `start_column` +
            `end_column`), when providing a `goto` line.
        set_focus: Optional[bool]
            If the opened file should gain focus. `True` by default.
        add_where: Optional[str]
            Position where to add the new file finfo (affects the files tab
            order). Possible values are: `start` to make the file the first and
             `end` (or any other value) to append.
        """
        return self.get_widget().load(*args, **kwargs)

    def load_edit(self, filename):
        """
        Load a `filename` passing to the base `load` method the `main_widget`
        as the `editorwindow` to force focus.

        Used by `spyder.plugins.outlineexplorer.plugin.[on_editor_available|on_editor_teardown]`  # noqa

        Parameters
        ----------
        filename: str
            Filename to load.
        """
        widget = self.get_widget()
        return self.get_widget().load(filenames=filename, editorwindow=widget)

    def load_edit_goto(self, filename, goto, word):
        """
        Load a `filename` and put the cursor in the line given by `goto` and
        `word`, passing to the `load` call the `main_widget` as the
        `editorwindow` to force focus.

        Used by `spyder.plugins.outlineexplorer.plugin.[on_editor_available|on_editor_teardown]`  # noqa

        Parameters
        ----------
        filename: str
            Filename to load.
        goto: int
            Represents a line to go to.
        word: str
            The `word` to use to set the cursor position when using `goto`.
        """
        widget = self.get_widget()
        return widget.load(
            filenames=filename, goto=goto, word=word, editorwindow=widget
        )

    def new(self, *args, **kwargs):
        """
        Create a new file.

        Parameters
        ----------
        fname: Optional[str]
            Name of the file to be created. The default is `None`.
            If `None`, `fname` will be named `untitledXX.py`. No actual file
            will be created until it is saved manually by the user.
        editorstack: Optional[spyder.plugins.editor.widgets.editorstack.EditorStack]  # noqa
            Reference to the `EditorStack` instance that will be used to:
                * Get `untitledXX.py` numbering for the file name.
                * Check if a file with the same name already exists and it is
                  closeable.
                * Set file as the current focused file.
            The default is `None`. If that's the case, the current
            `EditorStack` is used. See the `get_current_editorstack` method for
            more details.
        text: Optional[str]
            Base text content that will be added to the file. The default is
            `None`. If that's the case, the default content created will be 
            created via a template file. See
            `Preferences > Editor > Advanced settings > Edit template for new files`  # noqa
        """
        return self.get_widget().new(*args, **kwargs)

    def removed(self, filename):
        """
        Close file given his filename since it was removed.

        It's used, for instance, when a file was removed in the File or Project
        explorer plugins.

        Parameters
        ----------
        filename: str
            File path to be closed/removed.
        """
        return self.get_widget().removed(filename)

    def removed_tree(self, dirname):
        """
        Close files given a directory since it was removed.

        It's used, for instance, when a directory was removed in the File or
        Project explorer plugins.

        Parameters
        ----------
        dirname: str
            Base directory path of the files to be closed/removed.
        """
        return self.get_widget().removed_tree(dirname)

    def renamed(self, *args, **kwargs):
        """
        Propagate file rename to editor stacks and autosave component.

        This method is called when a file is renamed in the File or Project
        explorer plugins. The file may not be opened in the editor.

        Parameters
        ----------
        source: str
            Initial filename path.
        dest: str
            New filename path.
        editorstack_id_str: Optional[str]
            The default is `None`. If not, the `EditorStack` instance whose
            identity corresponds to `editorstack_id_str` **doesn't** perform
            the file rename operation.
        """
        return self.get_widget().renamed(*args, **kwargs)

    def renamed_tree(self, *args, **kwargs):
        """
        Propagate directory rename to editor stacks and autosave component.

        This is used when the directory was renamed in File or Project explorer
        plugins.

        Parameters
        ----------
        source: str
            Initial directory path.
        dest: str
            New directory path.
        """
        return self.get_widget().renamed_tree(*args, **kwargs)

    def add_supported_run_configuration(self, *args, **kwargs):
        """
        Add a run configuration schema supported by the Editor.

        Parameters
        ----------
        config : spyder.plugins.editor.api.run.EditorRunConfiguration
            New run configuration schema to be added.
        """
        return self.get_widget().add_supported_run_configuration(
            *args, **kwargs
        )

    def remove_supported_run_configuration(self, *args, **kwargs):
        """
        Remove a run configuration schema supported by the Editor.

        Parameters
        ----------
        config : spyder.plugins.editor.api.run.EditorRunConfiguration
            Run configuration schema to be removed.
        """
        return self.get_widget().remove_supported_run_configuration(
            *args, **kwargs
        )

    def get_current_editor(self):
        """
        Get current `CodeEditor` instance if available.

        Returns
        -------
        spyder.plugins.editor.codeeditor.CodeEditor
            `CodeEditor` instance focused or available.
        """
        return self.get_widget().get_current_editor()

    def get_current_editorstack(self):
        """
        Get current `EditorStack` instance if available.

        Returns
        -------
        spyder.plugins.editor.editorstack.EditorStack
            `EditorStack` instance focused or available.
        """
        return self.get_widget().get_current_editorstack()

    def get_focus_widget(self):
        """
        Return the widget to give focus to.

        This happens when plugin's main widget is raised to the top-level.

        Returns
        -------
        spyder.plugins.editor.codeeditor.CodeEditor
            `CodeEditor` instance focused or available.
        """
        return self.get_widget().get_focus_widget()

    def setup_open_files(self,  close_previous_files=True):
        """
        Open the list of saved files per project.

        Also, open any files that the user selected in the recovery dialog and
        setup toolbars and menus for 'New window' instances (i.e. it calls the
        `setup_other_windows` method).

        Parameters
        ----------
        close_previous_files : Optional[bool]
            If any previously open file should be closed. Default `True`.
        """
        widget = self.get_widget()
        outline = self.get_plugin(Plugins.OutlineExplorer, error=False)
        if outline:
            widget.setup_other_windows(self._main, outline)
        return self.get_widget().setup_open_files(
            close_previous_files=close_previous_files
        )

    def save_open_files(self,):
        """Save the list of open files."""
        return self.get_widget().save_open_files()

    def save(self, index=None, force=False):
        """
        Save file.

        Parameters
        ----------
        index : Optional[int]
            Index related to the file position in the current editorstack.
            The default is `None`, which uses the current file index.
        force : Optional[bool]
            Force save regardless of file state. The default is `False`.

        Returns
        -------
        bool
            `True` if the save operation was sucessfull. `False` otherwise.
        """
        return self.get_widget().save(index=None, force=False)

    def save_bookmark(self, slot_num):
        """
        Save current line and position as bookmark.

        Parameters
        ----------
        slot_num : int
        """
        return self.get_widget().save_bookmark(slot_num)

    def load_bookmark(self, slot_num):
        """
        Set cursor to bookmarked file and position.

        Parameters
        ----------
        slot_num : int
        """
        return self.get_widget().load_bookmark(slot_num)

    def edit_template(self):
        """Edit `New file` template."""
        return self.get_widget().edit_template()

    def get_current_filename(self):
        """Get current editor 'filename'."""
        return self.get_widget().get_current_filename()

    def get_filenames(self):
        """
        Get list with all open files.

        Returns
        -------
        list
            A list with the names of all files currently opened in
            the editorstack.
        """
        return self.get_widget().get_filenames()

    def close_file(self):
        """Close current file."""
        return self.get_widget().close_file()

    def close_file_from_name(self, filename):
        """
        Close file from its name.

        Parameters
        ----------
        filename : str
            Filename to be closed.
        """
        return self.get_widget().close_file_from_name(filename)

    def close_all_files(self):
        """Close all opened files."""
        return self.get_widget().close_all_files()

    def go_to_line(self, line=None):
        """
        Open 'go to line' dialog.

        Parameters
        ----------
        line : Optional[int]
            Line to use for programatic calls without showing the dialog. The
            default is `None`.
        """
        return self.get_widget().go_to_line(line=line)

    def set_current_filename(self, *args, **kwargs):
        """
        Set current filename.

        Returns
        -------
        spyder.plugins.editor.codeeditor.CodeEditor
            The associated `CodeEditor` instance.
        """
        return self.get_widget().set_current_filename(*args, **kwargs)

    def set_current_project_path(self, root_path=None):
        """
        Set the current active project root path.

        Parameters
        ----------
        root_path: Optional[str]
            Path to current project root path. Default is `None`.
        """
        return self.get_widget().set_current_project_path(root_path=root_path)

    # ---- Private API
    # ------------------------------------------------------------------------
    # ---- Run related methods
    def _register_run_configuration_metadata(self, metadata):
        run = self.get_plugin(Plugins.Run, error=False)
        if run is not None:
            run.register_run_configuration_metadata(
                self.get_widget(), metadata
            )

    def _deregister_run_configuration_metadata(self, file_id):
        run = self.get_plugin(Plugins.Run, error=False)
        if run is not None:
            run.deregister_run_configuration_metadata(file_id)

    def _get_currently_selected_run_configuration(self):
        run = self.get_plugin(Plugins.Run, error=False)
        if run is not None:
            return run.get_currently_selected_configuration()

    def _switch_focused_run_configuration(self, file_id):
        run = self.get_plugin(Plugins.Run, error=False)
        if run is not None:
            run.switch_focused_run_configuration(file_id)

    # ---- Completions related methods
    def _register_file_completions(self, language, filename, codeeditor):
        completions = self.get_plugin(Plugins.Completions, error=False)
        status = None
        fallback_only = False
        if completions is not None:
            status = (
                completions.start_completion_services_for_language(
                    language.lower()
                )
            )
            completions.register_file(
                language.lower(), filename, codeeditor
            )
            fallback_only = completions.is_fallback_only(language.lower())
        return (status, fallback_only)

    def _send_completions_request(self, language, request, params):
        completions = self.get_plugin(Plugins.Completions, error=False)
        if completions is not None:
            completions.send_request(language, request, params)

    def _after_configuration_update(self, config):
        completions = self.get_plugin(Plugins.Completions, error=False)
        if completions is not None:
            completions.after_configuration_update(config)

    # ---- Projects related methods
    def _start_project_workspace_services(self):
        projects = self.get_plugin(Plugins.Projects, error=False)
        if projects is not None:
            projects.start_workspace_services()

    def _get_project_filenames(self):
        if self.get_widget().get_active_project_path():
            projects = self.get_plugin(Plugins.Projects, error=False)
            return projects.get_project_filenames()

    def _on_project_loaded(self, path):
        self.get_widget().update_active_project_path(path)

    def _on_project_closed(self):
        self.get_widget().update_active_project_path(None)

    # ---- Debugger related methods
    def _debugger_close_file(self, filename):
        debugger = self.get_plugin(Plugins.Debugger, error=False)
        if debugger is None:
            return True
        return debugger.can_close_file(filename)
