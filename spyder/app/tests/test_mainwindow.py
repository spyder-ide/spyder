# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the main window.
"""

# Standard library imports
import gc
import os
import os.path as osp
import random
import re
import shutil
import sys
import tempfile
from textwrap import dedent
from unittest.mock import Mock
import uuid

# Third party imports
from flaky import flaky
import ipykernel
from IPython.core import release as ipy_release
from matplotlib.testing.compare import compare_images
import nbconvert
import numpy as np
from numpy.testing import assert_array_equal
from packaging.version import parse
import pylint
import pytest
from qtpy import PYQT_VERSION, PYQT5
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QImage, QTextCursor
from qtpy.QtWidgets import QAction, QApplication, QInputDialog, QWidget
from qtpy.QtWebEngineWidgets import WEBENGINE

# Local imports
from spyder import __trouble_url__
from spyder.api.utils import get_class_values
from spyder.api.widgets.auxiliary_widgets import SpyderWindowWidget
from spyder.api.plugins import Plugins
from spyder.app.tests.conftest import (
    COMPILE_AND_EVAL_TIMEOUT, COMPLETION_TIMEOUT, EVAL_TIMEOUT,
    find_desired_tab_in_window, LOCATION, open_file_in_editor,
    preferences_dialog_helper, read_asset_file, reset_run_code,
    SHELL_TIMEOUT, start_new_kernel)
from spyder.config.base import (
    get_home_dir, get_conf_path, get_module_path, running_in_ci)
from spyder.config.manager import CONF
from spyder.dependencies import DEPENDENCIES
from spyder.plugins.help.widgets import ObjectComboBox
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.layout.layouts import DefaultLayouts
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.py3compat import qbytearray_to_str, to_text_string
from spyder.utils.environ import set_user_env
from spyder.utils.misc import remove_backslashes
from spyder.utils.clipboard_helper import CLIPBOARD_HELPER
from spyder.widgets.dock import DockTitleBar


@pytest.mark.order(1)
@pytest.mark.single_instance
@pytest.mark.known_leak
@pytest.mark.skipif(
    not running_in_ci(), reason="It's not meant to be run outside of CIs")
def test_single_instance_and_edit_magic(main_window, qtbot, tmpdir):
    """Test single instance mode and %edit magic."""
    editorstack = main_window.editor.get_current_editorstack()
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    spy_dir = osp.dirname(get_module_path('spyder'))
    lock_code = (
        "import sys\n"
        "sys.path.append(r'{spy_dir_str}')\n"
        "from spyder.utils.external import lockfile\n"
        "lock_file = r'{lock_file}'\n"
        "lock = lockfile.FilesystemLock(lock_file)\n"
        "lock_created = lock.lock()\n"
        "print(lock_created)".format(
            spy_dir_str=spy_dir,
            lock_file=get_conf_path('spyder.lock'))
    )

    with qtbot.waitSignal(shell.executed, timeout=2000):
        shell.execute(lock_code)
    qtbot.wait(1000)
    assert not shell.get_value('lock_created')

    # Test %edit magic
    n_editors = editorstack.get_stack_count()
    p = tmpdir.mkdir("foo").join("bar.py")
    p.write(lock_code)

    with qtbot.waitSignal(shell.executed):
        shell.execute('%edit {}'.format(to_text_string(p)))

    qtbot.wait(3000)
    assert editorstack.get_stack_count() == n_editors + 1
    assert editorstack.get_current_editor().toPlainText() == lock_code

    main_window.editor.close_file()


@pytest.mark.use_introspection
@pytest.mark.skipif(os.name == 'nt', reason="Fails on Windows")
def test_leaks(main_window, qtbot):
    """
    Test leaks in mainwindow when closing a file or a console.

    Many other ways of leaking exist but are not covered here.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Count initial objects
    # Only one of each should be present, but because of many leaks,
    # this is most likely not the case. Here only closing is tested
    shell.wait_all_shutdown()
    gc.collect()
    objects = gc.get_objects()
    n_code_editor_init = 0
    for o in objects:
        if type(o).__name__ == "CodeEditor":
            n_code_editor_init += 1
    n_shell_init = 0
    for o in objects:
        if type(o).__name__ == "ShellWidget":
            n_shell_init += 1
    del objects

    # Open a second file and console
    main_window.editor.new()
    main_window.ipyconsole.create_new_client()
    # Do something interesting in the new window
    code_editor = main_window.editor.get_focus_widget()
    # Show an error in the editor
    code_editor.set_text("aaa")
    del code_editor

    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")

    # Close all files and consoles
    main_window.editor.close_all_files()
    main_window.ipyconsole.restart()

    # Wait until the shells are closed
    shell = main_window.ipyconsole.get_current_shellwidget()
    shell.wait_all_shutdown()
    # Count final objects
    gc.collect()
    objects = gc.get_objects()
    n_code_editor = 0
    for o in objects:
        if type(o).__name__ == "CodeEditor":
            n_code_editor += 1
    n_shell = 0
    for o in objects:
        if type(o).__name__ == "ShellWidget":
            n_shell += 1

    # Make sure no new objects have been created
    assert n_shell <= n_shell_init
    assert n_code_editor <= n_code_editor_init


def test_lock_action(main_window, qtbot):
    """Test the lock interface action."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    action = main_window.layouts.lock_interface_action
    plugins = main_window.widgetlist

    # By default the interface is locked.
    assert main_window.layouts._interface_locked

    # In this state the title bar is an empty QWidget
    for plugin in plugins:
        title_bar = plugin.dockwidget.titleBarWidget()
        assert not isinstance(title_bar, DockTitleBar)
        assert isinstance(title_bar, QWidget)

    # Test that our custom title bar is shown when the action
    # is triggered.
    action.trigger()
    for plugin in plugins:
        title_bar = plugin.dockwidget.titleBarWidget()
        assert isinstance(title_bar, DockTitleBar)
    assert not main_window.layouts._interface_locked

    # Restore default state
    action.trigger()
    assert main_window.layouts._interface_locked


@pytest.mark.order(1)
@pytest.mark.skipif(sys.platform.startswith('linux') and not running_in_ci(),
                    reason='Fails on Linux when run locally')
@pytest.mark.skipif(sys.platform == 'darwin' and running_in_ci(),
                    reason='Fails on MacOS when run in CI')
def test_default_plugin_actions(main_window, qtbot):
    """Test the effect of dock, undock, close and toggle view actions."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Use a particular plugin
    file_explorer = main_window.explorer
    main_widget = file_explorer.get_widget()

    # Undock action
    main_widget.undock_action.triggered.emit(True)
    qtbot.wait(500)
    main_widget.windowwidget.move(200, 200)
    assert not file_explorer.dockwidget.isVisible()
    assert main_widget.undock_action is not None
    assert isinstance(main_widget.windowwidget, SpyderWindowWidget)
    assert main_widget.windowwidget.centralWidget() == main_widget

    # Dock action
    main_widget.dock_action.triggered.emit(True)
    qtbot.wait(500)
    assert file_explorer.dockwidget.isVisible()
    assert main_widget.windowwidget is None

    # Test geometry was saved on close
    geometry = file_explorer.get_conf('window_geometry')
    assert geometry != ''

    # Test restoring undocked plugin with the right geometry
    file_explorer.set_conf('undocked_on_window_close', True)
    main_window.restore_undocked_plugins()
    assert main_widget.windowwidget is not None
    assert (
        geometry == qbytearray_to_str(main_widget.windowwidget.saveGeometry())
    )
    main_widget.windowwidget.close()

    # Close action
    main_widget.close_action.triggered.emit(True)
    qtbot.wait(500)
    assert not file_explorer.dockwidget.isVisible()
    assert not file_explorer.toggle_view_action.isChecked()

    # Toggle view action
    file_explorer.toggle_view_action.setChecked(True)
    assert file_explorer.dockwidget.isVisible()


@flaky(max_runs=3)
@pytest.mark.parametrize(
    'main_window',
    [{'spy_config': ('main', 'opengl', 'software')}],
    indirect=True)
def test_opengl_implementation(main_window, qtbot):
    """
    Test that we are setting the selected OpenGL implementation
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    assert main_window._test_setting_opengl('software')

    # Restore default config value
    CONF.set('main', 'opengl', 'automatic')


@flaky(max_runs=3)
@pytest.mark.skipif(
    np.__version__ < '1.14.0',
    reason="This only happens in Numpy 1.14+"
)
@pytest.mark.parametrize(
    'main_window',
    [{'spy_config': ('variable_explorer', 'minmax', True)}],
    indirect=True)
def test_filter_numpy_warning(main_window, qtbot):
    """
    Test that we filter a warning shown when an array contains nan
    values and the Variable Explorer option 'Show arrays min/man'
    is on.

    For spyder-ide/spyder#7063.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create an array with a nan value
    with qtbot.waitSignal(shell.executed):
        shell.execute('import numpy as np; A=np.full(16, np.nan)')

    qtbot.wait(1000)

    # Assert that no warnings are shown in the console
    assert "warning" not in control.toPlainText()
    assert "Warning" not in control.toPlainText()

    # Restore default config value
    CONF.set('variable_explorer', 'minmax', False)


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform == 'darwin',
                    reason="Fails on other than macOS")
@pytest.mark.known_leak  # Opens Spyder/QtWebEngine/Default/Cookies
def test_get_help_combo(main_window, qtbot):
    """
    Test that Help can display docstrings for names typed in its combobox.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    if WEBENGINE:
        webpage = webview.page()
    else:
        webpage = webview.page().mainFrame()

    # --- From the console ---
    # Write some object in the console
    with qtbot.waitSignal(shell.executed):
        shell.execute('import numpy as np')

    # Get help - numpy
    object_combo = help_plugin.get_widget().object_combo
    object_combo.setFocus()

    qtbot.keyClicks(object_combo, 'numpy', delay=100)

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "NumPy"), timeout=6000)

    # Get help - numpy.arange
    qtbot.keyClicks(object_combo, '.arange', delay=100)

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "arange"), timeout=6000)

    # Get help - np
    # Clear combo
    object_combo.set_current_text('')

    qtbot.keyClicks(object_combo, 'np', delay=100)

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "NumPy"), timeout=6000)

    # Get help - np.arange
    qtbot.keyClicks(object_combo, '.arange', delay=100)

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "arange"), timeout=6000)


@pytest.mark.known_leak  # Opens Spyder/QtWebEngine/Default/Cookies
def test_get_help_ipython_console_dot_notation(main_window, qtbot, tmpdir):
    """
    Test that Help works when called from the IPython console
    with dot calls i.e np.sin

    See spyder-ide/spyder#11821
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Open test file
    test_file = osp.join(LOCATION, 'script_unicode.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # Run test file
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    webpage = webview.page() if WEBENGINE else webview.page().mainFrame()

    # Write function name
    qtbot.keyClicks(control, u'np.linalg.norm')

    # Get help
    control.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(
        lambda: check_text(webpage, "Matrix or vector norm."),
        timeout=6000)


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Too flaky on Mac")
def test_get_help_ipython_console_special_characters(
        main_window, qtbot, tmpdir):
    """
    Test that Help works when called from the IPython console
    for unusual characters.

    See spyder-ide/spyder#7699
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Open test file
    test_file = osp.join(LOCATION, 'script_unicode.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # Run test file
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    webpage = webview.page() if WEBENGINE else webview.page().mainFrame()

    # Write function name and assert in Console
    def check_control(control, value):
        return value in control.toPlainText()

    qtbot.keyClicks(control, u'aa\t')
    qtbot.waitUntil(lambda: check_control(control, u'aaʹbb'),
                    timeout=SHELL_TIMEOUT)

    # Get help
    control.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "This function docstring."),
                    timeout=6000)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' and running_in_ci(),
                    reason="Times out on Windows")
def test_get_help_ipython_console(main_window, qtbot):
    """Test that Help works when called from the IPython console."""
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    webpage = webview.page() if WEBENGINE else webview.page().mainFrame()

    # Write some object in the console
    qtbot.keyClicks(control, 'runfile')

    # Get help
    control.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "namespace"), timeout=6000)


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Does not work on Mac and Windows!")
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.parametrize(
    "object_info",
    [("range", "range"),
     ("import numpy as np", "An array object of arbitrary homogeneous items")])
def test_get_help_editor(main_window, qtbot, object_info):
    """Test that Help works when called from the Editor."""
    # Wait until the window is fully up
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    webpage = webview.page() if WEBENGINE else webview.page().mainFrame()

    main_window.editor.new(fname="test.py", text="")
    code_editor = main_window.editor.get_focus_widget()
    editorstack = main_window.editor.get_current_editorstack()
    qtbot.waitUntil(lambda: code_editor.completions_available,
                    timeout=COMPLETION_TIMEOUT)

    # Write some object in the editor
    object_name, expected_text = object_info
    code_editor.set_text(object_name)
    code_editor.move_cursor(len(object_name))
    with qtbot.waitSignal(code_editor.completions_response_signal,
                          timeout=COMPLETION_TIMEOUT):
        code_editor.document_did_change()

    # Get help
    with qtbot.waitSignal(code_editor.sig_display_object_info, timeout=30000):
        editorstack.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, expected_text), timeout=30000)

    assert check_text(webpage, expected_text)


def test_window_title(main_window, tmpdir, qtbot):
    """Test window title with non-ascii characters."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    projects = main_window.projects

    # Create a project in non-ascii path
    path = to_text_string(tmpdir.mkdir(u'測試'))
    projects.open_project(path=path)

    # Set non-ascii window title
    main_window._cli_options.window_title = u'اختبار'

    # Assert window title is computed without errors
    # and has the expected strings
    main_window.set_window_title()
    title = main_window.base_title
    assert u'Spyder' in title
    assert u'Python' in title
    assert u'اختبار' in title
    assert u'測試' in title

    projects.close_project()


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Fails sometimes on Windows and Mac")
@pytest.mark.parametrize("debugcell", [True, False])
def test_move_to_first_breakpoint(main_window, qtbot, debugcell):
    """Test that we move to the first breakpoint if there's one present."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Main variables
    control = shell._control
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # Set breakpoint
    code_editor.debugger.toogle_breakpoint(line_number=10)
    qtbot.wait(500)
    cursor = code_editor.textCursor()
    cursor.setPosition(0)
    code_editor.setTextCursor(cursor)

    if debugcell:
        # Advance 2 cells
        for i in range(2):
            qtbot.keyClick(code_editor, Qt.Key_Return,
                           modifier=Qt.ShiftModifier)
            qtbot.wait(500)

        # Debug the cell
        with qtbot.waitSignal(shell.executed):
            qtbot.keyClick(code_editor, Qt.Key_Return,
                           modifier=Qt.AltModifier | Qt.ShiftModifier)

        # Make sure everything is ready
        assert shell.spyder_kernel_comm.is_open()
        assert shell.is_waiting_pdb_input()

        with qtbot.waitSignal(shell.executed):
            shell.pdb_execute('!b')
        assert 'script.py:10' in shell._control.toPlainText()
        # We need to press continue as we don't test yet if a breakpoint
        # is in the cell
        with qtbot.waitSignal(shell.executed):
            shell.pdb_execute('!c')

    else:
        # Click the debug button
        with qtbot.waitSignal(shell.executed):
            qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Verify that we are at first breakpoint
    shell.clear_console()
    qtbot.wait(500)
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!list")
    assert "1--> 10 arr = np.array(li)" in control.toPlainText()

    # Exit debugging
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!exit")

    # Set breakpoint on first line with code
    code_editor.debugger.toogle_breakpoint(line_number=2)

    # Click the debug button
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Wait until continue and stop on the breakpoint
    qtbot.waitUntil(lambda: "IPdb [2]:" in control.toPlainText())

    # Verify that we are still on debugging
    assert shell.is_waiting_pdb_input()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason='Fails on windows!')
def test_runconfig_workdir(main_window, qtbot, tmpdir):
    """Test runconfig workdir options."""
    from spyder.plugins.run.widgets import RunConfiguration
    CONF.set('run', 'configurations', [])

    # ---- Load test file ----
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # --- Use cwd for this file ---
    rc = RunConfiguration().get()
    rc['default'] = False
    rc['file_dir'] = False
    rc['cw_dir'] = True
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    # --- Run test file ---
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    # --- Assert we're in cwd after execution ---
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os; current_dir = os.getcwd()')
    assert shell.get_value('current_dir') == get_home_dir()

    # --- Use fixed execution dir for test file ---
    temp_dir = str(tmpdir.mkdir("test_dir"))
    rc['file_dir'] = False
    rc['cw_dir'] = False
    rc['fixed_dir'] = True
    rc['dir'] = temp_dir
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    # --- Run test file ---
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    # --- Assert we're in fixed dir after execution ---
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os; current_dir = os.getcwd()')
    assert shell.get_value('current_dir') == temp_dir

    # ---- Closing test file and resetting config ----
    main_window.editor.close_file()
    CONF.set('run', 'configurations', [])


@pytest.mark.order(1)
@pytest.mark.no_new_console
@flaky(max_runs=3)
@pytest.mark.skipif(
    sys.platform == 'darwin', reason='Hangs sometimes on Mac')
def test_dedicated_consoles(main_window, qtbot):
    """Test running code in dedicated consoles."""
    from spyder.plugins.run.widgets import RunConfiguration

    # ---- Load test file ----
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # --- Set run options for this file ---
    rc = RunConfiguration().get()

    # A dedicated console is used when these three options are False
    rc['default'] = rc['current'] = rc['systerm'] = False
    rc['clear_namespace'] = False
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    # --- Run test file and assert that we get a dedicated console ---
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    nsb = main_window.variableexplorer.current_widget()

    assert len(main_window.ipyconsole.get_clients()) == 2
    assert main_window.ipyconsole.get_widget().filenames == ['', test_file]
    assert main_window.ipyconsole.get_widget().tabwidget.tabText(1) == 'script.py/A'

    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4)
    assert nsb.editor.source_model.rowCount() == 4

    # --- Assert only runfile text is present and there's no banner text ---
    # See spyder-ide/spyder#5301.
    text = control.toPlainText()
    assert ('runfile' in text) and not ('Python' in text or 'IPython' in text)

    # --- Check namespace retention after re-execution ---
    with qtbot.waitSignal(shell.executed):
        shell.execute('zz = -1')

    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.waitUntil(lambda: shell.is_defined('zz'))
    assert shell.is_defined('zz')

    # --- Assert runfile text is present after reruns ---
    assert 'runfile' in control.toPlainText()

    # --- Clean namespace after re-execution with clear_namespace ---
    rc['clear_namespace'] = True
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    qtbot.wait(500)
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.waitUntil(lambda: not shell.is_defined('zz'))
    assert not shell.is_defined('zz')

    # --- Assert runfile text is present after reruns ---
    assert 'runfile' in control.toPlainText()

    # ---- Closing test file and resetting config ----
    main_window.editor.close_file()
    CONF.set('run', 'configurations', [])


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="Fails frequently on Linux")
def test_connection_to_external_kernel(main_window, qtbot):
    """Test that only Spyder kernels are connected to the Variable Explorer."""
    # Test with a generic kernel
    km, kc = start_new_kernel()

    main_window.ipyconsole.create_client_for_kernel(kc.connection_file)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert that there are no variables in the variable explorer
    main_window.variableexplorer.change_visibility(True)
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 0)
    assert nsb.editor.source_model.rowCount() == 0

    python_shell = shell

    # Test with a kernel from Spyder
    spykm, spykc = start_new_kernel(spykernel=True)
    main_window.ipyconsole.create_client_for_kernel(spykc.connection_file)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert that a variable is visible in the variable explorer
    main_window.variableexplorer.change_visibility(True)
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1)
    assert nsb.editor.source_model.rowCount() == 1

    # Test runfile in external_kernel
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(
        "print(2 + 1)"
    )

    # Start running
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(run_button, Qt.LeftButton)

    assert "runfile" in shell._control.toPlainText()
    assert "3" in shell._control.toPlainText()

    # Try quitting the kernels
    with qtbot.waitSignal(shell.executed):
        shell.execute('quit()')
    python_shell.execute('quit()')

    # Make sure everything quit properly
    qtbot.waitUntil(lambda: not km.is_alive())
    assert not km.is_alive()
    qtbot.waitUntil(lambda: not spykm.is_alive())
    assert not spykm.is_alive()

    # Close the channels
    spykc.stop_channels()
    kc.stop_channels()


@pytest.mark.order(1)
@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt', reason="It times out sometimes on Windows")
def test_change_types_in_varexp(main_window, qtbot):
    """Test that variable types can't be changed in the Variable Explorer."""
    # Create object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Edit object
    main_window.variableexplorer.change_visibility(True)
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()

    # Try to change types
    qtbot.keyClicks(QApplication.focusWidget(), "'s'")
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key_Enter)
    qtbot.wait(1000)

    # Assert object remains the same
    assert shell.get_value('a') == 10


@flaky(max_runs=3)
@pytest.mark.parametrize("test_directory", [u"non_ascii_ñ_í_ç", u"test_dir"])
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_change_cwd_ipython_console(
        main_window, qtbot, tmpdir, test_directory):
    """
    Test synchronization with working directory and File Explorer when
    changing cwd in the IPython console.
    """
    wdir = main_window.workingdirectory
    treewidget = main_window.explorer.get_widget().treewidget
    shell = main_window.ipyconsole.get_current_shellwidget()

    # Wait until the window is fully up
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create temp dir
    temp_dir = str(tmpdir.mkdir(test_directory))

    # Change directory in IPython console using %cd
    with qtbot.waitSignal(shell.executed):
        shell.execute(u"%cd {}".format(temp_dir))

    qtbot.waitUntil(
        lambda: osp.normpath(wdir.get_container().history[-1]) == osp.normpath(
            temp_dir), timeout=SHELL_TIMEOUT)

    # Assert that cwd changed in workingdirectory
    assert osp.normpath(wdir.get_container().history[-1]) == osp.normpath(
        temp_dir)

    qtbot.waitUntil(
        lambda: osp.normpath(treewidget.get_current_folder()) == osp.normpath(
            temp_dir), timeout=SHELL_TIMEOUT)

    # Assert that cwd changed in explorer
    assert osp.normpath(treewidget.get_current_folder()) == osp.normpath(
        temp_dir)


@flaky(max_runs=3)
@pytest.mark.parametrize("test_directory", [u"non_ascii_ñ_í_ç", u"test_dir"])
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_change_cwd_explorer(main_window, qtbot, tmpdir, test_directory):
    """
    Test synchronization with working directory and IPython console when
    changing directories in the File Explorer.
    """
    wdir = main_window.workingdirectory
    explorer = main_window.explorer
    shell = main_window.ipyconsole.get_current_shellwidget()

    # Wait until the window is fully up
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create temp directory
    temp_dir = to_text_string(tmpdir.mkdir(test_directory))

    # Change directory in the explorer widget
    explorer.chdir(temp_dir)
    qtbot.wait(1000)

    # Assert that cwd changed in workingdirectory
    assert osp.normpath(wdir.get_container().history[-1]) == osp.normpath(
        temp_dir)

    # Assert that cwd changed in IPython console
    assert osp.normpath(temp_dir) == osp.normpath(shell._cwd)


@flaky(max_runs=3)
@pytest.mark.skipif(
    (os.name == 'nt' or sys.platform == 'darwin' or
     parse(ipy_release.version) == parse('7.11.0')),
    reason="Hard to test on Windows and macOS and fails for IPython 7.11.0")
def test_run_cython_code(main_window, qtbot):
    """Test all the different ways we have to run Cython code"""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # ---- Setup ----
    # Get a reference to the code editor widget
    code_editor = main_window.editor.get_focus_widget()

    # ---- Run pyx file ----
    # Load test file
    main_window.editor.load(osp.join(LOCATION, 'pyx_script.pyx'))

    # Run file
    qtbot.keyClick(code_editor, Qt.Key_F5)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.current_widget()

    # Wait until an object appears
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=COMPILE_AND_EVAL_TIMEOUT)

    # Verify result
    shell = main_window.ipyconsole.get_current_shellwidget()
    assert shell.get_value('a') == 3628800

    # Reset and close file
    reset_run_code(qtbot, shell, code_editor, nsb)
    main_window.editor.close_file()

    # ---- Import pyx file ----
    # Load test file
    main_window.editor.load(osp.join(LOCATION, 'pyx_lib_import.py'))

    # Run file
    qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=COMPILE_AND_EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('b') == 3628800

    # Close file
    main_window.editor.close_file()


@flaky(max_runs=5)
def test_project_path(main_window, tmpdir, qtbot):
    """Test project path added to spyder_pythonpath and IPython Console."""
    projects = main_window.projects

    # Create a project path
    path = str(tmpdir.mkdir('project_path'))
    assert path not in projects.get_conf(
        'spyder_pythonpath', section='pythonpath_manager')

    # Ensure project path is added to spyder_pythonpath
    projects.open_project(path=path)
    assert path in projects.get_conf(
        'spyder_pythonpath', section='pythonpath_manager')

    # Ensure project path is added to IPython console
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute("import sys; import os; "
                      "sys_path = sys.path; "
                      "os_path = os.environ.get('PYTHONPATH', [])")
    assert path in shell.get_value("sys_path")
    assert path in shell.get_value("os_path")

    projects.close_project()

    # Ensure that project path is removed from spyder_pythonpath
    assert path not in projects.get_conf(
        'spyder_pythonpath', section='pythonpath_manager')

    # Ensure that project path is removed from IPython console
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute("import sys; import os; "
                      "sys_path = sys.path; "
                      "os_path = os.environ.get('PYTHONPATH', [])")
    assert path not in shell.get_value("sys_path")
    assert path not in shell.get_value("os_path")


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It fails on Windows.")
def test_open_notebooks_from_project_explorer(main_window, qtbot, tmpdir):
    """Test that notebooks are open from the Project explorer."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    projects = main_window.projects
    projects.toggle_view_action.setChecked(True)
    editorstack = main_window.editor.get_current_editorstack()

    # Create a temp project directory
    project_dir = to_text_string(tmpdir.mkdir('test'))

    # Create an empty notebook in the project dir
    nb = osp.join(LOCATION, 'notebook.ipynb')
    shutil.copy(nb, osp.join(project_dir, 'notebook.ipynb'))

    # Create project
    with qtbot.waitSignal(projects.sig_project_loaded):
        projects._create_project(project_dir)

    # Select notebook in the project explorer
    idx = projects.get_widget().treewidget.get_index(
        osp.join(project_dir, 'notebook.ipynb'))
    projects.get_widget().treewidget.setCurrentIndex(idx)

    # Prese Enter there
    qtbot.keyClick(projects.get_widget().treewidget, Qt.Key_Enter)

    # Assert that notebook was open
    assert 'notebook.ipynb' in editorstack.get_current_filename()

    # Convert notebook to a Python file
    projects.get_widget().treewidget.convert_notebook(
        osp.join(project_dir, 'notebook.ipynb'))

    # Assert notebook was open
    assert 'untitled' in editorstack.get_current_filename()

    # Assert its contents are the expected ones
    file_text = editorstack.get_current_editor().toPlainText()
    if nbconvert.__version__ >= '5.4.0':
        expected_text = ('#!/usr/bin/env python\n# coding: utf-8\n\n# In[1]:'
                         '\n\n\n1 + 1\n\n\n# In[ ]:\n\n\n\n\n')
    else:
        expected_text = '\n# coding: utf-8\n\n# In[1]:\n\n\n1 + 1\n\n\n'
    assert file_text == expected_text

    # Close project
    projects.close_project()


@flaky(max_runs=3)
def test_runfile_from_project_explorer(main_window, qtbot, tmpdir):
    """Test that file are run from the Project explorer."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    projects = main_window.projects
    projects.toggle_view_action.setChecked(True)
    editorstack = main_window.editor.get_current_editorstack()

    # Create a temp project directory
    project_dir = to_text_string(tmpdir.mkdir('test'))

    # Create an empty file in the project dir
    test_file = osp.join(LOCATION, 'script.py')
    shutil.copy(test_file, osp.join(project_dir, 'script.py'))

    # Create project
    with qtbot.waitSignal(projects.sig_project_loaded):
        projects._create_project(project_dir)

    # Select file in the project explorer
    idx = projects.get_widget().treewidget.get_index(
        osp.join(project_dir, 'script.py'))
    projects.get_widget().treewidget.setCurrentIndex(idx)

    # Press Enter there
    qtbot.keyClick(projects.get_widget().treewidget, Qt.Key_Enter)

    # Assert that the file was open
    assert 'script.py' in editorstack.get_current_filename()

    # Run Python file
    projects.get_widget().treewidget.run([osp.join(project_dir, 'script.py')])

    # Wait until the new console is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Wait until all objects have appeared in the variable explorer
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Check variables value
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    # Close project
    projects.close_project()


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt', reason="It times out sometimes on Windows")
def test_set_new_breakpoints(main_window, qtbot):
    """Test that new breakpoints are set in the IPython console."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Set a breakpoint
    code_editor = main_window.editor.get_focus_widget()
    code_editor.debugger.toogle_breakpoint(line_number=6)

    # Verify that the breakpoint was set
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!b")
    assert "1   breakpoint   keep yes   at {}:6".format(
        test_file) in control.toPlainText()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@flaky(max_runs=3)
def test_run_code(main_window, qtbot, tmpdir):
    """Test all the different ways we have to run code"""
    # ---- Setup ----
    p = (tmpdir.mkdir(u"runtest's folder èáïü Øαôå 字分误")
         .join(u"runtest's file èáïü Øαôå 字分误.py"))
    filepath = to_text_string(p)
    shutil.copyfile(osp.join(LOCATION, 'script.py'), filepath)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Load test file
    main_window.editor.load(filepath)

    # Move to the editor's first line
    editor = main_window.editor
    code_editor = editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.current_widget()

    # Set modifier for CTRL or darwin Meta
    modifier = Qt.ControlModifier
    if sys.platform == 'darwin':
        modifier = Qt.MetaModifier

    # ---- Run file ----
    qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run lines ----
    # Run the whole file line by line
    for _ in range(code_editor.blockCount()):
        qtbot.keyClick(code_editor, Qt.Key_F9)
        qtbot.wait(200)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run to line ----
    # Run lines from file start until, but excluding, current cursor line
    # Move to line 10 then move one characters into the line and
    # run lines above
    editor.go_to_line(10)
    qtbot.keyClick(code_editor, Qt.Key_Right)
    qtbot.keyClick(code_editor, Qt.Key_F9, modifier=Qt.ShiftModifier)
    qtbot.wait(500)

    assert shell.get_value('a') == 10
    assert shell.get_value('li') == [1, 2, 3]
    # Test that lines below did not run
    assert 'arr' not in nsb.editor.source_model._data.keys()
    assert 's' not in nsb.editor.source_model._data.keys()

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run from line ----
    # Move to line 6, run lines from current cursor line to end
    # Note that last line (14) will raise a NameError if 'a' is not defined
    # Set 'a' to a different value before hand to avoid errors in shell
    shell.execute('a = 100')
    editor.go_to_line(6)
    qtbot.keyClick(code_editor, Qt.Key_Right)
    qtbot.keyClick(code_editor, Qt.Key_F9, modifier=modifier)
    qtbot.wait(500)

    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))
    # Test that lines above did not run, i.e. a is still 100
    assert shell.get_value('a') == 100

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run cell and advance ----
    # Run the five cells present in file
    # Add an unnamed cell at the top of the file
    qtbot.keyClicks(code_editor, 'a = 10')
    qtbot.keyClick(code_editor, Qt.Key_Return)
    qtbot.keyClick(code_editor, Qt.Key_Up)
    for _ in range(5):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
        qtbot.wait(500)

    # Check for errors and the runcell function
    assert 'runcell' in shell._control.toPlainText()
    assert 'Error:' not in shell._control.toPlainText()
    control_text = shell._control.toPlainText()

    # Rerun
    shell.setFocus()
    qtbot.keyClick(shell._control, Qt.Key_Up)
    qtbot.wait(500)
    qtbot.keyClick(shell._control, Qt.Key_Enter, modifier=Qt.ShiftModifier)
    qtbot.wait(500)
    code_editor.setFocus()

    assert control_text != shell._control.toPlainText()
    control_text = shell._control.toPlainText()[len(control_text):]
    # Check for errors and the runcell function
    assert 'runcell' in control_text
    assert 'Error' not in control_text

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Verify result
    assert ']: 10\n' in shell._control.toPlainText()
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Run cell ----
    # Run the first cell in file
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=modifier)

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('a') == 10

    # Press Ctrl+Enter a second time to verify that we're *not* advancing
    # to the next cell
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=modifier)
    assert nsb.editor.source_model.rowCount() == 1

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Debug cell ------
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return,
                       modifier=Qt.AltModifier | Qt.ShiftModifier)
    qtbot.keyClicks(shell._control, '!c')
    qtbot.keyClick(shell._control, Qt.Key_Enter)

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=EVAL_TIMEOUT)

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Re-run last cell ----
    # Run the first three cells in file
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.wait(500)
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.wait(500)
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)

    # Wait until objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 2,
                    timeout=EVAL_TIMEOUT)

    # Clean namespace
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')

    # Wait until there are no objects in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 0,
                    timeout=EVAL_TIMEOUT)

    # Re-run last cell
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.AltModifier)

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=EVAL_TIMEOUT)
    assert shell.get_value('li') == [1, 2, 3]

    # try running cell without file name
    shell.clear()
    # Clean namespace
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')

    with qtbot.waitSignal(shell.executed):
        shell.execute('runcell(0)')
    # Verify result
    assert shell.get_value('a') == 10
    assert 'error' not in shell._control.toPlainText().lower()

    # ---- Closing test file ----
    main_window.editor.close_file()


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
@pytest.mark.parametrize('main_window',
                         [{'spy_config': ('editor', 'run_cell_copy', True)}],
                         indirect=True)
def test_run_cell_copy(main_window, qtbot, tmpdir):
    """Test all the different ways we have to run code"""
    # ---- Setup ----
    p = (tmpdir.mkdir(u"runtest's folder èáïü Øαôå 字分误")
         .join(u"runtest's file èáïü Øαôå 字分误.py"))
    filepath = to_text_string(p)
    shutil.copyfile(osp.join(LOCATION, 'script.py'), filepath)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    # Make sure run_cell_copy is properly set
    for editorstack in main_window.editor.editorstacks:
        editorstack.set_run_cell_copy(True)
    # Load test file
    main_window.editor.load(filepath)

    # Move to the editor's first line
    code_editor = main_window.editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.current_widget()

    # ---- Run cell and advance ----
    # Run the three cells present in file
    for _ in range(4):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
        qtbot.wait(500)

    # Check for errors and the copied code
    assert 'runcell' not in shell._control.toPlainText()
    assert 'a = 10' in shell._control.toPlainText()
    assert 'Error:' not in shell._control.toPlainText()

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Verify result
    assert ']: 10\n' in shell._control.toPlainText()
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

    # ---- Closing test file and reset config ----
    main_window.editor.close_file()
    CONF.set('editor', 'run_cell_copy', False)


@flaky(max_runs=3)
@pytest.mark.skipif(running_in_ci(), reason="Fails on CIs")
def test_open_files_in_new_editor_window(main_window, qtbot):
    """
    This tests that opening files in a new editor window
    is working as expected.

    Test for spyder-ide/spyder#4085.
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


@flaky(max_runs=3)
def test_close_when_file_is_changed(main_window, qtbot):
    """Test closing spyder when there is a file with modifications open."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    editorstack = main_window.editor.get_current_editorstack()
    editor = editorstack.get_current_editor()
    editor.document().setModified(True)

    # Wait for the segfault
    qtbot.wait(3000)


@flaky(max_runs=3)
def test_maximize_minimize_plugins(main_window, qtbot):
    """Test that the maximize button is working as expected."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    def get_random_plugin():
        """Get a random dockable plugin and give it focus"""
        plugins = main_window.get_dockable_plugins()
        for plugin_name, plugin in plugins:
            if plugin_name in [Plugins.Editor, Plugins.IPythonConsole]:
                plugins.remove((plugin_name, plugin))

        plugin = random.choice(plugins)[1]

        if not plugin.get_widget().toggle_view_action.isChecked():
            plugin.toggle_view(True)
            plugin._hide_after_test = True

        plugin.get_widget().get_focus_widget().setFocus()
        return plugin

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Grab maximize button
    max_action = main_window.layouts.maximize_action
    toolbar = main_window.get_plugin(Plugins.Toolbar)
    main_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.Main)
    max_button = main_toolbar.widgetForAction(max_action)

    # Maximize a random plugin
    plugin_1 = get_random_plugin()
    qtbot.mouseClick(max_button, Qt.LeftButton)

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Assert plugin_1 is unmaximized and focus is in the editor
    assert not plugin_1.get_widget().get_maximized_state()
    assert QApplication.focusWidget() is main_window.editor.get_focus_widget()
    assert not max_action.isChecked()
    if hasattr(plugin_1, '_hide_after_test'):
        plugin_1.toggle_view(False)

    # Maximize editor
    qtbot.mouseClick(max_button, Qt.LeftButton)
    assert main_window.editor._ismaximized

    # Verify that the action minimizes the plugin too
    qtbot.mouseClick(max_button, Qt.LeftButton)
    assert not main_window.editor._ismaximized

    # Don't call switch_to_plugin when the IPython console is undocked
    qtbot.mouseClick(max_button, Qt.LeftButton)
    assert main_window.editor._ismaximized
    ipyconsole = main_window.get_plugin(Plugins.IPythonConsole)
    ipyconsole.create_window()
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)
    assert main_window.editor._ismaximized

    # Unmaximize when docking back the IPython console
    ipyconsole.close_window()
    assert not main_window.editor._ismaximized

    # Maximize a plugin and check that it's unmaximized after clicking the
    # debug button
    plugin_2 = get_random_plugin()
    qtbot.mouseClick(max_button, Qt.LeftButton)
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: 'IPdb' in shell._control.toPlainText())
    assert not plugin_2.get_widget().get_maximized_state()
    assert not max_action.isChecked()

    # This checks that running other debugging actions doesn't maximize the
    # editor by error
    debug_next_action = main_window.debug_toolbar_actions[1]
    debug_next_button = main_window.debug_toolbar.widgetForAction(
        debug_next_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_next_button, Qt.LeftButton)
    assert not main_window.editor._ismaximized
    assert not max_action.isChecked()

    # Check that running debugging actions unmaximizes plugins
    plugin_2.get_widget().get_focus_widget().setFocus()
    qtbot.mouseClick(max_button, Qt.LeftButton)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_next_button, Qt.LeftButton)
    assert not plugin_2.get_widget().get_maximized_state()
    assert not max_action.isChecked()
    if hasattr(plugin_2, '_hide_after_test'):
        plugin_2.toggle_view(False)

    # Stop debugger
    stop_debug_action = main_window.debug_toolbar_actions[5]
    stop_debug_button = main_window.debug_toolbar.widgetForAction(
        stop_debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(stop_debug_button, Qt.LeftButton)

    # Maximize a plugin and check that it's unmaximized after running a file
    plugin_3 = get_random_plugin()
    qtbot.mouseClick(max_button, Qt.LeftButton)
    qtbot.mouseClick(run_button, Qt.LeftButton)
    assert not plugin_3.get_widget().get_maximized_state()
    assert not max_action.isChecked()
    if hasattr(plugin_3, '_hide_after_test'):
        plugin_3.toggle_view(False)

    # Maximize a plugin and check that it's unmaximized after running a cell
    plugin_4 = get_random_plugin()
    run_cell_action = main_window.run_toolbar_actions[1]
    run_cell_button = main_window.run_toolbar.widgetForAction(run_cell_action)
    qtbot.mouseClick(max_button, Qt.LeftButton)
    qtbot.mouseClick(run_cell_button, Qt.LeftButton)
    assert not plugin_4.get_widget().get_maximized_state()
    assert not max_action.isChecked()
    if hasattr(plugin_4, '_hide_after_test'):
        plugin_4.toggle_view(False)

    # Maximize a plugin and check that it's unmaximized after running a
    # selection
    plugin_5 = get_random_plugin()
    run_selection_action = main_window.run_toolbar_actions[3]
    run_selection_button = main_window.run_toolbar.widgetForAction(
        run_selection_action)
    qtbot.mouseClick(max_button, Qt.LeftButton)
    qtbot.mouseClick(run_selection_button, Qt.LeftButton)
    assert not plugin_5.get_widget().get_maximized_state()
    assert not max_action.isChecked()
    if hasattr(plugin_5, '_hide_after_test'):
        plugin_5.toggle_view(False)


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt' or running_in_ci() and (PYQT5 and PYQT_VERSION >= '5.9'),
    reason="It times out on Windows and segfaults in our CIs with PyQt >= 5.9")
def test_issue_4066(main_window, qtbot):
    """
    Test for a segfault when these steps are followed:

    1. Open an object present in the Variable Explorer (e.g. a list).
    2. Delete that object in its corresponding console while its
       editor is still open.
    3. Closing that editor by pressing its *Ok* button.
    """
    # Create the object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('myobj = [1, 2, 3]')

    # Open editor associated with that object and get a reference to it
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()
    obj_editor_id = list(nsb.editor.delegate._editors.keys())[0]
    obj_editor = nsb.editor.delegate._editors[obj_editor_id]['editor']

    # Move to the IPython console and delete that object
    main_window.ipyconsole.get_widget().get_focus_widget().setFocus()
    with qtbot.waitSignal(shell.executed):
        shell.execute('del myobj')
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 0, timeout=EVAL_TIMEOUT)

    # Close editor
    ok_widget = obj_editor.btn_close
    qtbot.mouseClick(ok_widget, Qt.LeftButton)

    # Wait for the segfault
    qtbot.wait(3000)


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt', reason="It times out sometimes on Windows")
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
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Edit object
    main_window.variableexplorer.change_visibility(True)
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()

    # Change focus to IPython console
    main_window.ipyconsole.get_widget().get_focus_widget().setFocus()

    # Wait for the error
    qtbot.wait(3000)


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It times out sometimes on Windows and macOS")
def test_c_and_n_pdb_commands(main_window, qtbot):
    """Test that c and n Pdb commands update the Variable Explorer."""
    nsb = main_window.variableexplorer.current_widget()

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Set a breakpoint
    code_editor = main_window.editor.get_focus_widget()
    code_editor.debugger.toogle_breakpoint(line_number=6)
    qtbot.wait(500)

    # Verify that c works
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!c')
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 1)

    # Verify that n works
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 2)

    # Verify that doesn't go to sitecustomize.py with next and stops
    # the debugging session.
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 3)

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!n')
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that the prompt appear
    shell.clear_console()
    assert 'In [2]:' in control.toPlainText()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt', reason="It times out sometimes on Windows")
def test_stop_dbg(main_window, qtbot):
    """Test that we correctly stop a debugging session."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Move to the next line
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!n")

    # Stop debugging
    stop_debug_action = main_window.debug_toolbar_actions[5]
    stop_debug_button = main_window.debug_toolbar.widgetForAction(
        stop_debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(stop_debug_button, Qt.LeftButton)

    # Assert there are only two ipdb prompts in the console
    assert shell._control.toPlainText().count('IPdb') == 2

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It only works on Linux")
def test_change_cwd_dbg(main_window, qtbot):
    """
    Test that using the Working directory toolbar is working while debugging.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file to be able to enter in debugging mode
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: 'IPdb' in control.toPlainText())

    # Set LOCATION as cwd
    main_window.workingdirectory.chdir(tempfile.gettempdir())
    qtbot.wait(1000)
    print(repr(control.toPlainText()))
    shell.clear_console()
    qtbot.waitUntil(lambda: 'IPdb [2]:' in control.toPlainText())

    # Get cwd in console
    qtbot.keyClicks(control, 'import os; os.getcwd()')
    qtbot.keyClick(control, Qt.Key_Enter)

    # Assert cwd is the right one
    qtbot.waitUntil(lambda: tempfile.gettempdir() in control.toPlainText())
    assert tempfile.gettempdir() in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Times out sometimes")
def test_varexp_magic_dbg(main_window, qtbot):
    """Test that %varexp is working while debugging."""
    nsb = main_window.variableexplorer.current_widget()

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file to be able to enter in debugging mode
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Get to an object that can be plotted
    for _ in range(3):
        with qtbot.waitSignal(shell.executed):
            qtbot.keyClicks(control, '!n')
            qtbot.keyClick(control, Qt.Key_Enter)

    # Generate the plot from the Variable Explorer
    nsb.editor.plot('li', 'plot')
    qtbot.wait(1000)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1


@flaky(max_runs=3)
@pytest.mark.parametrize(
    'main_window',
    [{'spy_config': ('ipython_console', 'pylab/inline/figure_format', 1)},
     {'spy_config': ('ipython_console', 'pylab/inline/figure_format', 0)}],
    indirect=True)
def test_plots_plugin(main_window, qtbot, tmpdir, mocker):
    """
    Test that plots generated in the IPython console are properly displayed
    in the plots plugin.
    """
    assert CONF.get('plots', 'mute_inline_plotting') is False
    shell = main_window.ipyconsole.get_current_shellwidget()
    figbrowser = main_window.plots.current_widget()

    # Wait until the window is fully up.
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Generate a plot inline.
    with qtbot.waitSignal(shell.executed):
        shell.execute(("import matplotlib.pyplot as plt\n"
                       "fig = plt.plot([1, 2, 3, 4], '.')\n"))

    if CONF.get('ipython_console', 'pylab/inline/figure_format') == 0:
        assert figbrowser.figviewer.figcanvas.fmt == 'image/png'
    else:
        assert figbrowser.figviewer.figcanvas.fmt == 'image/svg+xml'

    # Get the image name from the html, fetch the image from the shell, and
    # save it as a png.
    html = shell._control.toHtml()
    img_name = re.search('''<img src="(.+?)" /></p>''', html).group(1)

    ipython_figname = osp.join(to_text_string(tmpdir), 'ipython_img.png')
    ipython_qimg = shell._get_image(img_name)
    ipython_qimg.save(ipython_figname)

    # Save the image with the Plots plugin as a png.
    plots_figname = osp.join(to_text_string(tmpdir), 'plots_img.png')
    mocker.patch('spyder.plugins.plots.widgets.figurebrowser.getsavefilename',
                 return_value=(plots_figname, '.png'))
    figbrowser.save_figure()

    assert compare_images(ipython_figname, plots_figname, 0.1) is None


@flaky(max_runs=3)
@pytest.mark.skipif(
    (parse(ipy_release.version) >= parse('7.23.0') and
     parse(ipykernel.__version__) <= parse('5.5.3')),
    reason="Fails due to a bug in the %matplotlib magic")
@pytest.mark.skipif(
    sys.platform.startswith('linux'),
    reason="Timeouts a lot on Linux")
def test_tight_layout_option_for_inline_plot(main_window, qtbot, tmpdir):
    """
    Test that the option to set bbox_inches to 'tight' or 'None' is
    working when plotting inline in the IPython console. By default, figures
    are plotted inline with bbox_inches='tight'.
    """
    tmpdir = to_text_string(tmpdir)

    # Assert that the default is True.
    assert CONF.get('ipython_console', 'pylab/inline/bbox_inches') is True

    fig_dpi = float(CONF.get('ipython_console', 'pylab/inline/resolution'))
    fig_width = float(CONF.get('ipython_console', 'pylab/inline/width'))
    fig_height = float(CONF.get('ipython_console', 'pylab/inline/height'))

    # Wait until the window is fully up.
    shell = main_window.ipyconsole.get_current_shellwidget()
    client = main_window.ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Generate a plot inline with bbox_inches=tight (since it is default) and
    # save the figure with savefig.
    savefig_figname = osp.join(
        tmpdir, 'savefig_bbox_inches_tight.png').replace('\\', '/')
    with qtbot.waitSignal(shell.executed):
        shell.execute(("import matplotlib.pyplot as plt\n"
                       "fig, ax = plt.subplots()\n"
                       "fig.set_size_inches(%f, %f)\n"
                       "ax.set_position([0.25, 0.25, 0.5, 0.5])\n"
                       "ax.set_xticks(range(10))\n"
                       "ax.xaxis.set_ticklabels([])\n"
                       "ax.set_yticks(range(10))\n"
                       "ax.yaxis.set_ticklabels([])\n"
                       "ax.tick_params(axis='both', length=0)\n"
                       "for loc in ax.spines:\n"
                       "    ax.spines[loc].set_color('#000000')\n"
                       "    ax.spines[loc].set_linewidth(2)\n"
                       "ax.axis([0, 9, 0, 9])\n"
                       "ax.plot(range(10), color='#000000', lw=2)\n"
                       "fig.savefig('%s',\n"
                       "            bbox_inches='tight',\n"
                       "            dpi=%f)"
                       ) % (fig_width, fig_height, savefig_figname, fig_dpi))

    # Get the image name from the html, fetch the image from the shell, and
    # then save it to a file.
    html = shell._control.toHtml()
    img_name = re.search('''<img src="(.+?)" /></p>''', html).group(1)
    qimg = shell._get_image(img_name)
    assert isinstance(qimg, QImage)

    # Save the inline figure and assert it is similar to the one generated
    # with savefig.
    inline_figname = osp.join(tmpdir, 'inline_bbox_inches_tight.png')
    qimg.save(inline_figname)
    assert compare_images(savefig_figname, inline_figname, 0.1) is None

    # Change the option so that bbox_inches=None.
    CONF.set('ipython_console', 'pylab/inline/bbox_inches', False)

    # Restart the kernel and wait until it's up again
    with qtbot.waitSignal(client.sig_execution_state_changed,
                          timeout=SHELL_TIMEOUT):
        client.restart_kernel()
    qtbot.waitUntil(lambda: 'In [1]:' in control.toPlainText(),
                    timeout=SHELL_TIMEOUT)

    # Generate the same plot inline with bbox_inches='tight' and save the
    # figure with savefig.
    savefig_figname = osp.join(
        tmpdir, 'savefig_bbox_inches_None.png').replace('\\', '/')
    with qtbot.waitSignal(shell.executed):
        shell.execute(("import matplotlib.pyplot as plt\n"
                       "fig, ax = plt.subplots()\n"
                       "fig.set_size_inches(%f, %f)\n"
                       "ax.set_position([0.25, 0.25, 0.5, 0.5])\n"
                       "ax.set_xticks(range(10))\n"
                       "ax.xaxis.set_ticklabels([])\n"
                       "ax.set_yticks(range(10))\n"
                       "ax.yaxis.set_ticklabels([])\n"
                       "ax.tick_params(axis='both', length=0)\n"
                       "for loc in ax.spines:\n"
                       "    ax.spines[loc].set_color('#000000')\n"
                       "    ax.spines[loc].set_linewidth(2)\n"
                       "ax.axis([0, 9, 0, 9])\n"
                       "ax.plot(range(10), color='#000000', lw=2)\n"
                       "fig.savefig('%s',\n"
                       "            bbox_inches=None,\n"
                       "            dpi=%f)"
                       ) % (fig_width, fig_height, savefig_figname, fig_dpi))

    # Get the image name from the html, fetch the image from the shell, and
    # then save it to a file.
    html = shell._control.toHtml()
    img_name = re.search('''<img src="(.+?)" /></p>''', html).group(1)
    qimg = shell._get_image(img_name)
    assert isinstance(qimg, QImage)

    # Save the inline figure and assert it is similar to the one generated
    # with savefig.
    inline_figname = osp.join(tmpdir, 'inline_bbox_inches_None.png')
    qimg.save(inline_figname)
    assert compare_images(savefig_figname, inline_figname, 0.1) is None


@pytest.mark.skip
@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
def test_switcher(main_window, qtbot, tmpdir):
    """Test the use of shorten paths when necessary in the switcher."""
    switcher = main_window.switcher

    # Assert that the full path of a file is shown in the switcher
    file_a = tmpdir.join('test_file_a.py')
    file_a.write('''
def example_def():
    pass

def example_def_2():
    pass
''')
    main_window.editor.load(str(file_a))

    main_window.open_switcher()
    switcher_paths = [switcher.model.item(item_idx).get_description()
                      for item_idx in range(switcher.model.rowCount())]
    assert osp.dirname(str(file_a)) in switcher_paths or len(str(file_a)) > 75
    switcher.close()

    # Assert that long paths are shortened in the switcher
    dir_b = tmpdir
    for _ in range(3):
        dir_b = dir_b.mkdir(str(uuid.uuid4()))
    file_b = dir_b.join('test_file_b.py')
    file_b.write('bar\n')
    main_window.editor.load(str(file_b))

    main_window.open_switcher()
    file_b_text = switcher.model.item(
        switcher.model.rowCount() - 1).get_description()
    assert '...' in file_b_text
    switcher.close()

    # Assert search works correctly
    search_texts = ['test_file_a', 'file_b', 'foo_spam']
    expected_paths = [file_a, file_b, None]
    for search_text, expected_path in zip(search_texts, expected_paths):
        main_window.open_switcher()
        qtbot.keyClicks(switcher.edit, search_text)
        qtbot.wait(200)
        assert switcher.count() == bool(expected_path)
        switcher.close()

    # Assert symbol switcher works
    main_window.editor.set_current_filename(str(file_a))

    code_editor = main_window.editor.get_focus_widget()
    qtbot.waitUntil(lambda: code_editor.completions_available,
                    timeout=COMPLETION_TIMEOUT)

    with qtbot.waitSignal(
            code_editor.completions_response_signal,
            timeout=COMPLETION_TIMEOUT):
        code_editor.request_symbols()

    qtbot.wait(9000)

    main_window.open_switcher()
    qtbot.keyClicks(switcher.edit, '@')
    qtbot.wait(200)
    assert switcher.count() == 2
    switcher.close()


@flaky(max_runs=3)
def test_edidorstack_open_switcher_dlg(main_window, tmpdir, qtbot):
    """
    Test that the file switcher is working as expected when called from the
    editorstack.

    Regression test for spyder-ide/spyder#10684
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Add a file to the editor.
    file = tmpdir.join('test_file_open_switcher_dlg.py')
    file.write("a test file for test_edidorstack_open_switcher_dlg")
    main_window.editor.load(str(file))

    # Test that the file switcher opens as expected from the editorstack.
    editorstack = main_window.editor.get_current_editorstack()
    assert editorstack.switcher_dlg is None
    editorstack.open_switcher_dlg()
    assert editorstack.switcher_dlg
    assert editorstack.switcher_dlg.isVisible()
    assert (editorstack.switcher_dlg.count() ==
            len(main_window.editor.get_filenames()))


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It times out too much on Windows and macOS")
def test_editorstack_open_symbolfinder_dlg(main_window, qtbot, tmpdir):
    """
    Test that the symbol finder is working as expected when called from the
    editorstack.

    Regression test for spyder-ide/spyder#10684
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Add a file to the editor.
    file = tmpdir.join('test_file.py')
    file.write('''
               def example_def():
                   pass

               def example_def_2():
                   pass
               ''')
    main_window.editor.load(str(file))

    code_editor = main_window.editor.get_focus_widget()
    qtbot.waitUntil(lambda: code_editor.completions_available,
                    timeout=COMPLETION_TIMEOUT)

    with qtbot.waitSignal(
            code_editor.completions_response_signal,
            timeout=COMPLETION_TIMEOUT):
        code_editor.request_symbols()

    qtbot.wait(5000)

    # Test that the symbol finder opens as expected from the editorstack.
    editorstack = main_window.editor.get_current_editorstack()
    assert editorstack.switcher_dlg is None
    editorstack.open_symbolfinder_dlg()
    assert editorstack.switcher_dlg
    assert editorstack.switcher_dlg.isVisible()
    assert editorstack.switcher_dlg.count() == 2


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="Times out sometimes on macOS")
def test_run_static_code_analysis(main_window, qtbot):
    """This tests that the Pylint plugin is working as expected."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    from spyder.plugins.pylint.main_widget import PylintWidgetActions
    # Select the third-party plugin
    pylint_plugin = main_window.get_plugin(Plugins.Pylint)

    # Do an analysis
    test_file = osp.join(LOCATION, 'script_pylint.py')
    main_window.editor.load(test_file)
    pylint_plugin.get_action(PylintWidgetActions.RunCodeAnalysis).trigger()
    qtbot.wait(3000)

    # Perform the test
    # Check output of the analysis
    treewidget = pylint_plugin.get_widget().get_focus_widget()
    qtbot.waitUntil(lambda: treewidget.results is not None,
                    timeout=SHELL_TIMEOUT)
    result_content = treewidget.results
    assert result_content['C:']

    pylint_version = parse(pylint.__version__)
    if pylint_version < parse('2.5.0'):
        number_of_conventions = 5
    else:
        number_of_conventions = 3
    assert len(result_content['C:']) == number_of_conventions

    # Close the file
    main_window.editor.close_file()


@flaky(max_runs=3)
@pytest.mark.close_main_window
@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It stalls the CI sometimes on Linux")
def test_troubleshooting_menu_item_and_url(main_window, qtbot, monkeypatch):
    """Test that the troubleshooting menu item calls the valid URL."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    application_plugin = main_window.application
    MockQDesktopServices = Mock()
    mockQDesktopServices_instance = MockQDesktopServices()
    attr_to_patch = ('spyder.utils.qthelpers.QDesktopServices')
    monkeypatch.setattr(attr_to_patch, MockQDesktopServices)

    # Unit test of help menu item: Make sure the correct URL is called.
    application_plugin.trouble_action.trigger()
    assert MockQDesktopServices.openUrl.call_count == 1
    mockQDesktopServices_instance.openUrl.called_once_with(__trouble_url__)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It fails on Windows")
@pytest.mark.skipif(
    sys.platform == 'darwin' and running_in_ci(),
    reason="It stalls the CI sometimes on MacOS")
@pytest.mark.close_main_window
def test_help_opens_when_show_tutorial_full(main_window, qtbot):
    """
    Test fix for spyder-ide/spyder#6317.

    'Show tutorial' opens the help plugin if closed.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    HELP_STR = "Help"

    help_pane_menuitem = None
    for action in main_window.layouts.plugins_menu.get_actions():
        if action.text() == HELP_STR:
            help_pane_menuitem = action
            break

    # Test opening tutorial with Help plugin closed
    main_window.help.toggle_view_action.setChecked(False)
    qtbot.wait(500)
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert help_tabbar is None and help_index is None
    assert not isinstance(main_window.focusWidget(), ObjectComboBox)
    assert not help_pane_menuitem.isChecked()

    main_window.help.show_tutorial()
    qtbot.wait(500)

    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert None not in (help_tabbar, help_index)
    assert help_index == help_tabbar.currentIndex()
    assert help_pane_menuitem.isChecked()

    # Test opening tutorial with help plugin open, but not selected
    help_tabbar.setCurrentIndex((help_tabbar.currentIndex() + 1)
                                % help_tabbar.count())
    qtbot.wait(500)
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert None not in (help_tabbar, help_index)
    assert help_index != help_tabbar.currentIndex()
    assert help_pane_menuitem.isChecked()

    main_window.help.show_tutorial()
    qtbot.wait(500)
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert None not in (help_tabbar, help_index)
    assert help_index == help_tabbar.currentIndex()
    assert help_pane_menuitem.isChecked()

    # Test opening tutorial with help plugin open and the active tab
    qtbot.wait(500)
    main_window.help.show_tutorial()
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    qtbot.wait(500)
    assert None not in (help_tabbar, help_index)
    assert help_index == help_tabbar.currentIndex()
    assert help_pane_menuitem.isChecked()


@flaky(max_runs=3)
@pytest.mark.close_main_window
def test_report_issue(main_window, qtbot):
    """Test that the report error dialog opens correctly."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    main_window.console.report_issue()
    qtbot.waitUntil(
        lambda: main_window.console.get_widget()._report_dlg is not None)
    assert main_window.console.get_widget()._report_dlg.isVisible()
    assert main_window.console.get_widget()._report_dlg.close()


@flaky(max_runs=3)
@pytest.mark.skipif(
    not os.name == 'nt', reason="It segfaults on Linux and Mac")
def test_custom_layouts(main_window, qtbot):
    """Test that layout are showing the expected widgets visible."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    mw = main_window
    mw.first_spyder_run = False
    prefix = 'window' + '/'
    settings = mw.layouts.load_window_settings(prefix=prefix, default=True)

    # Test layout changes
    for layout_idx in get_class_values(DefaultLayouts):
        with qtbot.waitSignal(mw.sig_layout_setup_ready, timeout=5000):
            layout = mw.layouts.setup_default_layouts(
                layout_idx, settings=settings)

            qtbot.wait(500)

            for area in layout._areas:
                if area['visible']:
                    for plugin_id in area['plugin_ids']:
                        if plugin_id not in area['hidden_plugin_ids']:
                            plugin = mw.get_plugin(plugin_id)
                            print(plugin)  # spyder: test-skip
                            try:
                                # New API
                                assert plugin.get_widget().isVisible()
                            except AttributeError:
                                # Old API
                                assert plugin.isVisible()


@flaky(max_runs=3)
@pytest.mark.skipif(not running_in_ci() or sys.platform.startswith('linux'),
                    reason="Only runs in CIs and fails on Linux sometimes")
def test_programmatic_custom_layouts(main_window, qtbot):
    """
    Test that a custom layout gets registered and it is recognized."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    mw = main_window
    mw.first_spyder_run = False

    # Test layout registration
    layout_id = 'testing layout'
    # Test the testing plugin is being loaded
    mw.get_plugin('spyder_boilerplate')
    # Get the registered layout
    layout = mw.layouts.get_layout(layout_id)

    with qtbot.waitSignal(mw.sig_layout_setup_ready, timeout=5000):
        mw.layouts.quick_layout_switch(layout_id)

        qtbot.wait(500)

        for area in layout._areas:
            if area['visible']:
                for plugin_id in area['plugin_ids']:
                    if plugin_id not in area['hidden_plugin_ids']:
                        plugin = mw.get_plugin(plugin_id)
                        print(plugin)  # spyder: test-skip
                        try:
                            # New API
                            assert plugin.get_widget().isVisible()
                        except AttributeError:
                            # Old API
                            assert plugin.isVisible()


@flaky(max_runs=3)
def test_save_on_runfile(main_window, qtbot):
    """Test that layout are showing the expected widgets visible."""
    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    test_file_copy = test_file[:-3] + '_copy.py'
    shutil.copyfile(test_file, test_file_copy)
    main_window.editor.load(test_file_copy)
    code_editor = main_window.editor.get_focus_widget()

    # Verify result
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    qtbot.keyClicks(code_editor, 'test_var = 123', delay=100)
    filename = code_editor.filename
    with qtbot.waitSignal(shell.sig_prompt_ready):
        shell.execute('runfile("{}")'.format(remove_backslashes(filename)))

    assert shell.get_value('test_var') == 123
    main_window.editor.close_file()
    os.remove(test_file_copy)


@pytest.mark.skipif(sys.platform == 'darwin', reason="Fails on macOS")
@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="Fails on Linux sometimes")
def test_pylint_follows_file(qtbot, tmpdir, main_window):
    """Test that file editor focus change updates pylint combobox filename."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    pylint_plugin = main_window.get_plugin(Plugins.Pylint)

    # Show pylint plugin
    pylint_plugin.dockwidget.show()
    pylint_plugin.dockwidget.raise_()

    # Create base temporary directory
    basedir = tmpdir.mkdir('foo')

    # Open some files
    for idx in range(2):
        fh = basedir.join('{}.py'.format(idx))
        fname = str(fh)
        fh.write('print("Hello world!")')
        main_window.open_file(fh)
        qtbot.wait(200)
        assert fname == pylint_plugin.get_filename()

    # Create a editor split
    main_window.editor.editorsplitter.split(orientation=Qt.Vertical)
    qtbot.wait(500)

    # Open other files
    for idx in range(4):
        fh = basedir.join('{}.py'.format(idx))
        fh.write('print("Hello world!")')
        fname = str(fh)
        main_window.open_file(fh)
        qtbot.wait(200)
        assert fname == pylint_plugin.get_filename()

    # Close split panel
    for editorstack in reversed(main_window.editor.editorstacks):
        editorstack.close_split()
        break
    qtbot.wait(1000)


@flaky(max_runs=3)
@pytest.mark.skipif(
    sys.platform == 'darwin', reason="Segfaults on MacOS after passing")
def test_report_comms_error(qtbot, main_window):
    """Test if a comms error is correctly displayed."""
    CONF.set('main', 'show_internal_errors', True)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    # Create a bogus get_cwd
    with qtbot.waitSignal(shell.executed):
        shell.execute('def get_cwd(): import foo')
    with qtbot.waitSignal(shell.executed):
        shell.execute("get_ipython().kernel.frontend_comm."
                      "register_call_handler('get_cwd', get_cwd)")
    with qtbot.waitSignal(shell.executed, timeout=3000):
        shell.execute('ls')

    qtbot.waitUntil(lambda: main_window.console.error_dialog is not None,
                    timeout=EVAL_TIMEOUT)
    error_dialog = main_window.console.error_dialog
    assert 'Exception in comms call get_cwd' in error_dialog.error_traceback
    assert 'No module named' in error_dialog.error_traceback
    main_window.console.close_error_dialog()
    CONF.set('main', 'show_internal_errors', False)


@flaky(max_runs=3)
def test_break_while_running(main_window, qtbot, tmpdir):
    """Test that we can set breakpoints while running."""
    # Create loop
    code = ("import time\n"
            "for i in range(100):\n"
            "    print(i)\n"
            "    time.sleep(0.1)\n"
            )
    p = tmpdir.join("loop_script.py")
    p.write(code)
    test_file = to_text_string(p)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Load test file
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Click the debug button
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)
        qtbot.wait(1000)

    # Continue debugging
    qtbot.keyClicks(shell._control, '!c')
    qtbot.keyClick(shell._control, Qt.Key_Enter)
    qtbot.wait(500)

    with qtbot.waitSignal(shell.executed):
        # Set a breakpoint
        code_editor.debugger.toogle_breakpoint(line_number=3)
        # We should drop into the debugger

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(shell._control, '!q')
        qtbot.keyClick(shell._control, Qt.Key_Enter)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()


@flaky(max_runs=5)
def test_preferences_run_section_exists(main_window, qtbot):
    """
    Test for spyder-ide/spyder#13524 regression.
    Ensure the Run section exists.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    dlg, index, page = preferences_dialog_helper(qtbot, main_window, 'run')
    assert page

    dlg.ok_btn.animateClick()

    preferences = main_window.preferences
    container = preferences.get_container()

    qtbot.waitUntil(lambda: container.dialog is None, timeout=5000)


def test_preferences_checkboxes_not_checked_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#10139 regression.

    Enabling codestyle/docstyle on the completion section of preferences,
    was not updating correctly.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Reset config
    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values', 'pydocstyle'),
             False)

    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values', 'pycodestyle'),
             False)

    # Open completion prefences and update options
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'completions')
    # Get the correct tab pages inside the Completion preferences page
    tnames = [page.tabs.tabText(i).lower() for i in range(page.tabs.count())]

    tabs = [(page.tabs.widget(i).layout().itemAt(0).widget(), i)
            for i in range(page.tabs.count())]

    tabs = dict(zip(tnames, tabs))
    tab_widgets = {
        'code style and formatting': 'code_style_check',
        'docstring style': 'docstring_style_check'
    }

    for tabname in tab_widgets:
        tab, idx = tabs[tabname]
        check_name = tab_widgets[tabname]
        check = getattr(tab, check_name)
        page.tabs.setCurrentIndex(idx)
        check.animateClick()
        qtbot.wait(500)
    dlg.ok_btn.animateClick()

    preferences = main_window.preferences
    container = preferences.get_container()

    qtbot.waitUntil(lambda: container.dialog is None,
                    timeout=5000)

    # Check the menus are correctly updated
    count = 0
    for menu_item in main_window.source_menu_actions:
        if menu_item and isinstance(menu_item, QAction):
            print(menu_item.text(), menu_item.isChecked())

            if 'code style' in menu_item.text():
                assert menu_item.isChecked()
                count += 1
            elif 'docstring style' in menu_item.text():
                assert menu_item.isChecked()
                count += 1
    assert count == 2

    # Reset config
    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values', 'pydocstyle'),
             False)

    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values', 'pycodestyle'),
             False)


def test_preferences_change_font_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#10284 regression.

    Changing font resulted in error.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'appearance')
    for fontbox in [page.plain_text_font.fontbox,
                    page.rich_text_font.fontbox]:
        fontbox.setFocus()
        idx = fontbox.currentIndex()
        fontbox.setCurrentIndex(idx + 1)

    preferences = main_window.preferences
    container = preferences.get_container()

    dlg.ok_btn.animateClick()

    qtbot.waitUntil(lambda: container.dialog is None, timeout=5000)


@pytest.mark.skipif(
    sys.platform == 'darwin',
    reason="Changes of Shitf+Return shortcut cause an ambiguous shortcut")
def test_preferences_empty_shortcut_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#12992 regression.

    Overwriting shortcuts results in a shortcuts conflict.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Setup shortcuts (set run cell and advance shortcut to run selection)
    base_run_cell_advance = CONF.get_shortcut(
        'editor', 'run cell and advance')  # Should be Shift+Return
    base_run_selection = CONF.get_shortcut(
        'editor', 'run selection')  # Should be F9
    assert base_run_cell_advance == 'Shift+Return'
    assert base_run_selection == 'F9'

    CONF.set_shortcut(
        'editor', 'run cell and advance', '')
    CONF.set_shortcut(
        'editor', 'run selection', base_run_cell_advance)
    with qtbot.waitSignal(main_window.shortcuts.sig_shortcuts_updated):
        main_window.shortcuts.apply_shortcuts()

    # Check execution of shortcut
    # Create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(u'print(0)\nprint(ññ)')

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(lambda: u'print(0)' in shell._control.toPlainText())
    assert u'ññ' not in shell._control.toPlainText()

    # Reset shortcuts
    CONF.set_shortcut(
        'editor', 'run selection', 'F9')
    CONF.set_shortcut(
        'editor', 'run cell and advance', 'Shift+Return')

    # Wait for shortcut change to actually be applied
    with qtbot.waitSignal(main_window.shortcuts.sig_shortcuts_updated):
        main_window.shortcuts.apply_shortcuts()

    # Check shortcut run cell and advance reset
    code_editor.setFocus()
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)

    qtbot.waitUntil(lambda: u'ññ' in shell._control.toPlainText(),
                    timeout=EVAL_TIMEOUT)

    assert u'ññ' in shell._control.toPlainText()


def test_preferences_shortcut_reset_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#11132 regression.

    Resetting shortcut resulted in error.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'shortcuts')
    page.reset_to_default(force=True)
    dlg.ok_btn.animateClick()

    qtbot.waitUntil(
        lambda: main_window.preferences.get_container().dialog is None,
        timeout=EVAL_TIMEOUT)


@pytest.mark.order(1)
@flaky(max_runs=3)
def test_preferences_change_interpreter(qtbot, main_window):
    """Test that on main interpreter change signal is emitted."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Check original pyls configuration
    lsp = main_window.completions.get_provider('lsp')
    config = lsp.generate_python_config()
    jedi = config['configurations']['pylsp']['plugins']['jedi']
    assert jedi['environment'] is sys.executable
    assert jedi['extra_paths'] == []

    # Change main interpreter on preferences
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'main_interpreter')
    page.cus_exec_radio.setChecked(True)
    page.cus_exec_combo.combobox.setCurrentText(sys.executable)

    mi_container = main_window.main_interpreter.get_container()
    with qtbot.waitSignal(mi_container.sig_interpreter_changed,
                          timeout=5000, raising=True):
        dlg.ok_btn.animateClick()

    # Check updated pyls configuration
    config = lsp.generate_python_config()
    jedi = config['configurations']['pylsp']['plugins']['jedi']
    assert jedi['environment'] == sys.executable
    assert jedi['extra_paths'] == []


@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="Segfaults on Linux")
def test_preferences_last_page_is_loaded(qtbot, main_window):
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Test that the last page is updated on re open
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'main_interpreter')
    preferences = main_window.preferences
    container = preferences.get_container()

    qtbot.waitUntil(lambda: container.dialog is not None,
                    timeout=5000)
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: container.dialog is None,
                    timeout=5000)

    main_window.show_preferences()
    qtbot.waitUntil(lambda: container.dialog is not None,
                    timeout=5000)
    dlg = container.dialog
    assert dlg.get_current_index() == index
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: container.dialog is None,
                    timeout=5000)


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It times out too much on Windows and macOS")
def test_go_to_definition(main_window, qtbot, capsys):
    """Test that go-to-definition works as expected."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # --- Code that gives no definition
    code_no_def = dedent("""
    from qtpy.QtCore import Qt
    Qt.FramelessWindowHint""")

    # Create new editor with code and wait until LSP is ready
    main_window.editor.new(text=code_no_def)
    code_editor = main_window.editor.get_focus_widget()
    qtbot.waitUntil(lambda: code_editor.completions_available,
                    timeout=COMPLETION_TIMEOUT)

    # Move cursor to the left one character to be next to
    # FramelessWindowHint
    code_editor.move_cursor(-1)
    with qtbot.waitSignal(
            code_editor.completions_response_signal,
            timeout=COMPLETION_TIMEOUT):
        code_editor.go_to_definition_from_cursor()

    # Capture stderr and assert there are no errors
    sys_stream = capsys.readouterr()
    assert sys_stream.err == u''

    # --- Code that gives definition
    code_def = "import qtpy.QtCore"

    # Create new editor with code and wait until LSP is ready
    main_window.editor.new(text=code_def)
    code_editor = main_window.editor.get_focus_widget()
    qtbot.waitUntil(lambda: code_editor.completions_available,
                    timeout=COMPLETION_TIMEOUT)

    # Move cursor to the left one character to be next to QtCore
    code_editor.move_cursor(-1)
    with qtbot.waitSignal(
            code_editor.completions_response_signal,
            timeout=COMPLETION_TIMEOUT):
        code_editor.go_to_definition_from_cursor()

    def _get_filenames():
        return [osp.basename(f) for f in main_window.editor.get_filenames()]

    qtbot.waitUntil(lambda: 'QtCore.py' in _get_filenames())
    assert 'QtCore.py' in _get_filenames()


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="It times out on macOS")
def test_debug_unsaved_file(main_window, qtbot):
    """Test that we can debug an unsaved file."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    control = shell._control
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text('print(0)\nprint(1)\nprint(2)')

    # Set breakpoint
    code_editor.debugger.toogle_breakpoint(line_number=2)
    qtbot.wait(500)

    # Start debugging
    qtbot.mouseClick(debug_button, Qt.LeftButton)

    # There is a breakpoint, so it should continue
    qtbot.waitUntil(
        lambda: '!continue' in shell._control.toPlainText())
    qtbot.waitUntil(
        lambda: "1---> 2 print(1)" in control.toPlainText())


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "debug", [True, False])
@pytest.mark.known_leak
def test_runcell(main_window, qtbot, tmpdir, debug):
    """Test the runcell command."""
    # Write code with a cell to a file
    code = u"result = 10; fname = __file__"
    p = tmpdir.join("cell-test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    if debug:
        function = 'debugcell'
    else:
        function = 'runcell'
    # Execute runcell
    with qtbot.waitSignal(shell.executed):
        shell.execute(function + u"(0, r'{}')".format(to_text_string(p)))

    if debug:
        # Reach the 'name' input
        shell.pdb_execute('!c')

    qtbot.wait(1000)

    # Verify that the `result` variable is defined
    assert shell.get_value('result') == 10

    # Verify that the `fname` variable is `cell-test.py`
    assert "cell-test.py" in shell.get_value('fname')

    # Verify that the `__file__` variable is undefined
    try:
        shell.get_value('__file__')
        assert False
    except KeyError:
        pass


@flaky(max_runs=3)
def test_runcell_leading_indent(main_window, qtbot, tmpdir):
    """Test the runcell command with leading indent."""
    # Write code with a cell to a file
    code = ("def a():\n    return\nif __name__ == '__main__':\n"
            "# %%\n    print(1233 + 1)\n")
    p = tmpdir.join("cell-test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Execute runcell
    with qtbot.waitSignal(shell.executed):
        shell.execute("runcell(1, r'{}')".format(to_text_string(p)))

    assert "1234" in shell._control.toPlainText()
    assert "This is not valid Python code" not in shell._control.toPlainText()


@flaky(max_runs=3)
def test_varexp_rename(main_window, qtbot, tmpdir):
    """
    Test renaming a variable.
    Regression test for spyder-ide/spyder#10735
    """
    # ---- Setup ----
    p = (tmpdir.mkdir(u"varexp_rename").join(u"script.py"))
    filepath = to_text_string(p)
    shutil.copyfile(osp.join(LOCATION, 'script.py'), filepath)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Load test file
    main_window.editor.load(filepath)

    # Move to the editor's first line
    code_editor = main_window.editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.current_widget()

    # ---- Run file ----
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Rename one element
    nsb.editor.setCurrentIndex(nsb.editor.model.index(1, 0))
    nsb.editor.rename_item(new_name='arr2')

    # Wait until all objects have updated in the variable explorer
    def data(cm, i, j):
        return cm.data(cm.index(i, j))
    qtbot.waitUntil(lambda: data(nsb.editor.model, 1, 0) == 'arr2',
                    timeout=EVAL_TIMEOUT)

    assert data(nsb.editor.model, 0, 0) == 'a'
    assert data(nsb.editor.model, 1, 0) == 'arr2'
    assert data(nsb.editor.model, 2, 0) == 'li'
    assert data(nsb.editor.model, 3, 0) == 's'

    # ---- Run file again ----
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 5,
                    timeout=EVAL_TIMEOUT)

    assert data(nsb.editor.model, 0, 0) == 'a'
    assert data(nsb.editor.model, 1, 0) == 'arr'
    assert data(nsb.editor.model, 2, 0) == 'arr2'
    assert data(nsb.editor.model, 3, 0) == 'li'
    assert data(nsb.editor.model, 4, 0) == 's'


@flaky(max_runs=3)
def test_varexp_remove(main_window, qtbot, tmpdir):
    """
    Test removing a variable.
    Regression test for spyder-ide/spyder#10709
    """
    # ---- Setup ----
    p = (tmpdir.mkdir(u"varexp_remove").join(u"script.py"))
    filepath = to_text_string(p)
    shutil.copyfile(osp.join(LOCATION, 'script.py'), filepath)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Load test file
    main_window.editor.load(filepath)

    # Move to the editor's first line
    code_editor = main_window.editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.current_widget()

    # ---- Run file ----
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_F5)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Remove one element
    nsb.editor.setCurrentIndex(nsb.editor.model.index(1, 0))
    nsb.editor.remove_item(force=True)

    # Wait until all objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 3,
                    timeout=EVAL_TIMEOUT)

    def data(cm, i, j):
        assert cm.rowCount() == 3
        return cm.data(cm.index(i, j))
    assert data(nsb.editor.model, 0, 0) == 'a'
    assert data(nsb.editor.model, 1, 0) == 'li'
    assert data(nsb.editor.model, 2, 0) == 's'


@flaky(max_runs=3)
def test_varexp_refresh(main_window, qtbot):
    """
    Test refreshing the variable explorer while the kernel is executing.
    """
    # Create object
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    shell.execute("import time\n"
                  "for i in range(10):\n"
                  "    print('i = {}'.format(i))\n"
                  "    time.sleep(.1)\n")

    qtbot.waitUntil(lambda: "i = 0" in control.toPlainText())
    qtbot.wait(300)
    # Get value object
    nsb = main_window.variableexplorer.current_widget()

    # This is empty
    assert len(nsb.editor.source_model._data) == 0

    nsb.refresh_table()
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 1)

    assert 0 < int(nsb.editor.source_model._data['i']['view']) < 9


@flaky(max_runs=3)
@pytest.mark.no_new_console
@pytest.mark.skipif(sys.platform == 'darwin', reason="Fails on macOS")
@pytest.mark.parametrize('main_window',
                         [{'spy_config': ('editor', 'run_cell_copy', False)}],
                         indirect=True)
def test_runcell_edge_cases(main_window, qtbot, tmpdir):
    """
    Test if runcell works with an unnamed cell at the top of the file
    and with an empty cell.
    """
    # Write code with a cell to a file
    code = ('if True:\n'
            '    a = 1\n'
            '#%%')
    p = tmpdir.join("test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    code_editor = main_window.editor.get_focus_widget()
    # call runcell
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(lambda: 'runcell(0' in shell._control.toPlainText(),
                    timeout=SHELL_TIMEOUT)
    assert 'runcell(0' in shell._control.toPlainText()
    assert 'cell is empty' not in shell._control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(lambda: 'runcell(1' in shell._control.toPlainText(),
                    timeout=SHELL_TIMEOUT)
    assert 'runcell(1' in shell._control.toPlainText()
    assert 'Error' not in shell._control.toPlainText()
    assert 'cell is empty' in shell._control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="Fails on linux")
def test_runcell_pdb(main_window, qtbot):
    """Test the runcell command in pdb."""
    # Write code with a cell to a file
    code = ("if 'abba' in dir():\n"
            "    print('abba {}'.format(abba))\n"
            "else:\n"
            "    def foo():\n"
            "        abba = 27\n"
            "    foo()\n")
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)

    # Start debugging
    with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    for key in ['!n', '!n', '!s', '!n', '!n']:
        with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
            qtbot.keyClicks(shell._control, key)
            qtbot.keyClick(shell._control, Qt.Key_Enter)

    assert shell.get_value('abba') == 27

    code_editor.setFocus()
    # call runcell
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    assert "runcell" in shell._control.toPlainText()

    # Make sure the local variables are detected
    assert "abba 27" in shell._control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.parametrize("debug", [False, True])
def test_runcell_cache(main_window, qtbot, debug):
    """Test the runcell command cache."""
    # Write code with a cell to a file
    code = ("import time\n"
            "time.sleep(.5)\n"
            "# %%\n"
            "print('Done')\n")
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)

    if debug:
        # Start debugging
        with qtbot.waitSignal(shell.executed):
            shell.execute("%debug print()")

    # Run the two cells
    code_editor.setFocus()
    code_editor.move_cursor(0)
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.wait(100)
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.wait(500)

    qtbot.waitUntil(lambda: "Done" in shell._control.toPlainText())


@flaky(max_runs=3)
def test_path_manager_updates_clients(qtbot, main_window, tmpdir):
    """Check that on path manager updates, consoles correctly update."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    python_path_manager = main_window.get_plugin(Plugins.PythonpathManager)
    python_path_manager.show_path_manager()
    dlg = python_path_manager.path_manager_dialog

    test_folder = 'foo-spam-bar-123'
    folder = str(tmpdir.mkdir(test_folder))
    dlg.add_path(folder)
    qtbot.waitUntil(lambda: dlg.button_ok.isEnabled(), timeout=EVAL_TIMEOUT)

    with qtbot.waitSignal(dlg.sig_path_changed, timeout=EVAL_TIMEOUT):
        dlg.button_ok.animateClick()

    cmd = 'import sys;print(sys.path)'

    # Check that there is at least one shell
    shells = [c.shellwidget for c in main_window.ipyconsole.get_clients()
              if c is not None]
    assert len(shells) >= 1

    # Check clients are updated
    for shell in shells:
        control = shell._control
        control.setFocus()

        qtbot.waitUntil(lambda: shell._prompt_html is not None,
                        timeout=SHELL_TIMEOUT)

        with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
            shell.execute(cmd)

        # Shell sys.path should be updated
        # Output to shell may be delayed, timeout stands in for assertion
        # control.toPlainText may have extra file separators so use test_folder
        qtbot.waitUntil(lambda: test_folder in control.toPlainText(),
                        timeout=SHELL_TIMEOUT)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or sys.platform == 'darwin',
                    reason="It times out on macOS and Windows")
def test_pdb_key_leak(main_window, qtbot, tmpdir):
    """
    Check that pdb notify spyder doesn't call
    QApplication.processEvents(). If it does there might be keystoke leakage.
    see #10834
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = shell._control

    # Write code to a file
    code1 = ("def a():\n"
             "    1/0")
    code2 = ("from tmp import a\n"
             "a()")
    folder = tmpdir.join('tmp_folder')
    test_file = folder.join('tmp.py')
    test_file.write(code1, ensure=True)

    test_file2 = folder.join('tmp2.py')
    test_file2.write(code2)

    # Run tmp2 and get an error
    with qtbot.waitSignal(shell.executed):
        shell.execute('runfile("' + str(test_file2).replace("\\", "/") +
                      '", wdir="' + str(folder).replace("\\", "/") + '")')
    assert '1/0' in control.toPlainText()

    # Replace QApplication.processEvents to make sure it is not called
    super_processEvents = QApplication.processEvents

    def processEvents():
        processEvents.called = True
        return super_processEvents()

    processEvents.called = False
    try:
        QApplication.processEvents = processEvents
        # Debug and open both files
        with qtbot.waitSignal(shell.executed):
            shell.execute('%debug')
        with qtbot.waitSignal(shell.executed):
            qtbot.keyClicks(control, '!u')
            qtbot.keyClick(control, Qt.Key_Enter)

        # Wait until both files are open
        qtbot.waitUntil(
            lambda: osp.normpath(str(test_file)) in [
                osp.normpath(p) for p in main_window.editor.get_filenames()])
        qtbot.waitUntil(
            lambda: str(test_file2) in [
                osp.normpath(p) for p in main_window.editor.get_filenames()])

        # Make sure the events are not processed.
        assert not processEvents.called
    finally:
        QApplication.processEvents = super_processEvents


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="It times out on macOS")
@pytest.mark.parametrize("where", [True, False])
def test_pdb_step(main_window, qtbot, tmpdir, where):
    """
    Check that pdb notify Spyder only moves when a new line is reached.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = shell._control

    # Write code to a file
    code1 = ("def a():\n"
             "    1/0")
    code2 = ("from tmp import a\n"
             "a()")
    folder = tmpdir.join('tmp_folder')
    test_file = folder.join('tmp.py')
    test_file.write(code1, ensure=True)

    test_file2 = folder.join('tmp2.py')
    test_file2.write(code2)

    # Run tmp2 and get an error
    with qtbot.waitSignal(shell.executed):
        shell.execute('runfile("' + str(test_file2).replace("\\", "/") +
                      '", wdir="' + str(folder).replace("\\", "/") + '")')
    qtbot.wait(1000)
    assert '1/0' in control.toPlainText()

    # Debug and enter first file
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug')
    qtbot.waitUntil(
        lambda: osp.samefile(
            main_window.editor.get_current_editor().filename,
            str(test_file)))

    # Move to another file
    main_window.editor.new()
    qtbot.wait(100)
    assert main_window.editor.get_current_editor().filename != str(test_file)
    current_filename = main_window.editor.get_current_editor().filename

    # Run a random command, make sure we don't move
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!a')
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(1000)
    assert current_filename == main_window.editor.get_current_editor().filename

    # Go up and enter second file
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!u')
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: osp.samefile(
            main_window.editor.get_current_editor().filename,
            str(test_file2)))

    # Go back to first file
    editor_stack = main_window.editor.get_current_editorstack()
    index = editor_stack.has_filename(str(test_file))
    assert index is not None
    editor_stack.set_stack_index(index)

    assert osp.samefile(
        main_window.editor.get_current_editor().filename,
        str(test_file))

    if where:
        # go back to the second file with where
        with qtbot.waitSignal(shell.executed):
            qtbot.keyClicks(control, '!w')
            qtbot.keyClick(control, Qt.Key_Enter)
        qtbot.wait(1000)

        # Make sure we moved
        assert osp.samefile(
            main_window.editor.get_current_editor().filename,
            str(test_file2))

    else:
        # Stay at the same place
        with qtbot.waitSignal(shell.executed):
            qtbot.keyClicks(control, '!a')
            qtbot.keyClick(control, Qt.Key_Enter)
        qtbot.wait(1000)

        # Make sure we didn't move
        assert osp.samefile(
            main_window.editor.get_current_editor().filename,
            str(test_file))


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="Fails sometimes on macOS")
def test_runcell_after_restart(main_window, qtbot):
    """Test runcell after a kernel restart."""
    # Write code to a file
    code = "print('test_runcell_after_restart')"
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)

    # Restart Kernel
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=10000):
        shell.ipyclient.restart_kernel()

    # call runcell
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(
        lambda: "test_runcell_after_restart" in shell._control.toPlainText())

    # Make sure no errors are shown
    assert "error" not in shell._control.toPlainText().lower()


@flaky(max_runs=3)
@pytest.mark.skipif(
    not os.name == 'nt',
    reason="Sometimes fails on Linux and hangs on Mac")
@pytest.mark.parametrize("ipython", [True, False])
@pytest.mark.parametrize("test_cell_magic", [True, False])
def test_ipython_magic(main_window, qtbot, tmpdir, ipython, test_cell_magic):
    """Test the runcell command with cell magic."""
    # Write code with a cell to a file
    write_file = tmpdir.mkdir("foo").join("bar.txt")
    assert not osp.exists(to_text_string(write_file))
    if test_cell_magic:
        code = "\n\n%%writefile " + to_text_string(write_file) + "\ntest\n"
    else:
        code = "\n\n%debug print()"
    if ipython:
        fn = "cell-test.ipy"
    else:
        fn = "cell-test.py"
    p = tmpdir.join(fn)
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Execute runcell
    with qtbot.waitSignal(shell.executed):
        shell.execute("runcell(0, r'{}')".format(to_text_string(p)))
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    error_text = 'save this file with the .ipy extension'
    try:
        if ipython:
            if test_cell_magic:
                qtbot.waitUntil(
                    lambda: 'Writing' in control.toPlainText())

                # Verify that the code was executed
                assert osp.exists(to_text_string(write_file))
            else:
                qtbot.waitSignal(shell.executed)
            assert error_text not in control.toPlainText()
        else:
            qtbot.waitUntil(lambda: error_text in control.toPlainText())
    finally:
        if osp.exists(to_text_string(write_file)):
            os.remove(to_text_string(write_file))


@flaky(max_runs=3)
def test_running_namespace(main_window, qtbot, tmpdir):
    """
    Test that the running namespace is correctly sent when debugging in a
    new namespace.
    """
    code = ("def test(a):\n    print('a:',a)\na = 10\ntest(5)")

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)
    code_editor.debugger.toogle_breakpoint(line_number=2)

    # Write b in the namespace
    with qtbot.waitSignal(shell.executed):
        shell.execute('b = 10')

    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: 'b' in nsb.editor.source_model._data)
    assert nsb.editor.source_model._data['b']['view'] == '10'

    # Start debugging
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # b should not be there (running namespace) and the local a should be 5
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data and
                    nsb.editor.source_model._data['a']['view'] == '5',
                    timeout=3000)
    assert 'b' not in nsb.editor.source_model._data
    assert nsb.editor.source_model._data['a']['view'] == '5'
    qtbot.waitUntil(shell.is_waiting_pdb_input)
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute('!c')

    # At the end, b should be back and a should be 10
    qtbot.waitUntil(lambda: 'b' in nsb.editor.source_model._data)
    assert nsb.editor.source_model._data['a']['view'] == '10'
    assert nsb.editor.source_model._data['b']['view'] == '10'


@flaky(max_runs=3)
def test_running_namespace_refresh(main_window, qtbot, tmpdir):
    """
    Test that the running namespace can be accessed recursively
    """
    code_i = (
        'import time\n'
        'for i in range(10):\n'
        '    time.sleep(.1)\n')
    code_j = (
        'import time\n'
        'for j in range(10):\n'
        '    time.sleep(.1)\n')

    # write code
    file1 = tmpdir.join('file1.py')
    file1.write(code_i)
    file2 = tmpdir.join('file2.py')
    file2.write(code_j)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    shell.execute(
        "runfile(" + repr(str(file2)) + ")"
    )

    # Check nothing is in the variableexplorer
    nsb = main_window.variableexplorer.current_widget()
    assert len(nsb.editor.source_model._data) == 0

    # Wait a bit, refresh, and make sure we captured an in-between value
    qtbot.wait(500)
    nsb.refresh_table()
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 1)
    assert 0 < int(nsb.editor.source_model._data['j']['view']) <= 9

    qtbot.waitSignal(shell.executed)

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "del j"
        )
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 0)

    # Run file inside a debugger
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "debugfile(" + repr(str(file1)) + ")"
        )

    # continue
    shell.execute("c")
    qtbot.wait(500)
    nsb.refresh_table()
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 1)
    assert 0 < int(nsb.editor.source_model._data['i']['view']) <= 9


@flaky(max_runs=3)
def test_debug_namespace(main_window, qtbot, tmpdir):
    """
    Test that the running namespace is correctly sent when debugging

    Regression test for spyder-ide/spyder-kernels#394.
    """
    code1 = (
        'file1_global_ns = True\n'
        'def f(file1_local_ns = True):\n'
        '    return\n')
    code2 = (
        'from file1 import f\n'
        'file2_global_ns = True\n'
        'f()\n')

    # write code
    file1 = tmpdir.join('file1.py')
    file1.write(code1)
    file2 = tmpdir.join('file2.py')
    file2.write(code2)

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "debugfile(" +
            repr(str(file2)) +
            ", wdir=" +
            repr(str(tmpdir)) +
            ")"
        )

    # Check nothing is in the variableexplorer
    nsb = main_window.variableexplorer.current_widget()
    assert len(nsb.editor.source_model._data) == 0

    # advance in file
    with qtbot.waitSignal(shell.executed):
        shell.execute("n")
    with qtbot.waitSignal(shell.executed):
        shell.execute("n")

    # check namespace
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 1)
    assert 'file2_global_ns' in nsb.editor.source_model._data

    # go to file 1
    with qtbot.waitSignal(shell.executed):
        shell.execute("s")

    # check namespace
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 2)
    assert 'file2_global_ns' not in nsb.editor.source_model._data
    assert 'file1_global_ns' in nsb.editor.source_model._data
    assert 'file1_local_ns' in nsb.editor.source_model._data


@flaky(max_runs=3)
def test_post_mortem(main_window, qtbot, tmpdir):
    """Test post mortem works"""
    # Check we can use custom complete for pdb
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    test_file = tmpdir.join('test.py')
    test_file.write('raise RuntimeError\n')

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "runfile(" + repr(str(test_file)) + ", post_mortem=True)")

    assert "IPdb [" in control.toPlainText()


@flaky(max_runs=3)
def test_run_unsaved_file_multiprocessing(main_window, qtbot):
    """Test that we can run an unsaved file with multiprocessing."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    if sys.platform == 'darwin':
        # Since Python 3.8 MacOS uses by default `spawn` instead of `fork`
        # and that causes problems.
        # See https://stackoverflow.com/a/65666298/15954282
        text = ("import multiprocessing\n"
                'multiprocessing.set_start_method("fork")\n'
                "import traceback\n"
                'if __name__ == "__main__":\n'
                "    p = multiprocessing.Process(target=traceback.print_exc)\n"
                "    p.start()\n"
                "    p.join()\n")
    else:
        text = ("import multiprocessing\n"
                "import traceback\n"
                'if __name__ == "__main__":\n'
                "    p = multiprocessing.Process(target=traceback.print_exc)\n"
                "    p.start()\n"
                "    p.join()\n")
    code_editor.set_text(text)
    # This code should run even on windows

    # Start running
    qtbot.mouseClick(run_button, Qt.LeftButton)

    # Because multiprocessing is behaving strangly on windows, only some
    # situations will work. This is one of these situations so it shouldn't
    # be broken.
    if os.name == 'nt':
        qtbot.waitUntil(
            lambda: "Warning: multiprocessing" in shell._control.toPlainText(),
            timeout=SHELL_TIMEOUT)
    else:
        # There is no exception, so the exception is None
        qtbot.waitUntil(
            lambda: 'None' in shell._control.toPlainText(),
            timeout=SHELL_TIMEOUT)


@flaky(max_runs=3)
def test_varexp_cleared_after_kernel_restart(main_window, qtbot):
    """
    Test that the variable explorer is cleared after a kernel restart.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create a variable
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert the value is shown in the variable explorer
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data,
                    timeout=3000)

    # Restart Kernel
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=10000):
        shell.ipyclient.restart_kernel()

    # Assert the value was removed
    qtbot.waitUntil(lambda: 'a' not in nsb.editor.source_model._data,
                    timeout=3000)


@flaky(max_runs=3)
def test_varexp_cleared_after_reset(main_window, qtbot):
    """
    Test that the variable explorer is cleared after triggering a
    reset in the IPython console and variable explorer panes.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create a variable
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert the value is shown in the variable explorer
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data,
                    timeout=3000)

    # Trigger a reset in the variable explorer
    nsb.reset_namespace()

    # Assert the value was removed
    qtbot.waitUntil(lambda: 'a' not in nsb.editor.source_model._data,
                    timeout=3000)

    # Create the variable again
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert the value is shown in the variable explorer
    nsb = main_window.variableexplorer.current_widget()
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data,
                    timeout=3000)

    # Trigger a reset in the console
    shell.ipyclient.reset_namespace()

    # Assert the value was removed
    qtbot.waitUntil(lambda: 'a' not in nsb.editor.source_model._data,
                    timeout=3000)


@flaky(max_runs=3)
def test_immediate_debug(main_window, qtbot):
    """
    Check if we can enter debugging immediately
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
        shell.execute("%debug print()")


@flaky(max_runs=3)
def test_local_namespace(main_window, qtbot, tmpdir):
    """
    Test that the local namespace is not reset.

    This can happen if `frame.f_locals` is called on the current frame, as this
    has the side effect of discarding the pdb locals.
    """
    code = ("""
def hello():
    test = 1
    print('test ==', test)
hello()
""")

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)
    code_editor.debugger.toogle_breakpoint(line_number=4)

    nsb = main_window.variableexplorer.current_widget()

    # Start debugging
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Check `test` has a value of 1
    # Here we use "waitUntil" because `shell.executed` is emitted twice
    # One at the beginning of the file, and once at the breakpoint
    qtbot.waitUntil(lambda: 'test' in nsb.editor.source_model._data and
                    nsb.editor.source_model._data['test']['view'] == '1',
                    timeout=3000)

    # change value of test
    with qtbot.waitSignal(shell.executed):
        shell.execute("test = 1 + 1")

    # check value of test
    with qtbot.waitSignal(shell.executed):
        shell.execute("print('test =', test)")

    qtbot.waitUntil(lambda: "test = 2" in shell._control.toPlainText(),
                    timeout=SHELL_TIMEOUT)
    assert "test = 2" in shell._control.toPlainText()

    # change value of test
    with qtbot.waitSignal(shell.executed):
        shell.execute("test = 1 + 1 + 1")

    # do next
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!next")

    qtbot.waitUntil(lambda: "test == 3" in shell._control.toPlainText(),
                    timeout=SHELL_TIMEOUT)
    assert "test == 3" in shell._control.toPlainText()

    # Check the namespace browser is updated
    assert ('test' in nsb.editor.source_model._data and
            nsb.editor.source_model._data['test']['view'] == '3')


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.preload_project
@pytest.mark.skipif(os.name == 'nt', reason='Times out on Windows')
@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="Too flaky with Linux on CI")
@pytest.mark.known_leak
@pytest.mark.close_main_window
def test_ordering_lsp_requests_at_startup(main_window, qtbot):
    """
    Test the ordering of requests we send to the LSP at startup when a
    project was left open during the previous session.

    This is a regression test for spyder-ide/spyder#13351.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Wait until the LSP server is up.
    code_editor = main_window.editor.get_current_editor()
    qtbot.waitSignal(code_editor.completions_response_signal, timeout=30000)

    # Wait until the initial requests are sent to the server.
    lsp = main_window.completions.get_provider('lsp')
    python_client = lsp.clients['python']
    qtbot.wait(5000)

    expected_requests = [
        'initialize',
        'initialized',
        'workspace/didChangeConfiguration',
        'workspace/didChangeWorkspaceFolders',
        'textDocument/didOpen',
    ]

    skip_intermediate = {
        'initialized': {'workspace/didChangeConfiguration'}
    }

    lsp_requests = python_client['instance']._requests
    start_idx = lsp_requests.index((0, 'initialize'))

    request_order = []
    expected_iter = iter(expected_requests)
    current_expected = next(expected_iter)
    for i in range(start_idx, len(lsp_requests)):
        if current_expected is None:
            break

        _, req_type = lsp_requests[i]
        if req_type == current_expected:
            request_order.append(req_type)
            current_expected = next(expected_iter, None)
        else:
            skip_set = skip_intermediate.get(current_expected, set({}))
            if req_type in skip_set:
                continue
            else:
                assert req_type == current_expected

    assert request_order == expected_requests


@flaky(max_runs=3)
@pytest.mark.parametrize(
    'main_window',
    [{'spy_config': ('tours', 'show_tour_message', True)}],
    indirect=True)
def test_tour_message(main_window, qtbot):
    """Test that the tour message displays and sends users to the tour."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Wait until window setup is finished, which is when the message appears
    tours = main_window.get_plugin(Plugins.Tours)
    tour_dialog = tours.get_container()._tour_dialog
    animated_tour = tours.get_container()._tour_widget
    qtbot.waitSignal(main_window.sig_setup_finished, timeout=30000)

    # Check that tour is shown automatically and manually show it
    assert tours.get_conf('show_tour_message')
    tours.show_tour_message(force=True)

    # Wait for the message to appear
    qtbot.waitUntil(lambda: bool(tour_dialog), timeout=5000)
    qtbot.waitUntil(lambda: tour_dialog.isVisible(), timeout=2000)

    # Check that clicking dismiss hides the dialog and disables it
    qtbot.mouseClick(tour_dialog.dismiss_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not tour_dialog.isVisible(),
                    timeout=2000)
    assert not tours.get_conf('show_tour_message')

    # Confirm that calling show_tour_message() normally doesn't show it again
    tours.show_tour_message()
    qtbot.wait(2000)
    assert not tour_dialog.isVisible()

    # Ensure that it opens again with force=True
    tours.show_tour_message(force=True)
    qtbot.waitUntil(lambda: tour_dialog.isVisible(), timeout=5000)

    # Run the tour and confirm it's running and the dialog is closed
    qtbot.mouseClick(tour_dialog.launch_tour_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: animated_tour.is_running, timeout=9000)
    assert not tour_dialog.isVisible()
    assert not tours.get_conf('show_tour_message')

    # Close the tour
    animated_tour.close_tour()
    qtbot.waitUntil(lambda: not animated_tour.is_running, timeout=9000)


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.preload_complex_project
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only works on Linux")
@pytest.mark.known_leak
def test_update_outline(main_window, qtbot, tmpdir):
    """
    Test that files in the Outline pane are updated at startup and
    after switching projects.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Helper functions
    def editors_filled(treewidget):
        editors_py = [
            editor for editor in treewidget.editor_ids.keys()
            if editor.get_language() == 'Python'
        ]

        return all(
            [
                treewidget.editor_items[editor.get_id()].node.childCount() == 2
                for editor in editors_py
            ]
        )

    def editors_with_info(treewidget):
        editors_py = [
            editor for editor in treewidget.editor_ids.keys()
            if editor.get_language() == 'Python'
        ]

        return all([editor.info is not None for editor in editors_py])

    # Show outline explorer
    outline_explorer = main_window.outlineexplorer
    outline_explorer.toggle_view_action.setChecked(True)

    # Get Python editor trees
    treewidget = outline_explorer.get_widget().treewidget

    # Wait for trees to be filled
    qtbot.waitUntil(lambda: editors_filled(treewidget), timeout=25000)

    # Split editor
    editorstack_1 = main_window.editor.get_current_editorstack()
    editorstack_1.sig_split_vertically.emit()
    qtbot.wait(1000)

    # Check all editors have symbols info after the split
    qtbot.waitUntil(lambda: editors_with_info(treewidget), timeout=25000)

    # Select file with no outline in split editorstack
    editorstack_2 = main_window.editor.get_current_editorstack()
    editorstack_2.set_stack_index(2)
    editor_1 = editorstack_2.get_current_editor()
    assert osp.splitext(editor_1.filename)[1] == '.txt'
    assert editor_1.is_cloned

    # Assert tree is empty
    editor_tree = treewidget.current_editor
    tree = treewidget.editor_tree_cache[editor_tree.get_id()]
    assert len(tree) == 0

    # Assert spinner is not shown
    assert not outline_explorer.get_widget()._spinner.isSpinning()

    # Select a random cloned Python file and check that symbols for it are
    # displayed in the Outline
    idx = random.choice(range(3, editorstack_2.tabs.count()))
    editorstack_2.set_stack_index(idx)
    qtbot.wait(500)
    root_1 = treewidget.editor_items[treewidget.current_editor.get_id()]
    assert root_1.node.childCount() == 2

    # Check that class/function selector of cloned editor is populated
    editorstack_1.set_stack_index(idx)
    editor_1 = editorstack_1.get_current_editor()
    editor_2 = editorstack_2.get_current_editor()
    assert editor_2.is_cloned
    # one class + "<None>" entry
    assert editor_2.classfuncdropdown.class_cb.count() == 2
    # one function + two methods + "<None>" entry
    assert editor_2.classfuncdropdown.method_cb.count() == 4
    assert editor_1.classfuncdropdown._data == editor_2.classfuncdropdown._data

    def get_cb_list(cb):
        return [cb.itemText(i) for i in range(cb.count())]
    assert get_cb_list(editor_1.classfuncdropdown.class_cb) == \
           get_cb_list(editor_2.classfuncdropdown.class_cb)
    assert get_cb_list(editor_1.classfuncdropdown.method_cb) == \
           get_cb_list(editor_2.classfuncdropdown.method_cb)

    # Check that class/function selector of cloned editor is updated
    with qtbot.waitSignal(editor_2.oe_proxy.sig_outline_explorer_data_changed,
                          timeout=5000):
        editor_2.set_text('def baz(x):\n    return x')
    assert editor_2.is_cloned
    # "<None>" entry
    assert editor_2.classfuncdropdown.class_cb.count() == 1
    # one function + "<None>" entry
    assert editor_2.classfuncdropdown.method_cb.count() == 2
    assert editor_1.classfuncdropdown._data == editor_2.classfuncdropdown._data
    assert get_cb_list(editor_1.classfuncdropdown.class_cb) == \
           get_cb_list(editor_2.classfuncdropdown.class_cb)
    assert get_cb_list(editor_1.classfuncdropdown.method_cb) == \
           get_cb_list(editor_2.classfuncdropdown.method_cb)

    # Hide outline from view
    outline_explorer.toggle_view_action.setChecked(False)

    # Remove content from first file and assert outline was not updated
    editorstack_2.set_stack_index(0)
    editor_2 = editorstack_2.get_current_editor()
    with qtbot.waitSignal(editor_2.oe_proxy.sig_outline_explorer_data_changed,
                          timeout=5000):
        editor_2.selectAll()
        editor_2.cut()
        editorstack_2.save()
    len(treewidget.editor_tree_cache[treewidget.current_editor.get_id()]) == 4

    # Set some files as session without projects
    prev_filenames = ["prev_file_1.py", "prev_file_2.py"]
    prev_paths = []
    for fname in prev_filenames:
        file = tmpdir.join(fname)
        file.write(read_asset_file("script_outline_1.py"))
        prev_paths.append(str(file))

    CONF.set('editor', 'filenames', prev_paths)

    # Close project to open that file automatically
    main_window.projects.close_project()

    # Show outline again
    outline_explorer.toggle_view_action.setChecked(True)

    # Wait a bit for trees to be filled
    qtbot.waitUntil(lambda: editors_filled(treewidget), timeout=25000)

    # Create editor window and check Outline editors there have symbols info
    editorwindow = main_window.editor.create_new_window()
    treewidget_on_window = editorwindow.editorwidget.outlineexplorer.treewidget
    qtbot.waitUntil(lambda: editors_with_info(treewidget_on_window),
                    timeout=25000)

    # Go to main window, modify content in file which is hidden on the editor
    # one, move to that window and check its outline is updated after giving
    # focus to it
    main_window.activateWindow()
    editorstack_2.set_stack_index(1)
    editor_3 = editorstack_2.get_current_editor()
    with qtbot.waitSignal(editor_3.oe_proxy.sig_outline_explorer_data_changed,
                          timeout=5000):
        editor_3.set_text('def baz(x):\n    return x')

    editorwindow.activateWindow()
    editorstack_on_window = editorwindow.editorwidget.editorstacks[0]
    editorstack_on_window.set_stack_index(1)
    qtbot.wait(500)
    root_2 = treewidget_on_window.editor_items[
        treewidget_on_window.current_editor.get_id()
    ]
    qtbot.wait(500)
    assert root_2.node.childCount() == 1

    # Remove test files from session
    CONF.set('editor', 'filenames', [])


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(3)
@pytest.mark.preload_namespace_project
@pytest.mark.known_leak
@pytest.mark.skipif(sys.platform == 'darwin', reason="Doesn't work on Mac")
def test_no_update_outline(main_window, qtbot, tmpdir):
    """
    Test the Outline is not updated in different scenarios.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Main variables
    outline_explorer = main_window.outlineexplorer
    treewidget = outline_explorer.get_widget().treewidget
    editor_stack = main_window.editor.get_current_editorstack()

    # Hide the outline explorer just in case
    outline_explorer.toggle_view_action.setChecked(False)

    # Helper functions
    def trees_update_state(treewidget):
        proxy_editors = treewidget.editor_ids.keys()
        return [pe.is_tree_updated for pe in proxy_editors]

    def write_code(code, treewidget):
        proxy_editors = treewidget.editor_ids.keys()
        for i, pe in enumerate(proxy_editors):
            code_editor = pe._editor
            with qtbot.waitSignal(pe.sig_outline_explorer_data_changed,
                                  timeout=5000):
                editor_stack.tabs.setCurrentIndex(i)
                qtbot.mouseClick(editor_stack.tabs.currentWidget(),
                                 Qt.LeftButton)
                code_editor.set_text(code.format(i=i))
                qtbot.wait(300)  # Make changes visible

    def check_symbols_number(number, treewidget):
        proxy_editors = treewidget.editor_ids.keys()
        assert all(
            [len(treewidget.editor_tree_cache[pe.get_id()]) == number
             for pe in proxy_editors]
        )

    def editors_with_info(treewidget):
        editors = treewidget.editor_ids.keys()
        return all([editor.info is not None for editor in editors])

    def move_across_tabs(editorstack):
        for i in range(editorstack.tabs.count()):
            editorstack.tabs.setCurrentIndex(i)
            qtbot.mouseClick(editorstack.tabs.currentWidget(), Qt.LeftButton)
            qtbot.wait(300)  # Make changes visible

    # Wait until symbol services are up
    qtbot.waitUntil(lambda: not treewidget.starting.get('python', True),
                    timeout=10000)

    # Trees shouldn't be updated at startup
    assert not any(trees_update_state(treewidget))

    # Write some code to the current files
    write_code("def foo{i}(x):\n    return x", treewidget)

    # Trees shouldn't be updated after new symbols arrive
    assert not any(trees_update_state(treewidget))

    # Make outline visible
    outline_explorer.toggle_view_action.setChecked(True)

    # Trees should be filled now
    qtbot.waitUntil(lambda: all(trees_update_state(treewidget)))
    check_symbols_number(1, treewidget)

    # Undock Outline
    outline_explorer.create_window()

    # Change code in files.
    # NOTE: By necessity users need to make the main window active to perform
    # these actions. So we need to emulate that (else the test below throws an
    # error).
    main_window.activateWindow()
    write_code("def bar{i}(y):\n    return y\n\ndef baz{i}(z):\n    return z",
               treewidget)

    # Assert trees are updated. This is a regression for issue
    # spyder-ide/spyder#16634
    check_symbols_number(2, treewidget)

    # Minimize undocked window and change code
    outline_explorer.get_widget().windowwidget.showMinimized()
    write_code("def func{i}(x):\n    return x", treewidget)

    # Trees shouldn't be updated in this case
    assert not any(trees_update_state(treewidget))

    # Restore undocked window to normal state
    outline_explorer.get_widget().windowwidget.showNormal()

    # The trees should be updated now with the new code
    qtbot.waitUntil(lambda: all(trees_update_state(treewidget)))
    check_symbols_number(1, treewidget)

    # Hide outline from view
    outline_explorer.toggle_view_action.setChecked(False)
    assert outline_explorer.get_widget().windowwidget is None

    # Change code again and save it to emulate what users need to do to close
    # the current project during the next step.
    write_code("def blah{i}(x):\n    return x", treewidget)
    editor_stack.save_all()
    assert not any(trees_update_state(treewidget))

    # Create editor window and wait until its trees are updated
    editorwindow = main_window.editor.create_new_window()
    editorwidget = editorwindow.editorwidget
    treewidget_on_window = editorwidget.outlineexplorer.treewidget
    qtbot.waitUntil(lambda: editors_with_info(treewidget_on_window),
                    timeout=5000)

    # Minimize editor window and change code in main window
    editorwindow.showMinimized()
    main_window.activateWindow()
    write_code("def bar{i}(y):\n    return y\n\ndef baz{i}(z):\n    return z",
               treewidget)

    # Assert trees are not updated on editor window.
    assert not any(trees_update_state(treewidget_on_window))

    # Restore editor window, move across its tabs and check symbols are updated
    editorwindow.showNormal()
    editorwindow.activateWindow()
    editorstack_on_window = editorwidget.editorstacks[0]
    move_across_tabs(editorstack_on_window)

    qtbot.waitUntil(lambda: all(trees_update_state(treewidget_on_window)))
    check_symbols_number(2, treewidget_on_window)

    # Hide Outline on editor window, update code for files on it and check
    # trees are not updated
    splitter_on_window = editorwidget.splitter
    split_sizes = splitter_on_window.sizes()
    splitter_on_window.moveSplitter(editorwidget.size().width(), 0)
    write_code("def blah{i}(x):\n    return x", treewidget_on_window)

    assert not any(trees_update_state(treewidget_on_window))

    # Show Outline on editor window, move across its tabs and check symbols
    # are updated
    splitter_on_window.moveSplitter(split_sizes[0], 1)
    move_across_tabs(editorstack_on_window)

    qtbot.waitUntil(lambda: all(trees_update_state(treewidget_on_window)))
    check_symbols_number(1, treewidget_on_window)

    # Show Outline, minimize main window and change code in editor window
    outline_explorer.toggle_view_action.setChecked(True)
    main_window.showMinimized()
    editorwindow.activateWindow()
    write_code("def bar{i}(y):\n    return y\n\ndef baz{i}(z):\n    return z",
               treewidget_on_window)

    qtbot.waitUntil(lambda: editors_with_info(treewidget_on_window),
                    timeout=5000)

    # Check Outline on main window was not updated
    assert not any(trees_update_state(treewidget))

    # Restore main window and check Outline is updated
    main_window.showNormal()
    main_window.showMaximized()
    qtbot.waitUntil(lambda: all(trees_update_state(treewidget)))
    check_symbols_number(2, treewidget)

    # Hide Outline and close editor window
    outline_explorer.toggle_view_action.setChecked(False)
    editorwindow.close()
    qtbot.wait(1000)

    # Show Outline and close project immediately. This checks that no errors
    # are generated after doing that.
    outline_explorer.toggle_view_action.setChecked(True)
    main_window.projects.close_project()


@flaky(max_runs=3)
def test_prevent_closing(main_window, qtbot):
    """
    Check we can bypass prevent closing.
    """
    code = "print(1 + 6)\nprint(1 + 6)\n"

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)
    code_editor.debugger.toogle_breakpoint(line_number=1)

    # Start debugging
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)

    CONF.set('ipython_console', 'pdb_prevent_closing', False)
    # Check we can close a file we debug if the option is disabled
    assert main_window.editor.get_current_editorstack().close_file()
    CONF.set('ipython_console', 'pdb_prevent_closing', True)
    # Check we are still debugging
    assert shell.is_debugging()


@flaky(max_runs=3)
def test_continue_first_line(main_window, qtbot):
    """
    Check we can bypass prevent closing.
    """
    code = "print('a =', 1 + 6)\nprint('b =', 1 + 8)\n"

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Main variables
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)

    CONF.set('ipython_console', 'pdb_stop_first_line', False)
    # Start debugging
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(debug_button, Qt.LeftButton)
    # The debugging should finish
    qtbot.waitUntil(lambda: not shell.is_debugging())
    CONF.set('ipython_console', 'pdb_stop_first_line', True)

    # Check everything was executed
    qtbot.waitUntil(lambda: "a = 7" in shell._control.toPlainText())
    assert "b = 9" in shell._control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.skipif(os.name == 'nt', reason="Fails on Windows")
def test_outline_no_init(main_window, qtbot):
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Open file in one of our directories without an __init__ file
    spy_dir = osp.dirname(get_module_path('spyder'))
    main_window.editor.load(osp.join(spy_dir, 'tools', 'rm_whitespace.py'))

    # Show outline explorer
    outline_explorer = main_window.outlineexplorer
    outline_explorer.toggle_view_action.setChecked(True)

    # Wait a bit for trees to be filled
    qtbot.wait(5000)

    # Get tree length
    treewidget = outline_explorer.get_widget().treewidget
    editor_id = list(treewidget.editor_ids.values())[1]

    # Assert symbols in the file are detected and shown
    assert len(treewidget.editor_tree_cache[editor_id]) > 0


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="Flaky on Linux")
def test_pdb_without_comm(main_window, qtbot):
    """Check if pdb works without comm."""
    ipyconsole = main_window.ipyconsole
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("get_ipython().kernel.frontend_comm.close()")
    shell.execute("%debug print()")
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')
    qtbot.keyClicks(control, "print('Two: ' + str(1+1))")
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    assert "Two: 2" in control.toPlainText()

    # Press step button and expect a sig_pdb_step signal
    with qtbot.waitSignal(shell.sig_pdb_step):
        main_window.editor.debug_command("step")

    # Stop debugging and expect an executed signal
    with qtbot.waitSignal(shell.executed):
        main_window.editor.stop_debugging()


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Flaky on Mac and Windows")
def test_print_comms(main_window, qtbot):
    """Test warning printed when comms print."""
    # Write code with a cell to a file
    code = ("class Test:\n    @property\n    def shape(self):"
            "\n        print((10,))")
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    nsb = main_window.variableexplorer.current_widget()

    # Create some output from spyder call
    with qtbot.waitSignal(shell.executed):
        shell.execute(code)

    assert nsb.editor.source_model.rowCount() == 0

    with qtbot.waitSignal(shell.executed):
        shell.execute("a = Test()")

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 1,
                    timeout=EVAL_TIMEOUT)

    # Make sure the warning is printed
    assert ("Output from spyder call 'get_namespace_view':"
            in control.toPlainText())


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="UTF8 on Windows")
def test_goto_find(main_window, qtbot, tmpdir):
    """Test find goes to the right place."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Use UTF8 only character to make sure positions are respected
    code = "we Weee wee\nWe\n🚫 wee"
    match_positions = [
        (0, 2),
        (3, 7),
        (8, 11),
        (12, 14),
        (18, 21)
    ]
    subdir = tmpdir.mkdir("find-sub")
    p = subdir.join("find-test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    code_editor = main_window.editor.get_focus_widget()

    main_window.explorer.chdir(str(subdir))

    main_window.findinfiles.switch_to_plugin()
    findinfiles = main_window.findinfiles.get_widget()
    findinfiles.set_search_text("we+")
    findinfiles.search_regexp_action.setChecked(True)
    findinfiles.case_action.setChecked(False)
    with qtbot.waitSignal(findinfiles.sig_finished, timeout=SHELL_TIMEOUT):
        findinfiles.find()

    results = findinfiles.result_browser.data
    assert len(results) == 5
    assert len(findinfiles.result_browser.files) == 1

    file_item = list(findinfiles.result_browser.files.values())[0]
    assert file_item.childCount() == 5

    for i in range(5):
        item = file_item.child(i)
        findinfiles.result_browser.setCurrentItem(item)
        findinfiles.result_browser.activated(item)
        cursor = code_editor.textCursor()
        position = (cursor.selectionStart(), cursor.selectionEnd())
        assert position == match_positions[i]


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt',
    reason="test fails on windows.")
def test_copy_paste(main_window, qtbot, tmpdir):
    """Test copy paste."""
    code = (
        "if True:\n"
        "    class a():\n"
        "        def b():\n"
        "            print()\n"
        "        def c():\n"
        "            print()\n"
        )

    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text(code)

    # Test copy
    cursor = code_editor.textCursor()
    cursor.setPosition(69)
    cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)
    qtbot.keyClick(code_editor, "c", modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == (
        "def c():\n            print()\n")
    assert CLIPBOARD_HELPER.metadata_indent == 8

    # Test paste in console
    qtbot.keyClick(shell._control, "v", modifier=Qt.ControlModifier)
    expected = "In [1]: def c():\n   ...:     print()"
    assert expected in shell._control.toPlainText()

    # Test paste at zero indentation
    qtbot.keyClick(code_editor, Qt.Key_Backspace)
    qtbot.keyClick(code_editor, Qt.Key_Backspace)
    qtbot.keyClick(code_editor, Qt.Key_Backspace)
    # Check again that the clipboard is ready
    assert QApplication.clipboard().text() == (
        "def c():\n            print()\n")
    assert CLIPBOARD_HELPER.metadata_indent == 8
    qtbot.keyClick(code_editor, "v", modifier=Qt.ControlModifier)
    assert "\ndef c():\n    print()" in code_editor.toPlainText()

    # Test paste at automatic indentation
    qtbot.keyClick(code_editor, "z", modifier=Qt.ControlModifier)
    qtbot.keyClick(code_editor, Qt.Key_Tab)
    qtbot.keyClick(code_editor, "v", modifier=Qt.ControlModifier)
    expected = (
        "\n"
        "            def c():\n"
        "                print()\n"
        )
    assert expected in code_editor.toPlainText()


@pytest.mark.skipif(not running_in_ci(), reason="Only works in CIs")
def test_add_external_plugins_to_dependencies(main_window, qtbot):
    """Test that we register external plugins in the main window."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    external_names = []
    for dep in DEPENDENCIES:
        name = getattr(dep, 'package_name', None)
        if name:
            external_names.append(name)

    assert 'spyder-boilerplate' in external_names


@flaky(max_runs=3)
def test_print_multiprocessing(main_window, qtbot, tmpdir):
    """Test print commands from multiprocessing."""
    # Write code with a cell to a file
    code = """
import multiprocessing
import sys
def test_func():
    print("Test stdout")
    print("Test stderr", file=sys.stderr)

if __name__ == "__main__":
    p = multiprocessing.Process(target=test_func)
    p.start()
    p.join()
"""

    p = tmpdir.join("print-test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    # Click the run button
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(run_button, Qt.LeftButton)
    qtbot.wait(1000)

    assert 'Test stdout' in control.toPlainText()
    assert 'Test stderr' in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.name == 'nt',
    reason="ctypes.string_at(0) doesn't segfaults on Windows")
def test_print_faulthandler(main_window, qtbot, tmpdir):
    """Test printing segfault info from kernel crashes."""
    # Write code with a cell to a file
    code = """
def crash_func():
    import ctypes; ctypes.string_at(0)
crash_func()
"""

    p = tmpdir.join("print-test.py")
    p.write(code)
    main_window.editor.load(to_text_string(p))
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    # Click the run button
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)
    qtbot.mouseClick(run_button, Qt.LeftButton)

    qtbot.waitUntil(lambda: 'Segmentation fault' in control.toPlainText(),
                    timeout=SHELL_TIMEOUT)
    assert 'Segmentation fault' in control.toPlainText()
    assert 'in crash_func' in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Tour messes up focus on Windows")
@pytest.mark.parametrize("focus_to_editor", [True, False])
def test_focus_to_editor(main_window, qtbot, tmpdir, focus_to_editor):
    """Test that the focus_to_editor option works as expected."""

    def check_focus(button):
        # Give focus back to the editor before running the next test
        if not focus_to_editor:
            code_editor.setFocus()

        # Make sure we don't switch to the console after pressing the button
        if focus_to_editor:
            with qtbot.assertNotEmitted(
                main_window.ipyconsole.sig_switch_to_plugin_requested,
                wait=1000
            ):
                with qtbot.waitSignal(shell.executed):
                    qtbot.mouseClick(button, Qt.LeftButton)
        else:
            with qtbot.waitSignal(shell.executed):
                qtbot.mouseClick(button, Qt.LeftButton)

        # Check the right widget has focus
        focus_widget = QApplication.focusWidget()
        if focus_to_editor:
            assert focus_widget is code_editor
        else:
            assert focus_widget is control

    # Write code with cells to a file
    code = """# %%
def foo(x):
    return 2 * x

# %%
foo(1)
"""
    p = tmpdir.join("test.py")
    p.write(code)

    # Load code in the editor
    main_window.editor.load(to_text_string(p))

    # Change focus_to_editor option
    main_window.editor.set_option('focus_to_editor', focus_to_editor)
    main_window.editor.apply_plugin_settings({'focus_to_editor'})
    code_editor = main_window.editor.get_current_editor()

    # Wait for the console to be up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    # Be sure the focus is on the editor before proceeding
    code_editor.setFocus()
    assert QApplication.focusWidget() is code_editor

    # Run a file
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)
    check_focus(run_button)

    # Run a cell
    run_cell_action = main_window.run_toolbar_actions[1]
    run_cell_button = main_window.run_toolbar.widgetForAction(run_cell_action)
    check_focus(run_cell_button)

    # Move cursor to last line to run it
    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
    cursor.movePosition(QTextCursor.PreviousBlock, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)

    # Run selection
    run_selection_action = main_window.run_toolbar_actions[3]
    run_selection_button = main_window.run_toolbar.widgetForAction(
        run_selection_action)
    check_focus(run_selection_button)

    # Debug a file
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    check_focus(debug_button)

    # Execute another debugging command
    debug_command_action = main_window.debug_toolbar_actions[1]
    debug_command_button = main_window.debug_toolbar.widgetForAction(
        debug_command_action)
    check_focus(debug_command_button)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Tour messes up focus on Windows")
def test_focus_for_plugins_with_raise_and_focus(main_window, qtbot):
    """
    Check that we give focus to the focus widget declared by plugins that use
    the RAISE_AND_FOCUS class constant.
    """
    # Wait for the console to be up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()

    # Show internal console
    console = main_window.get_plugin(Plugins.Console)
    console.toggle_view_action.setChecked(True)

    # Change to the IPython console and assert focus is given to its focus
    # widget
    main_window.ipyconsole.dockwidget.raise_()
    focus_widget = QApplication.focusWidget()
    assert focus_widget is control

    # Change to the Internal console and assert focus is given to its focus
    # widget
    console.dockwidget.raise_()
    focus_widget = QApplication.focusWidget()
    assert focus_widget is console.get_widget().get_focus_widget()

    # Switch to Find and assert focus is given to its focus widget
    find = main_window.get_plugin(Plugins.Find)
    find.toggle_view_action.setChecked(True)
    focus_widget = QApplication.focusWidget()
    assert focus_widget is find.get_widget().get_focus_widget()


@flaky(max_runs=3)
@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason="Hangs sometimes on Windows and Mac")
def test_rename_files_in_editor_after_folder_rename(main_window, mocker,
                                                    tmpdir, qtbot):
    """
    Check that we rename files in the editor after the directory that
    contains them was renamed in Files.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    old_path = 'test_rename_old'
    new_path = 'test_rename_new'
    fname = 'foo.py'

    # Mock output of QInputDialog to set new path after rename
    mocker.patch.object(QInputDialog, 'getText',
                        return_value=(new_path, True))

    # Create temp folder and simple file on it
    file = tmpdir.mkdir(old_path).join(fname)
    file.write("print('Hello world!')")

    # Load file in editor
    editor = main_window.get_plugin(Plugins.Editor)
    editor.load(str(file))

    # Switch to temp dir and give focus to Files
    explorer = main_window.get_plugin(Plugins.Explorer)
    explorer.chdir(str(tmpdir))
    explorer.switch_to_plugin()
    explorer.get_widget().get_focus_widget().setFocus()

    # Select directory in widget
    treewidget = explorer.get_widget().treewidget
    idx = treewidget.get_index(old_path)
    treewidget.setCurrentIndex(idx)

    # Rename directory
    treewidget.rename()

    # Check file was renamed in editor
    codeeditor = editor.get_current_editor()
    assert codeeditor.filename == osp.join(str(tmpdir), new_path, fname)


@flaky(max_runs=3)
def test_history_from_ipyconsole(main_window, qtbot):
    """
    Check that we register commands introduced in the IPython console in
    the History pane.
    """
    # Wait for the console to be up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Run some code in the console
    code = '5 + 3'
    with qtbot.waitSignal(shell.executed):
        shell.execute(code)

    # Check that code is displayed in History
    history = main_window.get_plugin(Plugins.History)
    history.switch_to_plugin()
    history_editor = history.get_widget().editors[0]
    text = history_editor.toPlainText()
    assert text.splitlines()[-1] == code


def test_debug_unsaved_function(main_window, qtbot):
    """
    Test that a breakpoint in an unsaved file is reached.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Main variables
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    run_action = main_window.run_toolbar_actions[0]
    run_button = main_window.run_toolbar.widgetForAction(run_action)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # create new file
    main_window.editor.new()
    code_editor = main_window.editor.get_focus_widget()
    code_editor.set_text('def foo():\n    print(1)')

    # Set breakpoint
    code_editor.debugger.toogle_breakpoint(line_number=2)

    # run file
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(run_button, Qt.LeftButton)

    # debug foo
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug foo()')

    with qtbot.waitSignal(shell.executed):
        shell.execute('continue')

    assert "1---> 2     print(1)" in control.toPlainText()


@flaky(max_runs=5)
@pytest.mark.close_main_window
def test_out_runfile_runcell(main_window, qtbot):
    """
    Test that runcell and runfile return values if last statment
    is expression.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    codes = {
        "a = 1 + 1; a": (2, True),
        "a = 1 + 3; a;": (4, False),
        "a = 1 + 5\na": (6, True),
        "a = 1 + 7\na;": (8, False)
        }
    for code in codes:
        num, shown = codes[code]
        # create new file
        main_window.editor.new()
        code_editor = main_window.editor.get_focus_widget()
        code_editor.set_text(code)
        with qtbot.waitSignal(shell.executed):
            main_window.editor.run_cell()
        if shown:
            assert "]: " + str(num) in control.toPlainText()
        else:
            assert not "]: " + str(num) in control.toPlainText()


def test_visible_plugins(main_window, qtbot):
    """
    Test that saving and restoring visible plugins works as expected.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load default layout
    main_window.layouts.quick_layout_switch(DefaultLayouts.SpyderLayout)

    # Make some non-default plugins visible
    selected = [Plugins.Plots, Plugins.History]
    for plugin_name in selected:
        main_window.get_plugin(plugin_name).dockwidget.raise_()

    # Save visible plugins
    main_window.layouts.save_visible_plugins()

    # Change visible plugins
    for plugin_name in [Plugins.VariableExplorer, Plugins.IPythonConsole]:
        main_window.get_plugin(plugin_name).dockwidget.raise_()

    # Make sure plugins to test are not visible
    for plugin_name in selected:
        assert not main_window.get_plugin(plugin_name).get_widget().is_visible

    # Restore saved visible plugins
    main_window.layouts.restore_visible_plugins()

    # Assert visible plugins are the expected ones
    visible_plugins = []
    for plugin_name, plugin in main_window.get_dockable_plugins():
        if plugin_name != Plugins.Editor and plugin.get_widget().is_visible:
            visible_plugins.append(plugin_name)

    assert set(selected) == set(visible_plugins)


def test_cwd_is_synced_when_switching_consoles(main_window, qtbot, tmpdir):
    """
    Test that the current working directory is synced between the IPython
    console and other plugins when switching consoles.
    """
    ipyconsole = main_window.ipyconsole
    workdir = main_window.workingdirectory
    files = main_window.get_plugin(Plugins.Explorer)

    # Wait for the window to be fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create two new clients and change their cwd's
    for i in range(2):
        sync_dir = tmpdir.mkdir(f'test_sync_{i}')
        ipyconsole.create_new_client()
        shell = ipyconsole.get_current_shellwidget()
        qtbot.waitUntil(lambda: shell._prompt_html is not None,
                        timeout=SHELL_TIMEOUT)
        with qtbot.waitSignal(shell.executed):
            shell.execute(f'cd {str(sync_dir)}')

    # Switch between clients and check that the cwd is in sync with other
    # plugins
    for i in range(3):
        ipyconsole.get_widget().tabwidget.setCurrentIndex(i)
        shell_cwd = ipyconsole.get_current_shellwidget().get_cwd()
        assert shell_cwd == workdir.get_workdir() == files.get_current_folder()


@flaky(max_runs=5)
def test_console_initial_cwd_is_synced(main_window, qtbot, tmpdir):
    """
    Test that the initial current working directory for new consoles is synced
    with other plugins.
    """
    ipyconsole = main_window.ipyconsole
    workdir = main_window.workingdirectory
    files = main_window.get_plugin(Plugins.Explorer)

    # Wait for the window to be fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Open console from Files in tmpdir
    files.get_widget().treewidget.open_interpreter([str(tmpdir)])
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    assert shell.get_cwd() == str(tmpdir) == workdir.get_workdir() == \
           files.get_current_folder()

    # Check that a new client has the same initial cwd as the current one
    ipyconsole.create_new_client()
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    qtbot.wait(500)
    assert shell.get_cwd() == str(tmpdir) == workdir.get_workdir() == \
           files.get_current_folder()

    # Check new clients with a fixed directory
    ipyconsole.set_conf('console/use_cwd', False, section='workingdir')
    ipyconsole.set_conf(
        'console/use_fixed_directory',
        True,
        section='workingdir'
    )

    fixed_dir = str(tmpdir.mkdir('fixed_dir'))
    ipyconsole.set_conf(
        'console/fixed_directory',
        fixed_dir,
        section='workingdir'
    )

    ipyconsole.create_new_client()
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    qtbot.wait(500)
    assert shell.get_cwd() == fixed_dir == workdir.get_workdir() == \
           files.get_current_folder()

    # Check when opening projects
    project_path = str(tmpdir.mkdir('test_project'))
    main_window.projects.open_project(path=project_path)
    qtbot.wait(500)

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    qtbot.wait(500)
    assert shell.get_cwd() == project_path == workdir.get_workdir() == \
           files.get_current_folder()

    # Check when closing projects
    main_window.projects.close_project()
    qtbot.wait(500)

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    qtbot.wait(500)
    assert shell.get_cwd() == get_home_dir() == workdir.get_workdir() == \
           files.get_current_folder()


@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.order(after="test_debug_unsaved_function")
@pytest.mark.preload_namespace_project
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only works on Linux")
@pytest.mark.known_leak
def test_outline_namespace_package(main_window, qtbot, tmpdir):
    """
    Test that we show symbols in the Outline pane for projects that have
    namespace packages, i.e. with no __init__.py file in its root directory.

    This is a regression test for issue spyder-ide/spyder#16406.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Show outline explorer
    outline_explorer = main_window.outlineexplorer
    outline_explorer.toggle_view_action.setChecked(True)

    # Get Python editor trees
    treewidget = outline_explorer.get_widget().treewidget
    editors_py = [
        editor for editor in treewidget.editor_ids.keys()
        if editor.get_language() == 'Python'
    ]

    def editors_filled():
        return all(
            [
                len(treewidget.editor_tree_cache[editor.get_id()]) == 4
                for editor in editors_py
            ]
        )

    # Wait a bit for trees to be filled
    qtbot.waitUntil(editors_filled, timeout=25000)
    assert editors_filled()

    # Remove test file from session
    CONF.set('editor', 'filenames', [])


@pytest.mark.skipif(
    sys.platform == 'darwin',
    reason="Only works on Windows and Linux")
@pytest.mark.order(before='test_tour_message')
def test_switch_to_plugin(main_window, qtbot):
    """
    Test that switching between the two most important plugins, the Editor and
    the IPython console, is working as expected.

    This is a regression test for issue spyder-ide/spyder#19374.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Switch to the IPython console and check the focus is there
    qtbot.keyClick(main_window, Qt.Key_I,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)
    control = main_window.ipyconsole.get_widget().get_focus_widget()
    assert QApplication.focusWidget() is control

    # Switch to the editor and assert the focus is there
    qtbot.keyClick(main_window, Qt.Key_E,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)
    code_editor = main_window.editor.get_current_editor()
    assert QApplication.focusWidget() is code_editor


@flaky(max_runs=5)
def test_PYTHONPATH_in_consoles(main_window, qtbot, tmp_path,
                                restore_user_env):
    """
    Test that PYTHONPATH is passed to IPython consoles under different
    scenarios.
    """
    # Wait until the window is fully up
    ipyconsole = main_window.ipyconsole
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Add a new directory to PYTHONPATH
    new_dir = tmp_path / 'new_dir'
    new_dir.mkdir()
    set_user_env({"PYTHONPATH": str(new_dir)})

    # Open Pythonpath dialog to detect new_dir
    ppm = main_window.get_plugin(Plugins.PythonpathManager)
    ppm.show_path_manager()
    qtbot.wait(500)

    # Check new_dir was added to sys.path after closing the dialog
    ppm.path_manager_dialog.close()
    with qtbot.waitSignal(shell.executed, timeout=2000):
        shell.execute("import sys; sys_path = sys.path")

    assert str(new_dir) in shell.get_value("sys_path")

    # Create new console
    ipyconsole.create_new_client()
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Check new_dir is part of the new console's sys.path
    with qtbot.waitSignal(shell.executed, timeout=2000):
        shell.execute("import sys; sys_path = sys.path")

    assert str(new_dir) in shell.get_value("sys_path")


@flaky(max_runs=10)
def test_clickable_ipython_tracebacks(main_window, qtbot, tmp_path):
    """
    Test that file names in IPython console tracebacks are clickable.

    This is a regression test for issue spyder-ide/spyder#20407.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Copy test file to a temporary location to avoid modifying it.
    # See spyder-ide/spyder#21186 for the details
    test_file_orig = osp.join(LOCATION, 'script.py')
    test_file = str(tmp_path / 'script.py')
    shutil.copyfile(test_file_orig, test_file)
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # Introduce an error at the end of the file. This only works if the last
    # line is empty.
    text = code_editor.toPlainText()
    assert text.splitlines(keepends=True)[-1].endswith('\n')

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
    code_editor.setTextCursor(cursor)
    qtbot.keyClicks(code_editor, '1/0')

    # Run test file
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    # Find last 'File' line in traceback, which corresponds to the file we
    # opened.
    control.setFocus()
    find_widget = main_window.ipyconsole.get_widget().find_widget
    find_widget.show()
    find_widget.search_text.lineEdit().setText('  File')
    find_widget.find_previous()

    # Position mouse on top of that line
    cursor_point = control.cursorRect(control.textCursor()).center()
    qtbot.mouseMove(control, cursor_point)
    qtbot.wait(500)

    # Check cursor shape is the right one
    assert QApplication.overrideCursor().shape() == Qt.PointingHandCursor

    # Click on the line and check that that sends us to the editor
    qtbot.mouseClick(control.viewport(), Qt.LeftButton, pos=cursor_point,
                     delay=300)
    assert QApplication.focusWidget() is code_editor

    # Check we are in the right line
    cursor = code_editor.textCursor()
    assert cursor.blockNumber() == code_editor.blockCount() - 1


if __name__ == "__main__":
    pytest.main()
