# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.widgets
==================

This package exposes shareable widgets that can be used in
third-party plugins.
"""

from spyder.widgets.tabs import Tabs
from spyder.widgets.comboboxes import PythonModulesComboBox
from spyder.widgets.variableexplorer.texteditor import TextEditor
from spyder.widgets.browser import WebView, FrameWebView
