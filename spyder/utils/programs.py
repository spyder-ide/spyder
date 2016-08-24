# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Running programs utilities"""

from __future__ import print_function

from distutils.version import LooseVersion
import imp
import inspect
import os
import os.path as osp
import re
import subprocess
import sys
import tempfile

# Local imports
from spyder.utils import encoding
from spyder.py3compat import PY2, is_text_string


class ProgramError(Exception):
    pass


if os.name == 'nt':
    TEMPDIR = tempfile.gettempdir() + osp.sep + 'spyder'
else:
    username = encoding.to_unicode_from_fs(os.environ.get('USER'))
    TEMPDIR = tempfile.gettempdir() + osp.sep + 'spyder-' + username


def is_program_installed(basename):
    """
    Return program absolute path if installed in PATH.

    Otherwise, return None
    """
    for path in os.environ["PATH"].split(os.pathsep):
        abspath = osp.join(path, basename)
        if osp.isfile(abspath):
            return abspath


def find_program(basename):
    """
    Find program in PATH and return absolute path

    Try adding .exe or .bat to basename on Windows platforms
    (return None if not found)
    """
    names = [basename]
    if os.name == 'nt':
        # Windows platforms
        extensions = ('.exe', '.bat', '.cmd')
        if not basename.endswith(extensions):
            names = [basename+ext for ext in extensions]+[basename]
    for name in names:
        path = is_program_installed(name)
        if path:
            return path


def alter_subprocess_kwargs_by_platform(**kwargs):
    """
    Given a dict, populate kwargs to create a generally
    useful default setup for running subprocess processes
    on different platforms. For example, `close_fds` is
    set on posix and creation of a new console window is
    disabled on Windows.

    This function will alter the given kwargs and return
    the modified dict.
    """
    kwargs.setdefault('close_fds', os.name == 'posix')
    if os.name == 'nt':
        CONSOLE_CREATION_FLAGS = 0  # Default value
        # See: https://msdn.microsoft.com/en-us/library/windows/desktop/ms684863%28v=vs.85%29.aspx
        CREATE_NO_WINDOW = 0x08000000
        # We "or" them together
        CONSOLE_CREATION_FLAGS |= CREATE_NO_WINDOW
        kwargs.setdefault('creationflags', CONSOLE_CREATION_FLAGS)
    return kwargs


def run_shell_command(cmdstr, **subprocess_kwargs):
    """
    Execute the given shell command.
    
    Note that *args and **kwargs will be passed to the subprocess call.

    If 'shell' is given in subprocess_kwargs it must be True,
    otherwise ProgramError will be raised.
    .
    If 'executable' is not given in subprocess_kwargs, it will
    be set to the value of the SHELL environment variable.

    Note that stdin, stdout and stderr will be set by default
    to PIPE unless specified in subprocess_kwargs.

    :str cmdstr: The string run as a shell command.
    :subprocess_kwargs: These will be passed to subprocess.Popen.
    """
    if 'shell' in subprocess_kwargs and not subprocess_kwargs['shell']:
        raise ProgramError(
                'The "shell" kwarg may be omitted, but if '
                'provided it must be True.')
    else:
        subprocess_kwargs['shell'] = True

    if 'executable' not in subprocess_kwargs:
        subprocess_kwargs['executable'] = os.getenv('SHELL')

    for stream in ['stdin', 'stdout', 'stderr']:
        subprocess_kwargs.setdefault(stream, subprocess.PIPE)
    subprocess_kwargs = alter_subprocess_kwargs_by_platform(
            **subprocess_kwargs)
    return subprocess.Popen(cmdstr, **subprocess_kwargs)


def run_program(program, args=None, **subprocess_kwargs):
    """
    Run program in a separate process.

    NOTE: returns the process object created by
    `subprocess.Popen()`. This can be used with
    `proc.communicate()` for example.

    If 'shell' appears in the kwargs, it must be False,
    otherwise ProgramError will be raised.

    If only the program name is given and not the full path,
    a lookup will be performed to find the program. If the
    lookup fails, ProgramError will be raised.

    Note that stdin, stdout and stderr will be set by default
    to PIPE unless specified in subprocess_kwargs.

    :str program: The name of the program to run.
    :list args: The program arguments.
    :subprocess_kwargs: These will be passed to subprocess.Popen.
    """
    if 'shell' in subprocess_kwargs and subprocess_kwargs['shell']:
        raise ProgramError(
                "This function is only for non-shell programs, "
                "use run_shell_command() instead.")
    fullcmd = find_program(program)
    if not fullcmd:
        raise ProgramError("Program %s was not found" % program)
    # As per subprocess, we make a complete list of prog+args
    fullcmd = [fullcmd] + (args or [])
    for stream in ['stdin', 'stdout', 'stderr']:
        subprocess_kwargs.setdefault(stream, subprocess.PIPE)
    subprocess_kwargs = alter_subprocess_kwargs_by_platform(
            **subprocess_kwargs)
    return subprocess.Popen(fullcmd, **subprocess_kwargs)


def start_file(filename):
    """
    Generalized os.startfile for all platforms supported by Qt

    This function is simply wrapping QDesktopServices.openUrl

    Returns True if successfull, otherwise returns False.
    """
    from qtpy.QtCore import QUrl
    from qtpy.QtGui import QDesktopServices

    # We need to use setUrl instead of setPath because this is the only
    # cross-platform way to open external files. setPath fails completely on
    # Mac and doesn't open non-ascii files on Linux.
    # Fixes Issue 740
    url = QUrl()
    url.setUrl(filename)
    return QDesktopServices.openUrl(url)


def python_script_exists(package=None, module=None):
    """
    Return absolute path if Python script exists (otherwise, return None)
    package=None -> module is in sys.path (standard library modules)
    """
    assert module is not None
    try:
        if package is None:
            path = imp.find_module(module)[1]
        else:
            path = osp.join(imp.find_module(package)[1], module)+'.py'
    except ImportError:
        return
    if not osp.isfile(path):
        path += 'w'
    if osp.isfile(path):
        return path


def run_python_script(package=None, module=None, args=[], p_args=[]):
    """
    Run Python script in a separate process
    package=None -> module is in sys.path (standard library modules)
    """
    assert module is not None
    assert isinstance(args, (tuple, list)) and isinstance(p_args, (tuple, list))
    path = python_script_exists(package, module)
    run_program(sys.executable, p_args + [path] + args)


def shell_split(text):
    """
    Split the string `text` using shell-like syntax

    This avoids breaking single/double-quoted strings (e.g. containing
    strings with spaces). This function is almost equivalent to the shlex.split
    function (see standard library `shlex`) except that it is supporting
    unicode strings (shlex does not support unicode until Python 2.7.3).
    """
    assert is_text_string(text)  # in case a QString is passed...
    pattern = r'(\s+|(?<!\\)".*?(?<!\\)"|(?<!\\)\'.*?(?<!\\)\')'
    out = []
    for token in re.split(pattern, text):
        if token.strip():
            out.append(token.strip('"').strip("'"))
    return out


def get_python_args(fname, python_args, interact, debug, end_args):
    """Construct Python interpreter arguments"""
    p_args = []
    if python_args is not None:
        p_args += python_args.split()
    if interact:
        p_args.append('-i')
    if debug:
        p_args.extend(['-m', 'pdb'])
    if fname is not None:
        if os.name == 'nt' and debug:
            # When calling pdb on Windows, one has to replace backslashes by
            # slashes to avoid confusion with escape characters (otherwise, 
            # for example, '\t' will be interpreted as a tabulation):
            p_args.append(osp.normpath(fname).replace(os.sep, '/'))
        else:
            p_args.append(fname)
    if end_args:
        p_args.extend(shell_split(end_args))
    return p_args


def run_python_script_in_terminal(fname, wdir, args, interact,
                                  debug, python_args):
    """
    Run Python script in an external system terminal.

    :str wdir: working directory, may be empty.
    """
    
    # If fname has spaces on it it can't be ran on Windows, so we have to
    # enclose it in quotes. Also wdir can come with / as os.sep, so we
    # need to take care of it
    if os.name == 'nt':
        fname = '"' + fname + '"'
        wdir = wdir.replace('/', '\\')
    
    p_args = ['python']
    p_args += get_python_args(fname, python_args, interact, debug, args)
    
    if os.name == 'nt':
        cmd = 'start cmd.exe /c "cd %s && ' % wdir + ' '.join(p_args) + '"'
        # Command line and cwd have to be converted to the filesystem
        # encoding before passing them to subprocess, but only for
        # Python 2.
        # See http://bugs.python.org/issue1759845#msg74142 and Issue 1856
        if PY2:
            cmd = encoding.to_fs_from_unicode(cmd)
            wdir = encoding.to_fs_from_unicode(wdir)
        try:
            run_shell_command(cmd, cwd=wdir)
        except WindowsError:
            from qtpy.QtWidgets import QMessageBox
            from spyder.config.base import _
            QMessageBox.critical(None, _('Run'),
                                 _("It was not possible to run this file in "
                                   "an external terminal"),
                                 QMessageBox.Ok)
    elif os.name == 'posix':
        programs = [{'cmd': 'gnome-terminal',
                     'wdir-option': '--working-directory',
                     'execute-option': '-x'},
                    {'cmd': 'konsole',
                     'wdir-option': '--workdir',
                     'execute-option': '-e'},
                    {'cmd': 'xfce4-terminal',
                     'wdir-option': '--working-directory',
                     'execute-option': '-x'},
                    {'cmd': 'xterm',
                     'wdir-option': None,
                     'execute-option': '-e'},]
        for program in programs:
            if is_program_installed(program['cmd']):
                arglist = []
                if program['wdir-option'] and wdir:
                    arglist += [program['wdir-option'], wdir]
                arglist.append(program['execute-option'])
                arglist += p_args
                if wdir:
                    run_program(program['cmd'], arglist, cwd=wdir)
                else:
                    run_program(program['cmd'], arglist)
                return
        # TODO: Add a fallback to OSX
    else:
        raise NotImplementedError


def is_stable_version(version):
    """
    A stable version has no letters in the final component, but only numbers.

    Stable version example: 1.2, 1.3.4, 1.0.5
    Not stable version: 1.2alpha, 1.3.4beta, 0.1.0rc1, 3.0.0dev
    """
    if not isinstance(version, tuple):
        version = version.split('.')
    last_part = version[-1]

    if not re.search('[a-zA-Z]', last_part):
        return True
    else:
        return False


def check_version(actver, version, cmp_op):
    """
    Check version string of an active module against a required version.

    If dev/prerelease tags result in TypeError for string-number comparison,
    it is assumed that the dependency is satisfied.
    Users on dev branches are responsible for keeping their own packages up to
    date.
    
    Copyright (C) 2013  The IPython Development Team

    Distributed under the terms of the BSD License.
    """
    if isinstance(actver, tuple):
        actver = '.'.join([str(i) for i in actver])

    # Hacks needed so that LooseVersion understands that (for example)
    # version = '3.0.0' is in fact bigger than actver = '3.0.0rc1'
    if is_stable_version(version) and not is_stable_version(actver) and \
      actver.startswith(version) and version != actver:
        version = version + 'zz'
    elif is_stable_version(actver) and not is_stable_version(version) and \
      version.startswith(actver) and version != actver:
        actver = actver + 'zz'

    try:
        if cmp_op == '>':
            return LooseVersion(actver) > LooseVersion(version)
        elif cmp_op == '>=':
            return LooseVersion(actver) >= LooseVersion(version)
        elif cmp_op == '=':
            return LooseVersion(actver) == LooseVersion(version)
        elif cmp_op == '<':
            return LooseVersion(actver) < LooseVersion(version)
        elif cmp_op == '<=':
            return LooseVersion(actver) <= LooseVersion(version)
        else:
            return False
    except TypeError:
        return True


def get_module_version(module_name):
    """Return module version or None if version can't be retrieved."""
    mod = __import__(module_name)
    return getattr(mod, '__version__', getattr(mod, 'VERSION', None))


def is_module_installed(module_name, version=None, installed_version=None,
                        interpreter=None):
    """
    Return True if module *module_name* is installed

    If version is not None, checking module version
    (module must have an attribute named '__version__')

    version may starts with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')

    interpreter: check if a module is installed with a given version
    in a determined interpreter
    """
    if interpreter:
        if not osp.isdir(TEMPDIR):
            os.mkdir(TEMPDIR)
        
        if osp.isfile(interpreter) and ('python' in interpreter):
            checkver = inspect.getsource(check_version)
            get_modver = inspect.getsource(get_module_version)
            stable_ver = inspect.getsource(is_stable_version)
            ismod_inst = inspect.getsource(is_module_installed)
            fd, script = tempfile.mkstemp(suffix='.py', dir=TEMPDIR)
            with os.fdopen(fd, 'w') as f:
                f.write("# -*- coding: utf-8 -*-" + "\n\n")
                f.write("from distutils.version import LooseVersion" + "\n")
                f.write("import re" + "\n\n")
                f.write(stable_ver + "\n")
                f.write(checkver + "\n")
                f.write(get_modver + "\n")
                f.write(ismod_inst + "\n")
                if version:
                    f.write("print(is_module_installed('%s','%s'))"\
                            % (module_name, version))
                else:
                    f.write("print(is_module_installed('%s'))" % module_name)
            try:
                proc = run_program(interpreter, [script])
                output, _err = proc.communicate()
            except subprocess.CalledProcessError:
                return True
            if output:  # TODO: Check why output could be empty!
                return eval(output.decode())
            else:
                return False
        else:
            # Try to not take a wrong decision if there is no interpreter
            # available (needed for the change_pystartup method of ExtConsole
            # config page)
            return True
    else:
        if installed_version is None:
            try:
                actver = get_module_version(module_name)
            except ImportError:
                # Module is not installed
                return False
        else:
            actver = installed_version
        if actver is None and version is not None:
            return False
        elif version is None:
            return True
        else:
            if ';' in version:
                output = True
                for ver in version.split(';'):
                    output = output and is_module_installed(module_name, ver)
                return output
            match = re.search('[0-9]', version)
            assert match is not None, "Invalid version number"
            symb = version[:match.start()]
            if not symb:
                symb = '='
            assert symb in ('>=', '>', '=', '<', '<='),\
                    "Invalid version condition '%s'" % symb
            version = version[match.start():]
            
            return check_version(actver, version, symb)


def test_programs():
    assert find_program('git')
    assert shell_split('-q -o -a') == ['-q', '-o', '-a']
    assert shell_split('-q "d:\\Python de xxxx\\t.txt" -o -a') == \
           ['-q', 'd:\\Python de xxxx\\t.txt', '-o', '-a']
    assert check_version('0.9.4-1', '0.9.4', '>=')
    assert check_version('3.0.0rc1', '3.0.0', '<')
    assert check_version('1.0', '1.0b2', '>')
    assert is_module_installed('qtconsole', '>=4.0')
    assert not is_module_installed('IPython', '>=1.0;<3.0')
    assert is_module_installed('jedi', '>=0.7.0')


if __name__ == '__main__':
    test_programs()
