# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for the Editor plugin."""

# Standard library imports
import os.path as osp
import shutil

# Third party imports
import pytest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

from qtpy.QtWidgets import QWidget

# Local imports
from spyder.utils.qthelpers import qapplication


@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    qapplication()
    # monkeypatch.setattr('spyder.dependencies', Mock())
    from spyder.plugins.editor.plugin import Editor

    monkeypatch.setattr('spyder.plugins.editor.plugin.IntrospectionManager', Mock())
    monkeypatch.setattr('spyder.plugins.editor.plugin.add_actions', Mock())

    class MainMock(QWidget):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            elif attr == 'projects':
                projects = Mock()
                projects.get_active_project.return_value = None
                return projects
            else:
                return Mock()

        def get_spyder_pythonpath(*args):
            return []

    editor = Editor(MainMock())
    qtbot.addWidget(editor)
    editor.show()

    yield editor, qtbot


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
         [(False, '/file2.py', [4, 2, 8, 12])]),
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


def test_renamed_tree(setup_editor, mocker):
    """Test editor.renamed_tree().

    This tests that the file renaming functions are called correctly,
    but does not test that all the renaming happens in File Explorer,
    Project Explorer, and Editor widget as those aren't part of the plugin.
    """
    editor, qtbot = setup_editor
    mocker.patch.object(editor, 'get_filenames')
    mocker.patch.object(editor, 'renamed')
    editor.get_filenames.return_value = ['/test/directory/file1.py',
                                         '/test/directory/file2.txt',
                                         '/home/spyder/testing/file3.py',
                                         '/test/directory/file4.rst']

    editor.renamed_tree('/test/directory', '/test/dir')
    assert editor.renamed.call_count == 3
    assert editor.renamed.called_with(source='/test/directory/file1.py',
                                      dest='test/dir/file1.py')
    assert editor.renamed.called_with(source='/test/directory/file2.txt',
                                      dest='test/dir/file2.txt')
    assert editor.renamed.called_with(source='/test/directory/file4.rst',
                                      dest='test/dir/file4.rst')


def test_no_template(setup_editor):
    """
    Test that new files can be opened when no template is found.
    """
    editor, qtbot = setup_editor

    # Move template to another file to simulate the lack of it
    template = editor.TEMPLATE_PATH
    shutil.move(template, osp.join(osp.dirname(template), 'template.py.old'))

    # Open a new file
    editor.new()

    # Get contents
    code_editor = editor.get_focus_widget()
    contents = code_editor.get_text('sof', 'eof')

    # Assert contents are empty
    assert not contents

    # Revert template back
    shutil.move(osp.join(osp.dirname(template), 'template.py.old'), template)
