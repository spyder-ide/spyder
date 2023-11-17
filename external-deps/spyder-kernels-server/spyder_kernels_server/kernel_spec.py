# -*- coding: utf-8 -*-
import sys

from jupyter_client.kernelspec import KernelSpec

from .conda_utils import (
    is_conda_env, get_conda_env_path, find_conda, is_different_interpreter
)


def get_python_executable():
    """Return path to Spyder Python executable"""
    executable = sys.executable.replace("pythonw.exe", "python.exe")
    if executable.endswith("spyder.exe"):
        # py2exe distribution
        executable = "python.exe"
    return executable


def get_kernel_spec(kernel_spec_dict):

    kernel_spec = KernelSpec()
    for key in kernel_spec_dict:
        setattr(kernel_spec, key, kernel_spec_dict[key])

    # Python interpreter used to start kernels
    if (kernel_spec.pyexec is None):
        pyexec = get_python_executable()
    else:
        pyexec = kernel_spec.pyexec

    # Command used to start kernels
    kernel_cmd = [
        pyexec,
        # This is necessary to avoid a spurious message on Windows.
        # Fixes spyder-ide/spyder#20800.
        '-Xfrozen_modules=off',
        '-m', 'spyder_kernels.console',
        '-f', '{connection_file}'
    ]

    # Part of spyder-ide/spyder#11819
    is_different = is_different_interpreter(pyexec)
    if is_different and is_conda_env(pyexec=pyexec):
        # If executable is a conda environment and different from Spyder's
        # runtime environment, we need to activate the environment to run
        # spyder-kernels
        kernel_cmd[:0] = [
            find_conda(), 'run',
            '-p', get_conda_env_path(pyexec),
        ]
    kernel_spec.argv = kernel_cmd

    return kernel_spec
