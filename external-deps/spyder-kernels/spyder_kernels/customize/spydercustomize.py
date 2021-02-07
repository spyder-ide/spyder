#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------
#
# IMPORTANT NOTE: Don't add a coding line here! It's not necessary for
# site files
#
# Spyder consoles sitecustomize
#

import bdb
import cmd
import io
import logging
import os
import pdb
import shlex
import sys
import time
import warnings

from IPython import __version__ as ipy_version
from IPython.core.getipython import get_ipython

from spyder_kernels.comms.frontendcomm import CommError, frontend_request
from spyder_kernels.customize.namespace_manager import NamespaceManager
from spyder_kernels.customize.spyderpdb import SpyderPdb, enter_debugger
from spyder_kernels.customize.umr import UserModuleReloader
from spyder_kernels.py3compat import TimeoutError, PY2, _print, encode

if not PY2:
    from IPython.core.inputtransformer2 import (
        TransformerManager, leading_indent, leading_empty_lines)
else:
    from IPython.core.inputsplitter import IPythonInputSplitter


logger = logging.getLogger(__name__)


# =============================================================================
# sys.argv can be missing when Python is embedded, taking care of it.
# Fixes Issue 1473 and other crazy crashes with IPython 0.13 trying to
# access it.
# =============================================================================
if not hasattr(sys, 'argv'):
    sys.argv = ['']


# =============================================================================
# Main constants
# =============================================================================
IS_EXT_INTERPRETER = os.environ.get('SPY_EXTERNAL_INTERPRETER') == "True"
HIDE_CMD_WINDOWS = os.environ.get('SPY_HIDE_CMD') == "True"
SHOW_INVALID_SYNTAX_MSG = True


# =============================================================================
# Execfile functions
#
# The definitions for Python 2 on Windows were taken from the IPython project
# Copyright (C) The IPython Development Team
# Distributed under the terms of the modified BSD license
# =============================================================================
try:
    # Python 2
    import __builtin__ as builtins

except ImportError:
    # Python 3
    import builtins
    basestring = (str,)


# =============================================================================
# Setting console encoding (otherwise Python does not recognize encoding)
# for Windows platforms
# =============================================================================
if os.name == 'nt' and PY2:
    try:
        import locale, ctypes
        _t, _cp = locale.getdefaultlocale('LANG')
        try:
            _cp = int(_cp[2:])
            ctypes.windll.kernel32.SetConsoleCP(_cp)
            ctypes.windll.kernel32.SetConsoleOutputCP(_cp)
        except (ValueError, TypeError):
            # Code page number in locale is not valid
            pass
    except Exception:
        pass


# =============================================================================
# Prevent subprocess.Popen calls to create visible console windows on Windows.
# See issue #4932
# =============================================================================
if os.name == 'nt' and HIDE_CMD_WINDOWS:
    import subprocess
    creation_flag = 0x08000000  # CREATE_NO_WINDOW

    class SubprocessPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs['creationflags'] = creation_flag
            super(SubprocessPopen, self).__init__(*args, **kwargs)

    subprocess.Popen = SubprocessPopen

# =============================================================================
# Importing user's sitecustomize
# =============================================================================
try:
    import sitecustomize  #analysis:ignore
except Exception:
    pass


# =============================================================================
# Add default filesystem encoding on Linux to avoid an error with
# Matplotlib 1.5 in Python 2 (Fixes Issue 2793)
# =============================================================================
if PY2 and sys.platform.startswith('linux'):
    def _getfilesystemencoding_wrapper():
        return 'utf-8'

    sys.getfilesystemencoding = _getfilesystemencoding_wrapper


# =============================================================================
# Set PyQt API to #2
# =============================================================================
if os.environ.get("QT_API") == 'pyqt':
    try:
        import sip
        for qtype in ('QString', 'QVariant', 'QDate', 'QDateTime',
                      'QTextStream', 'QTime', 'QUrl'):
            sip.setapi(qtype, 2)
    except Exception:
        pass
else:
    try:
        os.environ.pop('QT_API')
    except KeyError:
        pass


# =============================================================================
# Patch PyQt4 and PyQt5
# =============================================================================
# This saves the QApplication instances so that Python doesn't destroy them.
# Python sees all the QApplication as differnet Python objects, while
# Qt sees them as a singleton (There is only one Application!). Deleting one
# QApplication causes all the other Python instances to become broken.
# See spyder-ide/spyder/issues/2970
try:
    from PyQt5 import QtWidgets

    class SpyderQApplication(QtWidgets.QApplication):
        def __init__(self, *args, **kwargs):
            super(SpyderQApplication, self).__init__(*args, **kwargs)
            # Add reference to avoid destruction
            # This creates a Memory leak but avoids a Segmentation fault
            SpyderQApplication._instance_list.append(self)

    SpyderQApplication._instance_list = []
    QtWidgets.QApplication = SpyderQApplication
except Exception:
    pass

try:
    from PyQt4 import QtGui

    class SpyderQApplication(QtGui.QApplication):
        def __init__(self, *args, **kwargs):
            super(SpyderQApplication, self).__init__(*args, **kwargs)
            # Add reference to avoid destruction
            # This creates a Memory leak but avoids a Segmentation fault
            SpyderQApplication._instance_list.append(self)

    SpyderQApplication._instance_list = []
    QtGui.QApplication = SpyderQApplication
except Exception:
    pass

# =============================================================================
# IPython adjustments
# =============================================================================
# Patch unittest.main so that errors are printed directly in the console.
# See http://comments.gmane.org/gmane.comp.python.ipython.devel/10557
# Fixes Issue 1370
import unittest
from unittest import TestProgram

class IPyTesProgram(TestProgram):
    def __init__(self, *args, **kwargs):
        test_runner = unittest.TextTestRunner(stream=sys.stderr)
        kwargs['testRunner'] = kwargs.pop('testRunner', test_runner)
        kwargs['exit'] = False
        TestProgram.__init__(self, *args, **kwargs)

unittest.main = IPyTesProgram

# Ignore some IPython/ipykernel warnings
try:
    warnings.filterwarnings(action='ignore', category=DeprecationWarning,
                            module='ipykernel.ipkernel')
except Exception:
    pass


# =============================================================================
# Turtle adjustments
# =============================================================================
# This is needed to prevent turtle scripts crashes after multiple runs in the
# same IPython Console instance.
# See Spyder issue #6278
try:
    import turtle
    from turtle import Screen, Terminator

    def spyder_bye():
        try:
            Screen().bye()
            turtle.TurtleScreen._RUNNING = True
        except Terminator:
            pass
    turtle.bye = spyder_bye
except Exception:
    pass


# =============================================================================
# Pandas adjustments
# =============================================================================
try:
    import pandas as pd

    # Set Pandas output encoding
    pd.options.display.encoding = 'utf-8'

    # Filter warning that appears for DataFrames with np.nan values
    # Example:
    # >>> import pandas as pd, numpy as np
    # >>> pd.Series([np.nan,np.nan,np.nan],index=[1,2,3])
    # Fixes Issue 2991
    # For 0.18-
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.core.format',
                            message=".*invalid value encountered in.*")
    # For 0.18.1+
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.formats.format',
                            message=".*invalid value encountered in.*")
except Exception:
    pass


# =============================================================================
# Numpy adjustments
# =============================================================================
try:
    # Filter warning that appears when users have 'Show max/min'
    # turned on and Numpy arrays contain a nan value.
    # Fixes Issue 7063
    # Note: It only happens in Numpy 1.14+
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='numpy.core._methods',
                            message=".*invalid value encountered in.*")
except Exception:
    pass


# =============================================================================
# Multiprocessing adjustments
# =============================================================================
# This patch is only needed on Python 3
if not PY2:
    # This could fail with changes in Python itself, so we protect it
    # with a try/except
    try:
        import multiprocessing.spawn
        _old_preparation_data = multiprocessing.spawn.get_preparation_data

        def _patched_preparation_data(name):
            """
            Patched get_preparation_data to work when all variables are
            removed before execution.
            """
            try:
                d = _old_preparation_data(name)
            except AttributeError:
                main_module = sys.modules['__main__']
                # Any string for __spec__ does the job
                main_module.__spec__ = ''
                d = _old_preparation_data(name)
            # On windows, there is no fork, so we need to save the main file
            # and import it
            if (os.name == 'nt' and 'init_main_from_path' in d
                    and not os.path.exists(d['init_main_from_path'])):
                _print(
                    "Warning: multiprocessing may need the main file to exist. "
                    "Please save {}".format(d['init_main_from_path']))
                # Remove path as the subprocess can't do anything with it
                del d['init_main_from_path']
            return d
        multiprocessing.spawn.get_preparation_data = _patched_preparation_data
    except Exception:
        pass


# =============================================================================
# Pdb adjustments
# =============================================================================
def cmd_input(prompt=''):
    return get_ipython().kernel.cmd_input(prompt)


pdb.Pdb = SpyderPdb

if PY2:
    cmd.raw_input = cmd_input
else:
    cmd.input = cmd_input


# =============================================================================
# User module reloader
# =============================================================================
__umr__ = UserModuleReloader(namelist=os.environ.get("SPY_UMR_NAMELIST", None))


# =============================================================================
# Handle Post Mortem Debugging and Traceback Linkage to Spyder
# =============================================================================
def post_mortem_excepthook(type, value, tb):
    """
    For post mortem exception handling, print a banner and enable post
    mortem debugging.
    """
    ipython_shell = get_ipython()
    ipython_shell.showtraceback((type, value, tb))
    p = pdb.Pdb(ipython_shell.colors)

    if not type == SyntaxError:
        # wait for stderr to print (stderr.flush does not work in this case)
        time.sleep(0.1)
        _print('*' * 40)
        _print('Entering post mortem debugging...')
        _print('*' * 40)
        #  add ability to move between frames
        p.send_initial_notification = False
        p.reset()
        frame = tb.tb_next.tb_frame
        # wait for stdout to print
        time.sleep(0.1)
        p.interaction(frame, tb)


# ==============================================================================
# runfile and debugfile commands
# ==============================================================================
def get_current_file_name():
    """Get the current file name."""
    try:
        return frontend_request().current_filename()
    except Exception:
        _print("This command failed to be executed because an error occurred"
               " while trying to get the current file name from Spyder's"
               " editor. The error was:\n\n")
        get_ipython().showtraceback(exception_only=True)
        return None


def count_leading_empty_lines(cell):
    """Count the number of leading empty cells."""
    if PY2:
        lines = cell.splitlines(True)
    else:
        lines = cell.splitlines(keepends=True)
    if not lines:
        return 0
    for i, line in enumerate(lines):
        if line and not line.isspace():
            return i
    return len(lines)


def transform_cell(code, indent_only=False):
    """Transform IPython code to Python code."""
    number_empty_lines = count_leading_empty_lines(code)
    if indent_only:
        # Not implemented for PY2
        if PY2:
            return code
        if not code.endswith('\n'):
            code += '\n'  # Ensure the cell has a trailing newline
        lines = code.splitlines(keepends=True)
        lines = leading_indent(leading_empty_lines(lines))
        code = ''.join(lines)
    else:
        if PY2:
            tm = IPythonInputSplitter()
            return tm.transform_cell(code)
        else:
            tm = TransformerManager()
            code = tm.transform_cell(code)
    return '\n' * number_empty_lines + code


def exec_code(code, filename, ns_globals, ns_locals=None, post_mortem=False):
    """Execute code and display any exception."""
    # Tell IPython to hide this frame (>7.16)
    __tracebackhide__ = True
    global SHOW_INVALID_SYNTAX_MSG

    if PY2:
        filename = encode(filename)
        code = encode(code)

    ipython_shell = get_ipython()
    is_ipython = os.path.splitext(filename)[1] == '.ipy'
    try:
        if not is_ipython:
            # TODO: remove the try-except and let the SyntaxError raise
            # Because there should not be ipython code in a python file
            try:
                compiled = compile(
                    transform_cell(code, indent_only=True), filename, 'exec')
            except SyntaxError as e:
                try:
                    compiled = compile(transform_cell(code), filename, 'exec')
                except SyntaxError:
                    if PY2:
                        raise e
                    else:
                        # Need to call exec to avoid Syntax Error in Python 2.
                        # TODO: remove exec when dropping Python 2 support.
                        exec("raise e from None")
                else:
                    if SHOW_INVALID_SYNTAX_MSG:
                        _print(
                            "\nWARNING: This is not valid Python code. "
                            "If you want to use IPython magics, "
                            "flexible indentation, and prompt removal, "
                            "we recommend that you save this file with the "
                            ".ipy extension.\n")
                        SHOW_INVALID_SYNTAX_MSG = False
        else:
            compiled = compile(transform_cell(code), filename, 'exec')
        exec(compiled, ns_globals, ns_locals)
    except SystemExit as status:
        # ignore exit(0)
        if status.code:
            ipython_shell.showtraceback(exception_only=True)
    except BaseException as error:
        if (isinstance(error, bdb.BdbQuit)
                and ipython_shell.kernel._pdb_obj):
            # Ignore BdbQuit if we are debugging, as it is expected.
            ipython_shell.kernel._pdb_obj = None
        elif post_mortem and isinstance(error, Exception):
            error_type, error, tb = sys.exc_info()
            post_mortem_excepthook(error_type, error, tb)
        else:
            # We ignore the call to exec
            ipython_shell.showtraceback(tb_offset=1)
    __tracebackhide__ = "__pdb_exit__"


def get_file_code(filename, save_all=True):
    """Retrive the content of a file."""
    # Get code from spyder
    try:
        file_code = frontend_request().get_file_code(
            filename, save_all=save_all)
    except (CommError, TimeoutError):
        file_code = None
    if file_code is None:
        with open(filename, 'r') as f:
            return f.read()
    return file_code


def runfile(filename=None, args=None, wdir=None, namespace=None,
            post_mortem=False, current_namespace=False):
    """
    Run filename
    args: command line arguments (string)
    wdir: working directory
    namespace: namespace for execution
    post_mortem: boolean, whether to enter post-mortem mode on error
    current_namespace: if true, run the file in the current namespace
    """
    # Tell IPython to hide this frame (>7.16)
    __tracebackhide__ = True
    ipython_shell = get_ipython()
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return
    else:
        # get_debugger replaces \\ by / so we must undo that here
        # Otherwise code caching doesn't work
        if os.name == 'nt':
            filename = filename.replace('/', '\\')

    try:
        filename = filename.decode('utf-8')
    except (UnicodeError, TypeError, AttributeError):
        # UnicodeError, TypeError --> eventually raised in Python 2
        # AttributeError --> systematically raised in Python 3
        pass
    if PY2:
        filename = encode(filename)
    if __umr__.enabled:
        __umr__.run()
    if args is not None and not isinstance(args, basestring):
        raise TypeError("expected a character buffer object")
    try:
        file_code = get_file_code(filename)
    except Exception:
        _print(
            "This command failed to be executed because an error occurred"
            " while trying to get the file code from Spyder's"
            " editor. The error was:\n\n")
        get_ipython().showtraceback(exception_only=True)
        return
    if file_code is None:
        _print("Could not get code from editor.\n")
        return

    with NamespaceManager(filename, namespace, current_namespace,
                          file_code=file_code) as (ns_globals, ns_locals):
        sys.argv = [filename]
        if args is not None:
            for arg in shlex.split(args):
                sys.argv.append(arg)
        if wdir is not None:
            if PY2:
                try:
                    wdir = wdir.decode('utf-8')
                except (UnicodeError, TypeError):
                    # UnicodeError, TypeError --> eventually raised in Python 2
                    pass
            if os.path.isdir(wdir):
                os.chdir(wdir)
                # See https://github.com/spyder-ide/spyder/issues/13632
                if "multiprocessing.process" in sys.modules:
                    try:
                        import multiprocessing.process
                        multiprocessing.process.ORIGINAL_DIR = os.path.abspath(
                            wdir)
                    except Exception:
                        pass
            else:
                _print("Working directory {} doesn't exist.\n".format(wdir))

        if __umr__.has_cython:
            # Cython files
            with io.open(filename, encoding='utf-8') as f:
                ipython_shell.run_cell_magic('cython', '', f.read())
        else:
            exec_code(file_code, filename, ns_globals, ns_locals,
                      post_mortem=post_mortem)

        sys.argv = ['']


builtins.runfile = runfile


def debugfile(filename=None, args=None, wdir=None, post_mortem=False,
              current_namespace=False):
    """
    Debug filename
    args: command line arguments (string)
    wdir: working directory
    post_mortem: boolean, included for compatiblity with runfile
    """
    # Tell IPython to hide this frame (>7.16)
    __tracebackhide__ = True
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return

    enter_debugger(
        filename, True,
        "runfile({}" +
        ", args=%r, wdir=%r, current_namespace=%r)" % (
            args, wdir, current_namespace))


builtins.debugfile = debugfile


def runcell(cellname, filename=None, post_mortem=False):
    """
    Run a code cell from an editor as a file.

    Currently looks for code in an `ipython` property called `cell_code`.
    This property must be set by the editor prior to calling this function.
    This function deletes the contents of `cell_code` upon completion.

    Parameters
    ----------
    cellname : str or int
        Cell name or index.
    filename : str
        Needed to allow for proper traceback links.
    """
    # Tell IPython to hide this frame (>7.16)
    __tracebackhide__ = True
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return
    else:
        # get_debugger replaces \\ by / so we must undo that here
        # Otherwise code caching doesn't work
        if os.name == 'nt':
            filename = filename.replace('/', '\\')
    try:
        filename = filename.decode('utf-8')
    except (UnicodeError, TypeError, AttributeError):
        # UnicodeError, TypeError --> eventually raised in Python 2
        # AttributeError --> systematically raised in Python 3
        pass
    ipython_shell = get_ipython()
    try:
        # Get code from spyder
        cell_code = frontend_request().run_cell(cellname, filename)
    except Exception:
        _print("This command failed to be executed because an error occurred"
               " while trying to get the cell code from Spyder's"
               " editor. The error was:\n\n")
        get_ipython().showtraceback(exception_only=True)
        return

    if not cell_code or cell_code.strip() == '':
        _print("Nothing to execute, this cell is empty.\n")
        return

    # Trigger `post_execute` to exit the additional pre-execution.
    # See Spyder PR #7310.
    ipython_shell.events.trigger('post_execute')
    try:
        file_code = get_file_code(filename, save_all=False)
    except Exception:
        file_code = None
    with NamespaceManager(filename, current_namespace=True,
                          file_code=file_code) as (ns_globals, ns_locals):
        exec_code(cell_code, filename, ns_globals, ns_locals,
                  post_mortem=post_mortem)


builtins.runcell = runcell


def debugcell(cellname, filename=None, post_mortem=False):
    """Debug a cell."""
    # Tell IPython to hide this frame (>7.16)
    __tracebackhide__ = True
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return

    enter_debugger(
        filename, False,
        "runcell({}, ".format(repr(cellname)) +
        "{})")


builtins.debugcell = debugcell


def cell_count(filename=None):
    """
    Get the number of cells in a file.

    Parameters
    ----------
    filename : str
        The file to get the cells from. If None, the currently opened file.
    """
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            raise RuntimeError('Could not get cell count from frontend.')
    try:
        # Get code from spyder
        cell_count = frontend_request().cell_count(filename)
        return cell_count
    except Exception:
        etype, error, tb = sys.exc_info()
        raise etype(error)


builtins.cell_count = cell_count


# =============================================================================
# Extend sys.path with paths that come from Spyder
# =============================================================================
def set_spyder_pythonpath():
    pypath = os.environ.get('SPY_PYTHONPATH')
    if pypath:
        pathlist = pypath.split(os.pathsep)
        sys.path.extend(pathlist)

set_spyder_pythonpath()
