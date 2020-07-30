# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the editor extension API.

Adapted from pyqode/core/api/mode.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/mode.py>
"""

import logging


logger = logging.getLogger(__name__)


class EditorExtension(object):
    """
    Base class for editor extensions.

    An extension is a "thing" that can be installed on an editor to add new
    behaviours or to modify its appearance.

    A panel (model child class) is added to an editor by using the
    PanelsManager:
        - :meth:
            `spyder.plugins.editor.widgets.codeeditor.CodeEditor.panels.append`

    Subclasses may/should override the following methods:

        - :meth:`spyder.api.EditorExtension.on_install`
        - :meth:`spyder.api.EditorExtension.on_uninstall`
        - :meth:`spyder.api.EditorExtension.on_state_changed`

    ..warning: The editor extension will be identified by its class name, this
    means that **there cannot be two editor extensions of the same type on the
    same editor instance!**
    """

    @property
    def editor(self):
        """
        Returns a reference to the parent code editor widget.

        **READ ONLY**

        :rtype: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        """
        if self._editor is not None:
            return self._editor
        else:
            return None

    @property
    def enabled(self):
        """
        Tells if the editor extension is enabled.

        :meth:`spyder.api.EditorExtension.on_state_changed` will be called as
        soon as the editor extension state changed.

        :type: bool
        """
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        if enabled != self._enabled:
            self._enabled = enabled
            self.on_state_changed(enabled)

    def __init__(self):
        """
        EditorExtension name/identifier.
        :class:`spyder.widgets.sourcecode.CodeEditor` uses that as the
        attribute key when you install a editor extension.
        """
        self.name = self.__class__.__name__
        # EditorExtension description
        self.description = self.__doc__
        self._enabled = False
        self._editor = None
        self._on_close = False

    def __del__(self):
        logger.debug('%s.__del__', type(self))

    def on_install(self, editor):
        """
        Installs the extension on the editor.

        :param editor: editor widget instance
        :type editor: spyder.plugins.editor.widgets.codeeditor.CodeEditor

        .. note:: This method is called by editor when you install a
                  EditorExtension.
                  You should never call it yourself, even in a subclasss.

        .. warning:: Don't forget to call **super** when subclassing
        """
        self._editor = editor
        self.enabled = True

    def on_uninstall(self):
        """Uninstalls the editor extension from the editor."""
        self._on_close = True
        self.enabled = False
        self._editor = None

    def on_state_changed(self, state):
        """
        Called when the enable state has changed.

        This method does not do anything, you may override it if you need
        to connect/disconnect to the editor's signals (connect when state is
        true and disconnect when it is false).

        :param state: True = enabled, False = disabled
        :type state: bool
        """
        pass

    def clone_settings(self, original):
        """
        Clone the settings from another editor extension (same class).

        This method is called when splitting an editor widget.
        # TODO at the current estate this is not working

        :param original: other editor extension (must be the same class).

        .. note:: The base method does not do anything, you must implement
            this method for every new editor extension/panel (if you plan on
            using the split feature). You should also make sure any properties
            will be propagated to the clones.
        """
        pass
