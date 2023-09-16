# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""Spyder debugger."""

import ast
import bdb
import builtins
from contextlib import contextmanager
import logging
import os
import sys
import traceback
import threading
from collections import namedtuple
from functools import lru_cache

from IPython.core.autocall import ZMQExitAutocall
from IPython.core.debugger import Pdb as ipyPdb
from IPython.core.inputtransformer2 import TransformerManager

import spyder_kernels
from spyder_kernels.comms.frontendcomm import CommError, frontend_request
from spyder_kernels.customize.utils import path_is_library, capture_last_Expr


logger = logging.getLogger(__name__)


class DebugWrapper:
    """
    Notifies the frontend when debugging starts/stops
    """
    def __init__(self, pdb_obj):
        self.pdb_obj = pdb_obj
        self._cleanup = True

    def __enter__(self):
        """
        Debugging starts.
        """
        shell = self.pdb_obj.shell
        if shell.pdb_session == self.pdb_obj:
            self._cleanup = False
        else:
            shell.add_pdb_session(self.pdb_obj)
            self._cleanup = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Debugging ends.
        """
        if self._cleanup:
            self.pdb_obj.shell.remove_pdb_session(self.pdb_obj)


class SpyderPdb(ipyPdb):
    """
    Extends Pdb to add features:

     - Process IPython magics.
     - Accepts multiline input.
     - Better interrupt signal handling.
     - Option to skip libraries while stepping.
     - Add completion to non-command code.
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 skip=None, nosigint=False):
        """Init Pdb."""
        self.curframe_locals = None
        # Only set to true when calling debugfile
        self.continue_if_has_breakpoints = False
        self.pdb_ignore_lib = False
        self.pdb_execute_events = False
        self.pdb_use_exclamation_mark = False
        self.pdb_publish_stack = False
        self._exclamation_warning_printed = False
        self.pdb_stop_first_line = True
        self._disable_next_stack_entry = False
        super(SpyderPdb, self).__init__()

        # content of tuple: (filename, line number)
        self._previous_step = None

        # Don't report hidden frames for IPython 7.24+. This attribute
        # has no effect in previous versions.
        self.report_skipped = False

        # Keep track of remote filename
        self.remote_filename = None

        # Needed to know which namespace to show (user or current frame)
        # Line received from the frontend
        self._cmd_input_line = None

        # Disable sigint so we can do it ourselves
        self.nosigint = True

        # Keep track of interrupting state to avoid several interruptions
        self.interrupting = False

        # Should the frontend force go to the current line?
        self._request_where = False

        # Turn off IPython's debugger skip funcionality by default because
        # it makes our debugger quite slow. It's also important to remark
        # that this functionality doesn't do anything on its own. Users
        # need to mark what frames they want to skip for it to be useful.
        # So, we hope that knowledgeable users will find that they need to
        # enable it in Spyder.
        # Fixes spyder-ide/spyder#20639.
        self._predicates["debuggerskip"] = False

    # --- Methods overriden for code execution
    def print_exclamation_warning(self):
        """Print pdb warning for exclamation mark."""
        if not self._exclamation_warning_printed:
            print("Warning: The exclamation mark option is enabled. "
                  "Please use '!' as a prefix for Pdb commands.")
            self._exclamation_warning_printed = True

    def default(self, line):
        """
        Default way of running pdb statment.
        """
        execute_events = self.pdb_execute_events
        if line[:1] == '!':
            line = line[1:]
        elif self.pdb_use_exclamation_mark:
            self.print_exclamation_warning()
            self.error("Unknown command '" + line.split()[0] + "'")
            return

        # Replace %debug magic in the debugger
        if line.startswith("%debug") or line.startswith("%%debug"):
            cmd, arg, _ = self.parseline(line.lstrip("%"))
            if cmd == "debug":
                return self.do_debug(arg)

        locals = self.curframe_locals
        globals = self.curframe.f_globals

        if self.pdb_use_exclamation_mark:
            # Find pdb commands executed without !
            cmd, arg, line = self.parseline(line)
            if cmd:
                cmd_in_namespace = (
                    cmd in globals
                    or cmd in locals
                    or cmd in builtins.__dict__
                )
                # Special case for quit and exit
                if cmd in ("quit", "exit"):
                    if cmd in globals and isinstance(
                            globals[cmd], ZMQExitAutocall):
                        # Use the pdb call
                        cmd_in_namespace = False
                cmd_func = getattr(self, 'do_' + cmd, None)
                is_pdb_cmd = cmd_func is not None
                # Look for assignment
                is_assignment = False
                try:
                    for node in ast.walk(ast.parse(line)):
                        if isinstance(node, ast.Assign):
                            is_assignment = True
                            break
                except SyntaxError:
                    pass

                if is_pdb_cmd:
                    if not cmd_in_namespace and not is_assignment:
                        # This is a pdb command without the '!' prefix.
                        self.lastcmd = line
                        return cmd_func(arg)
                    else:
                        # The pdb command is masked by something
                        self.print_exclamation_warning()
        try:
            line = TransformerManager().transform_cell(line)
            save_stdout = sys.stdout
            save_stdin = sys.stdin
            save_displayhook = sys.displayhook
            try:
                sys.stdin = self.stdin
                sys.stdout = self.stdout
                sys.displayhook = self.displayhook
                if execute_events:
                     self.shell.events.trigger('pre_execute')

                code_ast = ast.parse(line)

                if line.rstrip()[-1:] == ";":
                    # Supress output with ;
                    capture_last_expression = False
                else:
                    code_ast, capture_last_expression = capture_last_Expr(
                        code_ast, "_spyderpdb_out")

                globals["__spyder_builtins__"] = builtins

                if locals is not globals:
                    # Mitigates a behaviour of CPython that makes it difficult
                    # to work with exec and the local namespace
                    # See:
                    #  - https://bugs.python.org/issue41918
                    #  - https://bugs.python.org/issue46153
                    #  - https://bugs.python.org/issue21161
                    #  - spyder-ide/spyder#13909
                    #  - spyder-ide/spyder-kernels#345
                    #
                    # The idea here is that the best way to emulate being in a
                    # function is to actually execute the code in a function.
                    # A function called `_spyderpdb_code` is created and
                    # called. It will first load the locals, execute the code,
                    # and then update the locals.
                    #
                    # One limitation of this approach is that locals() is only
                    # a copy of the curframe locals. This means that closures
                    # for example are early binding instead of late binding.

                    # Create a function
                    indent = "    "
                    code = ["def _spyderpdb_code():"]

                    # Add locals in globals
                    # If the debugger is recursive, the globals could already
                    # have a _spyderpdb_locals as it might be shared between
                    # levels
                    if "_spyderpdb_locals" in globals:
                        globals["_spyderpdb_locals"].append(locals)
                    else:
                        globals["_spyderpdb_locals"] = [locals]

                    # Load locals if they have a valid name
                    # In comprehensions, locals could contain ".0" for example
                    code += [indent + "{k} = _spyderpdb_locals[-1]['{k}']".format(
                        k=k) for k in locals if k.isidentifier()]

                    # The code comes here

                    # Update the locals
                    code += [indent + "_spyderpdb_locals[-1].update("
                             "__spyder_builtins__.locals())"]

                    # Run the function
                    code += ["_spyderpdb_code()"]

                    # Parse the function
                    fun_ast = ast.parse('\n'.join(code) + '\n')

                    # Inject code_ast in the function before the locals update
                    fun_ast.body[0].body = (
                        fun_ast.body[0].body[:-1]  # The locals
                        + code_ast.body  # Code to run
                        + fun_ast.body[0].body[-1:]  # Locals update
                    )
                    code_ast = fun_ast

                try:
                    exec(compile(code_ast, "<stdin>", "exec"), globals)
                finally:
                    if locals is not globals:
                        # CLeanup code
                        globals.pop("_spyderpdb_code", None)
                        if len(globals["_spyderpdb_locals"]) > 1:
                            del globals["_spyderpdb_locals"][-1]
                        else:
                            del globals["_spyderpdb_locals"]
                        

                if capture_last_expression:
                    out = globals.pop("_spyderpdb_out", None)
                    if out is not None:
                        sys.stdout.flush()
                        sys.stderr.flush()
                        try:
                            frontend_request(blocking=False).show_pdb_output(
                                repr(out))
                        except (CommError, TimeoutError):
                            # Fallback
                            print("pdb out> ", repr(out))

            finally:
                if execute_events:
                     self.shell.events.trigger('post_execute')
                sys.stdout = save_stdout
                sys.stdin = save_stdin
                sys.displayhook = save_displayhook
        except BaseException:
            exc_info = sys.exc_info()[:2]
            self.error(
                traceback.format_exception_only(*exc_info)[-1].strip())

    # --- Methods overriden for signal handling
    def interrupt(self):
        """Stop debugger on next instruction."""
        self.interrupting = True
        self.message("\nProgram interrupted. (Use 'cont' to resume).")
        self.set_step()

    def set_trace(self, frame=None):
        """Register that debugger is tracing."""
        self.shell.add_pdb_session(self)
        super(SpyderPdb, self).set_trace(frame)

    def set_quit(self):
        """Register that debugger is not tracing."""
        self.shell.remove_pdb_session(self)
        super(SpyderPdb, self).set_quit()

    def interaction(self, frame, traceback):
        """
        Called when a user interaction is required.
        """
        with DebugWrapper(self):
            # Wrapp in case the frontend was not notified, e.g. postmortem
            return super(SpyderPdb, self).interaction(
                frame, traceback)

    def print_stack_entry(self, *args, **kwargs):
        """Disable printing stack entry if requested."""
        if self._disable_next_stack_entry:
            self._disable_next_stack_entry = False
            return
        return super().print_stack_entry(*args, **kwargs)

    # --- Methods overriden for skipping libraries
    def stop_here(self, frame):
        """Check if pdb should stop here."""
        # Never stop if we are continuing unless there is a breakpoint
        if self.stopframe == self.botframe and self.stoplineno == -1:
            return False
        if self.continue_if_has_breakpoints and self.should_continue(frame):
            self.set_continue()
            return False
        if (
            frame is not None
            and "__tracebackhide__" in frame.f_locals
            and frame.f_locals["__tracebackhide__"] == "__pdb_exit__"
        ):
            self.onecmd('exit')
            return False

        if not super().stop_here(frame):
            return False
        if frame is self.stopframe:
            return True
        filename = frame.f_code.co_filename
        if filename.startswith('<'):
            # This is not a file
            return True
        if self.pdb_ignore_lib and path_is_library(filename):
            return False
        if self.skip_hidden and os.path.dirname(spyder_kernels.__file__) in filename:
            # This is spyder-kernels internals
            return False
        return True
    
    def should_continue(self, frame):
        """
        Jump to first breakpoint if needed.

        Fixes spyder-ide/spyder#2034
        """

        if not self.continue_if_has_breakpoints:
            # This was disabled
            return False
        self.continue_if_has_breakpoints = False

        # Get all breakpoints for the file we're going to debug
        if not frame:
            # We are not debugging, return. Solves spyder-ide/spyder#10290
            return False

        lineno = frame.f_lineno
        breaks = self.get_file_breaks(frame.f_code.co_filename)

        # Do 'continue' if the first breakpoint is *not* placed
        # where the debugger is going to land.
        # Fixes spyder-ide/spyder#4681
        if self.pdb_stop_first_line:
            return breaks and lineno < breaks[0]

        # The breakpoint could be in another file.
        return not (breaks and lineno >= breaks[0])

    def do_where(self, arg):
        """w(here)
        Print a stack trace, with the most recent frame at the bottom.
        An arrow indicates the "current frame", which determines the
        context of most commands. 'bt' is an alias for this command.

        Take a number as argument as an (optional) number of context line to
        print"""
        self._request_where = True
        return super(SpyderPdb, self).do_where(arg)

    do_w = do_where

    do_bt = do_where

    # --- Method defined by us to respond to ipython complete protocol
    def do_complete(self, code, cursor_pos):
        """
        Respond to a complete request.
        """
        if self.pdb_use_exclamation_mark:
            return self._complete_exclamation(code, cursor_pos)
        else:
            return self._complete_default(code, cursor_pos)

    def _complete_default(self, code, cursor_pos):
        """
        Respond to a complete request if not pdb_use_exclamation_mark.
        """
        if cursor_pos is None:
            cursor_pos = len(code)

        # Get text to complete
        text = code[:cursor_pos].split(' ')[-1]
        # Choose Pdb function to complete, based on cmd.py
        origline = code
        line = origline.lstrip()
        if not line:
            # Nothing to complete
            return
        stripped = len(origline) - len(line)
        begidx = cursor_pos - len(text) - stripped
        endidx = cursor_pos - stripped

        compfunc = None
        ipython_do_complete = True
        if begidx > 0:
            # This could be after a Pdb command
            cmd, args, _ = self.parseline(line)
            if cmd != '':
                try:
                    # Function to complete Pdb command arguments
                    compfunc = getattr(self, 'complete_' + cmd)
                    # Don't call ipython do_complete for commands
                    ipython_do_complete = False
                except AttributeError:
                    pass
        elif line[0] != '!':
            # This could be a Pdb command
            compfunc = self.completenames

        def is_name_or_composed(text):
            if not text or text[0] == '.':
                return False
            # We want to keep value.subvalue
            return text.replace('.', '').isidentifier()

        while text and not is_name_or_composed(text):
            text = text[1:]
            begidx += 1

        matches = []
        if compfunc:
            matches = compfunc(text, line, begidx, endidx)

        cursor_start = cursor_pos - len(text)

        if ipython_do_complete:
            # Make complete call with current frame
            if self.curframe:
                if self.curframe_locals:
                    Frame = namedtuple("Frame", ["f_locals", "f_globals"])
                    frame = Frame(self.curframe_locals,
                                  self.curframe.f_globals)
                else:
                    frame = self.curframe
                self.shell.set_completer_frame(frame)
            result = self.shell.kernel._do_complete(code, cursor_pos)
            # Reset frame
            self.shell.set_completer_frame()
            # If there is no Pdb results to merge, return the result
            if not compfunc:
                return result

            ipy_matches = result['matches']
            # Make sure both match lists start at the same place
            if cursor_start < result['cursor_start']:
                # Fill IPython matches
                missing_txt = code[cursor_start:result['cursor_start']]
                ipy_matches = [missing_txt + m for m in ipy_matches]
            elif result['cursor_start'] < cursor_start:
                # Fill Pdb matches
                missing_txt = code[result['cursor_start']:cursor_start]
                matches = [missing_txt + m for m in matches]
                cursor_start = result['cursor_start']

            # Add Pdb-specific matches
            matches += [match for match in ipy_matches if match not in matches]

        return {'matches': matches,
                'cursor_end': cursor_pos,
                'cursor_start': cursor_start,
                'metadata': {},
                'status': 'ok'}

    def _complete_exclamation(self, code, cursor_pos):
        """
        Respond to a complete request if pdb_use_exclamation_mark.
        """
        if cursor_pos is None:
            cursor_pos = len(code)

        # Get text to complete
        text = code[:cursor_pos].split(' ')[-1]
        # Choose Pdb function to complete, based on cmd.py
        origline = code
        line = origline.lstrip()
        if not line:
            # Nothing to complete
            return
        is_pdb_command = line[0] == '!'
        is_pdb_command_name = False

        stripped = len(origline) - len(line)
        begidx = cursor_pos - len(text) - stripped
        endidx = cursor_pos - stripped

        compfunc = None

        if is_pdb_command:
            line = line[1:]
            begidx -= 1
            endidx -= 1
            if begidx == -1:
                is_pdb_command_name = True
                text = text[1:]
                begidx += 1
                compfunc = self.completenames
            else:
                cmd, args, _ = self.parseline(line)
                if cmd != '':
                    try:
                        # Function to complete Pdb command arguments
                        compfunc = getattr(self, 'complete_' + cmd)
                    except AttributeError:
                        # This command doesn't exist, nothing to complete
                        return
                else:
                    # We don't know this command
                    return

        if not is_pdb_command_name:
            # Remove eg. leading opening parenthesis
            def is_name_or_composed(text):
                if not text or text[0] == '.':
                    return False
                # We want to keep value.subvalue
                return text.replace('.', '').isidentifier()

            while text and not is_name_or_composed(text):
                text = text[1:]
                begidx += 1

        cursor_start = cursor_pos - len(text)
        matches = []
        if is_pdb_command:
            matches = compfunc(text, line, begidx, endidx)
            return {
                'matches': matches,
                'cursor_end': cursor_pos,
                'cursor_start': cursor_start,
                'metadata': {},
                'status': 'ok'
                }

        # Make complete call with current frame
        if self.curframe:
            if self.curframe_locals:
                Frame = namedtuple("Frame", ["f_locals", "f_globals"])
                frame = Frame(self.curframe_locals,
                              self.curframe.f_globals)
            else:
                frame = self.curframe
            self.shell.set_completer_frame(frame)
        result = self.shell.kernel._do_complete(code, cursor_pos)
        # Reset frame
        self.shell.set_completer_frame()
        return result

    # --- Methods overriden by us for Spyder integration
    def postloop(self):
        # postloop() is called when the debugger’s input prompt exists. Reset
        # _previous_step so that get_pdb_state() actually notifies Spyder
        # about a changed frame the next the input prompt is entered again.
        self._previous_step = None

    def set_continue(self):
        """
        Stop only at breakpoints or when finished.

        Reimplemented to avoid stepping out of debugging if there are no
        breakpoints. We could add more later.
        """
        # Don't stop except at breakpoints or when finished
        self._set_stopinfo(self.botframe, None, -1)

    def do_debug(self, arg):
        """
        Debug code

        Enter a recursive debugger that steps through the code
        argument (which is an arbitrary expression or statement to be
        executed in the current environment).
        """
        with self.recursive_debugger() as debugger:
            self.message("Entering recursive debugger")
            try:
                globals = self.curframe.f_globals
                locals = self.curframe_locals
                return sys.call_tracing(debugger.run, (arg, globals, locals))
            except Exception:
                exc_info = sys.exc_info()[:2]
                self.error(
                    traceback.format_exception_only(*exc_info)[-1].strip())
            finally:
                self.message("Leaving recursive debugger")

    @contextmanager
    def recursive_debugger(self):
        """Get a recursive debugger."""
        # Save and restore tracing function
        trace_function = sys.gettrace()
        sys.settrace(None)

        # Create child debugger
        debugger = self.__class__(
            completekey=self.completekey,
            stdin=self.stdin, stdout=self.stdout)
        debugger.prompt = "(%s) " % self.prompt.strip()
        try:
            yield debugger
        finally:
            # Reset parent debugger
            sys.settrace(trace_function)
            self.lastcmd = debugger.lastcmd

            # Reset _previous_step so that get_pdb_state() notifies Spyder about
            # a changed debugger position. The reset is required because the
            # recursive debugger might change the position, but the parent
            # debugger (self) is not aware of this.
            self._previous_step = None

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        # This is useful when debugging in an active interpreter (otherwise,
        # the debugger will stop before reaching the target file)
        if self._wait_for_mainpyfile:
            if (self.mainpyfile != self.canonic(frame.f_code.co_filename)
                    or frame.f_lineno <= 0):
                return
            self._wait_for_mainpyfile = False
        super(SpyderPdb, self).user_return(frame, return_value)

    def _cmdloop(self):
        """Modifies the error text."""
        self.interrupting = False
        while True:
            try:
                # keyboard interrupts allow for an easy way to cancel
                # the current command, so allow them during interactive input
                self.allow_kbdint = True
                self.cmdloop()
                self.allow_kbdint = False
                break
            except KeyboardInterrupt:
                print("--KeyboardInterrupt--\n"
                      "For copying text while debugging, use Ctrl+Shift+C",
                      file=self.stdout)

    @lru_cache
    def canonic(self, filename):
        """Return canonical form of filename."""
        return super().canonic(filename)

    def do_exitdb(self, arg):
        """Exit the debugger"""
        self._set_stopinfo(self.botframe, None, -1)
        sys.settrace(None)
        frame = sys._getframe().f_back
        while frame and frame is not self.botframe:
            del frame.f_trace
            frame = frame.f_back
        return 1

    def cmdloop(self, intro=None):
        """
        Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            if self.cmdqueue:
                line = self.cmdqueue.pop(0)
            else:
                try:
                    line = self.cmd_input(self.prompt)
                except EOFError:
                    line = 'EOF'
            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def cmd_input(self, prompt=''):
        """
        Get input from frontend. Blocks until return
        """
        kernel = self.shell.kernel
        # Only works if the comm is open
        if not kernel.frontend_comm.is_open():
            return input(prompt)

        # Flush output before making the request.
        sys.stderr.flush()
        sys.stdout.flush()
        sys.__stderr__.flush()
        sys.__stdout__.flush()

        # Send the input request.
        self._cmd_input_line = None
        kernel.frontend_call(display_error=True).pdb_input(
            prompt, state=self.get_pdb_state())

        # Allow GUI event loop to update
        is_main_thread = (
            threading.current_thread() is threading.main_thread())

        # Get input by running eventloop
        if is_main_thread and kernel.eventloop:
            while self._cmd_input_line is None:
                eventloop = kernel.eventloop
                # Check if the current backend is Tk on Windows
                # to let GUI update.
                # See spyder-ide/spyder#17523
                if (eventloop and hasattr(kernel, "app_wrapper") and
                        os.name == "nt"):
                    kernel.app_wrapper.app.update()
                elif eventloop:
                    eventloop(kernel)
                else:
                    break

        # Get input by blocking
        if self._cmd_input_line is None:
            kernel.frontend_comm.wait_until(
                lambda: self._cmd_input_line is not None)

        return self._cmd_input_line

    def precmd(self, line):
        """
        Hook method executed just before the command line is
        interpreted, but after the input prompt is generated and issued.

        Here we switch ! and non !
        """
        if not self.pdb_use_exclamation_mark:
            return line
        if not line:
            return line
        if line[0] == '!':
            line = line[1:]
        else:
            line = '!' + line
        return line

    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""
        # Flush in case the command produced output on underlying outputs
        sys.__stderr__.flush()
        sys.__stdout__.flush()
        return stop

    # --- Methods defined by us for Spyder integration
    def set_spyder_breakpoints(self, breakpoints):
        """Set Spyder breakpoints."""
        self.clear_all_breaks()
        # -----Really deleting all breakpoints:
        for bp in bdb.Breakpoint.bpbynumber:
            if bp:
                bp.deleteMe()
        bdb.Breakpoint.next = 1
        bdb.Breakpoint.bplist = {}
        bdb.Breakpoint.bpbynumber = [None]
        # -----
        for fname, data in list(breakpoints.items()):
            for linenumber, condition in data:
                try:
                    self.set_break(self.canonic(fname), linenumber,
                                   cond=condition)
                except ValueError:
                    # Fixes spyder/issues/15546
                    # The file is not readable
                    pass

    breakpoints = property(fset=set_spyder_breakpoints)

    def get_pdb_state(self):
        """
        Send debugger state (frame position) to the frontend.

        The state is only sent if it has changed since the last update.
        """
        state = self.shell.kernel.get_state()

        frame = self.curframe
        if frame is None:
            self._previous_step = None
            return state

        if self._request_where:
            self._request_where = False
            state["do_where"] = True

        # Get filename and line number of the current frame
        fname = self.canonic(frame.f_code.co_filename)
        if fname == self.mainpyfile and self.remote_filename is not None:
            fname = self.remote_filename
        lineno = frame.f_lineno

        if self._previous_step == (fname, lineno):
            # Do not update state if not needed
            return state

        # Set step of the current frame (if any)
        step = {}
        self._previous_step = None
        if isinstance(fname, str) and isinstance(lineno, int):
            step = dict(fname=fname, lineno=lineno)
            self._previous_step = (fname, lineno)

        state['step'] = step

        if self.pdb_publish_stack:
            # Publish Pdb stack so we can update the Debugger plugin on Spyder
            pdb_stack = traceback.StackSummary.extract(self.stack)
            pdb_index = self.curindex

            skip_hidden = getattr(self, 'skip_hidden', False)

            if skip_hidden:
                # Filter out the hidden frames
                hidden = self.hidden_frames(self.stack)
                pdb_stack = [f for f, h in zip(pdb_stack, hidden) if not h]
                # Adjust the index
                pdb_index -= sum([bool(i) for i in hidden[:pdb_index]])

            state['stack'] = (pdb_stack, pdb_index)

        return state

    def run(self, cmd, globals=None, locals=None):
        """Debug a statement executed via the exec() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        with DebugWrapper(self):
            super(SpyderPdb, self).run(cmd, globals, locals)

    def runeval(self, expr, globals=None, locals=None):
        """Debug an expression executed via the eval() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        with DebugWrapper(self):
            super(SpyderPdb, self).runeval(expr, globals, locals)

    def runcall(self, *args, **kwds):
        """Debug a single function call.

        Return the result of the function call.
        """
        with DebugWrapper(self):
            super(SpyderPdb, self).runcall(*args, **kwds)

    def set_remote_filename(self, filename):
        """Set remote filename to signal Spyder on mainpyfile."""
        self.remote_filename = filename
        self.mainpyfile = self.canonic(filename)
        self._wait_for_mainpyfile = True
