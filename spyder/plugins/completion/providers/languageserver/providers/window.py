# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client window handler routines."""

import logging

from lsprotocol import types as lsp

from spyder.plugins.completion.providers.languageserver.decorators import (
    handles)

logger = logging.getLogger(__name__)


class WindowProvider:

    @handles(lsp.WINDOW_SHOW_MESSAGE)
    def process_show_message(
        self, params: lsp.ShowMessageParams, *args
    ) -> None:
        """Handle window/showMessage notifications from the LSP server."""
        msg_type = params.type
        logger.debug(
            'showMessage [%s]: %s',
            msg_type.name if msg_type else '?',
            params.message,
        )

    @handles(lsp.WINDOW_LOG_MESSAGE)
    def process_log_message(
        self, params: lsp.LogMessageParams, *args
    ) -> None:
        """Handle window/logMessage notifications from the LSP server."""
        msg_type = params.type
        logger.debug(
            'logMessage [%s]: %s',
            msg_type.name if msg_type else '?',
            params.message,
        )
