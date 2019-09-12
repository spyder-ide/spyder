# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.completion
=====================

Here, 'completion' are Qt objects that provide code completion, introspection
and workspace managment functions.
"""

from qtpy.QtCore import QObject, Signal
from spyder.api.plugins import SpyderPlugin


class SpyderCompletionPlugin(QObject, SpyderPlugin):
    """
    Spyder plugin API for completion clients.

    All completion clients must implement this interface in order to interact
    with Spyder CodeEditor and Projects manager.
    """

    # Use this signal to send a response back to the completion manager
    # str: Completion client name
    # int: Request sequence identifier
    # dict: Response dictionary
    sig_response_ready = Signal(str, int, dict)

    # Use this signal to indicate that the plugin is ready
    sig_plugin_ready = Signal(str)

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the completion service
    # Status: Required
    COMPLETION_CLIENT_NAME = None

    def __init__(self, parent):
        QObject.__init__(self, parent)
        SpyderPlugin.__init__(self, parent)
        self.main = parent

    def register_file(self, language, filename, codeeditor):
        """
        Register file to perform completions.
        If a language client is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file
        filename: str
            Filename to register
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the client configurations
        """
        pass

    def send_request(self, language, req_type, req, req_id):
        """
        Process completion/introspection request from Spyder.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        req_id: int
            Request identifier for response
        """
        pass

    def send_notification(self, language, notification_type, notification):
        """
        Send notification to completion server based on Spyder changes.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        notification_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        notification: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        """
        pass

    def send_response(self, response, resp_id):
        """
        Send response for server request.

        Parameters
        ----------
        response: dict
            Response body for server
            {
                **kwargs: response-specific keys
            }
        resp_id: int
            Request identifier for response
        """
        pass

    def broadcast_notification(self, notification_type, notification):
        """
        Send a broadcast notification across all programming languages.

        Parameters
        ----------
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        req: dict
            Request body
            {
                **kwargs: notification-specific parameters
            }
        req_id: int
            Request identifier for response, None if notification
        """
        pass

    def update_configuration(self):
        """Handle completion option configuration updates."""
        pass

    def project_path_update(self, project_path, update_kind):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder modified
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.WorkspaceUpdateKind`
        """
        pass

    def start_client(self, language):
        """
        Start completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to start analyzing

        Returns
        -------
        bool
            True if language client could be started, otherwise False.
        """
        return False

    def stop_client(self, language):
        """
        Stop completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to stop analyzing
        """
        pass

    def start(self):
        """Start completion plugin."""
        self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME)

    def shutdown(self):
        """Stop completion plugin."""
        pass
