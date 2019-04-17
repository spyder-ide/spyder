# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Kernel spec for Spyder kernels
"""

import os
import os.path as osp

from jupyter_client.kernelspec import KernelSpec

from spyder.config.base import (SAFE_MODE, get_module_source_path,
                                running_under_pytest)
from spyder.config.main import CONF
from spyder.utils.encoding import to_unicode_from_fs
from spyder.utils.programs import is_python_interpreter
from spyder.py3compat import PY2, iteritems, to_text_string, to_binary_string
from spyder.utils.misc import (add_pathlist_to_PYTHONPATH,
                               get_python_executable)


class SpyderKernelSpec(KernelSpec):
    """Kernel spec for Spyder kernels"""

    def __init__(self, is_cython=False, is_pylab=False,
                 is_sympy=False, **kwargs):
        super(SpyderKernelSpec, self).__init__(**kwargs)
        self.is_cython = is_cython
        self.is_pylab = is_pylab
        self.is_sympy = is_sympy

        self.display_name = 'Python 2 (Spyder)' if PY2 else 'Python 3 (Spyder)'
        self.language = 'python2' if PY2 else 'python3'
        self.resource_dir = ''

    @property
    def argv(self):
        """Command to start kernels"""
        # Python interpreter used to start kernels
        if CONF.get('main_interpreter', 'default'):
            pyexec = get_python_executable()
        else:
            # Avoid IPython adding the virtualenv on which Spyder is running
            # to the kernel sys.path
            os.environ.pop('VIRTUAL_ENV', None)
            pyexec = CONF.get('main_interpreter', 'executable')
            if not is_python_interpreter(pyexec):
                pyexec = get_python_executable()
                CONF.set('main_interpreter', 'executable', '')
                CONF.set('main_interpreter', 'default', True)
                CONF.set('main_interpreter', 'custom', False)

        # Fixes Issue #3427
        if os.name == 'nt':
            dir_pyexec = osp.dirname(pyexec)
            pyexec_w = osp.join(dir_pyexec, 'pythonw.exe')
            if osp.isfile(pyexec_w):
                pyexec = pyexec_w

        # Command used to start kernels
        kernel_cmd = [
            pyexec,
            '-m',
            'spyder_kernels.console',
            '-f',
            '{connection_file}'
        ]

        return kernel_cmd

    @property
    def env(self):
        """Env vars for kernels"""
        # Add our PYTHONPATH to the kernel
        pathlist = CONF.get('main', 'spyder_pythonpath', default=[])

        default_interpreter = CONF.get('main_interpreter', 'default')
        pypath = add_pathlist_to_PYTHONPATH([], pathlist, ipyconsole=True,
                                            drop_env=False)

        # Environment variables that we need to pass to our sitecustomize
        umr_namelist = CONF.get('main_interpreter', 'umr/namelist')

        if PY2:
            original_list = umr_namelist[:]
            for umr_n in umr_namelist:
                try:
                    umr_n.encode('utf-8')
                except UnicodeDecodeError:
                    umr_namelist.remove(umr_n)
            if original_list != umr_namelist:
                CONF.set('main_interpreter', 'umr/namelist', umr_namelist)

        env_vars = {
            'SPY_EXTERNAL_INTERPRETER': not default_interpreter,
            'SPY_UMR_ENABLED': CONF.get('main_interpreter', 'umr/enabled'),
            'SPY_UMR_VERBOSE': CONF.get('main_interpreter', 'umr/verbose'),
            'SPY_UMR_NAMELIST': ','.join(umr_namelist),
            'SPY_RUN_LINES_O': CONF.get('ipython_console', 'startup/run_lines'),
            'SPY_PYLAB_O': CONF.get('ipython_console', 'pylab'),
            'SPY_BACKEND_O': CONF.get('ipython_console', 'pylab/backend'),
            'SPY_AUTOLOAD_PYLAB_O': CONF.get('ipython_console',
                                             'pylab/autoload'),
            'SPY_FORMAT_O': CONF.get('ipython_console',
                                     'pylab/inline/figure_format'),
            'SPY_BBOX_INCHES_O': CONF.get('ipython_console',
                                          'pylab/inline/bbox_inches'),
            'SPY_RESOLUTION_O': CONF.get('ipython_console',
                                         'pylab/inline/resolution'),
            'SPY_WIDTH_O': CONF.get('ipython_console', 'pylab/inline/width'),
            'SPY_HEIGHT_O': CONF.get('ipython_console', 'pylab/inline/height'),
            'SPY_USE_FILE_O': CONF.get('ipython_console',
                                       'startup/use_run_file'),
            'SPY_RUN_FILE_O': CONF.get('ipython_console', 'startup/run_file'),
            'SPY_AUTOCALL_O': CONF.get('ipython_console', 'autocall'),
            'SPY_GREEDY_O': CONF.get('ipython_console', 'greedy_completer'),
            'SPY_JEDI_O': CONF.get('ipython_console', 'jedi_completer'),
            'SPY_SYMPY_O': CONF.get('ipython_console', 'symbolic_math'),
            'SPY_TESTING': running_under_pytest() or SAFE_MODE,
            'SPY_HIDE_CMD': CONF.get('ipython_console', 'hide_cmd_windows')
        }

        if self.is_pylab is True:
            env_vars['SPY_AUTOLOAD_PYLAB_O'] = True
            env_vars['SPY_SYMPY_O'] = False
            env_vars['SPY_RUN_CYTHON'] = False
        if self.is_sympy is True:
            env_vars['SPY_AUTOLOAD_PYLAB_O'] = False
            env_vars['SPY_SYMPY_O'] = True
            env_vars['SPY_RUN_CYTHON'] = False
        if self.is_cython is True:
            env_vars['SPY_AUTOLOAD_PYLAB_O'] = False
            env_vars['SPY_SYMPY_O'] = False
            env_vars['SPY_RUN_CYTHON'] = True

        # Add our PYTHONPATH to env_vars
        env_vars.update(pypath)

        # Making all env_vars strings
        for key,var in iteritems(env_vars):
            if PY2:
                # Try to convert vars first to utf-8.
                try:
                    unicode_var = to_text_string(var)
                except UnicodeDecodeError:
                    # If that fails, try to use the file system
                    # encoding because one of our vars is our
                    # PYTHONPATH, and that contains file system
                    # directories
                    try:
                        unicode_var = to_unicode_from_fs(var)
                    except:
                        # If that also fails, make the var empty
                        # to be able to start Spyder.
                        # See https://stackoverflow.com/q/44506900/438386
                        # for details.
                        unicode_var = ''
                env_vars[key] = to_binary_string(unicode_var,
                                                 encoding='utf-8')
            else:
                env_vars[key] = to_text_string(var)
        return env_vars
