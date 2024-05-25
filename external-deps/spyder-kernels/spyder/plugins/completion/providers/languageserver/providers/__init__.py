# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client method providers."""

from .document import DocumentProvider
from .window import WindowProvider
from .workspace import WorkspaceProvider
from .client import ClientProvider


class LSPMethodProviderMixIn(DocumentProvider, WindowProvider,
                             WorkspaceProvider, ClientProvider):
    pass
