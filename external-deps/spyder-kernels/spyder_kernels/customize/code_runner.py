#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Spyder magics related to code execution, debugging, profiling, etc.
"""

# Standard library imports
import ast
import bdb
import builtins
from contextlib import contextmanager
import cProfile
from functools import partial
import io
import logging
import os
import pdb
import tempfile
import shlex
import sys
import time

# Third-party imports
from IPython.core.inputtransformer2 import (
    TransformerManager,
    leading_indent,
    leading_empty_lines,
)
from IPython.core.magic import (
    needs_local_scope,
    no_var_expand,
    line_cell_magic,
    magics_class,
    Magics,
    line_magic,
)
from IPython.core import magic_arguments

# Local imports
from spyder_kernels.comms.frontendcomm import frontend_request, CommError
from spyder_kernels.customize.namespace_manager import NamespaceManager
from spyder_kernels.customize.spyderpdb import SpyderPdb
from spyder_kernels.customize.umr import UserModuleReloader
from spyder_kernels.customize.utils import (
    capture_last_Expr, canonic, create_pathlist, exec_encapsulate_locals
)


# For logging
logger = logging.getLogger(__name__)


def runfile_arguments(func):
    """Decorator to add runfile magic arguments to magic."""
    decorators = [
        magic_arguments.magic_arguments(),
        magic_arguments.argument(
            "filename",
            help="""
            Filename to run
            """,
        ),
        magic_arguments.argument(
            "--args",
            help="""
            Command line arguments (string)
            """,
        ),
        magic_arguments.argument(
            "--wdir",
            const=True,
            nargs="?",
            help="""
            Working directory
            """,
        ),
        magic_arguments.argument(
            "--post-mortem",
            action="store_true",
            help="""
            Enter post-mortem mode on errors
            """,
        ),
        magic_arguments.argument(
            "--current-namespace",
            action="store_true",
            help="""
            Use current namespace
            """,
        ),
        magic_arguments.argument(
            "--namespace",
            help="""
            Namespace to run the file in
            """,
        )
        ]
    for dec in reversed(decorators):
        func = dec(func)
    return func


def runcell_arguments(func):
    """Decorator to add runcell magic arguments to magic."""
    decorators = [
        magic_arguments.magic_arguments(),
        magic_arguments.argument(
            "--name", "-n",
            help="""
            Cell name.
            """,
        ),
        magic_arguments.argument(
            "--index", "-i",
            help="""
            Cell index.
            """,
        ),
        magic_arguments.argument(
            "filename",
            nargs="?",
            help="""
            Filename
            """,
        ),
        magic_arguments.argument(
            "--post-mortem",
            action="store_true",
            default=False,
            help="""
            Enter post-mortem mode on errors
            """,
        )
        ]
    for dec in reversed(decorators):
        func = dec(func)
    return func


@magics_class
class SpyderCodeRunner(Magics):
    """
    Functions and magics related to code execution, debugging, profiling, etc.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.show_global_msg = True
        self.show_invalid_syntax_msg = True
        self.umr = UserModuleReloader(
            namelist=os.environ.get("SPY_UMR_NAMELIST", None),
            shell=self.shell,
        )

    @runfile_arguments
    @needs_local_scope
    @line_magic
    def runfile(self, line, local_ns=None):
        """
        Run a file.
        """
        args, local_ns = self._parse_runfile_argstring(
            self.runfile, line, local_ns)

        return self._exec_file(
            filename=args.filename,
            canonic_filename=args.canonic_filename,
            args=args.args,
            wdir=args.wdir,
            post_mortem=args.post_mortem,
            current_namespace=args.current_namespace,
            context_globals=args.namespace,
            context_locals=local_ns,
        )

    @runfile_arguments
    @needs_local_scope
    @line_magic
    def debugfile(self, line, local_ns=None):
        """
        Debug a file.
        """
        args, local_ns = self._parse_runfile_argstring(
            self.debugfile, line, local_ns)

        with self._debugger_exec(args.canonic_filename, True) as debug_exec:
            self._exec_file(
                filename=args.filename,
                canonic_filename=args.canonic_filename,
                args=args.args,
                wdir=args.wdir,
                current_namespace=args.current_namespace,
                exec_fun=debug_exec,
                post_mortem=args.post_mortem,
                context_globals=args.namespace,
                context_locals=local_ns,
            )

    @runfile_arguments
    @needs_local_scope
    @line_magic
    def profilefile(self, line, local_ns=None):
        """Profile a file."""
        args, local_ns = self._parse_runfile_argstring(
            self.profilefile, line, local_ns)

        with self._profile_exec() as prof_exec:
            self._exec_file(
                filename=args.filename,
                canonic_filename=args.canonic_filename,
                wdir=args.wdir,
                current_namespace=args.current_namespace,
                args=args.args,
                exec_fun=prof_exec,
                post_mortem=args.post_mortem,
                context_globals=args.namespace,
                context_locals=local_ns,
            )

    @runcell_arguments
    @needs_local_scope
    @line_magic
    def runcell(self, line, local_ns=None):
        """
        Run a code cell from an editor.
        """
        args = self._parse_runcell_argstring(self.runcell, line)

        return self._exec_cell(
            cell_id=args.cell_id,
            filename=args.filename,
            canonic_filename=args.canonic_filename,
            post_mortem=args.post_mortem,
            context_globals=self.shell.user_ns,
            context_locals=local_ns,
        )

    @runcell_arguments
    @needs_local_scope
    @line_magic
    def debugcell(self, line, local_ns=None):
        """
        Debug a code cell from an editor.
        """
        args = self._parse_runcell_argstring(self.debugcell, line)

        with self._debugger_exec(args.canonic_filename, False) as debug_exec:
            return self._exec_cell(
                cell_id=args.cell_id,
                filename=args.filename,
                canonic_filename=args.canonic_filename,
                exec_fun=debug_exec,
                post_mortem=args.post_mortem,
                context_globals=self.shell.user_ns,
                context_locals=local_ns,
            )

    @runcell_arguments
    @needs_local_scope
    @line_magic
    def profilecell(self, line, local_ns=None):
        """Profile a code cell."""
        args = self._parse_runcell_argstring(self.profilecell, line)

        with self._profile_exec() as prof_exec:
            return self._exec_cell(
                cell_id=args.cell_id,
                filename=args.filename,
                canonic_filename=args.canonic_filename,
                exec_fun=prof_exec,
                post_mortem=args.post_mortem,
                context_globals=self.shell.user_ns,
                context_locals=local_ns,
            )

    @no_var_expand
    @needs_local_scope
    @line_cell_magic
    def profile(self, line, cell=None, local_ns=None):
        """Profile the given line."""
        if cell is not None:
            line += "\n" + cell
        with self._profile_exec() as prof_exec:
            return prof_exec(line, self.shell.user_ns, local_ns)

    @contextmanager
    def _debugger_exec(self, filename, continue_if_has_breakpoints):
        """Get an exec function to use for debugging."""
        if not self.shell.is_debugging():
            debugger = SpyderPdb()
            debugger.set_remote_filename(filename)
            debugger.continue_if_has_breakpoints = continue_if_has_breakpoints
            yield debugger.run
            return

        session = self.shell.pdb_session
        with session.recursive_debugger() as debugger:
            debugger.set_remote_filename(filename)
            debugger.continue_if_has_breakpoints = continue_if_has_breakpoints

            def debug_exec(code, glob=None, loc=None):
                return sys.call_tracing(debugger.run, (code, glob, loc))

            # Enter recursive debugger
            yield debug_exec

    @contextmanager
    def _profile_exec(self):
        """Get an exec function for profiling."""
        tmp_dir = None
        if sys.platform.startswith('linux'):
            # Do not use /tmp for temporary files
            try:
                from xdg.BaseDirectory import xdg_data_home
                tmp_dir = xdg_data_home
                os.makedirs(tmp_dir, exist_ok=True)
            except Exception:
                tmp_dir = None

        with tempfile.TemporaryDirectory(dir=tmp_dir) as tempdir:
            # Reset the tracing function in case we are debugging
            trace_fun = sys.gettrace()
            sys.settrace(None)

            # Get a file to save the results
            profile_filename = os.path.join(tempdir, "profile.prof")

            try:
                if self.shell.is_debugging():
                    def prof_exec(code, glob=None, loc=None):
                        """
                        If we are debugging (tracing), call_tracing is
                        necessary for profiling.
                        """
                        return sys.call_tracing(cProfile.runctx, (
                            code, glob, loc, profile_filename
                        ))

                    yield prof_exec
                else:
                    yield partial(cProfile.runctx, filename=profile_filename)
            finally:
                # Reset tracing function
                sys.settrace(trace_fun)

                # Send result to frontend
                if os.path.isfile(profile_filename):
                    with open(profile_filename, "br") as f:
                        profile_result = f.read()
                    try:
                        frontend_request(blocking=False).show_profile_file(
                            profile_result, create_pathlist()
                        )
                    except CommError:
                        logger.debug(
                            "Could not send profile result to the frontend."
                        )

    def _exec_file(
        self,
        filename=None,
        args=None,
        wdir=None,
        post_mortem=False,
        current_namespace=False,
        exec_fun=None,
        canonic_filename=None,
        context_locals=None,
        context_globals=None,
    ):
        """
        Execute a file.
        """
        if self.umr.enabled and self.shell.special != "cython":
            self.umr.run()
        if args is not None and not isinstance(args, str):
            raise TypeError("expected a character buffer object")

        try:
            file_code = self._get_file_code(filename, raise_exception=True)
        except Exception:
            print(
                "This command failed to be executed because an error occurred "
                "while trying to get the file code from Spyder's  editor. "
                "The error was:\n\n"
            )
            self.shell.showtraceback(exception_only=True)
            return

        # Here the remote filename has been used. It must now be valid locally.
        filename = canonic_filename

        with NamespaceManager(
            self.shell,
            filename,
            current_namespace=current_namespace,
            file_code=file_code,
            context_locals=context_locals,
            context_globals=context_globals,
        ) as (ns_globals, ns_locals):
            sys.argv = [filename]
            if args is not None:
                # args are a sting in a string
                for arg in shlex.split(args):
                    sys.argv.append(arg)

            if "multiprocessing" in sys.modules:
                # See https://github.com/spyder-ide/spyder/issues/16696
                try:
                    sys.modules["__mp_main__"] = sys.modules["__main__"]
                except Exception:
                    pass

            if wdir is not None:
                if wdir is True:
                    # True means use file dir
                    wdir = os.path.dirname(filename)
                if os.path.isdir(wdir):
                    os.chdir(wdir)

                    # See https://github.com/spyder-ide/spyder/issues/13632
                    if "multiprocessing.process" in sys.modules:
                        try:
                            import multiprocessing.process
                            multiprocessing.process.ORIGINAL_DIR = os.path.abspath(wdir)
                        except Exception:
                            pass
                else:
                    print("Working directory {} doesn't exist.\n".format(wdir))

            try:
                if self.shell.special == "cython":
                    # Cython files
                    with io.open(filename, encoding="utf-8") as f:
                        self.shell.run_cell_magic("cython", "", f.read())
                else:
                    self._exec_code(
                        file_code,
                        filename,
                        ns_globals,
                        ns_locals,
                        post_mortem=post_mortem,
                        exec_fun=exec_fun,
                        capture_last_expression=False,
                        global_warning=not current_namespace,
                    )
            finally:
                sys.argv = [""]

    def _exec_cell(
        self,
        cell_id,
        filename=None,
        post_mortem=False,
        exec_fun=None,
        canonic_filename=None,
        context_locals=None,
        context_globals=None,
    ):
        """
        Execute a code cell.
        """
        try:
            # Get code from spyder
            cell_code = frontend_request(blocking=True).run_cell(cell_id, filename)
        except Exception:
            print(
                "This command failed to be executed because an error occurred "
                "while trying to get the cell code from Spyder's editor."
                "The error was:\n\n"
            )
            self.shell.showtraceback(exception_only=True)
            return

        if not cell_code or cell_code.strip() == "":
            print("Nothing to execute, this cell is empty.\n")
            return

        # Trigger `post_execute` to exit the additional pre-execution.
        # See Spyder PR #7310.
        self.shell.events.trigger("post_execute")
        file_code = self._get_file_code(filename, save_all=False)

        # Here the remote filename has been used. It must now be valid locally.
        filename = canonic_filename

        with NamespaceManager(
            self.shell,
            filename,
            current_namespace=True,
            file_code=file_code,
            context_locals=context_locals,
            context_globals=context_globals
        ) as (ns_globals, ns_locals):
            return self._exec_code(
                cell_code,
                filename,
                ns_globals,
                ns_locals,
                post_mortem=post_mortem,
                exec_fun=exec_fun,
                capture_last_expression=True,
            )

    def _get_current_file_name(self):
        """Get the current editor file name."""
        try:
            return frontend_request(blocking=True).current_filename()
        except Exception:
            print(
                "This command failed to be executed because an error occurred "
                "while trying to get the current file name from Spyder's editor."
                "The error was:\n\n"
            )
            self.shell.showtraceback(exception_only=True)
            return None

    def _get_file_code(self, filename, save_all=True, raise_exception=False):
        """Retrieve the content of a file."""
        # Get code from spyder
        try:
            return frontend_request(blocking=True).get_file_code(
                filename, save_all=save_all
            )
        except Exception:
            # Maybe this is a local file
            try:
                with open(filename, "r") as f:
                    return f.read()
            except FileNotFoundError:
                pass

            if raise_exception:
                raise

            # Finally return None
            return None

    def _exec_code(
        self,
        code,
        filename,
        ns_globals,
        ns_locals=None,
        post_mortem=False,
        exec_fun=None,
        capture_last_expression=False,
        global_warning=False,
    ):
        """Execute code and display any exception."""
        if exec_fun is None:
            exec_fun = exec

        is_ipython = os.path.splitext(filename)[1] == ".ipy"
        try:
            if not is_ipython:
                # TODO: Remove the try-except and let the SyntaxError raise
                # because there should't be IPython code in a Python file.
                try:
                    ast_code = ast.parse(
                        self._transform_cell(code, indent_only=True)
                    )
                except SyntaxError as e:
                    try:
                        ast_code = ast.parse(self._transform_cell(code))
                    except SyntaxError:
                        raise e from None
                    else:
                        if self.show_invalid_syntax_msg:
                            print(
                                "\nWARNING: This is not valid Python code. "
                                "If you want to use IPython magics, "
                                "flexible indentation, and prompt removal, "
                                "we recommend that you save this file with the "
                                ".ipy extension.\n"
                            )
                            self.show_invalid_syntax_msg = False
            else:
                ast_code = ast.parse(self._transform_cell(code))

            # Print warning for global
            if global_warning and self.show_global_msg:
                has_global = any(
                    isinstance(node, ast.Global) for node in ast.walk(ast_code)
                )
                if has_global:
                    print(
                        "\nWARNING: This file contains a global statement, "
                        "but it is run in an empty namespace. "
                        "Consider using the "
                        "'Run in console's namespace instead of an empty one' "
                        "option, that you can find in the menu 'Run > "
                        "Configuration per file', if you want to capture the "
                        "namespace.\n"
                    )
                    self.show_global_msg = False

            if code.rstrip()[-1:] == ";":
                # Supress output with ;
                capture_last_expression = False

            if capture_last_expression:
                ast_code, capture_last_expression = capture_last_Expr(
                    ast_code, "_spyder_out", ns_globals
                )

            exec_encapsulate_locals(
                ast_code, ns_globals, ns_locals, exec_fun, filename
            )

            if capture_last_expression:
                out = ns_globals.pop("_spyder_out", None)
                if out is not None:
                    return out
        except SystemExit as status:
            # ignore exit(0)
            if status.code:
                self.shell.showtraceback(exception_only=True)
        except BaseException as error:
            if isinstance(error, bdb.BdbQuit) and self.shell.pdb_session:
                # Ignore BdbQuit if we are debugging, as it is expected.
                pass
            elif post_mortem and isinstance(error, Exception):
                error_type, error, tb = sys.exc_info()
                self._post_mortem_excepthook(error_type, error, tb)
            else:
                # We ignore the call to exec
                self.shell.showtraceback(tb_offset=1)
        finally:
            __tracebackhide__ = "__pdb_exit__"

    def _count_leading_empty_lines(self, cell):
        """Count the number of leading empty cells."""
        lines = cell.splitlines(keepends=True)
        if not lines:
            return 0
        for i, line in enumerate(lines):
            if line and not line.isspace():
                return i
        return len(lines)

    def _transform_cell(self, code, indent_only=False):
        """Transform IPython code to Python code."""
        number_empty_lines = self._count_leading_empty_lines(code)
        if indent_only:
            if not code.endswith("\n"):
                code += "\n"  # Ensure the cell has a trailing newline
            lines = code.splitlines(keepends=True)
            lines = leading_indent(leading_empty_lines(lines))
            code = "".join(lines)
        else:
            tm = TransformerManager()
            code = tm.transform_cell(code)
        return "\n" * number_empty_lines + code

    def _post_mortem_excepthook(self, type, value, tb):
        """
        For post mortem exception handling, print a banner and enable post
        mortem debugging.
        """
        self.shell.showtraceback((type, value, tb))
        p = pdb.Pdb(self.shell.colors)

        if not type == SyntaxError:
            # wait for stderr to print (stderr.flush does not work in this case)
            time.sleep(0.1)
            print("*" * 40)
            print("Entering post mortem debugging...")
            print("*" * 40)
            #  add ability to move between frames
            p.reset()
            frame = tb.tb_next.tb_frame
            # wait for stdout to print
            time.sleep(0.1)
            p.interaction(frame, tb)
    
    def _parse_argstring(self, magic_func, argstring):
        """
        Parse a string of arguments for a magic function.

        This is needed because magic_arguments.parse_argstring does
        platform-dependent things with quotes and backslashes. For
        example, on Windows, strings are removed and backslashes are
        escaped.
        """
        argv = shlex.split(argstring)
        args = magic_func.parser.parse_args(argv)
        if args.filename is None:
            args.filename = self._get_current_file_name()
        args.canonic_filename = canonic(args.filename)
        return args
    
    def _parse_runfile_argstring(self, magic_func, argstring, local_ns):
        """Parse an args string for runfile and debugfile."""
        args = self._parse_argstring(magic_func, argstring)
        if args.namespace is None:
            args.namespace = self.shell.user_ns
        else:
            if local_ns is not None and args.namespace in local_ns:
                args.namespace = local_ns[args.namespace]
            elif args.namespace in self.shell.user_ns:
                args.namespace = self.shell.user_ns[args.namespace]
            else:
                raise NameError(
                    f"name '{args.namespace}' is not defined"
                )
            local_ns = None
            args.current_namespace = True
        return args, local_ns

    def _parse_runcell_argstring(self, magic_func, argstring):
        """Parse an args string for runcell and debugcell."""
        args = self._parse_argstring(magic_func, argstring)
        args.cell_id = args.name
        if args.cell_id is None:
            args.cell_id = int(args.index)
        return args
