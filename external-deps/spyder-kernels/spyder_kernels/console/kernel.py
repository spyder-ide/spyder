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
import faulthandler
import json
import logging
import os
import re
import sys
import traceback
import tempfile
import threading

# Third-party imports
from ipykernel.ipkernel import IPythonKernel
from ipykernel import get_connection_info
from traitlets.config.loader import LazyConfigValue
import zmq
from zmq.utils.garbage import gc

# Local imports
import spyder_kernels
from spyder_kernels.comms.frontendcomm import FrontendComm
from spyder_kernels.comms.decorators import (
    register_comm_handlers, comm_handler)
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.mpl import automatic_backend, MPL_BACKENDS_TO_SPYDER
from spyder_kernels.utils.nsview import (
    get_remote_data, make_remote_view, get_size)
from spyder_kernels.console.shell import SpyderShell
from spyder_kernels.comms.utils import WriteContext


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
        register_comm_handlers(self, self.frontend_comm)
        register_comm_handlers(self.shell, self.frontend_comm)

        self.namespace_view_settings = {}
        self.faulthandler_handle = None
        self._cwd_initialised = False

        # Add handlers to control to process messages while debugging
        self.control_handlers['comm_msg'] = self.control_comm_msg
        self.control_handlers['complete_request'] = self.shell_handlers[
            'complete_request']

        # Socket to signal shell_stream locally
        self.loopback_socket = None

        # To track the interactive backend
        self.interactive_backend = None

    @property
    def kernel_info(self):
        # Used for checking correct version by spyder
        infos = super().kernel_info
        infos.update({
            "spyder_kernels_info": (
                spyder_kernels.__version__,
                sys.executable
            )
        })
        return infos

    # -- Public API -----------------------------------------------------------
    def frontend_call(self, blocking=False, broadcast=True,
                      timeout=None, callback=None, display_error=False):
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
            timeout=timeout,
            display_error=display_error)

    def get_state(self):
        """"get current state to send to the frontend"""
        state = {}
        with WriteContext("get_state"):
            if self._cwd_initialised:
                state["cwd"] = self.get_cwd()
            state["namespace_view"] = self.get_namespace_view()
            state["var_properties"] = self.get_var_properties()
        return state

    def publish_state(self):
        """Publish the current kernel state"""
        if not self.frontend_comm.is_open():
            # No one to send to
            return
        try:
            self.frontend_call(blocking=False).update_state(self.get_state())
        except Exception:
            pass

    def enable_faulthandler(self):
        """
        Open a file to save the faulthandling and identifiers for
        internal threads.
        """
        fault_dir = None
        if sys.platform.startswith('linux'):
            # Do not use /tmp for temporary files
            try:
                from xdg.BaseDirectory import xdg_data_home
                fault_dir = os.path.join(xdg_data_home, "spyder")
                os.makedirs(fault_dir, exist_ok=True)
            except Exception:
                fault_dir = None

        self.faulthandler_handle = tempfile.NamedTemporaryFile(
            'wt', suffix='.fault', dir=fault_dir
        )

        main_id = threading.main_thread().ident
        system_ids = [
            thread.ident for thread in threading.enumerate()
            if thread is not threading.main_thread()
        ]
        faulthandler.enable(self.faulthandler_handle)
        return self.faulthandler_handle.name, main_id, system_ids

    @comm_handler
    def safe_exec(self, filename):
        """Safely execute a file using IPKernelApp._exec_file."""
        self.parent._exec_file(filename)

    @comm_handler
    def get_fault_text(self, fault_filename, main_id, ignore_ids):
        """Get fault text from old run."""
        # Read file
        try:
            with open(fault_filename, 'r') as f:
                fault = f.read()
        except FileNotFoundError:
            return
        except UnicodeDecodeError as e:
            return (
                "Can not read fault file!\n"
                + "UnicodeDecodeError: " + str(e))

        # Remove file
        try:
            os.remove(fault_filename)
        except Exception:
            pass

        # Process file
        if not fault:
            return

        thread_regex = (
            r"(Current thread|Thread) "
            r"(0x[\da-f]+) \(most recent call first\):"
            r"(?:.|\r\n|\r|\n)+?(?=Current thread|Thread|\Z)")
        # Keep line for future improvements
        # files_regex = r"File \"([^\"]+)\", line (\d+) in (\S+)"

        text = ""
        start_idx = 0
        for idx, match in enumerate(re.finditer(thread_regex, fault)):
            # Add anything non-matched
            text += fault[start_idx:match.span()[0]]
            start_idx = match.span()[1]
            thread_id = int(match.group(2), base=16)
            if thread_id != main_id:
                if thread_id in ignore_ids:
                    continue
                if "wurlitzer.py" in match.group(0):
                    # Wurlitzer threads are launched later
                    continue
                text += "\n" + match.group(0) + "\n"
            else:
                try:
                    pattern = (r".*(?:/IPython/core/interactiveshell\.py|"
                               r"\\IPython\\core\\interactiveshell\.py).*")
                    match_internal = next(re.finditer(pattern, match.group(0)))
                    end_idx = match_internal.span()[0]
                except StopIteration:
                    end_idx = None
                text += "\nMain thread:\n" + match.group(0)[:end_idx] + "\n"

        # Add anything after match
        text += fault[start_idx:]
        return text

    def get_system_threads_id(self):
        """Return the list of system threads id."""
        ignore_threads = [
            self.parent.poller,  # Parent poller
            self.shell.history_manager.save_thread,  # history
            self.parent.heartbeat,  # heartbeat
            self.parent.iopub_thread.thread,  # iopub
            gc.thread,  # ZMQ garbage collector thread
            self.parent.control_thread,  # control
        ]
        return [
            thread.ident for thread in ignore_threads if thread is not None]

    def filter_stack(self, stack, is_main):
        """Return the part of the stack the user needs to see."""
        # Remove wurlitzer frames
        for frame_summary in stack:
            if "wurlitzer.py" in frame_summary.filename:
                return
        # Cleanup main thread
        if is_main:
            start_idx = -1
            for idx in range(len(stack)):
                if stack[idx].filename.endswith(
                        ("IPython/core/interactiveshell.py",
                         "IPython\\core\\interactiveshell.py")):
                    start_idx = idx + 1
            if start_idx != -1:
                stack = stack[start_idx:]
            else:
                stack = []
        return stack

    @comm_handler
    def get_current_frames(self, ignore_internal_threads=True):
        """Get the current frames."""
        ignore_list = self.get_system_threads_id()
        main_id = threading.main_thread().ident
        frames = {}
        thread_names = {thread.ident: thread.name
                        for thread in threading.enumerate()}

        for thread_id, frame in sys._current_frames().items():
            stack = traceback.StackSummary.extract(
                traceback.walk_stack(frame))
            stack.reverse()
            if ignore_internal_threads:
                if thread_id in ignore_list:
                    continue
                stack = self.filter_stack(stack, main_id == thread_id)
            if stack is not None:
                if thread_id in thread_names:
                    thread_name = thread_names[thread_id]
                else:
                    thread_name = str(thread_id)
                frames[thread_name] = stack
        return frames

    # --- For the Variable Explorer
    @comm_handler
    def get_namespace_view(self, frame=None):
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
            ns = self.shell._get_current_namespace(frame=frame)
            view = make_remote_view(ns, settings, EXCLUDED_NAMES)
            return view
        else:
            return None

    @comm_handler
    def get_var_properties(self):
        """
        Get some properties of the variables in the current
        namespace
        """
        settings = self.namespace_view_settings
        if settings:
            ns = self.shell._get_current_namespace()
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

    @comm_handler
    def get_value(self, name):
        """Get the value of a variable"""
        ns = self.shell._get_current_namespace()
        return ns[name]

    @comm_handler
    def set_value(self, name, value):
        """Set the value of a variable"""
        ns = self.shell._get_reference_namespace(name)
        ns[name] = value
        self.log.debug(ns)

    @comm_handler
    def remove_value(self, name):
        """Remove a variable"""
        ns = self.shell._get_reference_namespace(name)
        ns.pop(name)

    @comm_handler
    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        ns = self.shell._get_reference_namespace(orig_name)
        ns[new_name] = ns[orig_name]

    @comm_handler
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

    @comm_handler
    def save_namespace(self, filename):
        """Save namespace into filename"""
        ns = self.shell._get_current_namespace()
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

    def interrupt_eventloop(self):
        """
        Interrupts the eventloop.

        To be used when the main thread is blocked by a call to self.eventloop.
        This can be called from another thread, e.g. the control thread.

        note:
        Interrupting the eventloop is only implemented when a message is
        received on the shell channel, but this message is queued and
        won't be processed because an `execute` message is being
        processed.
        """
        if not self.eventloop:
            return

        if self.loopback_socket is None:
            # Add socket to signal shell_stream locally
            self.loopback_socket = self.shell_stream.socket.context.socket(
                zmq.DEALER)
            port = json.loads(get_connection_info())['shell_port']
            self.loopback_socket.connect("tcp://127.0.0.1:%i" % port)
            # Add dummy handler
            self.shell_handlers["interrupt_eventloop"] = (
                lambda stream, ident, parent: None)

        self.session.send(
            self.loopback_socket, self.session.msg("interrupt_eventloop"))

    # --- For the Help plugin
    @comm_handler
    def is_defined(self, obj, force_import=False):
        """Return True if object is defined in current namespace"""
        from spyder_kernels.utils.dochelpers import isdefined

        ns = self.shell._get_current_namespace(with_magics=True)
        return isdefined(obj, force_import=force_import, namespace=ns)

    @comm_handler
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

    @comm_handler
    def get_source(self, objtxt):
        """Get object source"""
        from spyder_kernels.utils.dochelpers import getsource

        obj, valid = self._eval(objtxt)
        if valid:
            return getsource(obj)

    # -- For Matplolib
    @comm_handler
    def get_matplotlib_backend(self):
        """Get current matplotlib backend."""
        try:
            import matplotlib
            return MPL_BACKENDS_TO_SPYDER[matplotlib.get_backend().lower()]
        except Exception:
            return None

    @comm_handler
    def get_mpl_interactive_backend(self):
        """
        Get current Matplotlib interactive backend.

        This is different from the current backend because, for instance, the
        user can set first the Qt backend, then the Inline one. In that case,
        the current backend is Inline, but the current interactive one is Qt,
        and this backend can't be changed without a kernel restart.
        """
        # Backends that Spyder can handle
        recognized_backends = {'qt', 'tk', 'macosx'}

        # --- Return backend according to framework
        if self.interactive_backend is None:
            # Since no interactive backend has been set yet, this is equivalent
            # to having the inline one.
            return 'inline'
        elif self.interactive_backend in recognized_backends:
            return self.interactive_backend
        else:
            # This covers the case of other backends (e.g. Wx or Gtk)
            # which users can set interactively with the %matplotlib
            # magic but not through our Preferences.
            return -1

    @comm_handler
    def set_matplotlib_conf(self, conf):
        """Set matplotlib configuration"""
        pylab_autoload_n = 'pylab/autoload'
        pylab_backend_n = 'pylab/backend'
        figure_format_n = 'pylab/inline/figure_format'
        resolution_n = 'pylab/inline/resolution'
        width_n = 'pylab/inline/width'
        height_n = 'pylab/inline/height'
        fontsize_n = 'pylab/inline/fontsize'
        bottom_n = 'pylab/inline/bottom'
        bbox_inches_n = 'pylab/inline/bbox_inches'
        inline_backend = 'inline'

        if pylab_autoload_n in conf or pylab_backend_n in conf:
            self._set_mpl_backend(
                conf.get(pylab_backend_n, inline_backend),
                pylab=conf.get(pylab_autoload_n, False)
            )

        if figure_format_n in conf:
            self._set_config_option(
                'InlineBackend.figure_format',
                conf[figure_format_n]
            )

        if resolution_n in conf:
            self._set_mpl_inline_rc_config('figure.dpi', conf[resolution_n])

        if width_n in conf and height_n in conf:
            self._set_mpl_inline_rc_config(
                'figure.figsize',
                (conf[width_n], conf[height_n])
            )

        if fontsize_n in conf:
            self._set_mpl_inline_rc_config('font.size', conf[fontsize_n])

        if bottom_n in conf:
            self._set_mpl_inline_rc_config(
                'figure.subplot.bottom',
                conf[bottom_n]
            )

        if bbox_inches_n in conf:
            self.set_mpl_inline_bbox_inches(conf[bbox_inches_n])


    def set_mpl_inline_bbox_inches(self, bbox_inches):
        """
        Set inline print figure bbox inches.

        The change is done by updating the 'print_figure_kwargs' config dict.
        """
        config = self.config
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
    @comm_handler
    def set_configuration(self, conf):
        """Set kernel configuration"""
        ret = {}
        for key, value in conf.items():
            if key == "cwd":
                self._cwd_initialised = True
                os.chdir(value)
                self.publish_state()
            elif key == "namespace_view_settings":
                self.namespace_view_settings = value
                self.publish_state()
            elif key == "pdb":
                self.shell.set_pdb_configuration(value)
            elif key == "faulthandler":
                if value:
                    ret[key] = self.enable_faulthandler()
            elif key == "special_kernel":
                try:
                    self.set_special_kernel(value)
                except Exception:
                    ret["special_kernel_error"] = value
            elif key == "color scheme":
                self.set_color_scheme(value)
            elif key == "jedi_completer":
                self.set_jedi_completer(value)
            elif key == "greedy_completer":
                self.set_greedy_completer(value)
            elif key == "autocall":
                self.set_autocall(value)
            elif key == "matplotlib":
                self.set_matplotlib_conf(value)
            elif key == "update_gui":
                self.shell.update_gui_frontend = value
            elif key == "wurlitzer":
                if value:
                    self._load_wurlitzer()
            elif key == "autoreload_magic":
                self._autoreload_magic(value)
        return ret

    def set_color_scheme(self, color_scheme):
        if color_scheme == "dark":
            # Needed to change the colors of tracebacks
            self.shell.run_line_magic("colors", "linux")
            self.set_sympy_forecolor(background_color='dark')
        elif color_scheme == "light":
            self.shell.run_line_magic("colors", "lightbg")
            self.set_sympy_forecolor(background_color='light')

    def get_cwd(self):
        """Get current working directory."""
        try:
            return os.getcwd()
        except (IOError, OSError):
            pass

    @comm_handler
    def get_syspath(self):
        """Return sys.path contents."""
        return sys.path[:]

    @comm_handler
    def get_env(self):
        """Get environment variables."""
        return os.environ.copy()

    @comm_handler
    def close_all_mpl_figures(self):
        """Close all Matplotlib figures."""
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except:
            pass

    def set_special_kernel(self, special):
        """
        Check if optional dependencies are available for special consoles.
        """
        self.shell.special = None
        if special is None:
            return

        if special == "pylab":
            import matplotlib  # noqa
            exec("from pylab import *", self.shell.user_ns)
            self.shell.special = special
            return
           
        if special == "sympy":
            import sympy  # noqa
            sympy_init = "\n".join([
                "from sympy import *",
                "x, y, z, t = symbols('x y z t')",
                "k, m, n = symbols('k m n', integer=True)",
                "f, g, h = symbols('f g h', cls=Function)",
                "init_printing()",
            ])
            exec(sympy_init, self.shell.user_ns)
            self.shell.special = special
            return

        if special == "cython":
            import cython  # noqa

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
            pyximport.install(setup_args=pyx_setup_args,
                              reload_support=True)

            self.shell.run_line_magic("reload_ext", "Cython")
            self.shell.special = special
            return

        raise NotImplementedError(f"{special}")

    @comm_handler
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

        assert isinstance(text, str)
        ns = self.shell._get_current_namespace(with_magics=True)
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

        if backend == "auto":
            backend = automatic_backend()

        error = None
        try:
            # This prevents Matplotlib to automatically set the backend, which
            # overrides our own mechanism.
            matplotlib.rcParams['backend'] = 'Agg'

            # Set the backend
            self.shell.run_line_magic(magic, backend)
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
        if error:
            print(error)

    def _set_config_option(self, option, value):
        """
        Set config options using the %config magic.

        As parameters:
            option: config option, for example 'InlineBackend.figure_format'.
            value: value of the option, for example 'SVG', 'Retina', etc.
        """
        try:
            base_config = "{option} = "
            value_line = (
                "'{value}'" if isinstance(value, str) else "{value}")
            config_line = base_config + value_line
            self.shell.run_line_magic(
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

    def set_sympy_forecolor(self, background_color='dark'):
        """Set SymPy forecolor depending on console background."""
        if self.shell.special != "sympy":
            return

        try:
            from sympy import init_printing
            if background_color == 'dark':
                init_printing(forecolor='White', ip=self.shell)
            elif background_color == 'light':
                init_printing(forecolor='Black', ip=self.shell)
        except Exception:
            pass

    # --- Others
    def _autoreload_magic(self, enable):
        """Load %autoreload magic."""
        try:
            if enable:
                self.shell.run_line_magic('reload_ext', 'autoreload')
                self.shell.run_line_magic('autoreload', "2")
            else:
                self.shell.run_line_magic('autoreload', "off")

        except Exception:
            pass

    def _load_wurlitzer(self):
        """Load wurlitzer extension."""
        # Wurlitzer has no effect on Windows
        if not os.name == 'nt':
            # Enclose this in a try/except because if it fails the
            # console will be totally unusable.
            # Fixes spyder-ide/spyder#8668
            try:
                self.shell.run_line_magic('reload_ext', 'wurlitzer')
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

    def control_comm_msg(self, stream, ident, msg):
        """
        Handler for comm_msg messages from control channel.

        If comm is not open yet, cache message.
        """
        content = msg['content']
        comm_id = content['comm_id']
        comm = self.comm_manager.get_comm(comm_id)
        if comm is None:
            self.frontend_comm.cache_message(comm_id, msg)
            return
        try:
            comm.handle_msg(msg)
        except Exception:
            self.comm_manager.log.error(
                'Exception in comm_msg for %s', comm_id, exc_info=True)

    def pre_handler_hook(self):
        """Hook to execute before calling message handler"""
        pass

    def post_handler_hook(self):
        """Hook to execute after calling message handler"""
        # keep ipykernel behavior of resetting sigint every call
        self.shell.register_debugger_sigint()
        # Reset tracing function so that pdb.set_trace works
        sys.settrace(None)
