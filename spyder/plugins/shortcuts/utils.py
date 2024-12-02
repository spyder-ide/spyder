# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcuts utils."""

from dataclasses import dataclass
from typing import List, Optional

from qtpy.QtCore import QObject


@dataclass(frozen=True)
class ShortcutData:
    """Dataclass to represent shortcut data."""

    qobject: Optional[QObject]
    """
    QObject to which the shortcut will be associated.

    Notes
    -----
    This can be None when there's no need to register the shortcut to a
    specific QObject.
    """

    name: str
    """Shortcut name (e.g. "run cell")."""

    context: str
    """
    Name of the shortcut context.

    Notes
    -----
    This can be the plugin name (e.g. "editor" for shortcuts that have
    effect when the Editor is focused) or "_" for global shortcuts.
    """

    plugin_name: Optional[str] = None
    """
    Name of the plugin where the shortcut is defined.

    Notes
    -----
    This is only necessary for third-party plugins that have shortcuts with
    several contexts.
    """

    add_shortcut_to_tip: bool = False
    """Whether to add the shortcut to the qobject's tooltip."""


# List to save shortcut data registered for all widgets
SHORTCUTS_FOR_WIDGETS_DATA: List[ShortcutData] = []
