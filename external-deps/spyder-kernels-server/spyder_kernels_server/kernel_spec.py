# -*- coding: utf-8 -*-
import sys
import os
import os.path as osp
from jupyter_client.kernelspec import KernelSpec

WINDOWS = os.name == 'nt'
    
def get_python_executable():
    """Return path to Spyder Python executable"""
    executable = sys.executable.replace("pythonw.exe", "python.exe")
    if executable.endswith("spyder.exe"):
        # py2exe distribution
        executable = "python.exe"
    return executable


def is_different_interpreter(pyexec):
    """Check that pyexec is a different interpreter from sys.executable."""
    # Paths may be symlinks
    real_pyexe = osp.realpath(pyexec)
    real_sys_exe = osp.realpath(sys.executable)
    executable_validation = osp.basename(real_pyexe).startswith('python')
    directory_validation = osp.dirname(real_pyexe) != osp.dirname(real_sys_exe)
    return directory_validation and executable_validation


def add_quotes(path):
    """Return quotes if needed for spaces on path."""
    quotes = '"' if ' ' in path and '"' not in path else ''
    return '{quotes}{path}{quotes}'.format(quotes=quotes, path=path)


def get_conda_env_path(pyexec, quote=False):
    """
    Return the full path to the conda environment from give python executable.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    pyexec = pyexec.replace('\\', '/')
    if os.name == 'nt':
        conda_env = os.path.dirname(pyexec)
    else:
        conda_env = os.path.dirname(os.path.dirname(pyexec))

    if quote:
        conda_env = add_quotes(conda_env)

    return conda_env


def is_conda_env(prefix=None, pyexec=None):
    """Check if prefix or python executable are in a conda environment."""
    if pyexec is not None:
        pyexec = pyexec.replace('\\', '/')

    if (prefix is None and pyexec is None) or (prefix and pyexec):
        raise ValueError('Only `prefix` or `pyexec` should be provided!')

    if pyexec and prefix is None:
        prefix = get_conda_env_path(pyexec).replace('\\', '/')

    return os.path.exists(os.path.join(prefix, 'conda-meta'))


def get_kernel_spec(kernel_spec_dict):
    
    kernel_spec = KernelSpec()
    for key in kernel_spec_dict:
        setattr(kernel_spec, key, kernel_spec_dict[key])
   
    if kernel_spec.pyexec is None:
        kernel_spec.pyexec = get_python_executable()
    # Python interpreter used to start kernels
    if (
        kernel_spec.pyexec is None
    ):
        pyexec = get_python_executable()
    else:
        pyexec = kernel_spec.pyexec
        
       
    # Part of spyder-ide/spyder#11819
    is_different = is_different_interpreter(pyexec)

    # Command used to start kernels
    kernel_cmd = [
        pyexec,
        # This is necessary to avoid a spurious message on Windows.
        # Fixes spyder-ide/spyder#20800.
        '-Xfrozen_modules=off',
        '-m', 'spyder_kernels.console',
        '-f', '{connection_file}'
    ]

    if is_different and is_conda_env(pyexec=pyexec):
        # If executable is a conda environment and different from Spyder's
        # runtime environment, we need to activate the environment to run
        # spyder-kernels
        raise NotImplementedError("Sorry I can't find conda without importing spyder here :/, TODO")
        # kernel_cmd[:0] = [
        #     find_conda(), 'run',
        #     '-p', get_conda_env_path(pyexec),
        # ]
    kernel_spec.argv = kernel_cmd

    return kernel_spec