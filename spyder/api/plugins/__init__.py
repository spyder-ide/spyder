# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.plugins
==================

Here, 'plugins' are Qt objects that can make changes to Spyder's main window
and call other plugins directly.

There are two types of plugins available:

1. SpyderPluginV2 is a plugin that does not create a new dock/pane on Spyder's
   main window. Note: SpyderPluginV2 will be renamed to SpyderPlugin once the
   migration to the new API is finished

2. SpyderDockablePlugin is a plugin that does create a new dock/pane on
   Spyder's main window.
"""

from .enum import Plugins, DockablePlugins  # noqa
from .old_api import SpyderPlugin, SpyderPluginWidget  # noqa
from .new_api import SpyderDockablePlugin, SpyderPluginV2  # noqa
