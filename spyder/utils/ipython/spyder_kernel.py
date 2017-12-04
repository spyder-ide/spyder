# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder kernel for Jupyter
"""

# Standard library imports
import os
import os.path as osp
import sys

# Third-party imports
from ipykernel.ipkernel import IPythonKernel


PY2 = sys.version[0] == '2'

# Check if we are running under an external interpreter
# We add "spyder" to sys.path for external interpreters,
# so relative imports work!
IS_EXT_INTERPRETER = os.environ.get('EXTERNAL_INTERPRETER', '').lower() == "true"

# Excluded variables from the Variable Explorer (i.e. they are not
# shown at all there)
EXCLUDED_NAMES = ['In', 'Out', 'exit', 'get_ipython', 'quit']

# To be able to get and set variables between Python 2 and 3
PICKLE_PROTOCOL = 2


class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter"""

    def __init__(self, *args, **kwargs):
        super(SpyderKernel, self).__init__(*args, **kwargs)

        self.namespace_view_settings = {}

        self._pdb_obj = None
        self._pdb_step = None
        self._do_publish_pdb_state = True
        self._mpl_backend_error = None

        kernel_config = self.config.get('IPKernelApp', None)
        if kernel_config is not None:
            cf = kernel_config['connection_file']
            json_file = osp.basename(cf)
            self._kernel_id = json_file.split('.json')[0]
        else:
            self._kernel_id = None

    @property
    def _pdb_frame(self):
        """Return current Pdb frame if there is any"""
        if self._pdb_obj is not None and self._pdb_obj.curframe is not None:
            return self._pdb_obj.curframe

    @property
    def _pdb_locals(self):
        """
        Return current Pdb frame locals if available. Otherwise
        return an empty dictionary
        """
        if self._pdb_frame:
            return self._pdb_obj.curframe_locals
        else:
            return {}

    # -- Public API ---------------------------------------------------
    # --- For the Variable Explorer
    def get_namespace_view(self):
        """
        Return the namespace view

        This is a dictionary with the following structure

        {'a': {'color': '#800000', 'size': 1, 'type': 'str', 'view': '1'}}

        Here:
        * 'a' is the variable name
        * 'color' is the color used to show it
        * 'size' and 'type' are self-evident
        * and'view' is its value or the text shown in the last column
        """
        if not IS_EXT_INTERPRETER:
            from spyder.widgets.variableexplorer.utils import make_remote_view
        else:
            from widgets.variableexplorer.utils import make_remote_view

        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            view = repr(make_remote_view(ns, settings, EXCLUDED_NAMES))
            return view
        else:
            return repr(None)

    def get_var_properties(self):
        """
        Get some properties of the variables in the current
        namespace
        """
        if not IS_EXT_INTERPRETER:
            from spyder.widgets.variableexplorer.utils import get_remote_data
        else:
            from widgets.variableexplorer.utils import get_remote_data

        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            data = get_remote_data(ns, settings, mode='editable',
                                   more_excluded_names=EXCLUDED_NAMES)

            properties = {}
            for name, value in list(data.items()):
                properties[name] = {
                    'is_list':  isinstance(value, (tuple, list)),
                    'is_dict':  isinstance(value, dict),
                    'len': self._get_len(value),
                    'is_array': self._is_array(value),
                    'is_image': self._is_image(value),
                    'is_data_frame': self._is_data_frame(value),
                    'is_series': self._is_series(value),
                    'array_shape': self._get_array_shape(value),
                    'array_ndim': self._get_array_ndim(value)
                }

            return repr(properties)
        else:
            return repr(None)

    def send_spyder_msg(self, spyder_msg_type, content=None, data=None):
        """publish custom messages to the spyder frontend

        Parameters
        ----------

        spyder_msg_type: str
            The spyder message type
        content: dict
            The (JSONable) content of the message
        data: any
            Any object that is serializable by cloudpickle (should be most
            things). Will arrive as cloudpickled bytes in `.buffers[0]`.
        """
        import cloudpickle

        if content is None:
            content = {}
        content['spyder_msg_type'] = spyder_msg_type
        self.session.send(
            self.iopub_socket,
            'spyder_msg',
            content=content,
            buffers=[cloudpickle.dumps(data, protocol=PICKLE_PROTOCOL)],
            parent=self._parent_header,
        )

    def get_value(self, name):
        """Get the value of a variable"""
        ns = self._get_current_namespace()
        value = ns[name]
        try:
            self.send_spyder_msg('data', data=value)
        except:
            # * There is no need to inform users about
            #   these errors.
            # * value = None makes Spyder to ignore
            #   petitions to display a value
            self.send_spyder_msg('data', data=None)
        self._do_publish_pdb_state = False

    def set_value(self, name, value, PY2_frontend):
        """Set the value of a variable"""
        import cloudpickle
        ns = self._get_reference_namespace(name)

        # We send serialized values in a list of one element
        # from Spyder to the kernel, to be able to send them
        # at all in Python 2
        svalue = value[0]

        # We need to convert svalue to bytes if the frontend
        # runs in Python 2 and the kernel runs in Python 3
        if PY2_frontend and not PY2:
            svalue = bytes(svalue, 'latin-1')

        # Deserialize and set value in namespace
        dvalue = cloudpickle.loads(svalue)
        ns[name] = dvalue

    def remove_value(self, name):
        """Remove a variable"""
        ns = self._get_reference_namespace(name)
        ns.pop(name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        ns = self._get_reference_namespace(orig_name)
        ns[new_name] = ns[orig_name]

    def load_data(self, filename, ext):
        """Load data from filename"""
        if not IS_EXT_INTERPRETER:
            from spyder.utils.iofuncs import iofunctions
            from spyder.utils.misc import fix_reference_name
        else:
            from utils.iofuncs import iofunctions
            from utils.misc import fix_reference_name

        glbs = self._mglobals()

        load_func = iofunctions.load_funcs[ext]
        data, error_message = load_func(filename)

        if error_message:
            return error_message

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
        if not IS_EXT_INTERPRETER:
            from spyder.utils.iofuncs import iofunctions
            from spyder.widgets.variableexplorer.utils import get_remote_data
        else:
            from utils.iofuncs import iofunctions
            from widgets.variableexplorer.utils import get_remote_data

        ns = self._get_current_namespace()
        settings = self.namespace_view_settings
        data = get_remote_data(ns, settings, mode='picklable',
                               more_excluded_names=EXCLUDED_NAMES).copy()
        return iofunctions.save(data, filename)

    # --- For Pdb
    def publish_pdb_state(self):
        """
        Publish Variable Explorer state and Pdb step through
        send_spyder_msg.
        """
        if self._pdb_obj and self._do_publish_pdb_state:
            state = dict(namespace_view = self.get_namespace_view(),
                         var_properties = self.get_var_properties(),
                         step = self._pdb_step)
            self.send_spyder_msg('pdb_state', content={'pdb_state': state})
        self._do_publish_pdb_state = True

    def pdb_continue(self):
        """
        Tell the console to run 'continue' after entering a
        Pdb session to get to the first breakpoint.

        Fixes issue 2034
        """
        if self._pdb_obj:
            self.send_spyder_msg('pdb_continue')

    # --- For the Help plugin
    def is_defined(self, obj, force_import=False):
        """Return True if object is defined in current namespace"""
        if not IS_EXT_INTERPRETER:
            from spyder.utils.dochelpers import isdefined
        else:
            from utils.dochelpers import isdefined

        ns = self._get_current_namespace(with_magics=True)
        return isdefined(obj, force_import=force_import, namespace=ns)

    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        try:
            import matplotlib
            matplotlib.rcParams['docstring.hardcopy'] = True
        except:
            pass

        if not IS_EXT_INTERPRETER:
            from spyder.utils.dochelpers import getdoc
        else:
            from utils.dochelpers import getdoc

        obj, valid = self._eval(objtxt)
        if valid:
            return getdoc(obj)

    def get_source(self, objtxt):
        """Get object source"""
        if not IS_EXT_INTERPRETER:
            from spyder.utils.dochelpers import getsource
        else:
            from utils.dochelpers import getsource

        obj, valid = self._eval(objtxt)
        if valid:
            return getsource(obj)

    # --- Additional methods
    def set_cwd(self, dirname):
        """Set current working directory."""
        os.chdir(dirname)

    def get_cwd(self):
        """Get current working directory."""
        return os.getcwd()

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
            del plt
        except:
            pass

    # -- Private API ---------------------------------------------------
    # --- For the Variable Explorer
    def _get_current_namespace(self, with_magics=False):
        """
        Return current namespace

        This is globals() if not debugging, or a dictionary containing
        both locals() and globals() for current frame when debugging
        """
        ns = {}
        glbs = self._mglobals()

        if self._pdb_frame is None:
            ns.update(glbs)
        else:
            ns.update(glbs)
            ns.update(self._pdb_locals)

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
        glbs = self._mglobals()
        if self._pdb_frame is None:
            return glbs
        else:
            lcls = self._pdb_locals
            if name in lcls:
                return lcls
            else:
                return glbs

    def _mglobals(self):
        """Return current globals -- handles Pdb frames"""
        if self._pdb_frame is not None:
            return self._pdb_frame.f_globals
        else:
            return self.shell.user_ns

    def _get_len(self, var):
        """Return sequence length"""
        try:
            return len(var)
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

    # --- For Pdb
    def _register_pdb_session(self, pdb_obj):
        """Register Pdb session to use it later"""
        self._pdb_obj = pdb_obj

    def _set_spyder_breakpoints(self):
        """Set all Spyder breakpoints in an active pdb session"""
        if not self._pdb_obj:
            return
        self._pdb_obj.set_spyder_breakpoints()

    # --- For the Help plugin
    def _eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        if not IS_EXT_INTERPRETER:
            from spyder.py3compat import is_text_string
        else:
            from py3compat import is_text_string

        assert is_text_string(text)
        ns = self._get_current_namespace(with_magics=True)
        try:
            return eval(text, ns), True
        except:
            return None, False

    # --- Others
    def _set_mpl_backend(self, backend, pylab=False):
        """
        Set a backend for Matplotlib.

        backend: A parameter that can be passed to %matplotlib
                 (e.g. inline or tk).
        """
        import traceback
        from IPython.core.getipython import get_ipython

        generic_error = ("\n"
                         "NOTE: The following error appeared when setting "
                         "your Matplotlib backend\n\n"
                         "{0}")

        error = None
        try:
            if pylab:
                get_ipython().run_line_magic('pylab', backend)
            else:
                get_ipython().run_line_magic('matplotlib', backend)
        except RuntimeError as err:
            # This catches errors generated by ipykernel when
            # trying to set a backend. See issue 5541
            if "GUI eventloops" in str(err):
                import matplotlib
                previous_backend = matplotlib.get_backend()
                error = ("\n"
                         "NOTE: Spyder *can't* set your selected Matplotlib "
                         "backend because there is a previous backend already "
                         "in use.\n\n"
                         "Your backend will be {0}".format(previous_backend))
                del matplotlib
            # This covers other RuntimeError's
            else:
                error = generic_error.format(traceback.format_exc())
        except Exception:
            error = generic_error.format(traceback.format_exc())

        self._mpl_backend_error = error

    def _show_mpl_backend_errors(self):
        """Show Matplotlib backend errors after the prompt is ready."""
        if self._mpl_backend_error is not None:
            print(self._mpl_backend_error)  # spyder: test-skip

