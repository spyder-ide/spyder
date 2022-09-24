# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the IPython console plugin.
"""

# Standard library imports
import codecs
import glob
import os
import os.path as osp
import psutil
import shutil
import sys
import tempfile
from textwrap import dedent
import threading
import traceback
from unittest.mock import Mock

# Third party imports
import IPython
from IPython.core import release as ipy_release
from IPython.core.application import get_ipython_dir
from flaky import flaky
from pkg_resources import parse_version
from pygments.token import Name
import pytest
from qtpy import PYQT5
from qtpy.QtCore import Qt
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import QMessageBox, QMainWindow
import sympy

# Local imports
from spyder.api.plugins import Plugins
from spyder.app.cli_options import get_options
from spyder.config.base import (
    running_in_ci, running_in_ci_with_conda)
from spyder.config.gui import get_color_scheme
from spyder.config.manager import CONF
from spyder.py3compat import PY2, to_text_string
from spyder.plugins.debugger.plugin import Debugger
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.help.utils.sphinxify import CSS_PATH
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.ipythonconsole.utils import stdfile
from spyder.plugins.ipythonconsole.utils.style import create_style_class
from spyder.plugins.ipythonconsole.widgets import ClientWidget
from spyder.utils.programs import get_temp_dir
from spyder.utils.conda import is_conda_env


# =============================================================================
# Constants
# =============================================================================
SHELL_TIMEOUT = 20000
TEMP_DIRECTORY = tempfile.gettempdir()
NON_ASCII_DIR = osp.join(TEMP_DIRECTORY, u'測試', u'اختبار')
NEW_DIR = 'new_workingdir'


# =============================================================================
# Utillity Functions
# =============================================================================
def get_console_font_color(syntax_style):
    styles = create_style_class(syntax_style).styles
    font_color = styles[Name]
    return font_color


def get_console_background_color(style_sheet):
    background_color = style_sheet.split('background-color:')[1]
    background_color = background_color.split(';')[0]
    return background_color


def get_conda_test_env(test_env_name=u'spytest-ž'):
    """Return the full prefix path of the given `test_env_name`."""
    if 'envs' in sys.prefix:
        root_prefix = os.path.dirname(os.path.dirname(sys.prefix))
    else:
        root_prefix = sys.prefix

    test_env_prefix = os.path.join(root_prefix, 'envs', test_env_name)

    if os.name == 'nt':
        test_env_executable = os.path.join(test_env_prefix, 'python.exe')
    else:
        test_env_executable = os.path.join(test_env_prefix, 'bin', 'python')

    return test_env_executable


# =============================================================================
# Qt Test Fixtures
# =============================================================================
@pytest.fixture
def ipyconsole(qtbot, request, tmpdir):
    """IPython console fixture."""
    configuration = CONF
    no_web_widgets = request.node.get_closest_marker('no_web_widgets')

    class MainWindowMock(QMainWindow):

        def __init__(self):
            # This avoids using the cli options passed to pytest
            sys_argv = [sys.argv[0]]
            self._cli_options = get_options(sys_argv)[0]
            if no_web_widgets:
                self._cli_options.no_web_widgets = True
            super().__init__()

        def get_spyder_pythonpath(self):
            return configuration.get('main', 'spyder_pythonpath', [])

        def __getattr__(self, attr):
            if attr == 'consoles_menu_actions':
                return []
            elif attr == 'editor':
                return None
            else:
                return Mock()

    # Tests assume inline backend
    configuration.set('ipython_console', 'pylab/backend', 0)

    # Start the console in a fixed working directory
    use_startup_wdir = request.node.get_closest_marker('use_startup_wdir')
    if use_startup_wdir:
        new_wdir = str(tmpdir.mkdir(NEW_DIR))
        configuration.set(
            'workingdir',
            'startup/use_project_or_home_directory',
            False
        )
        configuration.set('workingdir', 'startup/use_fixed_directory', True)
        configuration.set('workingdir', 'startup/fixed_directory', new_wdir)
    else:
        configuration.set(
            'workingdir',
            'startup/use_project_or_home_directory',
            True
        )
        configuration.set('workingdir', 'startup/use_fixed_directory', False)

    # Test the console with a non-ascii temp dir
    non_ascii_dir = request.node.get_closest_marker('non_ascii_dir')
    if non_ascii_dir:
        test_dir = NON_ASCII_DIR
    else:
        test_dir = ''

    # Instruct the console to not use a stderr file
    no_stderr_file = request.node.get_closest_marker('no_stderr_file')
    if no_stderr_file:
        test_no_stderr = True
    else:
        test_no_stderr = False

    # Use the automatic backend if requested
    auto_backend = request.node.get_closest_marker('auto_backend')
    if auto_backend:
        configuration.set('ipython_console', 'pylab/backend', 1)

    # Use the Tkinter backend if requested
    tk_backend = request.node.get_closest_marker('tk_backend')
    if tk_backend:
        configuration.set('ipython_console', 'pylab/backend', 3)

    # Start a Pylab client if requested
    pylab_client = request.node.get_closest_marker('pylab_client')
    is_pylab = True if pylab_client else False

    # Start a Sympy client if requested
    sympy_client = request.node.get_closest_marker('sympy_client')
    is_sympy = True if sympy_client else False

    # Start a Cython client if requested
    cython_client = request.node.get_closest_marker('cython_client')
    is_cython = True if cython_client else False

    # Use an external interpreter if requested
    external_interpreter = request.node.get_closest_marker(
        'external_interpreter')
    if external_interpreter:
        configuration.set('main_interpreter', 'default', False)
        configuration.set('main_interpreter', 'executable', sys.executable)
    else:
        configuration.set('main_interpreter', 'default', True)
        configuration.set('main_interpreter', 'executable', '')

    # Use the test environment interpreter if requested
    test_environment_interpreter = request.node.get_closest_marker(
        'test_environment_interpreter')
    if test_environment_interpreter:
        configuration.set('main_interpreter', 'default', False)
        configuration.set(
            'main_interpreter', 'executable', get_conda_test_env())
    else:
        configuration.set('main_interpreter', 'default', True)
        configuration.set('main_interpreter', 'executable', '')

    # Conf css_path in the Appeareance plugin
    configuration.set('appearance', 'css_path', CSS_PATH)

    # Create the console and a new client and set environment
    os.environ['IPYCONSOLE_TESTING'] = 'True'
    stdfile.IPYCONSOLE_TEST_DIR = test_dir
    stdfile.IPYCONSOLE_TEST_NO_STDERR = test_no_stderr
    window = MainWindowMock()
    console = IPythonConsole(parent=window, configuration=configuration)

    # connect to a debugger plugin
    debugger = Debugger(parent=window, configuration=configuration)

    def get_plugin(name):
        if name == Plugins.IPythonConsole:
            return console
        return None

    debugger.get_plugin = get_plugin
    debugger.on_ipython_console_available()
    console.on_initialize()
    console._register()
    console.create_new_client(is_pylab=is_pylab,
                              is_sympy=is_sympy,
                              is_cython=is_cython)
    window.setCentralWidget(console.get_widget())

    # Set exclamation mark to True
    configuration.set('debugger', 'pdb_use_exclamation_mark', True)

    if os.name == 'nt':
        qtbot.addWidget(window)

    with qtbot.waitExposed(window):
        window.resize(640, 480)
        window.show()

    # Wait until the window is fully up
    qtbot.waitUntil(lambda: console.get_current_shellwidget() is not None)
    shell = console.get_current_shellwidget()
    try:
        qtbot.waitUntil(lambda: shell._prompt_html is not None,
                        timeout=SHELL_TIMEOUT)
    except Exception:
        # Print content of shellwidget and close window
        print(console.get_current_shellwidget(
            )._control.toPlainText())
        client = console.get_current_client()
        if client.info_page != client.blank_page:
            print('info_page')
            print(client.info_page)
        raise

    # Check for thread or open file leaks
    known_leak = request.node.get_closest_marker('known_leak')

    if os.name != 'nt' and not known_leak:
        # _DummyThread are created if current_thread() is called from them.
        # They will always leak (From python doc) so we ignore them.
        init_threads = [
            repr(thread) for thread in threading.enumerate()
            if not isinstance(thread, threading._DummyThread)]
        proc = psutil.Process()
        init_files = [repr(f) for f in proc.open_files()]
        init_subprocesses = [repr(f) for f in proc.children()]

    yield console

    # Print shell content if failed
    if request.node.rep_setup.passed:
        if request.node.rep_call.failed:
            # Print content of shellwidget and close window
            print(console.get_current_shellwidget(
                )._control.toPlainText())
            client = console.get_current_client()
            if client.info_page != client.blank_page:
                print('info_page')
                print(client.info_page)

    # Close
    console.on_close()
    os.environ.pop('IPYCONSOLE_TESTING')
    stdfile.IPYCONSOLE_TEST_DIR = None
    stdfile.IPYCONSOLE_TEST_NO_STDERR = False

    if os.name == 'nt' or known_leak:
        # Do not test for leaks
        return

    def show_diff(init_list, now_list, name):
        sys.stderr.write(f"Extra {name} before test:\n")
        for item in init_list:
            if item in now_list:
                now_list.remove(item)
            else:
                sys.stderr.write(item + "\n")
        sys.stderr.write(f"Extra {name} after test:\n")
        for item in now_list:
            sys.stderr.write(item + "\n")

    # The test is not allowed to open new files or threads.
    try:
        def threads_condition():
            threads = [
                thread for thread in threading.enumerate()
                if not isinstance(thread, threading._DummyThread)]
            return (len(init_threads) >= len(threads))

        qtbot.waitUntil(threads_condition, timeout=SHELL_TIMEOUT)
    except Exception:
        now_threads = [
            thread for thread in threading.enumerate()
            if not isinstance(thread, threading._DummyThread)]
        threads = [repr(t) for t in now_threads]
        show_diff(init_threads, threads, "thread")
        sys.stderr.write("Running Threads stacks:\n")
        now_thread_ids = [t.ident for t in now_threads]
        for thread_id, frame in sys._current_frames().items():
            if thread_id in now_thread_ids:
                sys.stderr.write("\nThread " + str(threads) + ":\n")
                traceback.print_stack(frame)
        raise

    try:
        # -1 from closed client
        qtbot.waitUntil(lambda: (
            len(init_subprocesses) - 1 >= len(proc.children())),
            timeout=SHELL_TIMEOUT)
    except Exception:
        subprocesses = [repr(f) for f in proc.children()]
        show_diff(init_subprocesses, subprocesses, "processes")
        raise

    try:
        qtbot.waitUntil(
            lambda: (len(init_files) >= len(proc.open_files())),
            timeout=SHELL_TIMEOUT)
    except Exception:
        files = [repr(f) for f in proc.open_files()]
        show_diff(init_files, files, "files")
        raise


# =============================================================================
# Tests
# =============================================================================
@flaky(max_runs=3)
@pytest.mark.external_interpreter
def test_banners(ipyconsole, qtbot):
    """Test that console banners are generated correctly."""
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control

    # Long banner
    text = control.toPlainText().splitlines()
    if "Update LANGUAGE_CODES" in text[0]:
        text = text[1:]
        while not text[0].strip():
            text = text[1:]
    py_ver = sys.version.splitlines()[0].strip()
    assert py_ver in text[0]  # Python version in first line
    assert 'license' in text[1]  # 'license' mention in second line
    assert '' == text[2]  # Third line is empty
    assert ipy_release.version in text[3]  # Fourth line is IPython

    # Short banner
    short_banner = shell.short_banner()
    py_ver = sys.version.split(' ')[0]
    expected = 'Python %s -- IPython %s' % (py_ver, ipy_release.version)
    assert expected == short_banner


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "function,signature,documentation",
    [("arange",
      ["start", "stop"],
      ["Return evenly spaced values within a given interval.<br>",
       "<br>Python built-in `range` function, but returns an ndarray ..."]),
     ("vectorize",
      ["pyfunc", "otype", "signature"],
      ["Generalized function class.<br>",
       "Define a vectorized function which takes a nested sequence ..."]),
     ("absolute",
      ["x", "/", "out"],
      ["Parameters<br>", "x : array_like ..."])]
    )
@pytest.mark.skipif(not os.name == 'nt',
                    reason="Times out on macOS and fails on Linux")
def test_get_calltips(ipyconsole, qtbot, function, signature, documentation):
    """Test that calltips show the documentation."""
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control

    # Import numpy
    with qtbot.waitSignal(shell.executed):
        shell.execute('import numpy as np')

    # Write an object in the console that should generate a calltip
    # and wait for the kernel to send its response.
    with qtbot.waitSignal(shell.kernel_client.shell_channel.message_received):
        qtbot.keyClicks(control, 'np.' + function + '(')

    # Wait a little bit for the calltip to appear
    qtbot.waitUntil(lambda: control.calltip_widget.isVisible())

    # Assert we displayed a calltip
    assert control.calltip_widget.isVisible()

    # Hide the calltip to avoid focus problems on Linux
    control.calltip_widget.hide()

    # Check spected elements for signature and documentation
    for element in signature:
        assert element in control.calltip_widget.text()
    for element in documentation:
        assert element in control.calltip_widget.text()


@flaky(max_runs=3)
@pytest.mark.auto_backend
@pytest.mark.skipif(
    running_in_ci() and not os.name == 'nt',
    reason="Times out on Linux and macOS")
def test_auto_backend(ipyconsole, qtbot):
    """Test that the automatic backend was set correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("ip = get_ipython(); ip.kernel.eventloop")

    # Assert there are no errors in the console and we set the right
    # backend.
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'NOTE' not in control.toPlainText()
    assert 'Error' not in control.toPlainText()
    assert 'loop_qt5' in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.tk_backend
@pytest.mark.skipif(
    running_in_ci() and not os.name == 'nt',
    reason="Times out on Linux and macOS")
def test_tk_backend(ipyconsole, qtbot):
    """Test that the Tkinter backend was set correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute("ip = get_ipython(); ip.kernel.eventloop")

    # Assert we set the right backend in the kernel.
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'loop_tk' in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.pylab_client
def test_pylab_client(ipyconsole, qtbot):
    """Test that the Pylab console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")

    # Assert there are no errors in the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'Error' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that `e` is still defined from numpy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'Error' not in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.sympy_client
@pytest.mark.xfail(parse_version('1.0') < parse_version(sympy.__version__) <
                   parse_version('1.2'),
                   reason="A bug with sympy 1.1.1 and IPython-Qtconsole")
def test_sympy_client(ipyconsole, qtbot):
    """Test that the SymPy console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("x")

    # Assert there are no errors in the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'NameError' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that `e` is still defined from sympy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("x")

    # Assert there are no errors after resetting the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'NameError' not in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.cython_client
@pytest.mark.skipif(
    (not sys.platform.startswith('linux') or
     parse_version(ipy_release.version) == parse_version('7.11.0')),
    reason="It only works reliably on Linux and fails for IPython 7.11.0")
def test_cython_client(ipyconsole, qtbot):
    """Test that the Cython console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
        shell.execute("%%cython\n"
                      "cdef int ctest(int x, int y):\n"
                      "    return x + y")

    # Assert there are no errors in the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'Error' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that cython is still enabled after reset
    with qtbot.waitSignal(shell.executed, timeout=SHELL_TIMEOUT):
        shell.execute("%%cython\n"
                      "cdef int ctest(int x, int y):\n"
                      "    return x + y")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'Error' not in control.toPlainText()


@flaky(max_runs=3)
def test_tab_rename_for_slaves(ipyconsole, qtbot):
    """Test slave clients are renamed correctly."""
    cf = ipyconsole.get_current_client().connection_file
    ipyconsole.create_client_for_kernel(cf)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    # Rename slave
    ipyconsole.get_widget().rename_tabs_after_change('foo')

    # Assert both clients have the same name
    assert 'foo' in ipyconsole.get_clients()[0].get_name()
    assert 'foo' in ipyconsole.get_clients()[1].get_name()


@flaky(max_runs=3)
def test_no_repeated_tabs_name(ipyconsole, qtbot):
    """Test that tabs can't have repeated given names."""
    # Rename first client
    ipyconsole.get_widget().rename_tabs_after_change('foo')

    # Create a new client and try to rename it
    ipyconsole.create_new_client()
    ipyconsole.get_widget().rename_tabs_after_change('foo')

    # Assert the rename didn't take place
    client_name = ipyconsole.get_current_client().get_name()
    assert '2' in client_name


@flaky(max_runs=3)
@pytest.mark.skipif(
    running_in_ci() and sys.platform == 'darwin',
    reason="Hangs sometimes on macOS")
@pytest.mark.skipif(os.name == 'nt' and running_in_ci_with_conda(),
                    reason="It hangs on Windows CI using conda")
def test_tabs_preserve_name_after_move(ipyconsole, qtbot):
    """Test that tabs preserve their names after they are moved."""
    # Create a new client
    ipyconsole.create_new_client()

    # Move tabs
    ipyconsole.get_widget().tabwidget.tabBar().moveTab(0, 1)

    # Assert the second client is in the first position
    client_name = ipyconsole.get_clients()[0].get_name()
    assert '2' in client_name


@flaky(max_runs=3)
def test_conf_env_vars(ipyconsole, qtbot):
    """Test that kernels have env vars set by our kernel spec."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Get a CONF env var
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; a = os.environ.get('SPY_SYMPY_O')")

    # Assert we get the assigned value correctly
    assert shell.get_value('a') == 'False'


@flaky(max_runs=3)
@pytest.mark.no_stderr_file
def test_no_stderr_file(ipyconsole, qtbot):
    """Test that consoles can run without an stderr."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Execute a simple assignment
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 1')

    # Assert we get the assigned value correctly
    assert shell.get_value('a') == 1


@pytest.mark.non_ascii_dir
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="It fails on Windows")
def test_non_ascii_stderr_file(ipyconsole, qtbot):
    """Test the creation of a console with a stderr file in a non-ascii dir."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Execute a simple assignment
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 1')

    # Assert we get the assigned value
    assert shell.get_value('a') == 1


@flaky(max_runs=3)
@pytest.mark.skipif(PY2 and sys.platform == 'darwin',
                    reason="It hangs frequently on Python 2.7 and macOS")
def test_console_import_namespace(ipyconsole, qtbot):
    """Test an import of the form 'from foo import *'."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Import numpy
    with qtbot.waitSignal(shell.executed):
        shell.execute('from numpy import *')

    # Assert we get the e value correctly
    assert shell.get_value('e') == 2.718281828459045


@flaky(max_runs=3)
def test_console_disambiguation(ipyconsole, qtbot):
    """Test the disambiguation of dedicated consoles."""
    # Create directories and file for TEMP_DIRECTORY/a/b/c.py
    # and TEMP_DIRECTORY/a/d/c.py
    dir_b = osp.join(TEMP_DIRECTORY, 'a', 'b')
    filename_b =  osp.join(dir_b, 'c.py')
    if not osp.isdir(dir_b):
        os.makedirs(dir_b)
    if not osp.isfile(filename_b):
        file_c = open(filename_b, 'w+')
        file_c.close()
    dir_d = osp.join(TEMP_DIRECTORY, 'a', 'd')
    filename_d =  osp.join(dir_d, 'c.py')
    if not osp.isdir(dir_d):
        os.makedirs(dir_d)
    if not osp.isfile(filename_d):
        file_e = open(filename_d, 'w+')
        file_e.close()

    # Create new client and assert name without disambiguation
    ipyconsole.create_client_for_file(filename_b)
    client = ipyconsole.get_current_client()
    assert client.get_name() == 'c.py/A'

    # Create new client and assert name with disambiguation
    ipyconsole.create_client_for_file(filename_d)
    client = ipyconsole.get_current_client()
    assert client.get_name() == 'c.py - d/A'
    ipyconsole.get_widget().tabwidget.setCurrentIndex(1)
    client = ipyconsole.get_current_client()
    assert client.get_name() == 'c.py - b/A'


@flaky(max_runs=3)
def test_console_coloring(ipyconsole, qtbot):
    """Test that console gets the same coloring present in the Editor."""
    config_options = ipyconsole.get_widget().config_options()

    syntax_style = config_options.JupyterWidget.syntax_style
    style_sheet = config_options.JupyterWidget.style_sheet
    console_font_color = get_console_font_color(syntax_style)
    console_background_color = get_console_background_color(style_sheet)

    selected_color_scheme = ipyconsole.get_conf(
        'selected', section='appearance')
    color_scheme = get_color_scheme(selected_color_scheme)
    editor_background_color = color_scheme['background']
    editor_font_color = color_scheme['normal'][0]

    console_background_color = console_background_color.replace("'", "")
    editor_background_color = editor_background_color.replace("'", "")
    console_font_color = console_font_color.replace("'", "")
    editor_font_color = editor_font_color.replace("'", "")

    assert console_background_color.strip() == editor_background_color.strip()
    assert console_font_color.strip() == editor_font_color.strip()


@flaky(max_runs=3)
def test_set_cwd(ipyconsole, qtbot, tmpdir):
    """Test kernel when changing cwd."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # spyder-ide/spyder#6451.
    savetemp = shell._cwd
    tempdir = to_text_string(tmpdir.mkdir("queen's"))
    shell.set_cwd(tempdir)

    # Get current directory.
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; cwd = os.getcwd()")

    # Assert we get the assigned value correctly
    assert shell.get_value('cwd') == tempdir

    # Restore original.
    shell.set_cwd(savetemp)


@flaky(max_runs=3)
def test_get_cwd(ipyconsole, qtbot, tmpdir):
    """Test current working directory."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # spyder-ide/spyder#6451.
    savetemp = shell._cwd
    tempdir = to_text_string(tmpdir.mkdir("queen's"))
    assert shell._cwd != tempdir

    # Need to escape \ on Windows.
    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\", u"\\\\")

    # Change directory in the console.
    with qtbot.waitSignal(shell.executed):
        shell.execute(u"import os; os.chdir(u'''{}''')".format(tempdir))

    # Ask for directory.
    with qtbot.waitSignal(shell.sig_working_directory_changed):
        shell.update_cwd()

    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\\\", u"\\")

    assert shell._cwd == tempdir

    shell.set_cwd(savetemp)


@flaky(max_runs=3)
def test_request_env(ipyconsole, qtbot):
    """Test that getting env vars from the kernel is working as expected."""
    shell = ipyconsole.get_current_shellwidget()

    # Add a new entry to os.environ
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; os.environ['FOO'] = 'bar'" )

    # Ask for os.environ contents
    with qtbot.waitSignal(shell.sig_show_env) as blocker:
        shell.request_env()

    # Get env contents from the signal
    env_contents = blocker.args[0]

    # Assert that our added entry is part of os.environ
    assert env_contents['FOO'] == 'bar'


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt',
                    reason="Fails due to differences in path handling")
def test_request_syspath(ipyconsole, qtbot, tmpdir):
    """
    Test that getting sys.path contents from the kernel is working as
    expected.
    """
    shell = ipyconsole.get_current_shellwidget()

    # Add a new entry to sys.path
    with qtbot.waitSignal(shell.executed):
        tmp_dir = to_text_string(tmpdir)
        shell.execute("import sys; sys.path.append('%s')" % tmp_dir)

    # Ask for sys.path contents
    with qtbot.waitSignal(shell.sig_show_syspath) as blocker:
        shell.request_syspath()

    # Get sys.path contents from the signal
    syspath_contents = blocker.args[0]

    # Assert that our added entry is part of sys.path
    assert tmp_dir in syspath_contents


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It doesn't work on Windows")
def test_save_history_dbg(ipyconsole, qtbot):
    """Test that browsing command history is working while debugging."""
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Enter an expression
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, 'aa = 10')
        qtbot.keyClick(control, Qt.Key_Enter)

    # Add a pdb command to make sure it is not saved
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!u')
        qtbot.keyClick(control, Qt.Key_Enter)

    # Add an empty line to make sure it is not saved
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Clear console (for some reason using shell.clear_console
    # doesn't work here)
    shell.reset(clear=True)
    qtbot.waitUntil(lambda: shell.is_waiting_pdb_input())

    # Make sure we are debugging
    assert shell.is_waiting_pdb_input()

    # Press Up arrow button and assert we get the last
    # introduced command
    qtbot.keyClick(control, Qt.Key_Up)
    assert 'aa = 10' in control.toPlainText()

    # Open new widget
    ipyconsole.create_new_client()

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Press Up arrow button and assert we get the last
    # introduced command
    qtbot.keyClick(control, Qt.Key_Up)
    assert 'aa = 10' in control.toPlainText()

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    # Add a multiline statment and ckeck we can browse it correctly
    shell._pdb_history.append('if True:\n    print(1)')
    shell._pdb_history.append('print(2)')
    shell._pdb_history.append('if True:\n    print(10)')
    shell._pdb_history_index = len(shell._pdb_history)
    # The continuation prompt is here
    qtbot.keyClick(control, Qt.Key_Up)
    assert '...:     print(10)' in control.toPlainText()
    shell._control.set_cursor_position(shell._control.get_position('eof') - 25)
    qtbot.keyClick(control, Qt.Key_Up)
    assert '...:     print(1)' in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(PY2 or IPython.version_info < (7, 17),
                    reason="insert is not the same in py2")
def test_dbg_input(ipyconsole, qtbot):
    """Test that spyder doesn't send pdb commands to unrelated input calls."""
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Debug with input
    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print('Hello', input('name'))")

    # Reach the 'name' input
    shell.pdb_execute('!n')
    qtbot.wait(100)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'name')

    # Execute some code and make sure that it doesn't work
    # as this is not a pdb prompt
    shell.pdb_execute('!n')
    shell.pdb_execute('aa = 10')
    qtbot.wait(500)
    assert control.toPlainText().split()[-1] == 'name'
    shell.kernel_client.input('test')
    qtbot.waitUntil(lambda: 'Hello test' in control.toPlainText())


@flaky(max_runs=3)
@pytest.mark.skipif(PY2, reason="It doesn't work on PY2")
def test_unicode_vars(ipyconsole, qtbot):
    """
    Test that the Variable Explorer Works with unicode variables.
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Set value for a Unicode variable
    with qtbot.waitSignal(shell.executed):
        shell.execute('д = 10')

    # Assert we get its value correctly
    assert shell.get_value('д') == 10

    # Change its value and verify
    shell.set_value('д', 20)
    qtbot.waitUntil(lambda: shell.get_value('д') == 20)
    assert shell.get_value('д') == 20


@flaky(max_runs=3)
def test_read_stderr(ipyconsole, qtbot):
    """
    Test the read operation of the stderr file of the kernel
    """
    client = ipyconsole.get_current_client()

    # Set contents of the stderr file of the kernel
    content = 'Test text'
    stderr_file = client.stderr_obj.filename
    codecs.open(stderr_file, 'w', 'cp437').write(content)
    # Assert that content is correct
    assert content == client.stderr_obj.get_contents()


@flaky(max_runs=10)
@pytest.mark.no_xvfb
@pytest.mark.skipif(running_in_ci() and os.name == 'nt',
                    reason="Times out on Windows")
def test_values_dbg(ipyconsole, qtbot):
    """
    Test that getting, setting, copying and removing values is working while
    debugging.
    """
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Get value
    with qtbot.waitSignal(shell.executed):
        shell.execute('aa = 10')

    assert 'aa = 10' in control.toPlainText()

    assert shell.get_value('aa') == 10

    # Set value
    shell.set_value('aa', 20)
    qtbot.waitUntil(lambda: shell.get_value('aa') == 20)
    assert shell.get_value('aa') == 20

    # Copy value
    shell.copy_value('aa', 'bb')
    qtbot.waitUntil(lambda: shell.get_value('bb') == 20)
    assert shell.get_value('bb') == 20

    # Remove value
    shell.remove_value('aa')

    def is_defined(val):
        try:
            shell.get_value(val)
            return True
        except KeyError:
            return False

    qtbot.waitUntil(lambda: not is_defined('aa'))
    with qtbot.waitSignal(shell.executed):
        shell.execute('aa')
    # Wait until the message is recieved
    assert "*** NameError: name 'aa' is not defined" in control.toPlainText()


@flaky(max_runs=3)
def test_execute_events_dbg(ipyconsole, qtbot):
    """Test execute events while debugging"""

    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Import Matplotlib
    with qtbot.waitSignal(shell.executed):
        shell.execute('import matplotlib.pyplot as plt')

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Set processing events to True
    ipyconsole.set_conf('pdb_execute_events', True, section='debugger')
    shell.call_kernel(interrupt=True).set_pdb_configuration({
        'pdb_execute_events': True
    })

    # Test reset magic
    qtbot.keyClicks(control, 'plt.plot(range(10))')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1

    # Set processing events to False
    ipyconsole.set_conf('pdb_execute_events', False, section='debugger')
    shell.call_kernel(interrupt=True).set_pdb_configuration({
        'pdb_execute_events': False
    })

    # Test reset magic
    qtbot.keyClicks(control, 'plt.plot(range(10))')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that there's no new plots in the console
    assert shell._control.toHtml().count('img src') == 1

    # Test if the plot is shown with plt.show()
    qtbot.keyClicks(control, 'plt.show()')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that there's a new plots in the console
    assert shell._control.toHtml().count('img src') == 2


@flaky(max_runs=3)
def test_run_doctest(ipyconsole, qtbot):
    """
    Test that doctests can be run without problems
    """
    shell = ipyconsole.get_current_shellwidget()

    code = dedent('''
    def add(x, y):
        """
        >>> add(1, 2)
        3
        >>> add(5.1, 2.2)
        7.3
        """
        return x + y
    ''')

    # Run code
    with qtbot.waitSignal(shell.executed):
        shell.execute(code)

    # Import doctest
    with qtbot.waitSignal(shell.executed):
        shell.execute('import doctest')

    # Run doctest
    with qtbot.waitSignal(shell.executed):
        shell.execute('doctest.testmod()')

    # Assert that doctests were run correctly
    assert "TestResults(failed=0, attempted=2)" in shell._control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt' or (PY2 and PYQT5),
                    reason="It times out frequently")
def test_mpl_backend_change(ipyconsole, qtbot):
    """
    Test that Matplotlib backend is changed correctly when
    using the %matplotlib magic
    """
    shell = ipyconsole.get_current_shellwidget()

    # Import Matplotlib
    with qtbot.waitSignal(shell.executed):
        shell.execute('import matplotlib.pyplot as plt')

    # Generate a plot
    with qtbot.waitSignal(shell.executed):
        shell.execute('plt.plot(range(10))')

    # Change backends
    with qtbot.waitSignal(shell.executed):
        shell.execute('%matplotlib tk')

    # Generate another plot
    with qtbot.waitSignal(shell.executed):
        shell.execute('plt.plot(range(10))')

    # Assert that there's a single inline plot in the console
    assert shell._control.toHtml().count('img src') == 1



@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It doesn't work on Windows")
def test_clear_and_reset_magics_dbg(ipyconsole, qtbot):
    """
    Test that clear and reset magics are working while debugging
    """
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Test clear magic
    shell.clear_console()
    qtbot.waitUntil(lambda: '\nIPdb [2]: ' == control.toPlainText())

    # Test reset magic
    qtbot.keyClicks(control, 'bb = 10')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    assert shell.get_value('bb') == 10

    shell.reset_namespace()
    qtbot.wait(1000)

    qtbot.keyClicks(control, 'bb')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    assert "*** NameError: name 'bb' is not defined" in control.toPlainText()


@flaky(max_runs=3)
def test_restart_kernel(ipyconsole, mocker, qtbot):
    """
    Test that kernel is restarted correctly
    """
    # Mock method we want to check
    mocker.patch.object(ClientWidget, "_show_mpl_backend_errors")

    ipyconsole.create_new_client()

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Do an assignment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Write something to stderr to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; sys.__stderr__.write("HEL"+"LO")')

    qtbot.waitUntil(
        lambda: 'HELLO' in shell._control.toPlainText(), timeout=SHELL_TIMEOUT)

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    ipyconsole.restart_kernel()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    assert 'Restarting kernel...' in shell._control.toPlainText()
    assert 'HELLO' not in shell._control.toPlainText()
    assert not shell.is_defined('a')

    # Check that we try to show Matplotlib backend errors at the beginning and
    # after the restart.
    assert ClientWidget._show_mpl_backend_errors.call_count == 2


@flaky(max_runs=3)
def test_load_kernel_file_from_id(ipyconsole, qtbot):
    """
    Test that a new client is created using its id
    """
    client = ipyconsole.get_current_client()

    connection_file = osp.basename(client.connection_file)
    id_ = connection_file.split('kernel-')[-1].split('.json')[0]

    ipyconsole.create_client_for_kernel(id_)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    new_client = ipyconsole.get_clients()[1]
    assert new_client.id_ == dict(int_id='1', str_id='B')


@flaky(max_runs=3)
def test_load_kernel_file_from_location(ipyconsole, qtbot, tmpdir):
    """
    Test that a new client is created using a connection file
    placed in a different location from jupyter_runtime_dir
    """
    client = ipyconsole.get_current_client()

    fname = osp.basename(client.connection_file)
    connection_file = to_text_string(tmpdir.join(fname))
    shutil.copy2(client.connection_file, connection_file)

    ipyconsole.create_client_for_kernel(connection_file)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    assert len(ipyconsole.get_clients()) == 2


@flaky(max_runs=3)
def test_load_kernel_file(ipyconsole, qtbot, tmpdir):
    """
    Test that a new client is created using the connection file
    of an existing client
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()

    ipyconsole.create_client_for_kernel(client.connection_file)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    new_client = ipyconsole.get_clients()[1]
    new_shell = new_client.shellwidget
    qtbot.waitUntil(lambda: new_shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(new_shell.executed):
        new_shell.execute('a = 10')

    assert new_client.id_ == dict(int_id='1', str_id='B')
    assert shell.get_value('a') == new_shell.get_value('a')


@flaky(max_runs=3)
def test_sys_argv_clear(ipyconsole, qtbot):
    """Test that sys.argv is cleared up correctly"""
    shell = ipyconsole.get_current_shellwidget()

    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")

    assert argv == ['']


@flaky(max_runs=5)
@pytest.mark.skipif(os.name == 'nt', reason="Fails sometimes on Windows")
def test_set_elapsed_time(ipyconsole, qtbot):
    """Test that the IPython console elapsed timer is set correctly."""
    client = ipyconsole.get_current_client()

    # Show time label.
    main_widget = ipyconsole.get_widget()
    main_widget.set_show_elapsed_time_current_client(True)

    # Set time to 2 minutes ago.
    client.t0 -= 120
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        client.timer.timeout.connect(client.show_time)
        client.timer.start(1000)
    assert ('00:02:00' in main_widget.time_label.text() or
            '00:02:01' in main_widget.time_label.text())

    # Wait for a second to pass, to ensure timer is counting up
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        pass
    assert ('00:02:01' in main_widget.time_label.text() or
            '00:02:02' in main_widget.time_label.text())

    # Make previous time later than current time.
    client.t0 += 2000
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        pass
    assert '00:00:00' in main_widget.time_label.text()

    client.timer.timeout.disconnect(client.show_time)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_stderr_file_is_removed_one_kernel(ipyconsole, qtbot, monkeypatch):
    """Test that consoles removes stderr when client is closed."""
    client = ipyconsole.get_current_client()

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, 'question',
                        classmethod(lambda *args: QMessageBox.Yes))
    assert osp.exists(client.stderr_obj.filename)
    ipyconsole.close_client(client=client)
    assert not osp.exists(client.stderr_obj.filename)


@flaky(max_runs=3)
@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason="Doesn't work on Windows and hangs sometimes on Mac")
def test_stderr_file_is_removed_two_kernels(ipyconsole, qtbot, monkeypatch):
    """Test that console removes stderr when client and related clients
    are closed."""
    client = ipyconsole.get_current_client()

    # New client with the same kernel
    ipyconsole.create_client_for_kernel(client.connection_file)
    assert len(ipyconsole.get_widget().get_related_clients(client)) == 1
    other_client = ipyconsole.get_widget().get_related_clients(client)[0]
    assert client.stderr_obj.filename == other_client.stderr_obj.filename

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, 'question',
                        classmethod(lambda *args: QMessageBox.Yes))
    assert osp.exists(client.stderr_obj.filename)
    ipyconsole.close_client(client=client)
    assert not osp.exists(client.stderr_obj.filename)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_stderr_file_remains_two_kernels(ipyconsole, qtbot, monkeypatch):
    """Test that console doesn't remove stderr when a related client is not
    closed."""
    client = ipyconsole.get_current_client()

    # New client with the same kernel
    ipyconsole.create_client_for_kernel(client.connection_file)

    assert len(ipyconsole.get_widget().get_related_clients(client)) == 1
    other_client = ipyconsole.get_widget().get_related_clients(client)[0]
    assert client.stderr_obj.filename == other_client.stderr_obj.filename

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, "question",
                        classmethod(lambda *args: QMessageBox.No))
    assert osp.exists(client.stderr_obj.filename)
    ipyconsole.close_client(client=client)
    assert osp.exists(client.stderr_obj.filename)


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="Fails sometimes on macOS")
def test_kernel_crash(ipyconsole, qtbot):
    """Test that we show an error message when a kernel crash occurs."""
    # Create an IPython kernel config file with a bad config
    ipy_kernel_cfg = osp.join(get_ipython_dir(), 'profile_default',
                              'ipython_kernel_config.py')
    try:
        with open(ipy_kernel_cfg, 'w') as f:
            # This option must be a string, not an int
            f.write("c.InteractiveShellApp.extra_extension = 1")

        ipyconsole.get_widget().close_cached_kernel()
        ipyconsole.create_new_client()

        # Assert that the console is showing an error
        error_client = ipyconsole.get_clients()[-1]
        qtbot.waitUntil(lambda: bool(error_client.error_text), timeout=6000)
        assert error_client.error_text

        # Assert the error contains the text we expect
        webview = error_client.infowidget
        if WEBENGINE:
            webpage = webview.page()
        else:
            webpage = webview.page().mainFrame()

        qtbot.waitUntil(
            lambda: check_text(webpage, "Bad config encountered"),
            timeout=6000)
    finally:
        # Remove bad kernel config file
        os.remove(ipy_kernel_cfg)


@flaky(max_runs=3)
@pytest.mark.skipif(not os.name == 'nt', reason="Only necessary on Windows")
def test_remove_old_std_files(ipyconsole, qtbot):
    """Test that we are removing old std files."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Create empty std files in our temp dir to see if they are removed
    # correctly.
    tmpdir = get_temp_dir()
    open(osp.join(tmpdir, 'foo.stderr'), 'a').close()
    open(osp.join(tmpdir, 'foo.stdout'), 'a').close()

    # Assert that only old std files are removed
    ipyconsole._remove_old_std_files()
    assert not osp.isfile(osp.join(tmpdir, 'foo.stderr'))
    assert not osp.isfile(osp.join(tmpdir, 'foo.stdout'))

    # The current kernel std files should be present
    for fname in glob.glob(osp.join(tmpdir, '*')):
        if osp.basename(fname) != 'test':
            assert osp.basename(fname).startswith('kernel')
            assert any(
                [osp.basename(fname).endswith(ext)
                 for ext in ('.stderr', '.stdout', '.fault')]
            )


@flaky(max_runs=3)
@pytest.mark.use_startup_wdir
def test_startup_working_directory(ipyconsole, qtbot):
    """
    Test that the fixed startup working directory option works as expected.
    """
    shell = ipyconsole.get_current_shellwidget()
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os; cwd = os.getcwd()')

    current_wdir = shell.get_value('cwd')
    folders = osp.split(current_wdir)
    assert folders[-1] == NEW_DIR


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux') or PY2,
                    reason="It only works on Linux with python 3.")
def test_console_complete(ipyconsole, qtbot, tmpdir):
    """Test code completions in the console."""
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    def check_value(name, value):
        try:
            return shell.get_value(name) == value
        except KeyError:
            return False

    # test complete with one result
    with qtbot.waitSignal(shell.executed):
        shell.execute('cbs = 1')
    qtbot.waitUntil(lambda: check_value('cbs', 1))
    qtbot.wait(500)

    qtbot.keyClicks(control, 'cb')
    qtbot.keyClick(control, Qt.Key_Tab)
    # Jedi completion takes time to start up the first time
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'cbs',
                    timeout=6000)

    # test complete with several result
    with qtbot.waitSignal(shell.executed):
        shell.execute('cbba = 1')
    qtbot.waitUntil(lambda: check_value('cbba', 1))
    qtbot.keyClicks(control, 'cb')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(shell._completion_widget.isVisible)
    # cbs is another solution, so not completed yet
    assert control.toPlainText().split()[-1] == 'cb'
    qtbot.keyClick(shell._completion_widget, Qt.Key_Enter)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'cbba')

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Test complete in debug mode
    # check abs is completed twice (as the cursor moves)
    qtbot.keyClicks(control, 'ab')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'abs')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # A second time to check a function call doesn't cause a problem
    qtbot.keyClicks(control, 'print(ab')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(
        lambda: control.toPlainText().split()[-1] == 'print(abs')
    qtbot.keyClicks(control, ')')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Enter an expression
    qtbot.keyClicks(control, 'baab = 10')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(100)
    qtbot.waitUntil(lambda: check_value('baab', 10))

    # Check baab is completed
    qtbot.keyClicks(control, 'baa')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'baab')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Check the completion widget is shown for abba, abs
    qtbot.keyClicks(control, 'abba = 10')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(100)
    qtbot.waitUntil(lambda: check_value('abba', 10))
    qtbot.keyClicks(control, 'ab')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(shell._completion_widget.isVisible)
    assert control.toPlainText().split()[-1] == 'ab'
    qtbot.keyClick(shell._completion_widget, Qt.Key_Enter)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'abba')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Create a class
    qtbot.keyClicks(control, 'class A(): baba = 1')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(100)
    qtbot.waitUntil(lambda: shell.is_defined('A'))
    qtbot.keyClicks(control, 'a = A()')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(100)
    qtbot.waitUntil(lambda: shell.is_defined('a'))

    # Check we can complete attributes
    qtbot.keyClicks(control, 'a.ba')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'a.baba')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Check we can complete pdb command names
    qtbot.keyClicks(control, '!longl')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == '!longlist')

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Check we can use custom complete for pdb
    test_file = tmpdir.join('test.py')
    test_file.write('stuff\n')
    # Set a breakpoint in the new file
    qtbot.keyClicks(control, '!b ' + str(test_file) + ':1')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    # Check we can complete the breakpoint number
    qtbot.keyClicks(control, '!ignore ')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == '1')


@flaky(max_runs=10)
def test_pdb_multiline(ipyconsole, qtbot):
    """Test entering a multiline statment into pdb"""
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    assert '\nIPdb [' in control.toPlainText()

    # Test reset magic
    qtbot.keyClicks(control, 'if True:')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)
    qtbot.keyClicks(control, 'bb = 10')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    assert shell.get_value('bb') == 10
    assert "if True:\n     ...:     bb = 10\n" in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "show_lib", [True, False])
def test_pdb_ignore_lib(ipyconsole, qtbot, show_lib):
    """Test that pdb can avoid closed files."""
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Tests assume inline backend
    qtbot.wait(1000)
    ipyconsole.set_conf('pdb_ignore_lib', not show_lib, section="debugger")
    qtbot.wait(1000)
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            '"value = " + str(get_ipython().pdb_session.pdb_ignore_lib)')
    assert "value = " + str(not show_lib) in control.toPlainText()

    qtbot.keyClicks(control, '!s')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    qtbot.keyClicks(control, '!q')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    if show_lib:
        assert 'iostream.py' in control.toPlainText()
    else:
        assert 'iostream.py' not in control.toPlainText()
    ipyconsole.set_conf('pdb_ignore_lib', True, section="debugger")


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Times out on macOS")
def test_calltip(ipyconsole, qtbot):
    """
    Test Calltip.

    See spyder-ide/spyder#10842
    """
    shell = ipyconsole.get_current_shellwidget()

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = {"a": 1}')
    qtbot.keyClicks(control, 'a.keys(', delay=100)
    qtbot.wait(1000)
    assert control.calltip_widget.isVisible()


@flaky(max_runs=3)
@pytest.mark.order(1)
@pytest.mark.test_environment_interpreter
def test_conda_env_activation(ipyconsole, qtbot):
    """
    Test that the conda environment associated with an external interpreter
    is activated before a kernel is created for it.
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Get conda activation environment variable
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "import os; conda_prefix = os.environ.get('CONDA_PREFIX')")

    expected_output = get_conda_test_env().replace('\\', '/')
    if is_conda_env(expected_output):
        output = shell.get_value('conda_prefix').replace('\\', '/')
        assert expected_output == output


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="no SIGTERM on Windows")
def test_kernel_kill(ipyconsole, qtbot):
    """
    Test that the kernel correctly restarts after a kill.
    """
    shell = ipyconsole.get_current_shellwidget()
    # Wait for the restarter to start
    qtbot.wait(3000)
    crash_string = 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)'
    # Check only one comm is open
    old_open_comms = list(shell.spyder_kernel_comm._comms.keys())
    assert len(old_open_comms) == 1
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=30000):
        shell.execute(crash_string)
    assert crash_string in shell._control.toPlainText()
    assert "Restarting kernel..." in shell._control.toPlainText()
    # Check a new comm replaced the old one
    new_open_comms = list(shell.spyder_kernel_comm._comms.keys())
    assert len(new_open_comms) == 1
    assert old_open_comms[0] != new_open_comms[0]
    # Wait until the comm replies
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_comm._comms[new_open_comms[0]][
            'status'] == 'ready')
    assert shell.spyder_kernel_comm._comms[new_open_comms[0]][
        'status'] == 'ready'


@flaky(max_runs=3)
@pytest.mark.parametrize("spyder_pythonpath", [True, False])
def test_wrong_std_module(ipyconsole, qtbot, tmpdir, spyder_pythonpath):
    """
    Test that a file with the same name of a standard library module in
    the current working directory doesn't break the console.
    """
    # Create an empty file called random.py in the cwd
    if spyder_pythonpath:
        wrong_random_mod = tmpdir.join('random.py')
        wrong_random_mod.write('')
        wrong_random_mod = str(wrong_random_mod)
        ipyconsole.set_conf('spyder_pythonpath', [str(tmpdir)], section='main')
    else:
        wrong_random_mod = osp.join(os.getcwd(), 'random.py')
        with open(wrong_random_mod, 'w') as f:
            f.write('')

    # Create a new client to see if its kernel starts despite the
    # faulty module.
    ipyconsole.create_new_client()

    # A prompt should be created if the kernel didn't crash.
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Assert the extra path from spyder_pythonpath was added
    if spyder_pythonpath:
        check_sys_path = (
            "import sys; path_added = r'{}' in sys.path".format(str(tmpdir))
        )
        with qtbot.waitSignal(shell.sig_prompt_ready, timeout=30000):
            shell.execute(check_sys_path)
        assert shell.get_value('path_added')

    # Remove wrong module
    os.remove(wrong_random_mod)

    # Restore CONF
    ipyconsole.set_conf('spyder_pythonpath', [], section='main')


@flaky(max_runs=3)
@pytest.mark.known_leak
@pytest.mark.skipif(os.name == 'nt', reason="no SIGTERM on Windows")
def test_kernel_restart_after_manual_restart_and_crash(ipyconsole, qtbot):
    """
    Test that the kernel restarts correctly after being restarted
    manually and then it crashes.

    This is a regresion for spyder-ide/spyder#12972.
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    ipyconsole.restart_kernel()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Wait for the restarter to start
    qtbot.wait(3000)

    # Generate a crash
    crash_string = 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)'
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=30000):
        shell.execute(crash_string)
    assert crash_string in shell._control.toPlainText()

    # Evaluate an expression to be sure the restart was successful
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')
    assert shell.is_defined('a')

    # Wait until the comm replies
    open_comms = list(shell.spyder_kernel_comm._comms.keys())
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_comm._comms[open_comms[0]][
            'status'] == 'ready')


@flaky(max_runs=3)
def test_stderr_poll(ipyconsole, qtbot):
    """Test if the content of stderr is printed to the console."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            'import sys; print("test_" + "test", file=sys.__stderr__)')

    # Wait for the poll
    qtbot.waitUntil(lambda: "test_test" in ipyconsole.get_widget(
        ).get_focus_widget().toPlainText())
    assert "test_test" in ipyconsole.get_widget(
        ).get_focus_widget().toPlainText()
    # Write a second time, makes sure it is not duplicated
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            'import sys; print("test_" + "test", file=sys.__stderr__)')
    # Wait for the poll
    qtbot.waitUntil(lambda: ipyconsole.get_widget().get_focus_widget(
        ).toPlainText().count("test_test") == 2)
    assert ipyconsole.get_widget().get_focus_widget().toPlainText(
        ).count("test_test") == 2


@flaky(max_runs=3)
def test_stdout_poll(ipyconsole, qtbot):
    """Test if the content of stdout is printed to the console."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; print("test_test", file=sys.__stdout__)')

    # Wait for the poll
    qtbot.waitUntil(lambda: "test_test" in ipyconsole.get_widget(
        ).get_focus_widget().toPlainText(), timeout=5000)


@flaky(max_runs=10)
def test_startup_code_pdb(ipyconsole, qtbot):
    """Test that startup code for pdb works."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Run a line on startup
    ipyconsole.set_conf(
        'startup/pdb_run_lines',
        'abba = 12; print("Hello")'
    )

    shell.execute('%debug print()')
    qtbot.waitUntil(lambda: 'Hello' in control.toPlainText())

    # Verify that the line was executed
    assert shell.get_value('abba') == 12

    # Reset setting
    ipyconsole.set_conf('startup/pdb_run_lines', '')


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "backend",
    ['inline', 'qt5', 'tk', 'osx']
)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Hangs frequently on Mac")
def test_pdb_eventloop(ipyconsole, qtbot, backend):
    """Check if setting an event loop while debugging works."""
    # Skip failing tests
    if backend == 'tk' and os.name == 'nt':
        return
    if backend == 'osx' and sys.platform != "darwin":
        return
    if backend == 'qt5' and not os.name == "nt" and running_in_ci():
        return

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("%matplotlib " + backend)
    qtbot.wait(1000)

    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    with qtbot.waitSignal(shell.executed):
        shell.execute("print('Two: ' + str(1+1))")

    assert "Two: 2" in control.toPlainText()


@flaky(max_runs=3)
def test_recursive_pdb(ipyconsole, qtbot):
    """Check commands and code are separted."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("abab = 10")
    # Check that we can't use magic twice
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("%debug print()")
    assert "Please don't use '%debug'" in control.toPlainText()
    # Check we can enter the recursive debugger twice
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!debug print()")
    assert "(IPdb [1]):" in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!debug print()")
    assert "((IPdb [1])):" in control.toPlainText()
    # quit one layer
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!quit")
    assert control.toPlainText().split()[-2:] == ["(IPdb", "[2]):"]
    # Check completion works
    qtbot.keyClicks(control, 'aba')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'abab',
                    timeout=SHELL_TIMEOUT)
    # quit one layer
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!quit")
    assert control.toPlainText().split()[-2:] == ["IPdb", "[4]:"]
    # Check completion works
    qtbot.keyClicks(control, 'aba')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'abab',
                    timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!quit")
    with qtbot.waitSignal(shell.executed):
        shell.execute("1 + 1")
    assert control.toPlainText().split()[-2:] == ["In", "[3]:"]


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on windows")
def test_stop_pdb(ipyconsole, qtbot):
    """Test if we can stop pdb"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()
    stop_button = ipyconsole.get_widget().stop_button
    # Enter pdb
    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    # Start and interrupt a long execution
    shell.execute("import time; time.sleep(10)")
    qtbot.wait(500)
    with qtbot.waitSignal(shell.executed, timeout=1000):
        qtbot.mouseClick(stop_button, Qt.LeftButton)
    assert "KeyboardInterrupt" in control.toPlainText()
    # We are still in the debugger
    assert "IPdb [2]:" in control.toPlainText()
    assert "In [2]:" not in control.toPlainText()
    # Leave the debugger
    with qtbot.waitSignal(shell.executed):
        qtbot.mouseClick(stop_button, Qt.LeftButton)
    assert "In [2]:" in control.toPlainText()


@flaky(max_runs=3)
def test_code_cache(ipyconsole, qtbot):
    """
    Test that code sent to execute is properly cached
    and that the cache is emptied on interrupt.
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    def check_value(name, value):
        try:
            return shell.get_value(name) == value
        except KeyError:
            return False

    # Send two execute requests and make sure the second one is executed
    shell.execute('import time; time.sleep(.5)')
    with qtbot.waitSignal(shell.executed):
        shell.execute('var = 142')
    qtbot.wait(500)
    qtbot.waitUntil(lambda: check_value('var', 142))
    assert shell.get_value('var') == 142

    # Send two execute requests and cancel the second one
    shell.execute('import time; time.sleep(.5)')
    shell.execute('var = 1000')
    qtbot.wait(100)
    shell.interrupt_kernel()
    qtbot.wait(1000)
    # Make sure the value of var didn't change
    assert shell.get_value('var') == 142

    # Same for debugging
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    assert 'IPdb [' in shell._control.toPlainText()
    # Send two execute requests and make sure the second one is executed
    shell.execute('time.sleep(.5)')
    shell.execute('var = 318')
    qtbot.wait(500)
    qtbot.waitUntil(lambda: check_value('var', 318))
    assert shell.get_value('var') == 318

    # Send two execute requests and cancel the second one
    shell.execute('import time; time.sleep(.5)')
    shell.execute('var = 1000')
    qtbot.wait(100)
    shell.interrupt_kernel()
    qtbot.wait(1000)
    # Make sure the value of var didn't change
    assert shell.get_value('var') == 318


@flaky(max_runs=3)
@pytest.mark.skipif(PY2, reason="Doesn't work on Python 2.7")
def test_pdb_code_and_cmd_separation(ipyconsole, qtbot):
    """Check commands and code are separted."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    assert "Error" not in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")
    assert "name 'e' is not defined" in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.execute("!n")
    assert "--Return--" in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.execute("a")
    assert ("*** NameError: name 'a' is not defined"
            not in control.toPlainText())
    with qtbot.waitSignal(shell.executed):
        shell.execute("abba")
    assert "name 'abba' is not defined" in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.execute("!abba")
    assert "Unknown command 'abba'" in control.toPlainText()


@flaky(max_runs=3)
def test_breakpoint_builtin(ipyconsole, qtbot, tmpdir):
    """Check that the breakpoint builtin is working."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    # Code to run
    code = dedent("""
    print('foo')
    breakpoint()
    """)

    # Write code to file on disk
    file = tmpdir.join('test_breakpoint.py')
    file.write(code)

    # Run file
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"runfile(filename=r'{str(file)}')")

    # Assert we entered debugging after the print statement
    qtbot.wait(5000)
    assert 'foo' in control.toPlainText()
    assert 'IPdb [1]:' in control.toPlainText()


def test_pdb_out(ipyconsole, qtbot):
    """Test that browsing command history is working while debugging."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_widget().get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Generate some output
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute('a = 12 + 1; a')

    assert "[1]: 13" in control.toPlainText()

    # Generate hide output
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute('a = 14 + 1; a;')

    assert "[2]: 15" not in control.toPlainText()

    # Multiline
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute('a = 16 + 1\na')

    assert "[3]: 17" in control.toPlainText()

    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute('a = 18 + 1\na;')

    assert "[4]: 19" not in control.toPlainText()
    assert "IPdb [4]:" in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.auto_backend
@pytest.mark.skipif(
    running_in_ci() and not os.name == 'nt',
    reason="Times out on Linux and macOS")
def test_shutdown_kernel(ipyconsole, qtbot):
    """
    Check that the kernel is shutdown after creating plots with the
    automatic backend.

    This is a regression test for issue spyder-ide/spyder#17011
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    qtbot.wait(1000)

    # Create a Matplotlib plot
    with qtbot.waitSignal(shell.executed):
        shell.execute("import matplotlib.pyplot as plt; plt.plot(range(10))")
    qtbot.wait(1000)

    # Get kernel pid
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; pid = os.getpid()")
    qtbot.wait(1000)

    kernel_pid = shell.get_value('pid')

    # Close current tab
    ipyconsole.get_widget().close_client()

    # Wait until new client is created and previous kernel is shutdown
    qtbot.wait(5000)
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Detect if previous kernel was killed
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            f"import psutil; kernel_exists = psutil.pid_exists({kernel_pid})"
        )

    assert not shell.get_value('kernel_exists')


def test_pdb_comprehension_namespace(ipyconsole, qtbot, tmpdir):
    """Check that the debugger handles the namespace of a comprehension."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_widget().get_focus_widget()

    # Code to run
    code = "locals = 1\nx = [locals + i for i in range(2)]"

    # Write code to file on disk
    file = tmpdir.join('test_breakpoint.py')
    file.write(code)

    # Run file
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"debugfile(filename=r'{str(file)}')")

    # steps 4 times
    for i in range(4):
        with qtbot.waitSignal(shell.executed):
            shell.pdb_execute("s")
    assert "Error" not in control.toPlainText()

    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("print('test', locals + i + 10)")

    assert "Error" not in control.toPlainText()
    assert "test 11" in control.toPlainText()

    settings = {
     'check_all': False,
     'exclude_callables_and_modules': True,
     'exclude_capitalized': False,
     'exclude_private': True,
     'exclude_unsupported': False,
     'exclude_uppercase': True,
     'excluded_names': [],
     'minmax': False,
     'show_callable_attributes': True,
     'show_special_attributes': False}

    shell.call_kernel(
            interrupt=True
        ).set_namespace_view_settings(settings)
    namespace = shell.call_kernel(blocking=True).get_namespace_view()
    for key in namespace:
        assert "_spyderpdb" not in key


@flaky(max_runs=3)
@pytest.mark.auto_backend
@pytest.mark.skipif(
    running_in_ci() and not os.name == 'nt',
    reason="Times out on Linux and macOS")
def test_restart_intertactive_backend(ipyconsole):
    """
    Test that we ask for a restart after switching to a different interactive
    backend in preferences.
    """
    main_widget = ipyconsole.get_widget()
    main_widget.change_possible_restart_and_mpl_conf('pylab/backend', 3)
    assert bool(os.environ.get('BACKEND_REQUIRE_RESTART'))


@flaky(max_runs=3)
@pytest.mark.no_web_widgets
def test_no_infowidget(ipyconsole):
    """Test that we don't create the infowidget if requested by the user."""
    client = ipyconsole.get_widget().get_current_client()
    assert client.infowidget is None


@flaky(max_runs=3)
def test_cwd_console_options(ipyconsole, qtbot, tmpdir):
    """
    Test that the working directory options for new consoles work as expected.
    """
    def get_cwd_of_new_client():
        ipyconsole.create_new_client()
        shell = ipyconsole.get_current_shellwidget()
        qtbot.waitUntil(lambda: shell._prompt_html is not None,
                        timeout=SHELL_TIMEOUT)

        with qtbot.waitSignal(shell.executed):
            shell.execute('import os; cwd = os.getcwd()')

        return shell.get_value('cwd')

    # --- Check use_project_or_home_directory
    ipyconsole.set_conf(
        'console/use_project_or_home_directory',
        True,
        section='workingdir',
    )

    # Simulate that there's a project open
    project_dir = str(tmpdir.mkdir('ipyconsole_project_test'))
    ipyconsole.get_widget().update_active_project_path(project_dir)

    # Get cwd of new client and assert is the expected one
    assert get_cwd_of_new_client() == project_dir

    # Reset option
    ipyconsole.set_conf(
        'console/use_project_or_home_directory',
        False,
        section='workingdir',
    )

    # --- Check current working directory
    ipyconsole.set_conf('console/use_cwd', True, section='workingdir')

    # Simulate a specific directory
    cwd_dir = str(tmpdir.mkdir('ipyconsole_cwd_test'))
    ipyconsole.get_widget().save_working_directory(cwd_dir)

    # Get cwd of new client and assert is the expected one
    assert get_cwd_of_new_client() == cwd_dir

    # Reset option
    ipyconsole.set_conf('console/use_cwd', False, section='workingdir')

    # --- Check fixed working directory
    ipyconsole.set_conf(
        'console/use_fixed_directory',
        True,
        section='workingdir'
    )

    # Simulate a fixed directory
    fixed_dir = str(tmpdir.mkdir('ipyconsole_fixed_test'))
    ipyconsole.set_conf(
        'console/fixed_directory',
        fixed_dir,
        section='workingdir'
    )

    # Get cwd of new client and assert is the expected one
    assert get_cwd_of_new_client() == fixed_dir


def test_startup_run_lines_project_directory(ipyconsole, qtbot, tmpdir):
    """
    Test 'startup/run_lines' config works with code from an active project.
    """
    project = tmpdir.mkdir('ipyconsole_project_test')
    project_dir = str(project)
    project_script = project.join('project_script.py')
    project_script.write('from numpy import pi')

    # Config spyder_pythonpath with the project path
    ipyconsole.set_conf(
        'spyder_pythonpath',
        [project_dir],
        section='main')

    # Config console with project path
    ipyconsole.set_conf(
        'startup/run_lines',
        'from project_script import *',
        section='ipython_console')
    ipyconsole.set_conf(
        'console/use_project_or_home_directory',
        True,
        section='workingdir',
    )
    ipyconsole.get_widget().update_active_project_path(project_dir)

    # Restart console
    ipyconsole.restart()

    # Check that the script was imnported
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    assert shell.get_value('pi')

    # Reset config for the 'spyder_pythonpath' and 'startup/run_lines'
    ipyconsole.set_conf(
        'spyder_pythonpath',
        [],
        section='main')
    ipyconsole.set_conf(
        'startup/run_lines',
        '',
        section='ipython_console')


def test_varexp_magic_dbg_locals(ipyconsole, qtbot):
    """Test that %varexp is working while debugging locals."""

    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute("def f():\n    li = [1, 2]\n    return li")

    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug f()")


    # Get to an object that can be plotted
    for _ in range(4):
        with qtbot.waitSignal(shell.executed):
            shell.execute("!s")

    # Generate the plot
    with qtbot.waitSignal(shell.executed):
        shell.execute("%varexp --plot li")

    qtbot.wait(1000)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1


@pytest.mark.skipif(os.name == 'nt', reason="Fails on windows")
def test_old_kernel_version(ipyconsole, qtbot):
    """
    Check that an error is shown when an version of spyder-kernels is used.
    """
    # Set a false _spyder_kernels_version in the cached kernel
    w = ipyconsole.get_widget()
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    kc = w._cached_kernel_properties[-1].kernel_client
    kc.start_channels()
    kc.execute("get_ipython()._spyder_kernels_version = ('1.0.0', '')")
    # Cleanup the kernel_client so it can be used again
    kc.stop_channels()
    kc._shell_channel = None
    kc._iopub_channel = None
    kc._stdin_channel = None
    kc._hb_channel = None
    kc._control_channel = None

    # Create new client
    w.create_new_client()
    client = w.get_current_client()

    # Make sure an error is shown
    control = client.get_control()
    qtbot.waitUntil(
        lambda: "1.0.0" in control.toPlainText(), timeout=SHELL_TIMEOUT)
    assert "conda install spyder" in control.toPlainText()


def test_run_script(ipyconsole, qtbot, tmp_path):
    """
    Test running multiple scripts at the same time.

    This is a regression test for issue spyder-ide/spyder#15405
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create two temp files: 'a.py' and 'b.py'
    dir_a = tmp_path / 'a'
    dir_a.mkdir()
    filename_a = dir_a / 'a.py'
    filename_a.write_text('a = 1')

    dir_b = tmp_path / 'b'
    dir_b.mkdir()
    filename_b = dir_a / 'b.py'
    filename_b.write_text('b = 1')

    filenames = [str(filename_a), str(filename_b)]

    # Run scripts
    for filename in filenames:
        ipyconsole.run_script(
            filename=filename,
            wdir=osp.dirname(filename),
            current_client=False,
            clear_variables=True
        )

    # Validate created consoles names and code executed
    for filename in filenames:
        basename = osp.basename(filename)
        client_name = f'{basename}/A'
        variable_name = basename.split('.')[0]

        client = ipyconsole.get_client_for_file(filename)
        assert client.get_name() == client_name

        sw = client.shellwidget
        qtbot.waitUntil(
            lambda: sw._prompt_html is not None, timeout=SHELL_TIMEOUT)

        # Wait for the respective script to be run
        control = client.get_control()
        qtbot.waitUntil(
            lambda: "In [2]:" in control.toPlainText(), timeout=SHELL_TIMEOUT)
        assert sw.get_value(variable_name) == 1


if __name__ == "__main__":
    pytest.main()
