# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Environment variable utilities
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtWidgets import QDialog, QMessageBox

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.plugins.variableexplorer.widgets.collectionseditor import (
        CollectionsEditor)


def envdict2listdict(envdict):
    """Dict --> Dict of lists"""
    sep = os.path.pathsep
    for key in envdict:
        if sep in envdict[key]:
            envdict[key] = [path.strip() for path in envdict[key].split(sep)]
    return envdict


def listdict2envdict(listdict):
    """Dict of lists --> Dict"""
    for key in listdict:
        if isinstance(listdict[key], list):
            listdict[key] = os.path.pathsep.join(listdict[key])
    return listdict


class RemoteEnvDialog(CollectionsEditor):
    """Remote process environment variables dialog."""

    def __init__(self, environ, parent=None):
        super(RemoteEnvDialog, self).__init__(parent)
        try:
            self.setup(
                envdict2listdict(environ),
                title=_("Environment variables"),
                width=700,
                readonly=True,
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


# For Windows only
try:
    from spyder.py3compat import winreg

    def get_user_env():
        """Return HKCU (current user) environment variables"""
        reg = dict()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        for index in range(0, winreg.QueryInfoKey(key)[1]):
            try:
                value = winreg.EnumValue(key, index)
                reg[value[0]] = value[1]
            except:
                break
        return envdict2listdict(reg)

    def set_user_env(reg, parent=None):
        """Set HKCU (current user) environment variables"""
        reg = listdict2envdict(reg)
        types = dict()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        for name in reg:
            try:
                _x, types[name] = winreg.QueryValueEx(key, name)
            except WindowsError:
                types[name] = winreg.REG_EXPAND_SZ
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                             winreg.KEY_SET_VALUE)
        for name in reg:
            winreg.SetValueEx(key, name, 0, types[name], reg[name])
        try:
            from win32gui import SendMessageTimeout
            from win32con import (HWND_BROADCAST, WM_SETTINGCHANGE,
                                  SMTO_ABORTIFHUNG)
            SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                               "Environment", SMTO_ABORTIFHUNG, 5000)
        except Exception:
            QMessageBox.warning(parent, _("Warning"),
                        _("Module <b>pywin32 was not found</b>.<br>"
                          "Please restart this Windows <i>session</i> "
                          "(not the computer) for changes to take effect."))

    class WinUserEnvDialog(CollectionsEditor):
        """Windows User Environment Variables Editor"""
        def __init__(self, parent=None):
            super(WinUserEnvDialog, self).__init__(parent)
            self.setup(get_user_env(),
                       title="HKEY_CURRENT_USER\Environment", width=600)
            if parent is None:
                parent = self
            QMessageBox.warning(parent, _("Warning"),
                        _("If you accept changes, "
                          "this will modify the current user environment "
                          "variables directly <b>in Windows registry</b>. "
                          "Use it with precautions, at your own risks.<br>"
                          "<br>Note that for changes to take effect, you will "
                          "need to restart the parent process of this applica"
                          "tion (simply restart Spyder if you have executed it "
                          "from a Windows shortcut, otherwise restart any "
                          "application from which you may have executed it, "
                          "like <i>Python(x,y) Home</i> for example)"))

        def accept(self):
            """Reimplement Qt method"""
            set_user_env(listdict2envdict(self.get_value()), parent=self)
            QDialog.accept(self)

except Exception:
    pass

def main():
    """Run Windows environment variable editor"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    if os.name == 'nt':
        dialog = WinUserEnvDialog()
    else:
        dialog = EnvDialog()
    dialog.show()
    app.exec_()

if __name__ == "__main__":
    main()
