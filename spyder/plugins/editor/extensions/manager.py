# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Editor extensions manager.
"""

# Standard library imports
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

# Local imports
from spyder.plugins.editor.api.manager import Manager


if TYPE_CHECKING:
    from spyder.plugins.editor.api.editorextension import EditorExtension


logger = logging.getLogger(__name__)


class EditorExtensionsManager(Manager):
    """Manage the editor extensions of a CodeEditor widget."""

    def __init__(self, editor):
        """Initialize and add a reference to the editor."""
        super().__init__(editor)
        self._extensions: dict[str: EditorExtension] = {}

    def add(self, extension: "EditorExtension") -> "EditorExtension":
        """
        Add an extension to the editor.

        Parameters
        ----------
        extension: EditorExtension
            The extension instance to add.

        Returns
        -------
        extension: EditorExtension
            The added extension
        """
        logger.debug('adding extension {}'.format(extension.name))
        self._extensions[extension.name] = extension
        extension.on_install(self.editor)
        return extension

    def remove(
        self, name_or_klass: str | type["EditorExtension"]
    ) -> "EditorExtension":
        """
        Remove an extension from the editor.

        Parameters
        ----------
        name_or_klass: str or type[EditorExtension]
            The name or class of the extension to remove.

        Returns
        -------
        extension: EditorExtension
            The removed extension.
        """
        logger.debug('removing extension {}'.format(name_or_klass))
        extension = self.get(name_or_klass)
        extension.on_uninstall()
        self._extensions.pop(extension.name)
        return extension

    def clear(self) -> None:
        """Remove all extensions from the editor."""
        while len(self._extensions):
            key = sorted(list(self._extensions.keys()))[0]
            self.remove(key)

    def get(
        self, name_or_klass: str | type["EditorExtension"]
    ) -> "EditorExtension":
        """
        Get an extension by name or class.

        Parameters
        ----------
        name_or_klass: str or type[EditorExtension]
            The name or class of the extension to get.

        Returns
        -------
        EditorExtension.
        """
        if not isinstance(name_or_klass, str):
            name_or_klass = name_or_klass.__name__

        return self._extensions[name_or_klass]

    def keys(self) -> list[str]:
        """Return the name list of the installed extensions."""
        return list(self._extensions.keys())

    def values(self) -> list["EditorExtension"]:
        """Return the list of installed extensions."""
        return list(self._extensions.values())

    def __len__(self):
        """Return the amount of installed extensions."""
        return len(self._extensions)

    def __iter__(self):
        """Return the list of extensions."""
        return iter([v for k, v in sorted(self._extensions.items())])
