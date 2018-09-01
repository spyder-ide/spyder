# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests syncing between the EditorStack and OutlineExplorerWidget.
"""

# Standard library imports
import os.path as osp
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.widgets import editor
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget


# ---- Qt Test Fixtures
@pytest.fixture(scope="module")
def python_files(tmpdir_factory):
    """Create and save some python codes in temporary files."""
    tmpdir = tmpdir_factory.mktemp("files")
    
    filename1 = osp.join(tmpdir.strpath, 'foo1.py')
    with open(filename1, 'w') as f:
        f.write("# -*- coding: utf-8 -*-\n"
                "def foo:\n"
                "    print(Hello World!)\n")

    filename2 = osp.join(tmpdir.strpath, 'foo2.py')
    with open(filename2, 'w') as f:
        f.write("# -*- coding: utf-8 -*-\n"
                "# ---- a comment\n")

    return [filename1, filename2]

@pytest.fixture
def empty_editor_bot(qtbot):
    """Set up an empty EditorStack with an OutlineExplorerWidget."""
    outlineexplorer = OutlineExplorerWidget(
        show_fullpath=False, show_all_files=True, group_cells=False,
        show_comments=True)
    # Fix the size of the outline explorer to prevent an
    # 'Unable to set geometry ' warning if the test fails.
    outlineexplorer.setFixedSize(400, 350)

    qtbot.addWidget(outlineexplorer)
    outlineexplorer.show()

    editorstack = editor.EditorStack(None, [])
    editorstack.set_introspector(Mock())
    editorstack.set_find_widget(Mock())
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    editorstack.analysis_timer = Mock()
    editorstack.save_dialog_on_tests = True
    editorstack.set_outlineexplorer(outlineexplorer)
    
    qtbot.addWidget(editorstack)
    editorstack.show()
    
    return editorstack, outlineexplorer, qtbot


@pytest.fixture
def editor_bot(empty_editor_bot, python_files):
    """
    Set up an EditorStack with an OutlineExplorerWidget and load some files.
    """
    editorstack, outlineexplorer, qtbot = empty_editor_bot
    for file in python_files:
        editorstack.load(file)

    return editorstack, outlineexplorer, qtbot

# ---- Tests
def test_load_files(empty_editor_bot, python_files):
    """
    Test that the content of the outline explorer is updated correctly
    after a file is loaded in the editor.
    """
    editorstack, outlineexplorer, qtbot = empty_editor_bot
    treewidget = outlineexplorer.treewidget
    
    # Load the first file and assert the content of the outline explorer.
    editorstack.load(python_files[0])
    assert editorstack.get_current_filename() == python_files[0]
    editorstack.tabs.currentIndex() == 0
    
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'foo']
        
    # Load the second file and assert the content of the outline explorer tree.
    editorstack.load(python_files[1])
    assert editorstack.get_current_filename() == python_files[1]
    editorstack.tabs.currentIndex() == 1
    
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'foo2.py', '---- a comment']

def test_close_editor(editor_bot):
    """
    Test that the content of the outline explorer is empty after the
    editorstack has been closed.

    Regression test for issue #7798.
    """
    editorstack, outlineexplorer, qtbot = editor_bot
    treewidget = outlineexplorer.treewidget
    assert treewidget.get_visible_items()

    # Close the editor and assert that the outline explorer tree is empty.
    editorstack.close()

    assert not treewidget.get_visible_items()
    
    