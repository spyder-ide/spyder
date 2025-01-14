# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Editor plugin."""

# Standard library imports
import os
import os.path as osp
import shutil

# Third party imports
from qtpy.QtCore import Qt
import pytest

# Local imports
from spyder.api.plugins import Plugins
from spyder.plugins.editor.utils.autosave import AutosaveForPlugin
from spyder.plugins.editor.widgets.editorstack import editorstack as editor_module
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.run.api import RunContext
from spyder.utils.sourcecode import get_eol_chars, get_eol_chars_from_os_name


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


def test_restore_open_files(qtbot, editor_plugin_open_files):
    """Test restoring of opened files without Projects plugin"""
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    # Pre-condition: Projects plugin is disabled
    assert editor.get_plugin(Plugins.Projects, error=False) is None

    # `expected_filenames` is modified. A copy is required because
    # `expected_filenames` and `editor.get_conf("filesnames")` are the same
    # object.
    expected_filenames = expected_filenames.copy()
    assert expected_filenames is not editor.get_conf("filenames")
    for i in range(2):
        filename = expected_filenames.pop()
        editor.close_file_from_name(filename)

    # Close editor and check that opened files are saved
    editor.on_close()
    filenames = [osp.normcase(f) for f in editor.get_conf("filenames")]
    assert filenames == expected_filenames

    # “Re-open” editor and check the opened files are restored
    editor.setup_open_files(close_previous_files=True)
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


def test_open_untitled_files(editor_plugin_open_files):
    """
    Test for checking the counter of the untitled files is starting
    correctly when there is one or more `untitledx.py` files saved.

    Regression test for spyder-ide/spyder#7831
    """
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    editor.new()
    filenames = editor.get_current_editorstack().get_filenames()
    new_filename = filenames[-1]
    assert 'untitled5.py' in new_filename


def test_renamed_tree(editor_plugin, mocker):
    """Test editor.renamed_tree().

    This tests that the file renaming functions are called correctly,
    but does not test that all the renaming happens in File Explorer,
    Project Explorer, and Editor widget as those aren't part of the plugin.
    """
    editor = editor_plugin
    editor_main_widget = editor.get_widget()
    mocker.patch.object(editor_main_widget, 'get_filenames')
    mocker.patch.object(editor_main_widget, 'renamed')
    if os.name == "nt":
        filenames = [r'C:\test\directory\file1.py',
                     r'C:\test\directory\file2.txt',
                     r'C:\home\spyder\testing\file3.py',
                     r'C:\test\directory\file4.rst']
        expected = [r'C:\test\dir\file1.py',
                    r'C:\test\dir\file2.txt',
                    r'C:\home\spyder\testing\file3.py',
                    r'C:\test\dir\file4.rst']
        sourcedir = r'C:\test\directory'
        destdir = r'C:\test\dir'
    else:
        filenames = ['/test/directory/file1.py',
                     '/test/directory/file2.txt',
                     '/home/spyder/testing/file3.py',
                     '/test/directory/file4.rst']
        expected = ['/test/dir/file1.py',
                    '/test/dir/file2.txt',
                    '/home/spyder/testing/file3.py',
                    '/test/dir/file4.rst']
        sourcedir = '/test/directory'
        destdir = '/test/dir'

    editor_main_widget.get_filenames.return_value = filenames

    editor_main_widget.renamed_tree(sourcedir, destdir)
    assert editor_main_widget.renamed.call_count == 3
    for file in [0, 1, 3]:
        editor_main_widget.renamed.assert_any_call(
            source=filenames[file],
            dest=expected[file]
        )


def test_no_template(editor_plugin):
    """
    Test that new files can be opened when no template is found.
    """
    editor = editor_plugin

    # Move template to another file to simulate the lack of it
    template = editor.get_widget().TEMPLATE_PATH
    shutil.move(template, osp.join(osp.dirname(template), 'template.py.old'))

    # Open a new file
    editor.new()

    # Get contents
    code_editor = editor.get_widget().get_focus_widget()
    contents = code_editor.get_text('sof', 'eof')

    # Assert contents are empty
    assert not contents

    # Revert template back
    shutil.move(osp.join(osp.dirname(template), 'template.py.old'), template)


def test_editor_has_autosave_component(editor_plugin):
    """Test that Editor includes an AutosaveForPlugin."""
    editor = editor_plugin
    assert isinstance(editor.get_widget().autosave, AutosaveForPlugin)


def test_autosave_component_do_autosave(editor_plugin, mocker):
    """Test that AutosaveForPlugin's do_autosave() calls the current editor
    stack's autosave_all()."""
    editor = editor_plugin
    editorStack = editor.get_current_editorstack()
    mocker.patch.object(editorStack.autosave, 'autosave_all')
    editor.get_widget().autosave.do_autosave()
    assert editorStack.autosave.autosave_all.called


def test_editorstacks_share_autosave_data(editor_plugin, qtbot):
    """Check that two EditorStacks share the same autosave data."""
    editor = editor_plugin.get_widget()
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
    assert mock_RecoveryDialog.return_value.exec_if_nonempty.called


def test_closing_editor_plugin_stops_autosave_timer(editor_plugin):
    editor = editor_plugin
    assert editor.get_widget().autosave.timer.isActive()
    editor.get_widget().close()
    assert not editor.get_widget().autosave.timer.isActive()


def test_renamed_propagates_to_autosave(editor_plugin_open_files, mocker):
    """Test that editor.renamed() propagates info to autosave component if,
    and only if, renamed file is open in editor.

    Regression test for spyder-ide/spyder#11348"""
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    editorstack = editor.get_current_editorstack()
    mocker.patch.object(editorstack, 'rename_in_data')
    mocker.patch.object(editorstack.autosave, 'file_renamed')

    # Test renaming a file that is not opened in the editor
    editor.renamed('nonexisting', 'newname')
    assert not editorstack.autosave.file_renamed.called

    # Test renaming a file that is opened in the editor
    filename = editorstack.get_filenames()[0]
    editor.renamed(filename, 'newname')
    assert editorstack.autosave.file_renamed.called


def test_go_to_prev_next_cursor_position(editor_plugin, python_files):
    """
    Test the previous and next cursor position feature of the Editor.

    Regression test for spyder-ide/spyder#8000.
    """
    filenames, tmpdir = python_files
    main_widget = editor_plugin.get_widget()
    editorstack = editor_plugin.get_current_editorstack()

    expected_cursor_undo_history = []
    assert main_widget.cursor_undo_history == expected_cursor_undo_history
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
    expected_cursor_undo_history = [
        (filenames[0], 0),
        (filenames[-1], len(editorstack.data[-1].get_source_code())),
        (filenames[2], 5)
        ]
    for history, expected_history in zip(main_widget.cursor_undo_history,
                                         expected_cursor_undo_history):
        assert history[0] == expected_history[0]
        # history[1] is a tuple of editor.all_cursor(s)
        # only a single cursor is expected for this test
        assert history[1][0].position() == expected_history[1]

    # Navigate to previous and next cursor positions.

    # The last entry in the cursor position history is overridden by the
    # current cursor position when going to previous or next cursor position,
    # so we need to update the last item of the expected_cursor_undo_history.
    expected_cursor_undo_history[-1] = (filenames[2], 5)

    cursor_index_moves = [-1, 1, 1, -1, -1, -1, 1, -1]
    expected_cursor_pos_indexes = [1, 2, 2, 1, 0, 0, 1, 0]
    for move, index in zip(cursor_index_moves, expected_cursor_pos_indexes):
        if move == -1:
            main_widget.go_to_previous_cursor_position()
        elif move == 1:
            main_widget.go_to_next_cursor_position()
        assert len(main_widget.cursor_undo_history) - 1 == index
        assert (editor_plugin.get_current_filename(),
                editor_plugin.get_current_editor().get_position('cursor')
                ) == expected_cursor_undo_history[index]

    for history, expected_history in zip(main_widget.cursor_undo_history,
                                         expected_cursor_undo_history[:1]):
        assert history[0] == expected_history[0]
        assert history[1][0].position() == expected_history[1]
    for history, expected_history in zip(main_widget.cursor_redo_history,
                                         expected_cursor_undo_history[:0:-1]):
        assert history[0] == expected_history[0]
        assert history[1][0].position() == expected_history[1]

    # So we are now expected to be at index 0 in the cursor position history.
    # From there, we go to the fourth file.
    editorstack.set_stack_index(3)

    # We expect that our last action caused the cursor position history to
    # be stripped from the current cursor position index and that the
    # new cursor position is added at the end of the cursor position history.
    expected_cursor_undo_history = expected_cursor_undo_history[:1]
    expected_cursor_undo_history.append((filenames[3], 0))

    for history, expected_history in zip(main_widget.cursor_undo_history,
                                         expected_cursor_undo_history):
        assert history[0] == expected_history[0]
        assert history[1][0].position() == expected_history[1]
    assert main_widget.cursor_redo_history == []


def test_open_and_close_lsp_requests(editor_plugin_open_files, mocker):
    """
    Test that we send the right LSP requests when opening and closing
    files.
    """
    # Patch methods whose calls we want to check
    mocker.patch.object(CodeEditor, "document_did_open")
    mocker.patch.object(CodeEditor, "notify_close")

    # Create files
    editor_factory = editor_plugin_open_files
    editor, expected_filenames, expected_current_filename = (
        editor_factory(None, None))

    # Assert that we called document_did_open once per file
    assert CodeEditor.document_did_open.call_count == 5

    # Generate a vertical split
    editorstack = editor.get_current_editorstack()
    editorstack.sig_split_vertically.emit()

    # Assert the current codeeditor has is_cloned as True
    codeeditor = editor.get_current_editor()
    assert codeeditor.is_cloned

    # Assert the number of calls to document_did_open is exactly the
    # same as before
    assert CodeEditor.document_did_open.call_count == 5

    # Close cloned editor to verify that notify_close is called from it.
    assert CodeEditor.notify_close.call_count == 0
    editorstack = editor.get_current_editorstack()
    editorstack.close_file()
    assert CodeEditor.notify_close.call_count == 2

    # Assert focus is left in the cloned editorstack
    assert editorstack.get_current_editor().is_cloned

    # Close cloned editorstack to verify that notify_close is not called
    editorstack.close_split()
    assert CodeEditor.notify_close.call_count == 2


@pytest.mark.parametrize('os_name', ['nt', 'mac', 'posix'])
def test_toggle_eol_chars(editor_plugin, python_files, qtbot, os_name):
    """
    Check that changing eol chars from the 'Convert end-of-line characters'
    menu works as expected.
    """
    filenames, tmpdir = python_files
    editorstack = editor_plugin.get_current_editorstack()

    # Load a test file
    fname = filenames[0]
    editor_plugin.load(fname)
    qtbot.wait(500)
    codeeditor = editor_plugin.get_current_editor()

    # Change to a different eol, save and check that file has the right eol.
    editor_plugin.get_widget().toggle_eol_chars(os_name, True)
    assert codeeditor.document().isModified()
    editorstack.save()
    with open(fname, mode='r', newline='') as f:
        text = f.read()
    assert get_eol_chars(text) == get_eol_chars_from_os_name(os_name)


@pytest.mark.order(1)
@pytest.mark.parametrize('os_name', ['nt', 'mac', 'posix'])
def test_save_with_preferred_eol_chars(editor_plugin, python_files, qtbot,
                                       os_name):
    """Check that saving files with preferred eol chars works as expected."""
    filenames, tmpdir = python_files
    editorstack = editor_plugin.get_current_editorstack()
    eol_lookup = {'posix': 'LF', 'nt': 'CRLF', 'mac': 'CR'}

    # Check default options value are set
    qtbot.waitUntil(
        lambda:
            not editorstack.convert_eol_on_save
            and editorstack.convert_eol_on_save_to == 'LF'
    )


    # Load a test file
    fname = filenames[0]
    editor_plugin.load(fname)
    qtbot.wait(500)
    codeeditor = editor_plugin.get_current_editor()

    # Set options
    editor_plugin.set_conf('convert_eol_on_save', True)
    editor_plugin.set_conf('convert_eol_on_save_to', eol_lookup[os_name])
    qtbot.waitUntil(
        lambda:
            editorstack.convert_eol_on_save
            and editorstack.convert_eol_on_save_to == eol_lookup[os_name]
    )

    # Set file as dirty, save it and check that it has the right eol.
    codeeditor.document().setModified(True)
    editorstack.save()
    with open(fname, mode='r', newline='') as f:
        text = f.read()
    assert get_eol_chars(text) == get_eol_chars_from_os_name(os_name)


def test_save_with_os_eol_chars(editor_plugin, mocker, qtbot, tmpdir):
    """Check that saving new files uses eol chars according to OS."""
    editorstack = editor_plugin.get_current_editorstack()

    # Mock output of save file dialog.
    fname = osp.join(tmpdir, 'test_eol_chars.py')
    mocker.patch.object(editor_module, 'getsavefilename')
    editor_module.getsavefilename.return_value = (fname, '')

    # Load new, empty file
    editor_plugin.new()
    qtbot.wait(500)
    codeeditor = editor_plugin.get_current_editor()

    # Write some blank lines on it.
    for __ in range(3):
        qtbot.keyClick(codeeditor, Qt.Key_Return)

    # Save file and check that it has the right eol.
    editorstack.save()
    with open(fname, mode='r', newline='') as f:
        text = f.read()

    assert get_eol_chars(text) == os.linesep


def test_remove_editorstacks_and_windows(editor_plugin, qtbot):
    """
    Check that editor stacks and windows are removed from the list maintained
    for them in the editor when closing editor windows and split editors.

    This is a regression test for spyder-ide/spyder#20144.
    """
    # Create empty file
    editor_plugin.new()

    # Create editor window
    editor_window = editor_plugin.get_widget().create_new_window()
    qtbot.wait(500)  # To check visually that the window was created

    # This is not done automatically by Qt when running our tests (don't know
    # why), but it's done in normal usage. So we need to do it manually
    editor_window.editorwidget.editorstacks[0].deleteLater()

    # Close editor window
    editor_window.close()
    qtbot.wait(500)  # Wait for bit so window objects are actually deleted

    # Check the window objects were removed
    assert len(editor_plugin.get_widget().editorstacks) == 1
    assert len(editor_plugin.get_widget().editorwindows) == 0

    # Split editor and check the focus is given to the cloned editorstack
    editor_plugin.get_widget().editorsplitter.split()
    qtbot.wait(500)  # To check visually that the split was done
    assert editor_plugin.get_current_editor().is_cloned

    # Close editorstack
    editor_plugin.get_current_editorstack().close()
    qtbot.wait(500)  # Wait for bit so the editorstack is actually deleted
    assert len(editor_plugin.get_widget().editorstacks) == 1


def test_register_run_metadata(editor_plugin):
    """
    Check that run metadata is registered for Python files and deregistered for
    non-Python ones on renames.

    This is a regression test for spyder-ide/spyder#22630.
    """
    # Add run config for Python files
    widget = editor_plugin.get_widget()
    widget.supported_run_configurations = {
        "py": {RunContext.File, RunContext.Selection, RunContext.Cell}
    }

    # Create empty file
    editor_plugin.new()

    # Check the file was registered to be run
    editorstack = editor_plugin.get_current_editorstack()
    filename = editorstack.get_filenames()[0]
    assert filename in widget.file_per_id.values()

    # Rename file to a type that can't be run
    editor_plugin.renamed(filename, 'foo.md')

    # Check the file is no longer available to be run
    filename = editorstack.get_filenames()[0]
    assert filename not in widget.file_per_id.values()
    assert widget.file_per_id == {}


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-vv', '-rw'])
