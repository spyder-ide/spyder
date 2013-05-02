
"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast

checker = __import__('pyflakes.checker').checker

def check(codeString, filename):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError as value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            print("%s: problem decoding source" % (filename, ), file=sys.stderr)
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            print('%s:%d: %s' % (filename, lineno, msg), file=sys.stderr)
            print(line, file=sys.stderr)

            if offset is not None:
                print(" " * offset, "^", file=sys.stderr)

        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(key=lambda m: m.lineno)
        for warning in w.messages:
            print(warning)
        return len(w.messages)


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        return check(open(filename, 'rb').read() + b'\n', filename)
    except IOError as msg:
        print("%s: %s" % (filename, msg.args[1]), file=sys.stderr)
        return 1


def main():
    warnings = 0
    args = sys.argv[1:]
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename))
            else:
                warnings += checkPath(arg)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(warnings > 0)
