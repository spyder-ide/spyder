# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the main window
"""

import os
import os.path as osp

from flaky import flaky
import numpy as np
from numpy.testing import assert_array_equal
import pytest
from qtpy.QtCore import Qt, QTimer
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QFileDialog, QLineEdit

from spyder.app.cli_options import get_options
from spyder.app.mainwindow import initialize, run_spyder


#==============================================================================
# Constants
#==============================================================================
# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))

# Time to wait until the IPython console is ready to receive input
# (in miliseconds)
SHELL_TIMEOUT = 20000

# Time to wait for the IPython console to evaluate something (in
# miliseconds)
EVAL_TIMEOUT = 3000


#==============================================================================
# Utility functions
#==============================================================================
def open_file_in_editor(main_window, fname, directory=None):
    """Open a file using the Editor and its open file dialog"""
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, QFileDialog):
            if directory is not None:
                w.setDirectory(directory)
            input_field = w.findChildren(QLineEdit)[0]
            input_field.setText(fname)
            QTest.keyClick(w, Qt.Key_Enter)


def reset_run_code(qtbot, shell, code_editor, nsb):
    """Reset state after a run code test"""
    shell.execute('%reset -f')
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=EVAL_TIMEOUT)
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)


#==============================================================================
# Fixtures
#==============================================================================
@pytest.fixture
def main_window(request):
    app = initialize()
    options, args = get_options()
    widget = run_spyder(app, options, args)
    def close_widget():
        widget.close()
    request.addfinalizer(close_widget)
    return widget


#==============================================================================
# Tests
#==============================================================================
@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_run_code(main_window, qtbot):
    """Test all the different ways we have to run code"""
    # ---- Setup ----
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file
    main_window.editor.load(osp.join(LOCATION, 'script.py'))

    # Move to the editor's first line
    code_editor = main_window.editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.get_focus_widget()

    # ---- Run file ----
    qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 3, timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run lines ----
    # Run the whole file line by line
    for _ in range(code_editor.blockCount()):
        qtbot.keyClick(code_editor, Qt.Key_F9)
        qtbot.wait(100)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 3, timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run cell and advance ----
    # Run the three cells present in file
    for _ in range(3):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
        qtbot.wait(100)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 3, timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run cell ----
    # Run the first cell in file
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ControlModifier)

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 1, timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10

    # Press Ctrl+Enter a second time to verify that we're *not* advancing
    # to the next cell
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ControlModifier)
    assert nsb.editor.model.rowCount() == 1

    main_window.editor.close_file()


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt' or os.environ.get('CI', None) is None,
                    reason="It times out sometimes on Windows and it's not "
                           "meant to be run outside of a CI")
def test_open_files_in_new_editor_window(main_window, qtbot):
    """
    This tests that opening files in a new editor window
    is working as expected.

    Test for issue 4085
    """
    # Set a timer to manipulate the open dialog while it's running
    QTimer.singleShot(2000, lambda: open_file_in_editor(main_window,
                                                        'script.py',
                                                        directory=LOCATION))

    # Create a new editor window
    # Note: editor.load() uses the current editorstack by default
    main_window.editor.create_new_window()
    main_window.editor.load()

    # Perform the test
    # Note: There's always one file open in the Editor
    editorstack = main_window.editor.get_current_editorstack()
    assert editorstack.get_stack_count() == 2


@flaky(max_runs=10)
def test_maximize_minimize_plugins(main_window, qtbot):
    """Test that the maximize button is working correctly."""
    # Set focus to the Editor
    main_window.editor.get_focus_widget().setFocus()

    # Click the maximize button
    max_action = main_window.maximize_action
    max_button = main_window.main_toolbar.widgetForAction(max_action)
    qtbot.mouseClick(max_button, Qt.LeftButton)

    # Verify that the Editor is maximized
    assert main_window.editor.ismaximized

    # Verify that the action minimizes the plugin too
    qtbot.mouseClick(max_button, Qt.LeftButton)
    assert not main_window.editor.ismaximized


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_issue_4066(main_window, qtbot):
    """
    Test for a segfault when these steps are followed:

    1. Open an object present in the Variable Explorer (e.g. a list).
    2. Delete that object in its corresponding console while its
       editor is still opem.
    3. Closing that editor by pressing its *Ok* button.
    """
    # Create the object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    shell.execute('myobj = [1, 2, 3]')

    # Open editor associated with that object and get a reference to it
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()
    obj_editor_id = list(nsb.editor.delegate._editors.keys())[0]
    obj_editor = nsb.editor.delegate._editors[obj_editor_id]['editor']

    # Move to the IPython console and delete that object
    main_window.ipyconsole.get_focus_widget().setFocus()
    shell.execute('del myobj')
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=EVAL_TIMEOUT)

    # Close editor
    ok_widget = obj_editor.bbox.button(obj_editor.bbox.Ok)
    qtbot.mouseClick(ok_widget, Qt.LeftButton)

    # Wait for the segfault
    qtbot.wait(3000)


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_varexp_edit_inline(main_window, qtbot):
    """
    Test for errors when editing inline values in the Variable Explorer
    and then moving to another plugin.

    Note: Errors for this test don't appear related to it but instead they
    are shown down the road. That's because they are generated by an
    async C++ RuntimeError.
    """
    # Create object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    shell.execute('a = 10')

    # Edit object
    main_window.variableexplorer.visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()

    # Change focus to IPython console
    main_window.ipyconsole.get_focus_widget().setFocus()

    # Wait for the error
    qtbot.wait(3000)


if __name__ == "__main__":
    pytest.main()
