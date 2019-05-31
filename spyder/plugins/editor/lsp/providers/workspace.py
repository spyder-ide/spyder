# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client window handler routines."""

import logging

from spyder.plugins.editor.lsp import LSPRequestTypes
from spyder.plugins.editor.lsp.decorators import handles, send_request

logger = logging.getLogger(__name__)


class WorkspaceProvider:
    @send_request(method=LSPRequestTypes.WORKSPACE_CONFIGURATION_CHANGE,
                  requires_response=False)
    def send_plugin_configurations(self, configurations, *args):
        self.plugin_configurations = configurations
        params = {
            'settings': configurations
        }
        return params
