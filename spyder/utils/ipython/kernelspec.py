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

from spyder.config.base import get_module_source_path
from spyder.config.main import CONF
from spyder.py3compat import PY2, iteritems, to_text_string, to_binary_string
from spyder.utils.misc import (add_pathlist_to_PYTHONPATH,
                               get_python_executable)


class SpyderKernelSpec(KernelSpec):

    default_interpreter = CONF.get('main_interpreter', 'default')
    spy_path = get_module_source_path('spyder')

    def __init__(self, **kwargs):
        super(SpyderKernelSpec, self).__init__(**kwargs)
        self.display_name = 'Spyder'
        self.language = 'python2' if PY2 else 'python3'
        self.resource_dir = ''

    @property
    def argv(self):
        """Command to start our kernels"""
        # Python interpreter used to start kernels
        if self.default_interpreter:
            pyexec = get_python_executable()
        else:
            # Avoid IPython adding the virtualenv on which Spyder is running
            # to the kernel sys.path
            os.environ.pop('VIRTUAL_ENV', None)
            pyexec = CONF.get('main_interpreter', 'executable')

        # Fixes Issue #3427
        if os.name == 'nt':
            dir_pyexec = osp.dirname(pyexec)
            pyexec_w = osp.join(dir_pyexec, 'pythonw.exe')
            if osp.isfile(pyexec_w):
                pyexec = pyexec_w

        # Command used to start kernels
        utils_path = osp.join(self.spy_path, 'utils', 'ipython')
        kernel_cmd = [
            pyexec,
            osp.join("%s" % utils_path, "start_kernel.py"),
            '-f',
            '{connection_file}'
        ]

        return kernel_cmd

    @property
    def env(self):
        """Env vars for our kernels"""
        # Paths that we need to add to PYTHONPATH:
        # 1. sc_path: Path to our sitecustomize
        # 2. spy_path: Path to our main module, so we can use our config
        #    system to configure kernels started by exterrnal interpreters
        # 3. spy_pythonpath: Paths saved by our users with our PYTHONPATH
        #    manager
        sc_path = osp.join(self.spy_path, 'utils', 'site')
        spy_pythonpath = CONF.get('main', 'spyder_pythonpath', default=[])

        default_interpreter = CONF.get('main_interpreter', 'default')
        if default_interpreter:
            pathlist = [sc_path] + spy_pythonpath
        else:
            pathlist = [sc_path, self.spy_path] + spy_pythonpath
        pypath = add_pathlist_to_PYTHONPATH([], pathlist, ipyconsole=True,
                                            drop_env=(not default_interpreter))

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
            'IPYTHON_KERNEL': 'True',
            'EXTERNAL_INTERPRETER': not default_interpreter,
            'UMR_ENABLED': CONF.get('main_interpreter', 'umr/enabled'),
            'UMR_VERBOSE': CONF.get('main_interpreter', 'umr/verbose'),
            'UMR_NAMELIST': ','.join(umr_namelist)
        }

        # Add our PYTHONPATH to env_vars
        env_vars.update(pypath)

        # Making all env_vars strings
        for k,v in iteritems(env_vars):
            if PY2:
                uv = to_text_string(v)
                env_vars[k] = to_binary_string(uv, encoding='utf-8')
            else:
                env_vars[k] = to_text_string(v)

        return env_vars
