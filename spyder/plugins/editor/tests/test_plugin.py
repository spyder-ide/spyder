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

    Regression test for #8458 .
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


def test_editor_sets_autosave_mapping_on_first_editorstack(editor_plugin):
    """Check that first editor stack gets autosave mapping from config."""
    editor = editor_plugin
    editorStack = editor.get_current_editorstack()
    assert editorStack.autosave_mapping == {}


def test_editor_syncs_autosave_mapping_among_editorstacks(editor_plugin, qtbot):
    """Check that when an editorstack emits a sig_option_changed for
    autosave_mapping, the autosave mapping of all other editorstacks is
    updated."""
    editor = editor_plugin
    editor.editorsplitter.split()
    assert len(editor.editorstacks) == 2
    old_mapping = {}
    for editorstack in editor.editorstacks:
        assert editorstack.autosave_mapping == old_mapping
    new_mapping = {'ham': 'spam'}
    editor.get_current_editorstack().sig_option_changed.emit(
            'autosave_mapping', new_mapping)
    for editorstack in editor.editorstacks:
        if editorstack == editor.get_current_editorstack():
            assert editorstack.autosave_mapping == old_mapping
        else:
            assert editorstack.autosave_mapping == new_mapping


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


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-vv', '-rw'])
