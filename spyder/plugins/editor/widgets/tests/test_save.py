# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for EditorStack save methods.
"""

# Standard library imports
import os.path as osp
import sys
from textwrap import dedent
from unittest.mock import Mock

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.editor.panels import DebuggerPanel
from spyder.plugins.editor.widgets import editor
from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri)
from spyder.plugins.outlineexplorer.main_widget import OutlineExplorerWidget


# ---- Helpers
def add_files(editorstack):
    editorstack.close_action.setEnabled(False)
    editorstack.set_find_widget(Mock())
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    editorstack.new('foo.py', 'utf-8', 'a = 1\n'
                                       'print(a)\n'
                                       '\n'
                                       'x = 2')
    editorstack.new('secondtab.py', 'utf-8', 'print(spam)')
    with open(__file__) as f:
        text = f.read()
    editorstack.new(__file__, 'utf-8', text)


# ---- Qt Test Fixtures
@pytest.fixture
def base_editor_bot(qtbot):
    editor_stack = editor.EditorStack(None, [])
    editor_stack.set_find_widget(Mock())
    editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    return editor_stack, qtbot


@pytest.fixture
def editor_bot(base_editor_bot, request):
    """
    Set up EditorStack with CodeEditors containing some Python code.
    The cursor is at the empty line below the code.
    """
    editor_stack, qtbot = base_editor_bot

    show_save_dialog = request.node.get_closest_marker('show_save_dialog')
    if show_save_dialog:
        editor_stack.save_dialog_on_tests = True

    qtbot.addWidget(editor_stack)
    add_files(editor_stack)
    return editor_stack, qtbot


@pytest.fixture
def editor_splitter_bot(qtbot):
    """Create editor splitter."""
    es = editor.EditorSplitter(None, Mock(), [], first=True)
    qtbot.addWidget(es)
    es.show()
    yield es
    es.destroy()


@pytest.fixture
def editor_splitter_layout_bot(editor_splitter_bot):
    """Create editor splitter for testing layouts."""
    es = editor_splitter_bot
    es.plugin.clone_editorstack.side_effect = add_files

    # Setup editor info for this EditorStack.
    add_files(es.editorstack)
    return es


# ---- Tests
@pytest.mark.show_save_dialog
def test_save_if_changed(editor_bot, mocker):
    """Test EditorStack.save_if_changed()."""
    editor_stack, qtbot = editor_bot
    save_if_changed = editor_stack.save_if_changed
    mocker.patch.object(editor.QMessageBox, 'exec_')
    mocker.patch.object(editor_stack, 'save')
    mocker.patch.object(editor_stack.autosave, 'remove_autosave_file')
    editor_stack.save.return_value = True

    # No file changed - returns True.
    editor_stack.data[0].editor.document().setModified(False)
    editor_stack.data[1].editor.document().setModified(False)
    editor_stack.data[2].editor.document().setModified(False)
    assert save_if_changed() is True
    assert not editor_stack.save.called
    assert not editor_stack.autosave.remove_autosave_file.called
    editor_stack.data[0].editor.document().setModified(True)
    editor_stack.data[1].editor.document().setModified(True)
    editor_stack.data[2].editor.document().setModified(True)

    # Cancel button - returns False.
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.Cancel
    assert save_if_changed(index=0, cancelable=True) is False
    assert not editor_stack.save.called
    assert not editor_stack.autosave.remove_autosave_file.called
    assert editor_stack.tabs.currentIndex() == 0

    # Yes button - return value from save().
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.Yes
    assert save_if_changed(index=0, cancelable=True) is True
    assert editor_stack.save.called
    assert not editor_stack.autosave.remove_autosave_file.called

    # YesToAll button - if any save() fails, then return False.
    editor_stack.save.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.YesToAll
    assert save_if_changed() is True
    assert editor_stack.save.call_count == 3
    assert not editor_stack.autosave.remove_autosave_file.called

    # No button - remove autosave, returns True.
    editor_stack.save.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.No
    assert save_if_changed(index=0, cancelable=True) is True
    assert not editor_stack.save.called
    assert editor_stack.autosave.remove_autosave_file.called

    # NoToAll button - remove autosave 3x, returns True.
    editor_stack.save.reset_mock()
    editor_stack.autosave.remove_autosave_file.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.NoToAll
    assert save_if_changed() is True
    assert not editor_stack.save.called
    assert editor_stack.autosave.remove_autosave_file.call_count == 3

    # Tempfile doesn't show message box - always calls save().
    editor.QMessageBox.exec_.reset_mock()
    editor_stack.autosave.remove_autosave_file.reset_mock()
    editor_stack.set_tempfile_path(__file__)
    editor_stack.save.return_value = False
    assert save_if_changed(index=2, cancelable=True) is False
    assert editor_stack.save.called
    assert not editor_stack.autosave.remove_autosave_file.called
    editor.QMessageBox.exec_.assert_not_called()


def test_save(editor_bot, mocker):
    """Test EditorStack.save()."""
    editor_stack, qtbot = editor_bot
    save = editor_stack.save
    mocker.patch.object(editor.QMessageBox, 'exec_')
    mocker.patch.object(editor.os.path, 'isfile')
    mocker.patch.object(editor.encoding, 'write')
    mocker.patch.object(editor_stack, 'save_as')
    mocker.patch.object(editor_stack.autosave, 'remove_autosave_file')
    save_file_saved = editor_stack.file_saved
    editor_stack.file_saved = Mock()
    editor.encoding.write.return_value = 'utf-8'

    # Not modified and not newly created - don't write.
    editor_stack.data[0].editor.document().setModified(False)
    editor_stack.data[0].newly_created = False
    assert save(index=0) is True
    assert not editor.encoding.write.called
    assert not editor_stack.autosave.remove_autosave_file.called
    assert editor_stack.autosave.file_hashes == {}

    # File modified.
    editor_stack.data[0].editor.document().setModified(True)

    # File not saved yet - call save_as().
    editor.os.path.isfile.return_value = False
    editor_stack.save_as.return_value = 'save_as_called'
    assert save(index=0) == 'save_as_called'
    editor_stack.save_as.assert_called_with(index=0)
    assert not editor.encoding.write.called
    assert not editor_stack.autosave.remove_autosave_file.called
    assert editor_stack.autosave.file_hashes == {}

    # Force save.
    editor.os.path.isfile.return_value = True
    assert save(index=0, force=True)
    assert editor.encoding.write.called == 1
    editor_stack.file_saved.emit.assert_called_with(
        str(id(editor_stack)), 'foo.py', 'foo.py')
    editor_stack.autosave.remove_autosave_file.assert_called_with(
        editor_stack.data[0].filename)
    expected = {'foo.py': hash('a = 1\nprint(a)\n\nx = 2\n')}
    assert editor_stack.autosave.file_hashes == expected

    editor_stack.file_saved = save_file_saved


def test_file_saved_in_other_editorstack(editor_splitter_layout_bot):
    """Test EditorStack.file_saved_in_other_editorstack()."""
    es = editor_splitter_layout_bot
    es.split()
    # Represents changed editor stack.
    panel1 = es.editorstack
    # Represents split editor stack.
    panel2 = es.widget(1).editorstack

    # Tabs match.
    for i in range(3):
        assert panel1.data[i].filename == panel2.data[i].filename

    # Rearrange tabs on first panel so that tabs aren't the same anymore.
    panel1.tabs.tabBar().moveTab(0, 1)
    assert panel1.data[0].filename == panel2.data[1].filename
    assert panel1.data[1].filename == panel2.data[0].filename
    assert panel1.data[2].filename == panel2.data[2].filename

    # Call file_saved_in_other_editorstack to align stacks.
    panel2.file_saved_in_other_editorstack(panel1.data[0].filename,
                                           panel1.data[0].filename)
    panel2.file_saved_in_other_editorstack(panel1.data[1].filename,
                                           panel1.data[1].filename)
    # Originally this test showed that using index as an arg instead
    # of the original_filename would incorrectly update the names on panel2.
    # See spyder-ide/spyder#5703.
    assert panel1.data[0].filename == panel2.data[1].filename
    assert panel1.data[1].filename == panel2.data[0].filename
    assert panel1.data[2].filename == panel2.data[2].filename


def test_select_savename(editor_bot, mocker):
    """Test EditorStack.select_savename()."""
    editor_stack, qtbot = editor_bot
    select_savename = editor_stack.select_savename
    mocker.patch.object(editor, 'getsavefilename')
    save_redirect_stdio = editor_stack.redirect_stdio
    editor_stack.redirect_stdio = Mock()

    # Cancel selection.
    editor.getsavefilename.return_value = ('', '')
    assert select_savename(__file__) is None

    # Select same name.
    editor.getsavefilename.return_value = (__file__, '')
    assert select_savename(__file__) == __file__

    # Select different name.
    editor.getsavefilename.return_value = ('mytest.py', '')
    assert select_savename(__file__) == 'mytest.py'

    # Restore.
    editor_stack.redirect_stdio = save_redirect_stdio


def test_save_as(editor_bot, mocker):
    """Test EditorStack.save_as()."""
    editor_stack, qtbot = editor_bot
    save_as = editor_stack.save_as
    mocker.patch.object(editor.encoding, 'write')
    mocker.patch.object(editor_stack, 'save')
    mocker.patch.object(editor_stack, 'close_file')
    mocker.patch.object(editor_stack, 'select_savename')
    mocker.patch.object(editor_stack, 'rename_in_data')
    mocker.patch.object(editor_stack, 'refresh')
    save_file_renamed_in_data = editor_stack.file_renamed_in_data
    editor_stack.file_renamed_in_data = Mock()
    editor.encoding.write.return_value = 'utf-8'
    editor_stack.save.return_value = True

    # No save name.
    editor_stack.select_savename.return_value = None
    assert save_as() is False
    assert not editor_stack.save.called

    # Save name is in the stack, but not the current index.
    editor_stack.select_savename.return_value = 'foo.py'
    editor_stack.close_file.return_value = False
    assert save_as(index=2) is None
    assert not editor_stack.save.called

    # Save name is in the stack, but not the current index.
    editor_stack.close_file.return_value = True
    assert save_as(index=2) is True
    editor_stack.close_file.assert_called_with(0)
    assert editor_stack.save.called
    # This index is one less because the tab with the saved name was closed.
    editor_stack.rename_in_data.assert_called_with(__file__,
                                                   new_filename='foo.py')
    assert editor_stack.file_renamed_in_data.emit.called == 1
    assert editor_stack.save.called == 1
    assert editor_stack.refresh.called == 1

    # Restore.
    editor_stack.file_renamed_in_data = save_file_renamed_in_data


@pytest.mark.show_save_dialog
def test_save_as_with_outline(completions_editor, mocker, qtbot, tmpdir):
    """
    Test EditorStack.save_as() when the outline explorer is active.

    Regression test for issues spyder-ide/spyder#7754 and
    spyder-ide/spyder#15517.
    """
    file_path, editorstack, code_editor, completion_plugin = completions_editor
    proxy = code_editor.oe_proxy

    # Set outline explorer to editor stack and refresh it.
    outline_explorer = OutlineExplorerWidget(None, None, None)
    treewidget = outline_explorer.treewidget
    outline_explorer.show()
    treewidget.is_visible = True

    editorstack.set_outlineexplorer(outline_explorer)
    qtbot.addWidget(editorstack.outlineexplorer)
    editorstack.outlineexplorer.register_editor(proxy)

    outline_explorer.start_symbol_services('python')
    editorstack.refresh()

    # Add some code to the test file and save it
    code = dedent("""
        def foo(x):
            return x

        def bar(y):
            return y
    """)

    code_editor.set_text(code)
    editorstack.save(force=True)

    # Notify changes
    with qtbot.waitSignal(
        code_editor.completions_response_signal, timeout=30000
    ):
        code_editor.document_did_change()

    # Wait until the outline is filled
    qtbot.waitUntil(
        lambda: len(treewidget.editor_tree_cache[proxy.get_id()]) > 0,
        timeout=5000
    )

    # No save name.
    mocker.patch.object(editorstack, 'select_savename', return_value=None)
    assert editorstack.save_as() is False

    # Save file as foo2.py in tmpdir
    new_filename = osp.join(tmpdir.strpath, 'foo2.py')
    editorstack.select_savename.return_value = new_filename
    assert not osp.exists(new_filename)

    # Symbols should have been requested for the renamed file, which emits the
    # signals below.
    with qtbot.waitSignals(
        [proxy.sig_start_outline_spinner,
         proxy.sig_outline_explorer_data_changed],
        timeout=30000
    ):
        assert editorstack.save_as() is True

    assert editorstack.get_filenames() == [new_filename]
    assert osp.exists(new_filename)

    # Wait until the outline is filled
    qtbot.waitUntil(
        lambda: len(treewidget.editor_tree_cache[proxy.get_id()]) > 0,
        timeout=5000
    )

    # Assert root and symbol items have the right path.
    items = treewidget.editor_items[proxy.get_id()]
    root_item = items.node

    assert root_item.path == new_filename
    assert items.path == new_filename
    assert all([item.path == new_filename for item in items.children])


def test_save_copy_as(editor_bot, mocker):
    """Test EditorStack.save_copy as()."""
    editor_stack, qtbot = editor_bot
    save_copy_as = editor_stack.save_copy_as
    mocker.patch.object(editor.QMessageBox, 'exec_')
    mocker.patch.object(editor.encoding, 'write')
    mocker.patch.object(editor_stack, 'close_file')
    mocker.patch.object(editor_stack, 'select_savename')
    save_plugin_load = editor_stack.plugin_load
    editor_stack.plugin_load = Mock()
    editor.encoding.write.return_value = 'utf-8'

    # No save name.
    editor_stack.select_savename.return_value = None
    assert save_copy_as() is False
    assert not editor.encoding.write.called

    # Save name is in the stack, but not the current index.
    editor_stack.select_savename.return_value = 'foo.py'
    editor_stack.close_file.return_value = False
    assert save_copy_as(index=2) is None
    assert not editor.encoding.write.called

    # Save name is in the stack, but not the current index.
    editor_stack.close_file.return_value = True
    assert save_copy_as(index=2) is True
    editor_stack.close_file.assert_called_with(0)
    assert editor.encoding.write.called
    editor_stack.plugin_load.emit.assert_called_with('foo.py')

    # Restore mocked objects.
    editor_stack.plugin_load = save_plugin_load


def test_save_all(editor_bot, mocker):
    """Test EditorStack.save_all()."""
    editor_stack, qtbot = editor_bot
    save_all = editor_stack.save_all
    mocker.patch.object(editor_stack, 'save')
    # Save return value isn't used in save_all.
    editor_stack.save.return_value = False

    save_all()
    assert editor_stack.save.call_count == 3
    editor_stack.save.assert_any_call(0, save_new_files=True)
    editor_stack.save.assert_any_call(1, save_new_files=True)
    editor_stack.save.assert_any_call(2, save_new_files=True)
    with pytest.raises(AssertionError):
        editor_stack.save.assert_any_call(3, save_new_files=True)


@pytest.mark.show_save_dialog
def test_save_as_change_file_type(editor_bot, mocker, tmpdir):
    """
    Test EditorStack.save_as() when changing the file type.

    Regression test for spyder-ide/spyder#13085.
    """
    editorstack, qtbot = editor_bot

    # Set and assert the initial state.
    editorstack.tabs.setCurrentIndex(1)
    assert editorstack.get_current_filename() == 'secondtab.py'
    editor = editorstack.get_current_editor()
    mocker.patch.object(editor, 'notify_close')
    editorstack.sig_open_file = Mock()

    # Save file with a different extension.
    new_filename = osp.join(tmpdir.strpath, 'foo.R')
    mocker.patch.object(editorstack, 'select_savename',
                        return_value=new_filename)
    assert not osp.exists(new_filename)
    assert editorstack.save_as() is True
    assert editorstack.get_filenames() == ['foo.py', new_filename, __file__]
    assert osp.exists(new_filename)

    # Assert the new language was assigned correctly
    assert editor.language == 'R'

    # Assert highlighting is working as expected.
    # This is the lexer name assigned by Pygments
    assert editor.highlighter_class._lexer.name == 'S'

    # Assert we sent notify_close and emitted sig_open_file
    assert editor.notify_close.call_count == 1
    assert editorstack.sig_open_file.emit.called == 1

    # Test the debugger panel is hidden
    debugger_panel = editor.panels.get(DebuggerPanel)
    assert not debugger_panel.isVisible()


@pytest.mark.order(1)
@flaky(max_runs=5)
@pytest.mark.skipif(running_in_ci() and sys.platform.startswith('linux'),
                    reason="Stalls test suite with Linux on CI")
def test_save_when_completions_are_visible(completions_editor, qtbot):
    """
    Test that save works when the completion widget is visible and the user
    press the save shortcut (Ctrl+S).

    Regression test for issue spyder-ide/spyder#14806.
    """
    file_path, editorstack, code_editor, __ = completions_editor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    code_editor.set_text('some = 0\nsomething = 1\n')
    editorstack.save(force=True)
    cursor = code_editor.textCursor()
    code_editor.moveCursor(cursor.End)

    # Complete some -> [some, something]
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'some')
    assert "some" in [x['label'] for x in sig.args[0]]
    assert "something" in [x['label'] for x in sig.args[0]]

    # Press keyboard shortcut corresponding to save
    qtbot.keyPress(
        completion, Qt.Key_S, modifier=Qt.ControlModifier, delay=300)

    # Assert file was saved
    with open(file_path, 'r') as f:
        saved_text = f.read()
    assert saved_text == 'some = 0\nsomething = 1\nsome'

    code_editor.toggle_code_snippets(True)


@pytest.mark.show_save_dialog
def test_save_as_lsp_calls(completions_editor, mocker, qtbot, tmpdir):
    """
    Test that EditorStack.save_as() sends the expected LSP requests.

    Regression test for spyder-ide/spyder#13085 and spyder-ide/spyder#20047
    """
    file_path, editorstack, code_editor, completion_plugin = completions_editor

    mocker.patch.object(code_editor, 'emit_request',
                        wraps=code_editor.emit_request)
    mocker.patch.object(code_editor, 'request_folding',
                        wraps=code_editor.request_folding)
    mocker.patch.object(code_editor, 'request_symbols',
                        wraps=code_editor.request_symbols)
    mocker.patch.object(code_editor, 'handle_folding_range',
                        wraps=code_editor.handle_folding_range)
    mocker.patch.object(code_editor, 'process_symbols',
                        wraps=code_editor.process_symbols)

    def symbols_and_folding_requested():
        return (
            code_editor.request_symbols.call_count == 1
            and code_editor.request_folding.call_count == 1
        )

    def symbols_and_folding_processed():
        return (
            code_editor.process_symbols.call_count == 1
            and code_editor.handle_folding_range.call_count == 1
        )

    # === Set and assert initial state
    assert editorstack.get_current_filename().endswith('test.py')
    assert editorstack.get_current_editor() is code_editor

    code_editor.set_text(dedent("""
        def foo(x):
            a = 0
            b = 1
    """))

    # Folding and symbols are requested some time after text is changed (see
    # usage of textChanged signal and _timer_sync_symbols_and_folding in
    # CodeEditor).
    qtbot.waitUntil(symbols_and_folding_requested, timeout=5000)
    qtbot.waitUntil(symbols_and_folding_processed, timeout=5000)

    # Check response by LSP
    assert code_editor.handle_folding_range.call_args == \
           mocker.call({'params': [(1, 3)]})

    symbols = [
        {
            'name': 'foo',
            'containerName': None,
            'location': {
                'uri': path_as_uri(str(file_path)),
                'range': {
                    'start': {'line': 1, 'character': 0},
                    'end': {'line': 4, 'character': 0}
                }
            },
            'kind': 12
        },
        {
            'name': 'a',
            'containerName': 'foo',
            'location': {
                'uri': path_as_uri(str(file_path)),
                'range': {
                    'start': {'line': 2, 'character': 4},
                    'end': {'line': 2, 'character': 9}
                }
            },
            'kind': 13
        },
        {
            'name': 'b',
            'containerName': 'foo',
            'location': {
                'uri': path_as_uri(str(file_path)),
                'range': {
                    'start': {'line': 3, 'character': 4},
                    'end': {'line': 3, 'character': 9}
                }
            },
            'kind': 13
        }
    ]

    assert code_editor.process_symbols.call_args == \
           mocker.call({'params': symbols})

    # === Reset mocks
    code_editor.emit_request.reset_mock()
    code_editor.request_folding.reset_mock()
    code_editor.request_symbols.reset_mock()
    code_editor.handle_folding_range.reset_mock()
    code_editor.process_symbols.reset_mock()

    # === Use Save as
    new_filename = osp.join(tmpdir.strpath, 'new_filename.py')
    mocker.patch.object(editorstack, 'select_savename',
                        return_value=new_filename)
    assert not osp.exists(new_filename)
    assert editorstack.save_as() is True
    assert editorstack.get_filenames() == [new_filename]
    assert osp.exists(new_filename)

    # === Check that expected LSP calls have been made
    assert code_editor.emit_request.call_count == 2

    # First call: notify_close() must have been called
    call = code_editor.emit_request.call_args_list[0]
    assert call.args[0] == 'textDocument/didClose'
    assert call.args[1]['file'].endswith('test.py')

    # Second call: document_did_open() must have been called
    call = code_editor.emit_request.call_args_list[1]
    assert call.args[0] == 'textDocument/didOpen'
    assert call.args[1]['file'].endswith('new_filename.py')

    # === Append new text
    code_editor.append(dedent("""
            c = 2

        def bar():
            x = 0
            y = -1
    """))

    # === Check that expected (LSP) calls have been made
    qtbot.waitUntil(symbols_and_folding_requested, timeout=5000)
    qtbot.waitUntil(symbols_and_folding_processed, timeout=5000)

    # We could check that emit_request() has been called as expected, however,
    # this is checked impliclity by the asserts below (which check that the LSP
    # responded to the requests).

    # Check that LSP responded with updated folding and symbols information
    assert code_editor.handle_folding_range.call_args == \
           mocker.call({'params': [(1, 5), (7, 9)]})

    # There must be 7 symbols (2 functions and 5 variables)
    assert len(code_editor.process_symbols.call_args.args[0]['params']) == 7


if __name__ == "__main__":
    pytest.main()
