# -*- coding: utf-8 -*-

"""
1. Console error (re spyder-kernels version) emits signal that launches
    the widget.
2. Widget will request permission to install spyder-kernels in the environment.
3. If rejected, close widget.
4. If accepted, install spyder-kernels in the environment, displaying progress.
5. If install successful, restart console and close widget.
6. If install fails, refer to documentation.
"""

# Local imports
from spyder.utils.conda import find_conda, get_conda_channel
from spyder.utils.programs import run_shell_command
from spyder_kernels.utils.pythonenv import is_conda_env, get_conda_env_path


def install_spyder_kernels(pyexec, ver):
    """Install spyder-kernels"""

    if is_conda_env(pyexec=pyexec):
        conda = find_conda()
        env_path = get_conda_env_path(pyexec)
        channel, channel_url = get_conda_channel(pyexec, "python")
        cmdstr = " ".join([
            conda, "install",
            "--prefix", env_path,
            "-c", channel,
            "-c", "conda-forge/label/spyder_kernels_rc",
            "-c", "conda-forge/label/spyder_kernels_dev",
            "--override-channels",
            f"spyder-kernels={ver}"
        ])
    else:
        # Pip environment
        cmdstr = " ".join([
            pyexec, "-m", "pip", "install",
            f"spyder-kernels=={ver}"
        ])

    out, err = run_shell_command(cmdstr).communicate()
