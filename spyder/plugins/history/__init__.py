# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.history
===========

History plugin.
"""

from spyder.plugins.history.plugin import HistoryLog

# The following statement is required to be able to grab internal plugins.
PLUGIN_CLASSES = [HistoryLog]
