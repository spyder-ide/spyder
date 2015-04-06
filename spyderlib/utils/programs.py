# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

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
from spyderlib.utils import encoding
from spyderlib.py3compat import PY2, is_text_string


if os.name == 'nt':
    TEMPDIR = tempfile.gettempdir() + osp.sep + 'spyder'
else:
    username = encoding.to_unicode_from_fs(os.environ.get('USER'))
    TEMPDIR = tempfile.gettempdir() + osp.sep + 'spyder-' + username


def is_program_installed(basename):
    """Return program absolute path if installed in PATH
    Otherwise, return None"""
    for path in os.environ["PATH"].split(os.pathsep):
        abspath = osp.join(path, basename)
        if osp.isfile(abspath):
            return abspath


def find_program(basename):
    """Find program in PATH and return absolute path
    Try adding .exe or .bat to basename on Windows platforms
    (return None if not found)"""
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


def run_program(name, args=[], cwd=None):
    """Run program in a separate process"""
    assert isinstance(args, (tuple, list))
    path = find_program(name)
    if not path:
        raise RuntimeError("Program %s was not found" % name)
    subprocess.Popen([path]+args, cwd=cwd)


def start_file(filename):
    """Generalized os.startfile for all platforms supported by Qt
    (this function is simply wrapping QDesktopServices.openUrl)
    Returns True if successfull, otherwise returns False."""
    from spyderlib.qt.QtGui import QDesktopServices
    from spyderlib.qt.QtCore import QUrl

    # We need to use setUrl instead of setPath because this is the only
    # cross-platform way to open external files. setPath fails completely on
    # Mac and doesn't open non-ascii files on Linux.
    # Fixes Issue 740
    url = QUrl()
    url.setUrl(filename)
    return QDesktopServices.openUrl(url)


def python_script_exists(package=None, module=None):
    """Return absolute path if Python script exists (otherwise, return None)
    package=None -> module is in sys.path (standard library modules)"""
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
    """Run Python script in a separate process
    package=None -> module is in sys.path (standard library modules)"""
    assert module is not None
    assert isinstance(args, (tuple, list)) and isinstance(p_args, (tuple, list))
    path = python_script_exists(package, module)
    subprocess.Popen([sys.executable]+p_args+[path]+args)


def shell_split(text):
    """Split the string `text` using shell-like syntax
    
    This avoids breaking single/double-quoted strings (e.g. containing 
    strings with spaces). This function is almost equivalent to the shlex.split
    function (see standard library `shlex`) except that it is supporting 
    unicode strings (shlex does not support unicode until Python 2.7.3)."""
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
    """Run Python script in an external system terminal"""
    
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
            subprocess.Popen(cmd, shell=True, cwd=wdir)
        except WindowsError:
            from spyderlib.qt.QtGui import QMessageBox
            from spyderlib.baseconfig import _
            QMessageBox.critical(None, _('Run'),
                                 _("It was not possible to run this file in "
                                   "an external terminal"),
                                 QMessageBox.Ok)
    elif os.name == 'posix':
        cmd = 'gnome-terminal'
        if is_program_installed(cmd):
            run_program(cmd, ['--working-directory', wdir, '-x'] + p_args,
                        cwd=wdir)
            return
        cmd = 'konsole'
        if is_program_installed(cmd):
            run_program(cmd, ['--workdir', wdir, '-e'] + p_args,
                        cwd=wdir)
            return
        cmd = 'xfce4-terminal'
        if is_program_installed(cmd):
            run_program(cmd, ['--working-directory', wdir, '-x'] + p_args,
                        cwd=wdir)
            return
        cmd = 'xterm'
        if is_program_installed(cmd):
            run_program(cmd, ['-e'] + p_args + [wdir])
            return		
        # TODO: Add a fallback to OSX
    else:
        raise NotImplementedError


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
    """Return True if module *module_name* is installed
    
    If version is not None, checking module version 
    (module must have an attribute named '__version__')
    
    version may starts with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')
    
    interpreter: check if a module is installed with a given version 
    in a determined interpreter"""
    if interpreter:
        if not osp.isdir(TEMPDIR):
            os.mkdir(TEMPDIR)
        
        if osp.isfile(interpreter) and ('python' in interpreter):
            checkver = inspect.getsource(check_version)
            get_modver = inspect.getsource(get_module_version)
            ismod_inst = inspect.getsource(is_module_installed)
            fd, script = tempfile.mkstemp(suffix='.py', dir=TEMPDIR)
            with os.fdopen(fd, 'w') as f:
                f.write("# -*- coding: utf-8 -*-" + "\n\n")
                f.write("from distutils.version import LooseVersion" + "\n")
                f.write("import re" + "\n\n")
                f.write(checkver + "\n")
                f.write(get_modver + "\n")
                f.write(ismod_inst + "\n")
                if version:
                    f.write("print(is_module_installed('%s','%s'))"\
                            % (module_name, version))
                else:
                    f.write("print(is_module_installed('%s'))" % module_name)
            try:
                output, _err = subprocess.Popen([interpreter, script],
                                        stdout=subprocess.PIPE).communicate()
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


if __name__ == '__main__':
    print(find_program('hg'))
    print(shell_split('-q -o -a'))
    print(shell_split('-q "d:\\Python de xxxx\\t.txt" -o -a'))
    print(is_module_installed('IPython', '>=0.12'))
    print(is_module_installed('IPython', '>=0.13;<1.0'))
    print(is_module_installed('jedi', '>=0.7.0'))
