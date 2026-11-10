# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Generic language server client provider."""

from spyder.plugins.languageservices.providers.lsp.config import (
    ServerConfig,
)
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
)

__all__ = ["LanguageServerClientProvider", "ServerConfig"]
