
import textwrap
import ast

import unittest

from pyflakes import checker


class Test(unittest.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        compiled_ast = compile(textwrap.dedent(input), "<test>", "exec", ast.PyCF_ONLY_AST)
        w = checker.Checker(compiled_ast, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assert_(outputs == expectedOutputs, '''\
for input:
%s
expected outputs:
%s
but got:
%s''' % (input, repr(expectedOutputs), '\n'.join([str(o) for o in w.messages])))
        return w
