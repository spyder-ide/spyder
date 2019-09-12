# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------


"""
spyder.plugins.variableexplorer.widgets.objectexplorer
======================================================

Object explorer widget.
"""

from .attribute_model import DEFAULT_ATTR_COLS, DEFAULT_ATTR_DETAILS
from .tree_item import TreeItem
from .tree_model import TreeModel, TreeProxyModel
from .toggle_column_mixin import ToggleColumnTreeView
from .objectexplorer import ObjectExplorer
