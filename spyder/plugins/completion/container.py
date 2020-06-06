# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main container for the Code completion plugin.
"""

# Standard library imports
import logging
from collections import OrderedDict

# Third-party imports
from qtpy.QtCore import QMutex, QMutexLocker, QTimer, Signal, Slot

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets import PluginMainContainer
from spyder.plugins.completion.api import (LSPRequestTypes, ProviderStatus,
                                           SpyderCompletionProvider)

logger = logging.getLogger(__name__)


class CodeCompletionContainer(PluginMainContainer):

    DEFAULT_OPTIONS = {
        "skip_intermediate_requests": {LSPRequestTypes.DOCUMENT_COMPLETION},
        "source_priority": {},
        "wait_completions_for_ms": 300,
        "wait_for_source": {},
    }

    # Signals
    sig_provider_ready = Signal(str)
    """
    Signal to inform that a provider is ready to provide completions.

    Parameters
    ----------
    provider_name: str
        Unique string provider identifier.
    """

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        self.providers = OrderedDict()  # Order of registry gives priority
        self.requests = {}
        self.language_status = {}
        self.started = False
        self.req_id = 0
        self.collection_mutex = QMutex(QMutex.Recursive)

    # --- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        pass

    def update_actions(self):
        pass

    def on_option_update(self, option, value):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    def register_completion_provider(self, provider):
        """
        Register a completion `provider`.

        Parameters
        ----------
        provider: spyder.plugins.completions.api.SpyderCompletionProvider
            Completion provider instance.
        """
        if not isinstance(provider, SpyderCompletionProvider):
            raise SpyderAPIError(
                "A completion provider must be a subclass of "
                "`SpyderCompletionProvider`")

        provider._check_interface()
        name = provider.NAME
        logger.debug("Completion provider: Registering {0}".format(name))
        self.providers[name] = provider
        provider.sig_response_ready.connect(self.receive_response)
        provider.sig_provider_ready.connect(self.set_provider_available)
        provider.sig_provider_ready.connect(self.sig_provider_ready)

        for language in self.language_status:
            server_status = self.language_status[language]
            server_status[name] = False

    @Slot(str, int, dict)
    def receive_response(self, completion_source, req_id, resp):
        """
        Receive provider responses.

        Parameters
        ----------
        completion_source: str
            Provider unique string name.
        req_id: int
            Request identifier.
        resp: dict
            Response dictionary.
        """
        logger.debug("Completion provider: Request {0} Got response "
                     "from {1}".format(req_id, completion_source))

        if req_id not in self.requests:
            return

        with QMutexLocker(self.collection_mutex):
            request_responses = self.requests[req_id]
            request_responses["sources"][completion_source] = resp
            self.send_to_codeeditor(req_id)

    @Slot(int)
    def receive_timeout(self, req_id):
        """
        Process repsonses after time out.

        Parameters
        ----------
        req_id: int
            Request identifier.
        """
        logger.debug("Completion provider: Request {} timed out".format(
            req_id))

        # On timeout, collect all completions and return to the user
        if req_id not in self.requests:
            return

        with QMutexLocker(self.collection_mutex):
            request_responses = self.requests[req_id]
            request_responses["timed_out"] = True
            self.send_to_codeeditor(req_id)

    def send_to_codeeditor(self, req_id):
        """
        Decide how to send the responses corresponding to req_id to
        the CodeEditor instance that requested them.

        Parameters
        ----------
        req_id: int
            Request identifier.
        """
        if req_id not in self.requests:
            return

        request_responses = self.requests[req_id]

        # Wait between providers to return responses. This will favor the
        # faster completion provider depending
        req_type = request_responses["req_type"]
        wait_for_source = self.get_option("wait_for_source")

        wait_for = set(
            source for source
            in wait_for_source.get(req_type, self.get_provider_names())
            if self.is_provider_running(source)
        )
        timed_out = request_responses["timed_out"]
        all_returned = all(source in request_responses["sources"]
                           for source in wait_for)

        if not timed_out:
            # Before the timeout
            if all_returned:
                self.skip_and_send_to_codeeditor(req_id)
        else:
            # After the timeout
            any_nonempty = any(request_responses["sources"].get(source)
                               for source in wait_for)
            if all_returned or any_nonempty:
                self.skip_and_send_to_codeeditor(req_id)

    def skip_and_send_to_codeeditor(self, req_id):
        """
        Skip intermediate responses coming from the same CodeEditor instance
        for some types of requests, and send the last one to it.

        Parameters
        ----------
        req_id: int
            Request identifier.
        """
        request_responses = self.requests[req_id]
        req_type = request_responses["req_type"]
        response_instance_id = id(request_responses["response_instance"])
        do_send = True

        # This is necessary to prevent sending completions for old requests
        # See spyder-ide/spyder#10798
        if req_type in self.get_option("skip_intermediate_requests"):
            req_ids = [-1]
            for key, item in self.requests.items():
                if (id(item["response_instance"]) == response_instance_id
                        and item["req_type"] == req_type):
                    req_ids.append(key)

            do_send = req_id == max(req_ids)

        logger.debug("Completion provider: Request {} removed".format(req_id))
        del self.requests[req_id]

        # Send only recent responses
        if do_send:
            self.gather_and_send_to_codeeditor(request_responses)

    @Slot(str)
    def set_provider_available(self, provider_name):
        """
        Set the provider status as running.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        """
        provider = self.providers.get(provider_name, None)
        if provider is not None:
            provider.status = ProviderStatus.Running

    def gather_completions(self, req_id_responses):
        """
        Gather completion responses from providers.

        Parameters
        ----------
        req_id_responses: dict
            Responsed by source.
        """
        source_priority = self.get_option("source_priority") or {}
        priorities = source_priority.get(LSPRequestTypes.DOCUMENT_COMPLETION,
                                         self.get_provider_names())
        merge_stats = {source: 0 for source in req_id_responses}
        responses = []
        dedupe_set = set()
        for priority, source in enumerate(priorities):
            if source not in req_id_responses:
                continue

            for response in req_id_responses[source].get("params", []):
                dedupe_key = response["label"].strip()
                if dedupe_key in dedupe_set:
                    continue

                dedupe_set.add(dedupe_key)
                response["sortText"] = (priority, response["sortText"])
                responses.append(response)
                merge_stats[source] += 1

        logger.debug("Responses statistics: {0}".format(merge_stats))
        responses = {"params": responses}
        return responses

    def gather_responses(self, req_type, responses):
        """Gather responses other than completions from plugins."""
        source_priority = self.get_option("source_priority") or {}
        priorities = source_priority.get(req_type, self.get_provider_names())
        response = None
        for source in priorities:
            if source in responses:
                response = responses[source].get("params", None)
                if response:
                    break

        return {"params": response}

    def gather_and_send_to_codeeditor(self, request_responses):
        """
        Gather request responses from all providers and send them to the
        CodeEditor instance that requested them.

        Parameters
        ----------
        request_responses: dict
            Request response from providers.
        """
        req_type = request_responses["req_type"]
        req_id_responses = request_responses["sources"]
        response_instance = request_responses["response_instance"]
        logger.debug("Gather responses for {0}".format(req_type))

        if req_type == LSPRequestTypes.DOCUMENT_COMPLETION:
            responses = self.gather_completions(req_id_responses)
        else:
            responses = self.gather_responses(req_type, req_id_responses)

        try:
            response_instance.handle_response(req_type, responses)
        except RuntimeError:
            # This is triggered when a codeeditor instance has been
            # removed before the response can be processed.
            pass

    def is_provider_running(self, provider_name):
        """
        Check if completion provider is running.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        """
        # FIXME: move this logic to the client
        if provider_name == 'lsp':
            # The LSP plugin does not emit a plugin ready signal
            return provider_name in self.providers

        provider = self.providers.get(provider_name, None)
        if provider is not None:
            return provider.status == ProviderStatus.Running

    def send_request(self, language, req_type, req):
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
        req_id = self.req_id
        self.req_id += 1

        self.requests[req_id] = {
            "language": language,
            "req_type": req_type,
            "response_instance": req["response_instance"],
            "sources": {},
            "timed_out": False,
        }

        # Start the timer on this request
        wait_ms = self.get_option("wait_completions_for_ms")
        if wait_ms > 0:
            QTimer.singleShot(wait_ms, lambda: self.receive_timeout(req_id))
        else:
            self.requests[req_id]["timed_out"] = True

        for provider_name in self.providers:
            provider = self.providers[provider_name]
            provider.send_request(language, req_type, req, req_id)

    def send_notification(self, language, notification_type, notification):
        """

        Parameters
        ----------
        language: str
            Unique language string identifier.
        notification_type: FIXME
            FIXME
        notification: FIXME
            FIXME
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.send_notification(
                    language,
                    notification_type,
                    notification,
                )

    def broadcast_notification(self, req_type, req):
        """
        Broadcaste notification for all clients on all providers.

        Parameters
        ----------
        req_type: str
            See spyder.plugins.completion.api.LSPRequestTypes.
        req: FIXME
            FIXME
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.broadcast_notification(req_type, req)

    # FIXME: rename? update_project_path?
    # FIXME: Use a class for the update_kind text
    def project_path_update(self, project_path, update_kind="addition"):
        """
        FIXME:
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.project_path_update(project_path, update_kind)

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
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.register_file(language, filename, codeeditor)

    def update_configuration(self):
        """
        Update configuration for all providers.
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.update_configuration()

    def start_providers(self):
        """
        Start all completion providers.
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Stopped:
                provider.start()

    def shutdown_providers(self):
        """
        Shutdown all completion providers.
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.shutdown()

    def start_provider_clients(self, language):
        """
        Start all completion provider clients for a given `language`.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        """
        started = False
        language_clients = self.language_status.get(language, {})
        for provider_name in self.providers:
            if self.is_provider_running(provider_name):
                provider = self.providers[provider_name]
                client_started = provider.start_client(language)
                started |= client_started
                language_clients[provider_name] = client_started

        self.language_status[language] = language_clients
        return started

    def stop_provider_clients(self, language):
        """
        Stop all completion provider clients for a given `language`.

        Parameters
        ----------
        language: str
            Unique language string identifier.
        """
        for provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.status == ProviderStatus.Running:
                provider.stop_client(language)

        self.language_status.pop(language)

    def get_provider(self, provider_name):
        """
        Return a completion provider instance by `provider_name`.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        """
        return self.providers.get(provider_name, None)

    def get_provider_names(self):
        """
        Return completion provider names.
        """
        return list(self.providers.keys())

    def set_wait_for_source_requests(self, name, request_types):
        """
        Set which request types should wait for source.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        request_types: list
            List of spyder.plugins.completion.api.LSPRequestTypes.
        """
        if name not in self.providers:
            raise KeyError("Invalid provider name!")

        wait_for_source = self.get_option("wait_for_source")
        for request_type in request_types:
            sources_for_req_type = wait_for_source.get(request_type, set())
            sources_for_req_type.add(name)
            wait_for_source[request_type] = sources_for_req_type

        self.set_option("wait_for_source", wait_for_source)

    def set_request_type_priority(self, provider_name, request_type):
        """
        Set request type top priority for given provider.

        Parameters
        ----------
        provider_name: str
            Unique name of the provider.
        request_type: str
            See spyder.plugins.completion.api.LSPRequestTypes
        """
        source_priority = self.get_option("source_priority")
        if provider_name not in self.providers:
            raise KeyError("Invalid provider name!")

        priorities = source_priority.get(
            request_type,
            self.get_provider_names(),
        )
        priorities.remove(provider_name)
        priorities.insert(0, provider_name)
        source_priority[request_type] = priorities
        self.set_option("source_priority", source_priority)
