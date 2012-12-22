# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Windows-specific utilities"""

set_attached_console_visible = None
is_attached_console_visible = None

try:
    import win32gui, win32console, win32con
    win32console.GetConsoleWindow() # do nothing, this is just a test
    def set_attached_console_visible(state):
        """Show/hide console window attached to current window
        
        This is for Windows platforms only. Requires pywin32 library."""
        win32gui.ShowWindow(win32console.GetConsoleWindow(),
                            win32con.SW_SHOW if state else win32con.SW_HIDE)
    def is_attached_console_visible():
        """Return True if attached console window is visible"""
        return win32gui.IsWindowVisible(win32console.GetConsoleWindow())
except (ImportError, NotImplementedError):
    # This is not a Windows platform (ImportError)
    # or pywin32 is not installed (ImportError)
    # or GetConsoleWindow is not implemented on current platform
    pass

