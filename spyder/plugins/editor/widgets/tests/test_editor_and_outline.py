# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests syncing between the EditorStack and OutlineExplorerWidget.
"""

# Standard library imports
import os
import os.path as osp
import sys
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

    filename2 = osp.join(tmpdir.strpath, 'text1.txt')
    with open(filename2, 'w') as f:
        f.write("This is a simple text file for\n"
                "testing the Outline Explorer.\n")

    filename3 = osp.join(tmpdir.strpath, 'foo2.py')
    with open(filename3, 'w') as f:
        f.write("# -*- coding: utf-8 -*-\n"
                "# ---- a comment\n")

    return [filename1, filename2, filename3]


@pytest.fixture
def outlineexplorer(qtbot):
    """Set up an OutlineExplorerWidget."""
    outlineexplorer = OutlineExplorerWidget(
        show_fullpath=False, show_all_files=True, group_cells=False,
        show_comments=True, sort_files_alphabetically=False)
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

        for index, file in enumerate(files):
            focus = index == 0
            editorstack.load(file, set_current=focus)
        return editorstack
    return _create_editorstack


# ---- Test all files mode
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
                       ['foo1.py', 'text1.txt'],
                       ['foo1.py', 'text1.txt', 'foo2.py']]
    for index, file in enumerate(test_files):
        editorstack.load(file)
        assert editorstack.get_current_filename() == file
        editorstack.get_stack_index() == index

        results = [item.text(0) for item in treewidget.get_visible_items()]
        assert results == expected_result[index]
        assert editorstack.get_stack_index() == index


def test_close_editor(editorstack, outlineexplorer, test_files):
    """
    Test that the content of the outline explorer is empty after the
    editorstack has been closed.

    Regression test for spyder-ide/spyder#7798.
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

    Regression test for spyder-ide/spyder#7798.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget

    # Close 'foo2.py' and assert that the content of the outline explorer
    # tree has been updated.
    editorstack.close_file(index=1)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'foo2.py']


def test_sort_file_alphabetically(editorstack, outlineexplorer, test_files):
    """
    Test that the option to sort the files in alphabetical order in the
    outline explorer is working as expected.

    This feature was introduced in spyder-ide/spyder#8015.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'text1.txt', 'foo2.py']

    # Set the option to sort files alphabetically to True.
    treewidget.toggle_sort_files_alphabetically(True)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'foo2.py', 'text1.txt']


def test_sync_file_order(editorstack, outlineexplorer, test_files):
    """
    Test that the order of the files in the Outline Explorer is updated when
    tabs are moved in the EditorStack.

    This feature was introduced in spyder-ide/spyder#8015.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'text1.txt', 'foo2.py']

    # Switch tab 1 with tab 2.
    editorstack.tabs.tabBar().moveTab(0, 1)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['text1.txt', 'foo1.py', 'foo2.py']


# ---- Test single file mode
def test_toggle_off_show_all_files(editorstack, outlineexplorer, test_files):
    """
    Test that toggling off the option to show all files in the Outline Explorer
    hide all root file items but the one corresponding to the currently
    selected Editor and assert that the remaning root file item is
    expanded correctly.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    assert editorstack.get_stack_index() == 0

    # Untoggle show all files option.
    treewidget.toggle_show_all_files(False)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py', 'foo']


@pytest.mark.skipif(sys.platform.startswith('linux'), reason="Fails on Linux")
def test_single_file_sync(editorstack, outlineexplorer, test_files, qtbot):
    """
    Test that the content of the Outline Explorer is updated correctly
    when the current Editor in the Editorstack changes.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    treewidget.toggle_show_all_files(False)
    assert editorstack.get_stack_index() == 0

    # Select the last file in the Editorstack.
    with qtbot.waitSignal(editorstack.editor_focus_changed):
        editorstack.tabs.setCurrentIndex(2)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo2.py', '---- a comment']


def test_toggle_on_show_all_files(editorstack, outlineexplorer, test_files):
    """
    Test that toggling back the option to show all files, after the
    order of the files in the Editorstack was changed while it was in single
    file mode, show all the root file items in the correct order.
    """
    editorstack = editorstack(test_files)
    treewidget = outlineexplorer.treewidget
    treewidget.toggle_show_all_files(False)

    # Move the first file to the second position in the tabbar of the
    # Editorstack and toggle back the show all files option.
    editorstack.tabs.tabBar().moveTab(0, 1)
    treewidget.toggle_show_all_files(True)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['text1.txt', 'foo1.py', 'foo', 'foo2.py']


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__), '-vv', '-rw'])
