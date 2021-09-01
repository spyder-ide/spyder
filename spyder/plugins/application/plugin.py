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
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.config.base import (DEV, get_module_path, get_debug_level,
                                running_under_pytest)
from spyder.plugins.application.confpage import ApplicationConfigPage
from spyder.plugins.application.container import (
    ApplicationContainer, ApplicationPluginMenus, WinUserEnvDialog)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, FileMenuSections, HelpMenuSections, ToolsMenuSections)
from spyder.utils.qthelpers import add_actions

# Localization
_ = get_translation('spyder')


class Application(SpyderPluginV2):
    NAME = 'application'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Help, Plugins.MainMenu, Plugins.Shortcuts,
                Plugins.Editor]
    CONTAINER_CLASS = ApplicationContainer
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_WIDGET_CLASS = ApplicationConfigPage

    def get_name(self):
        return _('Application')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide main application base actions.')

    def on_initialize(self):
        container = self.get_container()
        container.sig_report_issue_requested.connect(self.report_issue)
        container.set_window(self._window)

        self.sig_restart_requested.connect(self.restart)

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

    def on_close(self):
        self.get_container().on_close()

    def on_mainwindow_visible(self):
        """Actions after the mainwindow in visible."""
        container = self.get_container()

        # Show dialog with missing dependencies
        if not running_under_pytest():
            container.compute_dependencies()

        # Check for updates
        if DEV is None and self.get_conf('check_updates_on_startup'):
            container.give_updates_feedback = False
            container.check_updates(startup=True)

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

    # ---- Private API
    # ------------------------------------------------------------------------
    def _populate_file_menu(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.restart_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart)
        mainmenu.add_item_to_application_menu(
            self.restart_debug_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart)

    def _populate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        if WinUserEnvDialog is not None:
            mainmenu.add_item_to_application_menu(
                self.winenv_action,
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
                self.trouble_action, self.report_action,
                self.dependencies_action, self.check_updates_action,
                self.support_group_action]:
            mainmenu.add_item_to_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before_section=HelpMenuSections.ExternalDocumentation)

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
        menu = QMenu(parent=parent)
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
    def restart(self):
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

        if DEV:
            repo_dir = osp.dirname(spyder_start_directory)
            if os.name == 'nt':
                env['PYTHONPATH'] = ';'.join([repo_dir])
            else:
                env['PYTHONPATH'] = ':'.join([repo_dir])

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
            if self.main.closing(True):
                subprocess.Popen(command, shell=shell, env=env,
                                 startupinfo=startupinfo)
                console.quit()
        except Exception as error:
            # If there is an error with subprocess, Spyder should not quit and
            # the error can be inspected in the internal console
            print(error)  # spyder: test-skip
            print(command)  # spyder: test-skip

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
    def check_updates_action(self):
        """Check if a new version of Spyder is available."""
        return self.get_container().check_updates_action

    @property
    def support_group_action(self):
        """Open Spyder's Google support group in the browser."""
        return self.get_container().support_group_action

    @property
    def about_action(self):
        """Show Spyder's About dialog box."""
        return self.get_container().about_action

    @property
    def winenv_action(self):
        """Show Spyder's Windows user env variables dialog box."""
        return self.get_container().winenv_action

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
