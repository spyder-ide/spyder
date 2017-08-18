# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Copyright © <2013-2016> <Colin Duquesnoy and others, see pyqode/AUTHORS.rst>
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the editor extensions controller.
Adapted from:
https://github.com/pyQode/pyqode.core/raw/master/pyqode/core/managers/modes.py
"""

from spyder.api.manager import Manager
from spyder.config.base import debug_print


class EditorExtensionsManager(Manager):
    """
    Manages the list of editor extensions of the CodeEdit widget.
    """

    def __init__(self, editor):
        super(EditorExtensionsManager, self).__init__(editor)
        self._extensions = {}

    def append(self, extension):
        """
        Adds a extension to the editor.

        :param extension: The extension instance to append.

        """
        debug_print('adding extension {}'.format(extension.name))
        self._extensions[extension.name] = extension
        extension.on_install(self.editor)
        return extension

    def remove(self, name_or_klass):
        """
        Removes a extension from the editor.

        :param name_or_klass: The name (or class) of the extension to remove.
        :returns: The removed extension.
        """
        debug_print('removing extension {}'.format(name_or_klass))
        extension = self.get(name_or_klass)
        extension.on_uninstall()
        self._extensions.pop(extension.name)
        return extension

    def clear(self):
        """
        Removes all extensions from the editor. All extensions are removed from
        list and deleted.

        """
        while len(self._extensions):
            key = sorted(list(self._extensions.keys()))[0]
            self.remove(key)

    def get(self, name_or_klass):
        """
        Gets a extension by name (or class)

        :param name_or_klass: The name or the class of the extension to get
        :type name_or_klass: str or type
        :rtype: spyder.api.mode.EditorExtension
        """
        if not isinstance(name_or_klass, str):
            name_or_klass = name_or_klass.__name__
        return self._extensions[name_or_klass]

    def keys(self):
        """
        Returns the list of the names of the installed extensions.
        """
        return self._extensions.keys()

    def values(self):
        """
        Returns the list of installed extensions.
        """
        return self._extensions.values()

    def __len__(self):
        return len(list(self._extensions.values()))

    def __iter__(self):
        """
        Returns the list of extensions.

        :return:
        """
        return iter([v for k, v in sorted(self._extensions.items())])
