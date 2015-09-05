#
# Copyright (c) 2010 Mikhail Gusarov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
<<<<<<< HEAD
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
=======
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

<<<<<<< HEAD
""" path.py - An object representing a path to a file or directory.

Original author:
 Jason Orendorff <jason.orendorff\x40gmail\x2ecom>

Contributors:
 Mikhail Gusarov <dottedmag@dottedmag.net>
 Marc Abramowitz <marc@marc-abramowitz.com>

Example:

from path import path
d = path('/home/guido/bin')
for f in d.files('*.py'):
    f.chmod(0755)

This module requires Python 2.3 or later.
"""

from __future__ import generators

=======
"""
path.py - An object representing a path to a file or directory.

https://github.com/jaraco/path.py

Example::

    from path import Path
    d = Path('/home/guido/bin')
    for f in d.files('*.py'):
        f.chmod(0o755)
"""

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
import sys
import warnings
import os
import fnmatch
import glob
import shutil
import codecs
import hashlib
import errno
<<<<<<< HEAD

from spyderlib.py3compat import (TEXT_TYPES, getcwd, u,
                                 is_text_string, is_unicode)

__version__ = '2.4.1'
__all__ = ['path']

MODE_0777 = 511
MODE_0666 = 438

# Platform-specific support for path.owner
if os.name == 'nt':
    try:
        import win32security
    except ImportError:
        win32security = None
else:
    try:
        import pwd
    except ImportError:
        pwd = None

_base = TEXT_TYPES[-1]
_getcwd = getcwd

# Universal newline support
_textmode = 'U'
if hasattr(__builtins__, 'open') and not hasattr(open, 'newlines'):
    _textmode = 'r'
=======
import tempfile
import functools
import operator
import re
import contextlib
import io

try:
    import win32security
except ImportError:
    pass

try:
    import pwd
except ImportError:
    pass

try:
    import grp
except ImportError:
    pass

##############################################################################
# Python 2/3 support
PY3 = sys.version_info >= (3,)
PY2 = not PY3

string_types = str,
text_type = str
getcwdu = os.getcwd
u = lambda x: x

def surrogate_escape(error):
    """
    Simulate the Python 3 ``surrogateescape`` handler, but for Python 2 only.
    """
    chars = error.object[error.start:error.end]
    assert len(chars) == 1
    val = ord(chars)
    val += 0xdc00
    return __builtin__.unichr(val), error.end

if PY2:
    import __builtin__
    string_types = __builtin__.basestring,
    text_type = __builtin__.unicode
    getcwdu = os.getcwdu
    u = lambda x: codecs.unicode_escape_decode(x)[0]
    codecs.register_error('surrogateescape', surrogate_escape)

@contextlib.contextmanager
def io_error_compat():
    try:
        yield
    except IOError as io_err:
        # On Python 2, io.open raises IOError; transform to OSError for
        # future compatibility.
        os_err = OSError(*io_err.args)
        os_err.filename = getattr(io_err, 'filename', None)
        raise os_err

##############################################################################

__version__ = '7.3'
__all__ = ['Path', 'path', 'CaseInsensitivePattern']


LINESEPS = [u('\r\n'), u('\r'), u('\n')]
U_LINESEPS = LINESEPS + [u('\u0085'), u('\u2028'), u('\u2029')]
NEWLINE = re.compile('|'.join(LINESEPS))
U_NEWLINE = re.compile('|'.join(U_LINESEPS))
NL_END = re.compile(u(r'(?:{0})$').format(NEWLINE.pattern))
U_NL_END = re.compile(u(r'(?:{0})$').format(U_NEWLINE.pattern))

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

class TreeWalkWarning(Warning):
    pass

<<<<<<< HEAD
class path(_base):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in os.path.
    """

    # --- Special Python methods.

    def __repr__(self):
        return 'path(%s)' % _base.__repr__(self)

    # Adding a path and a string yields a path.
    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  # Python bug
            resultStr = NotImplemented
        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)

    def __radd__(self, other):
        if is_text_string(other):
            return self.__class__(other.__add__(self))
        else:
            return NotImplemented

    # The / operator joins paths.
=======

def simple_cache(func):
    """
    Save results for the :meth:'path.using_module' classmethod.
    When Python 3.2 is available, use functools.lru_cache instead.
    """
    saved_results = {}

    def wrapper(cls, module):
        if module in saved_results:
            return saved_results[module]
        saved_results[module] = func(cls, module)
        return saved_results[module]
    return wrapper


class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class multimethod(object):
    """
    Acts like a classmethod when invoked from the class and like an
    instancemethod when invoked from the instance.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return (
            functools.partial(self.func, owner) if instance is None
            else functools.partial(self.func, owner, instance)
        )


def alias(name):
    "Create a decorator which will make an alias of the decorated item"
    def decorate(item):
        globals()[name] = item
        return item
    return decorate


@alias('path')
class Path(text_type):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in :mod:`os.path`.
    """

    module = os.path
    """ The path module to use for path operations.

    .. seealso:: :mod:`os.path`
    """

    def __init__(self, other=''):
        if other is None:
            raise TypeError("Invalid initial value for path: None")

    @classmethod
    @simple_cache
    def using_module(cls, module):
        subclass_name = cls.__name__ + '_' + module.__name__
        bases = (cls,)
        ns = {'module': module}
        return type(subclass_name, bases, ns)

    @ClassProperty
    @classmethod
    def _next_class(cls):
        """
        What class should be used to construct new instances from this class
        """
        return cls

    @classmethod
    def _always_unicode(cls, path):
        """
        Ensure the path as retrieved from a Python API, such as :func:`os.listdir`,
        is a proper Unicode string.
        """
        if PY3 or isinstance(path, text_type):
            return path
        return path.decode(sys.getfilesystemencoding(), 'surrogateescape')

    # --- Special Python methods.

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, super(Path, self).__repr__())

    # Adding a Path and a string yields a Path.
    def __add__(self, more):
        try:
            return self._next_class(super(Path, self).__add__(more))
        except TypeError:  # Python bug
            return NotImplemented

    def __radd__(self, other):
        if not isinstance(other, string_types):
            return NotImplemented
        return self._next_class(other.__add__(self))

    # The / operator joins Paths.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
<<<<<<< HEAD
        """
        return self.__class__(os.path.join(self, rel))
=======

        .. seealso:: :func:`os.path.join`
        """
        return self._next_class(self.module.join(self, rel))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__

    def __enter__(self):
        self._old_dir = self.getcwd()
        os.chdir(self)
<<<<<<< HEAD
=======
        return self
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def __exit__(self, *_):
        os.chdir(self._old_dir)

<<<<<<< HEAD
    def getcwd(cls):
        """ Return the current working directory as a path object. """
        return cls(_getcwd())
    getcwd = classmethod(getcwd)

    #
    # --- Operations on path strings.

    def abspath(self):       return self.__class__(os.path.abspath(self))
    def normcase(self):      return self.__class__(os.path.normcase(self))
    def normpath(self):      return self.__class__(os.path.normpath(self))
    def realpath(self):      return self.__class__(os.path.realpath(self))
    def expanduser(self):    return self.__class__(os.path.expanduser(self))
    def expandvars(self):    return self.__class__(os.path.expandvars(self))
    def dirname(self):       return self.__class__(os.path.dirname(self))
    def basename(self):      return self.__class__(os.path.basename(self))

    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and normpath() on it.
=======
    @classmethod
    def getcwd(cls):
        """ Return the current working directory as a path object.

        .. seealso:: :func:`os.getcwdu`
        """
        return cls(getcwdu())

    #
    # --- Operations on Path strings.

    def abspath(self):
        """ .. seealso:: :func:`os.path.abspath` """
        return self._next_class(self.module.abspath(self))

    def normcase(self):
        """ .. seealso:: :func:`os.path.normcase` """
        return self._next_class(self.module.normcase(self))

    def normpath(self):
        """ .. seealso:: :func:`os.path.normpath` """
        return self._next_class(self.module.normpath(self))

    def realpath(self):
        """ .. seealso:: :func:`os.path.realpath` """
        return self._next_class(self.module.realpath(self))

    def expanduser(self):
        """ .. seealso:: :func:`os.path.expanduser` """
        return self._next_class(self.module.expanduser(self))

    def expandvars(self):
        """ .. seealso:: :func:`os.path.expandvars` """
        return self._next_class(self.module.expandvars(self))

    def dirname(self):
        """ .. seealso:: :attr:`parent`, :func:`os.path.dirname` """
        return self._next_class(self.module.dirname(self))

    def basename(self):
        """ .. seealso:: :attr:`name`, :func:`os.path.basename` """
        return self._next_class(self.module.basename(self))

    def expand(self):
        """ Clean up a filename by calling :meth:`expandvars()`,
        :meth:`expanduser()`, and :meth:`normpath()` on it.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        return self.expandvars().expanduser().normpath()

<<<<<<< HEAD
    def _get_namebase(self):
        base, ext = os.path.splitext(self.name)
        return base

    def _get_ext(self):
        f, ext = os.path.splitext(_base(self))
        return ext

    def _get_drive(self):
        drive, r = os.path.splitdrive(self)
        return self.__class__(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new path object.

        For example, path('/usr/local/lib/libpython.so').parent == path('/usr/local/lib')
=======
    @property
    def namebase(self):
        """ The same as :meth:`name`, but with one file extension stripped off.

        For example,
        ``Path('/home/guido/python.tar.gz').name == 'python.tar.gz'``,
        but
        ``Path('/home/guido/python.tar.gz').namebase == 'python.tar'``.
        """
        base, ext = self.module.splitext(self.name)
        return base

    @property
    def ext(self):
        """ The file extension, for example ``'.py'``. """
        f, ext = self.module.splitext(self)
        return ext

    @property
    def drive(self):
        """ The drive specifier, for example ``'C:'``.

        This is always empty on systems that don't use drive specifiers.
        """
        drive, r = self.module.splitdrive(self)
        return self._next_class(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new Path object.

        For example,
        ``Path('/usr/local/lib/libpython.so').parent ==
        Path('/usr/local/lib')``

        .. seealso:: :meth:`dirname`, :func:`os.path.dirname`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """)

    name = property(
        basename, None, None,
        """ The name of this file or directory without the full path.

<<<<<<< HEAD
        For example, path('/usr/local/lib/libpython.so').name == 'libpython.so'
        """)

    namebase = property(
        _get_namebase, None, None,
        """ The same as path.name, but with one file extension stripped off.

        For example, path('/home/guido/python.tar.gz').name     == 'python.tar.gz',
        but          path('/home/guido/python.tar.gz').namebase == 'python.tar'
        """)

    ext = property(
        _get_ext, None, None,
        """ The file extension, for example '.py'. """)

    drive = property(
        _get_drive, None, None,
        """ The drive specifier, for example 'C:'.
        This is always empty on systems that don't use drive specifiers.
        """)

    def splitpath(self):
        """ p.splitpath() -> Return (p.parent, p.name). """
        parent, child = os.path.split(self)
        return self.__class__(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return (p.drive, <the rest of p>).

        Split the drive specifier from this path.  If there is
        no drive specifier, p.drive is empty, so the return value
        is simply (path(''), p).  This is always the case on Unix.
        """
        drive, rel = os.path.splitdrive(self)
        return self.__class__(drive), rel

    def splitext(self):
        """ p.splitext() -> Return (p.stripext(), p.ext).
=======
        For example,
        ``Path('/usr/local/lib/libpython.so').name == 'libpython.so'``

        .. seealso:: :meth:`basename`, :func:`os.path.basename`
        """)

    def splitpath(self):
        """ p.splitpath() -> Return ``(p.parent, p.name)``.

        .. seealso:: :attr:`parent`, :attr:`name`, :func:`os.path.split`
        """
        parent, child = self.module.split(self)
        return self._next_class(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return ``(p.drive, <the rest of p>)``.

        Split the drive specifier from this path.  If there is
        no drive specifier, :samp:`{p.drive}` is empty, so the return value
        is simply ``(Path(''), p)``.  This is always the case on Unix.

        .. seealso:: :func:`os.path.splitdrive`
        """
        drive, rel = self.module.splitdrive(self)
        return self._next_class(drive), rel

    def splitext(self):
        """ p.splitext() -> Return ``(p.stripext(), p.ext)``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        Split the filename extension from this path and return
        the two parts.  Either part may be empty.

<<<<<<< HEAD
        The extension is everything from '.' to the end of the
        last path segment.  This has the property that if
        (a, b) == p.splitext(), then a + b == p.
        """
        filename, ext = os.path.splitext(self)
        return self.__class__(filename), ext
=======
        The extension is everything from ``'.'`` to the end of the
        last path segment.  This has the property that if
        ``(a, b) == p.splitext()``, then ``a + b == p``.

        .. seealso:: :func:`os.path.splitext`
        """
        filename, ext = self.module.splitext(self)
        return self._next_class(filename), ext
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def stripext(self):
        """ p.stripext() -> Remove one file extension from the path.

<<<<<<< HEAD
        For example, path('/home/guido/python.tar.gz').stripext()
        returns path('/home/guido/python.tar').
        """
        return self.splitext()[0]

    if hasattr(os.path, 'splitunc'):
        def splitunc(self):
            unc, rest = os.path.splitunc(self)
            return self.__class__(unc), rest

        def _get_uncshare(self):
            unc, r = os.path.splitunc(self)
            return self.__class__(unc)

        uncshare = property(
            _get_uncshare, None, None,
            """ The UNC mount point for this path.
            This is empty for paths on local drives. """)

    def joinpath(self, *args):
        """ Join two or more path components, adding a separator
        character (os.sep) if needed.  Returns a new path
        object.
        """
        return self.__class__(os.path.join(self, *args))
=======
        For example, ``Path('/home/guido/python.tar.gz').stripext()``
        returns ``Path('/home/guido/python.tar')``.
        """
        return self.splitext()[0]

    def splitunc(self):
        """ .. seealso:: :func:`os.path.splitunc` """
        unc, rest = self.module.splitunc(self)
        return self._next_class(unc), rest

    @property
    def uncshare(self):
        """
        The UNC mount point for this path.
        This is empty for paths on local drives.
        """
        unc, r = self.module.splitunc(self)
        return self._next_class(unc)

    @multimethod
    def joinpath(cls, first, *others):
        """
        Join first to zero or more :class:`Path` components, adding a separator
        character (:samp:`{first}.module.sep`) if needed.  Returns a new instance of
        :samp:`{first}._next_class`.

        .. seealso:: :func:`os.path.join`
        """
        if not isinstance(first, cls):
            first = cls(first)
        return first._next_class(first.module.join(first, *others))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def splitall(self):
        r""" Return a list of the path components in this path.

<<<<<<< HEAD
        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
=======
        The first item in the list will be a Path.  Its value will be
        either :data:`os.curdir`, :data:`os.pardir`, empty, or the root
        directory of this path (for example, ``'/'`` or ``'C:\\'``).  The
        other items in the list will be strings.

        ``path.Path.joinpath(*result)`` will yield the original path.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        parts = []
        loc = self
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = prev.splitpath()
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts

<<<<<<< HEAD
    def relpath(self):
        """ Return this path as a relative path,
        based from the current working directory.
        """
        cwd = self.__class__(os.getcwd())
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from self to dest.

        If there is no relative path from self to dest, for example if
        they reside on different drives in Windows, then this returns
        dest.abspath().
        """
        origin = self.abspath()
        dest = self.__class__(dest).abspath()
=======
    def relpath(self, start='.'):
        """ Return this path as a relative path,
        based from `start`, which defaults to the current working directory.
        """
        cwd = self._next_class(start)
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from `self` to `dest`.

        If there is no relative path from `self` to `dest`, for example if
        they reside on different drives in Windows, then this returns
        ``dest.abspath()``.
        """
        origin = self.abspath()
        dest = self._next_class(dest).abspath()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        orig_list = origin.normcase().splitall()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.splitall()

<<<<<<< HEAD
        if orig_list[0] != os.path.normcase(dest_list[0]):
=======
        if orig_list[0] != self.module.normcase(dest_list[0]):
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            # Can't get here from there.
            return dest

        # Find the location where the two paths start to differ.
        i = 0
        for start_seg, dest_seg in zip(orig_list, dest_list):
<<<<<<< HEAD
            if start_seg != os.path.normcase(dest_seg):
=======
            if start_seg != self.module.normcase(dest_seg):
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                break
            i += 1

        # Now i is the point where the two paths diverge.
        # Need a certain number of "os.pardir"s to work up
        # from the origin to the point of divergence.
        segments = [os.pardir] * (len(orig_list) - i)
        # Need to add the diverging part of dest_list.
        segments += dest_list[i:]
        if len(segments) == 0:
            # If they happen to be identical, use os.curdir.
            relpath = os.curdir
        else:
<<<<<<< HEAD
            relpath = os.path.join(*segments)
        return self.__class__(relpath)
=======
            relpath = self.module.join(*segments)
        return self._next_class(relpath)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    # --- Listing, searching, walking, and matching

    def listdir(self, pattern=None):
        """ D.listdir() -> List of items in this directory.

<<<<<<< HEAD
        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]
=======
        Use :meth:`files` or :meth:`dirs` instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are Path objects.

        With the optional `pattern` argument, this only lists
        items whose names match the given pattern.

        .. seealso:: :meth:`files`, :meth:`dirs`
        """
        if pattern is None:
            pattern = '*'
        return [
            self / child
            for child in map(self._always_unicode, os.listdir(self))
            if self._next_class(child).fnmatch(pattern)
        ]
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def dirs(self, pattern=None):
        """ D.dirs() -> List of this directory's subdirectories.

<<<<<<< HEAD
        The elements of the list are path objects.
        This does not walk recursively into subdirectories
        (but see path.walkdirs).

        With the optional 'pattern' argument, this only lists
        directories whose names match the given pattern.  For
        example, d.dirs('build-*').
=======
        The elements of the list are Path objects.
        This does not walk recursively into subdirectories
        (but see :meth:`walkdirs`).

        With the optional `pattern` argument, this only lists
        directories whose names match the given pattern.  For
        example, ``d.dirs('build-*')``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        return [p for p in self.listdir(pattern) if p.isdir()]

    def files(self, pattern=None):
        """ D.files() -> List of the files in this directory.

<<<<<<< HEAD
        The elements of the list are path objects.
        This does not walk into subdirectories (see path.walkfiles).

        With the optional 'pattern' argument, this only lists files
        whose names match the given pattern.  For example,
        d.files('*.pyc').
=======
        The elements of the list are Path objects.
        This does not walk into subdirectories (see :meth:`walkfiles`).

        With the optional `pattern` argument, this only lists files
        whose names match the given pattern.  For example,
        ``d.files('*.pyc')``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """

        return [p for p in self.listdir(pattern) if p.isfile()]

    def walk(self, pattern=None, errors='strict'):
        """ D.walk() -> iterator over files and subdirs, recursively.

<<<<<<< HEAD
        The iterator yields path objects naming each child item of
        this directory and its descendants.  This requires that
        D.isdir().
=======
        The iterator yields Path objects naming each child item of
        this directory and its descendants.  This requires that
        ``D.isdir()``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        This performs a depth-first traversal of the directory tree.
        Each directory is returned just before all its children.

<<<<<<< HEAD
        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")
=======
        The `errors=` keyword argument controls behavior when an
        error occurs.  The default is ``'strict'``, which causes an
        exception.  Other allowed values are ``'warn'`` (which
        reports the error via :func:`warnings.warn()`), and ``'ignore'``.
        `errors` may also be an arbitrary callable taking a msg parameter.
        """
        class Handlers:
            def strict(msg):
                raise

            def warn(msg):
                warnings.warn(msg, TreeWalkWarning)

            def ignore(msg):
                pass

        if not callable(errors) and errors not in vars(Handlers):
            raise ValueError("invalid errors parameter")
        errors = vars(Handlers).get(errors, errors)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        try:
            childList = self.listdir()
        except Exception:
<<<<<<< HEAD
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise
=======
            exc = sys.exc_info()[1]
            tmpl = "Unable to list directory '%(self)s': %(exc)s"
            msg = tmpl % locals()
            errors(msg)
            return
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        for child in childList:
            if pattern is None or child.fnmatch(pattern):
                yield child
            try:
                isdir = child.isdir()
            except Exception:
<<<<<<< HEAD
                if errors == 'ignore':
                    isdir = False
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (child, sys.exc_info()[1]),
                        TreeWalkWarning)
                    isdir = False
                else:
                    raise
=======
                exc = sys.exc_info()[1]
                tmpl = "Unable to access '%(child)s': %(exc)s"
                msg = tmpl % locals()
                errors(msg)
                isdir = False
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

            if isdir:
                for item in child.walk(pattern, errors):
                    yield item

    def walkdirs(self, pattern=None, errors='strict'):
        """ D.walkdirs() -> iterator over subdirs, recursively.

<<<<<<< HEAD
        With the optional 'pattern' argument, this yields only
        directories whose names match the given pattern.  For
        example, mydir.walkdirs('*test') yields only directories
        with names ending in 'test'.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
=======
        With the optional `pattern` argument, this yields only
        directories whose names match the given pattern.  For
        example, ``mydir.walkdirs('*test')`` yields only directories
        with names ending in ``'test'``.

        The `errors=` keyword argument controls behavior when an
        error occurs.  The default is ``'strict'``, which causes an
        exception.  The other allowed values are ``'warn'`` (which
        reports the error via :func:`warnings.warn()`), and ``'ignore'``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            dirs = self.dirs()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in dirs:
            if pattern is None or child.fnmatch(pattern):
                yield child
            for subsubdir in child.walkdirs(pattern, errors):
                yield subsubdir

    def walkfiles(self, pattern=None, errors='strict'):
        """ D.walkfiles() -> iterator over files in D, recursively.

<<<<<<< HEAD
        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
=======
        The optional argument `pattern` limits the results to files
        with names that match the pattern.  For example,
        ``mydir.walkfiles('*.tmp')`` yields only files with the ``.tmp``
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        extension.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            try:
                isfile = child.isfile()
                isdir = not isfile and child.isdir()
            except:
                if errors == 'ignore':
                    continue
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (self, sys.exc_info()[1]),
                        TreeWalkWarning)
                    continue
                else:
                    raise

            if isfile:
                if pattern is None or child.fnmatch(pattern):
                    yield child
            elif isdir:
                for f in child.walkfiles(pattern, errors):
                    yield f

<<<<<<< HEAD
    def fnmatch(self, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards,
            for example '*.py'.
        """
        return fnmatch.fnmatch(self.name, pattern)

    def glob(self, pattern):
        """ Return a list of path objects that match the pattern.

        pattern - a path relative to this directory, with wildcards.

        For example, path('/users').glob('*/bin/*') returns a list
        of all the files users have in their bin directories.
        """
        cls = self.__class__
        return [cls(s) for s in glob.glob(_base(self / pattern))]
=======
    def fnmatch(self, pattern, normcase=None):
        """ Return ``True`` if `self.name` matches the given `pattern`.

        `pattern` - A filename pattern with wildcards,
            for example ``'*.py'``. If the pattern contains a `normcase`
            attribute, it is applied to the name and path prior to comparison.

        `normcase` - (optional) A function used to normalize the pattern and
            filename before matching. Defaults to :meth:`self.module`, which defaults
            to :meth:`os.path.normcase`.

        .. seealso:: :func:`fnmatch.fnmatch`
        """
        default_normcase = getattr(pattern, 'normcase', self.module.normcase)
        normcase = normcase or default_normcase
        name = normcase(self.name)
        pattern = normcase(pattern)
        return fnmatch.fnmatchcase(name, pattern)

    def glob(self, pattern):
        """ Return a list of Path objects that match the pattern.

        `pattern` - a path relative to this directory, with wildcards.

        For example, ``Path('/users').glob('*/bin/*')`` returns a list
        of all the files users have in their :file:`bin` directories.

        .. seealso:: :func:`glob.glob`
        """
        cls = self._next_class
        return [cls(s) for s in glob.glob(self / pattern)]
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    #
    # --- Reading or writing an entire file at once.

<<<<<<< HEAD
    def open(self, mode='r'):
        """ Open this file.  Return a file object. """
        return open(self, mode)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        f = self.open('rb')
        try:
            return f.read()
        finally:
            f.close()
=======
    def open(self, *args, **kwargs):
        """ Open this file and return a corresponding :class:`file` object.

        Keyword arguments work as in :func:`io.open`.  If the file cannot be
        opened, an :class:`~exceptions.OSError` is raised.
        """
        with io_error_compat():
            return io.open(self, *args, **kwargs)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        with self.open('rb') as f:
            return f.read()

    def chunks(self, size, *args, **kwargs):
        """ Returns a generator yielding chunks of the file, so it can
            be read piece by piece with a simple for loop.

           Any argument you pass after `size` will be passed to :meth:`open`.

           :example:

               >>> hash = hashlib.md5()
               >>> for chunk in Path("path.py").chunks(8192, mode='rb'):
               ...     hash.update(chunk)

            This will read the file by chunks of 8192 bytes.
        """
        with self.open(*args, **kwargs) as f:
            while True:
                d = f.read(size)
                if not d:
                    break
                yield d
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def write_bytes(self, bytes, append=False):
        """ Open this file and write the given bytes to it.

        Default behavior is to overwrite any existing file.
<<<<<<< HEAD
        Call p.write_bytes(bytes, append=True) to append instead.
=======
        Call ``p.write_bytes(bytes, append=True)`` to append instead.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
<<<<<<< HEAD
        f = self.open(mode)
        try:
            f.write(bytes)
        finally:
            f.close()
=======
        with self.open(mode) as f:
            f.write(bytes)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def text(self, encoding=None, errors='strict'):
        r""" Open this file, read it in, return the content as a string.

<<<<<<< HEAD
        This uses 'U' mode in Python 2.3 and later, so '\r\n' and '\r'
        are automatically translated to '\n'.

        Optional arguments:

        encoding - The Unicode encoding (or character set) of
            the file.  If present, the content of the file is
            decoded and returned as a unicode object; otherwise
            it is returned as an 8-bit str.
        errors - How to handle Unicode errors; see help(str.decode)
            for the options.  Default is 'strict'.
        """
        if encoding is None:
            # 8-bit
            f = self.open(_textmode)
            try:
                return f.read()
            finally:
                f.close()
        else:
            # Unicode
            f = codecs.open(self, 'r', encoding, errors)
            # (Note - Can't use 'U' mode here, since codecs.open
            # doesn't support 'U' mode, even in Python 2.3.)
            try:
                t = f.read()
            finally:
                f.close()
            return (t.replace(u('\r\n'), u('\n'))
                     .replace(u('\r\x85'), u('\n'))
                     .replace(u('\r'), u('\n'))
                     .replace(u('\x85'), u('\n'))
                     .replace(u('\u2028'), u('\n')))

    def write_text(self, text, encoding=None, errors='strict', linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the 'append=True' keyword argument.

        There are two differences between path.write_text() and
        path.write_bytes(): newline handling and Unicode handling.
=======
        All newline sequences are converted to ``'\n'``.  Keyword arguments
        will be passed to :meth:`open`.

        .. seealso:: :meth:`lines`
        """
        with self.open(mode='r', encoding=encoding, errors=errors) as f:
            return U_NEWLINE.sub('\n', f.read())

    def write_text(self, text, encoding=None, errors='strict',
                   linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the `append=True` keyword argument.

        There are two differences between :meth:`write_text` and
        :meth:`write_bytes`: newline handling and Unicode handling.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        See below.

        Parameters:

<<<<<<< HEAD
          - text - str/unicode - The text to be written.

          - encoding - str - The Unicode encoding that will be used.
            This is ignored if 'text' isn't a Unicode string.

          - errors - str - How to handle Unicode encoding errors.
            Default is 'strict'.  See help(unicode.encode) for the
            options.  This is ignored if 'text' isn't a Unicode
            string.

          - linesep - keyword argument - str/unicode - The sequence of
            characters to be used to mark end-of-line.  The default is
            os.linesep.  You can also specify None; this means to
            leave all newlines as they are in 'text'.

          - append - keyword argument - bool - Specifies what to do if
            the file already exists (True: append to the end of it;
            False: overwrite it.)  The default is False.
=======
          `text` - str/unicode - The text to be written.

          `encoding` - str - The Unicode encoding that will be used.
              This is ignored if `text` isn't a Unicode string.

          `errors` - str - How to handle Unicode encoding errors.
              Default is ``'strict'``.  See ``help(unicode.encode)`` for the
              options.  This is ignored if `text` isn't a Unicode
              string.

          `linesep` - keyword argument - str/unicode - The sequence of
              characters to be used to mark end-of-line.  The default is
              :data:`os.linesep`.  You can also specify ``None`` to
              leave all newlines as they are in `text`.

          `append` - keyword argument - bool - Specifies what to do if
              the file already exists (``True``: append to the end of it;
              ``False``: overwrite it.)  The default is ``False``.
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f


        --- Newline handling.

<<<<<<< HEAD
        write_text() converts all standard end-of-line sequences
        ('\n', '\r', and '\r\n') to your platform's default end-of-line
        sequence (see os.linesep; on Windows, for example, the
        end-of-line marker is '\r\n').

        If you don't like your platform's default, you can override it
        using the 'linesep=' keyword argument.  If you specifically want
        write_text() to preserve the newlines as-is, use 'linesep=None'.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        u'\x85', u'\r\x85', and u'\u2028'.

        (This is slightly different from when you open a file for
        writing with fopen(filename, "w") in C or open(filename, 'w')
=======
        ``write_text()`` converts all standard end-of-line sequences
        (``'\n'``, ``'\r'``, and ``'\r\n'``) to your platform's default
        end-of-line sequence (see :data:`os.linesep`; on Windows, for example,
        the end-of-line marker is ``'\r\n'``).

        If you don't like your platform's default, you can override it
        using the `linesep=` keyword argument.  If you specifically want
        ``write_text()`` to preserve the newlines as-is, use ``linesep=None``.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        ``u'\x85'``, ``u'\r\x85'``, and ``u'\u2028'``.

        (This is slightly different from when you open a file for
        writing with ``fopen(filename, "w")`` in C or ``open(filename, 'w')``
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        in Python.)


        --- Unicode

<<<<<<< HEAD
        If 'text' isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The 'encoding' and
        'errors' arguments are not used and must be omitted.

        If 'text' is Unicode, it is first converted to bytes using the
        specified 'encoding' (or the default encoding if 'encoding'
        isn't specified).  The 'errors' argument applies only to this
        conversion.

        """
        if is_unicode(text):
            if linesep is not None:
                # Convert all standard end-of-line sequences to
                # ordinary newline characters.
                text = (text.replace(u('\r\n'), u('\n'))
                            .replace(u('\r\x85'), u('\n'))
                            .replace(u('\r'), u('\n'))
                            .replace(u('\x85'), u('\n'))
                            .replace(u('\u2028'), u('\n')))
                text = text.replace(u('\n'), linesep)
            if encoding is None:
                encoding = sys.getdefaultencoding()
            bytes = text.encode(encoding, errors)
        else:
            # It is an error to specify an encoding if 'text' is
            # an 8-bit string.
            assert encoding is None

            if linesep is not None:
                text = (text.replace('\r\n', '\n')
                            .replace('\r', '\n'))
                bytes = text.replace('\n', linesep)

        self.write_bytes(bytes, append)
=======
        If `text` isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The `encoding` and
        `errors` arguments are not used and must be omitted.

        If `text` is Unicode, it is first converted to :func:`bytes` using the
        specified `encoding` (or the default encoding if `encoding`
        isn't specified).  The `errors` argument applies only to this
        conversion.

        """
        if isinstance(text, text_type):
            if linesep is not None:
                text = U_NEWLINE.sub(linesep, text)
            text = text.encode(encoding or sys.getdefaultencoding(), errors)
        else:
            assert encoding is None
            text = NEWLINE.sub(linesep, text)
        self.write_bytes(text, append=append)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def lines(self, encoding=None, errors='strict', retain=True):
        r""" Open this file, read all lines, return them in a list.

        Optional arguments:
<<<<<<< HEAD
            encoding - The Unicode encoding (or character set) of
                the file.  The default is None, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            errors - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is 'strict'
            retain - If true, retain newline characters; but all newline
                character combinations ('\r', '\n', '\r\n') are
                translated to '\n'.  If false, newline characters are
                stripped off.  Default is True.

        This uses 'U' mode in Python 2.3 and later.
        """
        if encoding is None and retain:
            f = self.open(_textmode)
            try:
                return f.readlines()
            finally:
                f.close()
=======
            `encoding` - The Unicode encoding (or character set) of
                the file.  The default is ``None``, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            `errors` - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is ``'strict'``.
            `retain` - If ``True``, retain newline characters; but all newline
                character combinations (``'\r'``, ``'\n'``, ``'\r\n'``) are
                translated to ``'\n'``.  If ``False``, newline characters are
                stripped off.  Default is ``True``.

        This uses ``'U'`` mode.

        .. seealso:: :meth:`text`
        """
        if encoding is None and retain:
            with self.open('U') as f:
                return f.readlines()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        else:
            return self.text(encoding, errors).splitlines(retain)

    def write_lines(self, lines, encoding=None, errors='strict',
                    linesep=os.linesep, append=False):
        r""" Write the given lines of text to this file.

        By default this overwrites any existing file at this path.

        This puts a platform-specific newline sequence on every line.
<<<<<<< HEAD
        See 'linesep' below.

        lines - A list of strings.

        encoding - A Unicode encoding to use.  This applies only if
            'lines' contains any Unicode strings.

        errors - How to handle errors in Unicode encoding.  This
            also applies only to Unicode strings.

        linesep - The desired line-ending.  This line-ending is
            applied to every line.  If a line already has any
            standard line ending ('\r', '\n', '\r\n', u'\x85',
            u'\r\x85', u'\u2028'), that will be stripped off and
            this will be used instead.  The default is os.linesep,
            which is platform-dependent ('\r\n' on Windows, '\n' on
            Unix, etc.)  Specify None to write the lines as-is,
            like file.writelines().

        Use the keyword argument append=True to append lines to the
        file.  The default is to overwrite the file.  Warning:
        When you use this with Unicode data, if the encoding of the
        existing data in the file is different from the encoding
        you specify with the encoding= parameter, the result is
        mixed-encoding data, which can really confuse someone trying
        to read the file later.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            for line in lines:
                isUnicode = is_unicode(line)
                if linesep is not None:
                    # Strip off any existing line-end and add the
                    # specified linesep string.
                    if isUnicode:
                        if line[-2:] in (u('\r\n'), u('\x0d\x85')):
                            line = line[:-2]
                        elif line[-1:] in (u('\r'), u('\n'),
                                           u('\x85'), u('\u2028')):
                            line = line[:-1]
                    else:
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n'):
                            line = line[:-1]
                    line += linesep
                if isUnicode:
                    if encoding is None:
                        encoding = sys.getdefaultencoding()
                    line = line.encode(encoding, errors)
                f.write(line)
        finally:
            f.close()
=======
        See `linesep` below.

            `lines` - A list of strings.

            `encoding` - A Unicode encoding to use.  This applies only if
                `lines` contains any Unicode strings.

            `errors` - How to handle errors in Unicode encoding.  This
                also applies only to Unicode strings.

            linesep - The desired line-ending.  This line-ending is
                applied to every line.  If a line already has any
                standard line ending (``'\r'``, ``'\n'``, ``'\r\n'``,
                ``u'\x85'``, ``u'\r\x85'``, ``u'\u2028'``), that will
                be stripped off and this will be used instead.  The
                default is os.linesep, which is platform-dependent
                (``'\r\n'`` on Windows, ``'\n'`` on Unix, etc.).
                Specify ``None`` to write the lines as-is, like
                :meth:`file.writelines`.

        Use the keyword argument ``append=True`` to append lines to the
        file.  The default is to overwrite the file.

        .. warning ::

            When you use this with Unicode data, if the encoding of the
            existing data in the file is different from the encoding
            you specify with the `encoding=` parameter, the result is
            mixed-encoding data, which can really confuse someone trying
            to read the file later.
        """
        with self.open('ab' if append else 'wb') as f:
            for l in lines:
                isUnicode = isinstance(l, text_type)
                if linesep is not None:
                    pattern = U_NL_END if isUnicode else NL_END
                    l = pattern.sub('', l) + linesep
                if isUnicode:
                    l = l.encode(encoding or sys.getdefaultencoding(), errors)
                f.write(l)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def read_md5(self):
        """ Calculate the md5 hash for this file.

        This reads through the entire file.
<<<<<<< HEAD
=======

        .. seealso:: :meth:`read_hash`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        return self.read_hash('md5')

    def _hash(self, hash_name):
<<<<<<< HEAD
        f = self.open('rb')
        try:
            m = hashlib.new(hash_name)
            while True:
                d = f.read(8192)
                if not d:
                    break
                m.update(d)
            return m
        finally:
            f.close()
=======
        """ Returns a hash object for the file at the current path.

            `hash_name` should be a hash algo name (such as ``'md5'`` or ``'sha1'``)
            that's available in the :mod:`hashlib` module.
        """
        m = hashlib.new(hash_name)
        for chunk in self.chunks(8192, mode="rb"):
            m.update(chunk)
        return m
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def read_hash(self, hash_name):
        """ Calculate given hash for this file.

<<<<<<< HEAD
        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
=======
        List of supported hashes can be obtained from :mod:`hashlib` package.
        This reads the entire file.

        .. seealso:: :meth:`hashlib.hash.digest`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        return self._hash(hash_name).digest()

    def read_hexhash(self, hash_name):
        """ Calculate given hash for this file, returning hexdigest.

<<<<<<< HEAD
        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
=======
        List of supported hashes can be obtained from :mod:`hashlib` package.
        This reads the entire file.

        .. seealso:: :meth:`hashlib.hash.hexdigest`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """
        return self._hash(hash_name).hexdigest()

    # --- Methods for querying the filesystem.
    # N.B. On some platforms, the os.path functions may be implemented in C
    # (e.g. isdir on Windows, Python 3.2.2), and compiled functions don't get
    # bound. Playing it safe and wrapping them all in method calls.

<<<<<<< HEAD
    def isabs(self): return os.path.isabs(self)
    def exists(self): return os.path.exists(self)
    def isdir(self): return os.path.isdir(self)
    def isfile(self): return os.path.isfile(self)
    def islink(self): return os.path.islink(self)
    def ismount(self): return os.path.ismount(self)

    if hasattr(os.path, 'samefile'):
        def samefile(self): return os.path.samefile(self)

    def getatime(self): return os.path.getatime(self)
    atime = property(
        getatime, None, None,
        """ Last access time of the file. """)

    def getmtime(self): return os.path.getmtime(self)
    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file. """)

    if hasattr(os.path, 'getctime'):
        def getctime(self): return os.path.getctime(self)
        ctime = property(
            getctime, None, None,
            """ Creation time of the file. """)

    def getsize(self): return os.path.getsize(self)
    size = property(
        getsize, None, None,
        """ Size of the file, in bytes. """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return true if current user has access to this path.

            mode - One of the constants os.F_OK, os.R_OK, os.W_OK, os.X_OK
=======
    def isabs(self):
        """ .. seealso:: :func:`os.path.isabs` """
        return self.module.isabs(self)

    def exists(self):
        """ .. seealso:: :func:`os.path.exists` """
        return self.module.exists(self)

    def isdir(self):
        """ .. seealso:: :func:`os.path.isdir` """
        return self.module.isdir(self)

    def isfile(self):
        """ .. seealso:: :func:`os.path.isfile` """
        return self.module.isfile(self)

    def islink(self):
        """ .. seealso:: :func:`os.path.islink` """
        return self.module.islink(self)

    def ismount(self):
        """ .. seealso:: :func:`os.path.ismount` """
        return self.module.ismount(self)

    def samefile(self, other):
        """ .. seealso:: :func:`os.path.samefile` """
        return self.module.samefile(self, other)

    def getatime(self):
        """ .. seealso:: :attr:`atime`, :func:`os.path.getatime` """
        return self.module.getatime(self)

    atime = property(
        getatime, None, None,
        """ Last access time of the file.

        .. seealso:: :meth:`getatime`, :func:`os.path.getatime`
        """)

    def getmtime(self):
        """ .. seealso:: :attr:`mtime`, :func:`os.path.getmtime` """
        return self.module.getmtime(self)

    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file.

        .. seealso:: :meth:`getmtime`, :func:`os.path.getmtime`
        """)

    def getctime(self):
        """ .. seealso:: :attr:`ctime`, :func:`os.path.getctime` """
        return self.module.getctime(self)

    ctime = property(
        getctime, None, None,
        """ Creation time of the file.

        .. seealso:: :meth:`getctime`, :func:`os.path.getctime`
        """)

    def getsize(self):
        """ .. seealso:: :attr:`size`, :func:`os.path.getsize` """
        return self.module.getsize(self)

    size = property(
        getsize, None, None,
        """ Size of the file, in bytes.

        .. seealso:: :meth:`getsize`, :func:`os.path.getsize`
        """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return ``True`` if current user has access to this path.

            mode - One of the constants :data:`os.F_OK`, :data:`os.R_OK`,
            :data:`os.W_OK`, :data:`os.X_OK`

            .. seealso:: :func:`os.access`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            """
            return os.access(self, mode)

    def stat(self):
<<<<<<< HEAD
        """ Perform a stat() system call on this path. """
        return os.stat(self)

    def lstat(self):
        """ Like path.stat(), but do not follow symbolic links. """
        return os.lstat(self)

    def get_owner(self):
        r""" Return the name of the owner of this file or directory.

        This follows symbolic links.

        On Windows, this returns a name of the form ur'DOMAIN\User Name'.
        On Windows, a group can own a file or directory.
        """
        if os.name == 'nt':
            if win32security is None:
                raise Exception("path.owner requires win32all to be installed")
            desc = win32security.GetFileSecurity(
                self, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
            return domain + u('\\') + account
        else:
            if pwd is None:
                raise NotImplementedError("path.owner is not implemented on this platform.")
            st = self.stat()
            return pwd.getpwuid(st.st_uid).pw_name

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory. """)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a statvfs() system call on this path. """
=======
        """ Perform a ``stat()`` system call on this path.

        .. seealso:: :meth:`lstat`, :func:`os.stat`
        """
        return os.stat(self)

    def lstat(self):
        """ Like :meth:`stat`, but do not follow symbolic links.

        .. seealso:: :meth:`stat`, :func:`os.lstat`
        """
        return os.lstat(self)

    def __get_owner_windows(self):
        r"""
        Return the name of the owner of this file or directory. Follow
        symbolic links.

        Return a name of the form ``ur'DOMAIN\User Name'``; may be a group.

        .. seealso:: :attr:`owner`
        """
        desc = win32security.GetFileSecurity(
            self, win32security.OWNER_SECURITY_INFORMATION)
        sid = desc.GetSecurityDescriptorOwner()
        account, domain, typecode = win32security.LookupAccountSid(None, sid)
        return domain + u('\\') + account

    def __get_owner_unix(self):
        """
        Return the name of the owner of this file or directory. Follow
        symbolic links.

        .. seealso:: :attr:`owner`
        """
        st = self.stat()
        return pwd.getpwuid(st.st_uid).pw_name

    def __get_owner_not_implemented(self):
        raise NotImplementedError("Ownership not available on this platform.")

    if 'win32security' in globals():
        get_owner = __get_owner_windows
    elif 'pwd' in globals():
        get_owner = __get_owner_unix
    else:
        get_owner = __get_owner_not_implemented

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory.

        .. seealso:: :meth:`get_owner`""")

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a ``statvfs()`` system call on this path.

            .. seealso:: :func:`os.statvfs`
            """
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            return os.statvfs(self)

    if hasattr(os, 'pathconf'):
        def pathconf(self, name):
<<<<<<< HEAD
=======
            """ .. seealso:: :func:`os.pathconf` """
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            return os.pathconf(self, name)

    #
    # --- Modifying operations on files and directories

    def utime(self, times):
<<<<<<< HEAD
        """ Set the access and modified times of this file. """
        os.utime(self, times)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def rename(self, new):
        os.rename(self, new)

    def renames(self, new):
        os.renames(self, new)
=======
        """ Set the access and modified times of this file.

        .. seealso:: :func:`os.utime`
        """
        os.utime(self, times)
        return self

    def chmod(self, mode):
        """
        Set the mode. May be the new mode (os.chmod behavior) or a `symbolic
        mode <http://en.wikipedia.org/wiki/Chmod#Symbolic_modes>`_.

        .. seealso:: :func:`os.chmod`
        """
        if isinstance(mode, string_types):
            mask = _multi_permission_mask(mode)
            mode = mask(self.stat().st_mode)
        os.chmod(self, mode)
        return self

    if hasattr(os, 'chown'):
        def chown(self, uid=-1, gid=-1):
            """ .. seealso:: :func:`os.chown` """
            if 'pwd' in globals() and isinstance(uid, string_types):
                uid = pwd.getpwnam(uid).pw_uid
            if 'grp' in globals() and isinstance(gid, string_types):
                gid = grp.getgrnam(gid).gr_gid
            os.chown(self, uid, gid)
            return self

    def rename(self, new):
        """ .. seealso:: :func:`os.rename` """
        os.rename(self, new)
        return self._next_class(new)

    def renames(self, new):
        """ .. seealso:: :func:`os.renames` """
        os.renames(self, new)
        return self._next_class(new)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    #
    # --- Create/delete operations on directories

<<<<<<< HEAD
    def mkdir(self, mode=MODE_0777):
        os.mkdir(self, mode)

    def mkdir_p(self, mode=MODE_0777):
        try:
            self.mkdir(mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def makedirs(self, mode=MODE_0777):
        os.makedirs(self, mode)

    def makedirs_p(self, mode=MODE_0777):
        try:
            self.makedirs(mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def rmdir(self):
        os.rmdir(self)

    def rmdir_p(self):
        try:
            self.rmdir()
        except OSError as e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise

    def removedirs(self):
        os.removedirs(self)

    def removedirs_p(self):
        try:
            self.removedirs()
        except OSError as e:
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise
=======
    def mkdir(self, mode=0o777):
        """ .. seealso:: :func:`os.mkdir` """
        os.mkdir(self, mode)
        return self

    def mkdir_p(self, mode=0o777):
        """ Like :meth:`mkdir`, but does not raise an exception if the
        directory already exists. """
        try:
            self.mkdir(mode)
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.EEXIST:
                raise
        return self

    def makedirs(self, mode=0o777):
        """ .. seealso:: :func:`os.makedirs` """
        os.makedirs(self, mode)
        return self

    def makedirs_p(self, mode=0o777):
        """ Like :meth:`makedirs`, but does not raise an exception if the
        directory already exists. """
        try:
            self.makedirs(mode)
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.EEXIST:
                raise
        return self

    def rmdir(self):
        """ .. seealso:: :func:`os.rmdir` """
        os.rmdir(self)
        return self

    def rmdir_p(self):
        """ Like :meth:`rmdir`, but does not raise an exception if the
        directory is not empty or does not exist. """
        try:
            self.rmdir()
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise
        return self

    def removedirs(self):
        """ .. seealso:: :func:`os.removedirs` """
        os.removedirs(self)
        return self

    def removedirs_p(self):
        """ Like :meth:`removedirs`, but does not raise an exception if the
        directory is not empty or does not exist. """
        try:
            self.removedirs()
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.ENOTEMPTY and e.errno != errno.EEXIST:
                raise
        return self
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    # --- Modifying operations on files

    def touch(self):
        """ Set the access/modified times of this file to the current time.
        Create the file if it does not exist.
        """
<<<<<<< HEAD
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, MODE_0666)
        os.close(fd)
        os.utime(self, None)

    def remove(self):
        os.remove(self)

    def remove_p(self):
        try:
            self.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def unlink(self):
        os.unlink(self)

    def unlink_p(self):
        self.remove_p()
=======
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0o666)
        os.close(fd)
        os.utime(self, None)
        return self

    def remove(self):
        """ .. seealso:: :func:`os.remove` """
        os.remove(self)
        return self

    def remove_p(self):
        """ Like :meth:`remove`, but does not raise an exception if the
        file does not exist. """
        try:
            self.unlink()
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.ENOENT:
                raise
        return self

    def unlink(self):
        """ .. seealso:: :func:`os.unlink` """
        os.unlink(self)
        return self

    def unlink_p(self):
        """ Like :meth:`unlink`, but does not raise an exception if the
        file does not exist. """
        self.remove_p()
        return self
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    # --- Links

    if hasattr(os, 'link'):
        def link(self, newpath):
<<<<<<< HEAD
            """ Create a hard link at 'newpath', pointing to this file. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at 'newlink', pointing here. """
            os.symlink(self, newlink)
=======
            """ Create a hard link at `newpath`, pointing to this file.

            .. seealso:: :func:`os.link`
            """
            os.link(self, newpath)
            return self._next_class(newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at `newlink`, pointing here.

            .. seealso:: :func:`os.symlink`
            """
            os.symlink(self, newlink)
            return self._next_class(newlink)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    if hasattr(os, 'readlink'):
        def readlink(self):
            """ Return the path to which this symbolic link points.

            The result may be an absolute or a relative path.
<<<<<<< HEAD
            """
            return self.__class__(os.readlink(self))
=======

            .. seealso:: :meth:`readlinkabs`, :func:`os.readlink`
            """
            return self._next_class(os.readlink(self))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

        def readlinkabs(self):
            """ Return the path to which this symbolic link points.

            The result is always an absolute path.
<<<<<<< HEAD
=======

            .. seealso:: :meth:`readlink`, :func:`os.readlink`
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            """
            p = self.readlink()
            if p.isabs():
                return p
            else:
                return (self.parent / p).abspath()

    #
    # --- High-level functions from shutil

    copyfile = shutil.copyfile
    copymode = shutil.copymode
    copystat = shutil.copystat
    copy = shutil.copy
    copy2 = shutil.copy2
    copytree = shutil.copytree
    if hasattr(shutil, 'move'):
        move = shutil.move
    rmtree = shutil.rmtree

    def rmtree_p(self):
<<<<<<< HEAD
        try:
            self.rmtree()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
=======
        """ Like :meth:`rmtree`, but does not raise an exception if the
        directory does not exist. """
        try:
            self.rmtree()
        except OSError:
            _, e, _ = sys.exc_info()
            if e.errno != errno.ENOENT:
                raise
        return self

    def chdir(self):
        """ .. seealso:: :func:`os.chdir` """
        os.chdir(self)

    cd = chdir
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    #
    # --- Special stuff from os

    if hasattr(os, 'chroot'):
        def chroot(self):
<<<<<<< HEAD
=======
            """ .. seealso:: :func:`os.chroot` """
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            os.chroot(self)

    if hasattr(os, 'startfile'):
        def startfile(self):
<<<<<<< HEAD
            os.startfile(self)
=======
            """ .. seealso:: :func:`os.startfile` """
            os.startfile(self)
            return self

    # in-place re-writing, courtesy of Martijn Pieters
    # http://www.zopatista.com/python/2013/11/26/inplace-file-rewriting/
    @contextlib.contextmanager
    def in_place(self, mode='r', buffering=-1, encoding=None, errors=None,
            newline=None, backup_extension=None):
        """
        A context in which a file may be re-written in-place with new content.

        Yields a tuple of :samp:`({readable}, {writable})` file objects, where `writable`
        replaces `readable`.

        If an exception occurs, the old file is restored, removing the
        written data.

        Mode *must not* use ``'w'``, ``'a'``, or ``'+'``; only read-only-modes are
        allowed. A :exc:`ValueError` is raised on invalid modes.

        For example, to add line numbers to a file::

            p = Path(filename)
            assert p.isfile()
            with p.in_place() as reader, writer:
                for number, line in enumerate(reader, 1):
                    writer.write('{0:3}: '.format(number)))
                    writer.write(line)

        Thereafter, the file at `filename` will have line numbers in it.
        """
        import io

        if set(mode).intersection('wa+'):
            raise ValueError('Only read-only file modes can be used')

        # move existing file to backup, create new file with same permissions
        # borrowed extensively from the fileinput module
        backup_fn = self + (backup_extension or os.extsep + 'bak')
        try:
            os.unlink(backup_fn)
        except os.error:
            pass
        os.rename(self, backup_fn)
        readable = io.open(backup_fn, mode, buffering=buffering,
            encoding=encoding, errors=errors, newline=newline)
        try:
            perm = os.fstat(readable.fileno()).st_mode
        except OSError:
            writable = open(self, 'w' + mode.replace('r', ''),
                buffering=buffering, encoding=encoding, errors=errors,
                newline=newline)
        else:
            os_mode = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            if hasattr(os, 'O_BINARY'):
                os_mode |= os.O_BINARY
            fd = os.open(self, os_mode, perm)
            writable = io.open(fd, "w" + mode.replace('r', ''),
                buffering=buffering, encoding=encoding, errors=errors,
                newline=newline)
            try:
                if hasattr(os, 'chmod'):
                    os.chmod(self, perm)
            except OSError:
                pass
        try:
            yield readable, writable
        except Exception:
            # move backup back
            readable.close()
            writable.close()
            try:
                os.unlink(self)
            except os.error:
                pass
            os.rename(backup_fn, self)
            raise
        else:
            readable.close()
            writable.close()
        finally:
            try:
                os.unlink(backup_fn)
            except os.error:
                pass


class tempdir(Path):
    """
    A temporary directory via :func:`tempfile.mkdtemp`, and constructed with the
    same parameters that you can use as a context manager.

    Example:

        with tempdir() as d:
            # do stuff with the Path object "d"

        # here the directory is deleted automatically

    .. seealso:: :func:`tempfile.mkdtemp`
    """

    @ClassProperty
    @classmethod
    def _next_class(cls):
        return Path

    def __new__(cls, *args, **kwargs):
        dirname = tempfile.mkdtemp(*args, **kwargs)
        return super(tempdir, cls).__new__(cls, dirname)

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_value:
            self.rmtree()


def _multi_permission_mask(mode):
    """
    Support multiple, comma-separated Unix chmod symbolic modes.

    >>> _multi_permission_mask('a=r,u+w')(0) == 0o644
    True
    """
    compose = lambda f, g: lambda *args, **kwargs: g(f(*args, **kwargs))
    return functools.reduce(compose, map(_permission_mask, mode.split(',')))


def _permission_mask(mode):
    """
    Convert a Unix chmod symbolic mode like ``'ugo+rwx'`` to a function
    suitable for applying to a mask to affect that change.

    >>> mask = _permission_mask('ugo+rwx')
    >>> mask(0o554) == 0o777
    True

    >>> _permission_mask('go-x')(0o777) == 0o766
    True

    >>> _permission_mask('o-x')(0o445) == 0o444
    True

    >>> _permission_mask('a+x')(0) == 0o111
    True

    >>> _permission_mask('a=rw')(0o057) == 0o666
    True

    >>> _permission_mask('u=x')(0o666) == 0o166
    True

    >>> _permission_mask('g=')(0o157) == 0o107
    True
    """
    # parse the symbolic mode
    parsed = re.match('(?P<who>[ugoa]+)(?P<op>[-+=])(?P<what>[rwx]*)$', mode)
    if not parsed:
        raise ValueError("Unrecognized symbolic mode", mode)

    # generate a mask representing the specified permission
    spec_map = dict(r=4, w=2, x=1)
    specs = (spec_map[perm] for perm in parsed.group('what'))
    spec = functools.reduce(operator.or_, specs, 0)

    # now apply spec to each subject in who
    shift_map = dict(u=6, g=3, o=0)
    who = parsed.group('who').replace('a', 'ugo')
    masks = (spec << shift_map[subj] for subj in who)
    mask = functools.reduce(operator.or_, masks)

    op = parsed.group('op')

    # if op is -, invert the mask
    if op == '-':
        mask ^= 0o777

    # if op is =, retain extant values for unreferenced subjects
    if op == '=':
        masks = (0o7 << shift_map[subj] for subj in who)
        retain = functools.reduce(operator.or_, masks) ^ 0o777

    op_map = {
        '+': operator.or_,
        '-': operator.and_,
        '=': lambda mask, target: target & retain ^ mask,
    }
    return functools.partial(op_map[op], mask)


class CaseInsensitivePattern(text_type):
    """
    A string with a ``'normcase'`` property, suitable for passing to
    :meth:`listdir`, :meth:`dirs`, :meth:`files`, :meth:`walk`,
    :meth:`walkdirs`, or :meth:`walkfiles` to match case-insensitive.

    For example, to get all files ending in .py, .Py, .pY, or .PY in the
    current directory::

        from path import Path, CaseInsensitivePattern as ci
        Path('.').files(ci('*.py'))
    """

    @property
    def normcase(self):
        return __import__('ntpath').normcase
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
