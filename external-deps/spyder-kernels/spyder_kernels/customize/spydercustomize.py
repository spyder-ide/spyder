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
import io
import os
import pdb
import shlex
import sys
import time
import warnings
import logging

from IPython.core.getipython import get_ipython

from spyder_kernels.py3compat import TimeoutError, PY2, _print, encode
from spyder_kernels.comms.frontendcomm import CommError, frontend_request
from spyder_kernels.customize.namespace_manager import NamespaceManager
from spyder_kernels.customize.spyderpdb import SpyderPdb
from spyder_kernels.customize.umr import UserModuleReloader

if not PY2:
    from IPython.core.inputtransformer2 import TransformerManager
else:
    from IPython.core.inputsplitter import IPythonInputSplitter as TransformerManager


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
# This patch is only needed on Windows and Python 3
if os.name == 'nt' and not PY2:
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
                return _old_preparation_data(name)
            except AttributeError:
                main_module = sys.modules['__main__']
                # Any string for __spec__ does the job
                main_module.__spec__ = ''
                return _old_preparation_data(name)

        multiprocessing.spawn.get_preparation_data = _patched_preparation_data
    except Exception:
        pass


# =============================================================================
# Pdb adjustments
# =============================================================================
pdb.Pdb = SpyderPdb


# =============================================================================
# User module reloader
# =============================================================================
__umr__ = UserModuleReloader(namelist=os.environ.get("SPY_UMR_NAMELIST", None))


# =============================================================================
# Handle Post Mortem Debugging and Traceback Linkage to Spyder
# =============================================================================
def clear_post_mortem():
    """
    Remove the post mortem excepthook and replace with a standard one.
    """
    ipython_shell = get_ipython()
    ipython_shell.set_custom_exc((), None)


def post_mortem_excepthook(type, value, tb):
    """
    For post mortem exception handling, print a banner and enable post
    mortem debugging.
    """
    clear_post_mortem()
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
        frame = tb.tb_frame
        prev = frame
        while frame.f_back:
            prev = frame
            frame = frame.f_back
        frame = prev
        # wait for stdout to print
        time.sleep(0.1)
        p.interaction(frame, tb)


def set_post_mortem():
    """
    Enable the post mortem debugging excepthook.
    """
    def ipython_post_mortem_debug(shell, etype, evalue, tb,
                                  tb_offset=None):
        post_mortem_excepthook(etype, evalue, tb)

    ipython_shell = get_ipython()
    ipython_shell.set_custom_exc((Exception,), ipython_post_mortem_debug)


# Add post mortem debugging if requested and in a dedicated interpreter
# existing interpreters use "runfile" below
if "SPYDER_EXCEPTHOOK" in os.environ:
    set_post_mortem()


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


def get_debugger(filename):
    """Get a debugger for a given filename."""
    debugger = pdb.Pdb()
    filename = debugger.canonic(filename)
    debugger._wait_for_mainpyfile = 1
    debugger.mainpyfile = filename
    debugger._user_requested_quit = 0
    if os.name == 'nt':
        filename = filename.replace('\\', '/')
    return debugger, filename


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


def transform_cell(code):
    """Transform ipython code to python code."""
    tm = TransformerManager()
    number_empty_lines = count_leading_empty_lines(code)
    code = tm.transform_cell(code)
    if PY2:
        return code
    return '\n' * number_empty_lines + code


def exec_code(code, filename, ns_globals, ns_locals=None):
    """Execute code and display any exception."""
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
                compiled = compile(code, filename, 'exec')
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
                            "please save this file with the .ipy extension. "
                            "This will be an error in a future version of "
                            "Spyder.\n")
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
        else:
            # We ignore the call to exec
            ipython_shell.showtraceback(tb_offset=1)


def get_file_code(filename):
    """Retrive the content of a file."""
    # Get code from spyder
    try:
        file_code = frontend_request().get_file_code(filename)
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
            try:
                wdir = wdir.decode('utf-8')
            except (UnicodeError, TypeError, AttributeError):
                # UnicodeError, TypeError --> eventually raised in Python 2
                # AttributeError --> systematically raised in Python 3
                pass
            if os.path.isdir(wdir):
                os.chdir(wdir)
            else:
                _print("Working directory {} doesn't exist.\n".format(wdir))
        if post_mortem:
            set_post_mortem()

        if __umr__.has_cython:
            # Cython files
            with io.open(filename, encoding='utf-8') as f:
                ipython_shell.run_cell_magic('cython', '', f.read())
        else:
            exec_code(file_code, filename, ns_globals, ns_locals)

        clear_post_mortem()
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
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return
    debugger, filename = get_debugger(filename)
    debugger.continue_if_has_breakpoints = True
    debugger.run("runfile(%r, args=%r, wdir=%r, current_namespace=%r)" % (
        filename, args, wdir, current_namespace))


builtins.debugfile = debugfile


def runcell(cellname, filename=None):
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
        file_code = get_file_code(filename)
    except Exception:
        file_code = None
    with NamespaceManager(filename, current_namespace=True,
                          file_code=file_code) as (ns_globals, ns_locals):
        exec_code(cell_code, filename, ns_globals, ns_locals)


builtins.runcell = runcell


def debugcell(cellname, filename=None):
    """Debug a cell."""
    if filename is None:
        filename = get_current_file_name()
        if filename is None:
            return

    debugger, filename = get_debugger(filename)
    # The breakpoint might not be in the cell
    debugger.continue_if_has_breakpoints = False
    debugger.run("runcell({}, {})".format(
        repr(cellname), repr(filename)))


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
# Restoring original PYTHONPATH
# =============================================================================
try:
    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
    del os.environ['OLD_PYTHONPATH']
except KeyError:
    pass
