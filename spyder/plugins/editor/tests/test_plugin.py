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

from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.utils.qthelpers import qapplication


# ---- Qt Test Fixtures
@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    qapplication()
    from spyder.plugins.editor.plugin import Editor

    monkeypatch.setattr('spyder.plugins.editor.plugin.add_actions', Mock())

    class MainMock(QMainWindow):
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

    window = MainMock()
    editor = Editor(window)
    window.setCentralWidget(editor)
    window.resize(640, 480)
    qtbot.addWidget(window)
    window.show()

    yield editor
    editor.close()


@pytest.fixture(scope="module")
def python_files(tmpdir_factory):
    """Create and save some python codes in temporary files."""
    tmpdir = tmpdir_factory.mktemp("files")
    tmpdir = osp.normcase(tmpdir.strpath)

    filenames = [osp.join(tmpdir, f) for f in
                 ('file1.py', 'file2.py', 'file3.py', 'file4.py')]
    for filename in filenames:
        with open(filename, 'w') as f:
            f.write("# -*- coding: utf-8 -*-\n"
                    "print(Hello World!)\n")

    return filenames, tmpdir


@pytest.fixture
def editor_open_files(request, setup_editor, python_files):
    """
    Setup an Editor with a set of open files, given a past file in focus.

    If no/None ``last_focused_filename`` is passed, the ``"layout_settings"``
    key is not included in the options dict.
    If no/None ``expected_current_filename``, is assumed to be the first file.
    """
    def _get_editor_open_files(last_focused_filename,
                               expected_current_filename):
        editor, qtbot = setup_editor
        expected_filenames, tmpdir = python_files
        if expected_current_filename is None:
            expected_current_filename = expected_filenames[0]
        expected_current_filename = osp.join(tmpdir, expected_current_filename)
        options_dict = {
            'filenames': expected_filenames,
            'max_recent_files': 20,
            }
        if last_focused_filename is not None:
            splitsettings = [(False,
                              osp.join(tmpdir, last_focused_filename),
                              [1] * len(expected_filenames))]
            layout_dict = {'layout_settings': {'splitsettings': splitsettings}}
            options_dict.update(layout_dict)

        def get_option(option, default=None):
            return options_dict.get(option)
        editor.get_option = get_option

        editor.setup_open_files()
        return editor, qtbot, expected_filenames, expected_current_filename

    return _get_editor_open_files


def test_basic_initialization(setup_editor):
    """Test Editor plugin initialization."""
    editor = setup_editor

    # Assert that editor exists
    assert editor is not None


@pytest.mark.parametrize(
    'last_focused_filename, expected_current_filename',
    [('other_file.py', 'file1.py'),
     ('file1.py', 'file1.py'),
     ('file2.py', 'file2.py'),
     ('file4.py', 'file4.py')
     ])
def test_setup_open_files(editor_open_files, last_focused_filename,
                          expected_current_filename):
    """Test Editor plugin open files setup.

    Test that the file order is preserved during the Editor plugin setup and
    that the current file correspond to the last focused file.
    """
    editor_factory = editor_open_files
    editor, qtbot, expected_filenames, expected_current_filename = (
        editor_factory(last_focused_filename, expected_current_filename))

    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename
    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames


def test_setup_open_files_cleanprefs(editor_open_files):
    """Test that Editor successfully opens files if layout is not defined.

    Regression test for #8458 .
    """
    editor_factory = editor_open_files
    editor, qtbot, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames
    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename


def test_renamed_tree(setup_editor, mocker):
    """Test editor.renamed_tree().

    This tests that the file renaming functions are called correctly,
    but does not test that all the renaming happens in File Explorer,
    Project Explorer, and Editor widget as those aren't part of the plugin.
    """
    editor = setup_editor
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
    editor = setup_editor

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


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-vv', '-rw'])
