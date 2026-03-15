# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
API for editor extensions.
"""

from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from spyder.plugins.editor.widgets.codeeditor import CodeEditor


class EditorExtension:
    """
    Base class for editor extensions.

    An extension is an object that can be installed on an editor to add new
    behaviours or to modify its appearance.

    Subclasses may/should override the following methods:

        - :meth:`spyder.api.EditorExtension.on_install`
        - :meth:`spyder.api.EditorExtension.on_uninstall`
        - :meth:`spyder.api.EditorExtension.on_state_changed`

    Notes
    -----
    * The editor extension will be identified by its class name, this
      means that there cannot be two editor extensions of the same type on
      the same editor instance.
    """

    @property
    def editor(self) -> "CodeEditor":
        """
        Returns a reference to the parent code editor widget.

        This is a read-only attribute.

        :rtype: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        """
        return self._editor

    @property
    def enabled(self) -> bool:
        """
        Tells if the editor extension is enabled.

        :meth:`spyder.api.EditorExtension.on_state_changed` will be called as
        soon as the editor extension state changed.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        if enabled != self._enabled:
            self._enabled = enabled
            self.on_state_changed(enabled)

    def __init__(self):
        self.name = self.__class__.__name__
        self.description = self.__doc__

        self._enabled = False
        self._editor = None
        self._on_close = False

    def on_install(self, editor: "CodeEditor"):
        """
        Install the extension in the editor.

        Parameters
        ----------
        editor: CodeEditor
            The editor widget instance.

        Notes
        -----
        This method is called when the extension is added to the editor. You
        should never call it yourself, even in a subclasss.
        """
        self._editor = editor
        self.enabled = True

    def on_uninstall(self):
        """Uninstall the editor extension from the editor."""
        self._on_close = True
        self.enabled = False
        self._editor = None

    def on_state_changed(self, state: bool):
        """
        This is called when the enabled state has changed.

        This method does not do anything, you may override it if you need
        to connect/disconnect to the editor's signals (connect when state is
        true and disconnect when it is false).

        Parameters
        ----------
        state: bool
            Whether the extension is enabled or disabled.
        """
        pass
