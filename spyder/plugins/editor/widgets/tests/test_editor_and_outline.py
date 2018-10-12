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
def test_files(tmpdir_factory):
    """Create and save some python codes and text in temporary files."""
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

    filename3 = osp.join(tmpdir.strpath, 'text1.txt')
    with open(filename3, 'w') as f:
        f.write("This is a simple text file for\n"
                "testing the Outline Explorer.\n")

    return [filename1, filename2, filename3]


@pytest.fixture
def outlineexplorer(qtbot):
    """Set up an OutlineExplorerWidget."""
    outlineexplorer = OutlineExplorerWidget(
        show_fullpath=False, show_all_files=True, group_cells=False,
        show_comments=True)
    # Fix the size of the outline explorer to prevent an
    # 'Unable to set geometry ' warning if the test fails.
    outlineexplorer.setFixedSize(400, 350)

    qtbot.addWidget(outlineexplorer)
    outlineexplorer.show()

    return outlineexplorer


@pytest.fixture
def editorstack(qtbot, outlineexplorer):
    def _create_editorstack(files):
        editorstack = editor.EditorStack(None, [])
        editorstack.set_find_widget(Mock())
        editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
        editorstack.analysis_timer = Mock()
        editorstack.save_dialog_on_tests = True
        editorstack.set_outlineexplorer(outlineexplorer)

        qtbot.addWidget(editorstack)
        editorstack.show()

        for file in files:
            editorstack.load(file)

        return editorstack
    return _create_editorstack


# ---- Tests
def test_load_files(editorstack, outlineexplorer, test_files):
    """
    Test that the content of the outline explorer is updated correctly
    after a file is loaded in the editor.
    """
    editorstack = editorstack([])
    treewidget = outlineexplorer.treewidget

    # Load the test files one by one and assert the content of the
    # outline explorer.
    expected_result = [['foo1.py'],
                       ['foo1.py', 'foo2.py'],
                       ['foo1.py', 'foo2.py', 'text1.txt']]
    for index, file in enumerate(test_files):
        editorstack.load(file)
        assert editorstack.get_current_filename() == file
        editorstack.tabs.currentIndex() == index

        results = [item.text(0) for item in treewidget.get_visible_items()]
        assert results == expected_result[index]


def test_close_editor(editorstack, outlineexplorer, test_files):
    """
    Test that the content of the outline explorer is empty after the
    editorstack has been closed.

    Regression test for issue #7798.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    assert treewidget.get_visible_items()

    # Close the editor and assert that the outline explorer tree is empty.
    editorstack.close()
    assert not treewidget.get_visible_items()


def test_close_a_file(editorstack, outlineexplorer, test_files):
    """
    Test that the content of the outline explorer is updated corrrectly
    after a file has been closed in the editorstack.

    Regression test for issue #7798.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget

    # Close 'foo2.py' and assert that the content of the outline explorer
    # tree has been updated.
    editorstack.close_file(index=1)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'text1.txt']


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__), '-vv', '-rw'])
