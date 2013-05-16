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
    from ctypes import windll, wintypes
    class MemoryStatus(wintypes.Structure):
        _fields_ = [('dwLength', wintypes.DWORD),
                    ('dwMemoryLoad', wintypes.DWORD),
                    ('ullTotalPhys', wintypes.c_uint64),
                    ('ullAvailPhys', wintypes.c_uint64),
                    ('ullTotalPageFile', wintypes.c_uint64),
                    ('ullAvailPageFile', wintypes.c_uint64),
                    ('ullTotalVirtual', wintypes.c_uint64),
                    ('ullAvailVirtual', wintypes.c_uint64),
                    ('ullAvailExtendedVirtual', wintypes.c_uint64),]
    memorystatus = MemoryStatus()
    # MSDN documetation states that dwLength must be set to MemoryStatus
    # size before calling GlobalMemoryStatusEx
    # http://msdn.microsoft.com/en-us/library/aa366770(v=vs.85)
    memorystatus.dwLength = wintypes.sizeof(memorystatus)
    windll.kernel32.GlobalMemoryStatusEx(wintypes.byref(memorystatus))
    return float(memorystatus.dwMemoryLoad)

def psutil_phymem_usage():
    """Return physical memory usage (float)
    Requires the cross-platform psutil (>=v0.3) library
    (http://code.google.com/p/psutil/)"""
    import psutil
    return psutil.phymem_usage().percent

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
    print("*"*80)
    print(windows_memory_usage.__doc__)
    print(windows_memory_usage())
