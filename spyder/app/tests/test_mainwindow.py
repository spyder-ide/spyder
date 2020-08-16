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
from distutils.version import LooseVersion
import os
import os.path as osp
import re
import shutil
import tempfile
from textwrap import dedent
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock  # Python 2
import sys
import uuid

# Third party imports
from flaky import flaky
from IPython.core import release as ipy_release
from jupyter_client.manager import KernelManager
from matplotlib.testing.compare import compare_images
import nbconvert
import numpy as np
from numpy.testing import assert_array_equal
import pylint
import pytest
from qtpy import PYQT5, PYQT_VERSION
from qtpy.QtCore import Qt, QTimer, QEvent, QPoint, QUrl
from qtpy.QtTest import QTest
from qtpy.QtGui import QImage
from qtpy.QtWidgets import (QAction, QApplication, QFileDialog, QLineEdit,
                            QTabBar, QToolTip, QWidget)
from qtpy.QtWebEngineWidgets import WEBENGINE

# Local imports
from spyder import __trouble_url__, __project_url__
from spyder.app import start
from spyder.app.mainwindow import MainWindow  # Tests fail without this import
from spyder.config.base import get_home_dir, get_module_path
from spyder.config.manager import CONF
from spyder.api.widgets.dock import DockTitleBar, TabFilter
from spyder.plugins.base import PluginWindow
from spyder.plugins.help.widgets import ObjectComboBox
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.run.widgets import RunConfiguration
from spyder.py3compat import PY2, to_text_string
from spyder.utils.programs import is_module_installed
from spyder.utils.misc import remove_backslashes

# For testing various Spyder urls
if not PY2:
    from urllib.request import urlopen
    from urllib.error import URLError
else:
    from urllib2 import urlopen, URLError


# =============================================================================
# ---- Constants
# =============================================================================
# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))

# Time to wait until the IPython console is ready to receive input
# (in milliseconds)
SHELL_TIMEOUT = 40000 if os.name == 'nt' else 20000

# Need longer EVAL_TIMEOUT, because need to cythonize and C compile ".pyx" file
# before import and eval it
COMPILE_AND_EVAL_TIMEOUT = 30000

# Time to wait for the IPython console to evaluate something (in
# milliseconds)
EVAL_TIMEOUT = 3000


# =============================================================================
# ---- Utility functions
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
        try:
            # New API
            if plugin.get_name() == plugin_title:
                return plugin
        except AttributeError:
            # Old API
            if plugin.get_plugin_title() == plugin_title:
                return plugin


def reset_run_code(qtbot, shell, code_editor, nsb):
    """Reset state after a run code test"""
    qtbot.waitUntil(lambda: not shell._executing)
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 0, timeout=EVAL_TIMEOUT)
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
# ---- Fixtures
# =============================================================================

@pytest.fixture
def main_window(request):
    """Main Window fixture"""
    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 0)

    # Test assume the plots are rendered in the console as png
    CONF.set('plots', 'mute_inline_plotting', False)
    CONF.set('ipython_console', 'pylab/inline/figure_format', 0)

    # Check if we need to use introspection in a given test
    # (it's faster and less memory consuming not to use it!)
    use_introspection = request.node.get_closest_marker('use_introspection')

    if use_introspection:
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    else:
        try:
            os.environ.pop('SPY_TEST_USE_INTROSPECTION')
        except KeyError:
            pass

    # Only use single_instance mode for tests that require it
    single_instance = request.node.get_closest_marker('single_instance')

    if single_instance:
        CONF.set('main', 'single_instance', True)
    else:
        CONF.set('main', 'single_instance', False)

    # Get config values passed in parametrize and apply them
    try:
        param = request.param
        if isinstance(param, dict) and 'spy_config' in param:
            CONF.set(*param['spy_config'])
    except AttributeError:
        pass

    if not hasattr(main_window, 'window'):
        # Start the window
        window = start.main()
        main_window.window = window
    else:
        window = main_window.window
        # Close everything we can think of
        window.editor.close_file()
        window.projects.close_project()

        if window.console.error_dialog:
            window.console.close_error_dialog()

        window.switcher.close()
        for client in window.ipyconsole.get_clients():
            window.ipyconsole.close_client(client=client, force=True)

        # Reset cwd
        window.explorer.chdir(get_home_dir())

    yield window

    # Print shell content if failed
    if request.node.rep_setup.passed:
        if request.node.rep_call.failed:
            # Print content of shellwidget and close window
            print(window.ipyconsole.get_current_shellwidget(
                )._control.toPlainText())
            # Print info page content is not blank
            console = window.ipyconsole
            client = console.get_current_client()
            if client.info_page != client.blank_page:
                print('info_page')
                print(client.info_page)
            window.close()
            del main_window.window


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""
    def remove_test_dir():
        if hasattr(main_window, 'window'):
            main_window.window.close()
    request.addfinalizer(remove_test_dir)


# =============================================================================
# ---- Tests
# =============================================================================
@flaky(max_runs=3)
@pytest.mark.slow
@pytest.mark.first
@pytest.mark.single_instance
@pytest.mark.skipif((os.environ.get('CI', None) is None or (PY2
                     and not sys.platform.startswith('linux'))),
                    reason="It's not meant to be run outside of CIs")
def test_single_instance_and_edit_magic(main_window, qtbot, tmpdir):
    """Test single instance mode and %edit magic."""
    editorstack = main_window.editor.get_current_editorstack()
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    spy_dir = osp.dirname(get_module_path('spyder'))
    lock_code = ("import sys\n"
                 "sys.path.append(r'{spy_dir_str}')\n"
                 "from spyder.config.base import get_conf_path\n"
                 "from spyder.utils.external import lockfile\n"
                 "lock_file = get_conf_path('spyder.lock')\n"
                 "lock = lockfile.FilesystemLock(lock_file)\n"
                 "lock_created = lock.lock()".format(spy_dir_str=spy_dir))

    # Test single instance
    with qtbot.waitSignal(shell.executed, timeout=2000):
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
def test_lock_action(main_window):
    """Test the lock interface action."""
    action = main_window.lock_interface_action
    plugins = main_window.widgetlist

    # By default the interface is locked.
    assert main_window.interface_locked

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
    assert not main_window.interface_locked

    # Restore default state
    action.trigger()
    assert main_window.interface_locked


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(os.name == 'nt' and PY2, reason="Fails on win and py2")
def test_default_plugin_actions(main_window, qtbot):
    """Test the effect of dock, undock, close and toggle view actions."""
    # Use a particular plugin
    file_explorer = main_window.explorer

    # Undock action
    file_explorer._undock_action.triggered.emit(True)
    qtbot.wait(500)
    assert not file_explorer.dockwidget.isVisible()
    assert file_explorer._undocked_window is not None
    assert isinstance(file_explorer._undocked_window, PluginWindow)
    assert file_explorer._undocked_window.centralWidget() == file_explorer

    # Dock action
    file_explorer._dock_action.triggered.emit(True)
    qtbot.wait(500)
    assert file_explorer.dockwidget.isVisible()
    assert file_explorer._undocked_window is None

    # Close action
    file_explorer._close_plugin_action.triggered.emit(True)
    qtbot.wait(500)
    assert not file_explorer.dockwidget.isVisible()
    assert not file_explorer._toggle_view_action.isChecked()

    # Toggle view action
    file_explorer._toggle_view_action.setChecked(True)
    assert file_explorer.dockwidget.isVisible()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.parametrize('main_window', [{'spy_config': ('main', 'opengl', 'software')}], indirect=True)
def test_opengl_implementation(main_window, qtbot):
    """
    Test that we are setting the selected OpenGL implementation
    """
    assert main_window._test_setting_opengl('software')

    # Restore default config value
    CONF.set('main', 'opengl', 'automatic')


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(
    np.__version__ < '1.14.0' or (os.name == 'nt' and PY2),
    reason="This only happens in Numpy 1.14+"
)
@pytest.mark.parametrize('main_window', [{'spy_config': ('variable_explorer', 'minmax', True)}], indirect=True)
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(PY2 or not sys.platform == 'darwin',
                    reason="Times out in PY2 and fails on other than macOS")
def test_get_help_combo(main_window, qtbot):
    """
    Test that Help can display docstrings for names typed in its combobox.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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


@pytest.mark.slow
@pytest.mark.skipif(PY2, reason="Invalid definition of function in Python 2.")
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


@pytest.mark.slow
@pytest.mark.skipif(PY2, reason="Invalid definition of function in Python 2.")
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
    qtbot.waitUntil(lambda: check_control(control, u'aaʹbb'), timeout=2000)

    # Get help
    control.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, "This function docstring."),
                    timeout=6000)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Does not work on Mac and Windows!")
@pytest.mark.use_introspection
@pytest.mark.parametrize(
    "object_info",
    [("range", "range"),
     ("import matplotlib.pyplot as plt",
      "The object-oriented API is recommended for more complex plots.")])
def test_get_help_editor(main_window, qtbot, object_info):
    """Test that Help works when called from the Editor."""
    help_plugin = main_window.help
    webview = help_plugin.get_widget().rich_text.webview._webview
    webpage = webview.page() if WEBENGINE else webview.page().mainFrame()

    main_window.editor.new(fname="test.py", text="")
    code_editor = main_window.editor.get_focus_widget()
    editorstack = main_window.editor.get_current_editorstack()
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_open()

    # Write some object in the editor
    object_name, expected_text = object_info
    code_editor.set_text(object_name)
    code_editor.move_cursor(len(object_name))
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Get help
    with qtbot.waitSignal(code_editor.sig_display_object_info, timeout=30000):
        editorstack.inspect_current_object()

    # Check that a expected text is part of the page
    qtbot.waitUntil(lambda: check_text(webpage, expected_text), timeout=30000)


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
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or PY2, reason="It fails sometimes")
@pytest.mark.parametrize(
    "debugcell", [True, False])
def test_move_to_first_breakpoint(main_window, qtbot, debugcell):
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
        qtbot.keyClick(code_editor, Qt.Key_Return,
                       modifier=Qt.AltModifier | Qt.ShiftModifier)

        qtbot.waitUntil(
            lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

        # Make sure everything is ready
        assert shell.spyder_kernel_comm.is_open()
        assert shell.is_waiting_pdb_input()

        with qtbot.waitSignal(shell.executed):
            shell.pdb_execute('b')
        assert 'script.py:10' in shell._control.toPlainText()
        # We need to press continue as we don't test yet if a breakpoint
        # is in the cell
        with qtbot.waitSignal(shell.executed):
            shell.pdb_execute('c')

    else:
        # Click the debug button
        with qtbot.waitSignal(shell.executed):
            qtbot.mouseClick(debug_button, Qt.LeftButton)

    # Verify that we are at first breakpoint
    shell.clear_console()
    qtbot.wait(500)
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("list")
    assert "1--> 10 arr = np.array(li)" in control.toPlainText()

    # Exit debugging
    shell.pdb_execute("exit")
    qtbot.wait(500)

    # Set breakpoint on first line with code
    code_editor.debugger.toogle_breakpoint(line_number=2)
    qtbot.wait(500)

    # Click the debug button
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Verify that we are still on debugging
    try:
        assert shell.is_waiting_pdb_input()
    except Exception:
        print('Shell content: ', shell._control.toPlainText(), '\n\n')
        raise

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason='Fails on windows!')
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
@pytest.mark.skipif(os.name == 'nt' or sys.platform == 'darwin',
                    reason="It's failing there")
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
    assert nsb.editor.source_model.rowCount() == 4

    # --- Assert only runfile text is present and there's no banner text ---
    # See spyder-ide/spyder#5301.
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
    main_window.variableexplorer._visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.wait(500)
    assert nsb.editor.source_model.rowCount() == 0

    # Test with a kernel from Spyder
    spykm, spykc = start_new_kernel(spykernel=True)
    main_window.ipyconsole._create_client_for_kernel(spykc.connection_file, None,
                                                     None, None)
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert that a variable is visible in the variable explorer
    main_window.variableexplorer._visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.wait(500)
    assert nsb.editor.source_model.rowCount() == 1

    # Shutdown the kernels
    spykm.stop_restarter()
    km.stop_restarter()
    spykm.shutdown_kernel(now=True)
    km.shutdown_kernel(now=True)
    spykc.stop_channels()
    kc.stop_channels()


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
    main_window.variableexplorer._visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
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
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_change_cwd_ipython_console(main_window, qtbot, tmpdir, test_directory):
    """
    Test synchronization with working directory and File Explorer when
    changing cwd in the IPython console.
    """
    wdir = main_window.workingdirectory
    treewidget = main_window.explorer.fileexplorer.treewidget
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
    assert osp.normpath(wdir.get_container().history[-1]) == osp.normpath(
        temp_dir)

    # Assert that cwd changed in explorer
    assert osp.normpath(treewidget.get_current_folder()) == osp.normpath(
        temp_dir)


@pytest.mark.slow
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(
    (os.name == 'nt' or sys.platform == 'darwin' or
     LooseVersion(ipy_release.version) == LooseVersion('7.11.0')),
    reason="Hard to test on Windows and macOS and fails for IPython 7.11.0")
def test_run_cython_code(main_window, qtbot):
    """Test all the different ways we have to run Cython code"""
    # ---- Setup ----
    # Get a reference to the code editor widget
    code_editor = main_window.editor.get_focus_widget()

    # ---- Run pyx file ----
    # Load test file
    main_window.editor.load(osp.join(LOCATION, 'pyx_script.pyx'))

    # Run file
    qtbot.keyClick(code_editor, Qt.Key_F5)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.get_focus_widget()

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
    idx = projects.explorer.treewidget.get_index('notebook.ipynb')
    projects.explorer.treewidget.setCurrentIndex(idx)

    # Prese Enter there
    qtbot.keyClick(projects.explorer.treewidget, Qt.Key_Enter)

    # Assert that notebook was open
    assert 'notebook.ipynb' in editorstack.get_current_filename()

    # Convert notebook to a Python file
    projects.explorer.treewidget.convert_notebook(osp.join(project_dir, 'notebook.ipynb'))

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


@pytest.mark.slow
@flaky(max_runs=3)
def test_runfile_from_project_explorer(main_window, qtbot, tmpdir):
    """Test that file are run from the Project explorer."""
    projects = main_window.projects
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
    idx = projects.explorer.treewidget.get_index('script.py')
    projects.explorer.treewidget.setCurrentIndex(idx)

    # Press Enter there
    qtbot.keyClick(projects.explorer.treewidget, Qt.Key_Enter)

    # Assert that the file was open
    assert 'script.py' in editorstack.get_current_filename()

    # Run Python file
    projects.explorer.treewidget.run([osp.join(project_dir, 'script.py')])

    # Wait until the new console is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Wait until all objects have appeared in the variable explorer
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 4,
                    timeout=EVAL_TIMEOUT)

    # Check variables value
    assert shell.get_value('a') == 10
    assert shell.get_value('s') == "Z:\\escape\\test\\string\n"
    assert shell.get_value('li') == [1, 2, 3]
    assert_array_equal(shell.get_value('arr'), np.array([1, 2, 3]))

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
    code_editor.debugger.toogle_breakpoint(line_number=6)
    qtbot.wait(500)

    # Verify that the breakpoint was set
    shell.pdb_execute("b")
    qtbot.wait(500)
    assert "1   breakpoint   keep yes   at {}:6".format(test_file) in control.toPlainText()

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
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
    code_editor = main_window.editor.get_focus_widget()
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Get a reference to the namespace browser widget
    nsb = main_window.variableexplorer.get_focus_widget()

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
    modifier = Qt.ControlModifier
    if sys.platform == 'darwin':
        modifier = Qt.MetaModifier
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
    qtbot.keyClick(code_editor, Qt.Key_Return,
                   modifier=Qt.AltModifier | Qt.ShiftModifier)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')
    qtbot.keyClick(shell._control, 'c')
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

    # ---- Closing test file ----
    main_window.editor.close_file()


@pytest.mark.slow
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
    nsb = main_window.variableexplorer.get_focus_widget()

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
    assert main_window.editor._ismaximized

    # Verify that the action minimizes the plugin too
    qtbot.mouseClick(max_button, Qt.LeftButton)
    assert not main_window.editor._ismaximized


@pytest.mark.slow
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
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()
    obj_editor_id = list(nsb.editor.delegate._editors.keys())[0]
    obj_editor = nsb.editor.delegate._editors[obj_editor_id]['editor']

    # Move to the IPython console and delete that object
    main_window.ipyconsole.get_focus_widget().setFocus()
    with qtbot.waitSignal(shell.executed):
        shell.execute('del myobj')
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() == 0, timeout=EVAL_TIMEOUT)

    # Close editor
    ok_widget = obj_editor.btn_close
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
    main_window.variableexplorer._visibility_changed(True)
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: nsb.editor.source_model.rowCount() > 0, timeout=EVAL_TIMEOUT)
    nsb.editor.setFocus()
    nsb.editor.edit_item()

    # Change focus to IPython console
    main_window.ipyconsole.get_focus_widget().setFocus()

    # Wait for the error
    qtbot.wait(3000)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It times out sometimes on Windows and macOS")
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
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Set a breakpoint
    code_editor = main_window.editor.get_focus_widget()
    code_editor.debugger.toogle_breakpoint(line_number=6)
    qtbot.wait(500)

    # Verify that c works
    qtbot.keyClicks(control, 'c')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 1)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Verify that n works
    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 2)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Verify that doesn't go to sitecustomize.py with next and stops
    # the debugging session.
    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 3)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    qtbot.keyClicks(control, 'n')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(
        lambda: 'In [2]:' in control.toPlainText())

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
    shell.pdb_execute("n")
    qtbot.wait(1000)

    # Stop debugging
    stop_debug_action = main_window.debug_toolbar_actions[5]
    stop_debug_button = main_window.debug_toolbar.widgetForAction(stop_debug_action)
    qtbot.mouseClick(stop_debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Assert there are only two ipdb prompts in the console
    assert shell._control.toPlainText().count('ipdb') == 2

    # Remove breakpoint and close test file
    main_window.editor.clear_all_breakpoints()
    main_window.editor.close_file()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It only works on Linux")
def test_change_cwd_dbg(main_window, qtbot):
    """
    Test that using the Working directory toolbar is working while debugging.
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Load test file to be able to enter in debugging mode
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_focus_widget()
    control.setFocus()

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)

    # Set LOCATION as cwd
    main_window.workingdirectory.chdir(tempfile.gettempdir())
    qtbot.wait(1000)
    print(repr(control.toPlainText()))
    shell.clear_console()
    qtbot.wait(500)

    # Get cwd in console
    qtbot.keyClicks(control, '!import os; os.getcwd()')
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

    # Load test file to be able to enter in debugging mode
    test_file = osp.join(LOCATION, 'script.py')
    main_window.editor.load(test_file)

    # Give focus to the widget that's going to receive clicks
    control = main_window.ipyconsole.get_focus_widget()
    control.setFocus()

    # Click the debug button
    debug_action = main_window.debug_toolbar_actions[0]
    debug_button = main_window.debug_toolbar.widgetForAction(debug_action)
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Get to an object that can be plotted
    for _ in range(2):
        qtbot.keyClicks(control, 'n')
        qtbot.keyClick(control, Qt.Key_Enter)
        qtbot.waitUntil(
            lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Generate the plot from the Variable Explorer
    nsb.editor.plot('li', 'plot')
    qtbot.wait(1000)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(PY2, reason="It times out sometimes")
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(PY2, reason="It times out sometimes")
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
    control = main_window.ipyconsole.get_focus_widget()
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
    shell._prompt_html = None
    client.restart_kernel()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
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


@flaky(max_runs=3)
@pytest.mark.slow
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
    main_window.open_switcher()
    qtbot.keyClicks(switcher.edit, '@')
    qtbot.wait(200)
    assert switcher.count() == 2
    switcher.close()


@flaky(max_runs=3)
@pytest.mark.slow
def test_edidorstack_open_switcher_dlg(main_window, tmpdir):
    """
    Test that the file switcher is working as expected when called from the
    editorstack.

    Regression test for spyder-ide/spyder#10684
    """
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
@pytest.mark.slow
def test_edidorstack_open_symbolfinder_dlg(main_window, qtbot, tmpdir):
    """
    Test that the symbol finder is working as expected when called from the
    editorstack.

    Regression test for spyder-ide/spyder#10684
    """
    # Add a file to the editor.
    file = tmpdir.join('test_file.py')
    file.write('''
               def example_def():
                   pass

               def example_def_2():
                   pass
               ''')
    main_window.editor.load(str(file))

    # Test that the symbol finder opens as expected from the editorstack.
    editorstack = main_window.editor.get_current_editorstack()
    assert editorstack.switcher_dlg is None
    editorstack.open_symbolfinder_dlg()
    assert editorstack.switcher_dlg
    assert editorstack.switcher_dlg.isVisible()
    assert editorstack.switcher_dlg.count() == 2


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="Times out sometimes on macOS")
def test_run_static_code_analysis(main_window, qtbot):
    """This tests that the Pylint plugin is working as expected."""
    # Select the third-party plugin
    pylint_plugin = get_thirdparty_plugin(main_window, "Code Analysis")

    # Do an analysis
    test_file = osp.join(LOCATION, 'script_pylint.py')
    main_window.editor.load(test_file)
    code_editor = main_window.editor.get_focus_widget()
    qtbot.keyClick(code_editor, Qt.Key_F8)
    qtbot.wait(3000)

    # Perform the test
    # Check output of the analysis
    treewidget = pylint_plugin.get_focus_widget()
    qtbot.waitUntil(lambda: treewidget.results is not None,
                    timeout=SHELL_TIMEOUT)
    result_content = treewidget.results
    assert result_content['C:']

    pylint_version = LooseVersion(pylint.__version__)
    if pylint_version < LooseVersion('2.5.0'):
        number_of_conventions = 5
    else:
        number_of_conventions = 3
    assert len(result_content['C:']) == number_of_conventions

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
@pytest.mark.skipif(os.name == 'nt', reason="It fails on Windows")
def test_help_opens_when_show_tutorial_full(main_window, qtbot):
    """
    Test fix for spyder-ide/spyder#6317.

    'Show tutorial' opens the help plugin if closed.
    """
    HELP_STR = "Help"

    help_pane_menuitem = None
    for action in main_window.plugins_menu.actions():
        if action.text() == HELP_STR:
            help_pane_menuitem = action
            break

    # Test opening tutorial with Help plguin closed
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


@pytest.mark.slow
@flaky(max_runs=3)
def test_report_issue(main_window, qtbot):
    """Test that the report error dialog opens correctly."""
    main_window.report_issue()
    qtbot.wait(300)
    assert main_window._report_dlg is not None
    assert main_window._report_dlg.isVisible()
    assert main_window._report_dlg.close()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(
    sys.platform.startswith('linux'), reason="It segfaults on Linux")
def test_custom_layouts(main_window, qtbot):
    """Test that layout are showing the expected widgets visible."""
    mw = main_window
    mw.first_spyder_run = False
    prefix = 'window' + '/'
    settings = mw.load_window_settings(prefix=prefix, default=True)

    # Test layout changes
    for layout_idx in ['default'] + list(range(4)):
        with qtbot.waitSignal(mw.sig_layout_setup_ready, timeout=5000):
            layout = mw.setup_default_layouts(layout_idx, settings=settings)

            with qtbot.waitSignal(None, timeout=500, raising=False):
                # Add a wait to see changes
                pass

            widgets_layout = layout['widgets']
            hidden_widgets = layout['hidden widgets']
            for column in widgets_layout:
                for row in column:
                    for idx, widget in enumerate(row):
                        if idx == 0:
                            if widget not in hidden_widgets:
                                print(widget)  # spyder: test-skip
                                try:
                                    # New API
                                    assert widget.get_widget().isVisible()
                                except AttributeError:
                                    # Old API
                                    assert widget.isVisible()


@pytest.mark.slow
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


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == 'darwin', reason="Fails on macOS")
def test_pylint_follows_file(qtbot, tmpdir, main_window):
    """Test that file editor focus change updates pylint combobox filename."""
    for plugin in main_window.thirdparty_plugins:
        if plugin.CONF_SECTION == 'pylint':
            pylint_plugin = plugin
            break

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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Fails on Windows")
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

    error_dialog = main_window.console.error_dialog
    assert error_dialog is not None
    assert 'Exception in comms call get_cwd' in error_dialog.error_traceback
    assert 'No module named' in error_dialog.error_traceback
    main_window.console.close_error_dialog()
    CONF.set('main', 'show_internal_errors', False)


@pytest.mark.slow
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
    qtbot.mouseClick(debug_button, Qt.LeftButton)
    qtbot.wait(1000)
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Continue debugging
    qtbot.keyClick(shell._control, 'c')
    qtbot.keyClick(shell._control, Qt.Key_Enter)
    qtbot.wait(500)

    # Set a breakpoint
    code_editor.debugger.toogle_breakpoint(line_number=3)

    # We should drop into the debugger
    qtbot.waitUntil(
            lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    qtbot.keyClick(shell._control, 'q')
    qtbot.keyClick(shell._control, Qt.Key_Enter)
    qtbot.wait(500)

    # Clear all breakpoints
    main_window.editor.clear_all_breakpoints()


# --- Preferences
# ----------------------------------------------------------------------------
def preferences_dialog_helper(qtbot, main_window, section):
    """
    Open preferences dialog and select page with `section` (CONF_SECTION).
    """
    main_window.show_preferences()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is not None,
                    timeout=5000)
    dlg = main_window.prefs_dialog_instance
    index = dlg.get_index_by_name(section)
    page = dlg.get_page(index)
    dlg.set_current_index(index)
    return dlg, index, page


@pytest.mark.slow
def test_preferences_run_section_exists(main_window, qtbot):
    """
    Test for spyder-ide/spyder#13524 regression.

    Ensure the Run section exists.
    """
    assert preferences_dialog_helper(qtbot, main_window, 'run')


@pytest.mark.slow
def test_preferences_checkboxes_not_checked_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#10139 regression.

    Enabling codestyle/docstyle on the completion section of preferences,
    was not updating correctly.
    """
    # Reset config
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)

    # Open completion prefences and update options
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'lsp-server')
    # Get the correct tab pages inside the Completion preferences page
    tnames = [page.tabs.tabText(i).lower() for i in range(page.tabs.count())]
    tab_widgets = {
        tnames.index('code style'): page.code_style_check,
        tnames.index('docstring style'): page.docstring_style_check,
    }
    for idx, check in tab_widgets.items():
        page.tabs.setCurrentIndex(idx)
        check.animateClick()
        qtbot.wait(500)
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is None,
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
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)


@pytest.mark.slow
def test_preferences_change_font_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#10284 regression.

    Changing font resulted in error.
    """
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'appearance')
    for fontbox in [page.plain_text_font.fontbox,
                    page.rich_text_font.fontbox]:
        fontbox.setFocus()
        idx = fontbox.currentIndex()
        fontbox.setCurrentIndex(idx + 1)
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is None,
                    timeout=5000)


@pytest.mark.slow
@pytest.mark.skipif(
    sys.platform == 'darwin',
    reason="Changes of Shitf+Return shortcut cause an ambiguos shortcut")
def test_preferences_empty_shortcut_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#12992 regression.

    Overwritting shortcuts results in a shortcuts conflict.
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
    main_window.apply_shortcuts()

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
    main_window.apply_shortcuts()
    qtbot.wait(500)  # Wait for shortcut change to actually be applied

    # Check shortcut run cell and advance reset
    code_editor.setFocus()
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(lambda: 'runcell(0' in shell._control.toPlainText())


@pytest.mark.slow
def test_preferences_shortcut_reset_regression(main_window, qtbot):
    """
    Test for spyder-ide/spyder/#11132 regression.

    Resetting shortcut resulted in error.
    """
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'shortcuts')
    page.reset_to_default(force=True)
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is None,
                    timeout=5000)


@pytest.mark.slow
def test_preferences_change_interpreter(qtbot, main_window):
    """Test that on main interpreter change signal is emitted."""
    # Check original pyls configuration
    lsp = main_window.completions.get_client('lsp')
    config = lsp.generate_python_config()
    jedi = config['configurations']['pyls']['plugins']['jedi']
    assert jedi['environment'] is None
    assert jedi['extra_paths'] == []

    # Change main interpreter on preferences
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'main_interpreter')
    page.cus_exec_radio.setChecked(True)
    page.cus_exec_combo.combobox.setCurrentText(sys.executable)
    with qtbot.waitSignal(main_window.sig_main_interpreter_changed,
                          timeout=5000, raising=True):
        dlg.ok_btn.animateClick()

    # Check updated pyls configuration
    config = lsp.generate_python_config()
    jedi = config['configurations']['pyls']['plugins']['jedi']
    assert jedi['environment'] == sys.executable
    assert jedi['extra_paths'] == []


@pytest.mark.slow
def test_preferences_last_page_is_loaded(qtbot, main_window):
    # Test that the last page is updated on re open
    dlg, index, page = preferences_dialog_helper(qtbot, main_window,
                                                 'main_interpreter')
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is not None,
                    timeout=5000)
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is None,
                    timeout=5000)

    main_window.show_preferences()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is not None,
                    timeout=5000)
    dlg = main_window.prefs_dialog_instance
    assert dlg.get_current_index() == index
    dlg.ok_btn.animateClick()
    qtbot.waitUntil(lambda: main_window.prefs_dialog_instance is None,
                    timeout=5000)


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.use_introspection
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It times out too much on Windows and macOS")
def test_go_to_definition(main_window, qtbot, capsys):
    """Test that go-to-definition works as expected."""
    # --- Code that gives no definition
    code_no_def = dedent("""
    from qtpy.QtCore import Qt
    Qt.FramelessWindowHint""")

    # Create new editor with code and wait until LSP is ready
    main_window.editor.new(text=code_no_def)
    code_editor = main_window.editor.get_focus_widget()
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_open()

    # Move cursor to the left one character to be next to
    # FramelessWindowHint
    code_editor.move_cursor(-1)
    with qtbot.waitSignal(code_editor.lsp_response_signal):
        code_editor.go_to_definition_from_cursor()

    # Capture stderr and assert there are no errors
    sys_stream = capsys.readouterr()
    assert sys_stream.err == u''

    # --- Code that gives definition
    code_def = "import qtpy.QtCore"

    # Create new editor with code and wait until LSP is ready
    main_window.editor.new(text=code_def)
    n_editors = len(main_window.editor.get_filenames())
    code_editor = main_window.editor.get_focus_widget()
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_open()

    # Move cursor to the left one character to be next to QtCore
    code_editor.move_cursor(-1)
    with qtbot.waitSignal(code_editor.lsp_response_signal):
        code_editor.go_to_definition_from_cursor()

    def _get_filenames():
        return [osp.basename(f) for f in main_window.editor.get_filenames()]

    qtbot.waitUntil(lambda: 'QtCore.py' in _get_filenames())
    assert 'QtCore.py' in _get_filenames()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin' and not PY2,
                    reason="It times out on macOS/PY3")
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
        lambda: 'ipdb> continue' in shell._control.toPlainText())
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    assert "1---> 2 print(1)" in control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.parametrize(
    "debug", [True, False])
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
    shell.execute(function + u"(0, r'{}')".format(to_text_string(p)))
    control = main_window.ipyconsole.get_focus_widget()

    if debug:
        # Continue
        qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')

        # Reach the 'name' input
        shell.pdb_execute('c')

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


@pytest.mark.slow
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
    nsb = main_window.variableexplorer.get_focus_widget()

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


@pytest.mark.slow
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
    nsb = main_window.variableexplorer.get_focus_widget()

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


@pytest.mark.slow
@flaky(max_runs=3)
def test_varexp_refresh(main_window, qtbot):
    """
    Test refreshing the variable explorer while the kernel is executing.
    """
    # Create object
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = main_window.ipyconsole.get_focus_widget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    shell.execute("import time\n"
                  "for i in range(10):\n"
                  "    print('i = {}'.format(i))\n"
                  "    time.sleep(.1)\n")

    qtbot.waitUntil(lambda: "i = 0" in control.toPlainText())
    qtbot.wait(300)
    # Get value object
    nsb = main_window.variableexplorer.get_focus_widget()

    # This is empty
    assert len(nsb.editor.source_model._data) == 0

    nsb.refresh_table()
    qtbot.waitUntil(lambda: len(nsb.editor.source_model._data) == 1)

    assert 0 < int(nsb.editor.source_model._data['i']['view']) < 9


@pytest.mark.slow
@flaky(max_runs=3)
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
    assert 'runcell(0' in shell._control.toPlainText()
    assert 'cell is empty' not in shell._control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    assert 'runcell(1' in shell._control.toPlainText()
    assert 'Error' not in shell._control.toPlainText()
    assert 'cell is empty' in shell._control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=3)
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
    qtbot.mouseClick(debug_button, Qt.LeftButton)

    for key in ['n', 'n', 's', 'n', 'n']:
        qtbot.waitUntil(
            lambda: shell._control.toPlainText().split()[-1] == 'ipdb>',
            timeout=3000)
        qtbot.keyClick(shell._control, key)
        qtbot.keyClick(shell._control, Qt.Key_Enter)

    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')
    assert shell.get_value('abba') == 27

    code_editor.setFocus()
    # call runcell
    qtbot.keyClick(code_editor, Qt.Key_Return, modifier=Qt.ShiftModifier)
    qtbot.waitUntil(lambda: "!runcell" in shell._control.toPlainText())
    qtbot.waitUntil(
        lambda: shell._control.toPlainText().split()[-1] == 'ipdb>')

    # Make sure the local variables are detected
    assert "abba 27" in shell._control.toPlainText()


# --- Path manager
# ----------------------------------------------------------------------------
@pytest.mark.slow
def test_path_manager_updates_clients(qtbot, main_window, tmpdir):
    """Check that on path manager updates, consoles correctly update."""
    main_window.show_path_manager()
    dlg = main_window._path_manager

    test_folder = 'foo-spam-bar-123'
    folder = str(tmpdir.mkdir(test_folder))
    dlg.add_path(folder)
    qtbot.waitUntil(lambda: dlg.button_ok.isEnabled(), timeout=EVAL_TIMEOUT)

    with qtbot.waitSignal(dlg.sig_path_changed):
        dlg.button_ok.animateClick()

    cmd = 'import sys;print(sys.path)'

    # Check Spyder is updated
    main_window.console.execute_lines(cmd)
    syspath = main_window.console.get_sys_path()
    assert folder in syspath

    # Check clients are updated
    count = 0
    for client in main_window.ipyconsole.get_clients():
        shell = client.shellwidget
        if shell is not None:
            syspath = shell.execute(cmd)
            control = shell._control
            # `shell.executed` signal was not working so we use waitUntil
            qtbot.waitUntil(lambda: 'In [2]:' in control.toPlainText(),
                            timeout=EVAL_TIMEOUT)
            assert test_folder in control.toPlainText()
            count += 1
    assert count >= 1


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or sys.platform == 'darwin',
                    reason="It times out on macOS and Windows")
def test_pbd_key_leak(main_window, qtbot, tmpdir):
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
        shell.execute('%debug')
        qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')
        qtbot.keyClick(control, 'u')
        qtbot.keyClick(control, Qt.Key_Enter)
        qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')

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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="It times out on macOS")
def test_pbd_step(main_window, qtbot, tmpdir):
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
    assert '1/0' in control.toPlainText()

    # Debug and enter first file
    shell.execute('%debug')
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')
    qtbot.waitUntil(
        lambda: osp.samefile(
            main_window.editor.get_current_editor().filename,
            str(test_file)))

    # Go up and enter second file
    qtbot.keyClick(control, 'u')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')
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

    # Change frame but stay at the same place
    qtbot.keyClicks(control, 'test = 0')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'ipdb>')
    qtbot.wait(1000)

    # Make sure we didn't move
    assert osp.samefile(
        main_window.editor.get_current_editor().filename,
        str(test_file))


@pytest.mark.slow
@flaky(max_runs=3)
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform.startswith('linux'),
                    reason="It fails sometimes on Linux")
@pytest.mark.parametrize(
    "ipython", [True, False])
@pytest.mark.parametrize(
    "test_cell_magic", [True, False])
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
    control = main_window.ipyconsole.get_focus_widget()

    error_text = 'save this file with the .ipy extension'
    try:
        if ipython:
            if test_cell_magic:
                qtbot.waitUntil(
                    lambda: 'Writing' in control.toPlainText())

                # Verify that the code was executed
                assert osp.exists(to_text_string(write_file))
            else:
                qtbot.waitUntil(lambda: 'ipdb>' in control.toPlainText())
            assert error_text not in control.toPlainText()
        else:
            qtbot.waitUntil(lambda: error_text in control.toPlainText())
    finally:
        if osp.exists(to_text_string(write_file)):
            os.remove(to_text_string(write_file))


@pytest.mark.slow
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

    nsb = main_window.variableexplorer.get_focus_widget()
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

    with qtbot.waitSignal(shell.executed):
        shell.execute('c')

    # At the end, b should be back and a should be 10
    qtbot.waitUntil(lambda: 'b' in nsb.editor.source_model._data)
    assert nsb.editor.source_model._data['a']['view'] == '10'
    assert nsb.editor.source_model._data['b']['view'] == '10'


@pytest.mark.slow
@flaky(max_runs=3)
def test_post_mortem(main_window, qtbot, tmpdir):
    """Test post mortem works"""
    # Check we can use custom complete for pdb
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = main_window.ipyconsole.get_focus_widget()

    test_file = tmpdir.join('test.py')
    test_file.write('raise RuntimeError\n')

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "runfile(" + repr(str(test_file)) + ", post_mortem=True)")

    assert "ipdb>" in control.toPlainText()


@pytest.mark.slow
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
    code_editor.set_text(
        "import multiprocessing\n"
        "import traceback\n"
        'if __name__ is "__main__":\n'
        "    p = multiprocessing.Process(target=traceback.print_exc)\n"
        "    p.start()\n"
        "    p.join()\n"
    )
    # This code should run even on windows

    # Start running
    qtbot.mouseClick(run_button, Qt.LeftButton)

    # Because multiprocessing is behaving strangly on windows, only some
    # situations will work. This is one of these situations so it shouldn't
    # be broken.
    if os.name == 'nt':
        qtbot.waitUntil(
            lambda: "Warning: multiprocessing" in shell._control.toPlainText())
    else:
        # There is no exception, so the exception is None
        qtbot.waitUntil(
            lambda: 'None' in shell._control.toPlainText())


@pytest.mark.slow
@flaky(max_runs=3)
def test_varexp_cleared_after_kernel_restart(main_window, qtbot):
    """
    Test that the variable explorer is cleared after a kernel restart.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = main_window.ipyconsole.get_focus_widget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create a variable
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert the value is shown in the variable explorer
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data,
                    timeout=3000)

    # Restart Kernel
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=10000):
        shell.ipyclient.restart_kernel()

    # Assert the value was removed
    qtbot.waitUntil(lambda: 'a' not in nsb.editor.source_model._data,
                    timeout=3000)


@pytest.mark.slow
@flaky(max_runs=3)
def test_varexp_cleared_after_reset(main_window, qtbot):
    """
    Test that the variable explorer is cleared after triggering a
    reset in the IPython console and variable explorer panes.
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    control = main_window.ipyconsole.get_focus_widget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create a variable
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Assert the value is shown in the variable explorer
    nsb = main_window.variableexplorer.get_focus_widget()
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
    nsb = main_window.variableexplorer.get_focus_widget()
    qtbot.waitUntil(lambda: 'a' in nsb.editor.source_model._data,
                    timeout=3000)

    # Trigger a reset in the console
    shell.ipyclient.reset_namespace()

    # Assert the value was removed
    qtbot.waitUntil(lambda: 'a' not in nsb.editor.source_model._data,
                    timeout=3000)


@pytest.mark.slow
@flaky(max_runs=3)
def test_immediate_debug(main_window, qtbot):
    """
    Check if we can enter debugging immediately
    """
    shell = main_window.ipyconsole.get_current_shellwidget()
    with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
        shell.execute("%debug print()")


if __name__ == "__main__":
    pytest.main()
