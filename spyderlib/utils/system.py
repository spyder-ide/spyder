# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Operating system utilities"""


import os

# Local imports
from spyderlib.utils import programs


def windows_memory_usage():
    """Return physical memory usage (float)
    Works on Windows platforms only"""
    from ctypes import windll, Structure, c_uint64, sizeof, byref
    from ctypes.wintypes import DWORD
    class MemoryStatus(Structure):
        _fields_ = [('dwLength', DWORD),
                    ('dwMemoryLoad',DWORD),
                    ('ullTotalPhys', c_uint64),
                    ('ullAvailPhys', c_uint64),
                    ('ullTotalPageFile', c_uint64),
                    ('ullAvailPageFile', c_uint64),
                    ('ullTotalVirtual', c_uint64),
                    ('ullAvailVirtual', c_uint64),
                    ('ullAvailExtendedVirtual', c_uint64),]
    memorystatus = MemoryStatus()
    # MSDN documetation states that dwLength must be set to MemoryStatus
    # size before calling GlobalMemoryStatusEx
    # http://msdn.microsoft.com/en-us/library/aa366770(v=vs.85)
    memorystatus.dwLength = sizeof(memorystatus)
    windll.kernel32.GlobalMemoryStatusEx(byref(memorystatus))
    return float(memorystatus.dwMemoryLoad)

def psutil_phymem_usage():
    """
    Return physical memory usage (float)
    Requires the cross-platform psutil (>=v0.3) library
    (http://code.google.com/p/psutil/)
    """
    import psutil
    # This is needed to avoid a deprecation warning error with
    # newer psutil versions
    try:
        percent = psutil.virtual_memory().percent
    except:
        percent = psutil.phymem_usage().percent
    return percent

if programs.is_module_installed('psutil', '>=0.3.0'):
    #  Function `psutil.phymem_usage` was introduced in psutil v0.3.0
    memory_usage = psutil_phymem_usage
elif os.name == 'nt':
    # Backup plan for Windows platforms
    memory_usage = windows_memory_usage
else:
    raise ImportError("Feature requires psutil 0.3+ on non Windows platforms")


if __name__ == '__main__':
    print("*"*80)
    print(memory_usage.__doc__)
    print(memory_usage())
    if os.name == 'nt':
        #  windll can only be imported if os.name = 'nt' or 'ce'
        print("*"*80)
        print(windows_memory_usage.__doc__)
        print(windows_memory_usage())