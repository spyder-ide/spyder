# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

from unittest.mock import MagicMock

# Third party imports
from qtpy.QtCore import Signal, QObject
from qtpy.QtWidgets import QApplication, QMainWindow
import pytest

# This is necessary to run these tests independently from the rest in our
# test suite.
# NOTE: Don't move it to another place; it needs to be before importing the
# Pylint plugin below.
# Fixes spyder-ide/spyder#17071
if QApplication.instance() is None:
    app = QApplication([])

# Local imports
from spyder.plugins.pylint.plugin import Pylint
from spyder.plugins.preferences.tests.conftest import config_dialog


class MainWindowMock(QMainWindow):
    sig_editor_focus_changed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.editor = MagicMock()
        self.editor.sig_editor_focus_changed = self.sig_editor_focus_changed
        self.projects = MagicMock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [Pylint]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
