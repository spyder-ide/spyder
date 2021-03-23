# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Running programs utilities."""

from __future__ import print_function

# Standard library imports
from ast import literal_eval
from distutils.version import LooseVersion
from getpass import getuser
from textwrap import dedent
import glob
import importlib
import itertools
import os
import os.path as osp
import re
import subprocess
import sys
import tempfile
import threading
import time

# Third party imports
import pkg_resources
import psutil

# Local imports
from spyder.config.base import (is_stable_version, running_under_pytest,
                                get_home_dir)
from spyder.config.utils import is_anaconda
from spyder.py3compat import PY2, is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils.misc import get_python_executable


HERE = osp.abspath(osp.dirname(__file__))


class ProgramError(Exception):
    pass


def get_temp_dir(suffix=None):
    """
    Return temporary Spyder directory, checking previously that it exists.
    """
    to_join = [tempfile.gettempdir()]

    if os.name == 'nt':
        to_join.append('spyder')
    else:
        username = encoding.to_unicode_from_fs(getuser())
        to_join.append('spyder-' + username)

    if suffix is not None:
        to_join.append(suffix)

    tempdir = osp.join(*to_join)

    if not osp.isdir(tempdir):
        os.mkdir(tempdir)

    return tempdir


def is_program_installed(basename):
    """
    Return program absolute path if installed in PATH.
    Otherwise, return None.

    Also searches specific platform dependent paths that are not already in
    PATH. This permits general use without assuming user profiles are
    sourced (e.g. .bash_Profile), such as when login shells are not used to
    launch Spyder.

    On macOS systems, a .app is considered installed if it exists.
    """
    home = get_home_dir()
    req_paths = []
    if sys.platform == 'darwin':
        if basename.endswith('.app') and osp.exists(basename):
            return basename

        pyenv = [
            osp.join('/usr', 'local', 'bin'),
            osp.join(home, '.pyenv', 'bin')
        ]

        # Prioritize Anaconda before Miniconda; local before global.
        a = [osp.join(home, 'opt'), '/opt']
        b = ['anaconda', 'miniconda', 'anaconda3', 'miniconda3']
        conda = [osp.join(*p, 'condabin') for p in itertools.product(a, b)]

        req_paths.extend(pyenv + conda)

    elif sys.platform.startswith('linux'):
        pyenv = [
            osp.join('/usr', 'local', 'bin'),
            osp.join(home, '.pyenv', 'bin')
        ]

        a = [home, '/opt']
        b = ['anaconda', 'miniconda', 'anaconda3', 'miniconda3']
        conda = [osp.join(*p, 'condabin') for p in itertools.product(a, b)]

        req_paths.extend(pyenv + conda)

    elif os.name == 'nt':
        pyenv = [osp.join(home, '.pyenv', 'pyenv-win', 'bin')]

        a = [home, 'C:\\', osp.join('C:\\', 'ProgramData')]
        b = ['Anaconda', 'Miniconda', 'Anaconda3', 'Miniconda3']
        conda = [osp.join(*p, 'condabin') for p in itertools.product(a, b)]

        req_paths.extend(pyenv + conda)

    for path in os.environ['PATH'].split(os.pathsep) + req_paths:
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


def get_full_command_for_program(path):
    """
    Return the list of tokens necessary to open the program
    at a given path.

    On macOS systems, this function prefixes .app paths with
    'open -a', which is necessary to run the application.

    On all other OS's, this function has no effect.

    :str path: The path of the program to run.
    :return: The list of tokens necessary to run the program.
    """
    if sys.platform == 'darwin' and path.endswith('.app'):
        return ['open', '-a', path]
    return [path]


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

        # ensure Windows subprocess environment has SYSTEMROOT
        if kwargs.get('env') is not None:
            # Is SYSTEMROOT, SYSTEMDRIVE in env? case insensitive
            for env_var in ['SYSTEMROOT', 'SYSTEMDRIVE']:
                if env_var not in map(str.upper, kwargs['env'].keys()):
                    # Add from os.environ
                    for k, v in os.environ.items():
                        if env_var == k.upper():
                            kwargs['env'].update({k: v})
                            break  # don't risk multiple values
    else:
        # linux and macOS
        if kwargs.get('env') is not None:
            if 'HOME' not in kwargs['env']:
                kwargs['env'].update({'HOME': get_home_dir()})

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

    # Don't pass SHELL to subprocess on Windows because it makes this
    # fumction fail in Git Bash (where SHELL is declared; other Windows
    # shells don't set it).
    if not os.name == 'nt':
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
    fullcmd = get_full_command_for_program(fullcmd) + (args or [])
    for stream in ['stdin', 'stdout', 'stderr']:
        subprocess_kwargs.setdefault(stream, subprocess.PIPE)
    subprocess_kwargs = alter_subprocess_kwargs_by_platform(
            **subprocess_kwargs)
    return subprocess.Popen(fullcmd, **subprocess_kwargs)


def parse_linux_desktop_entry(fpath):
    """Load data from desktop entry with xdg specification."""
    from xdg.DesktopEntry import DesktopEntry

    try:
        entry = DesktopEntry(fpath)
        entry_data = {}
        entry_data['name'] = entry.getName()
        entry_data['icon_path'] = entry.getIcon()
        entry_data['exec'] = entry.getExec()
        entry_data['type'] = entry.getType()
        entry_data['hidden'] = entry.getHidden()
        entry_data['fpath'] = fpath
    except Exception:
        entry_data = {
            'name': '',
            'icon_path': '',
            'hidden': '',
            'exec': '',
            'type': '',
            'fpath': fpath
        }

    return entry_data


def _get_mac_application_icon_path(app_bundle_path):
    """Parse mac application bundle and return path for *.icns file."""
    import plistlib
    contents_path = info_path = os.path.join(app_bundle_path, 'Contents')
    info_path = os.path.join(contents_path, 'Info.plist')

    pl = {}
    if os.path.isfile(info_path):
        try:
            # readPlist is deprecated but needed for py27 compat
            pl = plistlib.readPlist(info_path)
        except Exception:
            pass

    icon_file = pl.get('CFBundleIconFile')
    icon_path = None
    if icon_file:
        icon_path = os.path.join(contents_path, 'Resources', icon_file)

        # Some app bundles seem to list the icon name without extension
        if not icon_path.endswith('.icns'):
            icon_path = icon_path + '.icns'

        if not os.path.isfile(icon_path):
            icon_path = None

    return icon_path


def get_username():
    """Return current session username."""
    if os.name == 'nt':
        username = os.getlogin()
    else:
        import pwd
        username = pwd.getpwuid(os.getuid())[0]

    return username


def _get_win_reg_info(key_path, hive, flag, subkeys):
    """
    See: https://stackoverflow.com/q/53132434
    """
    import winreg

    reg = winreg.ConnectRegistry(None, hive)
    software_list = []
    try:
        key = winreg.OpenKey(reg, key_path, 0, winreg.KEY_READ | flag)
        count_subkey = winreg.QueryInfoKey(key)[0]

        for index in range(count_subkey):
            software = {}
            try:
                subkey_name = winreg.EnumKey(key, index)
                if not (subkey_name.startswith('{')
                        and subkey_name.endswith('}')):
                    software['key'] = subkey_name
                    subkey = winreg.OpenKey(key, subkey_name)
                    for property in subkeys:
                        try:
                            value = winreg.QueryValueEx(subkey, property)[0]
                            software[property] = value
                        except EnvironmentError:
                            software[property] = ''
                    software_list.append(software)
            except EnvironmentError:
                continue
    except Exception:
        pass

    return software_list


def _clean_win_application_path(path):
    """Normalize windows path and remove extra quotes."""
    path = path.replace('\\', '/').lower()
    # Check for quotes at start and end
    if path[0] == '"' and path[-1] == '"':
        path = literal_eval(path)
    return path


def _get_win_applications():
    """Return all system installed windows applications."""
    import winreg

    # See:
    # https://docs.microsoft.com/en-us/windows/desktop/shell/app-registration
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths'

    # Hive and flags
    hfs = [
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    ]
    subkeys = [None]
    sort_key = 'key'
    app_paths = {}
    _apps = [_get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        if software[None]:
            key = software['key'].capitalize().replace('.exe', '')
            expanded_fpath = os.path.expandvars(software[None])
            expanded_fpath = _clean_win_application_path(expanded_fpath)
            app_paths[key] = expanded_fpath

    # See:
    # https://www.blog.pythonlibrary.org/2010/03/03/finding-installed-software-using-python/
    # https://stackoverflow.com/q/53132434
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall'
    subkeys = ['DisplayName', 'InstallLocation', 'DisplayIcon']
    sort_key = 'DisplayName'
    apps = {}
    _apps = [_get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        location = software['InstallLocation']
        name = software['DisplayName']
        icon = software['DisplayIcon']
        key = software['key']
        if name and icon:
            icon = icon.replace('"', '')
            icon = icon.split(',')[0]

            if location == '' and icon:
                location = os.path.dirname(icon)

            if not os.path.isfile(icon):
                icon = ''

            if location and os.path.isdir(location):
                files = [f for f in os.listdir(location)
                         if os.path.isfile(os.path.join(location, f))]
                if files:
                    for fname in files:
                        fn_low = fname.lower()
                        valid_file = fn_low.endswith(('.exe', '.com', '.bat'))
                        if valid_file and not fn_low.startswith('unins'):
                            fpath = os.path.join(location, fname)
                            expanded_fpath = os.path.expandvars(fpath)
                            expanded_fpath = _clean_win_application_path(
                                expanded_fpath)
                            apps[name + ' (' + fname + ')'] = expanded_fpath
    # Join data
    values = list(zip(*apps.values()))[-1]
    for name, fpath in app_paths.items():
        if fpath not in values:
            apps[name] = fpath

    return apps


def _get_linux_applications():
    """Return all system installed linux applications."""
    # See:
    # https://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
    # https://askubuntu.com/q/433609
    apps = {}
    desktop_app_paths = [
        '/usr/share/**/*.desktop',
        '~/.local/share/**/*.desktop',
    ]
    all_entries_data = []
    for path in desktop_app_paths:
        fpaths = glob.glob(path)
        for fpath in fpaths:
            entry_data = parse_linux_desktop_entry(fpath)
            all_entries_data.append(entry_data)

    for entry_data in sorted(all_entries_data, key=lambda x: x['name']):
        if not entry_data['hidden'] and entry_data['type'] == 'Application':
            apps[entry_data['name']] = entry_data['fpath']

    return apps


def _get_mac_applications():
    """Return all system installed osx applications."""
    apps = {}
    app_folders = [
        '/**/*.app',
        '/Users/{}/**/*.app'.format(get_username())
    ]

    fpaths = []
    for path in app_folders:
        fpaths += glob.glob(path)

    for fpath in fpaths:
        if os.path.isdir(fpath):
            name = os.path.basename(fpath).split('.app')[0]
            apps[name] = fpath

    return apps


def get_application_icon(fpath):
    """Return application icon or default icon if not found."""
    from qtpy.QtGui import QIcon
    from spyder.utils.icon_manager import ima

    if os.path.isfile(fpath) or os.path.isdir(fpath):
        icon = ima.icon('no_match')
        if sys.platform == 'darwin':
            icon_path = _get_mac_application_icon_path(fpath)
            if icon_path and os.path.isfile(icon_path):
                icon = QIcon(icon_path)
        elif os.name == 'nt':
            pass
        else:
            entry_data = parse_linux_desktop_entry(fpath)
            icon_path = entry_data['icon_path']
            if icon_path:
                if os.path.isfile(icon_path):
                    icon = QIcon(icon_path)
                else:
                    icon = QIcon.fromTheme(icon_path)
    else:
        icon = ima.icon('help')

    return icon


def get_installed_applications():
    """
    Return all system installed applications.

    The return value is a list of tuples where the first item is the icon path
    and the second item is the program executable path.
    """
    apps = {}
    if sys.platform == 'darwin':
        apps = _get_mac_applications()
    elif os.name == 'nt':
        apps = _get_win_applications()
    else:
        apps = _get_linux_applications()

    if sys.platform == 'darwin':
        apps = {key: val for (key, val) in apps.items() if osp.isdir(val)}
    else:
        apps = {key: val for (key, val) in apps.items() if osp.isfile(val)}

    return apps


def open_files_with_application(app_path, fnames):
    """
    Generalized method for opening files with a specific application.

    Returns a dictionary of the command used and the return code.
    A code equal to 0 means the application executed successfully.
    """
    return_codes = {}

    if os.name == 'nt':
        fnames = [fname.replace('\\', '/') for fname in fnames]

    if sys.platform == 'darwin':
        if not (app_path.endswith('.app') and os.path.isdir(app_path)):
            raise ValueError('`app_path`  must point to a valid OSX '
                             'application!')
        cmd = ['open', '-a', app_path] + fnames
        try:
            return_code = subprocess.call(cmd)
        except Exception:
            return_code = 1
        return_codes[' '.join(cmd)] = return_code
    elif os.name == 'nt':
        if not (app_path.endswith(('.exe', '.bat', '.com', '.cmd'))
                and os.path.isfile(app_path)):
            raise ValueError('`app_path`  must point to a valid Windows '
                             'executable!')
        cmd = [app_path] + fnames
        try:
            return_code = subprocess.call(cmd)
        except OSError:
            return_code = 1
        return_codes[' '.join(cmd)] = return_code
    else:
        if not (app_path.endswith('.desktop') and os.path.isfile(app_path)):
            raise ValueError('`app_path` must point to a valid Linux '
                             'application!')

        entry = parse_linux_desktop_entry(app_path)
        app_path = entry['exec']
        multi = []
        extra = []
        if len(fnames) == 1:
            fname = fnames[0]
            if '%u' in app_path:
                cmd = app_path.replace('%u', fname)
            elif '%f' in app_path:
                cmd = app_path.replace('%f', fname)
            elif '%U' in app_path:
                cmd = app_path.replace('%U', fname)
            elif '%F' in app_path:
                cmd = app_path.replace('%F', fname)
            else:
                cmd = app_path
                extra = fnames
        elif len(fnames) > 1:
            if '%U' in app_path:
                cmd = app_path.replace('%U', ' '.join(fnames))
            elif '%F' in app_path:
                cmd = app_path.replace('%F', ' '.join(fnames))
            if '%u' in app_path:
                for fname in fnames:
                    multi.append(app_path.replace('%u', fname))
            elif '%f' in app_path:
                for fname in fnames:
                    multi.append(app_path.replace('%f', fname))
            else:
                cmd = app_path
                extra = fnames

        if multi:
            for cmd in multi:
                try:
                    return_code = subprocess.call([cmd], shell=True)
                except Exception:
                    return_code = 1
                return_codes[cmd] = return_code
        else:
            try:
                return_code = subprocess.call([cmd] + extra, shell=True)
            except Exception:
                return_code = 1
            return_codes[cmd] = return_code

    return return_codes


def python_script_exists(package=None, module=None):
    """
    Return absolute path if Python script exists (otherwise, return None)
    package=None -> module is in sys.path (standard library modules)
    """
    assert module is not None
    if package is None:
        spec = importlib.util.find_spec(module)
        if spec:
            path = spec.origin
        else:
            path = None
    else:
        spec = importlib.util.find_spec(package)
        if spec:
            path = osp.join(spec.origin, module)+'.py'
        else:
            path = None
    if path:
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
                                  debug, python_args, executable=None):
    """
    Run Python script in an external system terminal.

    :str wdir: working directory, may be empty.
    """
    if executable is None:
        executable = get_python_executable()

    # If fname or python_exe contains spaces, it can't be ran on Windows, so we
    # have to enclose them in quotes. Also wdir can come with / as os.sep, so
    # we need to take care of it.
    if os.name == 'nt':
        fname = '"' + fname + '"'
        wdir = wdir.replace('/', '\\')
        executable = '"' + executable + '"'

    p_args = [executable]
    p_args += get_python_args(fname, python_args, interact, debug, args)

    if os.name == 'nt':
        cmd = 'start cmd.exe /K "'
        if wdir:
            cmd += 'cd ' + wdir + ' && '
        cmd += ' '.join(p_args) + '"' + ' ^&^& exit'
        # Command line and cwd have to be converted to the filesystem
        # encoding before passing them to subprocess, but only for
        # Python 2.
        # See https://bugs.python.org/issue1759845#msg74142 and
        # spyder-ide/spyder#1856.
        if PY2:
            cmd = encoding.to_fs_from_unicode(cmd)
            wdir = encoding.to_fs_from_unicode(wdir)
        try:
            if wdir:
                run_shell_command(cmd, cwd=wdir)
            else:
                run_shell_command(cmd)
        except WindowsError:
            from qtpy.QtWidgets import QMessageBox
            from spyder.config.base import _
            QMessageBox.critical(None, _('Run'),
                                 _("It was not possible to run this file in "
                                   "an external terminal"),
                                 QMessageBox.Ok)
    elif sys.platform.startswith('linux'):
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
    elif sys.platform == 'darwin':
        f = tempfile.NamedTemporaryFile('wt', prefix='run_spyder_',
                                        suffix='.sh', dir=get_temp_dir(),
                                        delete=False)
        if wdir:
            f.write('cd {}\n'.format(wdir))
        f.write(' '.join(p_args))
        f.close()
        os.chmod(f.name, 0o777)

        def run_terminal_thread():
            proc = run_shell_command('open -a Terminal.app ' + f.name)
            # Prevent race condition
            time.sleep(3)
            proc.wait()
            os.remove(f.name)

        thread = threading.Thread(target=run_terminal_thread)
        thread.start()
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
    ver = getattr(mod, '__version__', getattr(mod, 'VERSION', None))
    if not ver:
        ver = get_package_version(module_name)
    return ver


def get_package_version(package_name):
    """Return package version or None if version can't be retrieved."""

    # When support for Python 3.7 and below is dropped, this can be replaced
    # with the built-in importlib.metadata.version
    try:
        ver = pkg_resources.get_distribution(package_name).version
        return ver
    except pkg_resources.DistributionNotFound:
        return None


def is_module_installed(module_name, version=None, interpreter=None):
    """
    Return True if module ``module_name`` is installed

    If ``version`` is not None, checks that the module's installed version is
    consistent with ``version``. The module must have an attribute named
    '__version__' or 'VERSION'.

    version may start with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')

    If ``interpreter`` is not None, checks if a module is installed with a
    given ``version`` in the ``interpreter``'s environment. Otherwise checks
    in Spyder's environment.
    """
    if interpreter is not None:
        if is_python_interpreter(interpreter):
            cmd = dedent("""
                try:
                    import {} as mod
                except Exception:
                    print('No Module')  # spyder: test-skip
                print(getattr(mod, '__version__', getattr(mod, 'VERSION', None)))  # spyder: test-skip
                """).format(module_name)
            try:
                # use clean environment
                proc = run_program(interpreter, ['-c', cmd], env={})
                stdout, stderr = proc.communicate()
                stdout = stdout.decode().strip()
            except Exception:
                return False

            if 'No Module' in stdout:
                return False
            elif stdout != 'None':
                # the module is installed and it has a version attribute
                module_version = stdout
            else:
                module_version = None
        else:
            # Try to not take a wrong decision if interpreter check fails
            return True
    else:
        # interpreter is None, just get module version in Spyder environment
        try:
            module_version = get_module_version(module_name)
        except Exception:
            # Module is not installed
            return False

        # This can happen if a package was not uninstalled correctly. For
        # instance, if it's __pycache__ main directory is left behind.
        try:
            mod = __import__(module_name)
            if not getattr(mod, '__file__', None):
                return False
        except Exception:
            pass

    if version is None:
        return True
    else:
        if ';' in version:
            versions = version.split(';')
        else:
            versions = [version]

        output = True
        for _ver in versions:
            match = re.search(r'[0-9]', _ver)
            assert match is not None, "Invalid version number"
            symb = _ver[:match.start()]
            if not symb:
                symb = '='
            assert symb in ('>=', '>', '=', '<', '<='),\
                "Invalid version condition '%s'" % symb
            ver = _ver[match.start():]
            output = output and check_version(module_version, ver, symb)
        return output


def is_python_interpreter_valid_name(filename):
    """Check that the python interpreter file has a valid name."""
    pattern = r'.*python(\d\.?\d*)?(w)?(.exe)?$'
    if re.match(pattern, filename, flags=re.I) is None:
        return False
    else:
        return True


def is_python_interpreter(filename):
    """Evaluate whether a file is a python interpreter or not."""
    real_filename = os.path.realpath(filename)  # To follow symlink if existent
    if (not osp.isfile(real_filename) or
        not is_python_interpreter_valid_name(filename)):
        return False
    elif is_pythonw(filename):
        if os.name == 'nt':
            # pythonw is a binary on Windows
            if not encoding.is_text_file(real_filename):
                return True
            else:
                return False
        elif sys.platform == 'darwin':
            # pythonw is a text file in Anaconda but a binary in
            # the system
            if is_anaconda() and encoding.is_text_file(real_filename):
                return True
            elif not encoding.is_text_file(real_filename):
                return True
            else:
                return False
        else:
            # There's no pythonw in other systems
            return False
    elif encoding.is_text_file(real_filename):
        # At this point we can't have a text file
        return False
    else:
        return check_python_help(filename)


def is_pythonw(filename):
    """Check that the python interpreter has 'pythonw'."""
    pattern = r'.*python(\d\.?\d*)?w(.exe)?$'
    if re.match(pattern, filename, flags=re.I) is None:
        return False
    else:
        return True


def check_python_help(filename):
    """Check that the python interpreter can compile and provide the zen."""
    try:
        proc = run_program(filename, ['-c', 'import this'], env={})
        stdout, _ = proc.communicate()
        stdout = to_text_string(stdout)
        valid_lines = [
            'Beautiful is better than ugly.',
            'Explicit is better than implicit.',
            'Simple is better than complex.',
            'Complex is better than complicated.',
        ]
        if all(line in stdout for line in valid_lines):
            return True
        else:
            return False
    except Exception:
        return False


def is_spyder_process(pid):
    """
    Test whether given PID belongs to a Spyder process.

    This is checked by testing the first three command line arguments. This
    function returns a bool. If there is no process with this PID or its
    command line cannot be accessed (perhaps because the process is owned by
    another user), then the function returns False.
    """
    try:
        p = psutil.Process(int(pid))

        # Valid names for main script
        names = set(['spyder', 'spyder3', 'spyder.exe', 'spyder3.exe',
                     'bootstrap.py', 'spyder-script.py', 'Spyder.launch.pyw'])
        if running_under_pytest():
            names.add('runtests.py')

        # Check the first three command line arguments
        arguments = set(os.path.basename(arg) for arg in p.cmdline()[:3])
        conditions = [names & arguments]
        return any(conditions)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_interpreter_info(path):
    """Return version information of the selected Python interpreter."""
    try:
        out, __ = run_program(path, ['-V']).communicate()
        out = out.decode()
    except Exception:
        out = ''
    return out.strip()


def find_git():
    """Find git executable in the system."""
    if sys.platform == 'darwin':
        proc = subprocess.run(
            osp.join(HERE, "check-git.sh"), capture_output=True)
        if proc.returncode != 0:
            return None
        return find_program('git')
    else:
        return find_program('git')
