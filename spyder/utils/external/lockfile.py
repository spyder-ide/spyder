# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2005 Divmod, Inc.
# Copyright (c) 2008-2011 Twisted Matrix Laboratories
# Copyright (c) 2012- Spyder Project Contributors
#
# Distributed under the terms of the MIT (Expat) License
# (see LICENSE.txt in this directory and NOTICE.txt in the root for details)
# -----------------------------------------------------------------------------

"""
Filesystem-based interprocess mutex.

Taken from the Twisted project.
Distributed under the MIT (Expat) license.

Changes by the Spyder Team to the original module:
  * Rewrite kill Windows function to make it more reliable.
  * Detect if the process that owns the lock is an Spyder one.

Adapted from src/twisted/python/lockfile.py of the
`Twisted project <https://github.com/twisted/twisted>`_.
"""

__metaclass__ = type

import errno, os
from time import time as _uniquefloat

from spyder.py3compat import PY2, to_binary_string
from spyder.utils.programs import is_spyder_process

def unique():
    if PY2:
        return str(long(_uniquefloat() * 1000))
    else:
        return str(int(_uniquefloat() * 1000))

from os import rename
if not os.name == 'nt':
    from os import kill
    from os import symlink
    from os import readlink
    from os import remove as rmlink
    _windows = False
else:
    _windows = True

    import ctypes
    from ctypes import wintypes

    # https://docs.microsoft.com/en-us/windows/desktop/ProcThread/process-security-and-access-rights
    PROCESS_QUERY_INFORMATION = 0x400

    # GetExitCodeProcess uses a special exit code to indicate that the
    # process is still running.
    STILL_ACTIVE = 259

    def _is_pid_running(pid):
        """Taken from https://www.madebuild.org/blog/?p=30"""
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, 0, pid)
        if handle == 0:
            return False

        # If the process exited recently, a pid may still exist for the
        # handle. So, check if we can get the exit code.
        exit_code = wintypes.DWORD()
        retval = kernel32.GetExitCodeProcess(handle,
                                             ctypes.byref(exit_code))
        is_running = (retval == 0)
        kernel32.CloseHandle(handle)

        # See if we couldn't get the exit code or the exit code indicates
        # that the process is still running.
        return is_running or exit_code.value == STILL_ACTIVE

    def kill(pid, signal):                    # analysis:ignore
        if not _is_pid_running(pid):
            raise OSError(errno.ESRCH, None)
        else:
            return

    _open = open

    # XXX Implement an atomic thingamajig for win32
    def symlink(value, filename):    #analysis:ignore
        newlinkname = filename+"."+unique()+'.newlink'
        newvalname = os.path.join(newlinkname, "symlink")
        os.mkdir(newlinkname)
        f = _open(newvalname, 'wb')
        f.write(to_binary_string(value))
        f.flush()
        f.close()
        try:
            rename(newlinkname, filename)
        except:
            # This is needed to avoid an error when we don't
            # have permissions to write in ~/.spyder
            # See issues 6319 and 9093
            try:
                os.remove(newvalname)
                os.rmdir(newlinkname)
            except (IOError, OSError):
                return
            raise

    def readlink(filename):   #analysis:ignore
        try:
            fObj = _open(os.path.join(filename, 'symlink'), 'rb')
        except IOError as e:
            if e.errno == errno.ENOENT or e.errno == errno.EIO:
                raise OSError(e.errno, None)
            raise
        else:
            result = fObj.read().decode()
            fObj.close()
            return result

    def rmlink(filename):    #analysis:ignore
        os.remove(os.path.join(filename, 'symlink'))
        os.rmdir(filename)



class FilesystemLock:
    """
    A mutex.

    This relies on the filesystem property that creating
    a symlink is an atomic operation and that it will
    fail if the symlink already exists.  Deleting the
    symlink will release the lock.

    @ivar name: The name of the file associated with this lock.

    @ivar clean: Indicates whether this lock was released cleanly by its
        last owner.  Only meaningful after C{lock} has been called and
        returns True.

    @ivar locked: Indicates whether the lock is currently held by this
        object.
    """

    clean = None
    locked = False

    def __init__(self, name):
        self.name = name

    def lock(self):
        """
        Acquire this lock.

        @rtype: C{bool}
        @return: True if the lock is acquired, false otherwise.

        @raise: Any exception os.symlink() may raise, other than
        EEXIST.
        """
        clean = True
        while True:
            try:
                symlink(str(os.getpid()), self.name)
            except OSError as e:
                if _windows and e.errno in (errno.EACCES, errno.EIO):
                    # The lock is in the middle of being deleted because we're
                    # on Windows where lock removal isn't atomic.  Give up, we
                    # don't know how long this is going to take.
                    return False
                if e.errno == errno.EEXIST:
                    try:
                        pid = readlink(self.name)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            # The lock has vanished, try to claim it in the
                            # next iteration through the loop.
                            continue
                        raise
                    except IOError as e:
                        if _windows and e.errno == errno.EACCES:
                            # The lock is in the middle of being
                            # deleted because we're on Windows where
                            # lock removal isn't atomic.  Give up, we
                            # don't know how long this is going to
                            # take.
                            return False
                        raise
                    try:
                        if kill is not None:
                            kill(int(pid), 0)
                        if not is_spyder_process(int(pid)):
                            raise(OSError(errno.ESRCH, 'No such process'))
                    except OSError as e:
                        if e.errno == errno.ESRCH:
                            # The owner has vanished, try to claim it in the
                            # next iteration through the loop.
                            try:
                                rmlink(self.name)
                            except OSError as e:
                                if e.errno == errno.ENOENT:
                                    # Another process cleaned up the lock.
                                    # Race them to acquire it in the next
                                    # iteration through the loop.
                                    continue
                                raise
                            clean = False
                            continue
                        raise
                    return False
                raise
            self.locked = True
            self.clean = clean
            return True

    def unlock(self):
        """
        Release this lock.

        This deletes the directory with the given name.

        @raise: Any exception os.readlink() may raise, or
        ValueError if the lock is not owned by this process.
        """
        pid = readlink(self.name)
        if int(pid) != os.getpid():
            raise ValueError("Lock %r not owned by this process" % (self.name,))
        rmlink(self.name)
        self.locked = False


def isLocked(name):
    """Determine if the lock of the given name is held or not.

    @type name: C{str}
    @param name: The filesystem path to the lock to test

    @rtype: C{bool}
    @return: True if the lock is held, False otherwise.
    """
    l = FilesystemLock(name)
    result = None
    try:
        result = l.lock()
    finally:
        if result:
            l.unlock()
    return not result


__all__ = ['FilesystemLock', 'isLocked']
