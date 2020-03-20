# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

from unittest.mock import Mock

# Third party imports
from qtpy.QtCore import Signal, QObject
import pytest

# Local imports
from spyder.plugins.pylint.plugin import Pylint
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock(QObject):
    sig_editor_focus_changed = Signal(str)

    def __init__(self):
        super().__init__(None)
        self.editor = Mock()
        self.editor.sig_editor_focus_changed = self.sig_editor_focus_changed


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [Pylint]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
