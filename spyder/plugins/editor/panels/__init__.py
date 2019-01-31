# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the editor panels.

Panels are widgets used to extend editor functionalities.
"""

from .classfunctiondropdown import ClassFunctionDropdown
from .codefolding import FoldingPanel
from .debugger import DebuggerPanel
from .edgeline import EdgeLine
from .indentationguides import IndentationGuide
from .linenumber import LineNumberArea
from .manager import PanelsManager
from .scrollflag import ScrollFlagArea
