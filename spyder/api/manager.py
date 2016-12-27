# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Copyright © <2013-2016> <Colin Duquesnoy and others, see pyqode/AUTHORS.rst>
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the Manager API.
Adapted from https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/manager.py
"""
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
