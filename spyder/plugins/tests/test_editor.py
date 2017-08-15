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


@pytest.mark.parametrize(
    'filenames, expected_filenames, splitsettings, expected_splitsettings', [
        (['/file1.py', '/file2.py', '/file3.py', '/file4.py'],
         ['/file1.py', '/file2.py', '/file3.py', '/file4.py'],
         [(False, '/other_file.py', [2, 4, 8, 12])],
         [(False, '/file1.py', [2, 4, 8, 12])]),
        (['/file1.py', '/file2.py', '/file3.py', '/file4.py'],
         ['/file2.py', '/file1.py', '/file3.py', '/file4.py'],
         [(False, '/file2.py', [2, 4, 8, 12])],
         [(False, '/file2.py', [2, 2, 8, 12])]),
        (['/file1.py', '/file2.py', '/file3.py', '/file4.py'],
         ['/file1.py', '/file2.py', '/file3.py', '/file4.py'],
         None,
         None, )
    ])
def test_reorder_filenames(setup_editor, expected_filenames, filenames,
                           splitsettings, expected_splitsettings):
    editor, qtbot = setup_editor

    def get_option(*args):
        if splitsettings is None:
            return None
        return {'splitsettings': splitsettings}

    def set_option(name, layout_settings):
        assert layout_settings['splitsettings'] == expected_splitsettings

    editor.get_option = get_option
    editor.set_option = set_option

    assert expected_filenames == editor.reorder_filenames(filenames)
