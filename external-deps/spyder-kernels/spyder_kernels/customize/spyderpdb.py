# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""Spyder debugger."""

import ast
import bdb
import logging
import os
import sys
import traceback
import threading
from collections import namedtuple

from IPython.core.autocall import ZMQExitAutocall
from IPython.core.debugger import Pdb as ipyPdb
from IPython.core.getipython import get_ipython

from spyder_kernels.comms.frontendcomm import CommError, frontend_request
from spyder_kernels.customize.utils import path_is_library, capture_last_Expr
from spyder_kernels.py3compat import (
    TimeoutError, PY2, _print, isidentifier, PY3, input)

if not PY2:
    from IPython.core.inputtransformer2 import TransformerManager
    import builtins
    basestring = (str,)
else:
    import __builtin__ as builtins
    from IPython.core.inputsplitter import IPythonInputSplitter as TransformerManager


logger = logging.getLogger(__name__)


class DebugWrapper(object):
    """
    Notifies the frontend when debugging starts/stops
    """
    def __init__(self, pdb_obj):
        self.pdb_obj = pdb_obj

    def __enter__(self):
        """
        Debugging starts.
        """
        self.pdb_obj._frontend_notified = True
        try:
            frontend_request(blocking=True).set_debug_state(True)
        except (CommError, TimeoutError):
            logger.debug("Could not send debugging state to the frontend.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Debugging ends.
        """
        self.pdb_obj._frontend_notified = False
        try:
            frontend_request(blocking=True).set_debug_state(False)
        except (CommError, TimeoutError):
            logger.debug("Could not send debugging state to the frontend.")


class SpyderPdb(ipyPdb, object):  # Inherits `object` to call super() in PY2
    """
    Extends Pdb to add features:

     - Process IPython magics.
     - Accepts multiline input.
     - Better interrupt signal handling.
     - Option to skip libraries while stepping.
     - Add completion to non-command code.
    """

    send_initial_notification = True
    starting = True

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 skip=None, nosigint=False):
        """Init Pdb."""
        self.curframe_locals = None
        # Only set to true when calling debugfile
        self.continue_if_has_breakpoints = False
        self.pdb_ignore_lib = False
        self.pdb_execute_events = False
        self.pdb_use_exclamation_mark = False
        self._exclamation_warning_printed = False
        self.pdb_stop_first_line = True
        self._disable_next_stack_entry = False
        super(SpyderPdb, self).__init__()
        self._pdb_breaking = False
        self._frontend_notified = False

        # content of tuple: (filename, line number)
        self._previous_step = None

        # Don't report hidden frames for IPython 7.24+. This attribute
        # has no effect in previous versions.
        self.report_skipped = False


        # Keep track of remote filename
        self.remote_filename = None

        # Line received from the frontend
        self._cmd_input_line = None

        # This is not available in IPython 5
        if hasattr(self, '_predicates'):
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
        # Disallow the use of %debug magic in the debugger
        if line.startswith("%debug"):
            self.error("Please don't use '%debug' in the debugger.\n"
                       "For a recursive debugger, use the pdb 'debug'"
                       " command instead")
            return
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
                     get_ipython().events.trigger('pre_execute')

                code_ast = ast.parse(line)

                if line.rstrip()[-1:] == ";":
                    # Supress output with ;
                    capture_last_expression = False
                else:
                    code_ast, capture_last_expression = capture_last_Expr(
                        code_ast, "_spyderpdb_out")

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

                    # Load the locals
                    globals["_spyderpdb_builtins_locals"] = builtins.locals

                    # Save builtins locals in case it is shadowed
                    globals["_spyderpdb_locals"] = locals

                    # Load locals if they have a valid name
                    # In comprehensions, locals could contain ".0" for example
                    code += [indent + "{k} = _spyderpdb_locals['{k}']".format(
                        k=k) for k in locals if isidentifier(k)]


                    # Update the locals
                    code += [indent + "_spyderpdb_locals.update("
                             "_spyderpdb_builtins_locals())"]

                    # Run the function
                    code += ["_spyderpdb_code()"]

                    # Cleanup
                    code += [
                        "del _spyderpdb_code",
                        "del _spyderpdb_locals",
                        "del _spyderpdb_builtins_locals"
                    ]

                    # Parse the function
                    fun_ast = ast.parse('\n'.join(code) + '\n')

                    # Inject code_ast in the function before the locals update
                    fun_ast.body[0].body = (
                        fun_ast.body[0].body[:-1]  # The locals
                        + code_ast.body  # Code to run
                        + fun_ast.body[0].body[-1:]  # Locals update
                    )
                    code_ast = fun_ast

                exec(compile(code_ast, "<stdin>", "exec"), globals)

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
                     get_ipython().events.trigger('post_execute')
                sys.stdout = save_stdout
                sys.stdin = save_stdin
                sys.displayhook = save_displayhook
        except BaseException:
            if PY2:
                t, v = sys.exc_info()[:2]
                if type(t) == type(''):
                    exc_type_name = t
                else: exc_type_name = t.__name__
                print >>self.stdout, '***', exc_type_name + ':', v
            else:
                exc_info = sys.exc_info()[:2]
                self.error(
                    traceback.format_exception_only(*exc_info)[-1].strip())

    # --- Methods overriden for signal handling
    def sigint_handler(self, signum, frame):
        """
        Handle a sigint signal. Break on the frame above this one.

        This method is not present in python2 so this won't be called there.
        """
        if self.allow_kbdint:
            raise KeyboardInterrupt
        self.message("\nProgram interrupted. (Use 'cont' to resume).")
        # avoid stopping in set_trace
        sys.settrace(None)
        self._pdb_breaking = True
        self.set_step()
        self.set_trace(sys._getframe())

    def interaction(self, frame, traceback):
        """
        Called when a user interaction is required.

        If this is from sigint, break on the upper frame.
        If the frame is in spydercustomize.py, quit.
        Notifies spyder and print current code.
        """
        if self._pdb_breaking:
            self._pdb_breaking = False
            if frame and frame.f_back:
                return self.interaction(frame.f_back, traceback)

        # This is necessary to handle chained exceptions in Pdb, support for
        # which was added in IPython 8.15 and will be the default in Python
        # 3.13 (see ipython/ipython#14146).
        if isinstance(traceback, BaseException):
            _chained_exceptions, tb = self._get_tb_and_exceptions(traceback)

            with self._hold_exceptions(_chained_exceptions):
                self.interaction(frame, tb)

            return

        self.setup(frame, traceback)
        self.print_stack_entry(self.stack[self.curindex])

        if self._frontend_notified:
            self._cmdloop()
        else:
            with DebugWrapper(self):
                self._cmdloop()

        self.forget()

    def print_stack_entry(self, frame_lineno, prompt_prefix='\n-> ',
                          context=None):
        """Disable printing stack entry if requested."""
        if self._disable_next_stack_entry:
            self._disable_next_stack_entry = False
            return
        return super(SpyderPdb, self).print_stack_entry(
            frame_lineno, prompt_prefix, context)

    # --- Methods overriden for skipping libraries
    def stop_here(self, frame):
        """Check if pdb should stop here."""
        if (frame is not None
                and "__tracebackhide__" in frame.f_locals
                and frame.f_locals["__tracebackhide__"] == "__pdb_exit__"):
            self.onecmd('exit')
            return False

        if not super(SpyderPdb, self).stop_here(frame):
            return False
        filename = frame.f_code.co_filename
        if filename.startswith('<'):
            # This is not a file
            return True
        if self.pdb_ignore_lib and path_is_library(filename):
            return False
        return True

    def do_where(self, arg):
        """w(here)
        Print a stack trace, with the most recent frame at the bottom.
        An arrow indicates the "current frame", which determines the
        context of most commands. 'bt' is an alias for this command.

        Take a number as argument as an (optional) number of context line to
        print"""
        super(SpyderPdb, self).do_where(arg)
        try:
            frontend_request(blocking=False).do_where()
        except (CommError, TimeoutError):
            logger.debug("Could not send where request to the frontend.")

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
            return isidentifier(text.replace('.', ''))

        while text and not is_name_or_composed(text):
            text = text[1:]
            begidx += 1

        matches = []
        if compfunc:
            matches = compfunc(text, line, begidx, endidx)

        cursor_start = cursor_pos - len(text)

        if ipython_do_complete:
            kernel = get_ipython().kernel
            # Make complete call with current frame
            if self.curframe:
                if self.curframe_locals:
                    Frame = namedtuple("Frame", ["f_locals", "f_globals"])
                    frame = Frame(self.curframe_locals,
                                  self.curframe.f_globals)
                else:
                    frame = self.curframe
                kernel.shell.set_completer_frame(frame)
            result = kernel._do_complete(code, cursor_pos)
            # Reset frame
            kernel.shell.set_completer_frame()
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
                return isidentifier(text.replace('.', ''))

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

        kernel = get_ipython().kernel
        # Make complete call with current frame
        if self.curframe:
            if self.curframe_locals:
                Frame = namedtuple("Frame", ["f_locals", "f_globals"])
                frame = Frame(self.curframe_locals,
                              self.curframe.f_globals)
            else:
                frame = self.curframe
            kernel.shell.set_completer_frame(frame)
        result = kernel._do_complete(code, cursor_pos)
        # Reset frame
        kernel.shell.set_completer_frame()
        return result

    # --- Methods overriden by us for Spyder integration
    def postloop(self):
        # postloop() is called when the debugger’s input prompt exists. Reset
        # _previous_step so that publish_pdb_state() actually notifies Spyder
        # about a changed frame the next the input prompt is entered again.
        self._previous_step = None

    def preloop(self):
        """Ask Spyder for breakpoints before the first prompt is created."""
        try:
            pdb_settings = frontend_request(blocking=True).get_pdb_settings()
            self.pdb_ignore_lib = pdb_settings['pdb_ignore_lib']
            self.pdb_execute_events = pdb_settings['pdb_execute_events']
            self.pdb_use_exclamation_mark = pdb_settings[
                'pdb_use_exclamation_mark']
            self.pdb_stop_first_line = pdb_settings['pdb_stop_first_line']
            if self.starting:
                self.set_spyder_breakpoints(pdb_settings['breakpoints'])
            if self.send_initial_notification:
                self.publish_pdb_state()
        except (CommError, TimeoutError):
            logger.debug("Could not get breakpoints from the frontend.")
        super(SpyderPdb, self).preloop()

    def set_continue(self):
        """
        Stop only at breakpoints or when finished.

        Reimplemented to avoid stepping out of debugging if there are no
        breakpoints. We could add more later.
        """
        # Don't stop except at breakpoints or when finished
        self._set_stopinfo(self.botframe, None, -1)

    def reset(self):
        """
        Register Pdb session after reset.
        """
        super(SpyderPdb, self).reset()
        get_ipython().pdb_session = self

    def do_debug(self, arg):
        """
        Debug code

        Enter a recursive debugger that steps through the code
        argument (which is an arbitrary expression or statement to be
        executed in the current environment).
        """
        try:
            super(SpyderPdb, self).do_debug(arg)
        except Exception:
            if PY2:
                t, v = sys.exc_info()[:2]
                if type(t) == type(''):
                    exc_type_name = t
                else: exc_type_name = t.__name__
                print >>self.stdout, '***', exc_type_name + ':', v
            else:
                exc_info = sys.exc_info()[:2]
                self.error(
                    traceback.format_exception_only(*exc_info)[-1].strip())
        get_ipython().pdb_session = self

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
        while True:
            try:
                # keyboard interrupts allow for an easy way to cancel
                # the current command, so allow them during interactive input
                self.allow_kbdint = True
                self.cmdloop()
                self.allow_kbdint = False
                break
            except KeyboardInterrupt:
                _print("--KeyboardInterrupt--\n"
                       "For copying text while debugging, use Ctrl+Shift+C",
                       file=self.stdout)


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
        kernel = get_ipython().kernel
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
        kernel.frontend_call().pdb_input(prompt)

        # Allow GUI event loop to update
        if PY3:
            is_main_thread = (
                threading.current_thread() is threading.main_thread())
        else:
            is_main_thread = isinstance(
                threading.current_thread(), threading._MainThread)

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
        self.publish_pdb_state()
        return super(SpyderPdb, self).postcmd(stop, line)

    if PY2:
        def break_here(self, frame):
            """
            Breakpoints don't work for files with non-ascii chars in Python 2

            Fixes Issue 1484
            """
            from bdb import effective
            filename = self.canonic(frame.f_code.co_filename)
            try:
                filename = unicode(filename, "utf-8")
            except TypeError:
                pass
            if filename not in self.breaks:
                return False
            lineno = frame.f_lineno
            if lineno not in self.breaks[filename]:
                # The line itself has no breakpoint, but maybe the line is the
                # first line of a function with breakpoint set by function name
                lineno = frame.f_code.co_firstlineno
                if lineno not in self.breaks[filename]:
                    return False

            # flag says ok to delete temp. bp
            (bp, flag) = effective(filename, lineno, frame)
            if bp:
                self.currentbp = bp.number
                if (flag and bp.temporary):
                    self.do_clear(str(bp.number))
                return True
            else:
                return False

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

        # Jump to first breakpoint.
        # Fixes issue 2034
        if self.starting:
            # Only run this after a Pdb session is created
            self.starting = False

            # Get all breakpoints for the file we're going to debug
            frame = self.curframe
            if not frame:
                # We are not debugging, return. Solves #10290
                return
            lineno = frame.f_lineno
            breaks = self.get_file_breaks(frame.f_code.co_filename)

            # Do 'continue' if the first breakpoint is *not* placed
            # where the debugger is going to land.
            # Fixes issue 4681
            if self.pdb_stop_first_line:
                do_continue = (
                    self.continue_if_has_breakpoints
                    and breaks
                    and lineno < breaks[0])
            else:
                # The breakpoint could be in another file.
                do_continue = (
                    self.continue_if_has_breakpoints
                    and not (breaks and lineno >= breaks[0]))

            if do_continue:
                try:
                    if self.pdb_use_exclamation_mark:
                        cont_cmd = '!continue'
                    else:
                        cont_cmd = 'continue'
                    frontend_request(blocking=False).pdb_execute(cont_cmd)
                except (CommError, TimeoutError):
                    logger.debug(
                        "Could not send a Pdb continue call to the frontend.")

    def publish_pdb_state(self):
        """
        Send debugger state (frame position) to the frontend.

        The state is only sent if it has changed since the last update.
        """

        frame = self.curframe
        if frame is None:
            self._previous_step = None
            return

        # Get filename and line number of the current frame
        fname = self.canonic(frame.f_code.co_filename)
        if PY2:
            try:
                fname = unicode(fname, "utf-8")
            except TypeError:
                pass
        if fname == self.mainpyfile and self.remote_filename is not None:
            fname = self.remote_filename
        lineno = frame.f_lineno

        if self._previous_step == (fname, lineno):
            return

        # Set step of the current frame (if any)
        step = {}
        self._previous_step = None
        if isinstance(fname, basestring) and isinstance(lineno, int):
            step = dict(fname=fname, lineno=lineno)
            self._previous_step = (fname, lineno)

        try:
            frontend_request(blocking=False).pdb_state(dict(step=step))
        except (CommError, TimeoutError):
            logger.debug("Could not send Pdb state to the frontend.")

    def run(self, cmd, globals=None, locals=None):
        """Debug a statement executed via the exec() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        self.starting = True
        with DebugWrapper(self):
            super(SpyderPdb, self).run(cmd, globals, locals)

    def runeval(self, expr, globals=None, locals=None):
        """Debug an expression executed via the eval() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        self.starting = True
        with DebugWrapper(self):
            super(SpyderPdb, self).runeval(expr, globals, locals)

    def runcall(self, *args, **kwds):
        """Debug a single function call.

        Return the result of the function call.
        """
        self.starting = True
        with DebugWrapper(self):
            super(SpyderPdb, self).runcall(*args, **kwds)

    def enter_recursive_debugger(self, code, filename,
                                 continue_if_has_breakpoints):
        """
        Enter debugger recursively.
        """
        sys.settrace(None)
        globals = self.curframe.f_globals
        locals = self.curframe_locals
        # Create child debugger
        debugger = SpyderPdb(
            completekey=self.completekey,
            stdin=self.stdin, stdout=self.stdout)
        debugger.use_rawinput = self.use_rawinput
        debugger.prompt = "(%s) " % self.prompt.strip()

        debugger.set_remote_filename(filename)
        debugger.continue_if_has_breakpoints = continue_if_has_breakpoints

        # Enter recursive debugger
        sys.call_tracing(debugger.run, (code, globals, locals))
        # Reset parent debugger
        sys.settrace(self.trace_dispatch)
        self.lastcmd = debugger.lastcmd
        get_ipython().pdb_session = self

        # Reset _previous_step so that publish_pdb_state() called from within
        # postcmd() notifies Spyder about a changed debugger position. The reset
        # is required because the recursive debugger might change the position,
        # but the parent debugger (self) is not aware of this.
        self._previous_step = None

    def set_remote_filename(self, filename):
        """Set remote filename to signal Spyder on mainpyfile."""
        self.remote_filename = filename
        self.mainpyfile = self.canonic(filename)
        self._wait_for_mainpyfile = True


def get_new_debugger(filename, continue_if_has_breakpoints):
    """Get a new debugger."""
    debugger = SpyderPdb()
    debugger.set_remote_filename(filename)
    debugger.continue_if_has_breakpoints = continue_if_has_breakpoints
    return debugger
