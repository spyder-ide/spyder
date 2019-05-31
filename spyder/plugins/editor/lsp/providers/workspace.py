# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client window handler routines."""

import logging

from spyder.plugins.editor.lsp import LSPRequestTypes
from spyder.plugins.editor.lsp.decorators import handles

logger = logging.getLogger(__name__)


class WorkspaceProvider:
    pass
