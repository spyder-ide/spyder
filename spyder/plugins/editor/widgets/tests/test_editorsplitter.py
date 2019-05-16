# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for EditorSplitter class in editor.py
"""

# Standard library imports
try:
    from unittest.mock import Mock
    import pathlib
except ImportError:
    from mock import Mock  # Python 2
    import pathlib2 as pathlib

import os
import os.path as osp
from functools import partial

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.editor.widgets.editor import EditorStack, EditorSplitter


# ---- Qt Test Fixtures

def editor_stack():
    editor_stack = EditorStack(None, [])
    editor_stack.set_find_widget(Mock())
    editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    return editor_stack


@pytest.fixture
def editor_splitter_bot(qtbot):
    """Create editor splitter."""
    es = EditorSplitter(None, Mock(), [], first=True)
    qtbot.addWidget(es)
    es.show()
    return es


@pytest.fixture
def editor_splitter_lsp(qtbot_module, lsp_manager, request):
    text = """
    import sys
    """

    def report_file_open(options):
        filename = options['filename']
        language = options['language']
        callback = options['codeeditor']
        lsp_manager.register_file(
            language.lower(), filename, callback)
        settings = lsp_manager.main.editor.lsp_editor_settings['python']
        callback.start_lsp_services(settings)

        with qtbot_module.waitSignal(
                callback.lsp_response_signal, timeout=30000):
            callback.document_did_open()

    def register_editorstack(editorstack):
        editorstack.perform_lsp_request.connect(lsp_manager.send_request)
        editorstack.sig_open_file.connect(report_file_open)
        settings = lsp_manager.main.editor.lsp_editor_settings['python']
        editorstack.notify_server_ready('python', settings)

    def clone(editorstack, template=None):
        # editorstack.clone_from(template)
        editor_stack = EditorStack(None, [])
        editor_stack.set_find_widget(Mock())
        editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
        # Emulate "cloning"
        editorsplitter.editorstack.new('test.py', 'utf-8', text)

    mock_plugin = Mock()
    editorsplitter = EditorSplitter(
        None, mock_plugin, [], register_editorstack_cb=register_editorstack)

    editorsplitter.editorstack.set_find_widget(Mock())
    editorsplitter.editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    editorsplitter.editorstack.new('test.py', 'utf-8', text)

    mock_plugin.clone_editorstack.side_effect = partial(
        clone, template=editorsplitter.editorstack)
    qtbot_module.addWidget(editorsplitter)
    editorsplitter.show()

    def teardown():
        editorsplitter.hide()
        editorsplitter.close()

    request.addfinalizer(teardown)
    return editorsplitter, lsp_manager


@pytest.fixture
def editor_splitter_layout_bot(editor_splitter_bot):
    """Create editor splitter for testing layouts."""
    es = editor_splitter_bot

    # Allow the split() to duplicate editor stacks.
    def clone(editorstack):
        editorstack.close_action.setEnabled(False)
        editorstack.set_find_widget(Mock())
        editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
        editorstack.new('foo.py', 'utf-8', 'a = 1\nprint(a)\n\nx = 2')
        editorstack.new('layout_test.py', 'utf-8', 'print(spam)')
        with open(__file__) as f:
            text = f.read()
        editorstack.new(__file__, 'utf-8', text)

    es.plugin.clone_editorstack.side_effect = clone

    # Setup editor info for this EditorStack.
    clone(es.editorstack)
    return es


# ---- Tests
def test_init(editor_splitter_bot):
    """"Test __init__."""
    es = editor_splitter_bot
    assert es.orientation() == Qt.Horizontal
    assert es.testAttribute(Qt.WA_DeleteOnClose)
    assert not es.childrenCollapsible()
    assert not es.toolbar_list
    assert not es.menu_list
    assert es.register_editorstack_cb == es.plugin.register_editorstack
    assert es.unregister_editorstack_cb == es.plugin.unregister_editorstack

    # No menu actions in parameter call.
    assert not es.menu_actions
    # EditorStack adds its own menu actions to the existing actions.
    assert es.editorstack.menu_actions != []

    assert isinstance(es.editorstack, EditorStack)
    es.plugin.register_editorstack.assert_called_with(es.editorstack)
    es.plugin.unregister_editorstack.assert_not_called()
    es.plugin.clone_editorstack.assert_not_called()

    assert es.count() == 1
    assert es.widget(0) == es.editorstack


def test_close(editor_splitter_bot, qtbot):
    """Test the inteface for closing the editor splitters."""
    # Split the main editorspliter once, than split the second editorsplitter
    # twice.
    es = editor_splitter_bot

    es.split()
    esw1 = es.widget(1)
    esw1.editorstack.set_closable(True)
    assert es.count() == 2
    assert esw1.count() == 1

    esw1.split()
    esw1w1 = esw1.widget(1)
    esw1w1.editorstack.set_closable(True)
    assert es.count() == 2
    assert esw1.count() == 2
    assert esw1w1.count() == 1

    esw1.split()
    esw1w2 = esw1.widget(2)
    esw1w2.editorstack.set_closable(True)
    assert es.count() == 2
    assert esw1.count() == 3
    assert esw1w1.count() == esw1w2.count() == 1

    # Assert that all the editorsplitters are visible.
    assert es.isVisible()
    assert esw1.isVisible()
    assert esw1w1.isVisible()
    assert esw1w2.isVisible()

    # Close the editorstack of the editorsplitter esw1 and assert that it is
    # not destroyed because it still contains the editorsplitters esw1w1 and
    # esw1w2.
    with qtbot.waitSignal(esw1.editorstack.destroyed, timeout=1000):
        esw1.editorstack.close_split()
    assert es.count() == 2
    assert esw1.count() == 2
    assert esw1.editorstack is None

    assert es.isVisible()
    assert esw1.isVisible()
    assert esw1w1.isVisible()
    assert esw1w2.isVisible()

    # Close the editorstack of the editorsplitter esw1w1, assert it is
    # correctly destroyed afterwards on the Qt side and that it is correctly
    # removed from the editorsplitter esw1.
    with qtbot.waitSignal(esw1w1.destroyed, timeout=1000):
        esw1w1.editorstack.close_split()
    with pytest.raises(RuntimeError):
        esw1w1.count()
    assert es.count() == 2
    assert esw1.count() == 1

    assert es.isVisible()
    assert esw1.isVisible()
    assert esw1w2.isVisible()

    # Close the editorstack of the editorsplitter esw1w2 and assert that
    # editorsplitters esw1w2 AND esw1 are correctly destroyed afterward on
    # the Qt side.
    with qtbot.waitSignal(esw1.destroyed, timeout=1000):
        esw1w2.editorstack.close_split()
    with pytest.raises(RuntimeError):
        esw1.count()
    with pytest.raises(RuntimeError):
        esw1w2.count()

    assert es.isVisible()
    assert es.count() == 1

    # Test that the editorstack of the main editorsplitter es cannot be closed.
    es.editorstack.close_split()
    assert es.isVisible()
    assert es.count() == 1


def test_split(editor_splitter_layout_bot):
    """Test split() that adds new splitters to this instance."""
    es = editor_splitter_layout_bot

    # Split main panel with default split.
    es.split()  # Call directly.
    assert es.orientation() == Qt.Vertical
    assert not es.editorstack.horsplit_action.isEnabled()
    assert es.editorstack.versplit_action.isEnabled()
    assert es.count() == 2
    assert isinstance(es.widget(1), EditorSplitter)
    # Each splitter gets its own editor stack as the first widget.
    assert es.widget(1).count() == 1
    assert es.widget(1).editorstack == es.widget(1).widget(0)
    es.widget(1).plugin.clone_editorstack.assert_called_with(
                                    editorstack=es.widget(1).editorstack)

    # Create a horizontal split on original widget.
    es.editorstack.sig_split_horizontally.emit()  # Call from signal.
    assert es.orientation() == Qt.Horizontal
    assert es.editorstack.horsplit_action.isEnabled()
    assert not es.editorstack.versplit_action.isEnabled()
    assert es.count() == 3
    assert isinstance(es.widget(2), EditorSplitter)
    # Two splits have been created and each contains one EditorStack.
    assert es.widget(1).count() == 1
    assert es.widget(2).count() == 1

    # Test splitting one of the children.
    es1 = es.widget(1)
    es1.editorstack.sig_split_vertically.emit()
    assert es.orientation() == Qt.Horizontal  # Main split didn't change.
    assert es1.orientation() == Qt.Vertical  # Child splitter.
    assert not es1.editorstack.horsplit_action.isEnabled()
    assert es1.editorstack.versplit_action.isEnabled()
    assert es1.count() == 2
    assert isinstance(es1.widget(0), EditorStack)
    assert isinstance(es1.widget(1), EditorSplitter)
    assert not es1.widget(1).isHidden()


def test_iter_editorstacks(editor_splitter_bot):
    """Test iter_editorstacks."""
    es = editor_splitter_bot
    es_iter = es.iter_editorstacks

    # Check base splitter.
    assert es_iter() == [(es.editorstack, es.orientation())]

    # Split once.
    es.split(Qt.Vertical)
    esw1 = es.widget(1)
    assert es_iter() == [(es.editorstack, es.orientation()),
                         (esw1.editorstack, esw1.orientation())]

    # Second splitter on base isn't iterated.
    es.split(Qt.Horizontal)
    assert es_iter() == [(es.editorstack, es.orientation()),
                         (esw1.editorstack, esw1.orientation())]

    # Split a child.
    esw1.split(Qt.Vertical)
    esw1w1 = es.widget(1).widget(1)
    assert es_iter() == [(es.editorstack, es.orientation()),
                         (esw1.editorstack, esw1.orientation()),
                         (esw1w1.editorstack, esw1w1.orientation())]


def test_get_layout_settings(editor_splitter_bot, qtbot, mocker):
    """Test get_layout_settings()."""
    es = editor_splitter_bot

    # Initial settings from setup.
    setting = es.get_layout_settings()
    assert setting['splitsettings'] == [(False, None, [])]

    # Add some editors to patch output of iter_editorstacks.
    stack1 = editor_stack()
    stack1.new('foo.py', 'utf-8', 'a = 1\nprint(a)\n\nx = 2')
    stack1.new('layout_test.py', 'utf-8', 'spam egg\n')

    stack2 = editor_stack()
    stack2.new('test.py', 'utf-8', 'test text')

    mocker.patch.object(EditorSplitter, "iter_editorstacks")
    EditorSplitter.iter_editorstacks.return_value = (
        [(stack1, Qt.Vertical), (stack2, Qt.Horizontal)])

    setting = es.get_layout_settings()
    assert setting['hexstate']
    assert setting['sizes'] == es.sizes()
    assert setting['splitsettings'] == [(False, 'foo.py', [5, 3]),
                                        (False, 'test.py', [2])]


def test_set_layout_settings_dont_goto(editor_splitter_layout_bot):
    """Test set_layout_settings()."""
    es = editor_splitter_layout_bot
    linecount = es.editorstack.data[2].editor.get_cursor_line_number()

    # New layout to restore.
    state = '000000ff000000010000000200000231000001ff00ffffffff010000000200'
    sizes = [561, 511]
    splitsettings = [(False, 'layout_test.py', [2, 1, 52]),
                     (False, 'foo.py', [3, 2, 125]),
                     (False, __file__, [1, 1, 1])]

    new_settings = {'hexstate': state,
                    'sizes': sizes,
                    'splitsettings': splitsettings}

    # Current widget doesn't have saved settings applied.
    get_settings = es.get_layout_settings()
    assert es.count() == 1
    assert get_settings['hexstate'] != state
    assert get_settings['splitsettings'] != splitsettings

    # Invalid settings value.
    assert es.set_layout_settings({'spam': 'test'}) is None

    # Restore layout with dont_goto set.
    es.set_layout_settings(new_settings, dont_goto=True)
    get_settings = es.get_layout_settings()

    # Check that the panels were restored.
    assert es.count() == 2  # One EditorStack and one EditorSplitter.
    assert es.widget(1).count() == 2  # One EditorStack and one EditorSplitter.
    assert es.widget(1).widget(1).count() == 1  # One EditorStack.
    assert get_settings['hexstate'] == state

    # All the lines for each tab and split are at the last line number.
    assert get_settings['splitsettings'] == [(False, 'foo.py', [5, 2, linecount]),
                                             (False, 'foo.py', [5, 2, linecount]),
                                             (False, 'foo.py', [5, 2, linecount])]


def test_set_layout_settings_goto(editor_splitter_layout_bot):
    """Test set_layout_settings()."""
    es = editor_splitter_layout_bot

    # New layout to restore.
    state = '000000ff000000010000000200000231000001ff00ffffffff010000000200'
    sizes = [561, 511]
    splitsettings = [(False, 'layout_test.py', [2, 1, 52]),
                     (False, 'foo.py', [3, 2, 125]),
                     (False, __file__, [1, 1, 1])]

    new_settings = {'hexstate': state,
                    'sizes': sizes,
                    'splitsettings': splitsettings}

    # Restore layout without dont_goto, meaning it should position to the lines.
    es.set_layout_settings(new_settings, dont_goto=None)
    get_settings = es.get_layout_settings()
    # Even though the original splitsettings had different file names
    # selected, the current tab isn't restored in set_layout_settings().
    # However, this shows that the current line was positioned for each tab
    # and each split.
    assert get_settings['splitsettings'] == [(False, 'foo.py', [2, 1, 52]),
                                             (False, 'foo.py', [3, 2, 125]),
                                             (False, 'foo.py', [1, 1, 1])]


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(os.name == 'nt',
                    reason="Makes other tests fail on Windows")
def test_lsp_splitter_close(editor_splitter_lsp):
    """Test for issue #9341"""
    editorsplitter, lsp_manager = editor_splitter_lsp

    editorsplitter.split()
    lsp_files = lsp_manager.clients['python']['instance'].watched_files
    editor = editorsplitter.editorstack.get_current_editor()
    path = pathlib.Path(osp.abspath(editor.filename)).as_uri()
    assert len(lsp_files[path]) == 2

    editorstacks = editorsplitter.iter_editorstacks()
    assert len(editorstacks) == 2

    last_editorstack = editorstacks[0][0]
    last_editorstack.close()
    lsp_files = lsp_manager.clients['python']['instance'].watched_files
    assert len(lsp_files[path]) == 1


if __name__ == "__main__":
    import os.path as osp
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
