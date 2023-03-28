# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Spyder kernel for Jupyter.
"""

# Standard library imports
import logging
import os
import sys
import threading

# Third-party imports
from ipykernel.ipkernel import IPythonKernel
from ipykernel import eventloops
from traitlets.config.loader import LazyConfigValue

# Local imports
from spyder_kernels.py3compat import (
    TEXT_TYPES, to_text_string, PY3)
from spyder_kernels.comms.frontendcomm import FrontendComm
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.mpl import (
    MPL_BACKENDS_FROM_SPYDER, MPL_BACKENDS_TO_SPYDER, INLINE_FIGURE_FORMATS)
from spyder_kernels.utils.nsview import (
    get_remote_data, make_remote_view, get_size)
from spyder_kernels.console.shell import SpyderShell

if PY3:
    import faulthandler


logger = logging.getLogger(__name__)


# Excluded variables from the Variable Explorer (i.e. they are not
# shown at all there)
EXCLUDED_NAMES = ['In', 'Out', 'exit', 'get_ipython', 'quit']


class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter."""

    shell_class = SpyderShell

    def __init__(self, *args, **kwargs):
        super(SpyderKernel, self).__init__(*args, **kwargs)

        self.comm_manager.get_comm = self._get_comm
        self.frontend_comm = FrontendComm(self)

        # All functions that can be called through the comm
        handlers = {
            'set_breakpoints': self.set_spyder_breakpoints,
            'set_pdb_ignore_lib': self.set_pdb_ignore_lib,
            'set_pdb_execute_events': self.set_pdb_execute_events,
            'set_pdb_use_exclamation_mark': self.set_pdb_use_exclamation_mark,
            'get_value': self.get_value,
            'load_data': self.load_data,
            'save_namespace': self.save_namespace,
            'is_defined': self.is_defined,
            'get_doc': self.get_doc,
            'get_source': self.get_source,
            'set_value': self.set_value,
            'remove_value': self.remove_value,
            'copy_value': self.copy_value,
            'set_cwd': self.set_cwd,
            'get_cwd': self.get_cwd,
            'get_syspath': self.get_syspath,
            'get_env': self.get_env,
            'close_all_mpl_figures': self.close_all_mpl_figures,
            'show_mpl_backend_errors': self.show_mpl_backend_errors,
            'get_namespace_view': self.get_namespace_view,
            'set_namespace_view_settings': self.set_namespace_view_settings,
            'get_var_properties': self.get_var_properties,
            'set_sympy_forecolor': self.set_sympy_forecolor,
            'update_syspath': self.update_syspath,
            'is_special_kernel_valid': self.is_special_kernel_valid,
            'get_matplotlib_backend': self.get_matplotlib_backend,
            'get_mpl_interactive_backend': self.get_mpl_interactive_backend,
            'pdb_input_reply': self.pdb_input_reply,
            '_interrupt_eventloop': self._interrupt_eventloop,
            'enable_faulthandler': self.enable_faulthandler,
            }
        for call_id in handlers:
            self.frontend_comm.register_call_handler(
                call_id, handlers[call_id])

        self.namespace_view_settings = {}
        self._mpl_backend_error = None
        self._running_namespace = None
        self.faulthandler_handle = None

    # -- Public API -----------------------------------------------------------
    def do_shutdown(self, restart):
        """Disable faulthandler if enabled before proceeding."""
        self.disable_faulthandler()
        super(SpyderKernel, self).do_shutdown(restart)

    def frontend_call(self, blocking=False, broadcast=True,
                      timeout=None, callback=None):
        """Call the frontend."""
        # If not broadcast, send only to the calling comm
        if broadcast:
            comm_id = None
        else:
            comm_id = self.frontend_comm.calling_comm_id

        return self.frontend_comm.remote_call(
            blocking=blocking,
            comm_id=comm_id,
            callback=callback,
            timeout=timeout)

    def enable_faulthandler(self, fn):
        """
        Open a file to save the faulthandling and identifiers for
        internal threads.
        """
        if not PY3:
            # Not implemented
            return
        self.disable_faulthandler()
        f = open(fn, 'w')
        self.faulthandler_handle = f
        f.write("Main thread id:\n")
        f.write(hex(threading.main_thread().ident))
        f.write('\nSystem threads ids:\n')
        f.write(" ".join([hex(thread.ident) for thread in threading.enumerate()
                          if thread is not threading.main_thread()]))
        f.write('\n')
        faulthandler.enable(f)

    def disable_faulthandler(self):
        """
        Cancel the faulthandling, close the file handle and remove the file.
        """
        if not PY3:
            # Not implemented
            return
        if self.faulthandler_handle:
            faulthandler.disable()
            self.faulthandler_handle.close()
            self.faulthandler_handle = None

    # --- For the Variable Explorer
    def set_namespace_view_settings(self, settings):
        """Set namespace_view_settings."""
        self.namespace_view_settings = settings

    def get_namespace_view(self):
        """
        Return the namespace view

        This is a dictionary with the following structure

        {'a':
            {
                'type': 'str',
                'size': 1,
                'view': '1',
                'python_type': 'int',
                'numpy_type': 'Unknown'
            }
        }

        Here:
        * 'a' is the variable name.
        * 'type' and 'size' are self-evident.
        * 'view' is its value or its repr computed with
          `value_to_display`.
        * 'python_type' is its Python type computed with
          `get_type_string`.
        * 'numpy_type' is its Numpy type (if any) computed with
          `get_numpy_type_string`.
        """

        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            view = make_remote_view(ns, settings, EXCLUDED_NAMES)
            return view
        else:
            return None

    def get_var_properties(self):
        """
        Get some properties of the variables in the current
        namespace
        """
        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            data = get_remote_data(ns, settings, mode='editable',
                                   more_excluded_names=EXCLUDED_NAMES)

            properties = {}
            for name, value in list(data.items()):
                properties[name] = {
                    'is_list':  self._is_list(value),
                    'is_dict':  self._is_dict(value),
                    'is_set': self._is_set(value),
                    'len': self._get_len(value),
                    'is_array': self._is_array(value),
                    'is_image': self._is_image(value),
                    'is_data_frame': self._is_data_frame(value),
                    'is_series': self._is_series(value),
                    'array_shape': self._get_array_shape(value),
                    'array_ndim': self._get_array_ndim(value)
                }

            return properties
        else:
            return None

    def get_value(self, name):
        """Get the value of a variable"""
        ns = self._get_current_namespace()
        return ns[name]

    def set_value(self, name, value):
        """Set the value of a variable"""
        ns = self._get_reference_namespace(name)
        ns[name] = value
        self.log.debug(ns)

    def remove_value(self, name):
        """Remove a variable"""
        ns = self._get_reference_namespace(name)
        ns.pop(name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        ns = self._get_reference_namespace(orig_name)
        ns[new_name] = ns[orig_name]

    def load_data(self, filename, ext, overwrite=False):
        """
        Load data from filename.

        Use 'overwrite' to determine if conflicts between variable names need
        to be handle or not.

        For example, if a loaded variable is call 'var'
        and there is already a variable 'var' in the namespace, having
        'overwrite=True' will cause 'var' to be updated.
        In the other hand, with 'overwrite=False', a new variable will be
        created with a sufix starting with 000 i.e 'var000' (default behavior).
        """
        from spyder_kernels.utils.misc import fix_reference_name

        glbs = self.shell.user_ns
        load_func = iofunctions.load_funcs[ext]
        data, error_message = load_func(filename)

        if error_message:
            return error_message

        if not overwrite:
            # We convert to list since we mutate this dictionary
            for key in list(data.keys()):
                new_key = fix_reference_name(key, blacklist=list(glbs.keys()))
                if new_key != key:
                    data[new_key] = data.pop(key)

        try:
            glbs.update(data)
        except Exception as error:
            return str(error)

        return None

    def save_namespace(self, filename):
        """Save namespace into filename"""
        ns = self._get_current_namespace()
        settings = self.namespace_view_settings
        data = get_remote_data(ns, settings, mode='picklable',
                               more_excluded_names=EXCLUDED_NAMES).copy()
        return iofunctions.save(data, filename)

    # --- For Pdb
    def _do_complete(self, code, cursor_pos):
        """Call parent class do_complete"""
        return super(SpyderKernel, self).do_complete(code, cursor_pos)

    def do_complete(self, code, cursor_pos):
        """
        Call PdB complete if we are debugging.

        Public method of ipykernel overwritten for debugging.
        """
        if self.shell.is_debugging():
            return self.shell.pdb_session.do_complete(code, cursor_pos)
        return self._do_complete(code, cursor_pos)

    def set_spyder_breakpoints(self, breakpoints):
        """
        Handle a message from the frontend
        """
        if self.shell.pdb_session:
            self.shell.pdb_session.set_spyder_breakpoints(breakpoints)

    def set_pdb_ignore_lib(self, state):
        """
        Change the "Ignore libraries while stepping" debugger setting.
        """
        if self.shell.pdb_session:
            self.shell.pdb_session.pdb_ignore_lib = state

    def set_pdb_execute_events(self, state):
        """
        Handle a message from the frontend
        """
        if self.shell.pdb_session:
            self.shell.pdb_session.pdb_execute_events = state

    def set_pdb_use_exclamation_mark(self, state):
        """
        Set an option on the current debugging session to decide wether
        the Pdb commands needs to be prefixed by '!'
        """
        if self.shell.pdb_session:
            self.shell.pdb_session.pdb_use_exclamation_mark = state

    def pdb_input_reply(self, line, echo_stack_entry=True):
        """Get a pdb command from the frontend."""
        debugger = self.shell.pdb_session
        if debugger:
            debugger._disable_next_stack_entry = not echo_stack_entry
            debugger._cmd_input_line = line
        if self.eventloop:
            # Interrupting the eventloop is only implemented when a message is
            # received on the shell channel, but this message is queued and
            # won't be processed because an `execute` message is being
            # processed. Therefore we process the message here (control chan.)
            # and request a dummy message to be sent on the shell channel to
            # stop the eventloop. This will call back `_interrupt_eventloop`.
            self.frontend_call().request_interrupt_eventloop()

    def _interrupt_eventloop(self):
        """Interrupts the eventloop."""
        # Receiving the request is enough to stop the eventloop.
        pass

    # --- For the Help plugin
    def is_defined(self, obj, force_import=False):
        """Return True if object is defined in current namespace"""
        from spyder_kernels.utils.dochelpers import isdefined

        ns = self._get_current_namespace(with_magics=True)
        return isdefined(obj, force_import=force_import, namespace=ns)

    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        try:
            import matplotlib
            matplotlib.rcParams['docstring.hardcopy'] = True
        except:
            pass
        from spyder_kernels.utils.dochelpers import getdoc

        obj, valid = self._eval(objtxt)
        if valid:
            return getdoc(obj)

    def get_source(self, objtxt):
        """Get object source"""
        from spyder_kernels.utils.dochelpers import getsource

        obj, valid = self._eval(objtxt)
        if valid:
            return getsource(obj)

    # -- For Matplolib
    def get_matplotlib_backend(self):
        """Get current matplotlib backend."""
        try:
            import matplotlib
            return MPL_BACKENDS_TO_SPYDER[matplotlib.get_backend()]
        except Exception:
            return None

    def get_mpl_interactive_backend(self):
        """
        Get current Matplotlib interactive backend.

        This is different from the current backend because, for instance, the
        user can set first the Qt5 backend, then the Inline one. In that case,
        the current backend is Inline, but the current interactive one is Qt5,
        and this backend can't be changed without a kernel restart.
        """
        # Mapping from frameworks to backend names.
        mapping = {
            'qt': 'QtAgg',
            'tk': 'TkAgg',
            'macosx': 'MacOSX'
        }

        # --- Get interactive framework
        framework = None

        # Detect if there is a graphical framework running by checking the
        # eventloop function attached to the kernel.eventloop attribute (see
        # `ipykernel.eventloops.enable_gui` for context).
        from IPython.core.getipython import get_ipython
        loop_func = get_ipython().kernel.eventloop

        if loop_func is not None:
            if loop_func == eventloops.loop_tk:
                framework = 'tk'
            elif loop_func == eventloops.loop_qt5:
                framework = 'qt'
            elif loop_func == eventloops.loop_cocoa:
                framework = 'macosx'
            else:
                # Spyder doesn't handle other backends
                framework = 'other'

        # --- Return backend according to framework
        if framework is None:
            # Since no interactive backend has been set yet, this is
            # equivalent to having the inline one.
            return 0
        elif framework in mapping:
            return MPL_BACKENDS_TO_SPYDER[mapping[framework]]
        else:
            # This covers the case of other backends (e.g. Wx or Gtk)
            # which users can set interactively with the %matplotlib
            # magic but not through our Preferences.
            return -1

    def set_matplotlib_backend(self, backend, pylab=False):
        """Set matplotlib backend given a Spyder backend option."""
        mpl_backend = MPL_BACKENDS_FROM_SPYDER[to_text_string(backend)]
        self._set_mpl_backend(mpl_backend, pylab=pylab)

    def set_mpl_inline_figure_format(self, figure_format):
        """Set the inline figure format to use with matplotlib."""
        mpl_figure_format = INLINE_FIGURE_FORMATS[figure_format]
        self._set_config_option(
            'InlineBackend.figure_format', mpl_figure_format)

    def set_mpl_inline_resolution(self, resolution):
        """Set inline figure resolution."""
        self._set_mpl_inline_rc_config('figure.dpi', resolution)

    def set_mpl_inline_figure_size(self, width, height):
        """Set inline figure size."""
        value = (width, height)
        self._set_mpl_inline_rc_config('figure.figsize', value)

    def set_mpl_inline_bbox_inches(self, bbox_inches):
        """
        Set inline print figure bbox inches.

        The change is done by updating the 'print_figure_kwargs' config dict.
        """
        from IPython.core.getipython import get_ipython
        config = get_ipython().kernel.config
        inline_config = (
            config['InlineBackend'] if 'InlineBackend' in config else {})
        print_figure_kwargs = (
            inline_config['print_figure_kwargs']
            if 'print_figure_kwargs' in inline_config else {})
        bbox_inches_dict = {
            'bbox_inches': 'tight' if bbox_inches else None}
        print_figure_kwargs.update(bbox_inches_dict)

        # This seems to be necessary for newer versions of Traitlets because
        # print_figure_kwargs doesn't return a dict.
        if isinstance(print_figure_kwargs, LazyConfigValue):
            figure_kwargs_dict = print_figure_kwargs.to_dict().get('update')
            if figure_kwargs_dict:
                print_figure_kwargs = figure_kwargs_dict

        self._set_config_option(
            'InlineBackend.print_figure_kwargs', print_figure_kwargs)

    # -- For completions
    def set_jedi_completer(self, use_jedi):
        """Enable/Disable jedi as the completer for the kernel."""
        self._set_config_option('IPCompleter.use_jedi', use_jedi)

    def set_greedy_completer(self, use_greedy):
        """Enable/Disable greedy completer for the kernel."""
        self._set_config_option('IPCompleter.greedy', use_greedy)

    def set_autocall(self, autocall):
        """Enable/Disable autocall funtionality."""
        self._set_config_option('ZMQInteractiveShell.autocall', autocall)

    # --- Additional methods
    def set_cwd(self, dirname):
        """Set current working directory."""
        os.chdir(dirname)

    def get_cwd(self):
        """Get current working directory."""
        try:
            return os.getcwd()
        except (IOError, OSError):
            pass

    def get_syspath(self):
        """Return sys.path contents."""
        return sys.path[:]

    def get_env(self):
        """Get environment variables."""
        return os.environ.copy()

    def close_all_mpl_figures(self):
        """Close all Matplotlib figures."""
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except:
            pass

    def is_special_kernel_valid(self):
        """
        Check if optional dependencies are available for special consoles.
        """
        try:
            if os.environ.get('SPY_AUTOLOAD_PYLAB_O') == 'True':
                import matplotlib
            elif os.environ.get('SPY_SYMPY_O') == 'True':
                import sympy
            elif os.environ.get('SPY_RUN_CYTHON') == 'True':
                import cython
        except Exception:
            # Use Exception instead of ImportError here because modules can
            # fail to be imported due to a lot of issues.
            if os.environ.get('SPY_AUTOLOAD_PYLAB_O') == 'True':
                return u'matplotlib'
            elif os.environ.get('SPY_SYMPY_O') == 'True':
                return u'sympy'
            elif os.environ.get('SPY_RUN_CYTHON') == 'True':
                return u'cython'
        return None

    def update_syspath(self, path_dict, new_path_dict):
        """
        Update the PYTHONPATH of the kernel.

        `path_dict` and `new_path_dict` have the paths as keys and the state
        as values. The state is `True` for active and `False` for inactive.

        `path_dict` corresponds to the previous state of the PYTHONPATH.
        `new_path_dict` corresponds to the new state of the PYTHONPATH.
        """
        # Remove old paths
        for path in path_dict:
            while path in sys.path:
                sys.path.remove(path)

        # Add new paths
        pypath = [path for path, active in new_path_dict.items() if active]
        if pypath:
            sys.path.extend(pypath)
            os.environ.update({'PYTHONPATH': os.pathsep.join(pypath)})
        else:
            os.environ.pop('PYTHONPATH', None)

    # -- Private API ---------------------------------------------------
    # --- For the Variable Explorer
    def _get_current_namespace(self, with_magics=False):
        """
        Return current namespace

        This is globals() if not debugging, or a dictionary containing
        both locals() and globals() for current frame when debugging
        """
        ns = {}
        if self.shell.is_debugging() and self.shell.pdb_session.curframe:
            # Stopped at a pdb prompt
            ns.update(self.shell.user_ns)
            ns.update(self.shell._pdb_locals)
        else:
            # Give access to the running namespace if there is one
            if self._running_namespace is None:
                ns.update(self.shell.user_ns)
            else:
                # This is true when a file is executing.
                running_globals, running_locals = self._running_namespace
                ns.update(running_globals)
                if running_locals is not None:
                    ns.update(running_locals)

        # Add magics to ns so we can show help about them on the Help
        # plugin
        if with_magics:
            line_magics = self.shell.magics_manager.magics['line']
            cell_magics = self.shell.magics_manager.magics['cell']
            ns.update(line_magics)
            ns.update(cell_magics)
        return ns

    def _get_reference_namespace(self, name):
        """
        Return namespace where reference name is defined

        It returns the globals() if reference has not yet been defined
        """
        lcls = self.shell._pdb_locals
        if name in lcls:
            return lcls
        return self.shell.user_ns

    def _get_len(self, var):
        """Return sequence length"""
        try:
            return get_size(var)
        except:
            return None

    def _is_array(self, var):
        """Return True if variable is a NumPy array"""
        try:
            import numpy
            return isinstance(var, numpy.ndarray)
        except:
            return False

    def _is_image(self, var):
        """Return True if variable is a PIL.Image image"""
        try:
            from PIL import Image
            return isinstance(var, Image.Image)
        except:
            return False

    def _is_data_frame(self, var):
        """Return True if variable is a DataFrame"""
        try:
            from pandas import DataFrame
            return isinstance(var, DataFrame)
        except:
            return False

    def _is_series(self, var):
        """Return True if variable is a Series"""
        try:
            from pandas import Series
            return isinstance(var, Series)
        except:
            return False

    def _is_list(self, var):
        """Return True if variable is a list or tuple."""
        # The try/except is necessary to fix spyder-ide/spyder#19516.
        try:
            return isinstance(var, (tuple, list))
        except Exception:
            return False

    def _is_dict(self, var):
        """Return True if variable is a dictionary."""
        # The try/except is necessary to fix spyder-ide/spyder#19516.
        try:
            return isinstance(var, dict)
        except Exception:
            return False

    def _is_set(self, var):
        """Return True if variable is a set."""
        # The try/except is necessary to fix spyder-ide/spyder#19516.
        try:
            return isinstance(var, set)
        except Exception:
            return False

    def _get_array_shape(self, var):
        """Return array's shape"""
        try:
            if self._is_array(var):
                return var.shape
            else:
                return None
        except:
            return None

    def _get_array_ndim(self, var):
        """Return array's ndim"""
        try:
            if self._is_array(var):
                return var.ndim
            else:
                return None
        except:
            return None

    # --- For the Help plugin
    def _eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        from spyder_kernels.py3compat import is_text_string

        assert is_text_string(text)
        ns = self._get_current_namespace(with_magics=True)
        try:
            return eval(text, ns), True
        except:
            return None, False

    # --- For Matplotlib
    def _set_mpl_backend(self, backend, pylab=False):
        """
        Set a backend for Matplotlib.

        backend: A parameter that can be passed to %matplotlib
                 (e.g. 'inline' or 'tk').
        pylab: Is the pylab magic should be used in order to populate the
               namespace from numpy and matplotlib
        """
        import traceback
        from IPython.core.getipython import get_ipython

        # Don't proceed further if there's any error while importing Matplotlib
        try:
            import matplotlib
        except Exception:
            return

        generic_error = (
            "\n" + "="*73 + "\n"
            "NOTE: The following error appeared when setting "
            "your Matplotlib backend!!\n" + "="*73 + "\n\n"
            "{0}"
        )

        magic = 'pylab' if pylab else 'matplotlib'

        error = None
        try:
            # This prevents Matplotlib to automatically set the backend, which
            # overrides our own mechanism.
            matplotlib.rcParams['backend'] = 'Agg'

            # Set the backend
            get_ipython().run_line_magic(magic, backend)
        except RuntimeError as err:
            # This catches errors generated by ipykernel when
            # trying to set a backend. See issue 5541
            if "GUI eventloops" in str(err):
                previous_backend = matplotlib.get_backend()
                if not backend in previous_backend.lower():
                    # Only inform about an error if the user selected backend
                    # and the one set by Matplotlib are different. Else this
                    # message is very confusing.
                    error = (
                        "\n"
                        "NOTE: Spyder *can't* set your selected Matplotlib "
                        "backend because there is a previous backend already "
                        "in use.\n\n"
                        "Your backend will be {0}".format(previous_backend)
                    )
            # This covers other RuntimeError's
            else:
                error = generic_error.format(traceback.format_exc())
        except ImportError as err:
            additional_info = (
                "This is most likely caused by missing packages in the Python "
                "environment\n"
                "or installation whose interpreter is located at:\n\n"
                "    {0}"
            ).format(sys.executable)

            error = generic_error.format(err) + '\n\n' + additional_info
        except Exception:
            error = generic_error.format(traceback.format_exc())

        self._mpl_backend_error = error

    def _set_config_option(self, option, value):
        """
        Set config options using the %config magic.

        As parameters:
            option: config option, for example 'InlineBackend.figure_format'.
            value: value of the option, for example 'SVG', 'Retina', etc.
        """
        from IPython.core.getipython import get_ipython
        try:
            base_config = "{option} = "
            value_line = (
                "'{value}'" if isinstance(value, TEXT_TYPES) else "{value}")
            config_line = base_config + value_line
            get_ipython().run_line_magic(
                'config',
                config_line.format(option=option, value=value))
        except Exception:
            pass

    def _set_mpl_inline_rc_config(self, option, value):
        """
        Update any of the Matplolib rcParams given an option and value.
        """
        try:
            from matplotlib import rcParams
            rcParams[option] = value
        except Exception:
            # Needed in case matplolib isn't installed
            pass

    def show_mpl_backend_errors(self):
        """Show Matplotlib backend errors after the prompt is ready."""
        if self._mpl_backend_error is not None:
            print(self._mpl_backend_error)  # spyder: test-skip

    def set_sympy_forecolor(self, background_color='dark'):
        """Set SymPy forecolor depending on console background."""
        if os.environ.get('SPY_SYMPY_O') == 'True':
            try:
                from sympy import init_printing
                from IPython.core.getipython import get_ipython
                if background_color == 'dark':
                    init_printing(forecolor='White', ip=get_ipython())
                elif background_color == 'light':
                    init_printing(forecolor='Black', ip=get_ipython())
            except Exception:
                pass

    # --- Others
    def _load_autoreload_magic(self):
        """Load %autoreload magic."""
        from IPython.core.getipython import get_ipython
        try:
            get_ipython().run_line_magic('reload_ext', 'autoreload')
            get_ipython().run_line_magic('autoreload', '2')
        except Exception:
            pass

    def _load_wurlitzer(self):
        """Load wurlitzer extension."""
        # Wurlitzer has no effect on Windows
        if not os.name == 'nt':
            from IPython.core.getipython import get_ipython
            # Enclose this in a try/except because if it fails the
            # console will be totally unusable.
            # Fixes spyder-ide/spyder#8668
            try:
                get_ipython().run_line_magic('reload_ext', 'wurlitzer')
            except Exception:
                pass

    def _get_comm(self, comm_id):
        """
        We need to redefine this method from ipykernel.comm_manager to
        avoid showing a warning when the comm corresponding to comm_id
        is not present.

        Fixes spyder-ide/spyder#15498
        """
        try:
            return self.comm_manager.comms[comm_id]
        except KeyError:
            pass
