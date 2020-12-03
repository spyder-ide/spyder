# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Spyder MS Language Server Protocol v3.0 transport proxy implementation.

This module handles and processes incoming TCP messages sent by an LSP server,
then it relays the information to the actual Spyder LSP client via ZMQ.
"""

import logging
from spyder.plugins.completion.providers.languageserver.transport.common.consumer import (
    IncomingMessageThread)

logger = logging.getLogger(__name__)


class TCPIncomingMessageThread(IncomingMessageThread):
    """TCP socket consumer."""

    def read_num_bytes(self, n):
        return self.fd.recv(n)
