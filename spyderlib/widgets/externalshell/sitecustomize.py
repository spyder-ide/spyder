# -*- coding: utf-8 -*-
# Spyder's ExternalPythonShell sitecustomize

import sys
import os
import os.path as osp
import pdb
import bdb


# sys.argv can be missing when Python is embedded, taking care of it.
# Fixes Issue 1473 and other crazy crashes with IPython 0.13 trying to
# access it.
if not hasattr(sys, 'argv'):
    sys.argv = ['']

#==============================================================================
# Important Note:
#
# We avoid importing spyderlib here, so we are handling Python 3 compatiblity
# by hand.
#==============================================================================
def _print(*objects, **options):
    end = options.get('end', '\n')
    file = options.get('file', sys.stdout)
    sep = options.get('sep', ' ')
    string = sep.join([str(obj) for obj in objects])
    if sys.version[0] == '3':
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

try:
    import __builtin__ as builtins
except ImportError:
    # Python 3
    import builtins
    basestring = (str,)
    def execfile(filename, namespace):
        # Open a source file correctly, whatever its encoding is
        exec(compile(open(filename, 'rb').read(), filename, 'exec'), namespace)

# Colorization of sys.stderr (standard Python interpreter)
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


# Prepending this spyderlib package's path to sys.path to be sure 
# that another version of spyderlib won't be imported instead:
spyderlib_path = osp.dirname(__file__)
while not osp.isdir(osp.join(spyderlib_path, 'spyderlib')):
    spyderlib_path = osp.abspath(osp.join(spyderlib_path, os.pardir))
if not spyderlib_path.startswith(sys.prefix):
    # Spyder is not installed: moving its parent directory to the top of 
    # sys.path to be sure that this spyderlib package will be imported in 
    # the remote process (instead of another installed version of Spyder)
    while spyderlib_path in sys.path:
        sys.path.remove(spyderlib_path)
    sys.path.insert(0, spyderlib_path)
os.environ['SPYDER_PARENT_DIR'] = spyderlib_path


# Set PyQt4 API to #1 or #2
pyqt_api = int(os.environ.get("PYQT_API", "0"))
if pyqt_api:
    try:
        import sip
        try:
            for qtype in ('QString', 'QVariant'):
                sip.setapi(qtype, pyqt_api)
        except AttributeError:
            # Old version of sip
            pass
    except ImportError:
        pass


if os.name == 'nt': # Windows platforms
            
    # Setting console encoding (otherwise Python does not recognize encoding)
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


# For our MacOs X app
if sys.platform == 'darwin' and 'Spyder.app' in __file__:
    interpreter = os.environ.get('SPYDER_INTERPRETER')
    if 'Spyder.app' not in interpreter:
        # We added this file's dir to PYTHONPATH (in pythonshell.py)
        # so that external interpreters can import this script, and
        # now we are removing it
        del os.environ['PYTHONPATH']

        # Add a minimal library (with spyderlib) at the end of sys.path to
        # be able to connect our monitor to the external console
        app_pythonpath = 'Spyder.app/Contents/Resources/lib/python2.7'
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


mpl_backend = os.environ.get("MATPLOTLIB_BACKEND")
mpl_ion = os.environ.get("MATPLOTLIB_ION", "")
if mpl_backend:
    try:
        import matplotlib
        if os.environ.get('QT_API') == 'pyside':
            # Try to address PySide lack of an input hook on Mac by settting
            # mpl_backend to always be MacOSX
            # Fixes Issue 347
            if mpl_backend == 'Qt4Agg' and sys.platform == 'darwin':
                mpl_backend = 'MacOSX'
        matplotlib.rcParams['docstring.hardcopy'] = True
        if mpl_ion.lower() == "true":
            matplotlib.rcParams['interactive'] = True
        matplotlib.use(mpl_backend)
    except ImportError:
        pass


# Set standard outputs encoding:
# (otherwise, for example, print("é") will fail)
encoding = None
try:
    import locale
except ImportError:
    pass
else:
    loc = locale.getdefaultlocale()
    if loc[1]:
        encoding = loc[1]

if encoding is None:
    encoding = "UTF-8"

try:
    sys.setdefaultencoding(encoding)
    os.environ['SPYDER_ENCODING'] = encoding
except AttributeError:
    # Python 3
    pass
    
try:
    import sitecustomize  #analysis:ignore
except ImportError:
    pass


# Communication between Spyder and the remote process
if os.environ.get('SPYDER_SHELL_ID') is None:
    monitor = None
else:
    from spyderlib.widgets.externalshell.monitor import Monitor
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
    
    # * PyQt4:
    #   * Removing PyQt4 input hook which is not working well on Windows since 
    #     opening a subprocess do not attach a real console to it
    #     (with keyboard events...)
    #   * Replacing it with our own input hook
    # * PySide:
    #   * Installing an input hook: this feature is not yet supported 
    #     natively by PySide
    if os.environ.get("INSTALL_QT_INPUTHOOK", "").lower() == "true":
        if os.environ["QT_API"] == 'pyqt':
            from PyQt4 import QtCore
            # Removing PyQt's PyOS_InputHook implementation:
            QtCore.pyqtRemoveInputHook()
        elif os.environ["QT_API"] == 'pyside':
            from PySide import QtCore
            # XXX: when PySide will implement an input hook, we will have to 
            # remove it here
        else:
            assert False

        def qt_inputhook():
            """Qt input hook for Spyder's console
            
            This input hook wait for available stdin data (notified by
            ExternalPythonShell through the monitor's inputhook_flag
            attribute), and in the meantime it processes Qt events."""
            # Refreshing variable explorer, except on first input hook call:
            # (otherwise, on slow machines, this may freeze Spyder)
            monitor.refresh_from_inputhook()
            if os.name == 'nt':
                try:
                    # This call fails for Python without readline support
                    # (or on Windows platforms) when PyOS_InputHook is called
                    # for the second consecutive time, because the 100-bytes
                    # stdin buffer is full.
                    # For more details, see the `PyOS_StdioReadline` function
                    # in Python source code (Parser/myreadline.c)
                    sys.stdin.tell()
                except IOError:
                    return 0
            app = QtCore.QCoreApplication.instance()
            if app and app.thread() is QtCore.QThread.currentThread():
                timer = QtCore.QTimer()
                QtCore.QObject.connect(timer, QtCore.SIGNAL('timeout()'),
                                       app, QtCore.SLOT('quit()'))
                monitor.toggle_inputhook_flag(False)
                while not monitor.inputhook_flag:
                    timer.start(50)
                    QtCore.QCoreApplication.exec_()
                    timer.stop()
#                # Socket-based alternative:
#                socket = QtNetwork.QLocalSocket()
#                socket.connectToServer(os.environ['SPYDER_SHELL_ID'])
#                socket.waitForConnected(-1)
#                while not socket.waitForReadyRead(10):
#                    timer.start(50)
#                    QtCore.QCoreApplication.exec_()
#                    timer.stop()
#                socket.read(3)
#                socket.disconnectFromServer()
            return 0

        # Installing Spyder's PyOS_InputHook implementation:
        import ctypes
        cb_pyfunctype = ctypes.PYFUNCTYPE(ctypes.c_int)(qt_inputhook)
        pyos_ih = ctypes.c_void_p.in_dll(ctypes.pythonapi, "PyOS_InputHook")
        pyos_ih.value = ctypes.cast(cb_pyfunctype, ctypes.c_void_p).value
    else:
        # Quite limited feature: notify only when a result is displayed in
        # console (does not notify at every prompt)
        def displayhook(obj):
            sys.__displayhook__(obj)
            monitor.refresh()
    
        sys.displayhook = displayhook


#===============================================================================
# Monkey-patching pdb
#===============================================================================

if os.environ.get("IPYTHON_KERNEL", "").lower() == "true":

    #XXX If Matplotlib is not imported first, the next IPython import will fail
    try:
        import matplotlib  # analysis:ignore
    except ImportError:
        pass

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

class SpyderPdb(pdb.Pdb):
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
        from spyderlib.config import CONF
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
        lineno = frame.f_lineno
        if isinstance(fname, basestring) and isinstance(lineno, int):
            if osp.isfile(fname) and monitor is not None:
                monitor.notify_pdb_step(fname, lineno)

pdb.Pdb = SpyderPdb

#XXX: I know, this function is now also implemented as is in utils/misc.py but
#     I'm kind of reluctant to import spyderlib in sitecustomize, even if this
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
    self.notify_spyder(frame) #-----Spyder-specific-------------------------
    self.print_stack_entry(self.stack[self.curindex])
    self.cmdloop()
    self.forget()

@monkeypatch_method(pdb.Pdb, 'Pdb')
def reset(self):
    self._old_Pdb_reset()
    if monitor is not None:
        monitor.register_pdb_session(self)
    self.set_spyder_breakpoints()

#XXX: notify spyder on any pdb command (is that good or too lazy? i.e. is more 
#     specific behaviour desired?)
@monkeypatch_method(pdb.Pdb, 'Pdb')
def postcmd(self, stop, line):
    self.notify_spyder(self.curframe)
    return self._old_Pdb_postcmd(stop, line)


# Restoring (almost) original sys.path:
# (Note: do not remove spyderlib_path from sys.path because if Spyder has been
#  installed using python setup.py install, then this could remove the 
#  'site-packages' directory from sys.path!)
try:
    sys.path.remove(osp.join(spyderlib_path,
                             "spyderlib", "widgets", "externalshell"))
except ValueError:
    pass

# Ignore PyQt4's sip API changes (this should be used wisely -e.g. for
# debugging- as dynamic API change is not supported by PyQt)
if os.environ.get("IGNORE_SIP_SETAPI_ERRORS", "").lower() == "true":
    try:
        import sip
        from sip import setapi as original_setapi
        def patched_setapi(name, no):
            try:
                original_setapi(name, no)
            except ValueError as msg:
                _print("Warning/PyQt4-Spyder (%s)" % str(msg), file=sys.stderr)
        sip.setapi = patched_setapi
    except ImportError:
        pass


# The following classes and functions are mainly intended to be used from 
# an interactive Python session
class UserModuleDeleter(object):
    """
    User Module Deleter (UMD) aims at deleting user modules 
    to force Python to deeply reload them during import
    
    pathlist [list]: blacklist in terms of module path
    namelist [list]: blacklist in terms of module name
    """
    def __init__(self, namelist=None, pathlist=None):
        if namelist is None:
            namelist = []
        self.namelist = namelist+['sitecustomize', 'spyderlib', 'spyderplugins']
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
                   % ("UMD has deleted", ": "+", ".join(log)))

__umd__ = None


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


def runfile(filename, args=None, wdir=None, namespace=None):
    """
    Run filename
    args: command line arguments (string)
    wdir: working directory
    """
    try:
        filename = filename.decode('utf-8')
    except (UnicodeError, TypeError, AttributeError):
        # UnicodeError, TypeError --> eventually raised in Python 2
        # AttributeError --> systematically raised in Python 3
        pass
    global __umd__
    if os.environ.get("UMD_ENABLED", "").lower() == "true":
        if __umd__ is None:
            namelist = os.environ.get("UMD_NAMELIST", None)
            if namelist is not None:
                namelist = namelist.split(',')
            __umd__ = UserModuleDeleter(namelist=namelist)
        else:
            verbose = os.environ.get("UMD_VERBOSE", "").lower() == "true"
            __umd__.run(verbose=verbose)
    if args is not None and not isinstance(args, basestring):
        raise TypeError("expected a character buffer object")
    if namespace is None:
        namespace = _get_globals()
    namespace['__file__'] = filename
    sys.argv = [filename]
    if args is not None:
        for arg in args.split():
            sys.argv.append(arg)
    if wdir is not None:
        try:
            wdir = wdir.decode('utf-8')
        except (UnicodeError, TypeError, AttributeError):
            # UnicodeError, TypeError --> eventually raised in Python 2
            # AttributeError --> systematically raised in Python 3
            pass
        os.chdir(wdir)
    execfile(filename, namespace)
    sys.argv = ['']
    namespace.pop('__file__')
    
builtins.runfile = runfile


def debugfile(filename, args=None, wdir=None):
    """
    Debug filename
    args: command line arguments (string)
    wdir: working directory
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


def evalsc(command):
    """Evaluate special commands
    (analog to IPython's magic commands but far less powerful/complete)"""
    assert command.startswith(('%', '!'))
    system_command = command.startswith('!')
    command = command[1:].strip()
    if system_command:
        # System command
        if command.startswith('cd '):
            evalsc('%'+command)
        else:
            from subprocess import Popen, PIPE
            Popen(command, shell=True, stdin=PIPE)
            _print('\n')
    else:
        # General command
        namespace = _get_globals()
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
                evalsc('!dir')
            else:
                evalsc('!ls')
        elif command == 'scientific':
            from spyderlib import baseconfig
            execfile(baseconfig.SCIENTIFIC_STARTUP, namespace)
        else:
            raise NotImplementedError("Unsupported command: '%s'" % command)

builtins.evalsc = evalsc


# Restoring original PYTHONPATH
try:
    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
    del os.environ['OLD_PYTHONPATH']
except KeyError:
    if os.environ.get('PYTHONPATH') is not None:
        del os.environ['PYTHONPATH']
