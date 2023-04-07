#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

import linecache
import os.path
import types
import sys


def new_main_mod(filename, modname):
    """
    Reimplemented from IPython/core/interactiveshell.py to avoid caching
    and clearing recursive namespace.
    """
    filename = os.path.abspath(filename)

    main_mod = types.ModuleType(
        modname,
        doc="Module created for script run in IPython")

    main_mod.__file__ = filename
    # It seems pydoc (and perhaps others) needs any module instance to
    # implement a __nonzero__ method
    main_mod.__nonzero__ = lambda: True

    return main_mod


class NamespaceManager:
    """
    Get a namespace and set __file__ to filename for this namespace.

    The namespace is either namespace, the current namespace if
    current_namespace is True, or a new namespace.
    """

    def __init__(
        self,
        shell,
        filename,
        current_namespace=False,
        file_code=None,
        context_locals=None,
        context_globals=None,
    ):
        self.shell = shell
        self.filename = filename
        self.ns_globals = None
        self.ns_locals = None
        self.current_namespace = current_namespace
        self._previous_filename = None
        self._previous_main = None
        self._reset_main = False
        self._file_code = file_code
        if context_globals is None:
            context_globals = shell.user_ns
        self.context_globals = context_globals
        self.context_locals = context_locals

    def __enter__(self):
        """
        Prepare the namespace.
        """
        # Save previous __file__
        if self.current_namespace:
            self.ns_globals = self.context_globals
            self.ns_locals = self.context_locals
            if '__file__' in self.ns_globals:
                self._previous_filename = self.ns_globals['__file__']
            self.ns_globals['__file__'] = self.filename
        else:
            main_mod = new_main_mod(self.filename, '__main__')
            self.ns_globals = main_mod.__dict__
            self.ns_locals = None

            # Needed to allow pickle to reference main
            if '__main__' in sys.modules:
                self._previous_main = sys.modules['__main__']
            sys.modules['__main__'] = main_mod
            self._reset_main = True

        # Save current namespace for access by variable explorer
        self.shell.add_namespace_manager(self)

        if (self._file_code is not None
                and isinstance(self._file_code, bytes)):
            try:
                self._file_code = self._file_code.decode()
            except UnicodeDecodeError:
                # Setting the cache is not supported for non utf-8 files
                self._file_code = None
        if self._file_code is not None:
            # '\n' is used instead of the native line endings. (see linecache)
            # mtime is set to None to avoid a cache update.
            linecache.cache[self.filename] = (
                len(self._file_code), None,
                [line + '\n' for line in self._file_code.splitlines()],
                self.filename)
        return self.ns_globals, self.ns_locals

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Reset the namespace.
        """
        self.shell.remove_namespace_manager(self)
        if self._previous_filename:
            self.ns_globals['__file__'] = self._previous_filename
        elif '__file__' in self.ns_globals:
            self.ns_globals.pop('__file__')

        if not self.current_namespace:
            if self.context_locals is not None:
                self.context_locals.update(self.ns_globals)
            else:
                self.context_globals.update(self.ns_globals)

        if self._previous_main:
            sys.modules['__main__'] = self._previous_main
        elif '__main__' in sys.modules and self._reset_main:
            del sys.modules['__main__']
        if self.filename in linecache.cache and os.path.exists(self.filename):
            linecache.cache.pop(self.filename)
