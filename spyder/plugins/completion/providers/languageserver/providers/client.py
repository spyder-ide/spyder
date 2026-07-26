# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client client handler routines."""

import logging

from lsprotocol import types as lsp

from spyder.plugins.completion.providers.languageserver.decorators import (
    handles,
)

logger = logging.getLogger(__name__)


class ClientProvider:
    @handles(lsp.CLIENT_REGISTER_CAPABILITY)
    def handle_register_capability(
        self, params: lsp.RegistrationParams, *args
    ) -> None:
        """TODO: Handle the glob patterns of the files to watch."""
        for reg in params.registrations:
            logger.debug(
                'Register capability: id=%s method=%s',
                reg.id,
                reg.method,
            )
