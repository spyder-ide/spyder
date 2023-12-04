# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

# Standard library imports
import os
import os.path as osp
import sys
import tempfile
import threading
import traceback
from unittest.mock import Mock

# Third-party imports
import psutil
from pygments.token import Name
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.manager import CONF
from spyder.plugins.help.utils.sphinxify import CSS_PATH
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.ipythonconsole.utils.style import create_style_class
from spyder.utils.conda import get_list_conda_envs


# =============================================================================
# ---- Constants
# =============================================================================
SHELL_TIMEOUT = 20000
TEMP_DIRECTORY = tempfile.gettempdir()
NON_ASCII_DIR = osp.join(TEMP_DIRECTORY, u'測試', u'اختبار')
NEW_DIR = 'new_workingdir'
PY312_OR_GREATER = sys.version_info[:2] >= (3, 12)


# =============================================================================
# ---- Pytest adjustments
# =============================================================================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)


# =============================================================================
# ---- Utillity Functions
# =============================================================================
def get_console_font_color(syntax_style):
    styles = create_style_class(syntax_style).styles
    font_color = styles[Name]
    return font_color


def get_console_background_color(style_sheet):
    background_color = style_sheet.split('background-color:')[1]
    background_color = background_color.split(';')[0]
    return background_color


def get_conda_test_env():
    """
    Return the full prefix path of the env used to test kernel activation and
    its executable.
    """
    # Get conda env to use
    test_env_executable = get_list_conda_envs()['conda: spytest-ž'][0]

    # Get the env prefix
    if os.name == 'nt':
        test_env_prefix = osp.dirname(test_env_executable)
    else:
        test_env_prefix = osp.dirname(osp.dirname(test_env_executable))

    return (test_env_prefix, test_env_executable)


# =============================================================================
# ---- Fixtures
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
        test_no_stderr = 'True'
    else:
        test_no_stderr = ''

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
            'main_interpreter', 'executable', get_conda_test_env()[1])
    else:
        configuration.set('main_interpreter', 'default', True)
        configuration.set('main_interpreter', 'executable', '')

    # Conf css_path in the Appeareance plugin
    configuration.set('appearance', 'css_path', CSS_PATH)

    # Create the console and a new client and set environment
    os.environ['IPYCONSOLE_TESTING'] = 'True'
    os.environ['IPYCONSOLE_TEST_DIR'] = test_dir
    os.environ['IPYCONSOLE_TEST_NO_STDERR'] = test_no_stderr
    window = MainWindowMock()
    console = IPythonConsole(parent=window, configuration=configuration)
    console._register()
    console.create_new_client(is_pylab=is_pylab,
                              is_sympy=is_sympy,
                              is_cython=is_cython)
    window.setCentralWidget(console.get_widget())

    # Set exclamation mark to True
    configuration.set('ipython_console', 'pdb_use_exclamation_mark', True)

    if os.name == 'nt':
        qtbot.addWidget(window)

    with qtbot.waitExposed(window):
        window.resize(640, 480)
        window.show()

    if auto_backend or tk_backend:
        qtbot.wait(SHELL_TIMEOUT)
        console.create_new_client()

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
    os.environ.pop('IPYCONSOLE_TEST_DIR')
    os.environ.pop('IPYCONSOLE_TEST_NO_STDERR')

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
        for threadId, frame in sys._current_frames().items():
            if threadId in now_thread_ids:
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
