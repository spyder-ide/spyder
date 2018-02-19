# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the main window
"""

# Standard library imports
import os
import os.path as osp
import shutil
import tempfile
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock  # Python 2

# Third party imports
from flaky import flaky
from jupyter_client.manager import KernelManager
import numpy as np
from numpy.testing import assert_array_equal
import pytest
from qtpy import PYQT4, PYQT5, PYQT_VERSION
from qtpy.QtCore import Qt, QTimer, QEvent, QUrl
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QFileDialog, QLineEdit, QTabBar

# Local imports
from spyder import __trouble_url__, __project_url__
from spyder.app import start
from spyder.app.mainwindow import MainWindow  # Tests fail without this import
from spyder.config.base import get_home_dir
from spyder.config.main import CONF
from spyder.plugins import TabFilter
from spyder.plugins.help import ObjectComboBox
from spyder.plugins.runconfig import RunConfiguration
from spyder.py3compat import PY2, to_text_string
from spyder.utils.ipython.kernelspec import SpyderKernelSpec
from spyder.utils.programs import is_module_installed

# For testing various Spyder urls
if not PY2:
    from urllib.request import urlopen
    from urllib.error import URLError
else:
    from urllib2 import urlopen, URLError


# =============================================================================
# Constants
# =============================================================================
# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))

# Time to wait until the IPython console is ready to receive input
# (in miliseconds)
SHELL_TIMEOUT = 20000

# Need longer EVAL_TIMEOUT, because need to cythonize and C compile ".pyx" file
# before import and eval it
COMPILE_AND_EVAL_TIMEOUT = 30000

# Time to wait for the IPython console to evaluate something (in
# miliseconds)
EVAL_TIMEOUT = 3000

# Temporary directory
TEMP_DIRECTORY = tempfile.gettempdir()


# =============================================================================
# Utility functions
# =============================================================================
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


def get_thirdparty_plugin(main_window, plugin_title):
    """Get a reference to the thirdparty plugin with the title given."""
    for plugin in main_window.thirdparty_plugins:
        if plugin.get_plugin_title() == plugin_title:
            return plugin


def reset_run_code(qtbot, shell, code_editor, nsb):
    """Reset state after a run code test"""
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=EVAL_TIMEOUT)
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)


def start_new_kernel(startup_timeout=60, kernel_name='python', spykernel=False,
                     **kwargs):
    """Start a new kernel, and return its Manager and Client"""
    km = KernelManager(kernel_name=kernel_name)
    if spykernel:
        km._kernel_spec = SpyderKernelSpec()
    km.start_kernel(**kwargs)
    kc = km.client()
    kc.start_channels()
    try:
        kc.wait_for_ready(timeout=startup_timeout)
    except RuntimeError:
        kc.stop_channels()
        km.shutdown_kernel()
        raise

    return km, kc


def find_desired_tab_in_window(tab_name, window):
    all_tabbars = window.findChildren(QTabBar)
    for current_tabbar in all_tabbars:
        for tab_index in range(current_tabbar.count()):
            if current_tabbar.tabText(tab_index) == str(tab_name):
                return current_tabbar, tab_index
    return None, None


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def main_window(request):
    """Main Window fixture"""
    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 0)

    # Check if we need to use introspection in a given test
    # (it's faster and less memory consuming not to use it!)
    use_introspection = request.node.get_marker('use_introspection')
    if use_introspection:
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    else:
        try:
            os.environ.pop('SPY_TEST_USE_INTROSPECTION')
        except KeyError:
            pass

    # Only use single_instance mode for tests that require it
    single_instance = request.node.get_marker('single_instance')
    if single_instance:
        CONF.set('main', 'single_instance', True)
    else:
        CONF.set('main', 'single_instance', False)

    # Start the window
    window = start.main()

    # Teardown
    def close_window():
        window.close()
    request.addfinalizer(close_window)

    return window


# =============================================================================
# Tests
# =============================================================================
# IMPORTANT NOTE: Please leave this test to be the first one here to
# avoid possible timeouts in Appveyor
@pytest.mark.slow
@pytest.mark.use_introspection
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or not PY2,
                    reason="Times out on AppVeyor and fails on PY3/PyQt 5.6")
@pytest.mark.timeout(timeout=45, method='thread')
def test_calltip(main_window, qtbot):
    """Test that the calltip in editor is hidden when matching ')' is found."""
    # Load test file
    text = 'a = [1,2,3]\n(max'
    main_window.editor.new(fname="test.py", text=text)
    code_editor = main_window.editor.get_focus_widget()

    # Set text to start
    code_editor.set_text(text)
    code_editor.go_to_line(2)
    code_editor.move_cursor(5)
    calltip = code_editor.calltip_widget
    assert not calltip.isVisible()

    qtbot.keyPress(code_editor, Qt.Key_ParenLeft, delay=3000)
    qtbot.keyPress(code_editor, Qt.Key_A, delay=1000)
    qtbot.waitUntil(lambda: calltip.isVisible(), timeout=3000)

    qtbot.keyPress(code_editor, Qt.Key_ParenRight, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Space)
    assert not calltip.isVisible()
    qtbot.keyPress(code_editor, Qt.Key_ParenRight, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    main_window.editor.close_file()


@pytest.mark.slow
def test_window_title(main_window, tmpdir):
    """Test window title with non-ascii characters."""
    projects = main_window.projects

    # Create a project in non-ascii path
    path = to_text_string(tmpdir.mkdir(u'測試'))
    projects.open_project(path=path)

    # Set non-ascii window title
    main_window.window_title = u'اختبار'

    # Assert window title is computed without errors
    # and has the expected strings
    main_window.set_window_title()
    title = main_window.base_title
    assert u'Spyder' in title
    assert u'Python' in title
    assert u'اختبار' in title
    assert u'測試' in title

    projects.close_project()


@pytest.mark.slow
@pytest.mark.single_instance
def test_single_instance_and_edit_magic(main_window, qtbot, tmpdir):
    """Test single instance mode and for %edit magic."""
    editorstack = main_window.editor.get_current_editorstack()
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    lock_code = ("from spyder.config.base import get_conf_path\n"
                 "from spyder.utils.external import lockfile\n"
                 "lock_file = get_conf_path('spyder.lock')\n"
                 "lock = lockfile.FilesystemLock(lock_file)\n"
                 "lock_created = lock.lock()")

    # Test single instance
    with qtbot.waitSignal(shell.executed):
        shell.execute(lock_code)
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or PY2 or PYQT4,
                    reason="It fails sometimes")
def test_move_to_first_breakpoint(main_window, qtbot):
    """Test that we move to the first breakpoint if there's one present."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    code_editor.add_remove_breakpoint(line_number=10)
    qtbot.wait(500)

    # Click the debug button
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Verify that we are at first breakpoint
    shell.clear_console()
    qtbot.wait(500)
    shell.kernel_client.input("list")
    qtbot.wait(500)
    assert "1--> 10 arr = np.array(li)" in control.toPlainText()

    # Exit debugging
    shell.kernel_client.input("exit")
    qtbot.wait(500)

    # Set breakpoint on first line with code
    code_editor.add_remove_breakpoint(line_number=2)
    qtbot.wait(500)

    # Click the debug button
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Verify that we are still on debugging
    assert shell._reading

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason="It's not meant to be run locally")
def test_runconfig_workdir(main_window, qtbot, tmpdir):
    """Test runconfig workdir options."""
    CONF.set('run', 'configurations', [])

    # ---- Load test file ----
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # --- Use cwd for this file ---
    rc = RunConfiguration().get()
    rc['file_dir'] = False
    rc['cw_dir'] = True
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    # --- Run test file ---
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)

    # --- Assert we're in fixed dir after execution ---
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os; current_dir = os.getcwd()')
    assert shell.get_value('current_dir') == temp_dir

    # ---- Closing test file and resetting config ----
    main_window.editor.close_file()
    CONF.set('run', 'configurations', [])


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' and PY2, reason="It's failing there")
def test_dedicated_consoles(main_window, qtbot):
    """Test running code in dedicated consoles."""
    # ---- Load test file ----
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()

    # --- Set run options for this file ---
    rc = RunConfiguration().get()
    # A dedicated console is used when these two options are False
    rc['current'] = rc['systerm'] = False
    config_entry = (test_file, rc)
    CONF.set('run', 'configurations', [config_entry])

    # --- Run test file and assert that we get a dedicated console ---
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    nsb = main_window.variableexplorer.get_focus_widget()

    assert len(main_window.ipyconsole.get_clients()) == 2
    assert main_window.ipyconsole.filenames == ['', test_file]
    assert main_window.ipyconsole.tabwidget.tabText(1) == 'script.py/A'
    qtbot.wait(500)
    assert nsb.editor.model.rowCount() == 3

    # --- Assert only runfile text is present and there's no banner text ---
    # See PR #5301
    text = control.toPlainText()
    assert ('runfile' in text) and not ('Python' in text or 'IPython' in text)

    # --- Clean namespace after re-execution ---
    with qtbot.waitSignal(shell.executed):
        shell.execute('zz = -1')
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.wait(500)
    assert not shell.is_defined('zz')

    # --- Assert runfile text is present after reruns ---
    assert 'runfile' in control.toPlainText()

    # ---- Closing test file and resetting config ----
    main_window.editor.close_file()
    CONF.set('run', 'configurations', [])


@pytest.mark.slow
@flaky(max_runs=3)
def test_connection_to_external_kernel(main_window, qtbot):
    """Test that only Spyder kernels are connected to the Variable Explorer."""
    # Test with a generic kernel
    km, kc = start_new_kernel()

    main_window.ipyconsole._create_client_for_kernel(kc.connection_file, None,
                                                     None, None)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert that there are no variables in the variable explorer
    main_window.variableexplorer.visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.wait(500)
    assert nsb.editor.model.rowCount() == 0

    # Test with a kernel from Spyder
    spykm, spykc = start_new_kernel(spykernel=True)
    main_window.ipyconsole._create_client_for_kernel(spykc.connection_file, None,
                                                     None, None)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert that a variable is visible in the variable explorer
    main_window.variableexplorer.visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.wait(500)
    assert nsb.editor.model.rowCount() == 1

    # Shutdown the kernels
    spykm.shutdown_kernel(now=True)
    km.shutdown_kernel(now=True)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_np_threshold(main_window, qtbot):
    """Test that setting Numpy threshold doesn't make the Variable Explorer slow."""
    # Set Numpy threshold
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('import numpy as np; np.set_printoptions(threshold=np.nan)')

    # Create a big Numpy array
    with qtbot.waitSignal(shell.executed):
        shell.execute('x = np.random.rand(75000,5)')

    # Wait a very small time to see the array in the Variable Explorer
    main_window.variableexplorer.visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 1, timeout=500)

    # Assert that NumPy threshold remains the same as the one
    # set by the user
    with qtbot.waitSignal(shell.executed):
        shell.execute("t = np.get_printoptions()['threshold']")
    assert np.isnan(shell.get_value('t'))


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_change_types_in_varexp(main_window, qtbot):
    """Test that variable types can't be changed in the Variable Explorer."""
    # Create object
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Edit object
    main_window.variableexplorer.visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()

    # Try to change types
    qtbot.keyClicks(QApplication.focusWidget(), "'s'")
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key_Enter)
    qtbot.wait(1000)

    # Assert object remains the same
    assert shell.get_value('a') == 10


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.parametrize("test_directory", [u"non_ascii_ñ_í_ç", u"test_dir"])
def test_change_cwd_ipython_console(main_window, qtbot, tmpdir, test_directory):
    """
    Test synchronization with working directory and File Explorer when
    changing cwd in the IPython console.
    """
    wdir = main_window.workingdirectory
    treewidget = main_window.explorer.treewidget
    shell = main_window.ipyconsole.get_current_shellwidget()

    # Wait until the window is fully up
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create temp dir
    temp_dir = to_text_string(tmpdir.mkdir(test_directory))

    # Change directory in IPython console using %cd
    with qtbot.waitSignal(shell.executed):
        shell.execute(u"%cd {}".format(temp_dir))
    qtbot.wait(1000)

    # Assert that cwd changed in workingdirectory
    assert osp.normpath(wdir.history[-1]) == osp.normpath(temp_dir)

    # Assert that cwd changed in explorer
    assert osp.normpath(treewidget.get_current_folder()) == osp.normpath(temp_dir)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.parametrize("test_directory", [u"non_ascii_ñ_í_ç", u"test_dir"])
def test_change_cwd_explorer(main_window, qtbot, tmpdir, test_directory):
    """
    Test synchronization with working directory and IPython console when
    changing directories in the File Explorer.
    """
    wdir = main_window.workingdirectory
    explorer = main_window.explorer
    shell = main_window.ipyconsole.get_current_shellwidget()

    # Wait until the window is fully up
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create temp directory
    temp_dir = to_text_string(tmpdir.mkdir(test_directory))

    # Change directory in the explorer widget
    explorer.chdir(temp_dir)
    qtbot.wait(1000)

    # Assert that cwd changed in workingdirectory
    assert osp.normpath(wdir.history[-1]) == osp.normpath(temp_dir)

    # Assert that cwd changed in IPython console
    assert osp.normpath(temp_dir) == osp.normpath(shell._cwd)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or not is_module_installed('Cython'),
                    reason="It times out sometimes on Windows and Cython is needed")
def test_run_cython_code(main_window, qtbot):
    """Test all the different ways we have to run Cython code"""
    # ---- Setup ----
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.get_focus_widget()

    # Get a reference to the code editor widget
    code_editor = main_window.editor.get_focus_widget()

    # ---- Run pyx file ----
    # Load test file
    main_window.editor.load(osp.join(LOCATION, 'pyx_script.pyx'))

    # run file
    qtbot.keyClick(code_editor, Qt.Key_F5)
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 1,
                    timeout=COMPILE_AND_EVAL_TIMEOUT)

    # Verify result
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
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 1,
                    timeout=COMPILE_AND_EVAL_TIMEOUT)

    # Verify result
    assert shell.get_value('b') == 3628800

    # Close file
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It fails on Windows.")
def test_open_notebooks_from_project_explorer(main_window, qtbot, tmpdir):
    """Test that notebooks are open from the Project explorer."""
    projects = main_window.projects
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
    idx = projects.treewidget.get_index('notebook.ipynb')
    projects.treewidget.setCurrentIndex(idx)

    # Prese Enter there
    qtbot.keyClick(projects.treewidget, Qt.Key_Enter)

    # Assert that notebook was open
    assert 'notebook.ipynb' in editorstack.get_current_filename()

    # Convert notebook to a Python file
    projects.treewidget.convert_notebook(osp.join(project_dir, 'notebook.ipynb'))

    # Assert notebook was open
    assert 'untitled0.py' in editorstack.get_current_filename()

    # Assert its contents are the expected ones
    file_text = editorstack.get_current_editor().toPlainText()
    assert file_text == '\n# coding: utf-8\n\n# In[1]:\n\n\n1 + 1\n\n\n'

    # Close project
    projects.close_project()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_set_new_breakpoints(main_window, qtbot):
    """Test that new breakpoints are set in the IPython console."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Set a breakpoint
    code_editor = main_window.editor.get_focus_widget()
    code_editor.add_remove_breakpoint(line_number=6)
    qtbot.wait(500)

    # Verify that the breakpoint was set
    shell.kernel_client.input("b")
    qtbot.wait(500)
    assert "1   breakpoint   keep yes   at {}:6".format(test_file) in control.toPlainText()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
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

    reset_run_code(qtbot, shell, code_editor, nsb)

    # ---- Re-run last cell ----
    # Run the first two cells in file
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)

    # Wait until objects have appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 2, timeout=EVAL_TIMEOUT)

    # Clean namespace
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')

    # Wait until there are no objects in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=EVAL_TIMEOUT)

    # Re-run last cell
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.AltModifier)

    # Wait until the object has appeared in the variable explorer
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 1, timeout=EVAL_TIMEOUT)
    assert shell.get_value('li') == [1, 2, 3]

    # ---- Closing test file ----
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or os.environ.get('CI', None) is None or PYQT5,
                    reason="It times out sometimes on Windows, it's not "
                           "meant to be run outside of a CI and it segfaults "
                           "too frequently in PyQt5")
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


@pytest.mark.slow
@flaky(max_runs=3)
def test_close_when_file_is_changed(main_window, qtbot):
    """Test closing spyder when there is a file with modifications open."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)
    editorstack = main_window.editor.get_current_editorstack()
    editor = editorstack.get_current_editor()
    editor.document().setModified(True)

    # Wait for the segfault
    qtbot.wait(3000)


@pytest.mark.slow
@flaky(max_runs=3)
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


@flaky(max_runs=3)
@pytest.mark.skipif((os.name == 'nt' or
                     os.environ.get('CI', None) is not None and PYQT_VERSION >= '5.9'),
                    reason="It times out on Windows and segfaults in our CIs with PyQt >= 5.9")
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
    with qtbot.waitSignal(shell.executed):
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
    with qtbot.waitSignal(shell.executed):
        shell.execute('del myobj')
    qtbot.waitUntil(lambda: nsb.editor.model.rowCount() == 0, timeout=EVAL_TIMEOUT)

    # Close editor
    ok_widget = obj_editor.bbox.button(obj_editor.bbox.Ok)
    qtbot.mouseClick(ok_widget, Qt.LeftButton)

    # Wait for the segfault
    qtbot.wait(3000)


@pytest.mark.slow
@flaky(max_runs=3)
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
    with qtbot.waitSignal(shell.executed):
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_c_and_n_pdb_commands(main_window, qtbot):
    """Test that c and n Pdb commands update the Variable Explorer."""
    nsb = main_window.variableexplorer.get_focus_widget()

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Set a breakpoint
    code_editor = main_window.editor.get_focus_widget()
    code_editor.add_remove_breakpoint(line_number=6)
    qtbot.wait(500)

    # Verify that c works
    qtbot.keyClicks(control, 'c')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)
    assert nsb.editor.model.rowCount() == 1

    # Verify that n works
    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)
    assert nsb.editor.model.rowCount() == 2

    # Verify that doesn't go to sitecustomize.py with next and stops
    # the debugging session.
    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    assert nsb.editor.model.rowCount() == 3

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    # Assert that the prompt appear
    shell.clear_console()
    assert 'In [2]:' in control.toPlainText()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_stop_dbg(main_window, qtbot):
    """Test that we correctly stop a debugging session."""
    nsb = main_window.variableexplorer.get_focus_widget()

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()

    # Load test file
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Move to the next line
    shell.kernel_client.input("n")
    qtbot.wait(1000)

    # Stop debugging
    stop_debug_action = main_window.debug_toolbar_actions[5]
    stop_debug_button = main_window.debug_toolbar.widgetForAction(stop_debug_action)
    qtbot.mouseClick(stop_debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Assert that there is only one entry in the Variable Explorer
    assert nsb.editor.model.rowCount() == 1

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_change_cwd_dbg(main_window, qtbot):
    """
    Test that using the Working directory toolbar is working while debugging.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_focus_widget()
    control.setFocus()

    # Import os to get cwd
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os')

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Set LOCATION as cwd
    main_window.workingdirectory.chdir(tempfile.gettempdir(),
                                       browsing_history=False,
                                       refresh_explorer=True)
    qtbot.wait(1000)

    # Get cwd in console
    qtbot.keyClicks(control, 'os.getcwd()')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(1000)

    # Assert cwd is the right one
    assert tempfile.gettempdir() in control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or PY2, reason="It times out sometimes")
def test_varexp_magic_dbg(main_window, qtbot):
    """Test that %varexp is working while debugging."""
    nsb = main_window.variableexplorer.get_focus_widget()

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_focus_widget()
    control.setFocus()

    # Create an object that can be plotted
    with qtbot.waitSignal(shell.executed):
        shell.execute('li = [1, 2, 3]')

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Generate the plot from the Variable Explorer
    nsb.plot('li', 'plot')
    qtbot.wait(1000)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason="It's not meant to be run outside of a CI")
def test_fileswitcher(main_window, qtbot):
    """Test the use of shorten paths when necessary in the fileswitcher."""
    # Load tests files
    dir_b = osp.join(TEMP_DIRECTORY, 'temp_dir_a', 'temp_b')
    filename_b =  osp.join(dir_b, 'c.py')
    if not osp.isdir(dir_b):
        os.makedirs(dir_b)
    if not osp.isfile(filename_b):
        file_c = open(filename_b, 'w+')
        file_c.close()
    if PYQT5:
        dir_d = osp.join(TEMP_DIRECTORY, 'temp_dir_a', 'temp_c', 'temp_d', 'temp_e')
    else:
        dir_d = osp.join(TEMP_DIRECTORY, 'temp_dir_a', 'temp_c', 'temp_d')
        dir_e = osp.join(TEMP_DIRECTORY, 'temp_dir_a', 'temp_c', 'temp_dir_f', 'temp_e')
        filename_e = osp.join(dir_e, 'a.py')
        if not osp.isdir(dir_e):
            os.makedirs(dir_e)
        if not osp.isfile(filename_e):
            file_e = open(filename_e, 'w+')
            file_e.close()
    filename_d =  osp.join(dir_d, 'c.py')
    if not osp.isdir(dir_d):
        os.makedirs(dir_d)
    if not osp.isfile(filename_d):
        file_d = open(filename_d, 'w+')
        file_d.close()
    main_window.editor.load(filename_b)
    main_window.editor.load(filename_d)

    # Assert that all the path of the file is shown
    main_window.open_fileswitcher()
    if os.name == 'nt':
        item_text = main_window.fileswitcher.list.currentItem().text().replace('\\', '/').lower()
        dir_d = dir_d.replace('\\', '/').lower()
    else:
        item_text = main_window.fileswitcher.list.currentItem().text()
    assert dir_d in item_text

    # Resize Main Window to a third of its width
    size = main_window.window_size
    main_window.resize(size.width() / 3, size.height())
    main_window.open_fileswitcher()

    # Assert that the path shown in the fileswitcher is shorter
    if PYQT5:
        main_window.open_fileswitcher()
        item_text = main_window.fileswitcher.list.currentItem().text()
        assert '...' in item_text


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(not PYQT5, reason="It times out.")
def test_run_static_code_analysis(main_window, qtbot):
    """This tests that the Pylint plugin is working as expected."""
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Select the third-party plugin
    pylint = get_thirdparty_plugin(main_window, "Static code analysis")

    # Do an analysis
    test_file = osp.join(LOCATION, 'script_pylint.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()
    qtbot.keyClick(code_editor, Qt.Key_F8)
    qtbot.wait(3000)

    # Perform the test
    # Check output of the analysis
    treewidget = pylint.get_focus_widget()
    qtbot.waitUntil(lambda: treewidget.results is not None,
                    timeout=SHELL_TIMEOUT)
    result_content = treewidget.results
    assert result_content['C:']
    assert len(result_content['C:']) == 5

    # Close the file
    main_window.editor.close_file()


@flaky(max_runs=3)
def test_troubleshooting_menu_item_and_url(monkeypatch):
    """Test that the troubleshooting menu item calls the valid URL."""
    MockMainWindow = MagicMock(spec=MainWindow)
    mockMainWindow_instance = MockMainWindow()
    mockMainWindow_instance.__class__ = MainWindow
    MockQDesktopServices = Mock()
    mockQDesktopServices_instance = MockQDesktopServices()
    attr_to_patch = ('spyder.app.mainwindow.QDesktopServices')
    monkeypatch.setattr(attr_to_patch, MockQDesktopServices)

    # Unit test of help menu item: Make sure the correct URL is called.
    MainWindow.trouble_guide(mockMainWindow_instance)
    assert MockQDesktopServices.openUrl.call_count == 1
    mockQDesktopServices_instance.openUrl.called_once_with(__trouble_url__)

    # Check that the URL resolves correctly. Ignored if no internet connection.
    try:
        urlopen("https://www.github.com", timeout=1)
    except Exception:
        pass
    else:
        try:
            urlopen(__trouble_url__, timeout=1)
        except URLError:
            raise


@flaky(max_runs=3)
@pytest.mark.slow
def test_tabfilter_typeerror_full(main_window):
    """Test for #5813 ; event filter handles None indicies when moving tabs."""
    MockEvent = MagicMock()
    MockEvent.return_value.type.return_value = QEvent.MouseMove
    MockEvent.return_value.pos.return_value = 0
    mockEvent_instance = MockEvent()

    test_tabbar = main_window.findChildren(QTabBar)[0]
    test_tabfilter = TabFilter(test_tabbar, main_window)
    test_tabfilter.from_index = None
    test_tabfilter.moving = True

    assert test_tabfilter.eventFilter(None, mockEvent_instance)
    assert mockEvent_instance.pos.call_count == 1


@flaky(max_runs=3)
@pytest.mark.slow
def test_help_opens_when_show_tutorial_full(main_window, qtbot):
    """Test fix for #6317 : 'Show tutorial' opens the help plugin if closed."""
    HELP_STR = "Help"

    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    help_pane_menuitem = None
    for action in main_window.plugins_menu.actions():
        if action.text() == HELP_STR:
            help_pane_menuitem = action
            break

    # Test opening tutorial with Help plguin closed
    try:
        main_window.help.plugin_closed()
    except Exception:
        pass
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
    assert isinstance(main_window.focusWidget(), ObjectComboBox)
    assert help_pane_menuitem.isChecked()

    # Test opening tutorial with help plugin open, but not selected
    help_tabbar.setCurrentIndex((help_tabbar.currentIndex() + 1)
                                % help_tabbar.count())
    qtbot.wait(500)
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert None not in (help_tabbar, help_index)
    assert help_index != help_tabbar.currentIndex()
    assert not isinstance(main_window.focusWidget(), ObjectComboBox)
    assert help_pane_menuitem.isChecked()

    main_window.help.show_tutorial()
    qtbot.wait(500)
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    assert None not in (help_tabbar, help_index)
    assert help_index == help_tabbar.currentIndex()
    assert isinstance(main_window.focusWidget(), ObjectComboBox)
    assert help_pane_menuitem.isChecked()

    # Test opening tutorial with help plugin open and the active tab
    qtbot.wait(500)
    main_window.help.show_tutorial()
    help_tabbar, help_index = find_desired_tab_in_window(HELP_STR, main_window)
    qtbot.wait(500)
    assert None not in (help_tabbar, help_index)
    assert help_index == help_tabbar.currentIndex()
    assert isinstance(main_window.focusWidget(), ObjectComboBox)
    assert help_pane_menuitem.isChecked()


def test_report_issue_url(monkeypatch):
    """Test that report_issue sends the data, and to correct url."""
    body = 'This is an example error report body text.'
    title = 'Uncreative issue title here'
    body_autogenerated = 'Auto-generated text.'
    target_url_base = __project_url__ + '/issues/new'

    MockMainWindow = MagicMock(spec=MainWindow)
    mockMainWindow_instance = MockMainWindow()
    mockMainWindow_instance.__class__ = MainWindow
    mockMainWindow_instance.render_issue.return_value = body_autogenerated

    MockQDesktopServices = MagicMock()
    mockQDesktopServices_instance = MockQDesktopServices()
    attr_to_patch = ('spyder.app.mainwindow.QDesktopServices')
    monkeypatch.setattr(attr_to_patch, MockQDesktopServices)

    # Test when body=None, i.e. when Help > Report Issue is chosen
    target_url = QUrl(target_url_base + '?body=' + body_autogenerated)
    MainWindow.report_issue(mockMainWindow_instance, body=None, title=None)
    assert MockQDesktopServices.openUrl.call_count == 1
    MockQDesktopServices.openUrl.assert_called_once_with(target_url)

    # Test with body=None and title != None
    target_url = QUrl(target_url_base + '?body=' + body_autogenerated
                      + "&title=" + title)
    MainWindow.report_issue(mockMainWindow_instance, body=None, title=title)
    assert MockQDesktopServices.openUrl.call_count == 2
    mockQDesktopServices_instance.openUrl.called_with(target_url)

    # Test when body != None, i.e. when auto-submitting error to Github
    target_url = QUrl(target_url_base + '?body=' + body)
    MainWindow.report_issue(mockMainWindow_instance, body=body, title=None)
    assert MockQDesktopServices.openUrl.call_count == 3
    mockQDesktopServices_instance.openUrl.called_with(target_url)

    # Test when body != None and title != None
    target_url = QUrl(target_url_base + '?body=' + body
                      + "&title=" + title)
    MainWindow.report_issue(mockMainWindow_instance, body=body, title=title)
    assert MockQDesktopServices.openUrl.call_count == 4
    mockQDesktopServices_instance.openUrl.called_with(target_url)


def test_render_issue():
    """Test that render issue works without errors and returns text."""
    test_description = "This is a test description"
    test_traceback = "An error occured. Oh no!"

    MockMainWindow = MagicMock(spec=MainWindow)
    mockMainWindow_instance = MockMainWindow()
    mockMainWindow_instance.__class__ = MainWindow

    # Test when description and traceback are not provided
    test_issue_1 = MainWindow.render_issue(mockMainWindow_instance)
    assert type(test_issue_1) == str
    assert len(test_issue_1) > 100

    # Test when description and traceback are provided
    test_issue_2 = MainWindow.render_issue(mockMainWindow_instance,
                                           test_description, test_traceback)
    assert type(test_issue_2) == str
    assert len(test_issue_2) > 100
    assert test_description in test_issue_2
    assert test_traceback in test_issue_2


if __name__ == "__main__":
    pytest.main()
