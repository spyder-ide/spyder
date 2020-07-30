# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the Manager API.

Adapted from pyqode/core/api/manager.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/manager.py>
"""

# Standard library imports
import weakref


class Manager(object):
    """
    A manager manages a specific aspect of a CodeEditor instance:
        - panels management and drawing

    Managers are typically created internally when you create a CodeEditor.
    You interact with them later.

    ::
        editor = CodeEditor()

        # use the panels controller to install a panel
        editor.panels.install(MyPanel(), MyPanel.Position.Right)
        my_panel = editor.panels.get(MyPanel)

        # and so on

    """

    @property
    def editor(self):
        """Return a reference to the parent CodeEditor widget."""
        return self._editor()

    def __init__(self, editor):
        """:param editor: CodeEditor instance to control."""
        self._editor = weakref.ref(editor)
