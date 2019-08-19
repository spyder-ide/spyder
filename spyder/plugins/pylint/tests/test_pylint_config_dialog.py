# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
from qtpy.QtCore import Signal, QObject
import pytest

# Local imports
from spyder.plugins.pylint.plugin import Pylint
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock(QObject):
    sig_editor_focus_changed = Signal(str)

    def __init__(self):
        super(MainWindowMock, self).__init__(None)
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
