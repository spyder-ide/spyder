# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Spyder shell for Jupyter kernels.
"""

# Standard library imports
import bdb
import sys
import traceback

# Third-party imports
from ipykernel.zmqshell import ZMQInteractiveShell

# Local imports
from spyder_kernels.utils.mpl import automatic_backend


class SpyderShell(ZMQInteractiveShell):
    """Spyder shell."""

    def __init__(self, *args, **kwargs):
        # Create _pdb_obj before __init__
        self._pdb_obj = None
        super(SpyderShell, self).__init__(*args, **kwargs)

    # ---- Methods overriden by us.
    def ask_exit(self):
        """Engage the exit actions."""
        self.kernel.frontend_comm.close_thread()
        return super(SpyderShell, self).ask_exit()

    def _showtraceback(self, etype, evalue, stb):
        """
        Don't show a traceback when exiting our debugger after entering
        it through a `breakpoint()` call.

        This is because calling `!exit` after `breakpoint()` raises
        BdbQuit, which throws a long and useless traceback.
        """
        if etype is bdb.BdbQuit:
            stb = ['']
        super(SpyderShell, self)._showtraceback(etype, evalue, stb)

    # ---- For Pdb namespace integration
    def get_local_scope(self, stack_depth):
        """Get local scope at given frame depth."""
        frame = sys._getframe(stack_depth + 1)
        if self._pdb_frame is frame:
            # Avoid calling f_locals on _pdb_frame
            return self._pdb_obj.curframe_locals
        else:
            return frame.f_locals

    def get_global_scope(self, stack_depth):
        """Get global scope at given frame depth."""
        frame = sys._getframe(stack_depth + 1)
        return frame.f_globals

    def is_debugging(self):
        """
        Check if we are currently debugging.
        """
        return bool(self._pdb_frame)

    @property
    def pdb_session(self):
        """Get current pdb session."""
        return self._pdb_obj

    @pdb_session.setter
    def pdb_session(self, pdb_obj):
        """Register Pdb session to use it later"""
        self._pdb_obj = pdb_obj

    @property
    def _pdb_frame(self):
        """Return current Pdb frame if there is any"""
        if self.pdb_session is not None:
            return self.pdb_session.curframe

    @property
    def _pdb_locals(self):
        """
        Return current Pdb frame locals if available. Otherwise
        return an empty dictionary
        """
        if self._pdb_frame is not None:
            return self._pdb_obj.curframe_locals
        else:
            return {}

    @property
    def user_ns(self):
        """Get the current namespace."""
        if self._pdb_frame is not None:
            return self._pdb_frame.f_globals
        else:
            return self.__user_ns

    @user_ns.setter
    def user_ns(self, namespace):
        """Set user_ns."""
        self.__user_ns = namespace

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None,
                      exception_only=False, running_compiled_code=False):
        """Display the exception that just occurred."""
        super(SpyderShell, self).showtraceback(
            exc_tuple, filename, tb_offset,
            exception_only, running_compiled_code)
        if not exception_only:
            try:
                etype, value, tb = self._get_exc_info(exc_tuple)
                stack = traceback.extract_tb(tb.tb_next)
                for f_summary, f in zip(
                        stack, traceback.walk_tb(tb.tb_next)):
                    f_summary.locals = self.kernel.get_namespace_view(
                        frame=f[0])
                self.kernel.frontend_call(blocking=False).show_traceback(
                    etype, value, stack)
            except Exception:
                return
