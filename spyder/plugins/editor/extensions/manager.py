# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the editor extensions controller.

Adapted from pyqode/core/managers/modes.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/raw/master/pyqode/core/managers/modes.py>
"""

# Stdlib imports
import logging

# Local imports
from spyder.api.manager import Manager


logger = logging.getLogger(__name__)


class EditorExtensionsManager(Manager):
    """Manages the list of editor extensions of the CodeEdit widget."""

    def __init__(self, editor):
        """Initialize and add a reference to the editor."""
        super(EditorExtensionsManager, self).__init__(editor)
        self._extensions = {}

    def add(self, extension):
        """
        Add a extension to the editor.

        :param extension: The extension instance to add.

        """
        logger.debug('adding extension {}'.format(extension.name))
        self._extensions[extension.name] = extension
        extension.on_install(self.editor)
        return extension

    def remove(self, name_or_klass):
        """
        Remove a extension from the editor.

        :param name_or_klass: The name (or class) of the extension to remove.
        :returns: The removed extension.
        """
        logger.debug('removing extension {}'.format(name_or_klass))
        extension = self.get(name_or_klass)
        extension.on_uninstall()
        self._extensions.pop(extension.name)
        return extension

    def clear(self):
        """
        Remove all extensions from the editor.

        All extensions are removed fromlist and deleted.
        """
        while len(self._extensions):
            key = sorted(list(self._extensions.keys()))[0]
            self.remove(key)

    def get(self, name_or_klass):
        """
        Get a extension by name (or class).

        :param name_or_klass: The name or the class of the extension to get
        :type name_or_klass: str or type
        :rtype: spyder.api.mode.EditorExtension
        """
        if not isinstance(name_or_klass, str):
            name_or_klass = name_or_klass.__name__
        return self._extensions[name_or_klass]

    def keys(self):
        """
        Return the list of the names of the installed extensions.
        """
        return self._extensions.keys()

    def values(self):
        """
        Return the list of installed extensions.
        """
        return self._extensions.values()

    def __len__(self):
        """Return the amount of installed extensions."""
        return len(list(self._extensions.values()))

    def __iter__(self):
        """
        Return the list of extensions.

        :return:
        """
        return iter([v for k, v in sorted(self._extensions.items())])
