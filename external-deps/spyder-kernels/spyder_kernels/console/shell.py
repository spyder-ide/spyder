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
import logging
import os
import signal
import sys
import traceback
from _thread import interrupt_main

# Third-party imports
from ipykernel.zmqshell import ZMQInteractiveShell

# Local imports
import spyder_kernels
from spyder_kernels.customize.spyderpdb import SpyderPdb
from spyder_kernels.comms.frontendcomm import CommError
from spyder_kernels.utils.mpl import automatic_backend


logger = logging.getLogger(__name__)


class SpyderShell(ZMQInteractiveShell):
    """Spyder shell."""

    PDB_CONF_KEYS = [
        'pdb_ignore_lib',
        'pdb_execute_events',
        'pdb_use_exclamation_mark',
        'pdb_stop_first_line',
        'breakpoints',
        'pdb_publish_stack'
    ]

    def __init__(self, *args, **kwargs):
        # Create _pdb_obj_stack before __init__
        self._pdb_obj_stack = []
        self._request_pdb_stop = False
        self._pdb_conf = {}
        super(SpyderShell, self).__init__(*args, **kwargs)
        self._allow_kbdint = False
        self.register_debugger_sigint()

        # Used for checking correct version by spyder
        self._spyder_kernels_version = (
            spyder_kernels.__version__,
            sys.executable
        )

        # register post_execute
        self.events.register('post_execute', self.do_post_execute)

    def ask_exit(self):
        """Engage the exit actions."""
        if self.active_eventloop != "inline":
            # Some eventloops prevent the kernel from shutting down
            self.enable_gui('inline')
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

    def enable_matplotlib(self, gui=None):
        """Enable matplotlib."""
        if gui is None or gui.lower() == "auto":
            gui = automatic_backend()
        gui, backend = super(SpyderShell, self).enable_matplotlib(gui)
        try:
            self.kernel.frontend_call(blocking=False).update_matplotlib_gui(gui)
        except Exception:
            pass
        return gui, backend

    # --- For Pdb namespace integration
    def set_pdb_configuration(self, pdb_conf):
        """
        Set Pdb configuration.

        Parameters
        ----------
        pdb_conf: dict
            Dictionary containing the configuration. Its keys are part of the
            `PDB_CONF_KEYS` class constant.
        """
        for key in self.PDB_CONF_KEYS:
            if key in pdb_conf:
                self._pdb_conf[key] = pdb_conf[key]
                if self.pdb_session:
                    setattr(self.pdb_session, key, pdb_conf[key])

    def get_local_scope(self, stack_depth):
        """Get local scope at given frame depth."""
        frame = sys._getframe(stack_depth + 1)
        if self._pdb_frame is frame:
            # Avoid calling f_locals on _pdb_frame
            return self.pdb_session.curframe_locals
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
        if len(self._pdb_obj_stack) > 0:
            return self._pdb_obj_stack[-1]
        return None

    def add_pdb_session(self, pdb_obj):
        """Add a pdb object to the stack."""
        if self.pdb_session == pdb_obj:
            # Already added
            return
        self._pdb_obj_stack.append(pdb_obj)

        # Set config to pdb obj
        self.set_pdb_configuration(self._pdb_conf)

        try:
            self.kernel.frontend_call(blocking=False).set_debug_state(
                len(self._pdb_obj_stack))
        except (CommError, TimeoutError):
            logger.debug("Could not send debugging state to the frontend.")

    def remove_pdb_session(self, pdb_obj):
        """Remove a pdb object from the stack."""
        if self.pdb_session != pdb_obj:
            # Already removed
            return
        self._pdb_obj_stack.pop()

        if self.pdb_session:
            # Set config to newly active pdb obj
            self.set_pdb_configuration(self._pdb_conf)

        try:
            self.kernel.frontend_call(blocking=False).set_debug_state(
                len(self._pdb_obj_stack))
        except (CommError, TimeoutError):
            logger.debug("Could not send debugging state to the frontend.")

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
            return self.pdb_session.curframe_locals
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

    def register_debugger_sigint(self):
        """Register sigint handler."""
        signal.signal(signal.SIGINT, self.spyderkernel_sigint_handler)

    def raise_interrupt_signal(self):
        """Raise interrupt signal."""
        if os.name == "nt":
            # Check if signal handler is callable to avoid
            # 'int not callable' error (Python issue #23395)
            if callable(signal.getsignal(signal.SIGINT)):
                interrupt_main()
            else:
                self.kernel.log.error(
                    "Interrupt message not supported on Windows")
        else:
            self.kernel._send_interupt_children()

    def request_pdb_stop(self):
        """Request pdb to stop at the next possible position."""
        pdb_session = self.pdb_session
        if pdb_session:
            if pdb_session.interrupting:
                # interrupt already requested, wait
                return
            # trace_dispatch is active, stop at the next possible position
            pdb_session.interrupt()
        elif (self.spyderkernel_sigint_handler
              == signal.getsignal(signal.SIGINT)):
            # Use spyderkernel_sigint_handler
            self._request_pdb_stop = True
            self.raise_interrupt_signal()
        else:
            logger.debug(
                "Can not signal main thread to stop as SIGINT "
                "handler was replaced and the debugger is not active. "
                "The current handler is: " +
                repr(signal.getsignal(signal.SIGINT))
            )

    def spyderkernel_sigint_handler(self, signum, frame):
        """SIGINT handler."""
        if self._request_pdb_stop:
            # SIGINT called from request_pdb_stop
            self._request_pdb_stop = False
            debugger = SpyderPdb()
            debugger.interrupt()
            debugger.set_trace(frame)
            return

        pdb_session = self.pdb_session
        if pdb_session:
            # SIGINT called while debugging
            if pdb_session.allow_kbdint:
                raise KeyboardInterrupt
            if pdb_session.interrupting:
                # second call to interrupt, raise
                raise KeyboardInterrupt
            pdb_session.interrupt()
            return

        if self._allow_kbdint:
            # Do not raise KeyboardInterrupt in the middle of ipython code
            raise KeyboardInterrupt

    async def run_code(self, *args, **kwargs):
        """Execute a code object."""
        try:
            try:
                self._allow_kbdint = True
                return await super().run_code(*args, **kwargs)
            finally:
                self._allow_kbdint = False
        except KeyboardInterrupt:
            self.showtraceback()

    def pdb_input_reply(self, line, echo_stack_entry=True):
        """Get a pdb command from the frontend."""
        debugger = self.pdb_session
        if not debugger:
            return
        debugger._disable_next_stack_entry = not echo_stack_entry
        debugger._cmd_input_line = line
        # Interrupts eventloop if needed
        self.kernel.interrupt_eventloop()

    def do_post_execute(self):
        """Flush __std*__ after execution."""
        # Flush C standard streams.
        sys.__stderr__.flush()
        sys.__stdout__.flush()
