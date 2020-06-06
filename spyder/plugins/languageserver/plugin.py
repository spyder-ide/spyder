# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Manager for all LSP clients connected to the servers defined in Preferences.
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.translations import get_translation
from spyder.api.plugins import SpyderPluginV2, Plugins
from spyder.config.base import get_conf_path
from spyder.plugins.completion.api import LSPRequestTypes
from spyder.plugins.languageserver.confpage import LanguageServerConfigPage
from spyder.plugins.languageserver.container import LanguageServerContainer
from spyder.utils.misc import check_connection_port, getcwd_or_home

# Localization
_ = get_translation('spyder')


class LanguageServer(SpyderPluginV2):
    """
    Language server completion client plugin.
    """
    NAME = 'lsp'
    REQUIRES = [Plugins.CodeCompletion, Plugins.Console, Plugins.Editor]
    OPTIONAL = [Plugins.Projects]
    CONTAINER_CLASS = LanguageServerContainer
    CONF_SECTION = 'lsp-server'
    CONF_FILE = False
    CONF_WIDGET_CLASS = LanguageServerConfigPage
    CONF_FROM_OPTIONS = {
        'spyder_pythonpath': ('main', 'spyder_pythonpath'),
        'custom_interpreter': ('main_interpreter', 'custom_interpreter'),
        'default_interpreter': ('main_interpreter', 'default'),
    }

    # --- SpyderPlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Language server completion provider')

    def get_description(self):
        return _('Provide language server completions')

    def get_icon(self):
        return self.create_icon('lspserver')

    def register(self):
        container = self.get_container()
        completion = self.get_plugin(Plugins.CodeCompletion)

        # Register client
        completion.register_completion_provider(container.provider)

        # Set prioritites
        completion.set_wait_for_source_requests(
            container.provider.NAME,
            [
                LSPRequestTypes.DOCUMENT_COMPLETION,
                LSPRequestTypes.DOCUMENT_SIGNATURE,
                LSPRequestTypes.DOCUMENT_HOVER,
            ]
        )

        projects = self.get_plugin(Plugins.Projects)
        if projects is not None:
            projects.sig_project_loaded.connect(
                lambda: self._update_root_path())
            projects.sig_project_closed.connect(
                lambda: self._update_root_path())

        editor = self.get_plugin(Plugins.Editor)
        editor.sig_editor_focus_changed.connect(self._update_status_widget)

        # Add the stats widget
        self.add_application_status_widget(
            'lsp_status', container.status_widget)

        # Signals
        container.sig_restart_requested.connect(self.sig_restart_requested)
        container.sig_stop_completion_services_requested.connect(
            self._stop_completion_services)
        container.sig_register_client_instance_requested.connect(
            self._register_client_instance)

    # --- Private API
    # ------------------------------------------------------------------------
    def _stop_completion_services(self, language):
        """
        TODO:
        """
        # Only stop this if a language is provided
        if bool(language):
            editor = self.get_plugin(Plugins.Editor)
            editor.stop_completion_services(language)

        projects = self.get_plugin(Plugins.Projects)
        if projects is not None:
            projects.stop_lsp_services()

    def _update_root_path(self):
        """
        Get root path to pass to the LSP servers.

        This can be the current project path or the output of
        getcwd_or_home (except for Python, see below).
        """
        path = None
        language = 'python'

        # Get path of the current project
        projects = self.get_plugin(Plugins.Projects)
        if projects is not None:
            path = projects.get_active_project_path()

        if not path:
            # We can't use getcwd_or_home for LSP servers because if it
            # returns home and you have a lot of files on it
            # then computing completions takes a long time
            # and blocks the LSP server.
            # Instead we use an empty directory inside our config one,
            # just like we did for Rope in Spyder 3.
            path = get_conf_path('lsp_root_path')
            if not os.path.exists(path):
                os.mkdir(path)

        self.get_container().update_root_path(language, path)

    def _register_client_instance(self, client_instance):
        """
        Register signals emmited by a client instance.

        Parameters
        ----------
        client_instance: spyder.plugins.languageserver.client.LSPClient
            Language server protocol client instante.
        """
        container = self.get_container()
        main = self.get_main()

        main.sig_pythonpath_changed.connect(container.update_configuration)
        main.sig_main_interpreter_changed.connect(
            container.update_configuration)

        editor = self.get_plugin(Plugins.Editor)
        client_instance.sig_initialized.connect(
            editor.register_completion_server_settings)
        # editor.sig_editor_focus_changed.connect(
        #     self.status_widget.update_status)

        console = self.get_plugin(Plugins.Console)
        # FIXME: how does this work?
        # instance.sig_server_error.connect(self.report_server_error)

        projects = self.get_plugin(Plugins.Projects)
        if projects is not None:
            client_instance.sig_initialized.connect(
                projects.register_lsp_server_settings)

    def _update_status_widget(self):
        """
        Update the status widget on editor focus change.
        """
        language = _('Unknown')
        editor = self.get_plugin(Plugins.Editor)
        codeeditor = editor.get_current_editor()
        if codeeditor is not None:
            language = codeeditor.language

        self.get_container().update_current_editor_language(language)

    # --- Public API
    # ------------------------------------------------------------------------
    # TODO: Add api to perform extensions?
