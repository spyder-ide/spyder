# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main menu Plugin.
"""
# Standard library imports
import os
import os.path as osp
import subprocess
import sys

# Third party imports
from qtpy.QtCore import Qt, QTimer, Slot
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.config.base import DEV, get_module_path, running_under_pytest
from spyder.plugins.application.confpage import ApplicationConfigPage
from spyder.plugins.application.container import (
    ApplicationActions, ApplicationContainer, WinUserEnvDialog)
from spyder.plugins.console.api import ConsoleActions
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, FileMenuSections, HelpMenuSections, ToolsMenuSections)
from spyder.utils.qthelpers import add_actions

# Localization
_ = get_translation('spyder')


class Application(SpyderPluginV2):
    NAME = 'application'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Help, Plugins.MainMenu, Plugins.Shortcuts]
    CONTAINER_CLASS = ApplicationContainer
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        # Screen resolution section
        'normal_screen_resolution': ('main', 'normal_screen_resolution'),
        'high_dpi_scaling': ('main', 'high_dpi_scaling'),
        'high_dpi_custom_scale_factor': ('main',
                                         'high_dpi_custom_scale_factor'),
        'high_dpi_custom_scale_factors': ('main',
                                          'high_dpi_custom_scale_factors'),
        # Panes section
        'vertical_tabs': ('main', 'vertical_tabs'),
        'use_custom_margin': ('main', 'use_custom_margin'),
        'custom_margin': ('main', 'custom_margin'),
        'use_custom_cursor_blinking': ('main', 'use_custom_cursor_blinking'),
        # Advanced settings
        'opengl': ('main', 'opengl'),
        'single_instance': ('main', 'single_instance'),
        'prompt_on_exit': ('main', 'prompt_on_exit'),
        'check_updates_on_startup': ('main', 'check_updates_on_startup'),
        'show_internal_errors': ('main', 'show_internal_errors'),
    }
    CONF_WIDGET_CLASS = ApplicationConfigPage

    def get_name(self):
        return _('Application')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide main application base actions.')

    def register(self):
        # Register with Preferences plugin
        console = self.get_plugin(Plugins.Console)
        main_menu = self.get_plugin(Plugins.MainMenu)
        preferences = self.get_plugin(Plugins.Preferences)

        # Register conf page
        preferences.register_plugin_preferences(self)

        # Main menu population
        self._populate_file_menu()
        self._populate_tools_menu()
        self._populate_help_menu()

        # Actions
        report_action = self.create_action(
            ConsoleActions.SpyderReportAction,
            _("Report issue..."),
            icon=self.create_icon('bug'),
            triggered=console.report_issue)
        dependencies_action = self.get_action(
            ApplicationActions.SpyderDependenciesAction)
        if main_menu:
            main_menu.add_item_to_application_menu(
                report_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before=dependencies_action)

    def on_close(self):
        self.get_container().on_close()

    def on_mainwindow_visible(self):
        """Actions after the mainwindow in visible."""
        # Show dialog with missing dependencies
        if not running_under_pytest():
            # This avoids computing missing deps before the window is fully up
            timer_report_deps = QTimer(self)
            timer_report_deps.setInterval(2000)
            timer_report_deps.setSingleShot(True)
            timer_report_deps.timeout.connect(
                self.get_container().report_missing_dependencies)
            timer_report_deps.start()

    # --- Private methods
    # ------------------------------------------------------------------------

    def _populate_file_menu(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        if mainmenu:
            mainmenu.add_item_to_application_menu(
                self.restart_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Restart)

    def _populate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        if mainmenu:
            if WinUserEnvDialog is not None:
                mainmenu.add_item_to_application_menu(
                    self.winenv_action,
                    menu_id=ApplicationMenus.Tools,
                    section=ToolsMenuSections.Tools)

    def _populate_help_menu(self):
        """Add base actions and menus to the Help menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        self._populate_help_menu_documentation_section(mainmenu)
        self._populate_help_menu_support_section(mainmenu)
        self._populate_help_menu_about_section(mainmenu)

    def _populate_help_menu_documentation_section(self, mainmenu):
        """Add base Spyder documentation actions to the Help main menu."""
        if mainmenu:
            shortcuts = self.get_plugin(Plugins.Shortcuts)
            shortcuts_summary_action = None
            if shortcuts:
                from spyder.plugins.shortcuts.plugin import ShortcutActions
                shortcuts_summary_action = shortcuts.get_action(
                    ShortcutActions.ShortcutSummaryAction)
            for documentation_action in [
                    self.documentation_action, self.video_action]:
                mainmenu.add_item_to_application_menu(
                    documentation_action,
                    menu_id=ApplicationMenus.Help,
                    section=HelpMenuSections.Documentation,
                    before=shortcuts_summary_action,
                    before_section=HelpMenuSections.Support)

    def _populate_help_menu_support_section(self, mainmenu):
        """Add Spyder base support actions to the Help main menu."""
        if mainmenu:
            for support_action in [
                    self.trouble_action, self.dependencies_action,
                    self.check_updates_action, self.support_group_action]:
                mainmenu.add_item_to_application_menu(
                    support_action,
                    menu_id=ApplicationMenus.Help,
                    section=HelpMenuSections.Support,
                    before_section=HelpMenuSections.ExternalDocumentation)

    def _populate_help_menu_about_section(self, mainmenu):
        """Create Spyder base about actions."""
        if mainmenu:
            mainmenu.add_item_to_application_menu(
                self.about_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.About)

    # --- Public API
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

    def apply_settings(self):
        """Apply applications settings."""
        self._main.apply_settings()

    @Slot()
    def restart(self, reset=False):
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
        env['SPYDER_RESET'] = str(reset)

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
