import textwrap

from pyflakes import messages as m
from pyflakes.test.test_other import Test as TestOther
from pyflakes.test.test_imports import Test as TestImports
from pyflakes.test.test_undefined_names import Test as TestUndefinedNames
from pyflakes.test.harness import TestCase, skip


class _DoctestMixin(object):

    withDoctest = True

    def doctestify(self, input):
        lines = []
        for line in textwrap.dedent(input).splitlines():
            if line.strip() == '':
                pass
            elif (line.startswith(' ') or
                  line.startswith('except:') or
                  line.startswith('except ') or
                  line.startswith('finally:') or
                  line.startswith('else:') or
                  line.startswith('elif ')):
                line = "... %s" % line
            else:
                line = ">>> %s" % line
            lines.append(line)
        doctestificator = textwrap.dedent('''\
            def doctest_something():
                """
                   %s
                """
            ''')
        return doctestificator % "\n       ".join(lines)

    def flakes(self, input, *args, **kw):
        return super(_DoctestMixin, self).flakes(self.doctestify(input), *args, **kw)


class Test(TestCase):

    withDoctest = True

    def test_importBeforeDoctest(self):
        self.flakes("""
        import foo

        def doctest_stuff():
            '''
                >>> foo
            '''
        """)

    @skip("todo")
    def test_importBeforeAndInDoctest(self):
        self.flakes('''
        import foo

        def doctest_stuff():
            """
                >>> import foo
                >>> foo
            """

        foo
        ''', m.Redefined)

    def test_importInDoctestAndAfter(self):
        self.flakes('''
        def doctest_stuff():
            """
                >>> import foo
                >>> foo
            """

        import foo
        foo()
        ''')

    def test_offsetInDoctests(self):
        exc = self.flakes('''

        def doctest_stuff():
            """
                >>> x # line 5
            """

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 12)

    def test_offsetInLambdasInDoctests(self):
        exc = self.flakes('''

        def doctest_stuff():
            """
                >>> lambda: x # line 5
            """

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 20)

    def test_offsetAfterDoctests(self):
        exc = self.flakes('''

        def doctest_stuff():
            """
                >>> x = 5
            """

        x

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 8)
        self.assertEqual(exc.col, 0)

    def test_syntaxErrorInDoctest(self):
        exceptions = self.flakes(
            '''
            def doctest_stuff():
                """
                    >>> from # line 4
                    >>>     fortytwo = 42
                    >>> except Exception:
                """
            ''',
            m.DoctestSyntaxError,
            m.DoctestSyntaxError,
            m.DoctestSyntaxError).messages
        exc = exceptions[0]
        self.assertEqual(exc.lineno, 4)
        self.assertEqual(exc.col, 26)
        exc = exceptions[1]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 16)
        exc = exceptions[2]
        self.assertEqual(exc.lineno, 6)
        self.assertEqual(exc.col, 18)

    def test_indentationErrorInDoctest(self):
        exc = self.flakes('''
        def doctest_stuff():
            """
                >>> if True:
                ... pass
            """
        ''', m.DoctestSyntaxError).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 16)

    def test_offsetWithMultiLineArgs(self):
        (exc1, exc2) = self.flakes(
            '''
            def doctest_stuff(arg1,
                              arg2,
                              arg3):
                """
                    >>> assert
                    >>> this
                """
            ''',
            m.DoctestSyntaxError,
            m.UndefinedName).messages
        self.assertEqual(exc1.lineno, 6)
        self.assertEqual(exc1.col, 19)
        self.assertEqual(exc2.lineno, 7)
        self.assertEqual(exc2.col, 12)

    def test_doctestCanReferToFunction(self):
        self.flakes("""
        def foo():
            '''
                >>> foo
            '''
        """)

    def test_doctestCanReferToClass(self):
        self.flakes("""
        class Foo():
            '''
                >>> Foo
            '''
            def bar(self):
                '''
                    >>> Foo
                '''
        """)

    def test_noOffsetSyntaxErrorInDoctest(self):
        exceptions = self.flakes(
            '''
            def buildurl(base, *args, **kwargs):
                """
                >>> buildurl('/blah.php', ('a', '&'), ('b', '=')
                '/blah.php?a=%26&b=%3D'
                >>> buildurl('/blah.php', a='&', 'b'='=')
                '/blah.php?b=%3D&a=%26'
                """
                pass
            ''',
            m.DoctestSyntaxError,
            m.DoctestSyntaxError).messages
        exc = exceptions[0]
        self.assertEqual(exc.lineno, 4)
        exc = exceptions[1]
        self.assertEqual(exc.lineno, 6)

    def test_singleUnderscoreInDoctest(self):
        self.flakes('''
        def func():
            """A docstring

            >>> func()
            1
            >>> _
            1
            """
            return 1
        ''')


class TestOther(_DoctestMixin, TestOther):
    pass


class TestImports(_DoctestMixin, TestImports):

    def test_futureImport(self):
        """XXX This test can't work in a doctest"""

    def test_futureImportUsed(self):
        """XXX This test can't work in a doctest"""


class TestUndefinedNames(_DoctestMixin, TestUndefinedNames):

    def test_doubleNestingReportsClosestName(self):
        """
        Lines in doctest are a bit different so we can't use the test
        from TestUndefinedNames
        """
        exc = self.flakes('''
        def a():
            x = 1
            def b():
                x = 2 # line 7 in the file
                def c():
                    x
                    x = 3
                    return x
                return x
            return x
        ''', m.UndefinedLocal).messages[0]
        self.assertEqual(exc.message_args, ('x', 7))
