# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Editor plugin."""

# Standard library imports
import os.path as osp
import shutil

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.utils.autosave import AutosaveForPlugin


# =============================================================================
# ---- Tests
# =============================================================================
def test_basic_initialization(editor_plugin):
    """Test Editor plugin initialization."""
    editor = editor_plugin

    # Assert that editor exists
    assert editor is not None


@pytest.mark.parametrize(
    'last_focused_filename, expected_current_filename',
    [('other_file.py', 'file1.py'),
     ('file1.py', 'file1.py'),
     ('file2.py', 'file2.py'),
     ('file4.py', 'file4.py')
     ])
def test_setup_open_files(editor_plugin_open_files, last_focused_filename,
                          expected_current_filename):
    """Test Editor plugin open files setup.

    Test that the file order is preserved during the Editor plugin setup and
    that the current file correspond to the last focused file.
    """
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(last_focused_filename, expected_current_filename))

    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename
    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames


def test_setup_open_files_cleanprefs(editor_plugin_open_files):
    """Test that Editor successfully opens files if layout is not defined.

    Regression test for spyder-ide/spyder#8458.
    """
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    filenames = editor.get_current_editorstack().get_filenames()
    filenames = [osp.normcase(f) for f in filenames]
    assert filenames == expected_filenames
    current_filename = editor.get_current_editorstack().get_current_filename()
    current_filename = osp.normcase(current_filename)
    assert current_filename == expected_current_filename


def test_renamed_tree(editor_plugin, mocker):
    """Test editor.renamed_tree().

    This tests that the file renaming functions are called correctly,
    but does not test that all the renaming happens in File Explorer,
    Project Explorer, and Editor widget as those aren't part of the plugin.
    """
    editor = editor_plugin
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


def test_no_template(editor_plugin):
    """
    Test that new files can be opened when no template is found.
    """
    editor = editor_plugin

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


def test_editor_has_autosave_component(editor_plugin):
    """Test that Editor includes an AutosaveForPlugin."""
    editor = editor_plugin
    assert isinstance(editor.autosave, AutosaveForPlugin)


def test_autosave_component_do_autosave(editor_plugin, mocker):
    """Test that AutosaveForPlugin's do_autosave() calls the current editor
    stack's autosave_all()."""
    editor = editor_plugin
    editorStack = editor.get_current_editorstack()
    mocker.patch.object(editorStack.autosave, 'autosave_all')
    editor.autosave.do_autosave()
    assert editorStack.autosave.autosave_all.called


def test_editor_transmits_sig_option_changed(editor_plugin, qtbot):
    editor = editor_plugin
    editorStack = editor.get_current_editorstack()
    with qtbot.waitSignal(editor.sig_option_changed) as blocker:
        editorStack.sig_option_changed.emit('autosave_mapping', {1: 2})
    assert blocker.args == ['autosave_mapping', {1: 2}]


def test_editorstacks_share_autosave_data(editor_plugin, qtbot):
    """Check that two EditorStacks share the same autosave data."""
    editor = editor_plugin
    editor.editorsplitter.split()
    assert len(editor.editorstacks) == 2
    autosave1 = editor.editorstacks[0].autosave
    autosave2 = editor.editorstacks[1].autosave
    assert autosave1.name_mapping is autosave2.name_mapping
    assert autosave1.file_hashes is autosave2.file_hashes


# The mock_RecoveryDialog fixture needs to be called before setup_editor, so
# it needs to be mentioned first
def test_editor_calls_recoverydialog_exec_if_nonempty(
        mock_RecoveryDialog, editor_plugin):
    """Check that editor tries to exec a recovery dialog on construction."""
    editor = editor_plugin
    assert mock_RecoveryDialog.return_value.exec_if_nonempty.called


def test_closing_editor_plugin_stops_autosave_timer(editor_plugin):
    editor = editor_plugin
    assert editor.autosave.timer.isActive()
    editor.closing_plugin()
    assert not editor.autosave.timer.isActive()


def test_go_to_prev_next_cursor_position(editor_plugin, python_files):
    """
    Test the previous and next cursor position feature of the Editor.

    Regression test for spyder-ide/spyder#8000.
    """
    filenames, tmpdir = python_files
    editorstack = editor_plugin.get_current_editorstack()

    expected_cursor_pos_history = []
    assert editor_plugin.cursor_pos_history == expected_cursor_pos_history

    # Load the Python test files (4).
    editor_plugin.load(filenames)
    # Open a new file.
    editor_plugin.new()
    # Go to the third file.
    editorstack.set_stack_index(2)
    # Move the cursor within the third file. Note that this new position is
    # not added to the cursor position history.
    editorstack.get_current_editor().set_cursor_position(5)

    # Note that we use the filenames from the editor to define the expected
    # results because those returned by the python_files fixture are
    # normalized, so this would cause issues when assessing the results.
    filenames = editor_plugin.get_filenames()
    expected_cursor_pos_history = [
        (filenames[0], 0),
        (filenames[4], len(editorstack.data[4].get_source_code())),
        (filenames[2], 0)
        ]
    assert editor_plugin.cursor_pos_history == expected_cursor_pos_history

    # Navigate to previous and next cursor positions.

    # The last entry in the cursor position history is overriden by the
    # current cursor position when going to previous or next cursor position,
    # so we need to update the last item of the expected_cursor_pos_history.
    expected_cursor_pos_history[-1] = (filenames[2], 5)

    cursor_index_moves = [-1, 1, 1, -1, -1, -1, 1, -1]
    expected_cursor_pos_indexes = [1, 2, 2, 1, 0, 0, 1, 0]
    for move, index in zip(cursor_index_moves, expected_cursor_pos_indexes):
        if move == -1:
            editor_plugin.go_to_previous_cursor_position()
        elif move == 1:
            editor_plugin.go_to_next_cursor_position()

        assert editor_plugin.cursor_pos_index == index
        assert (editor_plugin.get_current_filename(),
                editor_plugin.get_current_editor().get_position('cursor')
                ) == expected_cursor_pos_history[index]
    assert editor_plugin.cursor_pos_history == expected_cursor_pos_history

    # So we are now expected to be at index 0 in the cursor position history.
    # From there, we go to the fourth file.
    editorstack.set_stack_index(3)

    # We expect that our last action caused the cursor position history to
    # be stripped from the current cursor position index and that the
    # new cursor position is added at the end of the cursor position history.
    expected_cursor_pos_history = expected_cursor_pos_history[:1]
    expected_cursor_pos_history.append((filenames[3], 0))
    assert editor_plugin.cursor_pos_history == expected_cursor_pos_history


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-vv', '-rw'])
