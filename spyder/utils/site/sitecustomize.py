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

import bdb
from distutils.version import LooseVersion
import io
import os
import os.path as osp
import pdb
import shlex
import sys
import time
import warnings

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
IS_EXT_INTERPRETER = os.environ.get('SPY_EXTERNAL_INTERPRETER') == "True"


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
    except:
        pass


#==============================================================================
# Settings for our MacOs X app
#==============================================================================
# FIXME: If/when we create new apps we need to revisit this!
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
# Cython support
#==============================================================================
RUN_CYTHON = os.environ.get("SPY_RUN_CYTHON") == "True"
HAS_CYTHON = False

if RUN_CYTHON:
    try:
        __import__('Cython')
        HAS_CYTHON = True
    except Exception:
        pass

    if HAS_CYTHON:
        # Import pyximport to enable Cython files support for
        # import statement
        import pyximport
        pyx_setup_args = {}

        # Add Numpy include dir to pyximport/distutils
        try:
            import numpy
            pyx_setup_args['include_dirs'] = numpy.get_include()
        except Exception:
            pass

        # Setup pyximport and enable Cython files reload
        pyximport.install(setup_args=pyx_setup_args, reload_support=True)


#==============================================================================
# Prevent subprocess.Popen calls to create visible console windows on Windows.
# See issue #4932
#==============================================================================
if os.name == 'nt':
    import subprocess
    creation_flag = 0x08000000  # CREATE_NO_WINDOW

    class SubprocessPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs['creationflags'] = creation_flag
            super(SubprocessPopen, self).__init__(*args, **kwargs)

    subprocess.Popen = SubprocessPopen

#==============================================================================
# Importing user's sitecustomize
#==============================================================================
try:
    import sitecustomize  #analysis:ignore
except:
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
else:
    os.environ.pop('QT_API')


#==============================================================================
# IPython kernel adjustments
#==============================================================================
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

# Patch ipykernel to avoid errors when setting the Qt5 Matplotlib
# backemd
# Fixes Issue 6091
import ipykernel
import IPython
if LooseVersion(ipykernel.__version__) <= LooseVersion('4.7.0'):
    if ((PY2 and LooseVersion(IPython.__version__) >= LooseVersion('5.5.0')) or
        (not PY2 and LooseVersion(IPython.__version__) >= LooseVersion('6.2.0'))
       ):
        from ipykernel import eventloops
        eventloops.loop_map['qt'] = eventloops.loop_map['qt5']


#==============================================================================
# Pandas adjustments
#==============================================================================
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
except:
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
except:
    pass


#==============================================================================
# Pdb adjustments
#==============================================================================
class SpyderPdb(pdb.Pdb):

    send_initial_notification = True
    starting = True

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

        from IPython.core.getipython import get_ipython
        kernel = get_ipython().kernel

        # Get filename and line number of the current frame
        fname = self.canonic(frame.f_code.co_filename)
        if PY2:
            try:
                fname = unicode(fname, "utf-8")
            except TypeError:
                pass
        lineno = frame.f_lineno

        # Jump to first breakpoint.
        # Fixes issue 2034
        if self.starting:
            # Only run this after a Pdb session is created
            self.starting = False

            # Get all breakpoints for the file we're going to debug
            breaks = self.get_file_breaks(frame.f_code.co_filename)

            # Do 'continue' if the first breakpoint is *not* placed
            # where the debugger is going to land.
            # Fixes issue 4681
            if breaks and lineno != breaks[0] and osp.isfile(fname):
                kernel.pdb_continue()

        # Set step of the current frame (if any)
        step = {}
        if isinstance(fname, basestring) and isinstance(lineno, int):
            if osp.isfile(fname):
                step = dict(fname=fname, lineno=lineno)

        # Publish Pdb state so we can update the Variable Explorer
        # and the Editor on the Spyder side
        kernel._pdb_step = step
        kernel.publish_pdb_state()

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
def __init__(self, completekey='tab', stdin=None, stdout=None,
             skip=None, nosigint=False):
    self._old_Pdb___init__()


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
    if frame is not None and "sitecustomize.py" in frame.f_code.co_filename:
        self.run('exit')
    else:
        self.setup(frame, traceback)
        if self.send_initial_notification:
            self.notify_spyder(frame)
        self.print_stack_entry(self.stack[self.curindex])
        self._cmdloop()
        self.forget()


@monkeypatch_method(pdb.Pdb, 'Pdb')
def _cmdloop(self):
    while True:
        try:
            # keyboard interrupts allow for an easy way to cancel
            # the current command, so allow them during interactive input
            self.allow_kbdint = True
            self.cmdloop()
            self.allow_kbdint = False
            break
        except KeyboardInterrupt:
            _print("--KeyboardInterrupt--\n"
                   "For copying text while debugging, use Ctrl+Shift+C",
                   file=self.stdout)


@monkeypatch_method(pdb.Pdb, 'Pdb')
def reset(self):
    self._old_Pdb_reset()

    from IPython.core.getipython import get_ipython
    kernel = get_ipython().kernel
    kernel._register_pdb_session(self)
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
    sys.path.remove(osp.join(spyder_path, "spyder", "utils", "site"))
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
        other_modules = ['pytorch']
        if PY2:
            other_modules.append('astropy')
        self.namelist = namelist + spy_modules + mpl_modules + other_modules

        if pathlist is None:
            pathlist = []
        self.pathlist = pathlist
        self.previous_modules = list(sys.modules.keys())

    def is_module_blacklisted(self, modname, modpath):
        if HAS_CYTHON:
            # Don't return cached inline compiled .PYX files
            return True
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
    from IPython.core.getipython import get_ipython
    ipython_shell = get_ipython()
    ipython_shell.set_custom_exc((), None)


def post_mortem_excepthook(type, value, tb):
    """
    For post mortem exception handling, print a banner and enable post
    mortem debugging.
    """
    clear_post_mortem()

    from IPython.core.getipython import get_ipython
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
    from IPython.core.getipython import get_ipython
    def ipython_post_mortem_debug(shell, etype, evalue, tb,
               tb_offset=None):
        post_mortem_excepthook(etype, evalue, tb)
    ipython_shell = get_ipython()
    ipython_shell.set_custom_exc((Exception,), ipython_post_mortem_debug)

# Add post mortem debugging if requested and in a dedicated interpreter
# existing interpreters use "runfile" below
if "SPYDER_EXCEPTHOOK" in os.environ:
    set_post_mortem()


#==============================================================================
# runfile and debugfile commands
#==============================================================================
def _get_globals():
    """Return current namespace"""
    from IPython.core.getipython import get_ipython
    ipython_shell = get_ipython()
    return ipython_shell.user_ns


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
    if os.environ.get("SPY_UMR_ENABLED", "").lower() == "true":
        if __umr__ is None:
            namelist = os.environ.get("SPY_UMR_NAMELIST", None)
            if namelist is not None:
                namelist = namelist.split(',')
            __umr__ = UserModuleReloader(namelist=namelist)
        else:
            verbose = os.environ.get("SPY_UMR_VERBOSE", "").lower() == "true"
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
    if HAS_CYTHON:
        # Cython files
        with io.open(filename, encoding='utf-8') as f:
            from IPython.core.getipython import get_ipython
            ipython_shell = get_ipython()
            ipython_shell.run_cell_magic('cython', '', f.read())
    else:
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
# Restoring original PYTHONPATH
#==============================================================================
try:
    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
    del os.environ['OLD_PYTHONPATH']
except KeyError:
    if os.environ.get('PYTHONPATH') is not None:
        del os.environ['PYTHONPATH']
