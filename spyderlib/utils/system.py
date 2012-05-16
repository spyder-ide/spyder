# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Operating system utilities"""

import os

def windows_memory_usage():
    """Return physical memory usage (float)
    Works on Windows platforms only"""
    from ctypes import windll
    from ctypes.wintypes import byref, Structure, DWORD, c_uint64, sizeof
    class MemoryStatus(Structure):
        _fields_ = [('dwLength', DWORD), ('dwMemoryLoad', DWORD),
                    ('ullTotalPhys', c_uint64), ('ullAvailPhys', c_uint64),
                    ('ullTotalPageFile', c_uint64), ('ullAvailPageFile', c_uint64),
                    ('ullTotalVirtual', c_uint64), ('ullAvailVirtual', c_uint64),
                    ('ullAvailExtendedVirtual', c_uint64),]
    memorystatus = MemoryStatus()
    # MSDN documetation states that dwLength must be set to MemoryStatus
    # size before calling GlobalMemoryStatusEx
    # http://msdn.microsoft.com/en-us/library/aa366770(v=vs.85)
    memorystatus.dwLength = sizeof(memorystatus)
    windll.kernel32.GlobalMemoryStatusEx(byref(memorystatus))
    return float(memorystatus.dwMemoryLoad)

def psutil_phymem_usage():
    """Return physical memory usage (float)
    Requires the cross-platform psutil library
    (http://code.google.com/p/psutil/)"""
    return psutil.phymem_usage().percent

try:
    import psutil
    memory_usage = psutil_phymem_usage
except ImportError:
    if os.name == 'nt':
        # Backup plan for Windows platforms
        memory_usage = windows_memory_usage
    else:
        raise

if __name__ == '__main__':
    print "*"*80
    print memory_usage.__doc__
    print memory_usage()
    print "*"*80
    print windows_memory_usage.__doc__
    print windows_memory_usage()
