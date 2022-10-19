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
    """Parse line and modify code to capture in globals the last expression."""
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
            'globals()[{}] = None'.format(repr(out_varname))).body[0]
        # Replace None by the value
        assign_node.value = expr_node.value
        # Fix line number and column offset
        assign_node.lineno = expr_node.lineno
        assign_node.col_offset = expr_node.col_offset
        if sys.version_info[:2] >= (3, 8):
            # Exists from 3.8, necessary from 3.11
            assign_node.end_lineno = expr_node.end_lineno
            if assign_node.lineno == assign_node.end_lineno:
                # Add 'globals()[{}] = ' and remove 'None'
                assign_node.end_col_offset += expr_node.end_col_offset - 4
            else:
                assign_node.end_col_offset = expr_node.end_col_offset
        code_ast.body[-1] = assign_node
    return code_ast, capture_last_expression


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
