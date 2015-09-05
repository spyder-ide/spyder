
import sys
import textwrap
import unittest

from pyflakes import checker

__all__ = ['TestCase', 'skip', 'skipIf']

if sys.version_info < (2, 7):
    skip = lambda why: (lambda func: 'skip')  # not callable
    skipIf = lambda cond, why: (skip(why) if cond else lambda func: func)
else:
    skip = unittest.skip
    skipIf = unittest.skipIf
PyCF_ONLY_AST = 1024


class TestCase(unittest.TestCase):

    withDoctest = False

    def flakes(self, input, *expectedOutputs, **kw):
        tree = compile(textwrap.dedent(input), "<test>", "exec", PyCF_ONLY_AST)
        w = checker.Checker(tree, withDoctest=self.withDoctest, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assertEqual(outputs, expectedOutputs, '''\
for input:
%s
expected outputs:
%r
but got:
%s''' % (input, expectedOutputs, '\n'.join([str(o) for o in w.messages])))
        return w

    if sys.version_info < (2, 7):

        def assertIs(self, expr1, expr2, msg=None):
            if expr1 is not expr2:
                self.fail(msg or '%r is not %r' % (expr1, expr2))
