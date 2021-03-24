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
import json
import os.path as osp
import sys
from unittest.mock import Mock

# Qt imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.widgets import editor
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor


HERE = osp.dirname(osp.abspath(__file__))
ASSETS = osp.join(HERE, 'assets')

AVAILABLE_CASES = ['text']
CASES = {
    case: {
        'file': osp.join(ASSETS, '{0}.py'.format(case)),
        'tree': osp.join(ASSETS, '{0}_trees.json'.format(case))
    }
    for case in AVAILABLE_CASES
}


def get_tree_elements(treewidget):
    """Get elements present in the Outline tree widget."""
    root_item = treewidget.get_top_level_items()[0]
    root_ref = root_item.ref
    filename = osp.basename(root_ref.name)
    root_tree = {filename: []}
    stack = [(root_tree[filename], node) for node in root_ref.children]

    while len(stack) > 0:
        parent_tree, node = stack.pop(0)
        this_tree = {node.name: []}
        parent_tree.append(this_tree)
        this_stack = [(this_tree[node.name], child)
                        for child in node.children]
        stack = this_stack + stack
    return root_tree


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
    outlineexplorer = OutlineExplorerWidget(None, None, None)
    outlineexplorer.set_conf('show_fullpath', False)
    outlineexplorer.set_conf('show_all_files', True)
    outlineexplorer.set_conf('group_cells', True)
    outlineexplorer.set_conf('show_comments', True)
    outlineexplorer.set_conf('sort_files_alphabetically', False)
    outlineexplorer.set_conf('display_variables', True)

    # Fix the size of the outline explorer to prevent an
    # 'Unable to set geometry ' warning if the test fails.
    outlineexplorer.setFixedSize(400, 350)

    qtbot.addWidget(outlineexplorer)
    outlineexplorer.show()

    return outlineexplorer


@pytest.fixture
def completions_codeeditor_outline(completions_codeeditor, outlineexplorer):
    editor, _ = completions_codeeditor
    editor.oe_proxy = OutlineExplorerProxyEditor(editor, editor.filename)
    outlineexplorer.register_editor(editor.oe_proxy)
    outlineexplorer.set_current_editor(
        editor.oe_proxy, update=False, clear=False)
    return editor, outlineexplorer


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
        assert editorstack.get_stack_index() == index

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
@pytest.mark.skipif(not sys.platform == 'darwin',
                    reason="Fails on Linux and Windows")
def test_toggle_off_show_all_files(editorstack, outlineexplorer, test_files,
                                   qtbot):
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
    qtbot.wait(500)
    results = [item.text(0) for item in treewidget.get_visible_items()]
    assert results == ['foo1.py']


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
    assert results == ['foo2.py']


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
    assert results == ['text1.txt', 'foo1.py', 'foo2.py']


@pytest.mark.slow
@pytest.mark.second
def test_editor_outlineexplorer(qtbot, completions_codeeditor_outline):
    """Tests that the outline explorer reacts to editor changes."""
    code_editor, outlineexplorer = completions_codeeditor_outline
    treewidget = outlineexplorer.treewidget

    case_info = CASES['text']
    filename = case_info['file']
    tree_file = case_info['tree']

    with open(filename, 'r') as f:
        lines = f.read()

    with open(tree_file, 'r') as f:
        trees = json.load(f)

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.set_text('')
    code_editor.go_to_line(1)

    # Put example text in editor
    code_editor.set_text(lines)
    qtbot.wait(3000)

    # Check that the outline tree was initialized successfully
    tree = trees[0]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree

    # Remove "d" symbol
    code_editor.go_to_line(14)
    cursor = code_editor.textCursor()
    start = code_editor.get_position_line_number(13, -1)
    end = code_editor.get_position_line_number(17, 0)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)
    code_editor.cut()
    qtbot.wait(3000)

    tree = trees[1]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree

    # Add "d" symbol elsewhere
    code_editor.go_to_line(36)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyPress(code_editor, Qt.Key_Return)

    qtbot.keyPress(code_editor, Qt.Key_Up)
    code_editor.paste()

    qtbot.wait(3000)

    tree = trees[2]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree

    # Move method1
    code_editor.go_to_line(56)
    cursor = code_editor.textCursor()
    start = code_editor.get_position_line_number(55, -1)
    end = code_editor.get_position_line_number(57, -1)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)
    code_editor.cut()
    qtbot.wait(3000)

    tree = trees[3]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree

    # Add method1
    code_editor.go_to_line(49)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyPress(code_editor, Qt.Key_Return)

    qtbot.keyPress(code_editor, Qt.Key_Up)
    code_editor.paste()
    qtbot.wait(3000)

    tree = trees[4]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree

    # Add attribute "y"
    code_editor.go_to_line(48)
    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    code_editor.setTextCursor(cursor)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyClicks(code_editor, 'self.y = None')
        qtbot.keyPress(code_editor, Qt.Key_Return)

    with qtbot.waitSignal(treewidget.sig_tree_updated, timeout=30000):
        code_editor.request_symbols()

    tree = trees[5]
    root_tree = get_tree_elements(treewidget)
    assert root_tree == tree


@pytest.mark.slow
@pytest.mark.second
def test_empty_file(qtbot, completions_codeeditor_outline):
    """
    Test that the outline explorer is updated correctly when
    it's associated file is empty.
    """
    code_editor, outlineexplorer = completions_codeeditor_outline
    treewidget = outlineexplorer.treewidget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set empty contents
    code_editor.set_text('')
    code_editor.go_to_line(1)
    qtbot.wait(3000)

    # Assert the spinner is not shown.
    assert not outlineexplorer._spinner.isSpinning()

    # Add some content
    code_editor.set_text("""
def foo():
    a = 10
    return a
""")
    qtbot.wait(3000)

    root_tree = get_tree_elements(treewidget)
    assert root_tree == {'test.py': [{'foo': [{'a': []}]}]}

    # Remove content
    code_editor.selectAll()
    qtbot.keyPress(code_editor, Qt.Key_Delete)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    qtbot.wait(3000)

    # Assert the tree is empty and the spinner is not shown.
    root_tree = get_tree_elements(treewidget)
    assert root_tree == {'test.py': []}
    assert not outlineexplorer._spinner.isSpinning()


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__), '-vv', '-rw'])
