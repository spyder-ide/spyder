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

IS_WIN = os.name == 'nt'
IS_MAC = __SYSTEM.startswith('darwin')
IS_LINUX = __SYSTEM.startswith('linux')
IS_POSIX = not IS_WIN

# Ubuntu
IS_UBUNTU = False
if IS_LINUX and osp.isfile('/etc/lsb-release'):
    release_info = open('/etc/lsb-release').read()
    if 'Ubuntu' in release_info:
        IS_UBUNTU = True


def is_win():
    """ """
    return os.name == 'nt'


def is_mac():
    """ """
    return __SYSTEM.startswith('darwin')


def is_linux():
    """ """
    return __SYSTEM.startswith('linux')


def is_posix():
    """ """
    return not is_win()


def is_ubuntu():
    """ """
    if is_linux() and osp.isfile('/etc/lsb-release'):
        release_info = open('/etc/lsb-release').read()
        if 'Ubuntu' in release_info:
            return True
        else:
            return False
    else:
        return False


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
