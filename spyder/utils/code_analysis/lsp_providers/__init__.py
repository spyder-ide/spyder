# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client method providers."""

from lsp_providers.document import DocumentProvider
from spyder.utils.code_analysis import LSPRequestTypes
from spyder.utils.code_analysis.decorators import handles


class LSPMethodProviderMixIn(DocumentProvider):
    @handles(LSPRequestTypes.INITIALIZE)
    def initialize_resp(self):
        print('This does not make sense!')
