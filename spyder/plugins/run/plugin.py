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
from typing import List, Dict

# Third-party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import get_translation
from spyder.plugins.run.confpage import RunConfigPage
from spyder.plugins.run.api import (
    RunContext, RunResultFormat, RunInputExtension, RunConfigurationProvider,
    SupportedRunConfiguration, RunExecutor, SupportedExecutionRunConfiguration,
    RunResultViewer, OutputFormat)
from spyder.plugins.run.container import RunContainer

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
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.MainMenu]
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
        pass

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        main_menu = self.get_plugin(Plugins.MainMenu)


    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    # --- Public API
    # ------------------------------------------------------------------------
    def register_input_provider_configuration(
            self, provider: RunConfigurationProvider,
            configuration: List[SupportedRunConfiguration]):
        """
        Register a :class:`RunConfigurationProvider` instance to indicate
        its support for a given set of run configurations.
        This method can be called whenever an input provider can extend its
        support for a given run input configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will register
            execution input type information.
        configuration: List[SuportedRunConfiguration]
            A list of input configurations that the provider is able to
            produce. Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        self.get_container().register_input_provider_configuration(
            provider, configuration)

    def deregister_input_provider_configuration(
            self, provider: RunConfigurationProvider,
            configuration: List[SupportedRunConfiguration]):
        """
        Deregister a :class:`RunConfigurationProvider` instance from providing
        a set of run configurations that are no longer supported by it. This
        method can be called whenever an input provider wants to remove its
        support for a given run input configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will deregister execution
            input type information.
        configuration: List[SupportedRunConfiguration]
            A list of input configurations that the provider wants to deregister.
            Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        self.get_container().deregister_input_provider_configuration(
            provider, configuration)

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
