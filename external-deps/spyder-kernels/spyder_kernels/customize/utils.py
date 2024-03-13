# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

"""Utility functions."""

import ast
import os
import re
import sys
import sysconfig


def create_pathlist():
    """
    Create list of Python library paths to be skipped from module
    reloading and Pdb steps.
    """
    # Get standard installation paths
    try:
        paths = sysconfig.get_paths()
        standard_paths = [paths['stdlib'],
                          paths['purelib'],
                          paths['scripts'],
                          paths['data']]
    except Exception:
        standard_paths = []

    # Get user installation path
    # See spyder-ide/spyder#8776
    try:
        import site
        if getattr(site, 'getusersitepackages', False):
            # Virtualenvs don't have this function but
            # conda envs do
            user_path = [site.getusersitepackages()]
        elif getattr(site, 'USER_SITE', False):
            # However, it seems virtualenvs have this
            # constant
            user_path = [site.USER_SITE]
        else:
            user_path = []
    except Exception:
        user_path = []

    return standard_paths + user_path


def path_is_library(path, initial_pathlist=None):
    """Decide if a path is in user code or a library according to its path."""
    # Compute DEFAULT_PATHLIST only once and make it global to reuse it
    # in any future call of this function.
    if 'DEFAULT_PATHLIST' not in globals():
        global DEFAULT_PATHLIST
        DEFAULT_PATHLIST = create_pathlist()

    if initial_pathlist is None:
        initial_pathlist = []

    pathlist = initial_pathlist + DEFAULT_PATHLIST

    if path is None:
        # Path probably comes from a C module that is statically linked
        # into the interpreter. There is no way to know its path, so we
        # choose to ignore it.
        return True
    elif any([p in path for p in pathlist]):
        # We don't want to consider paths that belong to the standard
        # library or installed to site-packages.
        return True
    elif os.name == 'nt':
        if re.search(r'.*\\pkgs\\.*', path):
            return True
        else:
            return False
    elif not os.name == 'nt':
        # Paths containing the strings below can be part of the default
        # Linux installation, Homebrew or the user site-packages in a
        # virtualenv.
        patterns = [
            r'^/usr/lib.*',
            r'^/usr/local/lib.*',
            r'^/usr/.*/dist-packages/.*',
            r'^/home/.*/.local/lib.*',
            r'^/Library/.*',
            r'^/Users/.*/Library/.*',
            r'^/Users/.*/.local/.*',
        ]

        if [p for p in patterns if re.search(p, path)]:
            return True
        else:
            return False
    else:
        return False


def capture_last_Expr(code_ast, out_varname):
    """
    Parse line and modify code to capture in globals the last expression.

    The namespace must contain __spyder_builtins__, which is the builtins module.
    """
    # Modify ast code to capture the last expression
    capture_last_expression = False
    if (
        len(code_ast.body)
        and isinstance(code_ast.body[-1], ast.Expr)
    ):
        capture_last_expression = True
        expr_node = code_ast.body[-1]
        # Create new assign node
        assign_node = ast.parse(
            '__spyder_builtins__.globals()[{}] = None'.format(
                repr(out_varname))).body[0]
        # Replace None by the value
        assign_node.value = expr_node.value
        # Fix line number and column offset
        assign_node.lineno = expr_node.lineno
        assign_node.col_offset = expr_node.col_offset
        if sys.version_info[:2] >= (3, 8):
            # Exists from 3.8, necessary from 3.11
            assign_node.end_lineno = expr_node.end_lineno
            if assign_node.lineno == assign_node.end_lineno:
                # Add '__spyder_builtins__.globals()[{}] = ' and remove 'None'
                assign_node.end_col_offset += expr_node.end_col_offset - 4
            else:
                assign_node.end_col_offset = expr_node.end_col_offset
        code_ast.body[-1] = assign_node
    return code_ast, capture_last_expression


def exec_encapsulate_locals(
    code_ast, globals, locals, exec_fun=None, filename=None
):
    """Execute by encapsulating locals if needed."""
    use_locals_hack = locals is not None and locals is not globals
    if use_locals_hack:
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
        if exec_fun is None:
            exec_fun = exec
        if filename is None:
            filename = "<stdin>"
        exec_fun(compile(code_ast, filename, "exec"), globals)
    finally:
        if use_locals_hack:
            # Cleanup code
            globals.pop("_spyderpdb_code", None)
            if len(globals["_spyderpdb_locals"]) > 1:
                del globals["_spyderpdb_locals"][-1]
            else:
                del globals["_spyderpdb_locals"]


def canonic(filename):
    """
    Return canonical form of filename.

    This is a copy of bdb.canonic, so that the debugger will process 
    filenames in the same way
    """
    if filename == "<" + filename[1:-1] + ">":
        return filename
    canonic = os.path.abspath(filename)
    canonic = os.path.normcase(canonic)
    return canonic
