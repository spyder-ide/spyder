# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Completion plugin to manage code completion and introspection providers.
"""

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.completion.container import CodeCompletionContainer

# Localization
_ = get_translation('spyder')


class CodeCompletion(SpyderPluginV2):
    """
    Completion plugin to manage code completion and introspection providers.
    """
    NAME = 'code_completion'
    REQUIRES = []
    OPTIONAL = []
    CONTAINER_CLASS = CodeCompletionContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        'wait_completions_for_ms': ('editor', 'wait_completions_for_ms'),
    }

    sig_provider_ready = Signal(str)
    """
    Inform that a provider is ready to provide completions.

    Parameters
    ----------
    language: str
        Unique language identifier string. Should be lowercased.
    """

    # --- SpyderPlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Completions')

    def get_description(self):
        return _('Provide completions management on widgets')

    def get_icon(self):
        return QIcon()

    def register(self):
        container = self.get_container()
        container.sig_provider_ready.connect(self.sig_provider_ready)

    def on_close(self):
        self.shutdown_providers()

    def on_mainwindow_visible(self):
        self.start_providers()
        self.start_provider_clients(language='python')

    # --- Plugin API
    # ------------------------------------------------------------------------
    def register_completion_provider(self, provider):
        """
        Register a completion `provider` with `provider_name`.

        Parameters
        ----------
        provider: spyder.plugins.completions.api.SpyderCompletionProvider
            Completion provider instance.
        """
        self.get_container().register_completion_provider(provider)

    def get_provider(self, provider_name):
        """
        Return a completion provider instance by `provider_name`.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        """
        return self.get_container().get_provider(provider_name)

    def start_providers(self):
        """
        Start all registered completion providers.
        """
        self.get_container().start_providers()

    def shutdown_providers(self):
        """
        Shutdown all registered completion providers.
        """
        self.get_container().shutdown_providers()

    def start_provider_clients(self, language):
        """
        Start a `language` client on all registered completion providers.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        """
        return self.get_container().start_provider_clients(language)

    def stop_provider_clients(self, language):
        """
        Stop a `language` client on all registered completion providers.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        """
        self.get_container().stop_provider_clients(language)

    def register_file(self, language, filename, codeeditor):
        """
        Register file with completion providers.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        filename: str
            Path to file.
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Code editor instance.
        """
        self.get_container().register_file(language, filename, codeeditor)

    def send_request(self, language, request_type, request):
        """
        Send a request to all providers.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        request_type: str
            See `spyder.plugins.completion.api.LSPRequestTypes`.
        request: dict
            Request information dictionary.
        """
        self.get_container().send_request(language, request_type, request)

    def set_wait_for_source_requests(self, provider_name, request_types):
        """
        Set which request types should wait for source.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        request_types: list
            List of spyder.plugins.completion.api.LSPRequestTypes.
        """
        self.get_container().set_wait_for_source_requests(
            provider_name, request_types)

    def set_request_type_priority(self, provider_name, request_type):
        """
        Set request type top priority for given provider.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        request_type: str
            See `spyder.plugins.completion.api.LSPRequestTypes`
        """
        self.get_container().set_wait_for_source_requests(
            provider_name, request_type)
