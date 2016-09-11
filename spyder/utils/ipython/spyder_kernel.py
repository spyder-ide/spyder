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

# Third-party imports
from ipykernel.datapub import publish_data
from ipykernel.ipkernel import IPythonKernel
from ipykernel.pickleutil import CannedObject
from ipykernel.serialize import deserialize_object

# Check if we are running under an external interpreter
IS_EXT_INTERPRETER = os.environ.get('EXTERNAL_INTERPRETER', '').lower() == "true"

# Local imports
if not IS_EXT_INTERPRETER:
    from spyder.utils.iofuncs import iofunctions
    from spyder.utils.misc import fix_reference_name
    from spyder.widgets.variableexplorer.utils import (get_remote_data,
                                                       make_remote_view)
else:
    # We add "spyder" to sys.path for external interpreters, so this works!
    # See create_kernel_spec of plugins/ipythonconsole
    from utils.iofuncs import iofunctions
    from utils.misc import fix_reference_name
    from widgets.variableexplorer.utils import (get_remote_data,
                                                make_remote_view)


class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter"""

    def __init__(self, *args, **kwargs):
        super(SpyderKernel, self).__init__(*args, **kwargs)
        self.pdb_frame = None
        self.pdb_locals = {}
        self.namespace_view_settings = {}

    # -- Public API ---------------------------------------------------
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
        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            more_excluded_names = ['In', 'Out']
            view = make_remote_view(ns, settings, more_excluded_names)
            return view

    def get_var_properties(self):
        """
        Get some properties of the variables in the current
        namespace
        """
        settings = self.namespace_view_settings
        if settings:
            ns = self._get_current_namespace()
            data = get_remote_data(ns, settings, mode='editable',
                                   more_excluded_names=['In', 'Out'])

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

            return properties
        else:
            return {}

    def get_value(self, name):
        """Get the value of a variable"""
        ns = self._get_current_namespace()
        value = ns[name]
        publish_data({'__spy_data__': value})

    def set_value(self, name, value):
        """Set the value of a variable"""
        ns = self._get_reference_namespace(name)
        value = deserialize_object(value)[0]
        if isinstance(value, CannedObject):
            value = value.get_object()
        ns[name] = value

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
        ns = self._get_current_namespace()
        settings = self.namespace_view_settings
        data = get_remote_data(ns, settings, mode='picklable',
                               more_excluded_names=['In', 'Out']).copy()
        return iofunctions.save(data, filename)

    # -- Private API ---------------------------------------------------
    def _get_current_namespace(self, with_magics=False):
        """
        Return current namespace

        This is globals() if not debugging, or a dictionary containing
        both locals() and globals() for current frame when debugging
        """
        ns = {}
        glbs = self._mglobals()

        if self.pdb_frame is None:
            ns.update(glbs)
        else:
            ns.update(glbs)
            ns.update(self.pdb_locals)

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
        if self.pdb_frame is None:
            return glbs
        else:
            lcls = self.pdb_locals
            if name in lcls:
                return lcls
            else:
                return glbs

    def _mglobals(self):
        """Return current globals -- handles Pdb frames"""
        if self.pdb_frame is not None:
            return self.pdb_frame.f_globals
        else:
            return self.shell.user_ns

    def _get_len(self, var):
        """Return sequence length"""
        try:
            return len(var)
        except TypeError:
            return None

    def _is_array(self, var):
        """Return True if variable is a NumPy array"""
        try:
            import numpy
            return isinstance(var, numpy.ndarray)
        except ImportError:
            return False

    def _is_image(self, var):
        """Return True if variable is a PIL.Image image"""
        try:
            from PIL import Image
            return isinstance(var, Image.Image)
        except ImportError:
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
            return var.shape
        except AttributeError:
            return None

    def _get_array_ndim(self, var):
        """Return array's ndim"""
        try:
            return var.ndim
        except AttributeError:
            return None
