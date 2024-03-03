# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Plugin"""

import logging
import sys

from qtpy.QtCore import Signal

from spyder.api.translations import _
from spyder.api.config.fonts import SpyderFontType
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
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

        # TODO: Move these connections to the `on_<>_available` of each plugin?
        # ---- Completions related signals
        widget.sig_after_configuration_update_requested.connect(
            self._after_configuration_update
        )

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

        # ---- Run plugin config definitions
        widget.supported_run_extensions = [
            {
                'input_extension': 'py',
                'contexts': [
                    {'context': {'name': 'File'}, 'is_super': True},
                    {'context': {'name': 'Selection'}, 'is_super': False},
                    {'context': {'name': 'Cell'}, 'is_super': False}
                ]
            },
            {
                'input_extension': 'ipy',
                'contexts': [
                    {'context': {'name': 'File'}, 'is_super': True},
                    {'context': {'name': 'Selection'}, 'is_super': False},
                    {'context': {'name': 'Cell'}, 'is_super': False}
                ]
            },
        ]

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
        run.register_run_configuration_provider(
            self.NAME, widget.supported_run_extensions
        )

        # Buttons creation
        run.create_run_button(
            RunContext.Cell,
            _("Run cell"),
            icon=self.create_icon('run_cell'),
            tip=_("Run current cell\n[Use #%% to create cells]"),
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

        self.sig_file_opened_closed_or_updated.connect(
            completions.file_opened_closed_or_updated
        )

        # TODO: Seems like `update_client_status` is only availabel from the
        # LSP provider?
        # widget.sig_update_active_languages_requested.connect(
        #     completions.update_client_status
        # )

        # TODO: Should this be moved to the Completions plugin
        # as done with the console/internal console plugin connections?
        completions.sig_language_completions_available.connect(
            widget.register_completion_capabilities)
        completions.sig_open_file.connect(widget.load)
        completions.sig_editor_rpc.connect(widget._rpc_call)
        completions.sig_stop_completions.connect(
            widget.stop_completion_services)

    @on_plugin_teardown(plugin=Plugins.Completions)
    def on_completions_teardown(self):
        widget = self.get_widget()
        completions = self.get_plugin(Plugins.Completions)
        self.sig_file_opened_closed_or_updated.disconnect(
            completions.file_opened_closed_or_updated
        )

        # TODO: Seems like `update_client_status` is only availabel from the
        # LSP provider?
        # widget.sig_update_active_languages_requested.disconnect(
        #     completions.update_client_status
        # )
        # TODO: Should this be moved to the Completions plugin
        # as done with the console/internal console plugin connections?
        completions.sig_language_completions_available.disconnect(
            widget.register_completion_capabilities)
        completions.sig_open_file.disconnect(widget.load)
        completions.sig_editor_rpc.disconnect(widget._rpc_call)
        completions.sig_stop_completions.disconnect(
            widget.stop_completion_services)

    @on_plugin_available(plugin=Plugins.OutlineExplorer)
    def on_outlineexplorer_available(self):
        widget = self.get_widget()
        outline = self.get_plugin(Plugins.OutlineExplorer)
        outline_widget = outline.get_widget()

        widget.set_outlineexplorer(outline_widget)

        # TODO: Should the above be done from the Outline Explorer plugin
        # as done with the console/internal console plugin?
        outline_widget.edit_goto.connect(
            lambda filenames, goto, word:
                widget.load(
                    filenames=filenames,
                    goto=goto,
                    word=word,
                    editorwindow=widget
                )
        )
        outline_widget.edit.connect(
            lambda filenames:
                widget.load(filenames=filenames, editorwindow=self)
        )

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
        # TODO: Seems like the switcher for symbols is failing? Missing a check
        self.get_widget().set_switcher(switcher)

    @on_plugin_teardown(plugin=Plugins.Switcher)
    def on_switcher_teardown(self):
        self.get_widget().set_switcher(None)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        # TODO: Should this work as is done in the IPython console?

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        widget = self.get_widget()
        projects = self.get_plugin(Plugins.Projects)
        if projects.get_active_project_path():
            projects.set_project_filenames(
                [finfo.filename for finfo in widget.editorstacks[0].data]
            )

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font(SpyderFontType.Monospace)
        self.get_widget().update_font(font)

    def on_mainwindow_visible(self):
        widget = self.get_widget()
        widget.restore_scrollbar_position()
        # TODO: Something else?. The `setup_other_windows` needed to be done as
        # part of `setup_open_files` to prevent errors

    def can_close(self):
        editorstack = self.get_widget().editorstacks[0]
        return editorstack.save_if_changed(cancelable=True)

    def on_close(self, cancelable=False):
        widget = self.get_widget()

        if not self._get_active_project_path():
            filenames = widget.get_open_filenames()
            self.set_conf('filenames', filenames)

    # ---- Public API
    # ------------------------------------------------------------------------
    # TODO: Add docstrings for all methods in this section because they are
    # public API.
    def get_codeeditor_for_filename(self, filename):
        return self.get_widget()._get_editor(filename)

    def refresh(self):
        """
        Refresh main widget.
        """
        self.get_widget().refresh()

    def load(self, *args, **kwargs):
        return self.get_widget().load(*args, **kwargs)

    def new(self, *args, **kwargs):
        return self.get_widget().new(*args, **kwargs)

    def removed(self, *args, **kwargs):  # explorer plugin
        return self.get_widget().removed(*args, **kwargs)

    def removed_tree(self, *args, **kwargs):  # explorer plugin
        return self.get_widget().removed_tree(*args, **kwargs)

    def renamed(self, *args, **kwargs):  # explorer plugin
        return self.get_widget().renamed(*args, **kwargs)

    def renamed_tree(self, *args, **kwargs):  # explorer plugin
        return self.get_widget().renamed_tree(*args, **kwargs)

    def add_supported_run_configuration(self, *args, **kwargs):
        # external console plugin
        return self.get_widget().add_supported_run_configuration(
            *args, **kwargs
        )

    def remove_supported_run_configuration(self, *args, **kwargs):
        return self.get_widget().remove_supported_run_configuration(
            *args, **kwargs
        )

    def get_current_editor(self, *args, **kwargs):  # debugger plugin
        return self.get_widget().get_current_editor(*args, **kwargs)

    def get_current_editorstack(self, *args, **kwargs):
        return self.get_widget().get_current_editorstack()

    def get_focus_widget(self):
        return self.get_widget().get_focus_widget()

    def setup_open_files(self, *args, **kwargs):  # on_mainwindow_visible?
        # TODO: `setup_other_windows` called here to ensure is called after
        # toolbar `on_mainwindow_visible`
        widget = self.get_widget()
        outline = self.get_plugin(Plugins.OutlineExplorer, error=False)
        widget.setup_other_windows(self._main, outline)
        return self.get_widget().setup_open_files(*args, **kwargs)

    def save_open_files(self, *args, **kwargs):  # projects plugin
        return self.get_widget().save_open_files(*args, **kwargs)

    def save(self, *args, **kwargs):
        return self.get_widget().save(*args, **kwargs)

    def save_bookmark(self, *args, **kwargs):
        return self.get_widget().save_bookmark(*args, **kwargs)

    def load_bookmark(self, *args, **kwargs):
        return self.get_widget().load_bookmark(*args, **kwargs)

    def edit_template(self):
        return self.get_widget().edit_template()

    def get_current_filename(self):
        return self.get_widget().get_current_filename()

    def get_filenames(self):
        return self.get_widget().get_filenames()

    def get_open_filenames(self):
        return self.get_widget().get_open_filenames()

    def close_file(self):
        return self.get_widget().close_file()

    def close_file_from_name(self, *args, **kwargs):
        return self.get_widget().close_file_from_name(*args, **kwargs)

    def close_all_files(self):
        return self.get_widget().close_all_files()

    def go_to_line(self, *args, **kwargs):
        return self.get_widget().go_to_line(*args, **kwargs)

    def set_current_filename(self, *args, **kwargs):
        return self.get_widget().set_current_filename(*args, **kwargs)

    def set_current_project_path(self, *args, **kwargs):
        return self.get_widget().set_current_project_path(*args, **kwargs)

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
        if self._get_active_project_path():
            projects = self.get_plugin(Plugins.Projects, error=False)
            return projects.get_project_filenames()

    def _get_active_project_path(self):
        projects = self.get_plugin(Plugins.Projects, error=False)
        if projects is not None:
            return projects.get_active_project_path()

    # ---- Debugger related methods
    def _debugger_close_file(self, filename):
        debugger = self.get_plugin(Plugins.Debugger, error=False)
        if debugger is None:
            return True
        return debugger.can_close_file(filename)
