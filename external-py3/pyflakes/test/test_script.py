
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import sys
from io import StringIO
import tempfile
import os.path
import os

from unittest import TestCase

from pyflakes.scripts.pyflakes import checkPath

def withStderrTo(stderr, f):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f()
    finally:
        sys.stderr = outer

def fileWithContents(contents):
    _, fname = tempfile.mkstemp()
    mode = 'wt' if isinstance(contents, str) else 'wb'
    fd = open(fname, mode)
    fd.write(contents)
    fd.close()
    return fname

class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """
    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = fileWithContents("def foo():\n\tpass\n\t")
        self.assertFalse(checkPath(fName))


    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath('extremo'))
        self.assertEquals(err.getvalue(), 'extremo: No such file or directory\n')
        self.assertEquals(count, 1)


    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        def evaluate(source):
            exec(source)
        try:
            evaluate(source)
        except SyntaxError as e:
            self.assertTrue(e.text.count('\n') > 1)
        else:
            self.fail()

        sourcePath = fileWithContents(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEqual(count, 1)

        self.assertEqual(
            err.getvalue(),
            """\
%s:8: invalid syntax
    '''quux'''
           ^
""" % (sourcePath,))


    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        source = "def foo("
        sourcePath = fileWithContents(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: unexpected EOF while parsing
def foo(
         ^
""" % (sourcePath,))


    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        sourcePath = fileWithContents(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: non-default argument follows default argument
def foo(bar=baz, bax):
        ^
""" % (sourcePath,))


    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        sourcePath = fileWithContents(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: non-keyword arg after keyword arg
foo(bar=baz, bax)
             ^
""" % (sourcePath,))


    def test_permissionDenied(self):
        """
        If the a source file is not readable, this is reported on standard
        error.
        """
        sourcePath = fileWithContents('')
        os.chmod(sourcePath, 0)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "%s: Permission denied\n" % (sourcePath,))


    def test_misencodedFile(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        source = """\
# coding: ascii
x = "\N{SNOWMAN}"
""".encode('utf-8')
        sourcePath = fileWithContents(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath))
        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "%s: problem decoding source\n" % (sourcePath,))
