
from _ast import PyCF_ONLY_AST
from sys import version_info

from pyflakes import messages as m, checker
from pyflakes.test.harness import TestCase, skip, skipIf


class Test(TestCase):
    def test_undefined(self):
        self.flakes('bar', m.UndefinedName)

    def test_definedInListComp(self):
        self.flakes('[a for a in range(10) if a]')

    def test_functionsNeedGlobalScope(self):
        self.flakes('''
        class a:
            def b():
                fu
        fu = 1
        ''')

    def test_builtins(self):
        self.flakes('range(10)')

    def test_builtinWindowsError(self):
        """
        C{WindowsError} is sometimes a builtin name, so no warning is emitted
        for using it.
        """
        self.flakes('WindowsError')

    def test_magicGlobalsFile(self):
        """
        Use of the C{__file__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__file__')

    def test_magicGlobalsBuiltins(self):
        """
        Use of the C{__builtins__} magic global should not emit an undefined
        name warning.
        """
        self.flakes('__builtins__')

    def test_magicGlobalsName(self):
        """
        Use of the C{__name__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__name__')

    def test_magicGlobalsPath(self):
        """
        Use of the C{__path__} magic global should not emit an undefined name
        warning, if you refer to it from a file called __init__.py.
        """
        self.flakes('__path__', m.UndefinedName)
        self.flakes('__path__', filename='package/__init__.py')

    def test_globalImportStar(self):
        """Can't find undefined names with import *."""
        self.flakes('from fu import *; bar', m.ImportStarUsed)

    def test_localImportStar(self):
        """
        A local import * still allows undefined names to be found
        in upper scopes.
        """
        self.flakes('''
        def a():
            from fu import *
        bar
        ''', m.ImportStarUsed, m.UndefinedName)

    @skipIf(version_info >= (3,), 'obsolete syntax')
    def test_unpackedParameter(self):
        """Unpacked function parameters create bindings."""
        self.flakes('''
        def a((bar, baz)):
            bar; baz
        ''')

    @skip("todo")
    def test_definedByGlobal(self):
        """
        "global" can make an otherwise undefined name in another function
        defined.
        """
        self.flakes('''
        def a(): global fu; fu = 1
        def b(): fu
        ''')

    def test_globalInGlobalScope(self):
        """
        A global statement in the global scope is ignored.
        """
        self.flakes('''
        global x
        def foo():
            print(x)
        ''', m.UndefinedName)

    def test_del(self):
        """Del deletes bindings."""
        self.flakes('a = 1; del a; a', m.UndefinedName)

    def test_delGlobal(self):
        """Del a global binding from a function."""
        self.flakes('''
        a = 1
        def f():
            global a
            del a
        a
        ''')

    def test_delUndefined(self):
        """Del an undefined name."""
        self.flakes('del a', m.UndefinedName)

    def test_globalFromNestedScope(self):
        """Global names are available from nested scopes."""
        self.flakes('''
        a = 1
        def b():
            def c():
                a
        ''')

    def test_laterRedefinedGlobalFromNestedScope(self):
        """
        Test that referencing a local name that shadows a global, before it is
        defined, generates a warning.
        """
        self.flakes('''
        a = 1
        def fun():
            a
            a = 2
            return a
        ''', m.UndefinedLocal)

    def test_laterRedefinedGlobalFromNestedScope2(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global declared in an enclosing scope, before it is defined, generates
        a warning.
        """
        self.flakes('''
            a = 1
            def fun():
                global a
                def fun2():
                    a
                    a = 2
                    return a
        ''', m.UndefinedLocal)

    def test_intermediateClassScopeIgnored(self):
        """
        If a name defined in an enclosing scope is shadowed by a local variable
        and the name is used locally before it is bound, an unbound local
        warning is emitted, even if there is a class scope between the enclosing
        scope and the local scope.
        """
        self.flakes('''
        def f():
            x = 1
            class g:
                def h(self):
                    a = x
                    x = None
                    print(x, a)
            print(x)
        ''', m.UndefinedLocal)

    def test_doubleNestingReportsClosestName(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        variable declared in two different outer scopes before it is defined
        in the innermost scope generates an UnboundLocal warning which
        refers to the nearest shadowed name.
        """
        exc = self.flakes('''
            def a():
                x = 1
                def b():
                    x = 2 # line 5
                    def c():
                        x
                        x = 3
                        return x
                    return x
                return x
        ''', m.UndefinedLocal).messages[0]
        self.assertEqual(exc.message_args, ('x', 5))

    def test_laterRedefinedGlobalFromNestedScope3(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global, before it is defined, generates a warning.
        """
        self.flakes('''
            def fun():
                a = 1
                def fun2():
                    a
                    a = 1
                    return a
                return a
        ''', m.UndefinedLocal)

    def test_undefinedAugmentedAssignment(self):
        self.flakes(
            '''
            def f(seq):
                a = 0
                seq[a] += 1
                seq[b] /= 2
                c[0] *= 2
                a -= 3
                d += 4
                e[any] = 5
            ''',
            m.UndefinedName,    # b
            m.UndefinedName,    # c
            m.UndefinedName, m.UnusedVariable,  # d
            m.UndefinedName,    # e
        )

    def test_nestedClass(self):
        """Nested classes can access enclosing scope."""
        self.flakes('''
        def f(foo):
            class C:
                bar = foo
                def f(self):
                    return foo
            return C()

        f(123).f()
        ''')

    def test_badNestedClass(self):
        """Free variables in nested classes must bind at class creation."""
        self.flakes('''
        def f():
            class C:
                bar = foo
            foo = 456
            return foo
        f()
        ''', m.UndefinedName)

    def test_definedAsStarArgs(self):
        """Star and double-star arg names are defined."""
        self.flakes('''
        def f(a, *b, **c):
            print(a, b, c)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_definedAsStarUnpack(self):
        """Star names in unpack are defined."""
        self.flakes('''
        a, *b = range(10)
        print(a, b)
        ''')
        self.flakes('''
        *a, b = range(10)
        print(a, b)
        ''')
        self.flakes('''
        a, *b, c = range(10)
        print(a, b, c)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_usedAsStarUnpack(self):
        """
        Star names in unpack are used if RHS is not a tuple/list literal.
        """
        self.flakes('''
        def f():
            a, *b = range(10)
        ''')
        self.flakes('''
        def f():
            (*a, b) = range(10)
        ''')
        self.flakes('''
        def f():
            [a, *b, c] = range(10)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_unusedAsStarUnpack(self):
        """
        Star names in unpack are unused if RHS is a tuple/list literal.
        """
        self.flakes('''
        def f():
            a, *b = any, all, 4, 2, 'un'
        ''', m.UnusedVariable, m.UnusedVariable)
        self.flakes('''
        def f():
            (*a, b) = [bool, int, float, complex]
        ''', m.UnusedVariable, m.UnusedVariable)
        self.flakes('''
        def f():
            [a, *b, c] = 9, 8, 7, 6, 5, 4
        ''', m.UnusedVariable, m.UnusedVariable, m.UnusedVariable)

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_keywordOnlyArgs(self):
        """Keyword-only arg names are defined."""
        self.flakes('''
        def f(*, a, b=None):
            print(a, b)
        ''')

        self.flakes('''
        import default_b
        def f(*, a, b=default_b):
            print(a, b)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_keywordOnlyArgsUndefined(self):
        """Typo in kwonly name."""
        self.flakes('''
        def f(*, a, b=default_c):
            print(a, b)
        ''', m.UndefinedName)

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_annotationUndefined(self):
        """Undefined annotations."""
        self.flakes('''
        from abc import note1, note2, note3, note4, note5
        def func(a: note1, *args: note2,
                 b: note3=12, **kw: note4) -> note5: pass
        ''')

        self.flakes('''
        def func():
            d = e = 42
            def func(a: {1, d}) -> (lambda c: e): pass
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_metaClassUndefined(self):
        self.flakes('''
        from abc import ABCMeta
        class A(metaclass=ABCMeta): pass
        ''')

    def test_definedInGenExp(self):
        """
        Using the loop variable of a generator expression results in no
        warnings.
        """
        self.flakes('(a for a in %srange(10) if a)' %
                    ('x' if version_info < (3,) else ''))

    def test_undefinedWithErrorHandler(self):
        """
        Some compatibility code checks explicitly for NameError.
        It should not trigger warnings.
        """
        self.flakes('''
        try:
            socket_map
        except NameError:
            socket_map = {}
        ''')
        self.flakes('''
        try:
            _memoryview.contiguous
        except (NameError, AttributeError):
            raise RuntimeError("Python >= 3.3 is required")
        ''')
        # If NameError is not explicitly handled, generate a warning
        self.flakes('''
        try:
            socket_map
        except:
            socket_map = {}
        ''', m.UndefinedName)
        self.flakes('''
        try:
            socket_map
        except Exception:
            socket_map = {}
        ''', m.UndefinedName)

    def test_definedInClass(self):
        """
        Defined name for generator expressions and dict/set comprehension.
        """
        self.flakes('''
        class A:
            T = range(10)

            Z = (x for x in T)
            L = [x for x in T]
            B = dict((i, str(i)) for i in T)
        ''')

        if version_info >= (2, 7):
            self.flakes('''
            class A:
                T = range(10)

                X = {x for x in T}
                Y = {x:x for x in T}
            ''')

    def test_undefinedInLoop(self):
        """
        The loop variable is defined after the expression is computed.
        """
        self.flakes('''
        for i in range(i):
            print(i)
        ''', m.UndefinedName)
        self.flakes('''
        [42 for i in range(i)]
        ''', m.UndefinedName)
        self.flakes('''
        (42 for i in range(i))
        ''', m.UndefinedName)


class NameTests(TestCase):
    """
    Tests for some extra cases of name handling.
    """
    def test_impossibleContext(self):
        """
        A Name node with an unrecognized context results in a RuntimeError being
        raised.
        """
        tree = compile("x = 10", "<test>", "exec", PyCF_ONLY_AST)
        # Make it into something unrecognizable.
        tree.body[0].targets[0].ctx = object()
        self.assertRaises(RuntimeError, checker.Checker, tree)
