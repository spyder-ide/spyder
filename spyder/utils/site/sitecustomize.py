#
# Copyright (c) Spyder Project Contributors)
# Licensed under the terms of the MIT License)
# (see spyder/__init__.py for details)
#
# IMPORTANT NOTE: Don't add a coding line here! It's not necessary for
# site files
#
# Spyder consoles sitecustomize
#

import sys
import os
import os.path as osp
import pdb
import bdb
import time
import traceback
import shlex


PY2 = sys.version[0] == '2'


#==============================================================================
# sys.argv can be missing when Python is embedded, taking care of it.
# Fixes Issue 1473 and other crazy crashes with IPython 0.13 trying to
# access it.
#==============================================================================
if not hasattr(sys, 'argv'):
    sys.argv = ['']


#==============================================================================
# Main constants
#==============================================================================
IS_IPYKERNEL = os.environ.get("IPYTHON_KERNEL", "").lower() == "true"
IS_EXT_INTERPRETER = os.environ.get('EXTERNAL_INTERPRETER', '').lower() == "true"


#==============================================================================
# Important Note:
#
# We avoid importing spyder here, so we are handling Python 3 compatiblity
# by hand.
#==============================================================================
def _print(*objects, **options):
    end = options.get('end', '\n')
    file = options.get('file', sys.stdout)
    sep = options.get('sep', ' ')
    string = sep.join([str(obj) for obj in objects])
    if not PY2:
        # Python 3
        local_dict = {}
        exec('printf = print', local_dict) # to avoid syntax error in Python 2
        local_dict['printf'](string, file=file, end=end, sep=sep)
    else:
        # Python 2
        if end:
            print >>file, string
        else:
            print >>file, string,


#==============================================================================
# Execfile functions
#
# The definitions for Python 2 on Windows were taken from the IPython project
# Copyright (C) The IPython Development Team
# Distributed under the terms of the modified BSD license
#==============================================================================
try:
    # Python 2
    import __builtin__ as builtins
    if os.name == 'nt':
        def encode(u):
            return u.encode('utf8', 'replace')
        def execfile(fname, glob=None, loc=None):
            loc = loc if (loc is not None) else glob
            scripttext = builtins.open(fname).read()+ '\n'
            # compile converts unicode filename to str assuming
            # ascii. Let's do the conversion before calling compile
            if isinstance(fname, unicode):
                filename = encode(fname)
            else:
                filename = fname
            exec(compile(scripttext, filename, 'exec'), glob, loc)
    else:
        def execfile(fname, *where):
            if isinstance(fname, unicode):
                filename = fname.encode(sys.getfilesystemencoding())
            else:
                filename = fname
            builtins.execfile(filename, *where)
except ImportError:
    # Python 3
    import builtins
    basestring = (str,)
    def execfile(filename, namespace):
        # Open a source file correctly, whatever its encoding is
        with open(filename, 'rb') as f:
            exec(compile(f.read(), filename, 'exec'), namespace)


#==============================================================================
# Colorization of sys.stderr (standard Python interpreter)
#==============================================================================
if os.environ.get("COLORIZE_SYS_STDERR", "").lower() == "true":
    class StderrProxy(object):
        """Proxy to sys.stderr file object overriding only the `write` method
        to provide red colorization for the whole stream, and blue-underlined
        for traceback file links"""
        def __init__(self):
            self.old_stderr = sys.stderr
            self.__buffer = ''
            sys.stderr = self

        def __getattr__(self, name):
            return getattr(self.old_stderr, name)

        def write(self, text):
            if os.name == 'nt' and '\n' not in text:
                self.__buffer += text
                return
            for text in (self.__buffer+text).splitlines(True):
                if text.startswith('  File') \
                and not text.startswith('  File "<'):
                    # Show error links in blue underlined text
                    colored_text = '  '+'\x1b[4;34m'+text[2:]+'\x1b[0m'
                else:
                    # Show error messages in red
                    colored_text = '\x1b[31m'+text+'\x1b[0m'
                self.old_stderr.write(colored_text)
            self.__buffer = ''

    stderrproxy = StderrProxy()


#==============================================================================
# Prepending this spyder package's path to sys.path to be sure
# that another version of spyder won't be imported instead:
#==============================================================================
spyder_path = osp.dirname(__file__)
while not osp.isdir(osp.join(spyder_path, 'spyder')):
    spyder_path = osp.abspath(osp.join(spyder_path, os.pardir))
if not spyder_path.startswith(sys.prefix):
    # Spyder is not installed: moving its parent directory to the top of
    # sys.path to be sure that this spyder package will be imported in
    # the remote process (instead of another installed version of Spyder)
    while spyder_path in sys.path:
        sys.path.remove(spyder_path)
    sys.path.insert(0, spyder_path)
os.environ['SPYDER_PARENT_DIR'] = spyder_path


#==============================================================================
# Setting console encoding (otherwise Python does not recognize encoding)
# for Windows platforms
#==============================================================================
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
    except ImportError:
        pass


#==============================================================================
# Settings for our MacOs X app
#==============================================================================
if sys.platform == 'darwin':
    from spyder.config.base import MAC_APP_NAME
    if MAC_APP_NAME in __file__:
        if IS_EXT_INTERPRETER:
            # Add a minimal library (with spyder) at the end of sys.path to
            # be able to connect our monitor to the external console
            py_ver = '%s.%s' % (sys.version_info[0], sys.version_info[1])
            app_pythonpath = '%s/Contents/Resources/lib/python%s' % (MAC_APP_NAME,
                                                                     py_ver)
            full_pythonpath = [p for p in sys.path if p.endswith(app_pythonpath)]
            if full_pythonpath:
                sys.path.remove(full_pythonpath[0])
                sys.path.append(full_pythonpath[0] + osp.sep + 'minimal-lib')
        else:
            # Add missing variables and methods to the app's site module
            import site
            import osx_app_site
            osx_app_site.setcopyright()
            osx_app_site.sethelper()
            site._Printer = osx_app_site._Printer
            site.USER_BASE = osx_app_site.getuserbase()
            site.USER_SITE = osx_app_site.getusersitepackages()


#==============================================================================
# Importing user's sitecustomize
#==============================================================================
try:
    import sitecustomize  #analysis:ignore
except ImportError:
    pass


#==============================================================================
# Add default filesystem encoding on Linux to avoid an error with
# Matplotlib 1.5 in Python 2 (Fixes Issue 2793)
#==============================================================================
if PY2 and sys.platform.startswith('linux'):
    def _getfilesystemencoding_wrapper():
        return 'utf-8'

    sys.getfilesystemencoding = _getfilesystemencoding_wrapper


#==============================================================================
# Set PyQt API to #2
#==============================================================================
if os.environ["QT_API"] == 'pyqt':
    try:
        import sip
        for qtype in ('QString', 'QVariant', 'QDate', 'QDateTime',
                      'QTextStream', 'QTime', 'QUrl'):
            sip.setapi(qtype, 2)
    except:
        pass


#==============================================================================
# Importing matplotlib before creating the monitor.
# This prevents a kernel crash with the inline backend in our IPython
# consoles on Linux and Python 3 (Fixes Issue 2257)
#==============================================================================
try:
    import matplotlib
except ImportError:
    matplotlib = None   # analysis:ignore


#==============================================================================
# Monitor-based functionality
#==============================================================================
if IS_IPYKERNEL or os.environ.get('SPYDER_SHELL_ID') is None:
    monitor = None
else:
    from spyder.widgets.externalshell.monitor import Monitor
    monitor = Monitor("127.0.0.1",
                      int(os.environ['SPYDER_I_PORT']),
                      int(os.environ['SPYDER_N_PORT']),
                      os.environ['SPYDER_SHELL_ID'],
                      float(os.environ['SPYDER_AR_TIMEOUT']),
                      os.environ["SPYDER_AR_STATE"].lower() == "true")
    monitor.start()

    def open_in_spyder(source, lineno=1):
        """
        Open a source file in Spyder's editor (it could be a filename or a
        Python module/package).

        If you want to use IPython's %edit use %ed instead
        """
        try:
            source = sys.modules[source]
        except KeyError:
            source = source
        if not isinstance(source, basestring):
            try:
                source = source.__file__
            except AttributeError:
                raise ValueError("source argument must be either "
                                 "a string or a module object")
        if source.endswith('.pyc'):
            source = source[:-1]
        source = osp.abspath(source)
        if osp.exists(source):
            monitor.notify_open_file(source, lineno=lineno)
        else:
            _print("Can't open file %s" % source, file=sys.stderr)
    builtins.open_in_spyder = open_in_spyder

    # Our own input hook, monitor based and for Windows only
    if os.name == 'nt' and matplotlib and not IS_IPYKERNEL:
        # Qt imports
        if os.environ["QT_API"] == 'pyqt5':
            from PyQt5 import QtCore
            from PyQt5 import QtWidgets
        elif os.environ["QT_API"] == 'pyqt':
            from PyQt4 import QtCore           # analysis:ignore
            from PyQt4 import QtGui as QtWidgets
        elif os.environ["QT_API"] == 'pyside':
            from PySide import QtCore          # analysis:ignore
            from PySide import QtGui as QtWidgets

        def qt_nt_inputhook():
            """Qt input hook for Windows

            This input hook wait for available stdin data (notified by
            ExternalPythonShell through the monitor's inputhook_flag
            attribute), and in the meantime it processes Qt events.
            """
            # Refreshing variable explorer, except on first input hook call:
            # (otherwise, on slow machines, this may freeze Spyder)
            monitor.refresh_from_inputhook()

            # NOTE: This is making the inputhoook to fail completely!!
            #       That's why it's commented.
            #try:
                # This call fails for Python without readline support
                # (or on Windows platforms) when PyOS_InputHook is called
                # for the second consecutive time, because the 100-bytes
                # stdin buffer is full.
                # For more details, see the `PyOS_StdioReadline` function
                # in Python source code (Parser/myreadline.c)
            #    sys.stdin.tell()
            #except IOError:
            #    return 0

            # Input hook
            app = QtCore.QCoreApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([" "])
            if app and app.thread() is QtCore.QThread.currentThread():
                try:
                    timer = QtCore.QTimer()
                    timer.timeout.connect(app.quit)
                    monitor.toggle_inputhook_flag(False)
                    while not monitor.inputhook_flag:
                        timer.start(50)
                        QtCore.QCoreApplication.exec_()
                        timer.stop()
                except KeyboardInterrupt:
                    _print("\nKeyboardInterrupt - Press Enter for new prompt")

                # Socket-based alternative:
                #socket = QtNetwork.QLocalSocket()
                #socket.connectToServer(os.environ['SPYDER_SHELL_ID'])
                #socket.waitForConnected(-1)
                #while not socket.waitForReadyRead(10):
                #    timer.start(50)
                #    QtCore.QCoreApplication.exec_()
                #    timer.stop()
                #socket.read(3)
                #socket.disconnectFromServer()
            return 0


#==============================================================================
# Matplotlib settings
#==============================================================================
if matplotlib is not None:
    if not IS_IPYKERNEL:
        mpl_backend = os.environ.get("SPY_MPL_BACKEND", "")
        mpl_ion = os.environ.get("MATPLOTLIB_ION", "")

        # Setting no backend if the user asks for it
        if not mpl_backend or mpl_backend.lower() == 'none':
            mpl_backend = ""

        # Set backend automatically
        if mpl_backend.lower() == 'automatic':
            if not IS_EXT_INTERPRETER:
                if os.environ["QT_API"] == 'pyqt5':
                    mpl_backend = 'Qt5Agg'
                else:
                    mpl_backend = 'Qt4Agg'
            else:
                # Test for backend libraries on external interpreters
                def set_mpl_backend(backend):
                    mod, bend, qt_api = backend
                    try:
                        if mod:
                            __import__(mod)
                        if qt_api and (os.environ["QT_API"] != qt_api):
                            return None
                        else:
                            matplotlib.use(bend)
                            return bend
                    except (ImportError, ValueError):
                        return None

                backends = [('PyQt5', 'Qt5Agg', 'pyqt5'),
                            ('PyQt4', 'Qt4Agg', 'pyqt'),
                            ('PySide', 'Qt4Agg', 'pyqt')]
                if not os.name == 'nt':
                     backends.append( ('_tkinter', 'TkAgg', None) )

                for b in backends:
                    mpl_backend = set_mpl_backend(b)
                    if mpl_backend:
                        break

                if not mpl_backend:
                    _print("NOTE: No suitable Matplotlib backend was found!\n"
                           "      You won't be able to create plots\n")

        # To have mpl docstrings as rst
        matplotlib.rcParams['docstring.hardcopy'] = True

        # Activate interactive mode when needed
        if mpl_ion.lower() == "true":
            matplotlib.rcParams['interactive'] = True

        from spyder.utils import inputhooks
        if mpl_backend:
            import ctypes

            # Grab QT_API
            qt_api = os.environ["QT_API"]

            # Setting the user defined backend
            if not IS_EXT_INTERPRETER:
                matplotlib.use(mpl_backend)

            # Setting the right input hook according to mpl_backend,
            # IMPORTANT NOTE: Don't try to abstract the steps to set a PyOS
            # input hook callback in a function. It will **crash** the
            # interpreter!!
            if (mpl_backend == "Qt4Agg" or mpl_backend == "Qt5Agg") and \
              os.name == 'nt' and monitor is not None:
                # Removing PyQt4 input hook which is not working well on
                # Windows since opening a subprocess does not attach a real
                # console to it (with keyboard events...)
                if qt_api == 'pyqt' or qt_api == 'pyqt5':
                    inputhooks.remove_pyqt_inputhook()
                # Using our own input hook
                # NOTE: it's not working correctly for some configurations
                # (See issue 1831)
                callback = inputhooks.set_pyft_callback(qt_nt_inputhook)
                pyos_ih = inputhooks.get_pyos_inputhook()
                pyos_ih.value = ctypes.cast(callback, ctypes.c_void_p).value
            elif mpl_backend == "Qt4Agg" and qt_api == 'pyside':
                # PySide doesn't have an input hook, so we need to install one
                # to be able to show plots
                # Note: This only works well for Posix systems
                callback = inputhooks.set_pyft_callback(inputhooks.qt4)
                pyos_ih = inputhooks.get_pyos_inputhook()
                pyos_ih.value = ctypes.cast(callback, ctypes.c_void_p).value
            elif (mpl_backend != "Qt4Agg" and qt_api == 'pyqt') \
              or (mpl_backend != "Qt5Agg" and qt_api == 'pyqt5'):
                # Matplotlib backends install their own input hooks, so we
                # need to remove the PyQt one to make them work
                inputhooks.remove_pyqt_inputhook()
        else:
            inputhooks.remove_pyqt_inputhook()
    else:
        # To have mpl docstrings as rst
        matplotlib.rcParams['docstring.hardcopy'] = True


#==============================================================================
# IPython kernel adjustments
#==============================================================================
if IS_IPYKERNEL:
    # Use ipydb as the debugger to patch on IPython consoles
    from IPython.core.debugger import Pdb as ipyPdb
    pdb.Pdb = ipyPdb

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


#==============================================================================
# Pandas adjustments
#==============================================================================
try:
    # Make Pandas recognize our Jupyter consoles as proper qtconsoles
    # Fixes Issue 2015
    def in_qtconsole():
        return True
    import pandas as pd
    pd.core.common.in_qtconsole = in_qtconsole

    # Set Pandas output encoding
    pd.options.display.encoding = 'utf-8'

    # Filter warning that appears for DataFrames with np.nan values
    # Example:
    # >>> import pandas as pd, numpy as np
    # >>> pd.Series([np.nan,np.nan,np.nan],index=[1,2,3])
    # Fixes Issue 2991
    import warnings
    # For 0.18-
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.core.format',
                            message=".*invalid value encountered in.*")
    # For 0.18.1+
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.formats.format',
                            message=".*invalid value encountered in.*")
except (ImportError, AttributeError):
    pass


#==============================================================================
# Pdb adjustments
#==============================================================================
class SpyderPdb(pdb.Pdb):
    send_initial_notification = True

    def set_spyder_breakpoints(self):
        self.clear_all_breaks()
        #------Really deleting all breakpoints:
        for bp in bdb.Breakpoint.bpbynumber:
            if bp:
                bp.deleteMe()
        bdb.Breakpoint.next = 1
        bdb.Breakpoint.bplist = {}
        bdb.Breakpoint.bpbynumber = [None]
        #------
        from spyder.config.main import CONF
        CONF.load_from_ini()
        if CONF.get('run', 'breakpoints/enabled', True):
            breakpoints = CONF.get('run', 'breakpoints', {})
            i = 0
            for fname, data in list(breakpoints.items()):
                for linenumber, condition in data:
                    i += 1
                    self.set_break(self.canonic(fname), linenumber,
                                   cond=condition)

    def notify_spyder(self, frame):
        if not frame:
            return
        fname = self.canonic(frame.f_code.co_filename)
        if PY2:
            try:
                fname = unicode(fname, "utf-8")
            except TypeError:
                pass
        lineno = frame.f_lineno
        if isinstance(fname, basestring) and isinstance(lineno, int):
            if osp.isfile(fname):
                if IS_IPYKERNEL:
                    from IPython.core.getipython import get_ipython
                    ipython_shell = get_ipython()
                    if ipython_shell:
                        step = dict(fname=fname, lineno=lineno)
                        ipython_shell.kernel._pdb_step = step
                elif monitor is not None:
                    monitor.notify_pdb_step(fname, lineno)
                    time.sleep(0.1)

pdb.Pdb = SpyderPdb

#XXX: I know, this function is now also implemented as is in utils/misc.py but
#     I'm kind of reluctant to import spyder in sitecustomize, even if this
#     import is very clean.
def monkeypatch_method(cls, patch_name):
    # This function's code was inspired from the following thread:
    # "[Python-Dev] Monkeypatching idioms -- elegant or ugly?"
    # by Robert Brewer <fumanchu at aminus.org>
    # (Tue Jan 15 19:13:25 CET 2008)
    """
    Add the decorated method to the given class; replace as needed.

    If the named method already exists on the given class, it will
    be replaced, and a reference to the old method is created as
    cls._old<patch_name><name>. If the "_old_<patch_name>_<name>" attribute
    already exists, KeyError is raised.
    """
    def decorator(func):
        fname = func.__name__
        old_func = getattr(cls, fname, None)
        if old_func is not None:
            # Add the old func to a list of old funcs.
            old_ref = "_old_%s_%s" % (patch_name, fname)
            #print(old_ref, old_func)
            old_attr = getattr(cls, old_ref, None)
            if old_attr is None:
                setattr(cls, old_ref, old_func)
            else:
                raise KeyError("%s.%s already exists."
                               % (cls.__name__, old_ref))
        setattr(cls, fname, func)
        return func
    return decorator

@monkeypatch_method(pdb.Pdb, 'Pdb')
def user_return(self, frame, return_value):
    """This function is called when a return trap is set here."""
    # This is useful when debugging in an active interpreter (otherwise,
    # the debugger will stop before reaching the target file)
    if self._wait_for_mainpyfile:
        if (self.mainpyfile != self.canonic(frame.f_code.co_filename)
            or frame.f_lineno<= 0):
            return
        self._wait_for_mainpyfile = 0
    self._old_Pdb_user_return(frame, return_value)

@monkeypatch_method(pdb.Pdb, 'Pdb')
def interaction(self, frame, traceback):
    self.setup(frame, traceback)
    if self.send_initial_notification:
        self.notify_spyder(frame) #-----Spyder-specific-----------------------
    self.print_stack_entry(self.stack[self.curindex])
    self.cmdloop()
    self.forget()

@monkeypatch_method(pdb.Pdb, 'Pdb')
def reset(self):
    self._old_Pdb_reset()
    if IS_IPYKERNEL:
        from IPython.core.getipython import get_ipython
        ipython_shell = get_ipython()
        if ipython_shell:
            ipython_shell.kernel._register_pdb_session(self)
    elif monitor is not None:
        monitor.register_pdb_session(self)
    self.set_spyder_breakpoints()

#XXX: notify spyder on any pdb command (is that good or too lazy? i.e. is more
#     specific behaviour desired?)
@monkeypatch_method(pdb.Pdb, 'Pdb')
def postcmd(self, stop, line):
    self.notify_spyder(self.curframe)
    return self._old_Pdb_postcmd(stop, line)

# Breakpoints don't work for files with non-ascii chars in Python 2
# Fixes Issue 1484
if PY2:
    @monkeypatch_method(pdb.Pdb, 'Pdb')
    def break_here(self, frame):
        from bdb import effective
        filename = self.canonic(frame.f_code.co_filename)
        try:
            filename = unicode(filename, "utf-8")
        except TypeError:
            pass
        if not filename in self.breaks:
            return False
        lineno = frame.f_lineno
        if not lineno in self.breaks[filename]:
            # The line itself has no breakpoint, but maybe the line is the
            # first line of a function with breakpoint set by function name.
            lineno = frame.f_code.co_firstlineno
            if not lineno in self.breaks[filename]:
                return False

        # flag says ok to delete temp. bp
        (bp, flag) = effective(filename, lineno, frame)
        if bp:
            self.currentbp = bp.number
            if (flag and bp.temporary):
                self.do_clear(str(bp.number))
            return True
        else:
            return False


#==============================================================================
# Restoring (almost) original sys.path:
#
# NOTE: do not remove spyder_path from sys.path because if Spyder has been
# installed using python setup.py install, then this could remove the
# 'site-packages' directory from sys.path!
#==============================================================================
try:
    sys.path.remove(osp.join(spyder_path, "spyder", "widgets",
                             "externalshell"))
except ValueError:
    pass


#==============================================================================
# User module reloader
#==============================================================================
class UserModuleReloader(object):
    """
    User Module Reloader (UMR) aims at deleting user modules
    to force Python to deeply reload them during import

    pathlist [list]: blacklist in terms of module path
    namelist [list]: blacklist in terms of module name
    """
    def __init__(self, namelist=None, pathlist=None):
        if namelist is None:
            namelist = []
        spy_modules = ['sitecustomize', 'spyder', 'spyderplugins']
        mpl_modules = ['matplotlib', 'tkinter', 'Tkinter']
        self.namelist = namelist + spy_modules + mpl_modules

        if pathlist is None:
            pathlist = []
        self.pathlist = pathlist
        self.previous_modules = list(sys.modules.keys())

    def is_module_blacklisted(self, modname, modpath):
        for path in [sys.prefix]+self.pathlist:
            if modpath.startswith(path):
                return True
        else:
            return set(modname.split('.')) & set(self.namelist)

    def run(self, verbose=False):
        """
        Del user modules to force Python to deeply reload them

        Do not del modules which are considered as system modules, i.e.
        modules installed in subdirectories of Python interpreter's binary
        Do not del C modules
        """
        log = []
        for modname, module in list(sys.modules.items()):
            if modname not in self.previous_modules:
                modpath = getattr(module, '__file__', None)
                if modpath is None:
                    # *module* is a C module that is statically linked into the
                    # interpreter. There is no way to know its path, so we
                    # choose to ignore it.
                    continue
                if not self.is_module_blacklisted(modname, modpath):
                    log.append(modname)
                    del sys.modules[modname]
        if verbose and log:
            _print("\x1b[4;33m%s\x1b[24m%s\x1b[0m"\
                   % ("Reloaded modules", ": "+", ".join(log)))

__umr__ = None


#==============================================================================
# Handle Post Mortem Debugging and Traceback Linkage to Spyder
#==============================================================================
def clear_post_mortem():
    """
    Remove the post mortem excepthook and replace with a standard one.
    """
    if IS_IPYKERNEL:
        from IPython.core.getipython import get_ipython
        ipython_shell = get_ipython()
        if ipython_shell:
            ipython_shell.set_custom_exc((), None)
    else:
        sys.excepthook = sys.__excepthook__


def post_mortem_excepthook(type, value, tb):
    """
    For post mortem exception handling, print a banner and enable post
    mortem debugging.
    """
    clear_post_mortem()
    if IS_IPYKERNEL:
        from IPython.core.getipython import get_ipython
        ipython_shell = get_ipython()
        ipython_shell.showtraceback((type, value, tb))
        p = pdb.Pdb(ipython_shell.colors)
    else:
        traceback.print_exception(type, value, tb, file=sys.stderr)
        p = pdb.Pdb()

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
    if IS_IPYKERNEL:
        from IPython.core.getipython import get_ipython
        def ipython_post_mortem_debug(shell, etype, evalue, tb,
                   tb_offset=None):
            post_mortem_excepthook(etype, evalue, tb)
        ipython_shell = get_ipython()
        ipython_shell.set_custom_exc((Exception,), ipython_post_mortem_debug)
    else:
        sys.excepthook = post_mortem_excepthook

# Add post mortem debugging if requested and in a dedicated interpreter
# existing interpreters use "runfile" below
if "SPYDER_EXCEPTHOOK" in os.environ:
    set_post_mortem()


#==============================================================================
# runfile and debugfile commands
#==============================================================================
def _get_globals():
    """Return current Python interpreter globals namespace"""
    from __main__ import __dict__ as namespace
    shell = namespace.get('__ipythonshell__')
    if shell is not None and hasattr(shell, 'user_ns'):
        # IPython 0.13+ kernel
        return shell.user_ns
    else:
        # Python interpreter
        return namespace
    return namespace


def runfile(filename, args=None, wdir=None, namespace=None, post_mortem=False):
    """
    Run filename
    args: command line arguments (string)
    wdir: working directory
    post_mortem: boolean, whether to enter post-mortem mode on error
    """
    try:
        filename = filename.decode('utf-8')
    except (UnicodeError, TypeError, AttributeError):
        # UnicodeError, TypeError --> eventually raised in Python 2
        # AttributeError --> systematically raised in Python 3
        pass
    global __umr__
    if os.environ.get("UMR_ENABLED", "").lower() == "true":
        if __umr__ is None:
            namelist = os.environ.get("UMR_NAMELIST", None)
            if namelist is not None:
                namelist = namelist.split(',')
            __umr__ = UserModuleReloader(namelist=namelist)
        else:
            verbose = os.environ.get("UMR_VERBOSE", "").lower() == "true"
            __umr__.run(verbose=verbose)
    if args is not None and not isinstance(args, basestring):
        raise TypeError("expected a character buffer object")
    if namespace is None:
        namespace = _get_globals()
    namespace['__file__'] = filename
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
        os.chdir(wdir)
    if post_mortem:
        set_post_mortem()
    execfile(filename, namespace)
    clear_post_mortem()
    sys.argv = ['']
    namespace.pop('__file__')

builtins.runfile = runfile


def debugfile(filename, args=None, wdir=None, post_mortem=False):
    """
    Debug filename
    args: command line arguments (string)
    wdir: working directory
    post_mortem: boolean, included for compatiblity with runfile
    """
    debugger = pdb.Pdb()
    filename = debugger.canonic(filename)
    debugger._wait_for_mainpyfile = 1
    debugger.mainpyfile = filename
    debugger._user_requested_quit = 0
    if os.name == 'nt':
        filename = filename.replace('\\', '/')
    debugger.run("runfile(%r, args=%r, wdir=%r)" % (filename, args, wdir))

builtins.debugfile = debugfile


#==============================================================================
# Evaluate external commands
#==============================================================================
def evalsc(command):
    """Evaluate special commands
    (analog to IPython's magic commands but far less powerful/complete)"""
    assert command.startswith('%')
    from spyder.utils import programs

    namespace = _get_globals()
    command = command[1:].strip()  # Remove leading %

    import re
    clear_match = re.match(r"^clear ([a-zA-Z0-9_, ]+)", command)
    cd_match = re.match(r"^cd \"?\'?([a-zA-Z0-9_\ \:\\\/\.]+)", command)

    if cd_match:
        os.chdir(eval('r"%s"' % cd_match.groups()[0].strip()))
    elif clear_match:
        varnames = clear_match.groups()[0].replace(' ', '').split(',')
        for varname in varnames:
            try:
                namespace.pop(varname)
            except KeyError:
                pass
    elif command in ('cd', 'pwd'):
        try:
            _print(os.getcwdu())
        except AttributeError:
            _print(os.getcwd())
    elif command == 'ls':
        if os.name == 'nt':
            programs.run_shell_command('dir')
            _print('\n')
        else:
            programs.run_shell_command('ls')
            _print('\n')
    elif command == 'scientific':
        from spyder.config import base
        execfile(base.SCIENTIFIC_STARTUP, namespace)
    else:
        raise NotImplementedError("Unsupported command: '%s'" % command)

builtins.evalsc = evalsc


#==============================================================================
# Restoring original PYTHONPATH
#==============================================================================
try:
    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
    del os.environ['OLD_PYTHONPATH']
except KeyError:
    if os.environ.get('PYTHONPATH') is not None:
        del os.environ['PYTHONPATH']
