# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.statusbar
========================

Statusbar plugin providing base widgets and management of status bar widgets.
"""

from spyder.plugins.statusbar.plugin import StatusBar

# The following statement is required to be able to grab internal plugins.
PLUGIN_CLASSES = [StatusBar]
