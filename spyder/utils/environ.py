# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Environment variable utilities.
"""

# Standard library imports
from functools import lru_cache
import logging
import os
from pathlib import Path
import re
import sys
from textwrap import dedent

try:
    import winreg
except Exception:
    pass

# Third party imports
import psutil
from qtpy.QtWidgets import QMessageBox
from requests.structures import CaseInsensitiveDict

# Local imports
from spyder.config.base import _, running_in_ci, get_conf_path
from spyder.widgets.collectionseditor import CollectionsEditor
from spyder.utils.icon_manager import ima
from spyder.utils.programs import run_shell_command

logger = logging.getLogger(__name__)


@lru_cache
def _get_user_env_script():
    """
    To get user environment variables from login and interactive startup files
    on posix, both -l and -i flags must be used. Parsing the environment list
    is problematic if the variable has a newline character, but Python's
    os.environ can do this for us. However, executing Python in an interactive
    shell in a subprocess causes Spyder to hang on Linux. Using a shell script
    resolves the issue. Note that -i must be in the sha-bang line; if -i and
    -l are swapped, Spyder will hang.
    """
    script_text = None
    shell = os.getenv('SHELL', '/bin/bash')
    user_env_script = Path(get_conf_path()) / 'user-env.sh'

    if Path(shell).name in ('bash', 'zsh'):
        script_text = dedent(
            f"""\
            #!{shell} -i
            unset HISTFILE
            {shell} -l -c "'{sys.executable}' -c 'import os; print(dict(os.environ))'"
            """
        )
    else:
        logger.info("Getting user environment variables is not supported "
                    "for shell '%s'", shell)

    if script_text is not None:
        user_env_script.write_text(script_text)
        user_env_script.chmod(0o744)  # Make it executable for the user

    return str(user_env_script)


def envdict2listdict(envdict):
    """Dict --> Dict of lists"""
    sep = os.path.pathsep
    for key, val in envdict.items():
        if isinstance(val, str) and sep in val:
            envdict[key] = [path.strip() for path in val.split(sep)]
    return envdict


def listdict2envdict(listdict):
    """Dict of lists --> Dict"""
    for key, val in listdict.items():
        if isinstance(val, list):
            listdict[key] = os.path.pathsep.join(val)
    return listdict


def get_windows_env_variables(hkcu: bool = True) -> CaseInsensitiveDict:
    """
    Get environment variables from Windows registry

    Parameters
    ----------
    hkcu : bool (True)
        Get environment variables from HKEY_CURRENT_USER (True) or from
        HKEY_LOCAL_MACHINE (False).

    Returns
    -------
    env_vars : CaseInsensitiveDict[str, str]
        Environment variables
    """
    hkey = winreg.HKEY_LOCAL_MACHINE
    subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    if hkcu:
        hkey = winreg.HKEY_CURRENT_USER
        subkey = "Environment"

    key = winreg.OpenKey(hkey, subkey)
    num_values = winreg.QueryInfoKey(key)[1]

    return CaseInsensitiveDict(
        [winreg.EnumValue(key, k)[:2] for k in range(num_values)]
    )


def get_user_environment_variables() -> dict:
    """
    Get user environment variables from Windows registry or subprocess.

    Returns
    -------
    env_vars : dict
        Key-value pairs of environment variables.
    """
    env_vars = {}

    if os.name == 'nt':
        # System variables
        env_vars = get_windows_env_variables(hkcu=False)

        # User variables
        user_env_vars = get_windows_env_variables(hkcu=True)

        # Remove PATH and PYTHONPATH for special treatment
        path = user_env_vars.pop("PATH", None)
        pythonpath = user_env_vars.pop("PYTHONPATH", None)

        # Merge system and user variables, user takes precedent
        env_vars.update(user_env_vars)

        # Append user PATH to system PATH
        if path is not None:
            path = ";".join([
                env_vars.get("PATH", "").strip(";"), path.strip(";")
            ]).strip(";")
            env_vars.update({"PATH": path})

        # Append user PYTHONPATH to system PYTHONPATH
        if pythonpath is not None:
            pythonpath = ";".join([
                env_vars.pop("PYTHONPATH", "").strip(";"), pythonpath.strip(";")
            ]).strip(";")
            env_vars.update({"PYTHONPATH": pythonpath})

        env_vars = dict(env_vars)  # Remove CaseInsensitiveDict type

    elif os.name == 'posix':
        # Detect if the Spyder process was launched from a system terminal.
        # This is None if that was not the case.
        launched_from_terminal = psutil.Process(os.getpid()).terminal()

        # We only need to do this if Spyder was **not** launched from a
        # terminal. Otherwise, it'll inherit the env vars present in it.
        # Fixes spyder-ide/spyder#22415
        if not launched_from_terminal or running_in_ci():
            try:
                user_env_script = _get_user_env_script()
                proc = run_shell_command(user_env_script, env={}, text=True)

                # Use timeout to fix spyder-ide/spyder#21172
                stdout, stderr = proc.communicate(timeout=3)

                if stderr:
                    logger.info(stderr.strip())
                if stdout:
                    env_vars = eval(stdout, None)
            except Exception as exc:
                logger.info(exc)
        else:
            env_vars = dict(os.environ)

    return env_vars


def get_user_env() -> dict:
    """Return current user environment variables with parsed values"""
    env_dict = get_user_environment_variables()
    return envdict2listdict(env_dict)


def set_user_env(env: dict, parent=None):
    """
    Set user environment variables via HKCU (Windows) or shell startup file
    (Unix).
    """
    env_dict = clean_env(listdict2envdict(env))

    if os.name == 'nt':
        env_dict = CaseInsensitiveDict(env_dict)

        # First extract identical system variables from env_dict
        sys_env_dict = get_windows_env_variables(hkcu=False)
        for k, v in env_dict.copy().items():
            if v == sys_env_dict.get(k, None):
                env_dict.pop(k)  # Remove identical variable

        def _remove_sys_paths(name):
            # Extract system paths from env_dict[name]
            s_path = sys_env_dict.get(name, None)
            e_path = env_dict.get(name, None)
            if s_path is not None and e_path is not None:
                s_path = s_path.strip(";").split(";")
                e_path = e_path.strip(";").split(";")
                [e_path.remove(p) for p in s_path if p in e_path]
                e_path = ";".join(e_path)
                env_dict.update({name: e_path}) if e_path else None

        # Extract system [PYTHON]PATHs from user [PYTHON]PATHs
        _remove_sys_paths("PATH")
        _remove_sys_paths("PYTHONPATH")

        # Write to user variables
        types = dict()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        for name in env_dict:
            try:
                _x, types[name] = winreg.QueryValueEx(key, name)
            except WindowsError:
                types[name] = winreg.REG_EXPAND_SZ
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                             winreg.KEY_SET_VALUE)
        for name in env_dict:
            winreg.SetValueEx(key, name, 0, types[name], env_dict[name])
        try:
            from win32gui import SendMessageTimeout
            from win32con import (HWND_BROADCAST, WM_SETTINGCHANGE,
                                  SMTO_ABORTIFHUNG)
            SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                               "Environment", SMTO_ABORTIFHUNG, 5000)
        except Exception:
            QMessageBox.warning(
                parent, _("Warning"),
                _("Module <b>pywin32 was not found</b>.<br>"
                  "Please restart this Windows <i>session</i> "
                  "(not the computer) for changes to take effect.")
            )
    elif os.name == 'posix' and running_in_ci():
        text = "\n".join([f"export {k}={v}" for k, v in env_dict.items()])
        amend_user_shell_init(text)
    else:
        raise NotImplementedError("Not implemented for platform %s", os.name)


def amend_user_shell_init(text="", restore=False):
    """Set user environment variable for pytests on Unix platforms"""
    if os.name == "nt":
        return

    HOME = Path(os.environ["HOME"])
    SHELL = os.environ.get("SHELL", "/bin/bash")
    if "bash" in SHELL:
        init_files = [".bash_profile", ".bash_login", ".profile"]
    elif "zsh" in SHELL:
        init_files = [".zprofile", ".zshrc"]
    else:
        raise Exception(f"{SHELL} not supported.")

    for file in init_files:
        init_file = HOME / file
        if init_file.exists():
            break

    script = init_file.read_text() if init_file.exists() else ""
    m1 = "# <<<< Spyder Environment <<<<"
    m2 = "# >>>> Spyder Environment >>>>"
    if restore:
        if init_file.exists() and (m1 in script and m2 in script):
            new_text = ""
        else:
            return
    else:
        new_text = f"{m1}\n" + text + f"\n{m2}"

    if m1 in script and m2 in script:
        _script = re.sub(f"{m1}(.*){m2}", new_text, script, flags=re.DOTALL)
    else:
        _script = script.rstrip() + "\n\n" + new_text

    init_file.write_text(_script.rstrip() + "\n")


def clean_env(env_vars):
    """
    Remove non-ascii entries from a dictionary of environments variables.

    The values will be converted to strings or bytes (on Python 2). If an
    exception is raised, an empty string will be used.
    """
    new_env_vars = env_vars.copy()
    for key, var in env_vars.items():
        new_env_vars[key] = str(var)

    return new_env_vars


class RemoteEnvDialog(CollectionsEditor):
    """Remote process environment variables dialog."""

    def __init__(self, environ, parent=None,
                 title=_("Environment variables"), readonly=True):
        super().__init__(parent)
        try:
            self.setup(
                envdict2listdict(environ),
                title=title,
                readonly=readonly,
                icon=ima.icon('environ')
            )
        except Exception as e:
            QMessageBox.warning(
                parent,
                _("Warning"),
                _("An error occurred while trying to show your "
                  "environment variables. The error was<br><br>"
                  "<tt>{0}</tt>").format(e),
                QMessageBox.Ok
            )


class EnvDialog(RemoteEnvDialog):
    """Environment variables Dialog"""

    def __init__(self, parent=None):
        RemoteEnvDialog.__init__(self, dict(os.environ), parent=parent)


class UserEnvDialog(RemoteEnvDialog):
    """User Environment Variables Viewer/Editor"""

    def __init__(self, parent=None):
        title = _("User environment variables")
        readonly = True
        if os.name == 'nt':
            title = _(r"User environment variables in Windows registry")
            readonly = False

        super().__init__(get_user_env(), parent, title, readonly)

        if os.name == 'nt':
            if parent is None:
                parent = self
            QMessageBox.warning(
                parent, _("Warning"),
                _("If you accept changes, "
                  "this will modify the current user environment "
                  "variables directly <b>in Windows registry</b>. "
                  "Use it with precautions, at your own risks.<br>"
                  "<br>Note that for changes to take effect, you will "
                  "need to restart the parent process of this applica"
                  "tion (simply restart Spyder if you have executed it "
                  "from a Windows shortcut, otherwise restart any "
                  "application from which you may have executed it, "
                  "like <i>Python(x,y) Home</i> for example)")
            )

    def accept(self):
        """Reimplement Qt method"""
        if os.name == 'nt':
            set_user_env(listdict2envdict(self.get_value()), parent=self)
        super().accept()


def test():
    """Run Windows environment variable editor"""
    import sys
    from spyder.utils.qthelpers import qapplication
    _ = qapplication()
    dlg = UserEnvDialog()
    dlg.show()
    sys.exit(dlg.exec())


if __name__ == "__main__":
    test()
