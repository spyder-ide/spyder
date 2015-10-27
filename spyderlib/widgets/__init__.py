# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.widgets
=================

Widgets defined in this module may be used in any other Qt-based application

They are also used in Spyder through the Plugin interface
(see spyderlib.plugins)
"""

from spyderlib.widgets.variableexplorer import arrayeditor
from spyderlib.widgets.variableexplorer import collectionseditor
from spyderlib.widgets.variableexplorer import dataframeeditor
from spyderlib.widgets.variableexplorer import objecteditor
from spyderlib.widgets.variableexplorer import texteditor

# For compatibility with Spyder 2
dicteditor = collectionseditor
