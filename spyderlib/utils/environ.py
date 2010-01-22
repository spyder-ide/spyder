# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Environment variable utilities
"""

from PyQt4.QtGui import QDialog, QMessageBox

import os

# Local imports
from spyderlib.widgets.dicteditor import DictEditor
from spyderlib.utils.qthelpers import translate

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

class EnvDialog(DictEditor):
    """Environment variables Dialog"""
    def __init__(self):
        super(EnvDialog, self).__init__(envdict2listdict( dict(os.environ) ),
                                        title="os.environ", width=600,
                                        icon='environ.png')
    def accept(self):
        """Reimplement Qt method"""
        os.environ = listdict2envdict( self.get_copy() )
        QDialog.accept(self)


try:
    #---- Windows platform
    from _winreg import (OpenKey, EnumValue, QueryInfoKey,
                         SetValueEx, QueryValueEx)
    from _winreg import HKEY_CURRENT_USER, KEY_SET_VALUE, REG_EXPAND_SZ

    def get_user_env():
        """Return HKCU (current user) environment variables"""
        reg = dict()
        key = OpenKey(HKEY_CURRENT_USER, "Environment")
        for index in range(0, QueryInfoKey(key)[1]):
            try:
                value = EnumValue(key, index)
                reg[value[0]] = value[1]
            except:
                break
        return envdict2listdict(reg)
    
    def set_user_env(reg):
        """Set HKCU (current user) environment variables"""
        reg = listdict2envdict(reg)
        types = dict()
        key = OpenKey(HKEY_CURRENT_USER, "Environment")
        for name in reg:
            try:
                _, types[name] = QueryValueEx(key, name)
            except WindowsError:
                types[name] = REG_EXPAND_SZ
        key = OpenKey(HKEY_CURRENT_USER, "Environment", 0, KEY_SET_VALUE)
        for name in reg:
            SetValueEx(key, name, 0, types[name], reg[name])
        try:
            from win32gui import SendMessageTimeout
            from win32con import (HWND_BROADCAST, WM_SETTINGCHANGE,
                                  SMTO_ABORTIFHUNG)
            SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                               "Environment", SMTO_ABORTIFHUNG, 5000)
        except ImportError:
            QMessageBox.warning(self,
                translate("WinUserEnvDialog", "Warning"),
                translate("WinUserEnvDialog",
                          "Module <b>pywin32 was not found</b>.<br>"
                          "Please restart this Windows <i>session</i> "
                          "(not the computer) for changes to take effect."))
            
    class WinUserEnvDialog(DictEditor):
        """Windows User Environment Variables Editor"""
        def __init__(self, parent=None):
            super(WinUserEnvDialog, self).__init__(get_user_env(),
               title="HKEY_CURRENT_USER\Environment", width=600)
            if parent is None:
                parent = self
            QMessageBox.warning(parent,
                translate("WinUserEnvDialog", "Warning"),
                translate("WinUserEnvDialog", "If you accept changes, "
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
            set_user_env( listdict2envdict(self.get_copy()) )
            QDialog.accept(self)

except ImportError:
    #---- Other platforms
    pass


def main():
    """Run Windows environment variable editor"""
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    dialog = WinUserEnvDialog()
    dialog.exec_()

if __name__ == "__main__":
    main()
