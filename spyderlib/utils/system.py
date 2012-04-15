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
    from ctypes.wintypes import byref, Structure, DWORD
    class MemoryStatus(Structure):
        _fields_ = [('dwLength', DWORD), ('dwMemoryLoad', DWORD),
                    ('dwTotalPhys', DWORD), ('dwAvailPhys', DWORD),
                    ('dwTotalPageFile', DWORD), ('dwAvailPageFile', DWORD),
                    ('dwTotalVirtual', DWORD), ('dwAvailVirtual', DWORD),]
    memorystatus = MemoryStatus()
    windll.kernel32.GlobalMemoryStatus(byref(memorystatus))
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
