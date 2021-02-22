# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.maininterpreter
==============================

Main interpreter Plugin.
"""

from spyder.plugins.maininterpreter.plugin import MainInterpreter

# The following statement is required to be able to grab internal plugins.
PLUGIN_CLASSES = [MainInterpreter]
