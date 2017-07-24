# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client initialization routines."""

from spyder.utils.code_analysis import LSPRequestTypes
from spyder.utils.code_analysis.decorators import handles


class InitializationProvider:
    @handles(LSPRequestTypes.INITIALIZE)
    def initialize(self):
        pass
