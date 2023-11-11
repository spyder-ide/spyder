# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.preferences
==========================

Preferences plugin
"""

from spyder.api.plugins import Plugins


# We consider these to be the plugins with the most important pages. So, we'll
# show those pages as the first entries in the config dialog
MOST_IMPORTANT_PAGES = [
    Plugins.Appearance,
    Plugins.Application,
    Plugins.MainInterpreter,
    Plugins.Shortcuts,
]
