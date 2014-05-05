# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Source code analysis utilities
"""

import sys
import re
import os
from subprocess import Popen, PIPE
import tempfile
import traceback

# Local import
from spyderlib.baseconfig import _, DEBUG
from spyderlib.utils import programs, encoding
from spyderlib.py3compat import to_text_string, to_binary_string, PY3
from spyderlib import dependencies
DEBUG_EDITOR = DEBUG >= 3

#==============================================================================
# Pyflakes/pep8 code analysis
#==============================================================================
TASKS_PATTERN = r"(^|#)[ ]*(TODO|FIXME|XXX|HINT|TIP|@todo)([^#]*)"

#TODO: this is a test for the following function
def find_tasks(source_code):
    """Find tasks in source code (TODO, FIXME, XXX, ...)"""
    results = []
    for line, text in enumerate(source_code.splitlines()):
        for todo in re.findall(TASKS_PATTERN, text):
            results.append((todo[-1].strip().capitalize(), line+1))
    return results


def check_with_pyflakes(source_code, filename=None):
    """Check source code with pyflakes
    Returns an empty list if pyflakes is not installed"""
    try:
        if filename is None:
            filename = '<string>'
        try:
            source_code += '\n'
        except TypeError:
            # Python 3
            source_code += to_binary_string('\n')
            
        import _ast
        from pyflakes.checker import Checker
        # First, compile into an AST and handle syntax errors.
        try:
            tree = compile(source_code, filename, "exec", _ast.PyCF_ONLY_AST)
        except SyntaxError as value:
            # If there's an encoding problem with the file, the text is None.
            if value.text is None:
                results = []
            else:
                results = [(value.args[0], value.lineno)]
        except (ValueError, TypeError):
            # Example of ValueError: file contains invalid \x escape character
            # (see http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674797)
            # Example of TypeError: file contains null character
            # (see http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674796)
            results = []
        else:
            # Okay, it's syntactically valid.  Now check it.
            w = Checker(tree, filename)
            w.messages.sort(key=lambda x: x.lineno)
            results = []
            coding = encoding.get_coding(source_code)
            lines = source_code.splitlines()
            for warning in w.messages:
                if 'analysis:ignore' not in \
                   to_text_string(lines[warning.lineno-1], coding):
                    results.append((warning.message % warning.message_args,
                                    warning.lineno))
    except Exception:
        # Never return None to avoid lock in spyderlib/widgets/editor.py
        # See Issue 1547
        results = []
        if DEBUG_EDITOR:
            traceback.print_exc()  # Print exception in internal console
    return results

# Required version:
# Why 0.5 (Python2)? Because it's based on _ast (thread-safe)
PYFLAKES_REQVER = '>=0.6.0' if PY3 else '>=0.5.0'
dependencies.add("pyflakes", _("Real-time code analysis on the Editor"),
                 required_version=PYFLAKES_REQVER)

PEP8_REQVER = '>=0.6'
dependencies.add("pep8", _("Real-time code style analysis on the Editor"),
                 required_version=PEP8_REQVER)


def is_pyflakes_installed():
    """Return True if pyflakes required version is installed"""
    return programs.is_module_installed('pyflakes', PYFLAKES_REQVER)


def get_checker_executable(name):
    """Return checker executable in the form of a list of arguments
    for subprocess.Popen"""
    if programs.is_program_installed(name):
        # Checker is properly installed
        return [name]
    else:
        path1 = programs.python_script_exists(package=None,
                                              module=name+'_script')
        path2 = programs.python_script_exists(package=None, module=name)
        if path1 is not None:  # checker_script.py is available
            # Checker script is available but has not been installed
            # (this may work with pyflakes)
            return [sys.executable, path1]
        elif path2 is not None:  # checker.py is available
            # Checker package is available but its script has not been
            # installed (this works with pep8 but not with pyflakes)
            return [sys.executable, path2]


def check(args, source_code, filename=None, options=None):
    """Check source code with checker defined with *args* (list)
    Returns an empty list if checker is not installed"""
    if args is None:
        return []
    if options is not None:
        args += options
    if any(['pyflakes' in arg for arg in args]):
        #  Pyflakes requires an ending new line (pep8 don't! -- see Issue 1123)
        #  Note: this code is not used right now as it is faster to invoke 
        #  pyflakes in current Python interpreter (see `check_with_pyflakes` 
        #  function above) than calling it through a subprocess
        source_code += '\n'
    if filename is None:
        # Creating a temporary file because file does not exist yet 
        # or is not up-to-date
        tempfd = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        tempfd.write(source_code)
        tempfd.close()
        args.append(tempfd.name)
    else:
        args.append(filename)
    output = Popen(args, stdout=PIPE, stderr=PIPE
                   ).communicate()[0].strip().decode().splitlines()
    if filename is None:
        os.unlink(tempfd.name)
    results = []
    coding = encoding.get_coding(source_code)
    lines = source_code.splitlines()
    for line in output:
        lineno = int(re.search(r'(\:[\d]+\:)', line).group()[1:-1])
        if 'analysis:ignore' not in to_text_string(lines[lineno-1], coding):
            message = line[line.find(': ')+2:]
            results.append((message, lineno))
    return results


def check_with_pep8(source_code, filename=None):
    """Check source code with pep8"""
    try:
        args = get_checker_executable('pep8')
        results = check(args, source_code, filename=filename, options=['-r'])
    except Exception:
        # Never return None to avoid lock in spyderlib/widgets/editor.py
        # See Issue 1547
        results = []
        if DEBUG_EDITOR:
            traceback.print_exc()  # Print exception in internal console
    return results


if __name__ == '__main__':
#    fname = __file__
    fname = os.path.join(os.path.dirname(__file__),
                         os.pardir, os.pardir, 'bootstrap.py')
    code = open(fname).read()
    check_results = check_with_pyflakes(code, fname)+\
                    check_with_pep8(code, fname)+find_tasks(code)
#    check_results = check_with_pep8(code, fname)
    for message, line in check_results:
        sys.stdout.write("Message: %s -- Line: %s\n" % (message, line))
