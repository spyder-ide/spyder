# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Base classes for constructing and accessing top-level Spyder plugin objects.

Here, "plugins" are Qt objects that can make changes to Spyder's main window
and call/connect to other plugins directly.

There are two types of plugins available:

* :class:`SpyderPluginV2` does not create a new pane in Spyder's main window.

   .. note::

       :class:`SpyderPluginV2` will be aliased to :class:`!SpyderPlugin`
       and deprecated in Spyder 6.2, and removed in Spyder 7.0.

* :class:`SpyderDockablePlugin` creates a new pane in Spyder's main window.
"""

from .enum import DockablePlugins, OptionalPlugins, Plugins  # noqa
from .new_api import SpyderDockablePlugin, SpyderPluginV2  # noqa


__all__ = [
    "Plugins",
    "DockablePlugins",
    "OptionalPlugins",
    "SpyderPluginV2",
    "SpyderDockablePlugin",
]
