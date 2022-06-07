# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Run Plugin.
"""

# Standard library imports
from typing import List, Dict, Optional
from numpy import short

# Third-party imports
from qtpy.QtCore import Signal
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import get_translation
from spyder.plugins.run.confpage import RunConfigPage
from spyder.plugins.run.api import (
    RunContext, RunResultFormat, RunInputExtension, RunConfigurationProvider,
    SupportedRunConfiguration, RunExecutor, SupportedExecutionRunConfiguration,
    RunResultViewer, OutputFormat, RunConfigurationMetadata, RunActions)
from spyder.plugins.run.container import RunContainer
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Run(SpyderPluginV2):
    """
    Run Plugin.
    """

    NAME = "run"
    # TODO: Fix requires to reflect the desired order in the preferences
    REQUIRES = [Plugins.Preferences, Plugins.WorkingDirectory]
    OPTIONAL = [Plugins.MainMenu, Plugins.Toolbar, Plugins.Shortcuts]
    CONTAINER_CLASS = RunContainer
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = RunConfigPage
    CONF_FILE = False

    sig_run_input = Signal(str)
    """
    Request to run an input.

    Arguments
    ---------
    context: str
        Context used to request the run input information from the currently
        focused `RunConfigurationProvider`
    """

    sig_switch_run_configuration_focus = Signal(str)
    """
    Change the current run configuration to the one that is focused.

    Arguments
    ---------
    uuid: str
        The run configuration identifier.
    """

    # --- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Run")

    def get_description(self):
        return _("Manage run configuration.")

    def get_icon(self):
        return self.create_icon('run')

    def on_initialize(self):
        self.pending_toolbar_actions = []
        self.pending_menu_actions = []
        self.pending_shortcut_actions = []

        self.sig_switch_run_configuration_focus.connect(
            self.switch_focused_run_configuration)

        container = self.get_container()
        container.sig_run_action_created.connect(
            self.register_action_shortcuts)

    @on_plugin_available(plugin=Plugins.WorkingDirectory)
    def on_working_directory_available(self):
        working_dir = self.get_plugin(Plugins.WorkingDirectory)
        working_dir.sig_current_directory_changed.connect(
            self.switch_working_dir)
        self.switch_working_dir(working_dir.get_workdir())

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        main_menu.add_item_to_application_menu(
            self.get_action(RunActions.Run),
            ApplicationMenus.Run, RunMenuSections.Run
        )
        while self.pending_menu_actions != []:
            action = self.pending_menu_actions.pop(0)
            main_menu.add_item_to_application_menu(
                action,
                ApplicationMenus.Run,
                RunMenuSections.RunExtras
            )

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.add_item_to_application_toolbar(
            self.get_action(RunActions.Run), ApplicationToolbars.Run)

        while self.pending_toolbar_actions != []:
            action = self.pending_toolbar_actions.pop(0)
            toolbar.add_item_to_application_toolbar(
                action, ApplicationToolbars.Run)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Shortcuts)
    def on_shortcuts_available(self):
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        while self.pending_shortcut_actions != []:
            args = self.pending_shortcut_actions.pop(0)
            shortcuts.register_shortcut(*args)
        shortcuts.apply_shortcuts()

    # --- Public API
    # ------------------------------------------------------------------------
    def register_run_configuration_metadata(
            self, provider: RunConfigurationProvider,
            metadata: RunConfigurationMetadata):
        """
        Register the metadata for a run configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will register
            and own a run configuration.
        metadata: RunConfigurationMetadata
            The metadata for a run configuration that the provider is able to
            produce.

        Notes
        -----
        The unique identifier for the metadata dictionary is produced and
        managed by the provider and the Run plugin will only refer to the
        run configuration by using such id.
        """
        self.get_container().register_run_configuration_metadata(
            provider, metadata)

    def deregister_run_configuration_metadata(self, uuid: str):
        """
        Deregister a given run configuration by its unique identifier.

        Parameters
        ----------
        uuid: str
            Unique identifier for a run configuration metadata that will not
            longer exist. This id should have been registered using
            `register_run_configuration_metadata`.
        """
        self.get_container().deregister_run_configuration_metadata(uuid)

    def register_executor_configuration(
            self, provider: RunExecutor,
            configuration: List[SupportedExecutionRunConfiguration]):
        """
        Register a :class:`RunExecutor` instance to indicate its support
        for a given set of run configurations. This method can be called
        whenever an executor can extend its support for a given run input
        configuration.

        Parameters
        ----------
        provider: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will register execution
            input type information.
        configuration: List[SupportedRunConfiguration]
            A list of input configurations that the provider is able to
            process. Each configuration specifies the input extension
            identifier, the available execution context and the output formats
            for that type.
        """
        self.get_container().register_executor_configuration(
            provider, configuration)

    def deregister_executor_configuration(
            self, provider: RunExecutor,
            configuration: List[SupportedExecutionRunConfiguration]):
        """
        Deregister a :class:`RunConfigurationProvider` instance from providing
        a set of run configurations that are no longer supported by it.
        This method can be called whenever an input provider wants to remove
        its support for a given run input configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will deregister
            execution input type information.
        configuration: List[SuportedRunConfiguration]
            A list of input configurations that the provider is able to
            process. Each configuration specifies the input extension
            identifier, the available execution context and the output formats
            for that type
        """
        self.get_container().deregister_executor_configuration(
            provider, configuration)

    def register_viewer_configuration(
            self, viewer: RunResultViewer, formats: List[OutputFormat]):
        """
        Register a :class:`RunExecutorProvider` instance to indicate its support
        for a given set of output run result formats. This method can be called
        whenever an viewer can extend its support for a given output format.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will register
            supported output formats.
        formats: List[OutputFormat]
            A list of output formats that the viewer is able to
            display.
        """
        self.get_container().register_viewer_configuration(viewer, formats)

    def deregister_viewer_configuration(
            self, viewer: RunResultViewer, formats: List[OutputFormat]):
        """
        Deregister a :class:`RunResultViewer` instance from supporting a set of
        output formats that are no longer supported by it. This method
        can be called whenever a viewer wants to remove its support
        for a given output format.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will deregister
            output format support.
        formats: List[OutputFormat]
            A list of output formats that the viewer wants to deregister.
        """
        self.get_container().deregister_viewer_configuration(viewer, formats)

    def create_run_button(self, context_name: str, text: str,
                          icon: Optional[QIcon] = None,
                          tip: Optional[str] = None,
                          shortcut_context: Optional[str] = None,
                          register_shortcut: bool = False,
                          extra_action_name: Optional[str] = None,
                          add_to_toolbar: bool = False,
                          add_to_menu: bool = False):
        """
        Create a run or a "run and do something" button
        for a specific run context.

        Parameters
        ----------
        context_name: str
            The identifier of the run context.
        text: str
           Localized text for the action
        icon: Optional[QIcon]
            Icon for the action when applied to menu or toolbutton.
        tip: Optional[str]
            Tooltip to define for action on menu or toolbar.
        shortcut_context: Optional[str]
            Set the `str` context of the shortcut.
        register_shortcut: bool
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.
        extra_action_name: Optional[str]
            The name of the action to execute on the run input provider
            after requesting the run input.
        add_to_toolbar: bool
            If True, then the action will be added to the Run section of the
            main toolbar.
        add_to_menu: bool
            If True, then the action will be added to the Run menu.

        Notes
        -----
        1. The context passed as a parameter must be a subordinate of the
        context of the current focused run configuration that was
        registered via `register_run_configuration_metadata`. e.g., Cell can
        be used if and only if the file was registered.

        2. The button will be registered as `run <context>` or
        `run <context> and <extra_action_name>` on the action registry.

        3. The created button will operate over the last focused run input
        provider.

        4. If the requested button already exists, this method will not do
        anything, which implies that the first registered shortcut will be the
        one to be used. For the built-in run contexts
        (file, cell and selection), the editor will register their
        corresponding icons and shortcuts.
        """
        action = self.get_container().create_run_button(
            context_name, text,
            icon=icon,
            tip=tip,
            shortcut_context=shortcut_context,
            register_shortcut=register_shortcut,
            extra_action_name=extra_action_name
        )

        if add_to_toolbar:
            toolbar = self.get_plugin(Plugins.Toolbar)
            if toolbar:
                toolbar.add_item_to_application_toolbar(
                    action, ApplicationToolbars.Run)
            else:
                self.pending_toolbar_actions.append(action)

        if add_to_menu:
            main_menu = self.get_plugin(Plugins.MainMenu)
            if main_menu:
                main_menu.add_item_to_application_menu(
                    action, ApplicationMenus.Run, RunMenuSections.RunExtras
                )
            else:
                self.pending_menu_actions.append(action)
        return action

    # --- Private API
    # ------------------------------------------------------------------------
    def switch_focused_run_configuration(self, uuid: str):
        self.get_container().switch_focused_run_configuration(uuid)

    def switch_working_dir(self, path: str):
        self.get_container().set_current_working_dir(path)

    def register_action_shortcuts(self, action_name: str,
                                  register_shortcut: bool,
                                  shortcut_context: str):
        if register_shortcut:
            action = self.get_action(action_name)
            shortcuts = self.get_plugin(Plugins.Shortcuts)
            if shortcuts:
                shortcuts.register_shortcut(action, shortcut_context,
                                            action_name)
                shortcuts.apply_shortcuts()
            else:
                self.pending_shortcut_actions.append(
                    (action, shortcut_context, action_name))
