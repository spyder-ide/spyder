# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Operating-system-specific utilities.
"""

# Standard library imports
import os

# Third-party imports
import psutil


def windows_memory_usage():
    """
    Return physical memory usage (float).

    It works on Windows platforms only and without psutil.
    """
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
    # MSDN documentation states that dwLength must be set to MemoryStatus
    # size before calling GlobalMemoryStatusEx
    # https://msdn.microsoft.com/en-us/library/aa366770(v=vs.85)
    memorystatus.dwLength = sizeof(memorystatus)
    windll.kernel32.GlobalMemoryStatusEx(byref(memorystatus))
    return float(memorystatus.dwMemoryLoad)


def memory_usage():
    """Return physical memory usage (float)."""
    # This is needed to avoid a deprecation warning error with
    # newer psutil versions
    try:
        percent = psutil.virtual_memory().percent
    except:
        percent = psutil.phymem_usage().percent
    return percent


if __name__ == '__main__':
    print("*"*80)  # spyder: test-skip
    print(memory_usage.__doc__)  # spyder: test-skip
    print(memory_usage())  # spyder: test-skip
    if os.name == 'nt':
        #  windll can only be imported if os.name = 'nt' or 'ce'
        print("*"*80)  # spyder: test-skip
        print(windows_memory_usage.__doc__)  # spyder: test-skip
        print(windows_memory_usage())  # spyder: test-skip
