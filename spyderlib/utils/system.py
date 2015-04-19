# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Operating system utilities"""


import os
import os.path as osp
import platform

# Local imports
from spyderlib.utils import programs


__SYSTEM = platform.system.lower()
__IS_WIN = os.name == 'nt'
__IS_MAC = __SYSTEM.startswith('darwin')
__IS_LINUX = __SYSTEM.startswith('linux')
__IS_POSIX = not __IS_WIN
__IS_UBUNTU = False
if __IS_LINUX and osp.isfile('/etc/lsb-release'):
    release_info = open('/etc/lsb-release').read()
    if 'Ubuntu' in release_info:
        __IS_UBUNTU = True


def is_win():
    """ """
    return __IS_WIN


def is_mac():
    """ """
    return __IS_MAC


def is_linux():
    """ """
    return __IS_LINUX


def is_posix():
    """ """
    return __IS_POSIX


def is_ubuntu():
    """ """
    return __IS_UBUNTU


def windows_memory_usage():
    """Return physical memory usage (float)
    Works on Windows platforms only"""
    from ctypes import windll, Structure, c_uint64, sizeof, byref
    from ctypes.wintypes import DWORD

    class MemoryStatus(Structure):
        _fields_ = [('dwLength', DWORD),
                    ('dwMemoryLoad', DWORD),
                    ('ullTotalPhys', c_uint64),
                    ('ullAvailPhys', c_uint64),
                    ('ullTotalPageFile', c_uint64),
                    ('ullAvailPageFile', c_uint64),
                    ('ullTotalVirtual', c_uint64),
                    ('ullAvailVirtual', c_uint64),
                    ('ullAvailExtendedVirtual', c_uint64)]
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
elif is_win():
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
