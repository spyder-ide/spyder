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
import os
import os.path as osp
import re
import shutil
import sys
from textwrap import dedent
from unittest.mock import patch

# Third party imports
from ipykernel._version import __version__ as ipykernel_version
from IPython.core import release as ipy_release
from IPython.core.application import get_ipython_dir
from flaky import flaky
import numpy as np
from packaging.version import parse
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWebEngineWidgets import WEBENGINE
from spyder_kernels import __version__ as spyder_kernels_version
from spyder_kernels.utils.pythonenv import is_conda_env
import sympy

# Local imports
from spyder.config.base import running_in_ci, running_in_ci_with_conda
from spyder.config.gui import get_color_scheme
from spyder.py3compat import to_text_string
from spyder.plugins.help.tests.test_plugin import check_text
from spyder.plugins.ipythonconsole.tests.conftest import (
    get_conda_test_env, get_console_background_color, get_console_font_color,
    NEW_DIR, SHELL_TIMEOUT, PY312_OR_GREATER)
from spyder.plugins.ipythonconsole.widgets import ShellWidget
from spyder.utils.conda import get_list_conda_envs


@flaky(max_runs=3)
@pytest.mark.external_interpreter
def test_banners(ipyconsole, qtbot):
    """Test that console banners are generated correctly."""
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control

    # Check long banner (the default)
    text = control.toPlainText().splitlines()
    py_ver = sys.version.splitlines()[0].strip()
    assert py_ver in text[0]  # Python version in first line
    assert 'license' in text[1]  # 'license' mention in second line
    assert '' == text[2]  # Third line is empty
    assert ipy_release.version in text[3]  # Fourth line is IPython

    # Check short banner for a new console
    ipyconsole.set_conf("show_banner", False)
    ipyconsole.create_new_client()
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=SHELL_TIMEOUT
    )

    py_ver = sys.version.split(' ')[0]
    expected = (
        f"Python {py_ver} -- IPython {ipy_release.version}\n\n" + "In [1]: "
    )
    assert expected == shell._control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "function, signature, documentation",
    [("np.arange",  # Check we get the signature from the object's docstring
      ["start", "stop"],
      ["Return evenly spaced values within a given interval.<br>",
       "open interval<br>..."]),
     ("np.vectorize",  # Numpy function with a proper signature
      ["pyfunc", "otype", "signature"],
      ["Returns an object that acts like pyfunc, but takes<br>arrays as input."
       "<br>",
       "Define a vectorized function which takes a nested<br>..."]),
     ("np.abs",  # np.abs has the same signature as np.absolute
      ["x", "/", "out"],
      ["Calculate the absolute value"]),
     ("np.where",  # Python gives an error when getting its signature
      ["condition", "/"],
      ["Return elements chosen from `x`"]),
     ("np.array",  # Signature is splitted into several lines
      ["object", "dtype=None"],
      ["Create an array.<br><br>", "Parameters"]),
     ("np.linalg.norm",  # Includes IPython default signature in inspect reply
      ["x", "ord=None"],
      ["Matrix or vector norm"]),
     ("range",  # Check we display the first signature among several
      ["stop"],
      ["range(stop) -> range object"]),
     ("dict",  # Check we skip an empty signature
      ["mapping"],
      ["dict() -> new empty dictionary"]),
     ("foo",  # Check we display the right tooltip for interactive objects
      ["x", "y"],
      ["My function"])
     ]
)
@pytest.mark.skipif(running_in_ci() and not os.name == 'nt',
                    reason="Times out on macOS and fails on Linux")
@pytest.mark.skipif(parse(np.__version__) < parse('1.25.0'),
                    reason="Documentation for np.vectorize is different")
def test_get_calltips(ipyconsole, qtbot, function, signature, documentation):
    """Test that calltips show the documentation."""
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control

    # Import numpy
    with qtbot.waitSignal(shell.executed):
        shell.execute('import numpy as np')

    if function == "foo":
        with qtbot.waitSignal(shell.executed):
            code = dedent('''
            def foo(x, y):
                """
                My function
                """
                return x + y
            ''')

            shell.execute(code)

    # Write an object in the console that should generate a calltip
    # and wait for the kernel to send its response.
    with qtbot.waitSignal(shell.kernel_client.shell_channel.message_received):
        qtbot.keyClicks(control, function + '(')

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
def test_auto_backend(ipyconsole, qtbot):
    """Test that the automatic backend was set correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("get_ipython().kernel.eventloop")

    # Assert there are no errors in the console and we set the right
    # backend.
    control = ipyconsole.get_widget().get_focus_widget()
    assert 'NOTE' not in control.toPlainText()
    assert 'Error' not in control.toPlainText()
    assert ('loop_qt5' in control.toPlainText() or
            'loop_qt' in control.toPlainText())


@flaky(max_runs=3)
@pytest.mark.tk_backend
@pytest.mark.skipif(
    os.name == 'nt' and (parse(ipykernel_version) == parse('6.21.0')),
    reason="Fails on Windows with IPykernel 6.21.0")
def test_tk_backend(ipyconsole, qtbot):
    """Test that the Tkinter backend was set correctly."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("get_ipython().kernel.eventloop")

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
@pytest.mark.xfail(parse('1.0') < parse(sympy.__version__) < parse('1.2'),
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
     parse(ipy_release.version) == parse('7.11.0')),
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
@pytest.mark.order(1)
@pytest.mark.environment_client
@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason='Only works with Anaconda'
)
@pytest.mark.skipif(not running_in_ci(), reason='Only works on CIs')
@pytest.mark.skipif(not os.name == 'nt', reason='Works reliably on Windows')
def test_environment_client(ipyconsole, qtbot):
    """
    Test that when creating a console for a specific conda environment, the
    environment is activated before a kernel is created for it.
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

    # Check console name
    client = ipyconsole.get_current_client()
    client.get_name() == "spytest-ž 1/A"

    # Get conda activation environment variable
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            "import os; conda_prefix = os.environ.get('CONDA_PREFIX')"
        )

    expected_output = get_conda_test_env()[0].replace('\\', '/')
    output = shell.get_value('conda_prefix').replace('\\', '/')
    assert expected_output == output


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
        shell.execute("import os; a = os.environ.get('SPY_TESTING')")

    # Assert we get the assigned value correctly
    assert shell.get_value('a') == 'True'


@flaky(max_runs=3)
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
def test_console_disambiguation(tmp_path, ipyconsole, qtbot):
    """Test the disambiguation of dedicated consoles."""
    # Create directories and file for tmp_path/a/b/c.py
    # and tmp_path/a/d/c.py
    dir_b = osp.join(tmp_path, 'a', 'b')
    filename_b =  osp.join(dir_b, 'c.py')
    if not osp.isdir(dir_b):
        os.makedirs(dir_b)
    if not osp.isfile(filename_b):
        file_c = open(filename_b, 'w+')
        file_c.close()
    dir_d = osp.join(tmp_path, 'a', 'd')
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
    savetemp = shell.get_cwd()
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
    savetemp = shell.get_cwd()
    tempdir = to_text_string(tmpdir.mkdir("queen's"))
    assert shell.get_cwd() != tempdir

    # Need to escape \ on Windows.
    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\", u"\\\\")

    # Change directory in the console.
    with qtbot.waitSignal(shell.executed):
        shell.execute(u"import os; os.chdir(u'''{}''')".format(tempdir))

    if os.name == 'nt':
        tempdir = tempdir.replace(u"\\\\", u"\\")

    assert shell.get_cwd() == tempdir

    shell.set_cwd(savetemp)


@flaky(max_runs=3)
def test_request_env(ipyconsole, qtbot):
    """Test that getting env vars from the kernel is working as expected."""
    shell = ipyconsole.get_current_shellwidget()

    # Add a new entry to os.environ
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; os.environ['FOO'] = 'bar'")

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
@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Fails on Windows and Mac"
)
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
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
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
@pytest.mark.skipif(sys.platform == "darwin", reason="Hangs on Mac")
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


@flaky(max_runs=10)
@pytest.mark.no_xvfb
@pytest.mark.skipif(
    (running_in_ci() and os.name == 'nt') or sys.platform == "darwin",
    reason="Hangs on CIs for Windows and Mac"
)
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
@pytest.mark.skipif(sys.platform == "darwin", reason="Hangs on Mac")
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
    shell.set_kernel_configuration("pdb", {'pdb_execute_events': True})

    # Test reset magic
    qtbot.keyClicks(control, 'plt.plot(range(10))')
    with qtbot.waitSignal(shell.executed):
        qtbot.keyClick(control, Qt.Key_Enter)

    # Assert that there's a plot in the console
    assert shell._control.toHtml().count('img src') == 1

    # Set processing events to False
    ipyconsole.set_conf('pdb_execute_events', False, section='debugger')
    shell.set_kernel_configuration("pdb", {'pdb_execute_events': False})

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
@pytest.mark.skipif(
    not os.name == 'nt' and running_in_ci(),
    reason="Fails on Linux/Mac and CIs")
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
@pytest.mark.skipif(
    os.name == 'nt' or sys.platform == "darwin",
    reason="Doesn't work on Windows and hangs on Mac"
)
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
    mocker.patch.object(ShellWidget, "send_spyder_kernel_configuration")

    ipyconsole.create_new_client()

    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=SHELL_TIMEOUT)

    # Do an assignment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Write something to stderr to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; sys.__stderr__.write("HEL"+"LO")')

    qtbot.waitUntil(
        lambda: 'HELLO' in shell._control.toPlainText(), timeout=SHELL_TIMEOUT)

    # Restart kernel and wait until it's up again.
    # NOTE: We trigger the restart_action instead of calling `restart_kernel`
    # directly to also check that that action is working as expected and avoid
    # regressions such as spyder-ide/spyder#22084.
    shell._prompt_html = None
    ipyconsole.get_widget().restart_action.trigger()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=SHELL_TIMEOUT)

    assert 'Restarting kernel...' in shell._control.toPlainText()
    assert 'HELLO' not in shell._control.toPlainText()
    assert not shell.is_defined('a')

    # Check that we send configuration at the beginning and after the restart.
    qtbot.waitUntil(
        lambda: ShellWidget.send_spyder_kernel_configuration.call_count == 2)


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
@pytest.mark.skipif(sys.platform == 'darwin',
                    reason="Fails sometimes on macOS")
def test_kernel_crash(ipyconsole, qtbot):
    """Test that we show an error message when a kernel crash occurs."""
    # Create an IPython kernel config file with a bad config
    ipy_kernel_cfg = osp.join(get_ipython_dir(), 'profile_default',
                              'ipython_config.py')
    try:
        with open(ipy_kernel_cfg, 'w') as f:
            # This option must be a string, not an int
            f.write("c.InteractiveShellApp.extra_extensions = 1")

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

        # Wait until the error has been received by the cached kernel_handler
        qtbot.waitUntil(lambda: bool(
            ipyconsole.get_widget()._cached_kernel_properties[-1]._init_stderr
        ))

        # Create a new client
        ipyconsole.create_new_client()

        # Assert that the console is showing an error
        error_client = ipyconsole.get_clients()[-1]
        qtbot.waitUntil(lambda: bool(error_client.error_text), timeout=6000)
    finally:
        # Remove bad kernel config file
        os.remove(ipy_kernel_cfg)


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
@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason="Only works on Linux")
@pytest.mark.skipif(
    parse('8.7.0') < parse(ipy_release.version) < parse('8.11.0'),
    reason="Fails for IPython 8.8.0, 8.9.0 and 8.10.0")
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

    # Test completions with one result
    with qtbot.waitSignal(shell.executed):
        shell.execute('cbs = 1')
    qtbot.waitUntil(lambda: check_value('cbs', 1))
    qtbot.wait(500)

    qtbot.keyClicks(control, 'cb')
    qtbot.keyClick(control, Qt.Key_Tab)
    # Jedi completion takes time to start up the first time
    qtbot.waitUntil(lambda: control.toPlainText().split()[-1] == 'cbs',
                    timeout=6000)

    # Test completions with several results
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

    # Check that we don't get repeated text after completing the expression
    # below.
    # This is a regression test for issue spyder-ide/spyder#20393
    with qtbot.waitSignal(shell.executed):
        shell.execute('import pandas as pd')

    qtbot.keyClicks(control, 'test = pd.conc')
    qtbot.keyClick(control, Qt.Key_Tab)
    qtbot.wait(500)
    completed_text = control.toPlainText().splitlines()[-1].split(':')[-1]
    assert completed_text.strip() == 'test = pd.concat'

    # Enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('%debug print()')

    # Test complete in debug mode
    # Check abs is completed twice (as the cursor moves)
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
@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason='Only works with Anaconda'
)
@pytest.mark.skipif(not running_in_ci(), reason='Only works on CIs')
@pytest.mark.skipif(not os.name == 'nt', reason='Works reliably on Windows')
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
            "import os; conda_prefix = os.environ.get('CONDA_PREFIX')"
        )

    expected_output = get_conda_test_env()[0].replace('\\', '/')
    output = shell.get_value('conda_prefix').replace('\\', '/')
    assert expected_output == output


@flaky(max_runs=3)
@pytest.mark.parametrize("external_interpreter", [True, False])
@pytest.mark.skipif(os.name == 'nt', reason="no SIGTERM on Windows")
def test_kernel_kill(ipyconsole, qtbot, external_interpreter):
    """
    Test that the kernel correctly restarts after a kill.
    """
    if external_interpreter:
        if running_in_ci():
            ipyconsole.set_conf('default', False, section='main_interpreter')
            pyexec = get_conda_test_env()[1]
            ipyconsole.set_conf(
                'executable', pyexec, section='main_interpreter'
            )
            ipyconsole.create_new_client()
        else:
            # We can't check this locally
            return

    shell = ipyconsole.get_current_shellwidget()

    # Wait for the restarter to start
    qtbot.wait(3000)
    crash_string = 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)'

    # Check only one comm is open
    old_open_comms = list(shell.kernel_handler.kernel_comm._comms.keys())
    assert len(old_open_comms) == 1
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=30000):
        shell.execute(crash_string)

    console_text = shell._control.toPlainText()
    assert crash_string in console_text
    assert "The kernel died, restarting..." in console_text

    # Check we don't show error generated by `conda run`
    assert "conda.cli.main_run" not in console_text

    # Check IPython version is shown as expected
    assert list(re.finditer(r"IPython \d+\.", console_text))

    # Check a new comm replaced the old one
    new_open_comms = list(shell.kernel_handler.kernel_comm._comms.keys())
    assert len(new_open_comms) == 1
    assert old_open_comms[0] != new_open_comms[0]

    # Wait until the comm replies
    qtbot.waitUntil(
        lambda: shell.kernel_handler.kernel_comm._comms[new_open_comms[0]][
            'status'] == 'ready'
    )

    assert shell.kernel_handler.kernel_comm._comms[new_open_comms[0]][
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
        ipyconsole.set_conf('spyder_pythonpath', [str(tmpdir)],
                            section='pythonpath_manager')
    else:
        wrong_random_mod = osp.join(os.getcwd(), 'random.py')
        with open(wrong_random_mod, 'w') as f:
            f.write('')

    # Create a new client to see if its kernel starts despite the
    # faulty module.
    ipyconsole.create_new_client()

    # A prompt should be created if the kernel didn't crash.
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
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
    ipyconsole.set_conf('spyder_pythonpath', [], section='pythonpath_manager')


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

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    ipyconsole.restart_kernel()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
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
    open_comms = list(shell.kernel_handler.kernel_comm._comms.keys())
    qtbot.waitUntil(
        lambda: shell.kernel_handler.kernel_comm._comms[open_comms[0]][
            'status'] == 'ready')


@flaky(max_runs=3)
def test_stderr_poll(ipyconsole, qtbot):
    """Test if the content of stderr is printed to the console."""
    shell = ipyconsole.get_current_shellwidget()
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            'import sys; print("test_" + "test", file=sys.__stderr__)')

    # Wait for the poll
    qtbot.waitUntil(
        lambda: "test_test"
        in ipyconsole.get_widget().get_focus_widget().toPlainText()
    )
    assert (
        "test_test" in ipyconsole.get_widget().get_focus_widget().toPlainText()
    )
    # Write a second time, makes sure it is not duplicated
    with qtbot.waitSignal(shell.executed):
        shell.execute(
            'import sys; print("test_" + "test", file=sys.__stderr__)')
    # Wait for the poll
    qtbot.waitUntil(
        lambda: ipyconsole.get_widget()
        .get_focus_widget()
        .toPlainText()
        .count("test_test")
        == 2
    )
    assert (
        ipyconsole.get_widget()
        .get_focus_widget()
        .toPlainText()
        .count("test_test")
        == 2
    )


@flaky(max_runs=3)
def test_stdout_poll(ipyconsole, qtbot):
    """Test if the content of stdout is printed to the console."""
    shell = ipyconsole.get_current_shellwidget()
    with qtbot.waitSignal(shell.executed):
        shell.execute('import sys; print("test_test", file=sys.__stdout__)')

    # Wait for the poll
    qtbot.waitUntil(
        lambda: "test_test"
        in ipyconsole.get_widget().get_focus_widget().toPlainText(),
        timeout=5000,
    )


@flaky(max_runs=10)
def test_startup_code_pdb(ipyconsole, qtbot):
    """Test that startup code for pdb works."""
    shell = ipyconsole.get_current_shellwidget()

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
    ['inline', 'qt', 'tk', 'osx']
)
@pytest.mark.skipif(sys.platform == 'darwin', reason="Hangs frequently on Mac")
def test_pdb_eventloop(ipyconsole, qtbot, backend):
    """Check if setting an event loop while debugging works."""
    # Skip failing tests
    if backend == 'osx' and sys.platform != "darwin":
        return
    if backend == 'qt' and not os.name == "nt" and running_in_ci():
        return

    shell = ipyconsole.get_current_shellwidget()
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
    control = ipyconsole.get_widget().get_focus_widget()

    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("abab = 10")
    # Check that we can use magic to enter recursive debugger
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("%debug print()")
    assert "(IPdb [1]):" in control.toPlainText()
    # Check we can enter the recursive debugger twice
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!debug print()")
    assert "((IPdb [1])):" in control.toPlainText()
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!debug print()")
    assert "(((IPdb [1]))):" in control.toPlainText()
    # Quit two layers
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute("!quit")
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
    assert control.toPlainText().split()[-2:] == ["IPdb", "[3]:"]
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


def test_pdb_magics_are_recursive(ipyconsole, qtbot, tmp_path):
    """
    Check that calls to Pdb magics start a recursive debugger when called in
    a debugging session.
    """
    shell = ipyconsole.get_current_shellwidget()
    control = ipyconsole.get_widget().get_focus_widget()

    # Code to run
    code = "a = 10\n\n# %%\n\nb = 20"

    # Write code to file on disk
    file = tmp_path / 'test_pdb_magics.py'
    file.write_text(code)

    # Filename in the format used when running magics from the main toolbar
    fname = str(file).replace('\\', '/')

    # Run file
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"%debugfile {fname}")

    # Run %debugfile in debugger
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute(f"%debugfile {fname}")

    # Check that there are no errors and we started a recursive debugger
    assert "error" not in control.toPlainText().lower()
    assert "(IPdb [1]):" in control.toPlainText()

    # Run %debugcell in debugger
    with qtbot.waitSignal(shell.executed):
        shell.pdb_execute(f"%debugcell -i 0 {fname}")

    # Check that there are no errors and we started a recursive debugger
    assert "error" not in control.toPlainText().lower()
    assert "((IPdb [1])):" in control.toPlainText()


@flaky(max_runs=3)
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on windows")
def test_stop_pdb(ipyconsole, qtbot):
    """Test if we can stop pdb"""
    shell = ipyconsole.get_current_shellwidget()
    control = ipyconsole.get_widget().get_focus_widget()
    stop_button = ipyconsole.get_widget().stop_button
    # Enter pdb
    with qtbot.waitSignal(shell.executed):
        shell.execute("%debug print()")
    # Start and interrupt a long execution
    shell.execute("import time; time.sleep(10)")
    qtbot.wait(500)
    with qtbot.waitSignal(shell.executed, timeout=10000):
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
def test_pdb_code_and_cmd_separation(ipyconsole, qtbot):
    """Check commands and code are separted."""
    shell = ipyconsole.get_current_shellwidget()
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
        shell.execute(f"%runfile {repr(str(file))}")

    # Assert we entered debugging after the print statement
    qtbot.wait(5000)
    assert 'foo' in control.toPlainText()
    assert 'IPdb [1]:' in control.toPlainText()


def test_pdb_out(ipyconsole, qtbot):
    """Test that browsing command history is working while debugging."""
    shell = ipyconsole.get_current_shellwidget()

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
@pytest.mark.skipif(
    parse(spyder_kernels_version) < parse("3.0.0.dev0"),
    reason="Not reliable with Spyder-kernels 2")
def test_shutdown_kernel(ipyconsole, qtbot):
    """
    Check that the kernel is shutdown after creating plots with the
    automatic backend.

    This is a regression test for issue spyder-ide/spyder#17011
    """
    shell = ipyconsole.get_current_shellwidget()
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
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
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
    control = ipyconsole.get_widget().get_focus_widget()

    # Code to run
    code = "locals = 1\nx = [locals + i for i in range(2)]"

    # Write code to file on disk
    file = tmpdir.join('test_breakpoint.py')
    file.write(code)

    # Run file
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"%debugfile {repr(str(file))}")

    # steps into the comprehension
    comprehension_steps = 2 if PY312_OR_GREATER else 4
    for i in range(comprehension_steps):
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
        'show_special_attributes': False,
        'filter_on': True
    }

    shell.set_kernel_configuration("namespace_view_settings", settings)
    namespace = shell.call_kernel(blocking=True).get_namespace_view()
    for key in namespace:
        assert "_spyderpdb" not in key


@flaky(max_runs=10)
@pytest.mark.auto_backend
def test_restart_interactive_backend(ipyconsole, qtbot):
    """
    Test that we ask for a restart or not after switching to different
    interactive backends.

    Also, check that we show the right backend in the Matplotlib status widget.
    """
    shell = ipyconsole.get_current_shellwidget()
    matplotlib_status = ipyconsole.get_widget().matplotlib_status

    # This is necessary to test no spurious messages are printed to the console
    shell.clear_console()
    empty_console_text = '\n\nIn [2]: ' if os.name == "nt" else '\nIn [2]: '
    qtbot.waitUntil(lambda: empty_console_text == shell._control.toPlainText())

    # Switch to the tk backend
    ipyconsole.set_conf('pylab/backend', 'tk')
    assert bool(os.environ.get('BACKEND_REQUIRE_RESTART'))
    assert shell.get_matplotlib_backend() == "qt"
    assert matplotlib_status.value == "Qt"

    # Switch to the inline backend
    os.environ.pop('BACKEND_REQUIRE_RESTART')
    ipyconsole.set_conf('pylab/backend', 'inline')
    assert not bool(os.environ.get('BACKEND_REQUIRE_RESTART'))
    qtbot.waitUntil(lambda: shell.get_matplotlib_backend() == "inline")
    assert matplotlib_status.value == "Inline"

    # Switch to the auto backend
    ipyconsole.set_conf('pylab/backend', 'auto')
    assert not bool(os.environ.get('BACKEND_REQUIRE_RESTART'))
    qtbot.waitUntil(lambda: shell.get_matplotlib_backend() == "qt")
    assert matplotlib_status.value == "Qt"

    # Switch to the qt backend
    ipyconsole.set_conf('pylab/backend', 'qt')
    assert not bool(os.environ.get('BACKEND_REQUIRE_RESTART'))
    assert matplotlib_status.value == "Qt"

    # Switch to the tk backend again
    ipyconsole.set_conf('pylab/backend', 'tk')
    assert bool(os.environ.get('BACKEND_REQUIRE_RESTART'))

    # Check we no spurious messages are shown before the restart below
    assert empty_console_text == shell._control.toPlainText()

    # Restart kernel to check if the new interactive backend is set
    ipyconsole.restart_kernel()
    qtbot.waitUntil(lambda: shell.spyder_kernel_ready, timeout=SHELL_TIMEOUT)
    qtbot.wait(SHELL_TIMEOUT)
    qtbot.waitUntil(lambda: shell.get_matplotlib_backend() == "tk")
    assert shell.get_mpl_interactive_backend() == "tk"
    assert matplotlib_status.value == "Tk"


def test_mpl_conf(ipyconsole, qtbot):
    """
    Test that after setting matplotlib-related config options, the member
    function send_mpl_backend of the shellwidget is called with the new value.
    """
    main_widget = ipyconsole.get_widget()
    client = main_widget.get_current_client()
    with patch.object(client.shellwidget, 'send_mpl_backend') as mock:
        main_widget.set_conf('pylab/inline/fontsize', 20.5)
    mock.assert_called_once_with({'pylab/inline/fontsize': 20.5})
    with patch.object(client.shellwidget, 'send_mpl_backend') as mock:
        main_widget.set_conf('pylab/inline/bottom', 0.314)
    mock.assert_called_once_with({'pylab/inline/bottom': 0.314})


def test_matplotlib_rc_params(mpl_rc_file, ipyconsole, qtbot):
    """
    Test that Matplotlib rcParams are correctly set/reset when changing
    backends and setting inline preferences.
    """
    rc_file = os.getenv('MATPLOTLIBRC')
    assert rc_file is not None
    assert osp.exists(rc_file)

    main_widget = ipyconsole.get_widget()
    shell = ipyconsole.get_current_shellwidget()
    assert shell.get_matplotlib_backend().lower() == 'inline'

    with qtbot.waitSignal(shell.executed):
        shell.execute(
            'import matplotlib as mpl;'
            'rcp = mpl.rcParams;'
            'rc_file = mpl.matplotlib_fname()'
        )

    # Test that the rc file is loaded
    assert rc_file == shell.get_value('rc_file')

    # Test that inline preferences are at defaults
    rcp = shell.get_value('rcp')
    assert rcp['figure.dpi'] == 144
    assert rcp['figure.figsize'] == [6, 4]
    assert rcp['figure.subplot.bottom'] == 0.11
    assert rcp['font.size'] == 10

    # Test that changing inline preferences are effective immediately
    def set_conf(option, value):
        main_widget.set_conf(option, value)
        # Allow time for the %config magic to run for each config change
        qtbot.wait(20)

    set_conf('pylab/inline/resolution', 112)
    set_conf('pylab/inline/width', 12)
    set_conf('pylab/inline/height', 12)
    set_conf('pylab/inline/bottom', 0.12)
    set_conf('pylab/inline/fontsize', 12)
    rcp = shell.get_value('rcp')
    assert rcp['figure.dpi'] == 112
    assert rcp['figure.figsize'] == [12, 12]
    assert rcp['figure.subplot.bottom'] == 0.12
    assert rcp['font.size'] == 12

    # Test that setting explicitly does not persist on backend change
    with qtbot.waitSignal(shell.executed):
        shell.execute('mpl.rcParams["font.size"] = 15')

    # Test that file defaults are restored on backend change
    with qtbot.waitSignal(shell.executed):
        shell.execute('%matplotlib qt')
    assert shell.get_matplotlib_backend().lower() == 'qt'
    rcp = shell.get_value('rcp')
    assert rcp['figure.dpi'] == 99
    assert rcp['figure.figsize'] == [9, 9]
    assert rcp['figure.subplot.bottom'] == 0.9
    assert rcp['font.size'] == 9

    # Test that setting explicitly does not persist on backend change
    with qtbot.waitSignal(shell.executed):
        shell.execute('mpl.rcParams["font.size"] = 15')

    # Test that inline preferences are restored on backend change
    with qtbot.waitSignal(shell.executed):
        shell.execute('%matplotlib inline')
    rcp = shell.get_value('rcp')
    assert rcp['figure.dpi'] == 112
    assert rcp['figure.figsize'] == [12, 12]
    assert rcp['figure.subplot.bottom'] == 0.12
    assert rcp['font.size'] == 12


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
        qtbot.waitUntil(
            lambda: shell.spyder_kernel_ready
            and shell._prompt_html is not None,
            timeout=SHELL_TIMEOUT
        )

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


@flaky(max_runs=10)
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
        section='pythonpath_manager')

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
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=SHELL_TIMEOUT)
    qtbot.wait(500)
    assert shell.get_value('pi')

    # Reset config for the 'spyder_pythonpath' and 'startup/run_lines'
    ipyconsole.set_conf(
        'spyder_pythonpath',
        [],
        section='pythonpath_manager')
    ipyconsole.set_conf(
        'startup/run_lines',
        '',
        section='ipython_console')


def test_varexp_magic_dbg_locals(ipyconsole, qtbot):
    """Test that %varexp is working while debugging locals."""

    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()

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

    kernel_handler = w._cached_kernel_properties[-1]
    kernel_handler.kernel_client.sig_spyder_kernel_info.disconnect()

    # Wait until it is launched
    qtbot.waitUntil(
        lambda: kernel_handler._comm_ready_received, timeout=SHELL_TIMEOUT
    )

    # Set wrong version
    kernel_handler.check_spyder_kernel_info(('1.0.0', ''))

    # Create new client
    w.create_new_client()

    # Make sure an error is shown
    info_page = w.get_current_client().infowidget.page()

    qtbot.waitUntil(
        lambda: check_text(info_page, "1.0.0"), timeout=6000
    )
    qtbot.waitUntil(
        lambda: check_text(info_page, "pip install spyder"), timeout=6000
    )


def test_run_script(ipyconsole, qtbot, tmp_path):
    """
    Test running multiple scripts at the same time.

    This is a regression test for issue spyder-ide/spyder#15405
    """
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


@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason="Only works with Anaconda"
)
def test_show_spyder_kernels_error_on_restart(ipyconsole, qtbot):
    """Test that we show Spyder-kernels error message on restarts."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Point to an interpreter without Spyder-kernels
    ipyconsole.set_conf('default', False, section='main_interpreter')
    pyexec = get_list_conda_envs()['Conda: base'][0]
    ipyconsole.set_conf('executable', pyexec, section='main_interpreter')

    # Restart kernel
    ipyconsole.restart_kernel()

    # Assert we show a kernel error
    info_page = ipyconsole.get_current_client().infowidget.page()

    qtbot.waitUntil(
        lambda: check_text(
            info_page,
            "The Python environment or installation"
        ),
        timeout=6000
    )

    # To check the kernel error visually
    qtbot.wait(500)

    # Check kernel related actions are disabled when accessing Options menu
    main_widget = ipyconsole.get_widget()
    main_widget._options_menu.aboutToShow.emit()
    assert not main_widget.restart_action.isEnabled()
    assert not main_widget.reset_action.isEnabled()
    assert not main_widget.env_action.isEnabled()
    assert not main_widget.syspath_action.isEnabled()
    assert not main_widget.show_time_action.isEnabled()


@pytest.mark.skipif(not sys.platform == "darwin", reason="Only works on Mac")
def test_restore_tmpdir(ipyconsole, qtbot, tmp_path):
    """
    Check the TMPDIR env var is available in the kernel if it is in the system.
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT
    )

    # Save the system TMPDIR
    system_tmpdir = os.environ["TMPDIR"]

    # Check it's the same in the kernel
    with qtbot.waitSignal(shell.executed):
        shell.execute("import os; tmpdir = os.environ.get('TMPDIR')")

    assert shell.get_value('tmpdir') == system_tmpdir


def test_floats_selected_on_double_click(ipyconsole, qtbot):
    """
    Check that doing a double click on floats selects the entire number.

    This is a regression test for issue spyder-ide/spyder#22207
    """
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT
    )

    # Write a floating point number
    control = shell._control
    float_number = "10.999e5"
    qtbot.keyClicks(control, float_number)

    # Move the cursor to the left a bit
    for __ in range(3):
        control.moveCursor(QTextCursor.Left, mode=QTextCursor.MoveAnchor)

    # Perform a double click and check the entire number was selected
    qtbot.mouseDClick(control.viewport(), Qt.LeftButton)
    assert control.get_selected_text() == float_number

    # Move cursor at the beginning and check the number is also selected
    qtbot.keyClick(control, Qt.Key_Home)
    qtbot.mouseDClick(control.viewport(), Qt.LeftButton)
    assert control.get_selected_text() == float_number


def test_filter_frames_in_tracebacks(ipyconsole, qtbot, tmp_path):
    """Check that we filter some unnecessary frames in tracebacks."""
    # Wait until the window is fully up
    shell = ipyconsole.get_current_shellwidget()
    control = shell._control
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT
    )

    # Write code to file
    file = tmp_path / 'test_filter_frames.py'
    file.write_text("# Comment\n1/0")

    # Filename in the format used when running magics from the main toolbar
    fname = str(file).replace('\\', '/')

    # Run file
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"%runfile {fname}")

    # Check frames related to spyder-kernels are not displayed
    assert "spyder_kernels" not in control.toPlainText()

    # Switch to %xmode plain and check again
    with qtbot.waitSignal(shell.executed):
        shell.execute("%xmode plain")

    with qtbot.waitSignal(shell.executed):
        shell.execute(f"%runfile {fname}")

    assert "spyder_kernels" not in control.toPlainText()

    # Switch back to %xmode verbose (the default)
    with qtbot.waitSignal(shell.executed):
        shell.execute("%xmode verbose")

    # Check we don't display a traceback when exiting our debugger if it's
    # started with breakpoint().
    file.write_text("# Comment\nbreakpoint()")
    with qtbot.waitSignal(shell.executed):
        shell.execute(f"%runfile {fname}")

    shell.clear_console()
    empty_console_text = (
        "\n\nIPdb [2]: " if os.name == "nt" else "\nIPdb [2]: "
    )
    qtbot.waitUntil(lambda: empty_console_text == control.toPlainText())

    with qtbot.waitSignal(shell.executed):
        qtbot.keyClicks(control, '!exit')
        qtbot.keyClick(control, Qt.Key_Enter)

    assert "BdbQuit" not in control.toPlainText()


if __name__ == "__main__":
    pytest.main()
