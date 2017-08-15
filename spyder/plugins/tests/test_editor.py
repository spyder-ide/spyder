# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for the Editor plugin."""

# Third party imports
import pytest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

from qtpy.QtWidgets import QWidget


@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    monkeypatch.setattr('spyder.dependencies', Mock())
    from spyder.plugins.editor import Editor

    monkeypatch.setattr('spyder.plugins.editor.IntrospectionManager', Mock())
    monkeypatch.setattr('spyder.plugins.editor.add_actions', Mock())

    class MainMock(QWidget):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            else:
                return Mock()

    editor = Editor(MainMock())
    qtbot.addWidget(editor)
    editor.show()

    return editor, qtbot


def test_basic_initialization(setup_editor):
    """Test Editor plugin initialization."""
    editor, qtbot = setup_editor

    # Assert that editor exists
    assert editor is not None
