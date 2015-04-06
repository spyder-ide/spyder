"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import os
import sys
import shutil
import subprocess
import tempfile

from pyflakes.messages import UnusedImport
from pyflakes.reporter import Reporter
from pyflakes.api import (
    checkPath,
    checkRecursive,
    iterSourceCode,
)
from pyflakes.test.harness import TestCase

if sys.version_info < (3,):
    from cStringIO import StringIO
else:
    from io import StringIO
    unichr = chr


def withStderrTo(stderr, f, *args, **kwargs):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f(*args, **kwargs)
    finally:
        sys.stderr = outer


class Node(object):
    """
    Mock an AST node.
    """
    def __init__(self, lineno, col_offset=0):
        self.lineno = lineno
        self.col_offset = col_offset


class LoggingReporter(object):
    """
    Implementation of Reporter that just appends any error to a list.
    """

    def __init__(self, log):
        """
        Construct a C{LoggingReporter}.

        @param log: A list to append log messages to.
        """
        self.log = log

    def flake(self, message):
        self.log.append(('flake', str(message)))

    def unexpectedError(self, filename, message):
        self.log.append(('unexpectedError', filename, message))

    def syntaxError(self, filename, msg, lineno, offset, line):
        self.log.append(('syntaxError', filename, msg, lineno, offset, line))


class TestIterSourceCode(TestCase):
    """
    Tests for L{iterSourceCode}.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def makeEmptyFile(self, *parts):
        assert parts
        fpath = os.path.join(self.tempdir, *parts)
        fd = open(fpath, 'a')
        fd.close()
        return fpath

    def test_emptyDirectory(self):
        """
        There are no Python files in an empty directory.
        """
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_singleFile(self):
        """
        If the directory contains one Python file, C{iterSourceCode} will find
        it.
        """
        childpath = self.makeEmptyFile('foo.py')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [childpath])

    def test_onlyPythonSource(self):
        """
        Files that are not Python source files are not included.
        """
        self.makeEmptyFile('foo.pyc')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_recurses(self):
        """
        If the Python files are hidden deep down in child directories, we will
        find them.
        """
        os.mkdir(os.path.join(self.tempdir, 'foo'))
        apath = self.makeEmptyFile('foo', 'a.py')
        os.mkdir(os.path.join(self.tempdir, 'bar'))
        bpath = self.makeEmptyFile('bar', 'b.py')
        cpath = self.makeEmptyFile('c.py')
        self.assertEqual(
            sorted(iterSourceCode([self.tempdir])),
            sorted([apath, bpath, cpath]))

    def test_multipleDirectories(self):
        """
        L{iterSourceCode} can be given multiple directories.  It will recurse
        into each of them.
        """
        foopath = os.path.join(self.tempdir, 'foo')
        barpath = os.path.join(self.tempdir, 'bar')
        os.mkdir(foopath)
        apath = self.makeEmptyFile('foo', 'a.py')
        os.mkdir(barpath)
        bpath = self.makeEmptyFile('bar', 'b.py')
        self.assertEqual(
            sorted(iterSourceCode([foopath, barpath])),
            sorted([apath, bpath]))

    def test_explicitFiles(self):
        """
        If one of the paths given to L{iterSourceCode} is not a directory but
        a file, it will include that in its output.
        """
        epath = self.makeEmptyFile('e.py')
        self.assertEqual(list(iterSourceCode([epath])),
                         [epath])


class TestReporter(TestCase):
    """
    Tests for L{Reporter}.
    """

    def test_syntaxError(self):
        """
        C{syntaxError} reports that there was a syntax error in the source
        file.  It reports to the error stream and includes the filename, line
        number, error message, actual line of source and a caret pointing to
        where the error is.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, 7, 'bad line of source')
        self.assertEqual(
            ("foo.py:3:8: a problem\n"
             "bad line of source\n"
             "       ^\n"),
            err.getvalue())

    def test_syntaxErrorNoOffset(self):
        """
        C{syntaxError} doesn't include a caret pointing to the error if
        C{offset} is passed as C{None}.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, None,
                             'bad line of source')
        self.assertEqual(
            ("foo.py:3: a problem\n"
             "bad line of source\n"),
            err.getvalue())

    def test_multiLineSyntaxError(self):
        """
        If there's a multi-line syntax error, then we only report the last
        line.  The offset is adjusted so that it is relative to the start of
        the last line.
        """
        err = StringIO()
        lines = [
            'bad line of source',
            'more bad lines of source',
        ]
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, len(lines[0]) + 7,
                             '\n'.join(lines))
        self.assertEqual(
            ("foo.py:3:7: a problem\n" +
             lines[-1] + "\n" +
             "      ^\n"),
            err.getvalue())

    def test_unexpectedError(self):
        """
        C{unexpectedError} reports an error processing a source file.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.unexpectedError('source.py', 'error message')
        self.assertEqual('source.py: error message\n', err.getvalue())

    def test_flake(self):
        """
        C{flake} reports a code warning from Pyflakes.  It is exactly the
        str() of a L{pyflakes.messages.Message}.
        """
        out = StringIO()
        reporter = Reporter(out, None)
        message = UnusedImport('foo.py', Node(42), 'bar')
        reporter.flake(message)
        self.assertEqual(out.getvalue(), "%s\n" % (message,))


class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """

    def makeTempFile(self, content):
        """
        Make a temporary file containing C{content} and return a path to it.
        """
        _, fpath = tempfile.mkstemp()
        if not hasattr(content, 'decode'):
            content = content.encode('ascii')
        fd = open(fpath, 'wb')
        fd.write(content)
        fd.close()
        return fpath

    def assertHasErrors(self, path, errorList):
        """
        Assert that C{path} causes errors.

        @param path: A path to a file to check.
        @param errorList: A list of errors expected to be printed to stderr.
        """
        err = StringIO()
        count = withStderrTo(err, checkPath, path)
        self.assertEqual(
            (count, err.getvalue()), (len(errorList), ''.join(errorList)))

    def getErrors(self, path):
        """
        Get any warnings or errors reported by pyflakes for the file at C{path}.

        @param path: The path to a Python file on disk that pyflakes will check.
        @return: C{(count, log)}, where C{count} is the number of warnings or
            errors generated, and log is a list of those warnings, presented
            as structured data.  See L{LoggingReporter} for more details.
        """
        log = []
        reporter = LoggingReporter(log)
        count = checkPath(path, reporter)
        return count, log

    def test_legacyScript(self):
        from pyflakes.scripts import pyflakes as script_pyflakes
        self.assertIs(script_pyflakes.checkPath, checkPath)

    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = self.makeTempFile("def foo():\n\tpass\n\t")
        self.assertHasErrors(fName, [])

    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        count, errors = self.getErrors('extremo')
        self.assertEqual(count, 1)
        self.assertEqual(
            errors,
            [('unexpectedError', 'extremo', 'No such file or directory')])

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
        except SyntaxError:
            e = sys.exc_info()[1]
            self.assertTrue(e.text.count('\n') > 1)
        else:
            self.fail()

        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:8:11: invalid syntax
    '''quux'''
          ^
""" % (sourcePath,)])

    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        sourcePath = self.makeTempFile("def foo(")
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1:9: unexpected EOF while parsing
def foo(
        ^
""" % (sourcePath,)])

    def test_eofSyntaxErrorWithTab(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        sourcePath = self.makeTempFile("if True:\n\tfoo =")
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:2:7: invalid syntax
\tfoo =
\t     ^
""" % (sourcePath,)])

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
        sourcePath = self.makeTempFile(source)
        last_line = '       ^\n' if sys.version_info >= (3, 2) else ''
        column = '8:' if sys.version_info >= (3, 2) else ''
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1:%s non-default argument follows default argument
def foo(bar=baz, bax):
%s""" % (sourcePath, column, last_line)])

    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        sourcePath = self.makeTempFile(source)
        last_line = '            ^\n' if sys.version_info >= (3, 2) else ''
        column = '13:' if sys.version_info >= (3, 2) else ''
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1:%s non-keyword arg after keyword arg
foo(bar=baz, bax)
%s""" % (sourcePath, column, last_line)])

    def test_invalidEscape(self):
        """
        The invalid escape syntax raises ValueError in Python 2
        """
        ver = sys.version_info
        # ValueError: invalid \x escape
        sourcePath = self.makeTempFile(r"foo = '\xyz'")
        if ver < (3,):
            decoding_error = "%s: problem decoding source\n" % (sourcePath,)
        else:
            last_line = '      ^\n' if ver >= (3, 2) else ''
            # Column has been "fixed" since 3.2.4 and 3.3.1
            col = 1 if ver >= (3, 3, 1) or ((3, 2, 4) <= ver < (3, 3)) else 2
            decoding_error = """\
%s:1:7: (unicode error) 'unicodeescape' codec can't decode bytes \
in position 0-%d: truncated \\xXX escape
foo = '\\xyz'
%s""" % (sourcePath, col, last_line)
        self.assertHasErrors(
            sourcePath, [decoding_error])

    def test_permissionDenied(self):
        """
        If the source file is not readable, this is reported on standard
        error.
        """
        sourcePath = self.makeTempFile('')
        os.chmod(sourcePath, 0)
        count, errors = self.getErrors(sourcePath)
        self.assertEqual(count, 1)
        self.assertEqual(
            errors,
            [('unexpectedError', sourcePath, "Permission denied")])

    def test_pyflakesWarning(self):
        """
        If the source file has a pyflakes warning, this is reported as a
        'flake'.
        """
        sourcePath = self.makeTempFile("import foo")
        count, errors = self.getErrors(sourcePath)
        self.assertEqual(count, 1)
        self.assertEqual(
            errors, [('flake', str(UnusedImport(sourcePath, Node(1), 'foo')))])

    def test_encodedFileUTF8(self):
        """
        If source file declares the correct encoding, no error is reported.
        """
        SNOWMAN = unichr(0x2603)
        source = ("""\
# coding: utf-8
x = "%s"
""" % SNOWMAN).encode('utf-8')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(sourcePath, [])

    def test_misencodedFileUTF8(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = unichr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-8')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["%s: problem decoding source\n" % (sourcePath,)])

    def test_misencodedFileUTF16(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = unichr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-16')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["%s: problem decoding source\n" % (sourcePath,)])

    def test_checkRecursive(self):
        """
        L{checkRecursive} descends into each directory, finding Python files
        and reporting problems.
        """
        tempdir = tempfile.mkdtemp()
        os.mkdir(os.path.join(tempdir, 'foo'))
        file1 = os.path.join(tempdir, 'foo', 'bar.py')
        fd = open(file1, 'wb')
        fd.write("import baz\n".encode('ascii'))
        fd.close()
        file2 = os.path.join(tempdir, 'baz.py')
        fd = open(file2, 'wb')
        fd.write("import contraband".encode('ascii'))
        fd.close()
        log = []
        reporter = LoggingReporter(log)
        warnings = checkRecursive([tempdir], reporter)
        self.assertEqual(warnings, 2)
        self.assertEqual(
            sorted(log),
            sorted([('flake', str(UnusedImport(file1, Node(1), 'baz'))),
                    ('flake',
                     str(UnusedImport(file2, Node(1), 'contraband')))]))


class IntegrationTests(TestCase):
    """
    Tests of the pyflakes script that actually spawn the script.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.tempfilepath = os.path.join(self.tempdir, 'temp')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def getPyflakesBinary(self):
        """
        Return the path to the pyflakes binary.
        """
        import pyflakes
        package_dir = os.path.dirname(pyflakes.__file__)
        return os.path.join(package_dir, '..', 'bin', 'pyflakes')

    def runPyflakes(self, paths, stdin=None):
        """
        Launch a subprocess running C{pyflakes}.

        @param args: Command-line arguments to pass to pyflakes.
        @param kwargs: Options passed on to C{subprocess.Popen}.
        @return: C{(returncode, stdout, stderr)} of the completed pyflakes
            process.
        """
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(sys.path)
        command = [sys.executable, self.getPyflakesBinary()]
        command.extend(paths)
        if stdin:
            p = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate(stdin)
        else:
            p = subprocess.Popen(command, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate()
        rv = p.wait()
        if sys.version_info >= (3,):
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
        return (stdout, stderr, rv)

    def test_goodFile(self):
        """
        When a Python source file is all good, the return code is zero and no
        messages are printed to either stdout or stderr.
        """
        fd = open(self.tempfilepath, 'a')
        fd.close()
        d = self.runPyflakes([self.tempfilepath])
        self.assertEqual(d, ('', '', 0))

    def test_fileWithFlakes(self):
        """
        When a Python source file has warnings, the return code is non-zero
        and the warnings are printed to stdout.
        """
        fd = open(self.tempfilepath, 'wb')
        fd.write("import contraband\n".encode('ascii'))
        fd.close()
        d = self.runPyflakes([self.tempfilepath])
        expected = UnusedImport(self.tempfilepath, Node(1), 'contraband')
        self.assertEqual(d, ("%s\n" % expected, '', 1))

    def test_errors(self):
        """
        When pyflakes finds errors with the files it's given, (if they don't
        exist, say), then the return code is non-zero and the errors are
        printed to stderr.
        """
        d = self.runPyflakes([self.tempfilepath])
        error_msg = '%s: No such file or directory\n' % (self.tempfilepath,)
        self.assertEqual(d, ('', error_msg, 1))

    def test_readFromStdin(self):
        """
        If no arguments are passed to C{pyflakes} then it reads from stdin.
        """
        d = self.runPyflakes([], stdin='import contraband'.encode('ascii'))
        expected = UnusedImport('<stdin>', Node(1), 'contraband')
        self.assertEqual(d, ("%s\n" % expected, '', 1))
