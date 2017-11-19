# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for EditorStack save methods.
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest

# Local imports
from spyder.widgets import editor


# Helpers
# --------------------------------
def add_files(editorstack):
    editorstack.close_action.setEnabled(False)
    editorstack.set_introspector(Mock())
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


# Qt Test Fixtures
# --------------------------------
@pytest.fixture
def base_editor_bot(qtbot):
    editor_stack = editor.EditorStack(None, [])
    editor_stack.set_introspector(Mock())
    editor_stack.set_find_widget(Mock())
    editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    return editor_stack, qtbot


@pytest.fixture
def editor_bot(base_editor_bot):
    """
    Set up EditorStack with CodeEditors containing some Python code.
    The cursor is at the empty line below the code.
    """
    editor_stack, qtbot = base_editor_bot
    qtbot.addWidget(editor_stack)
    add_files(editor_stack)
    return editor_stack, qtbot


@pytest.fixture
def editor_splitter_bot(qtbot):
    """Create editor splitter."""
    es = editor_splitter = editor.EditorSplitter(None, Mock(), [], first=True)
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


# Tests
# -------------------------------
def test_save_if_changed(editor_bot, mocker):
    """Test EditorStack.save_if_changed()."""
    editor_stack, qtbot = editor_bot
    save_if_changed = editor_stack.save_if_changed
    mocker.patch.object(editor.QMessageBox, 'exec_')
    mocker.patch.object(editor_stack, 'save')
    editor_stack.save.return_value = True

    # No file changed - returns True.
    editor_stack.data[0].editor.document().setModified(False)
    editor_stack.data[1].editor.document().setModified(False)
    editor_stack.data[2].editor.document().setModified(False)
    assert save_if_changed() is True
    assert not editor_stack.save.called
    editor_stack.data[0].editor.document().setModified(True)
    editor_stack.data[1].editor.document().setModified(True)
    editor_stack.data[2].editor.document().setModified(True)

    # Cancel button - returns False.
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.Cancel
    assert save_if_changed(index=0, cancelable=True) is False
    assert not editor_stack.save.called
    assert editor_stack.tabs.currentIndex() == 0

    # Yes button - return value from save().
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.Yes
    assert save_if_changed(index=0, cancelable=True) is True
    assert editor_stack.save.called

    # YesToAll button - if any save() fails, then return False.
    editor_stack.save.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.YesToAll
    assert save_if_changed() is True
    assert editor_stack.save.call_count == 3

    # No button - returns True.
    editor_stack.save.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.No
    assert save_if_changed(index=0, cancelable=True) is True
    assert not editor_stack.save.called

    # NoToAll button - returns True.
    editor_stack.save.reset_mock()
    editor.QMessageBox.exec_.return_value = editor.QMessageBox.NoToAll
    assert save_if_changed() is True
    assert not editor_stack.save.called

    # Tempfile doesn't show message box - always calls save().
    editor.QMessageBox.exec_.reset_mock()
    editor_stack.set_tempfile_path(__file__)
    editor_stack.save.return_value = False
    assert save_if_changed(index=2, cancelable=True) is False
    assert editor_stack.save.called
    editor.QMessageBox.exec_.assert_not_called()


def test_save(editor_bot, mocker):
    """Test EditorStack.save()."""
    editor_stack, qtbot = editor_bot
    save = editor_stack.save
    mocker.patch.object(editor.QMessageBox, 'exec_')
    mocker.patch.object(editor.os.path, 'isfile')
    mocker.patch.object(editor.encoding, 'write')
    mocker.patch.object(editor_stack, 'save_as')
    save_file_saved = editor_stack.file_saved
    editor_stack.file_saved = Mock()
    editor.encoding.write.return_value = 'utf-8'

    # Not modified and not newly created - don't write.
    editor_stack.data[0].editor.document().setModified(False)
    editor_stack.data[0].newly_created = False
    assert save(index=0) is True
    assert not editor.encoding.write.called

    # File modified.
    editor_stack.data[0].editor.document().setModified(True)

    # File not saved yet - call save_as().
    editor.os.path.isfile.return_value = False
    editor_stack.save_as.return_value = 'save_as_called'
    assert save(index=0) == 'save_as_called'
    editor_stack.save_as.assert_called_with(index=0)
    assert not editor.encoding.write.called

    # Force save.
    editor.os.path.isfile.return_value = True
    assert save(index=0, force=True)
    assert editor.encoding.write.called == 1
    editor_stack.file_saved.emit.assert_called_with(str(id(editor_stack)),
                                                    'foo.py', 'foo.py')

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
    # See issue 5703.
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
    editor_stack.save.assert_any_call(0)
    editor_stack.save.assert_any_call(1)
    editor_stack.save.assert_any_call(2)
    with pytest.raises(AssertionError):
        editor_stack.save.assert_any_call(3)


if __name__ == "__main__":
    pytest.main()
