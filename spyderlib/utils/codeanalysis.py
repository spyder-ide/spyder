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

# Local import
from spyderlib.utils import programs


#==============================================================================
# Pyflakes/pep8 code analysis
#==============================================================================
def find_tasks(source_code):
    """Find tasks in source code (TODO, FIXME, XXX, ...)"""
    pattern = r"# ?TODO ?:?[^#]*|# ?FIXME ?:?[^#]*|"\
              r"# ?XXX ?:?[^#]*|# ?HINT ?:?[^#]*|# ?TIP ?:?[^#]*"
    results = []
    for line, text in enumerate(source_code.splitlines()):
        for todo in re.findall(pattern, text):
            results.append((todo, line+1))
    return results


def check_with_pyflakes(source_code, filename=None):
    """Check source code with pyflakes
    Returns an empty list if pyflakes is not installed"""
    if filename is None:
        filename = '<string>'
    source_code += '\n'
    import _ast
    from spyderlib.utils.external.pyflakes.checker import Checker
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(source_code, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError, value:
        # If there's an encoding problem with the file, the text is None.
        if value.text is None:
            return []
        else:
            return [(value.args[0], value.lineno)]
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        results = []
        lines = source_code.splitlines()
        for warning in w.messages:
            if 'analysis:ignore' not in lines[warning.lineno-1]:
                results.append((warning.message % warning.message_args,
                                warning.lineno))
        return results


def get_checker_executable(name):
    """Return checker executable in the form of a list of arguments
    for subprocess.Popen"""
    if programs.is_program_installed(name):
        # Checker is properly installed
        return [name]
    else:
        path1 = programs.python_script_exists(package=None,
                                          module=name+'_script', get_path=True)
        path2 = programs.python_script_exists(package=None, module=name,
                                              get_path=True)
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
                   ).communicate()[0].strip().splitlines()
    if filename is None:
        os.unlink(tempfd.name)
    results = []
    lines = source_code.splitlines()
    for line in output:
        lineno = int(re.search(r'(\:[\d]+\:)', line).group()[1:-1])
        if 'analysis:ignore' not in lines[lineno-1]:
            message = line[line.find(': ')+2:]
            results.append((message, lineno))
    return results


def check_with_pep8(source_code, filename=None):
    """Check source code with pep8"""
    args = get_checker_executable('pep8')
    return check(args, source_code, filename=filename, options=['-r'])


if __name__ == '__main__':
    fname = __file__
    code = file(fname, 'U').read()
    check_results = check_with_pyflakes(code, fname)+\
                    check_with_pep8(code, fname)
    for message, line in check_results:
        print "Message: %s -- Line: %s" % (message, line)
