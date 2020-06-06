# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Manager for all LSP clients connected to the servers defined in Preferences.
"""

# Standard library imports
import functools
import logging
import os

# Third party imports
from qtpy.QtCore import QTimer, Signal, Slot

# Local imports
from spyder.api.translations import get_translation
from spyder.config.base import running_under_pytest
from spyder.plugins.completion.api import SpyderCompletionProvider
from spyder.plugins.languageserver.client import LSPClient
from spyder.utils.misc import check_connection_port, getcwd_or_home

# Logging
logger = logging.getLogger(__name__)

# Localization
_ = get_translation("spyder")


# --- Constants
# ----------------------------------------------------------------------------
# FIXME: To be placed elsewhere
class ClientStatus:
    Stopped = 'stopped'
    Running = 'running'


class ClientTransportType:
    TCP = "tcp"
    StandardIO = "stdio"


# --- Completion Provider
# ----------------------------------------------------------------------------
class LanguageServerProvider(SpyderCompletionProvider):
    # --- SpyderCompletionProvider API class attributes
    NAME = 'lsp'

    # --- Other class attributes
    TIME_BETWEEN_RESTARTS = 10000
    """
    TIME_BETWEEN_RESTARTS: int
        Time between restarts in miliseconds.
    """

    TIME_HEARTBEAT = 3000
    """
    TIME_HEARTBEAT: int
        Time between heartbeats in miliseconds.
    """

    MAX_RESTART_ATTEMPTS = 5
    """
    MAX_RESTART_ATTEMPTS: int
        Number of automatic restart attempts before decalaring a client is
        down.
    """

    # --- Signals
    sig_stop_completion_services_requested = Signal(str)
    """
    Request to stop the completion sevices for `language`.

    Parameters
    ----------
    language: str
        Unique language identifier string. Should be lowercased.
    """

    sig_lsp_down_reported = Signal(str)
    """
    Report the language server client for given `language` is down.

    Parameters
    ----------
    language: str
        Unique language identifier string. Should be lowercased.
    """

    sig_no_external_server_reported = Signal(str, int, str)
    """
    Report the external server client for given `language` is down.

    Parameters
    ----------
    host: str
        Host of client.
    port: int
        Port number used by client.
    language: str
        Unique language identifier string. Should be lowercased.
    """

    sig_register_client_instance_requested = Signal(LSPClient)
    """
    Request the registration of a client instance.

    Parameters
    ----------
    client_instance: spyder.plugins.languageserver.client.LSPClient
        Language server protocol client instante.
    """

    sig_update_status_requested = Signal(str, str)
    """
    Request a change of status on the status widget.

    Parameters
    ----------
    language: str
        Unique language identifier string. Should be lowercased.
    status: str
        Localized status string of the `language` client.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.root_paths = {}
        self.language_configs = {}
        self.clients = {}
        self.clients_restart_count = {}
        self.clients_restart_timers = {}
        self.clients_restarting = {}
        self.clients_hearbeat = {}
        self.clients_status = {}
        self.requests = set({})
        self.register_queue = {}

    # --- SpyderCompletionProvider API
    # ------------------------------------------------------------------------
    def start(self):
        pass

    def shutdown(self):
        logger.info("Shutting down LSP provider...")
        for language in self.clients:
            self.stop_client(language)

    def start_client(self, language):
        started = False
        if language in self.clients:
            language_client = self.clients[language]
            queue = self.register_queue[language]

            # Don't start LSP services when testing unless we demand them.
            if running_under_pytest():
                if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                    return started

            started = language_client['status'] == ClientStatus.Running

            # Start client heartbeat
            timer = QTimer(self)
            self.clients_hearbeat[language] = timer
            timer.setInterval(self.TIME_HEARTBEAT)
            timer.timeout.connect(lambda: self.check_heartbeat(language))
            timer.start()

            if language_client['status'] == ClientStatus.Stopped:
                config = language_client['config']

                # If we're trying to connect to an external server,
                # verify that it's listening before creating a
                # client for it.
                if config['external']:
                    host = config['host']
                    port = config['port']
                    response = check_connection_port(host, port)
                    if not response:
                        self.sig_no_external_server_reported.emit(
                            host, port, language)

                        self.update_status(language, _("down"))
                        return False

                language_client['instance'] = LSPClient(
                    parent=self,
                    server_settings=config,
                    folder=self.get_root_path(language),
                    language=language
                )

                self.register_client_instance(language_client['instance'])

                logger.info("Starting LSP client for {}...".format(language))
                language_client['instance'].start()
                language_client['status'] = ClientStatus.Running
                for entry in queue:
                    language_client['instance'].register_file(*entry)

                self.register_queue[language] = []

        return started

    def stop_client(self, language):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == ClientStatus.Running:
                logger.info("Stopping LSP client for {}...".format(language))
                # FIXME: This was commented before this PR, why?
                # language_client['instance'].shutdown()
                # language_client['instance'].exit()
                language_client['instance'].stop()

            language_client['status'] = ClientStatus.Stopped

    def register_file(self, language, filename, codeeditor):
        if language in self.clients:
            language_client = self.clients[language]['instance']
            if language_client is None:
                self.register_queue[language].append((filename, codeeditor))
            else:
                language_client.register_file(filename, codeeditor)

    def update_configuration(self, options=None):
        for language in self.get_languages():
            client_config = {'status': ClientStatus.Stopped,
                             'config': self.get_language_config(language),
                             'instance': None}

            if language not in self.clients:
                self.clients[language] = client_config
                self.register_queue[language] = []
            else:
                current_lang_config = self.clients[language]['config']
                new_lang_config = client_config['config']
                restart_diff = ['cmd', 'args', 'host',
                                'port', 'external', 'stdio']
                restart = any([current_lang_config[x] != new_lang_config[x]
                               for x in restart_diff])
                if restart:
                    logger.debug("Restart required for {} client!".format(
                        language))
                    if (self.clients[language]['status']
                            == ClientStatus.Stopped):
                        # If we move from an external non-working server to
                        # an internal one, we need to start a new client.
                        if (current_lang_config['external'] and
                                not new_lang_config['external']):
                            self.restart_client(language, client_config)
                        else:
                            self.clients[language] = client_config
                    elif (self.clients[language]['status']
                          == ClientStatus.Running):
                        self.restart_client(language, client_config)
                else:
                    if (self.clients[language]['status']
                            == ClientStatus.Running):
                        client = self.clients[language]['instance']
                        client.send_plugin_configurations(
                            new_lang_config['configurations'])

    def send_response(self):
        pass
        # FIXME: Was this a typo on the API? should it be receive or?

    def send_request(self, language, request, params, req_id):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == ClientStatus.Running:
                self.requests.add(req_id)
                client = self.clients[language]['instance']
                params['response_callback'] = functools.partial(
                    self.receive_response, language=language, req_id=req_id)
                client.perform_request(request, params)
                return

        self.sig_response_ready.emit(self.NAME, req_id, {})

    def send_notification(self, language, request, params):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == ClientStatus.Running:
                client = self.clients[language]['instance']
                client.perform_request(request, params)

    def broadcast_notification(self, request, params):
        language = params.pop('language', None)
        if language:
            self.send_notification(language, request, params)
        else:
            for language in self.clients:
                self.send_notification(language, request, params)

    # FIXME: This is called by the Projects. Decouple
    @Slot()
    def project_path_update(self, project_path, update_kind):
        self.sig_stop_completion_services_requested.emit('')
        for language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == ClientStatus.Running:
                self.main.editor.stop_completion_services(language)
                folder = self.get_root_path(language)
                instance = language_client['instance']
                instance.folder = folder
                instance.initialize({'pid': instance.stdio_pid})

    # --- Other API
    # ------------------------------------------------------------------------
    # FIXME: Was this a typo on the API? should it be send or?
    def receive_response(self, response_type, response, language, req_id):
        """
        Receive response and emit response ready if a valid request id.

        Parameters
        ----------
        response_type: str
            See spyder.plugins.completion.api.LSPRequestTypes
        response: dict
            Response dictionary from client.
        language: str
            Unique language identifier string. Should be lowercased.
        req_id: int
            Request identifier.
        """
        if req_id in self.requests:
            self.requests.discard(req_id)
            self.sig_response_ready.emit(self.NAME, req_id, response)

    # FIXME: This is called by the editor. Decouple
    def update_client_status(self, active_set):
        """
        Update client status.

        Parameters
        ----------
        active_set: set
            Set of language names.
        """
        for language in self.clients:
            if language not in active_set:
                self.stop_client(language)

    def restart_lsp(self, language, force=False):
        """
        Restart language server on failure.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        force: bool, optional
            Force a restart. Default is False.
        """
        client_config = {
            'status': ClientStatus.Stopped,
            'config': self.get_language_config(language),
            'instance': None,
        }

        if force:
            logger.info("Manual restart for {}...".format(language))
            self.update_status(language, _('restarting...'))
            self.restart_client(language, client_config)

        elif self.clients_restarting[language]:
            attempt = (self.MAX_RESTART_ATTEMPTS
                       - self.clients_restart_count[language] + 1)
            logger.info("Automatic restart attempt {} for {}...".format(
                attempt, language))
            self.update_status(language, _('restarting...'))

            self.clients_restart_count[language] -= 1
            self.restart_client(language, client_config)
            client = self.clients[language]

            # Restarted the maximum amount of times without
            if self.clients_restart_count[language] <= 0:
                logger.info("Restart failed!")
                self.clients_restarting[language] = False
                self.clients_restart_timers[language].stop()
                self.clients_restart_timers[language] = None
                try:
                    self.clients_hearbeat[language].stop()
                    client['instance'].disconnect()
                except (TypeError, KeyError, RuntimeError):
                    pass
                self.clients_hearbeat[language] = None
                self.sig_lsp_down_reported.emit(language)

            # Check if the restart was successful
            self.check_restart(client, language)

    def check_restart(self, client, language):
        """
        Check if a server restart was successful in order to stop
        further attempts.

        Parameters
        ----------
        client: object
            Client instance for `language`.
        language: str
            Unique language identifier string. Should be lowercased.
        """
        status = client['status']
        check = client['instance'].is_transport_alive()

        if status == ClientStatus.Running and check:
            logger.info("Restart successful!")
            self.clients_restarting[language] = False
            self.clients_restart_timers[language].stop()
            self.clients_restart_timers[language] = None
            self.clients_restart_count[language] = 0
            self.update_status(language, _('ready'))

    def check_heartbeat(self, language):
        """
        Check if client or server for a given language are down.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        client = self.clients[language]
        instance = client.get('instance', None)
        if instance is not None:
            if not instance.is_transport_alive():
                instance.sig_lsp_down.emit(language)

    def on_initialize(self, options, language):
        """
        Update the status bar widget on client initilization.

        Parameters
        ----------
        options: TODO: ?
            TODO: ?
        language: str
            Unique language identifier string. Should be lowercased.
        """
        if not self.clients_restarting.get(language, False):
            self.update_status(language, _('ready'))

        # This is the only place where we can detect if restarting
        # a stdio server was successful because its pid is updated
        # on initialization.
        if self.clients_restarting.get(language):
            client = self.clients[language]
            self.check_restart(client, language)

    def handle_lsp_down(self, language):
        """
        Handle automatic restart of client/server on failure.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        if (not self.clients_restarting.get(language, False)
                and not running_under_pytest()):
            try:
                self.clients_hearbeat[language].stop()
            except KeyError:
                pass
            logger.info("Automatic restart for {}...".format(language))

            timer = QTimer(self)
            timer.setSingleShot(False)
            timer.setInterval(self.TIME_BETWEEN_RESTARTS)
            timer.timeout.connect(lambda: self.restart_lsp(language))

            self.update_status(language, _('restarting...'))
            self.clients_restarting[language] = True
            self.clients_restart_count[language] = self.MAX_RESTART_ATTEMPTS
            self.clients_restart_timers[language] = timer
            timer.start()

    def restart_client(self, language, config):
        """
        Restart a `language` client with give `config`.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        config: dict
            Configuration for the given `language`.
        """
        self.sig_stop_completion_services_requested.emit(language)
        self.stop_client(language)
        self.clients[language] = config
        self.start_client(language)

    def set_language_config(self, language, config):
        """
        Set the configuration dictionary for the given `language`.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        config: dict
            Configuration for the given `language`.
        """
        self.language_configs[language] = config
        self.update_configuration()

    def get_language_config(self, language):
        """
        Return the configuration dictionary for the given `language`.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        return self.language_configs.get(language, {})

    def get_root_path(self, language):
        """
        Get the current root path for the given language.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        path = self.root_paths.get(language.lower())
        if path is None:
            path = getcwd_or_home()

        return path

    def set_root_path(self, language, root_path):
        """
        Set the current root path for the given language.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        root_path: str
            Path to current active root folder for language.
        """
        self.root_paths[language.lower()] = root_path

    def get_languages(self):
        """
        Get the list of languages to start servers and create clients.
        """
        return [lang.lower() for lang in self.language_configs.keys()]

    def update_status(self, language, status):
        """
        Update `status` of client running for given `language`.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        status: str
            Localized status string of the `language` client.
        """
        self.clients_status[language.lower()] = status
        self.sig_update_status_requested.emit(language.lower(), status)

    def register_client_instance(self, client_instance):
        """
        Register signals emmited by a client instance.

        Parameters
        ----------
        client_instance: spyder.plugins.languageserver.client.LSPClient
            Language server protocol client instante.
        """
        client_instance.sig_went_down.connect(self.handle_lsp_down)
        client_instance.sig_initialized.connect(self.on_initialize)
        self.sig_register_client_instance_requested.emit(client_instance)
