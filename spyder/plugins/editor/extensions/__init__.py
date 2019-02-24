# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Editor Extensions classes and manager.
"""

from .closebrackets import CloseBracketsExtension
from .closequotes import CloseQuotesExtension
from .docstring import DocstringWriterExtension, QMenuOnlyForEnter
from .manager import EditorExtensionsManager
