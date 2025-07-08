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
from typing import Dict, Optional, Tuple

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin, SpyderPluginV2
from spyder.api.translations import _
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.widgets.menus import SpyderMenu, MENU_SEPARATOR
from spyder.app import SHORTCUT_EXE
from spyder.config.base import (get_module_path, get_debug_level,
                                running_under_pytest)
from spyder.plugins.application.confpage import ApplicationConfigPage
from spyder.plugins.application.container import (
    ApplicationActions, ApplicationContainer, ApplicationPluginMenus)
from spyder.plugins.console.api import ConsoleActions
from spyder.plugins.editor.api.actions import EditorWidgetActions
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, FileMenuSections, HelpMenuSections, ToolsMenuSections)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import add_actions


class Application(SpyderPluginV2):
    NAME = 'application'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [
        Plugins.Editor,
        Plugins.Help,
        Plugins.IPythonConsole,
        Plugins.MainMenu,
        Plugins.StatusBar,
        Plugins.Toolbar,
        Plugins.UpdateManager,
    ]
    CONTAINER_CLASS = ApplicationContainer
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_WIDGET_CLASS = ApplicationConfigPage
    CAN_BE_DISABLED = False

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)
        self.focused_plugin: Optional[SpyderDockablePlugin] = None
        self.file_action_enabled: Dict[Tuple[str, str], bool] = {}

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
        container.sig_save_copy_as_requested.connect(self.save_copy_as)
        container.sig_revert_file_requested.connect(self.revert_file)
        container.sig_close_file_requested.connect(self.close_file)
        container.sig_close_all_requested.connect(self.close_all)
        container.set_window(self._window)
        self.sig_focused_plugin_changed.connect(self._update_focused_plugin)

    # --------------------- PLUGIN INITIALIZATION -----------------------------
    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipythonconsole_available(self):
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

        if self.is_plugin_enabled(Plugins.IPythonConsole):
            if self.is_plugin_available(Plugins.IPythonConsole):
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
                toolbar_id=ApplicationToolbars.File,
                before=EditorWidgetActions.NewCell
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
            container.save_as_action,
            container.save_copy_as_action,
            container.revert_action
        ]
        for save_action in save_actions:
            mainmenu.add_item_to_application_menu(
                save_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Save,
                before_section=FileMenuSections.Print
            )

        # Close section
        close_actions = [
            container.close_file_action,
            container.close_all_action
        ]
        for close_action in close_actions:
            mainmenu.add_item_to_application_menu(
                close_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Close,
                before_section=FileMenuSections.Restart
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
            section=ToolsMenuSections.Managers,
            before_section=ToolsMenuSections.Preferences,
        )

        if get_debug_level() >= 2:
            mainmenu.add_item_to_application_menu(
                self.debug_logs_menu,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before_section=HelpMenuSections.About,
            )

    def _populate_help_menu(self):
        """Add base actions and menus to the Help menu."""
        self._populate_help_menu_documentation_section()
        self._populate_help_menu_support_section()
        self._populate_help_menu_about_section()

    def _populate_help_menu_documentation_section(self):
        """Add base Spyder documentation actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)
        ipython_documentation_submenu = None

        if ipythonconsole:
            from spyder.plugins.ipythonconsole.api import (
                IPythonConsoleWidgetMenus
            )
            ipython_documentation_submenu = (
                IPythonConsoleWidgetMenus.Documentation
            )
        for documentation_action in [
                self.documentation_action, self.video_action]:
            mainmenu.add_item_to_application_menu(
                documentation_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.ExternalDocumentation,
                before=ipython_documentation_submenu,
                before_section=HelpMenuSections.Support,
            )

    def _populate_help_menu_support_section(self):
        """Add Spyder base support actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for support_action in [
            self.trouble_action,
            self.support_group_action,
            self.dependencies_action,
            self.report_action,
        ]:
            mainmenu.add_item_to_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before_section=HelpMenuSections.About,
            )

    def _populate_help_menu_about_section(self):
        """Create Spyder base about actions."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for about_action in [
            self.get_action(ApplicationActions.HelpSpyderAction),
            self.about_action,
        ]:
            mainmenu.add_item_to_application_menu(
                about_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.About,
            )

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
            ApplicationActions.SaveCopyAs,
            ApplicationActions.RevertFile,
            ApplicationActions.CloseFile,
            ApplicationActions.CloseAll,
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

    def _update_focused_plugin(
        self, plugin: Optional[SpyderDockablePlugin]
    ) -> None:
        """
        Update which plugin has currently focus.

        This function is called if another plugin gets keyboard focus.
        """
        self.focused_plugin = plugin
        self._update_file_actions()

    def _update_file_actions(self) -> None:
        """
        Update which file actions are enabled.

        File actions are enabled depending on whether the plugin that would
        currently process the file action has enabled it or not.
        """
        plugin = self.focused_plugin
        if not plugin or not getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin = self.get_plugin(Plugins.Editor, error=False)
        if plugin:
            for action_name in [
                ApplicationActions.NewFile,
                ApplicationActions.OpenLastClosed,
                ApplicationActions.SaveFile,
                ApplicationActions.SaveAll,
                ApplicationActions.SaveAs,
                ApplicationActions.SaveCopyAs,
                ApplicationActions.RevertFile,
                ApplicationActions.CloseFile,
                ApplicationActions.CloseAll,
            ]:
                action = self.get_action(action_name)
                key = (plugin.NAME, action_name)
                state = self.file_action_enabled.get(key, True)
                action.setEnabled(state)

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
        python = SHORTCUT_EXE or sys.executable

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

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then create a new
        file in that plugin. Otherwise, create a new file in the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.create_new_file()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.new()

    def open_file_using_dialog(self) -> None:
        """
        Show Open File dialog and open the selected file.

        Try asking the plugin that currently has focus for the name of the
        displayed file and whether it is a temporary file. If that does not
        work, ask the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin:
            filename = plugin.get_current_filename()
        else:
            filename = None

        if filename is None and self.is_plugin_available(Plugins.Editor):
            plugin = self.get_plugin(Plugins.Editor)
            filename = plugin.get_current_filename()

        if filename is not None and not plugin.current_file_is_temporary():
            basedir = osp.dirname(filename)
        else:
            basedir = getcwd_or_home()

        self.get_container().open_file_using_dialog(filename, basedir)

    def open_file_in_plugin(self, filename: str) -> None:
        """
        Open given file in a suitable plugin.

        Go through all plugins and open the file in the first plugin that
        registered the extension of the given file name. If none is found,
        then open the file in the Editor plugin.
        """
        ext = osp.splitext(filename)[1]
        for plugin_name in PLUGIN_REGISTRY:
            if PLUGIN_REGISTRY.is_plugin_available(plugin_name):
                plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
                if (
                    isinstance(plugin, SpyderDockablePlugin)
                    and ext in plugin.FILE_EXTENSIONS
                ):
                    plugin.switch_to_plugin()
                    plugin.open_file(filename)
                    return

        if self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.load(filename)

    def open_last_closed_file(self) -> None:
        """
        Open the last closed file again.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then open the
        last closed file in that plugin. Otherwise, open the last closed file
        in the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.open_last_closed_file()
        elif self.is_plugin_available(Plugins.Editor):
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

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then save the
        current file in that plugin. Otherwise, save the current file in the
        Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.save_file()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save()

    def save_file_as(self) -> None:
        """
        Save current file under a different name.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then save the
        current file in that plugin under a different name. Otherwise, save
        the current file in the Editor plugin under a different name.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.save_file_as()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save_as()

    def save_copy_as(self) -> None:
        """
        Save copy of current file under a different name.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then save a copy of
        the current file in that plugin under a different name. Otherwise, save
        a copy of the current file in the Editor plugin under a different name.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.save_copy_as()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save_copy_as()

    def save_all(self) -> None:
        """
        Save all files.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then save all files
        in that plugin. Otherwise, save all files in the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.save_all()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.save_all()

    def revert_file(self) -> None:
        """
        Revert current file to the version on disk.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then revert the
        current file in that plugin to the version stored on disk. Otherwise,
        revert the current file in the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.revert_file()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.revert_file()

    def close_file(self) -> None:
        """
        Close the current file.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then close the
        current file in that plugin. Otherwise, close the current file in the
        Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.close_file()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.close_file()

    def close_all(self) -> None:
        """
        Close all opened files in the current plugin.

        If the plugin that currently has focus, has its
        `CAN_HANDLE_FILE_ACTIONS` attribute set to `True`, then close all
        files in that plugin. Otherwise, close all files in the Editor plugin.
        """
        plugin = self.focused_plugin
        if plugin and getattr(plugin, 'CAN_HANDLE_FILE_ACTIONS', False):
            plugin.close_all()
        elif self.is_plugin_available(Plugins.Editor):
            editor = self.get_plugin(Plugins.Editor)
            editor.close_all_files()

    def enable_file_action(
        self,
        action_name: str,
        enabled: bool,
        plugin: str
    ) -> None:
        """
        Enable or disable file actions for a given plugin.

        Parameters
        ----------
        action_name : str
            The name of the action to be enabled or disabled. These names
            are listed in ApplicationActions, for instance "New file"
        enabled : bool
            True to enable the action, False to disable it.
        plugin : str
            The name of the plugin for which the save action needs to be
            enabled or disabled.
        """
        self.file_action_enabled[(plugin, action_name)] = enabled
        self._update_file_actions()

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
