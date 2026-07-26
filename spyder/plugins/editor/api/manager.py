# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Editor manager API.
"""

# Standard library imports
from typing import TYPE_CHECKING
import weakref


if TYPE_CHECKING:
    from spyder.plugins.editor.widgets.codeeditor import CodeEditor


class Manager:
    """
    Object that manages a specific aspect of a CodeEditor instance.

    Managers are typically created internally when you create a CodeEditor (
    e.g. the panels and extensions manager).

    See the BreakpointsManager in the Debugger plugin for an example of a
    manager created by an external plugin.
    """

    def __init__(self, editor: "CodeEditor"):
        """
        Initialize manager.

        Parameters
        ----------
        editor: CodeEditor
            Editor instance to manage.
        """
        super().__init__()

        self._editor = weakref.ref(editor)

    @property
    def editor(self) -> "CodeEditor":
        """Return a reference to the parent CodeEditor widget."""
        return self._editor()
