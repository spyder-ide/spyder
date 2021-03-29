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
from distutils.version import LooseVersion
import os
import os.path as osp
import shutil
import sys
import tempfile
from textwrap import dedent
from unittest.mock import Mock

# Third party imports
import IPython
from IPython.core import release as ipy_release
from IPython.core.application import get_ipython_dir
from flaky import flaky
from pygments.token import Name
import pytest
from qtpy import PYQT5
from qtpy.QtCore import Qt
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import QMessageBox, QMainWindow
import sympy

# Local imports
from spyder.config.base import get_home_dir
from spyder.config.gui import get_color_scheme
from spyder.config.manager import CONF
from spyder.py3compat import PY2, to_text_string
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.ipythonconsole.utils.style import create_style_class
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
def ipyconsole(qtbot, request):
    """IPython console fixture."""

    class MainWindowMock(QMainWindow):
        def get_spyder_pythonpath(self):
            return CONF.get('main', 'spyder_pythonpath', [])

        def __getattr__(self, attr):
            if attr == 'consoles_menu_actions':
                return []
            else:
                return Mock()

    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 0)

    # Start in a new working directory the console
    use_startup_wdir = request.node.get_closest_marker('use_startup_wdir')
    if use_startup_wdir:
        new_wdir = osp.join(os.getcwd(), NEW_DIR)
        if not osp.exists(new_wdir):
            os.mkdir(new_wdir)
        CONF.set('workingdir', 'console/use_fixed_directory', True)
        CONF.set('workingdir', 'console/fixed_directory', new_wdir)
    else:
        CONF.set('workingdir', 'console/use_fixed_directory', False)
        CONF.set('workingdir', 'console/fixed_directory', get_home_dir())

    # Test the console with a non-ascii temp dir
    non_ascii_dir = request.node.get_closest_marker('non_ascii_dir')
    if non_ascii_dir:
        test_dir = NON_ASCII_DIR
    else:
        test_dir = None

    # Instruct the console to not use a stderr file
    no_stderr_file = request.node.get_closest_marker('no_stderr_file')
    if no_stderr_file:
        test_no_stderr = True
    else:
        test_no_stderr = False

    # Use the automatic backend if requested
    auto_backend = request.node.get_closest_marker('auto_backend')
    if auto_backend:
        CONF.set('ipython_console', 'pylab/backend', 1)

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
    external_interpreter = request.node.get_closest_marker('external_interpreter')
    if external_interpreter:
        CONF.set('main_interpreter', 'default', False)
        CONF.set('main_interpreter', 'executable', sys.executable)
    else:
        CONF.set('main_interpreter', 'default', True)
        CONF.set('main_interpreter', 'executable', '')

    # Use the test environment interpreter if requested
    test_environment_interpreter = request.node.get_closest_marker(
        'test_environment_interpreter')

    if test_environment_interpreter:
        CONF.set('main_interpreter', 'default', False)
        CONF.set('main_interpreter', 'executable', get_conda_test_env())
    else:
        CONF.set('main_interpreter', 'default', True)
        CONF.set('main_interpreter', 'executable', '')


    # Create the console and a new client
    window = MainWindowMock()
    console = IPythonConsole(parent=window,
                             testing=True,
                             test_dir=test_dir,
                             test_no_stderr=test_no_stderr)
    console.dockwidget = Mock()
    console._toggle_view_action = Mock()
    console.create_new_client(is_pylab=is_pylab,
                              is_sympy=is_sympy,
                              is_cython=is_cython)
    window.setCentralWidget(console)

    # Set exclamation mark to True
    CONF.set('ipython_console', 'pdb_use_exclamation_mark', True)

    # This segfaults on macOS
    if not sys.platform == "darwin":
        qtbot.addWidget(window)
    window.resize(640, 480)
    window.show()

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
    console.closing_plugin()
    console.close()
    window.close()


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.external_interpreter
def test_banners(ipyconsole, qtbot):
    """Test that console banners are generated correctly."""
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Long banner
    text = control.toPlainText().splitlines()
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
@pytest.mark.skipif(os.name == 'nt', reason="It times out sometimes on Windows")
def test_auto_backend(ipyconsole, qtbot):
    """Test that the automatic backend is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("%matplotlib qt5")

    # Assert there are no errors in the console
    control = ipyconsole.get_focus_widget()
    assert 'NOTE' not in control.toPlainText()
    assert 'Error' not in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.pylab_client
def test_pylab_client(ipyconsole, qtbot):
    """Test that the Pylab console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")

    # Assert there are no errors in the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that `e` is still defined from numpy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.sympy_client
@pytest.mark.xfail('1.0' < sympy.__version__ < '1.2',
                   reason="A bug with sympy 1.1.1 and IPython-Qtconsole")
def test_sympy_client(ipyconsole, qtbot):
    """Test that the SymPy console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("x")

    # Assert there are no errors in the console
    control = ipyconsole.get_focus_widget()
    assert 'NameError' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that `e` is still defined from sympy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("x")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'NameError' not in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.cython_client
@pytest.mark.skipif(
    (not sys.platform.startswith('linux') or
     LooseVersion(ipy_release.version) == LooseVersion('7.11.0')),
    reason="It only works reliably on Linux and fails for IPython 7.11.0")
def test_cython_client(ipyconsole, qtbot):
    """Test that the Cython console is working correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # This is here to generate further errors
    with qtbot.waitSignal(shell.executed):
        shell.execute("%%cython\n"
                      "cdef int ctest(int x, int y):\n"
                      "    return x + y")

    # Assert there are no errors in the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()

    # Reset the console namespace
    shell.reset_namespace()
    qtbot.wait(1000)

    # See that cython is still enabled after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("%%cython\n"
                      "cdef int ctest(int x, int y):\n"
                      "    return x + y")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()


@flaky(max_runs=3)
def test_tab_rename_for_slaves(ipyconsole, qtbot):
    """Test slave clients are renamed correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    cf = ipyconsole.get_current_client().connection_file
    ipyconsole._create_client_for_kernel(cf, None, None, None)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    # Rename slave
    ipyconsole.rename_tabs_after_change('foo')

    # Assert both clients have the same name
    assert 'foo' in ipyconsole.get_clients()[0].get_name()
    assert 'foo' in ipyconsole.get_clients()[1].get_name()


@flaky(max_runs=3)
def test_no_repeated_tabs_name(ipyconsole, qtbot):
    """Test that tabs can't have repeated given names."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Rename first client
    ipyconsole.rename_tabs_after_change('foo')

    # Create a new client and try to rename it
    ipyconsole.create_new_client()
    ipyconsole.rename_tabs_after_change('foo')

    # Assert the rename didn't take place
    client_name = ipyconsole.get_current_client().get_name()
    assert '2' in client_name


@flaky(max_runs=3)
def test_tabs_preserve_name_after_move(ipyconsole, qtbot):
    """Test that tabs preserve their names after they are moved."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Create a new client
    ipyconsole.create_new_client()

    # Move tabs
    ipyconsole.tabwidget.tabBar().moveTab(0, 1)

    # Assert the second client is in the first position
    client_name = ipyconsole.get_clients()[0].get_name()
    assert '2' in client_name


@flaky(max_runs=3)
def test_conf_env_vars(ipyconsole, qtbot):
    """Test that kernels have env vars set by our kernel spec."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Import numpy
    with qtbot.waitSignal(shell.executed):
        shell.execute('from numpy import *')

    # Assert we get the e value correctly
    assert shell.get_value('e') == 2.718281828459045


@flaky(max_runs=3)
def test_console_disambiguation(ipyconsole, qtbot):
    """Test the disambiguation of dedicated consoles."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    ipyconsole.tabwidget.setCurrentIndex(1)
    client = ipyconsole.get_current_client()
    assert client.get_name() == 'c.py - b/A'


@flaky(max_runs=3)
def test_console_coloring(ipyconsole, qtbot):
    """Test that console gets the same coloring present in the Editor."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    config_options = ipyconsole.config_options()

    syntax_style = config_options.JupyterWidget.syntax_style
    style_sheet = config_options.JupyterWidget.style_sheet
    console_font_color = get_console_font_color(syntax_style)
    console_background_color = get_console_background_color(style_sheet)

    selected_color_scheme = CONF.get('appearance', 'selected')
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    with qtbot.waitSignal(shell.sig_change_cwd):
        shell.update_cwd()

    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\\\", u"\\")

    assert shell._cwd == tempdir

    shell.set_cwd(savetemp)


@flaky(max_runs=3)
def test_request_env(ipyconsole, qtbot):
    """Test that getting env vars from the kernel is working as expected."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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
    control = ipyconsole.get_focus_widget()
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Set contents of the stderr file of the kernel
    content = 'Test text'
    stderr_file = client.stderr_file
    codecs.open(stderr_file, 'w', 'cp437').write(content)
    # Assert that content is correct
    assert content == client._read_stderr()


@flaky(max_runs=10)
@pytest.mark.no_xvfb
@pytest.mark.skipif(os.environ.get('CI', None) is not None and os.name == 'nt',
                    reason="It times out on AppVeyor.")
@pytest.mark.skipif(PY2, reason="It times out in Python 2.")
def test_values_dbg(ipyconsole, qtbot):
    """
    Test that getting, setting, copying and removing values is working while
    debugging.
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Import Matplotlib
    with qtbot.waitSignal(shell.executed):
        shell.execute('import matplotlib.pyplot as plt')

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Set processing events to True
    CONF.set('ipython_console', 'pdb_execute_events', True)
    shell.set_pdb_execute_events(True)

    # Test reset magic
    qtbot.keyClicks(control, 'plt.plot(range(10))')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1

    # Set processing events to False
    CONF.set('ipython_console', 'pdb_execute_events', False)
    shell.set_pdb_execute_events(False)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

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
@pytest.mark.skipif(os.environ.get('CI', None) is not None or PYQT5,
                    reason="It fails frequently in PyQt5 and our CIs")
def test_ctrl_c_dbg(ipyconsole, qtbot):
    """
    Test that Ctrl+C works while debugging
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Test Ctrl+C
    qtbot.keyClick(control, Qt.Key_C, modifier=Qt.ControlModifier)
    qtbot.waitUntil(
        lambda: 'For copying text while debugging, use Ctrl+Shift+C' in
        control.toPlainText(), timeout=2000)

    assert 'For copying text while debugging, use Ctrl+Shift+C' in control.toPlainText()


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It doesn't work on Windows")
def test_clear_and_reset_magics_dbg(ipyconsole, qtbot):
    """
    Test that clear and reset magics are working while debugging
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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
def test_restart_kernel(ipyconsole, qtbot):
    """
    Test that kernel is restarted correctly
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Do an assignment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    ipyconsole.restart_kernel()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    assert 'Restarting kernel...' in shell._control.toPlainText()
    assert not shell.is_defined('a')


@flaky(max_runs=3)
def test_load_kernel_file_from_id(ipyconsole, qtbot):
    """
    Test that a new client is created using its id
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    connection_file = osp.basename(client.connection_file)
    id_ = connection_file.split('kernel-')[-1].split('.json')[0]

    ipyconsole._create_client_for_kernel(id_, None, None, None)
    qtbot.waitUntil(lambda: len(ipyconsole.get_clients()) == 2)

    new_client = ipyconsole.get_clients()[1]
    assert new_client.id_ == dict(int_id='1', str_id='B')


@flaky(max_runs=3)
def test_load_kernel_file_from_location(ipyconsole, qtbot, tmpdir):
    """
    Test that a new client is created using a connection file
    placed in a different location from jupyter_runtime_dir
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    fname = osp.basename(client.connection_file)
    connection_file = to_text_string(tmpdir.join(fname))
    shutil.copy2(client.connection_file, connection_file)

    ipyconsole._create_client_for_kernel(connection_file, None, None, None)
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    ipyconsole._create_client_for_kernel(client.connection_file,
                                         None, None, None)
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")

    assert argv == ['']


@flaky(max_runs=5)
@pytest.mark.skipif(os.name == 'nt', reason="Fails on Windows")
def test_set_elapsed_time(ipyconsole, qtbot):
    """Test that the IPython console elapsed timer is set correctly."""
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Set time to 2 minutes ago.
    client.t0 -= 120
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        ipyconsole.set_elapsed_time(client)
    assert ('00:02:00' in client.time_label.text() or
            '00:02:01' in client.time_label.text())

    # Wait for a second to pass, to ensure timer is counting up
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        pass
    assert ('00:02:01' in client.time_label.text() or
            '00:02:02' in client.time_label.text())

    # Make previous time later than current time.
    client.t0 += 2000
    with qtbot.waitSignal(client.timer.timeout, timeout=5000):
        pass
    assert '00:00:00' in client.time_label.text()

    client.timer.timeout.disconnect(client.show_time)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_stderr_file_is_removed_one_kernel(ipyconsole, qtbot, monkeypatch):
    """Test that consoles removes stderr when client is closed."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, 'question',
                        classmethod(lambda *args: QMessageBox.Yes))
    assert osp.exists(client.stderr_file)
    ipyconsole.close_client(client=client)
    assert not osp.exists(client.stderr_file)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_stderr_file_is_removed_two_kernels(ipyconsole, qtbot, monkeypatch):
    """Test that console removes stderr when client and related clients
    are closed."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # New client with the same kernel
    ipyconsole._create_client_for_kernel(client.connection_file, None, None,
                                         None)

    assert len(ipyconsole.get_related_clients(client)) == 1
    other_client = ipyconsole.get_related_clients(client)[0]
    assert client.stderr_file == other_client.stderr_file

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, 'question',
                        classmethod(lambda *args: QMessageBox.Yes))
    assert osp.exists(client.stderr_file)
    ipyconsole.close_client(client=client)
    assert not osp.exists(client.stderr_file)


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_stderr_file_remains_two_kernels(ipyconsole, qtbot, monkeypatch):
    """Test that console doesn't remove stderr when a related client is not
    closed."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # New client with the same kernel
    ipyconsole._create_client_for_kernel(client.connection_file, None, None,
                                         None)

    assert len(ipyconsole.get_related_clients(client)) == 1
    other_client = ipyconsole.get_related_clients(client)[0]
    assert client.stderr_file == other_client.stderr_file

    # In a normal situation file should exist
    monkeypatch.setattr(QMessageBox, "question",
                        classmethod(lambda *args: QMessageBox.No))
    assert osp.exists(client.stderr_file)
    ipyconsole.close_client(client=client)
    assert osp.exists(client.stderr_file)


@flaky(max_runs=3)
def test_kernel_crash(ipyconsole, qtbot):
    """Test that we show an error message when a kernel crash occurs."""
    # Create an IPython kernel config file with a bad config
    ipy_kernel_cfg = osp.join(get_ipython_dir(), 'profile_default',
                              'ipython_kernel_config.py')
    with open(ipy_kernel_cfg, 'w') as f:
        # This option must be a string, not an int
        f.write("c.InteractiveShellApp.extra_extension = 1")

    ipyconsole.create_new_client()

    # Assert that the console is showing an error
    qtbot.waitUntil(lambda: ipyconsole.get_clients()[-1].is_error_shown,
                    timeout=6000)
    error_client = ipyconsole.get_clients()[-1]
    assert error_client.is_error_shown

    # Assert the error contains the text we expect
    webview = error_client.infowidget
    if WEBENGINE:
        webpage = webview.page()
    else:
        webpage = webview.page().mainFrame()
    qtbot.waitUntil(
        lambda: check_text(webpage, "Bad config encountered"),
        timeout=6000)

    # Remove bad kernel config file
    os.remove(ipy_kernel_cfg)


@pytest.mark.skipif(not os.name == 'nt', reason="Only works on Windows")
def test_remove_old_stderr_files(ipyconsole, qtbot):
    """Test that we are removing old stderr files."""
    # Create empty stderr file in our temp dir to see
    # if it's removed correctly.
    tmpdir = get_temp_dir()
    open(osp.join(tmpdir, 'foo.stderr'), 'a').close()

    # Assert that only that file is removed
    ipyconsole._remove_old_stderr_files()
    assert not osp.isfile(osp.join(tmpdir, 'foo.stderr'))


@flaky(max_runs=10)
@pytest.mark.use_startup_wdir
def test_console_working_directory(ipyconsole, qtbot):
    """Test for checking the working directory."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    with qtbot.waitSignal(shell.executed):
        shell.execute('import os; cwd = os.getcwd()')

    current_wdir = shell.get_value('cwd')
    folders = osp.split(current_wdir)
    assert folders[-1] == NEW_DIR


@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux') or PY2,
                    reason="It only works on Linux with python 3.")
def test_console_complete(ipyconsole, qtbot, tmpdir):
    """Test for checking the working directory."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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


@pytest.mark.use_startup_wdir
def test_pdb_multiline(ipyconsole, qtbot):
    """Test entering a multiline statment into pdb"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Tests assume inline backend
    CONF.set('ipython_console', 'pdb_ignore_lib', not show_lib)
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

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
    CONF.set('ipython_console', 'pdb_ignore_lib', True)


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Times out on macOS")
def test_calltip(ipyconsole, qtbot):
    """
    Test Calltip.

    See spyder-ide/spyder#10842
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = {"a": 1}')
    qtbot.keyClicks(control, 'a.keys(', delay=100)
    qtbot.wait(1000)
    assert control.calltip_widget.isVisible()


@flaky(max_runs=3)
@pytest.mark.first
@pytest.mark.test_environment_interpreter
def test_conda_env_activation(ipyconsole, qtbot):
    """
    Test that the conda environment associated with an external interpreter
    is activated before a kernel is created for it.
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

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
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
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
        CONF.set('main', 'spyder_pythonpath', [str(tmpdir)])
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
    CONF.set('main', 'spyder_pythonpath', [])


@flaky(max_runs=3)
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
    client = ipyconsole.get_current_client()
    with open(client.stderr_file, 'w') as f:
        f.write("test_test")
    # Wait for the poll
    qtbot.wait(2000)
    assert "test_test" in ipyconsole.get_focus_widget().toPlainText()


@pytest.mark.slow
@pytest.mark.use_startup_wdir
def test_startup_code_pdb(ipyconsole, qtbot):
    """Test that startup code for pdb works."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Run a line on startup
    CONF.set('ipython_console', 'startup/pdb_run_lines',
             'abba = 12; print("Hello")')

    shell.execute('%debug print()')
    qtbot.waitUntil(lambda: 'Hello' in control.toPlainText())

    # Verify that the line was executed
    assert shell.get_value('abba') == 12

    # Reset setting
    CONF.set('ipython_console', 'startup/pdb_run_lines', '')


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "backend",
    ['inline', 'qt5', 'tk', 'osx', ]
)
def test_pdb_eventloop(ipyconsole, qtbot, backend):
    """Check if pdb works with every backend. (only testing 3)."""
    # Skip failing tests
    if backend == 'tk' and (os.name == 'nt' or PY2):
        return
    if backend == 'osx' and (sys.platform != "darwin" or PY2):
        return

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)
    control = ipyconsole.get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("%matplotlib " + backend)
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
    control = ipyconsole.get_focus_widget()

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
    control = ipyconsole.get_focus_widget()
    stop_button = ipyconsole.get_current_client().stop_button
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
@pytest.mark.skipif(sys.platform == 'nt', reason="Times out on Windows")
def test_code_cache(ipyconsole, qtbot):
    """
    Test that code sent to execute is properly cached
    and that the cache is empited on interrupt.
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    def check_value(name, value):
        try:
            return shell.get_value(name) == value
        except KeyError:
            return False

    # Send two execute requests and make sure the second one is executed
    shell.execute('import time; time.sleep(.5)')
    shell.execute('var = 142')
    qtbot.wait(500)
    qtbot.waitUntil(lambda: check_value('var', 142))
    assert shell.get_value('var') == 142

    # Send two execute requests and cancel the second one
    shell.execute('import time; time.sleep(.5)')
    shell.execute('var = 1000')
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
    control = ipyconsole.get_focus_widget()

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


if __name__ == "__main__":
    pytest.main()
