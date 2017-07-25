# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client document handler routines."""

from spyder.utils.code_analysis import LSPRequestTypes
from spyder.utils.code_analysis.decorators import handles


class DocumentProvider:
    @handles(LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_open(self):
        pass
