# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Kernel spec for Spyder kernels
"""

# Standard library imports
import logging
import os
import os.path as osp
import sys

# Third party imports
from jupyter_client.kernelspec import KernelSpec

# Local imports
from spyder.config.base import DEV, running_under_pytest, SAFE_MODE
from spyder.config.manager import CONF
from spyder.py3compat import PY2
from spyder.utils.conda import (get_conda_activation_script,
                                get_conda_env_path, is_conda_env)
from spyder.utils.environ import clean_env
from spyder.utils.misc import add_pathlist_to_PYTHONPATH, get_python_executable
from spyder.utils.programs import is_python_interpreter

# Constants
logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))

scripts_folder_path = os.path.join(os.path.dirname(HERE), 'scripts')


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
            pyexec = CONF.get('main_interpreter', 'executable')
            if not is_python_interpreter(pyexec):
                pyexec = get_python_executable()
                CONF.set('main_interpreter', 'executable', '')
                CONF.set('main_interpreter', 'default', True)
                CONF.set('main_interpreter', 'custom', False)

        # Command used to start kernels
        # Use an intermediate script to correctly activate the spyder-kernel.
        # If changes are needed on this section make sure you also update
        # the activation scripts at spyder/plugins/ipythonconsole/scripts/
        suffix = '.bat' if os.name == 'nt' else '.sh'
        if is_conda_env(pyexec=pyexec):
            script_path = os.path.join(scripts_folder_path,
                                       'conda-activate' + suffix)
            kernel_cmd = [script_path,
                          get_conda_activation_script(pyexec),
                          get_conda_env_path(pyexec)]  # Might be external
        else:
            script_path = os.path.join(scripts_folder_path,
                                       'env-activate' + suffix)
            kernel_cmd = [script_path]
        kernel_cmd.extend([pyexec, '{connection_file}'])

        logger.info('Kernel command: {}'.format(kernel_cmd))

        return kernel_cmd

    @property
    def env(self):
        """Env vars for kernels"""
        default_interpreter = CONF.get('main_interpreter', 'default')
        pathlist = CONF.get('main', 'spyder_pythonpath', default=[])

        # Add spyder-kernels subrepo path to pathlist
        if DEV or running_under_pytest():
            repo_path = osp.normpath(osp.join(HERE, '..', '..', '..', '..'))
            subrepo_path = osp.join(repo_path, 'external-deps',
                                    'spyder-kernels')

            if running_under_pytest():
                # Oddly pathlist is not set as an empty list when running
                # under pytest
                pathlist = [subrepo_path]
            else:
                pathlist += [subrepo_path] + pathlist

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
            'SPY_RUN_LINES_O': CONF.get('ipython_console',
                                        'startup/run_lines'),
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

        # Each platform requires certain env variables
        if os.name == 'nt':
            req_env_vars = ['HOMEPATH', 'PATH', 'SYSTEMROOT']
        elif sys.platform == 'darwin':
            req_env_vars = ['HOME']
            # keep PYTHONHOME for "Same as Spyder"
            if default_interpreter:
                req_env_vars += ['PYTHONHOME']
        elif sys.platform == 'linux':
            # Linux requires DISPLAY
            req_env_vars = ['DISPLAY', 'HOME']
        else:
            logger.info('Unknown platform: {}'.format(sys.platform))
            req_env_vars = []
        env_vars.update({k: os.environ[k] for k in req_env_vars
                         if k in os.environ})

        # Add our PYTHONPATH to env_vars
        # spyder env python should be omitted in kernels
        pypath = add_pathlist_to_PYTHONPATH([], pathlist, ipyconsole=True,
                                            drop_env=True)
        env_vars.update(pypath)

        # Making all env_vars strings
        clean_env_vars = clean_env(env_vars)

        return clean_env_vars
