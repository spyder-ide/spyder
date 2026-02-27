# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Windows-specific utilities"""

# Standard library imports
from ctypes import windll
import os.path as osp
import sys

# Third-party imports
from packaging.version import parse

# Local imports
from spyder import __version__

# --- Window control ---

SW_SHOW = 5    # activate and display
SW_SHOWNA = 8  # show without activation
SW_HIDE = 0

GetConsoleWindow = windll.kernel32.GetConsoleWindow
ShowWindow = windll.user32.ShowWindow
IsWindowVisible = windll.user32.IsWindowVisible

# Handle to console window associated with current Python
# interpreter procss, 0 if there is no window
console_window_handle = GetConsoleWindow()

def set_attached_console_visible(state):
    """Show/hide system console window attached to current process.
       Return it's previous state.

       Availability: Windows"""
    flag = {True: SW_SHOW, False: SW_HIDE}
    return bool(ShowWindow(console_window_handle, flag[state]))

def is_attached_console_visible():
    """Return True if attached console window is visible"""
    return IsWindowVisible(console_window_handle)

def set_windows_appusermodelid():
    """
    Make sure the correct icon is used on Windows taskbar by setting the
    AppUserModelID identical to that used by our menuinst shortcuts.
    """
    spy_ver = parse(__version__)
    env_name = osp.basename(osp.dirname(sys.executable))
    app_user_model_id = f"spyder-ide.Spyder-{spy_ver.major}.{env_name}"

    try:
        return windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_user_model_id
        )
    except AttributeError:
        return "SetCurrentProcessExplicitAppUserModelID not found"


# [ ] the console state asks for a storage container
# [ ] reopen console on exit - better die open than become a zombie
