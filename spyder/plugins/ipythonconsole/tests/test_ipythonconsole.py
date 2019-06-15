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
import os
import os.path as osp
import shutil
import sys
import tempfile
from textwrap import dedent
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import cloudpickle
from flaky import flaky
from jupyter_client.kernelspec import KernelSpec
from pygments.token import Name
import pytest
from qtpy import PYQT5
from qtpy.QtCore import Qt
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import QMessageBox, QMainWindow
import sympy

# Local imports
from spyder.config.gui import get_color_scheme
from spyder.config.main import CONF
from spyder.py3compat import PY2, to_text_string
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.ipythonconsole.utils.style import create_style_class
from spyder.utils.programs import get_temp_dir


# =============================================================================
# Constants
# =============================================================================
SHELL_TIMEOUT = 20000
TEMP_DIRECTORY = tempfile.gettempdir()
NON_ASCII_DIR = osp.join(TEMP_DIRECTORY, u'測試', u'اختبار')


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


class FaultyKernelSpec(KernelSpec):
    """Kernelspec that generates a kernel crash"""

    argv = [sys.executable, '-m', 'spyder_kernels.foo', '-f',
            '{connection_file}']


# =============================================================================
# Qt Test Fixtures
# =============================================================================
@pytest.fixture
def ipyconsole(qtbot, request):
    """IPython console fixture."""

    class MainWindowMock(QMainWindow):
        def __getattr__(self, attr):
            if attr == 'consoles_menu_actions':
                return []
            else:
                return Mock()

    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 0)

    # Test the console with a non-ascii temp dir
    non_ascii_dir = request.node.get_marker('non_ascii_dir')
    if non_ascii_dir:
        test_dir = NON_ASCII_DIR
    else:
        test_dir = None

    # Instruct the console to not use a stderr file
    no_stderr_file = request.node.get_marker('no_stderr_file')
    if no_stderr_file:
        test_no_stderr = True
    else:
        test_no_stderr = False

    # Use the automatic backend if requested
    auto_backend = request.node.get_marker('auto_backend')
    if auto_backend:
        CONF.set('ipython_console', 'pylab/backend', 1)

    # Start a Pylab client if requested
    pylab_client = request.node.get_marker('pylab_client')
    is_pylab = True if pylab_client else False

    # Start a Sympy client if requested
    sympy_client = request.node.get_marker('sympy_client')
    is_sympy = True if sympy_client else False

    # Start a Cython client if requested
    cython_client = request.node.get_marker('cython_client')
    is_cython = True if cython_client else False

    # Create the console and a new client
    window = MainWindowMock()
    console = IPythonConsole(parent=window,
                             testing=True,
                             test_dir=test_dir,
                             test_no_stderr=test_no_stderr)
    console.dockwidget = Mock()
    console.create_new_client(is_pylab=is_pylab,
                              is_sympy=is_sympy,
                              is_cython=is_cython)
    window.setCentralWidget(console)

    # Close callback
    def close_console():
        console.closing_plugin()
        console.close()
    request.addfinalizer(close_console)

    qtbot.addWidget(window)
    window.show()
    return console


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Times out on macOS")
def test_get_calltips(ipyconsole, qtbot):
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
        qtbot.keyClicks(control, 'np.abs(')

    # Wait a little bit for the calltip to appear
    qtbot.wait(500)

    # Assert we displayed a calltip
    assert control.calltip_widget.isVisible()
    assert 'Calculate the absolute value' in control.calltip_widget.text()
    # Hide the calltip to avoid focus problems on Linux
    control.calltip_widget.hide()


@pytest.mark.slow
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


@pytest.mark.slow
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
    shell.reset_namespace(warning=False)
    qtbot.wait(1000)

    # See that `e` is still defined from numpy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("e")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()


@pytest.mark.slow
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
    shell.reset_namespace(warning=False)
    qtbot.wait(1000)

    # See that `e` is still defined from sympy after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("x")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'NameError' not in control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.cython_client
@pytest.mark.skipif(os.name == 'nt', reason="It doesn't work on Windows")
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
    shell.reset_namespace(warning=False)
    qtbot.wait(1000)

    # See that cython is still enabled after reset
    with qtbot.waitSignal(shell.executed):
        shell.execute("%%cython\n"
                      "cdef int ctest(int x, int y):\n"
                      "    return x + y")

    # Assert there are no errors after restting the console
    control = ipyconsole.get_focus_widget()
    assert 'Error' not in control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=3)
def test_tab_rename_for_slaves(ipyconsole, qtbot):
    """Test slave clients are renamed correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    cf = ipyconsole.get_current_client().connection_file
    ipyconsole._create_client_for_kernel(cf, None, None, None)
    qtbot.wait(1000)

    # Rename slave
    ipyconsole.rename_tabs_after_change('foo')

    # Assert both clients have the same name
    assert 'foo' in ipyconsole.get_clients()[0].get_name()
    assert 'foo' in ipyconsole.get_clients()[1].get_name()


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
@flaky(max_runs=3)
def test_set_cwd(ipyconsole, qtbot, tmpdir):
    """Test kernel when changing cwd."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Issue 6451.
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


@pytest.mark.slow
@flaky(max_runs=3)
def test_get_cwd(ipyconsole, qtbot, tmpdir):
    """Test current working directory."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None,
                    timeout=SHELL_TIMEOUT)

    # Issue 6451.
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
        shell.get_cwd()

    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\\\", u"\\")

    assert shell._cwd == tempdir

    shell.set_cwd(savetemp)


@pytest.mark.slow
@flaky(max_runs=3)
def test_get_env(ipyconsole, qtbot):
    """Test that getting env vars from the kernel is working as expected."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Add a new entry to os.environ
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; os.environ['FOO'] = 'bar'" )

    # Ask for os.environ contents
    with qtbot.waitSignal(shell.sig_show_env) as blocker:
        shell.get_env()

    # Get env contents from the signal
    env_contents = blocker.args[0]

    # Assert that our added entry is part of os.environ
    assert env_contents['FOO'] == 'bar'


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt',
                    reason="Fails due to differences in path handling")
def test_get_syspath(ipyconsole, qtbot, tmpdir):
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
        shell.get_syspath()

    # Get sys.path contents from the signal
    syspath_contents = blocker.args[0]

    # Assert that our added entry is part of sys.path
    assert tmp_dir in syspath_contents


@pytest.mark.slow
@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It doesn't work on Windows")
def test_browse_history_dbg(ipyconsole, qtbot):
    """Test that browsing command history is working while debugging."""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')

    shell.execute('%debug')
    qtbot.wait(1000)

    # Enter an expression
    qtbot.keyClicks(control, '!aa = 10')
    qtbot.keyClick(control, Qt.Key_Enter)

    # Clear console (for some reason using shell.clear_console
    # doesn't work here)
    shell.reset(clear=True)
    qtbot.wait(1000)

    # Press Up arrow button and assert we get the last
    # introduced command
    qtbot.keyClick(control, Qt.Key_Up)
    assert '!aa = 10' in control.toPlainText()


@pytest.mark.slow
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
    shell.set_value('д', [cloudpickle.dumps(20, protocol=2)])
    qtbot.wait(1000)
    assert shell.get_value('д') == 20


@pytest.mark.slow
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


@pytest.mark.slow
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

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')
    shell.execute('%debug')
    qtbot.wait(1000)

    # Get value
    qtbot.keyClicks(control, '!aa = 10')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(1000)
    assert shell.get_value('aa') == 10

    # Set value
    shell.set_value('aa', [cloudpickle.dumps(20, protocol=2)])
    qtbot.wait(1000)
    assert shell.get_value('aa') == 20

    # Copy value
    shell.copy_value('aa', 'bb')
    qtbot.wait(1000)
    assert shell.get_value('bb') == 20

    # Rmoeve value
    shell.remove_value('aa')
    qtbot.wait(1000)
    qtbot.keyClicks(control, '!aa')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(1000)
    assert "*** NameError: name 'aa' is not defined" in control.toPlainText()


@pytest.mark.slow
@flaky(max_runs=10)
@pytest.mark.skipif(
    os.environ.get('AZURE', None) is not None,
    reason="It doesn't work on Windows and fails often on macOS")
def test_plot_magic_dbg(ipyconsole, qtbot):
    """Test our plot magic while debugging"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Give focus to the widget that's going to receive clicks
    control = ipyconsole.get_focus_widget()
    control.setFocus()

    # Import Matplotlib
    with qtbot.waitSignal(shell.executed):
        shell.execute('import matplotlib.pyplot as plt')

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')
    shell.execute('%debug')
    qtbot.wait(1000)

    # Test reset magic
    qtbot.keyClicks(control, '%plot plt.plot(range(10))')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(1000)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1


@pytest.mark.slow
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


@pytest.mark.slow
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

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')

    shell.execute('%debug')
    qtbot.wait(1000)

    # Test Ctrl+C
    qtbot.keyClick(control, Qt.Key_C, modifier=Qt.ControlModifier)
    qtbot.wait(2000)
    assert 'For copying text while debugging, use Ctrl+Shift+C' in control.toPlainText()


@pytest.mark.slow
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

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')

    shell.execute('%debug')
    qtbot.wait(1000)

    # Test clear magic
    shell.clear_console()
    qtbot.wait(1000)
    assert '\nipdb> ' == control.toPlainText()

    # Test reset magic
    qtbot.keyClicks(control, '!bb = 10')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)
    assert shell.get_value('bb') == 10

    shell.reset_namespace(warning=False)
    qtbot.wait(1000)

    qtbot.keyClicks(control, '!bb')
    qtbot.keyClick(control, Qt.Key_Enter)
    qtbot.wait(500)

    assert "*** NameError: name 'bb' is not defined" in control.toPlainText()


@pytest.mark.slow
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


@pytest.mark.slow
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
    qtbot.wait(1000)

    new_client = ipyconsole.get_clients()[1]
    assert new_client.id_ == dict(int_id='1', str_id='B')


@pytest.mark.slow
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
    qtbot.wait(1000)

    assert len(ipyconsole.get_clients()) == 2


@pytest.mark.slow
@flaky(max_runs=3)
def test_load_kernel_file(ipyconsole, qtbot, tmpdir):
    """
    Test that a new client is created using the connection file
    of an existing client
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    ipyconsole._create_client_for_kernel(client.connection_file, None, None, None)
    qtbot.wait(1000)

    new_client = ipyconsole.get_clients()[1]
    new_shell = new_client.shellwidget
    with qtbot.waitSignal(new_shell.executed):
        new_shell.execute('a = 10')

    assert new_client.id_ == dict(int_id='1', str_id='B')
    assert shell.get_value('a') == new_shell.get_value('a')


@pytest.mark.slow
@flaky(max_runs=3)
def test_sys_argv_clear(ipyconsole, qtbot):
    """Test that sys.argv is cleared up correctly"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")

    assert argv == ['']


@pytest.mark.slow
@flaky(max_runs=5)
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
@flaky(max_runs=3)
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="It only works on Linux")
def test_kernel_crash(ipyconsole, mocker, qtbot):
    """Test that we show kernel error messages when a kernel crash occurs."""
    # Patch create_kernel_spec method to make it return a faulty
    # kernel spec
    mocker.patch.object(ipyconsole, 'create_kernel_spec')
    ipyconsole.create_kernel_spec.return_value = FaultyKernelSpec()

    # Create a new client, which will use FaultyKernelSpec
    ipyconsole.create_new_client()

    # Assert that the console is showing an error
    qtbot.wait(6000)
    error_client = ipyconsole.get_clients()[-1]
    assert error_client.is_error_shown

    # Assert the error contains the text we expect
    webview = error_client.infowidget
    if WEBENGINE:
        webpage = webview.page()
    else:
        webpage = webview.page().mainFrame()
    qtbot.waitUntil(lambda: check_text(webpage, "foo"), timeout=6000)


@pytest.mark.slow
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


if __name__ == "__main__":
    pytest.main()
