"""
Tests for various Pyflakes behavior.
"""

from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skip, skipIf


class Test(TestCase):

    def test_duplicateArgs(self):
        self.flakes('def fu(bar, bar): pass', m.DuplicateArgument)

    def test_localReferencedBeforeAssignment(self):
        self.flakes('''
        a = 1
        def f():
            a; a=1
        f()
        ''', m.UndefinedLocal, m.UnusedVariable)

    def test_redefinedInListComp(self):
        """
        Test that shadowing a variable in a list comprehension raises
        a warning.
        """
        self.flakes('''
        a = 1
        [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        class A:
            a = 1
            [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        def f():
            a = 1
            [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        [1 for a, b in [(1, 2)]]
        [1 for a, b in [(1, 2)]]
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        [1 for a, b in [(1, 2)]]
        ''')

    def test_redefinedInGenerator(self):
        """
        Test that reusing a variable in a generator does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        (1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        class A:
            a = 1
            list(1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        def f():
            a = 1
            (1 for a, b in [(1, 2)])
        ''', m.UnusedVariable)
        self.flakes('''
        (1 for a, b in [(1, 2)])
        (1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        (1 for a, b in [(1, 2)])
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_redefinedInSetComprehension(self):
        """
        Test that reusing a variable in a set comprehension does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        class A:
            a = 1
            {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        def f():
            a = 1
            {1 for a, b in [(1, 2)]}
        ''', m.UnusedVariable)
        self.flakes('''
        {1 for a, b in [(1, 2)]}
        {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        {1 for a, b in [(1, 2)]}
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_redefinedInDictComprehension(self):
        """
        Test that reusing a variable in a dict comprehension does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        class A:
            a = 1
            {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        def f():
            a = 1
            {1: 42 for a, b in [(1, 2)]}
        ''', m.UnusedVariable)
        self.flakes('''
        {1: 42 for a, b in [(1, 2)]}
        {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        {1: 42 for a, b in [(1, 2)]}
        ''')

    def test_redefinedFunction(self):
        """
        Test that shadowing a function definition with another one raises a
        warning.
        """
        self.flakes('''
        def a(): pass
        def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedClassFunction(self):
        """
        Test that shadowing a function definition in a class suite with another
        one raises a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedIfElseFunction(self):
        """
        Test that shadowing a function definition twice in an if
        and else block does not raise a warning.
        """
        self.flakes('''
        if True:
            def a(): pass
        else:
            def a(): pass
        ''')

    def test_redefinedIfFunction(self):
        """
        Test that shadowing a function definition within an if block
        raises a warning.
        """
        self.flakes('''
        if True:
            def a(): pass
            def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedTryExceptFunction(self):
        """
        Test that shadowing a function definition twice in try
        and except block does not raise a warning.
        """
        self.flakes('''
        try:
            def a(): pass
        except:
            def a(): pass
        ''')

    def test_redefinedTryFunction(self):
        """
        Test that shadowing a function definition within a try block
        raises a warning.
        """
        self.flakes('''
        try:
            def a(): pass
            def a(): pass
        except:
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedIfElseInListComp(self):
        """
        Test that shadowing a variable in a list comprehension in
        an if and else block does not raise a warning.
        """
        self.flakes('''
        if False:
            a = 1
        else:
            [a for a in '12']
        ''')

    def test_redefinedElseInListComp(self):
        """
        Test that shadowing a variable in a list comprehension in
        an else (or if) block raises a warning.
        """
        self.flakes('''
        if False:
            pass
        else:
            a = 1
            [a for a in '12']
        ''', m.RedefinedInListComp)

    def test_functionDecorator(self):
        """
        Test that shadowing a function definition with a decorated version of
        that function does not raise a warning.
        """
        self.flakes('''
        from somewhere import somedecorator

        def a(): pass
        a = somedecorator(a)
        ''')

    def test_classFunctionDecorator(self):
        """
        Test that shadowing a function definition in a class suite with a
        decorated version of that function does not raise a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            a = classmethod(a)
        ''')

    @skipIf(version_info < (2, 6), "Python >= 2.6 only")
    def test_modernProperty(self):
        self.flakes("""
        class A:
            @property
            def t(self):
                pass
            @t.setter
            def t(self, value):
                pass
            @t.deleter
            def t(self):
                pass
        """)

    def test_unaryPlus(self):
        """Don't die on unary +."""
        self.flakes('+1')

    def test_undefinedBaseClass(self):
        """
        If a name in the base list of a class definition is undefined, a
        warning is emitted.
        """
        self.flakes('''
        class foo(foo):
            pass
        ''', m.UndefinedName)

    def test_classNameUndefinedInClassBody(self):
        """
        If a class name is used in the body of that class's definition and
        the name is not already defined, a warning is emitted.
        """
        self.flakes('''
        class foo:
            foo
        ''', m.UndefinedName)

    def test_classNameDefinedPreviously(self):
        """
        If a class name is used in the body of that class's definition and
        the name was previously defined in some other way, no warning is
        emitted.
        """
        self.flakes('''
        foo = None
        class foo:
            foo
        ''')

    def test_classRedefinition(self):
        """
        If a class is defined twice in the same module, a warning is emitted.
        """
        self.flakes('''
        class Foo:
            pass
        class Foo:
            pass
        ''', m.RedefinedWhileUnused)

    def test_functionRedefinedAsClass(self):
        """
        If a function is redefined as a class, a warning is emitted.
        """
        self.flakes('''
        def Foo():
            pass
        class Foo:
            pass
        ''', m.RedefinedWhileUnused)

    def test_classRedefinedAsFunction(self):
        """
        If a class is redefined as a function, a warning is emitted.
        """
        self.flakes('''
        class Foo:
            pass
        def Foo():
            pass
        ''', m.RedefinedWhileUnused)

    @skip("todo: Too hard to make this warn but other cases stay silent")
    def test_doubleAssignment(self):
        """
        If a variable is re-assigned to without being used, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        x = 20
        ''', m.RedefinedWhileUnused)

    def test_doubleAssignmentConditionally(self):
        """
        If a variable is re-assigned within a conditional, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        if True:
            x = 20
        ''')

    def test_doubleAssignmentWithUse(self):
        """
        If a variable is re-assigned to after being used, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        y = x * 2
        x = 20
        ''')

    def test_comparison(self):
        """
        If a defined name is used on either side of any of the six comparison
        operators, no warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x < y
        x <= y
        x == y
        x != y
        x >= y
        x > y
        ''')

    def test_identity(self):
        """
        If a defined name is used on either side of an identity test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x is y
        x is not y
        ''')

    def test_containment(self):
        """
        If a defined name is used on either side of a containment test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x in y
        x not in y
        ''')

    def test_loopControl(self):
        """
        break and continue statements are supported.
        """
        self.flakes('''
        for x in [1, 2]:
            break
        ''')
        self.flakes('''
        for x in [1, 2]:
            continue
        ''')

    def test_ellipsis(self):
        """
        Ellipsis in a slice is supported.
        """
        self.flakes('''
        [1, 2][...]
        ''')

    def test_extendedSlice(self):
        """
        Extended slices are supported.
        """
        self.flakes('''
        x = 3
        [1, 2][x,:]
        ''')

    def test_varAugmentedAssignment(self):
        """
        Augmented assignment of a variable is supported.
        We don't care about var refs.
        """
        self.flakes('''
        foo = 0
        foo += 1
        ''')

    def test_attrAugmentedAssignment(self):
        """
        Augmented assignment of attributes is supported.
        We don't care about attr refs.
        """
        self.flakes('''
        foo = None
        foo.bar += foo.baz
        ''')


class TestUnusedAssignment(TestCase):
    """
    Tests for warning about unused assignments.
    """

    def test_unusedVariable(self):
        """
        Warn when a variable in a function is assigned a value that's never
        used.
        """
        self.flakes('''
        def a():
            b = 1
        ''', m.UnusedVariable)

    def test_unusedVariableAsLocals(self):
        """
        Using locals() it is perfectly valid to have unused variables
        """
        self.flakes('''
        def a():
            b = 1
            return locals()
        ''')

    def test_unusedVariableNoLocals(self):
        """
        Using locals() in wrong scope should not matter
        """
        self.flakes('''
        def a():
            locals()
            def a():
                b = 1
                return
        ''', m.UnusedVariable)

    def test_assignToGlobal(self):
        """
        Assigning to a global and then not using that global is perfectly
        acceptable. Do not mistake it for an unused local variable.
        """
        self.flakes('''
        b = 0
        def a():
            global b
            b = 1
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_assignToNonlocal(self):
        """
        Assigning to a nonlocal and then not using that binding is perfectly
        acceptable. Do not mistake it for an unused local variable.
        """
        self.flakes('''
        b = b'0'
        def a():
            nonlocal b
            b = b'1'
        ''')

    def test_assignToMember(self):
        """
        Assigning to a member of another object and then not using that member
        variable is perfectly acceptable. Do not mistake it for an unused
        local variable.
        """
        # XXX: Adding this test didn't generate a failure. Maybe not
        # necessary?
        self.flakes('''
        class b:
            pass
        def a():
            b.foo = 1
        ''')

    def test_assignInForLoop(self):
        """
        Don't warn when a variable in a for loop is assigned to but not used.
        """
        self.flakes('''
        def f():
            for i in range(10):
                pass
        ''')

    def test_assignInListComprehension(self):
        """
        Don't warn when a variable in a list comprehension is
        assigned to but not used.
        """
        self.flakes('''
        def f():
            [None for i in range(10)]
        ''')

    def test_generatorExpression(self):
        """
        Don't warn when a variable in a generator expression is
        assigned to but not used.
        """
        self.flakes('''
        def f():
            (None for i in range(10))
        ''')

    def test_assignmentInsideLoop(self):
        """
        Don't warn when a variable assignment occurs lexically after its use.
        """
        self.flakes('''
        def f():
            x = None
            for i in range(10):
                if i > 2:
                    return x
                x = i * 2
        ''')

    def test_tupleUnpacking(self):
        """
        Don't warn when a variable included in tuple unpacking is unused. It's
        very common for variables in a tuple unpacking assignment to be unused
        in good Python code, so warning will only create false positives.
        """
        self.flakes('''
        def f(tup):
            (x, y) = tup
        ''')
        self.flakes('''
        def f():
            (x, y) = 1, 2
        ''', m.UnusedVariable, m.UnusedVariable)
        self.flakes('''
        def f():
            (x, y) = coords = 1, 2
            if x > 1:
                print(coords)
        ''')
        self.flakes('''
        def f():
            (x, y) = coords = 1, 2
        ''', m.UnusedVariable)
        self.flakes('''
        def f():
            coords = (x, y) = 1, 2
        ''', m.UnusedVariable)

    def test_listUnpacking(self):
        """
        Don't warn when a variable included in list unpacking is unused.
        """
        self.flakes('''
        def f(tup):
            [x, y] = tup
        ''')
        self.flakes('''
        def f():
            [x, y] = [1, 2]
        ''', m.UnusedVariable, m.UnusedVariable)

    def test_closedOver(self):
        """
        Don't warn when the assignment is used in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                return foo
            return bar
        ''')

    def test_doubleClosedOver(self):
        """
        Don't warn when the assignment is used in an inner function, even if
        that inner function itself is in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                def baz():
                    return foo
            return bar
        ''')

    def test_tracebackhideSpecialVariable(self):
        """
        Do not warn about unused local variable __tracebackhide__, which is
        a special variable for py.test.
        """
        self.flakes("""
            def helper():
                __tracebackhide__ = True
        """)

    def test_ifexp(self):
        """
        Test C{foo if bar else baz} statements.
        """
        self.flakes("a = 'moo' if True else 'oink'")
        self.flakes("a = foo if True else 'oink'", m.UndefinedName)
        self.flakes("a = 'moo' if True else bar", m.UndefinedName)

    def test_withStatementNoNames(self):
        """
        No warnings are emitted for using inside or after a nameless C{with}
        statement a name defined beforehand.
        """
        self.flakes('''
        from __future__ import with_statement
        bar = None
        with open("foo"):
            bar
        bar
        ''')

    def test_withStatementSingleName(self):
        """
        No warnings are emitted for using a name defined by a C{with} statement
        within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            bar
        bar
        ''')

    def test_withStatementAttributeName(self):
        """
        No warnings are emitted for using an attribute as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo.bar:
            pass
        ''')

    def test_withStatementSubscript(self):
        """
        No warnings are emitted for using a subscript as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[0]:
            pass
        ''')

    def test_withStatementSubscriptUndefined(self):
        """
        An undefined name warning is emitted if the subscript used as the
        target of a C{with} statement is not defined.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[bar]:
            pass
        ''', m.UndefinedName)

    def test_withStatementTupleNames(self):
        """
        No warnings are emitted for using any of the tuple of names defined by
        a C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as (bar, baz):
            bar, baz
        bar, baz
        ''')

    def test_withStatementListNames(self):
        """
        No warnings are emitted for using any of the list of names defined by a
        C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as [bar, baz]:
            bar, baz
        bar, baz
        ''')

    def test_withStatementComplicatedTarget(self):
        """
        If the target of a C{with} statement uses any or all of the valid forms
        for that part of the grammar (See
        U{http://docs.python.org/reference/compound_stmts.html#the-with-statement}),
        the names involved are checked both for definedness and any bindings
        created are respected in the suite of the statement and afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        c = d = e = g = h = i = None
        with open('foo') as [(a, b), c[d], e.f, g[h:i]]:
            a, b, c, d, e, g, h, i
        a, b, c, d, e, g, h, i
        ''')

    def test_withStatementSingleNameUndefined(self):
        """
        An undefined name warning is emitted if the name first defined by a
        C{with} statement is used before the C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        bar
        with open('foo') as bar:
            pass
        ''', m.UndefinedName)

    def test_withStatementTupleNamesUndefined(self):
        """
        An undefined name warning is emitted if a name first defined by a the
        tuple-unpacking form of the C{with} statement is used before the
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        baz
        with open('foo') as (bar, baz):
            pass
        ''', m.UndefinedName)

    def test_withStatementSingleNameRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by the name defined by a C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as bar:
            pass
        ''', m.RedefinedWhileUnused)

    def test_withStatementTupleNamesRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by one of the names defined by the tuple-unpacking form of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as (bar, baz):
            pass
        ''', m.RedefinedWhileUnused)

    def test_withStatementUndefinedInside(self):
        """
        An undefined name warning is emitted if a name is used inside the
        body of a C{with} statement without first being bound.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz
        ''', m.UndefinedName)

    def test_withStatementNameDefinedInBody(self):
        """
        A name defined in the body of a C{with} statement can be used after
        the body ends without warning.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz = 10
        baz
        ''')

    def test_withStatementUndefinedInExpression(self):
        """
        An undefined name warning is emitted if a name in the I{test}
        expression of a C{with} statement is undefined.
        """
        self.flakes('''
        from __future__ import with_statement
        with bar as baz:
            pass
        ''', m.UndefinedName)

        self.flakes('''
        from __future__ import with_statement
        with bar as bar:
            pass
        ''', m.UndefinedName)

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_dictComprehension(self):
        """
        Dict comprehensions are properly handled.
        """
        self.flakes('''
        a = {1: x for x in range(10)}
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_setComprehensionAndLiteral(self):
        """
        Set comprehensions are properly handled.
        """
        self.flakes('''
        a = {1, 2, 3}
        b = {x for x in range(10)}
        ''')

    def test_exceptionUsedInExcept(self):
        as_exc = ', ' if version_info < (2, 6) else ' as '
        self.flakes('''
        try: pass
        except Exception%se: e
        ''' % as_exc)

        self.flakes('''
        def download_review():
            try: pass
            except Exception%se: e
        ''' % as_exc)

    def test_exceptWithoutNameInFunction(self):
        """
        Don't issue false warning when an unnamed exception is used.
        Previously, there would be a false warning, but only when the
        try..except was in a function
        """
        self.flakes('''
        import tokenize
        def foo():
            try: pass
            except tokenize.TokenError: pass
        ''')

    def test_exceptWithoutNameInFunctionTuple(self):
        """
        Don't issue false warning when an unnamed exception is used.
        This example catches a tuple of exception types.
        """
        self.flakes('''
        import tokenize
        def foo():
            try: pass
            except (tokenize.TokenError, IndentationError): pass
        ''')

    def test_augmentedAssignmentImportedFunctionCall(self):
        """
        Consider a function that is called on the right part of an
        augassign operation to be used.
        """
        self.flakes('''
        from foo import bar
        baz = 0
        baz += bar()
        ''')

    @skipIf(version_info < (3, 3), 'new in Python 3.3')
    def test_yieldFromUndefined(self):
        """
        Test C{yield from} statement
        """
        self.flakes('''
        def bar():
            yield from foo()
        ''', m.UndefinedName)
