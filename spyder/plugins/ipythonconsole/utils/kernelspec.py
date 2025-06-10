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

# Third party imports
from jupyter_client.kernelspec import KernelSpec
from packaging.version import parse
from spyder_kernels.utils.pythonenv import (
    get_conda_env_path,
    get_pixi_manifest_path_and_env_name,
    is_conda_env,
    is_pixi_env,
)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _
from spyder.config.base import (get_safe_mode, is_conda_based_app,
                                running_under_pytest)
from spyder.plugins.ipythonconsole import (
    SPYDER_KERNELS_CONDA, SPYDER_KERNELS_PIP, SPYDER_KERNELS_VERSION,
    SpyderKernelError)
from spyder.utils.conda import conda_version, find_conda, find_pixi
from spyder.utils.environ import clean_env, get_user_environment_variables
from spyder.utils.misc import get_python_executable
from spyder.utils.programs import (
    get_module_version,
    get_temp_dir,
    is_python_interpreter,
    is_module_installed,
)

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)
ERROR_SPYDER_KERNEL_INSTALLED = _(
    "The Python environment or installation whose interpreter is located at"
    "<pre>"
    "    <tt>{0}</tt>"
    "</pre>"
    "doesn't have <tt>spyder-kernels</tt> version <tt>{1}</tt> installed. "
    "Without this module and specific version is not possible for Spyder to "
    "create a console for you.<br><br>"
    "You can install it by activating your environment (if necessary) and "
    "then running in a system terminal:"
    "<pre>"
    "    <tt>{2}</tt>"
    "</pre>"
    "or"
    "<pre>"
    "    <tt>{3}</tt>"
    "</pre>")


def has_spyder_kernels(pyexec):
    """Check if env has spyder kernels."""
    if is_module_installed(
        'spyder_kernels',
        version=SPYDER_KERNELS_VERSION,
        interpreter=pyexec
    ):
        return True

    # Dev versions of Spyder-kernels are acceptable
    try:
        return "dev0" in get_module_version('spyder_kernels', pyexec)
    except Exception:
        return False


HERE = osp.dirname(os.path.realpath(__file__))


class SpyderKernelSpec(KernelSpec, SpyderConfigurationAccessor):
    """Kernel spec for Spyder kernels"""

    CONF_SECTION = 'ipython_console'

    def __init__(self, path_to_custom_interpreter=None,
                 **kwargs):
        super(SpyderKernelSpec, self).__init__(**kwargs)
        self.path_to_custom_interpreter = path_to_custom_interpreter
        self.display_name = 'Python 3 (Spyder)'
        self.language = 'python3'
        self.resource_dir = ''

        self.env = get_user_environment_variables()

    @property
    def argv(self):
        """Command to start kernels"""
        # Python interpreter used to start kernels
        if (
            self.get_conf('default', section='main_interpreter')
            and not self.path_to_custom_interpreter
        ):
            pyexec = get_python_executable()
        else:
            pyexec = self.get_conf('executable', section='main_interpreter')
            if self.path_to_custom_interpreter:
                pyexec = self.path_to_custom_interpreter
            if not has_spyder_kernels(pyexec):
                raise SpyderKernelError(
                    ERROR_SPYDER_KERNEL_INSTALLED.format(
                        pyexec,
                        SPYDER_KERNELS_VERSION,
                        SPYDER_KERNELS_CONDA,
                        SPYDER_KERNELS_PIP
                    )
                )
                return
            if not is_python_interpreter(pyexec):
                pyexec = get_python_executable()
                self.set_conf('executable', '', section='main_interpreter')
                self.set_conf('default', True, section='main_interpreter')
                self.set_conf('custom', False, section='main_interpreter')

        # Command used to start kernels
        kernel_cmd = []

        if is_pixi_env(pyexec=pyexec):
            pixi_exe = find_pixi()

            if not pixi_exe:
                raise SpyderKernelError(
                    _(
                        "Spyder couldn't find pixi in your system to activate "
                        "the kernel's environment. Please add the directory "
                        "where the pixi executable is located to your PATH "
                        "environment variable for it to be detected."
                    )
                )
            pixi_manifest, pixi_env = get_pixi_manifest_path_and_env_name(
                pyexec,
            )
            kernel_cmd.extend([
                pixi_exe,
                'run',
                '--environment',
                pixi_env,
                '--manifest-path',
                pixi_manifest,
            ])

        elif is_conda_env(pyexec=pyexec):
            # If executable is a conda environment, use "run" subcommand to
            # activate it and run spyder-kernels.
            conda_exe = find_conda()

            if not conda_exe:
                # Raise error since we were unable to determine the path to
                # the conda executable (e.g when Anaconda/Miniconda was
                # installed in a non-standard location).
                # See spyder-ide/spyder#23595
                not_found_exe_message = _(
                    "Spyder couldn't find conda, mamba or micromamba in your "
                    "system to activate the kernel's environment. Please add "
                    "the directory where at least one of their executables "
                    "is located to your PATH environment variable for it to "
                    "be detected."
                )
                raise SpyderKernelError(not_found_exe_message)

            # Get conda/mamba/micromamba version to perform some checks
            conda_exe_version = conda_version(conda_executable=conda_exe)

            # Base command
            kernel_cmd.extend([
                conda_exe,
                'run',
                '--prefix',
                get_conda_env_path(pyexec)
            ])

            # We need to use these flags to prevent conda_exe from capturing
            # the kernel process stdout/stderr streams. That way we'll be able
            # to show them in Spyder.
            if "micromamba" in osp.basename(conda_exe) or (
                # Fixes spyder-ide/spyder#24513
                "mamba" in osp.basename(conda_exe)
                and conda_exe_version >= parse("2.0")
            ):
                kernel_cmd.extend(['--attach', '""'])
            elif (
                "mamba" in osp.basename(conda_exe)
                and conda_exe_version < parse("2.0")
            ) or (
                "conda" in osp.basename(conda_exe)
                and conda_exe_version >= parse("4.9")
            ):
                # Note: We use --no-capture-output instead of --live-stream
                # here because it works for older Conda versions (conda>=4.9).
                kernel_cmd.append('--no-capture-output')
            else:
                # Raise error since an unsupported conda version is being used
                # (conda<4.9).
                # See spyder-ide/spyder#22554
                raise SpyderKernelError(
                    _(
                        "The detected version of Conda is too old and not "
                        "supported by Spyder. The minimum supported version is "
                        "4.9 and currently you have {conda_version}.<br><br>."
                        "<b>Note</b>: You need to restart Spyder after "
                        "updating Conda for the change to take effect."
                    ).format(conda_version=conda_exe_version)
                )

        kernel_cmd.extend([
            pyexec,
            # This is necessary to avoid a spurious message on Windows.
            # Fixes spyder-ide/spyder#20800.
            '-Xfrozen_modules=off',
            '-m', 'spyder_kernels.console',
            '-f', '{connection_file}'
        ])

        logger.info('Kernel command: {}'.format(kernel_cmd))

        return kernel_cmd

    @property
    def env(self):
        """Env vars for kernels"""
        default_interpreter = self.get_conf(
            'default', section='main_interpreter')

        # Ensure that user environment variables are included, but don't
        # override existing environ values
        env_vars = self._env_vars.copy()
        env_vars.update(os.environ)

        # Avoid IPython adding the virtualenv on which Spyder is running
        # to the kernel sys.path
        env_vars.pop('VIRTUAL_ENV', None)

        # Do not pass PYTHONPATH to kernels directly, spyder-ide/spyder#13519
        env_vars.pop('PYTHONPATH', None)

        # List of modules to exclude from our UMR
        umr_namelist = self.get_conf(
            'umr/namelist', section='main_interpreter')

        # Get TMPDIR value, if available
        tmpdir_var = env_vars.get("TMPDIR", "")

        # Environment variables that we need to pass to the kernel
        env_vars.update({
            'SPY_EXTERNAL_INTERPRETER': (not default_interpreter
                                         or self.path_to_custom_interpreter),
            'SPY_UMR_ENABLED': self.get_conf(
                'umr/enabled', section='main_interpreter'),
            'SPY_UMR_VERBOSE': self.get_conf(
                'umr/verbose', section='main_interpreter'),
            'SPY_UMR_NAMELIST': ','.join(umr_namelist),
            'SPY_AUTOCALL_O': self.get_conf('autocall'),
            'SPY_GREEDY_O': self.get_conf('greedy_completer'),
            'SPY_JEDI_O': self.get_conf('jedi_completer'),
            'SPY_TESTING': running_under_pytest() or get_safe_mode(),
            'SPY_HIDE_CMD': self.get_conf('hide_cmd_windows'),
            # This env var avoids polluting the OS default temp directory with
            # files generated by `conda run`. It's restored/removed in the
            # kernel after initialization.
            "TMPDIR": get_temp_dir(),
            # This is necessary to restore TMPDIR in the kernel, if it exists
            "SPY_TMPDIR": tmpdir_var,
        })

        # App considerations
        # ??? Do we need this?
        if is_conda_based_app() and default_interpreter:
            # See spyder-ide/spyder#16927
            # See spyder-ide/spyder#16828
            # See spyder-ide/spyder#17552
            env_vars['PYDEVD_DISABLE_FILE_VALIDATION'] = 1

        # Remove this variable because it prevents starting kernels for
        # external interpreters when present.
        # Fixes spyder-ide/spyder#13252
        env_vars.pop('PYTHONEXECUTABLE', None)

        # Making all env_vars strings
        clean_env_vars = clean_env(env_vars)

        return clean_env_vars

    @env.setter
    def env(self, env_vars):
        self._env_vars = dict(env_vars)
        self._env_vars.pop('PYTEST_CURRENT_TEST', None)
