# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the text debugger manager.
"""
from spyder.api.manager import Manager


class DebuggerManager(Manager):
    """
    Manages adding/removing breakpoint from the editor.
    """
    def __init__(self, editor):
        super(DebuggerManager, self).__init__(editor)
