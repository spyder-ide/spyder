# Copyright (c) 2005 Divmod, Inc.
# Copyright (c) Twisted Matrix Laboratories.
# Twisted is distributed under the MIT license.

"""
Filesystem-based interprocess mutex.
"""

__metaclass__ = type

import errno, os

from time import time as _uniquefloat

def unique():
    return str(long(_uniquefloat() * 1000))

from os import rename
if not os.name == 'nt':
    from os import kill
    from os import symlink
    from os import readlink
    from os import remove as rmlink
    _windows = False
else:
    _windows = True

    try:
        from win32api import OpenProcess
        import pywintypes
    except ImportError:
        kill = None   #analysis:ignore
    else:
        ERROR_ACCESS_DENIED = 5
        ERROR_INVALID_PARAMETER = 87

        def kill(pid, signal):
            try:
                OpenProcess(0, 0, pid)
            except pywintypes.error, e:
                if e.args[0] == ERROR_ACCESS_DENIED:
                    return
                elif e.args[0] == ERROR_INVALID_PARAMETER:
                    raise OSError(errno.ESRCH, None)
                raise
            else:
                raise RuntimeError("OpenProcess is required to fail.")

    _open = file

    # XXX Implement an atomic thingamajig for win32
    def symlink(value, filename):    #analysis:ignore
        newlinkname = filename+"."+unique()+'.newlink'
        newvalname = os.path.join(newlinkname,"symlink")
        os.mkdir(newlinkname)
        f = _open(newvalname,'wcb')
        f.write(value)
        f.flush()
        f.close()
        try:
            rename(newlinkname, filename)
        except:
            os.remove(newvalname)
            os.rmdir(newlinkname)
            raise

    def readlink(filename):   #analysis:ignore
        try:
            fObj = _open(os.path.join(filename,'symlink'), 'rb')
        except IOError, e:
            if e.errno == errno.ENOENT or e.errno == errno.EIO:
                raise OSError(e.errno, None)
            raise
        else:
            result = fObj.read()
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
            except OSError, e:
                if _windows and e.errno in (errno.EACCES, errno.EIO):
                    # The lock is in the middle of being deleted because we're
                    # on Windows where lock removal isn't atomic.  Give up, we
                    # don't know how long this is going to take.
                    return False
                if e.errno == errno.EEXIST:
                    try:
                        pid = readlink(self.name)
                    except OSError, e:
                        if e.errno == errno.ENOENT:
                            # The lock has vanished, try to claim it in the
                            # next iteration through the loop.
                            continue
                        raise
                    except IOError, e:
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
                    except OSError, e:
                        if e.errno == errno.ESRCH:
                            # The owner has vanished, try to claim it in the next
                            # iteration through the loop.
                            try:
                                rmlink(self.name)
                            except OSError, e:
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

