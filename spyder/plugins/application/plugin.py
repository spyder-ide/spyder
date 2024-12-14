# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Application Plugin.
"""

# Standard library imports
import os
import os.path as osp
import subprocess
import sys

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.widgets.menus import SpyderMenu, MENU_SEPARATOR
from spyder.config.base import (get_module_path, get_debug_level,
                                running_under_pytest)
from spyder.plugins.application.confpage import ApplicationConfigPage
from spyder.plugins.application.container import (
    ApplicationActions, ApplicationContainer, ApplicationPluginMenus)
from spyder.plugins.console.api import ConsoleActions
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, FileMenuSections, HelpMenuSections, ToolsMenuSections)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import add_actions


class Application(SpyderPluginV2):
    NAME = 'application'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Help, Plugins.MainMenu, Plugins.Shortcuts,
                Plugins.Editor, Plugins.StatusBar, Plugins.UpdateManager,
                Plugins.Toolbar]
    CONTAINER_CLASS = ApplicationContainer
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_WIDGET_CLASS = ApplicationConfigPage
    CAN_BE_DISABLED = False

    @staticmethod
    def get_name():
        return _('Application')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('genprefs')

    @staticmethod
    def get_description():
        return _('Provide main application base actions.')

    def on_initialize(self):
        container = self.get_container()
        container.sig_report_issue_requested.connect(self.report_issue)
        container.sig_new_file_requested.connect(self.create_new_file)
        container.sig_open_file_in_plugin_requested.connect(
            self.open_file_in_plugin
        )
        container.sig_open_file_using_dialog_requested.connect(
            self.open_file_using_dialog
        )
        container.sig_open_last_closed_requested.connect(
            self.open_last_closed_file
        )
        container.sig_save_file_requested.connect(self.save_file)
        container.sig_save_all_requested.connect(self.save_all)
        container.sig_save_file_as_requested.connect(self.save_file_as)
        container.set_window(self._window)

    # --------------------- PLUGIN INITIALIZATION -----------------------------
    @on_plugin_available(plugin=Plugins.Shortcuts)
    def on_shortcuts_available(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self._populate_help_menu()

    @on_plugin_available(plugin=Plugins.Console)
    def on_console_available(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self.report_action.setVisible(True)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        self._populate_file_menu()
        self._populate_tools_menu()

        if self.is_plugin_enabled(Plugins.Shortcuts):
            if self.is_plugin_available(Plugins.Shortcuts):
                self._populate_help_menu()
        else:
            self._populate_help_menu()

        if not self.is_plugin_available(Plugins.Console):
            self.report_action.setVisible(False)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_container().sig_load_log_file.connect(editor.load)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        statusbar = self.get_plugin(Plugins.StatusBar)
        inapp_appeal_status = self.get_container().inapp_appeal_status
        statusbar.add_status_widget(inapp_appeal_status)

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        for action in [
            container.new_action,
            container.open_action,
            container.save_action,
            container.save_all_action
        ]:
            toolbar.add_item_to_application_toolbar(
                action,
                toolbar_id=ApplicationToolbars.File
            )

    # -------------------------- PLUGIN TEARDOWN ------------------------------
    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_container().sig_load_log_file.disconnect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Console)
    def on_console_teardown(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self.report_action.setVisible(False)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        self._depopulate_file_menu()
        self._depopulate_tools_menu()
        self._depopulate_help_menu()
        self.report_action.setVisible(False)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        statusbar = self.get_plugin(Plugins.StatusBar)
        inapp_appeal_status = self.get_container().inapp_appeal_status
        statusbar.remove_status_widget(inapp_appeal_status.ID)

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        for action in [
            ApplicationActions.NewFile,
            ApplicationActions.OpenFile,
            ApplicationActions.SaveFile,
            ApplicationActions.SaveAll
        ]:
            toolbar.remove_item_from_application_toolbar(
                action,
                toolbar_id=ApplicationToolbars.File
            )

    def on_close(self, _unused=True):
        self.get_container().on_close()

    def on_mainwindow_visible(self):
        """Actions after the mainwindow in visible."""
        container = self.get_container()

        # Show dialog with missing dependencies
        if not running_under_pytest():
            container.compute_dependencies()

        # Handle DPI scale and window changes to show a restart message.
        # Don't activate this functionality on macOS because it's being
        # triggered in the wrong situations.
        # See spyder-ide/spyder#11846
        if not sys.platform == 'darwin':
            window = self._window.windowHandle()
            window.screenChanged.connect(container.handle_new_screen)
            screen = self._window.windowHandle().screen()
            container.current_dpi = screen.logicalDotsPerInch()
            screen.logicalDotsPerInchChanged.connect(
                container.show_dpi_change_message)

        # Show appeal the fifth and 25th time Spyder starts
        spyder_runs = self.get_conf("spyder_runs_for_appeal", default=1)
        if spyder_runs in [5, 25]:
            container.inapp_appeal_status.show_appeal()

            # Increase counting in one to not get stuck at this point.
            # Fixes spyder-ide/spyder#22457
            self.set_conf("spyder_runs_for_appeal", spyder_runs + 1)
        else:
            if spyder_runs < 25:
                self.set_conf("spyder_runs_for_appeal", spyder_runs + 1)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _populate_file_menu(self):
        container = self.get_container()
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # New section
        mainmenu.add_item_to_application_menu(
            container.new_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.New,
            before_section=FileMenuSections.Open
        )

        # Open section
        open_actions = [
            container.open_action,
            container.open_last_closed_action,
            container.recent_files_menu,
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
            container.save_action,
            container.save_all_action,
            container.save_as_action
        ]
        for save_action in save_actions:
            mainmenu.add_item_to_application_menu(
                save_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Save,
                before_section=FileMenuSections.Print
            )

        # Restart section
        mainmenu.add_item_to_application_menu(
            self.restart_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart
        )
        mainmenu.add_item_to_application_menu(
            self.restart_debug_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart
        )

    def _populate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.user_env_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools)

        if get_debug_level() >= 2:
            mainmenu.add_item_to_application_menu(
                self.debug_logs_menu,
                menu_id=ApplicationMenus.Tools,
                section=ToolsMenuSections.Extras)

    def _populate_help_menu(self):
        """Add base actions and menus to the Help menu."""
        self._populate_help_menu_documentation_section()
        self._populate_help_menu_support_section()
        self._populate_help_menu_about_section()

    def _populate_help_menu_documentation_section(self):
        """Add base Spyder documentation actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts_summary_action = None

        if shortcuts:
            from spyder.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_summary_action = ShortcutActions.ShortcutSummaryAction
        for documentation_action in [
                self.documentation_action, self.video_action]:
            mainmenu.add_item_to_application_menu(
                documentation_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Documentation,
                before=shortcuts_summary_action,
                before_section=HelpMenuSections.Support)

    def _populate_help_menu_support_section(self):
        """Add Spyder base support actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for support_action in [
            self.trouble_action,
            self.report_action,
            self.dependencies_action,
            self.support_group_action,
            self.get_action(ApplicationActions.HelpSpyderAction),
        ]:
            mainmenu.add_item_to_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before_section=HelpMenuSections.ExternalDocumentation
            )

    def _populate_help_menu_about_section(self):
        """Create Spyder base about actions."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.about_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.About)

    @property
    def _window(self):
        return self.main.window()

    def _depopulate_help_menu(self):
        self._depopulate_help_menu_documentation_section()
        self._depopulate_help_menu_support_section()
        self._depopulate_help_menu_about_section()

    def _depopulate_help_menu_documentation_section(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for documentation_action in [
                ApplicationActions.SpyderDocumentationAction,
                ApplicationActions.SpyderDocumentationVideoAction]:
            mainmenu.remove_item_from_application_menu(
                documentation_action,
                menu_id=ApplicationMenus.Help)

    def _depopulate_help_menu_support_section(self):
        """Remove Spyder base support actions from the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for support_action in [
                ApplicationActions.SpyderTroubleshootingAction,
                ConsoleActions.SpyderReportAction,
                ApplicationActions.SpyderDependenciesAction,
                ApplicationActions.SpyderSupportAction]:
            mainmenu.remove_item_from_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help)

    def _depopulate_help_menu_about_section(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ApplicationActions.SpyderAbout,
            menu_id=ApplicationMenus.Help)

    def _depopulate_file_menu(self):
        container = self.get_container()
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for action_id in [
            ApplicationActions.NewFile,
            ApplicationActions.OpenFile,
            ApplicationActions.OpenLastClosed,
            container.recent_file_menu,
            ApplicationActions.SaveFile,
            ApplicationActions.SaveAll,
            ApplicationActions.SaveAs,
            ApplicationActions.SpyderRestart,
            ApplicationActions.SpyderRestartDebug
        ]:
            mainmenu.remove_item_from_application_menu(
                action_id,
                menu_id=ApplicationMenus.File)

    def _depopulate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ApplicationActions.SpyderUserEnvVariables,
            menu_id=ApplicationMenus.Tools)

        if get_debug_level() >= 2:
            mainmenu.remove_item_from_application_menu(
                ApplicationPluginMenus.DebugLogsMenu,
                menu_id=ApplicationMenus.Tools)

    # ---- Public API
    # ------------------------------------------------------------------------
    def get_application_context_menu(self, parent=None):
        """
        Return menu with the actions to be shown by the Spyder context menu.
        """
        tutorial_action = None
        shortcuts_action = None

        help_plugin = self.get_plugin(Plugins.Help)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        menu = SpyderMenu(parent=parent)
        actions = [self.documentation_action]
        # Help actions
        if help_plugin:
            from spyder.plugins.help.plugin import HelpActions
            tutorial_action = help_plugin.get_action(
                HelpActions.ShowSpyderTutorialAction)
            actions += [tutorial_action]
        # Shortcuts actions
        if shortcuts:
            from spyder.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_action = shortcuts.get_action(
                ShortcutActions.ShortcutSummaryAction)
            actions.append(shortcuts_action)
        # Application actions
        actions += [MENU_SEPARATOR, self.about_action]

        add_actions(menu, actions)

        return menu

    def report_issue(self):
        if self.is_plugin_available(Plugins.Console):
            console = self.get_plugin(Plugins.Console)
            console.report_issue()

    def apply_settings(self):
        """Apply applications settings."""
        self._main.apply_settings()

    @Slot()
    def restart(self, reset=False, close_immediately=False):
        """
        Quit and Restart Spyder application.

        If reset True it allows to reset spyder on restart.
        """
        # Get console plugin reference to call the quit action
        console = self.get_plugin(Plugins.Console)

        # Get start path to use in restart script
        spyder_start_directory = get_module_path('spyder')
        restart_script = osp.join(spyder_start_directory, 'app', 'restart.py')

        # Get any initial argument passed when spyder was started
        # Note: Variables defined in bootstrap.py and spyder/app/start.py
        env = os.environ.copy()
        bootstrap_args = env.pop('SPYDER_BOOTSTRAP_ARGS', None)
        spyder_args = env.pop('SPYDER_ARGS')

        # Get current process and python running spyder
        pid = os.getpid()
        python = sys.executable

        # Check if started with bootstrap.py
        if bootstrap_args is not None:
            spyder_args = bootstrap_args
            is_bootstrap = True
        else:
            is_bootstrap = False

        # Pass variables as environment variables (str) to restarter subprocess
        env['SPYDER_ARGS'] = spyder_args
        env['SPYDER_PID'] = str(pid)
        env['SPYDER_IS_BOOTSTRAP'] = str(is_bootstrap)

        # Build the command and popen arguments depending on the OS
        if os.name == 'nt':
            # Hide flashing command prompt
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            shell = False
        else:
            startupinfo = None
            shell = True

        command = '"{0}" "{1}"'
        command = command.format(python, restart_script)

        try:
            if self.main.closing(True, close_immediately=close_immediately):
                subprocess.Popen(command, shell=shell, env=env,
                                 startupinfo=startupinfo)
                console.quit()
        except Exception as error:
            # If there is an error with subprocess, Spyder should not quit and
            # the error can be inspected in the internal console
            print(error)  # spyder: test-skip
            print(command)  # spyder: test-skip

    def create_new_file(self) -> None:
        """
        Create new file in a suitable plugin.

        For the moment, this creates a new file in the Editor plugin.
        """
        plugin = self.get_plugin(Plugins.Editor)
        plugin.new()

    def open_file_using_dialog(self) -> None:
        """
        Show Open File dialog and open the selected file.

        Ask Editor plugin for the name of the currently displayed file and
        whether it is a temporary file, and then call the function with the
        same name in the container widget to do the actual work.
        """
        filename = None
        basedir = getcwd_or_home()

        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            filename = editor.get_current_filename()
            if not editor.current_file_is_temporary():
                basedir = osp.dirname(filename)

        self.get_container().open_file_using_dialog(filename, basedir)

    def open_file_in_plugin(self, filename: str) -> None:
        """
        Open given file in a suitable plugin.

        For the moment, this opens the file in the Editor plugin.
        """
        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.load(filename)

    def open_last_closed_file(self) -> None:
        """
        Open the last closed file again.

        For the moment, forward the request to the Editor plugin.
        """
        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.open_last_closed()

    def add_recent_file(self, fname: str) -> None:
        """
        Add file to list of recent files.

        This function adds the given file name to the list of recent files,
        which is used in the `File > Open recent` menu. The function ensures
        that the list has no duplicates and it is no longer than the maximum
        length.
        """
        self.get_container().add_recent_file(fname)

    def save_file(self) -> None:
        """
        Save current file.

        For the moment, this instructs the Editor plugin to save the current
        file.
        """
        editor = self.get_plugin(Plugins.Editor)
        editor.save()

    def save_file_as(self) -> None:
        """
        Save current file in Editor plugin under a different name.
        """
        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save_as()

    def save_all(self) -> None:
        """
        Save all files.

        Save all files in the Editor plugin.
        """
        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save_all()

    def enable_save_action(self, state: bool) -> None:
        """
        Enable or disable save action.

        Parameters
        ----------
        state : bool
            True to enable save action, False to disable it.
        """
        self.get_container().save_action.setEnabled(state)

    def enable_save_all_action(self, state: bool) -> None:
        """
        Enable or disable "Save All" action.

        Parameters
        ----------
        state : bool
            True to enable "Save All" action, False to disable it.
        """
        self.get_container().save_all_action.setEnabled(state)

    @property
    def documentation_action(self):
        """Open Spyder's Documentation in the browser."""
        return self.get_container().documentation_action

    @property
    def video_action(self):
        """Open Spyder's video documentation in the browser."""
        return self.get_container().video_action

    @property
    def trouble_action(self):
        """Open Spyder's troubleshooting documentation in the browser."""
        return self.get_container().trouble_action

    @property
    def dependencies_action(self):
        """Show Spyder's Dependencies dialog box."""
        return self.get_container().dependencies_action

    @property
    def support_group_action(self):
        """Open Spyder's Google support group in the browser."""
        return self.get_container().support_group_action

    @property
    def about_action(self):
        """Show Spyder's About dialog box."""
        return self.get_container().about_action

    @property
    def user_env_action(self):
        """Show Spyder's Windows user env variables dialog box."""
        return self.get_container().user_env_action

    @property
    def restart_action(self):
        """Restart Spyder action."""
        return self.get_container().restart_action

    @property
    def restart_debug_action(self):
        """Restart Spyder in DEBUG mode action."""
        return self.get_container().restart_debug_action

    @property
    def report_action(self):
        """Restart Spyder action."""
        return self.get_container().report_action

    @property
    def debug_logs_menu(self):
        return self.get_container().get_menu(
            ApplicationPluginMenus.DebugLogsMenu)
