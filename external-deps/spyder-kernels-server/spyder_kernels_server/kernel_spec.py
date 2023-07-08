# -*- coding: utf-8 -*-
import sys
import os
import os.path as osp
from glob import glob
import itertools
import locale

from jupyter_client.kernelspec import KernelSpec
    
def get_python_executable():
    """Return path to Spyder Python executable"""
    executable = sys.executable.replace("pythonw.exe", "python.exe")
    if executable.endswith("spyder.exe"):
        # py2exe distribution
        executable = "python.exe"
    return executable


def get_kernel_spec(kernel_spec_dict):
    
    kernel_spec = KernelSpec()
    for key in kernel_spec_dict:
        setattr(kernel_spec, key, kernel_spec_dict[key])
   
    # Python interpreter used to start kernels
    if (kernel_spec.pyexec is None):
        pyexec = get_python_executable()
    else:
        pyexec = kernel_spec.pyexec

    # Command used to start kernels
    kernel_cmd = [
        pyexec,
        # This is necessary to avoid a spurious message on Windows.
        # Fixes spyder-ide/spyder#20800.
        '-Xfrozen_modules=off',
        '-m', 'spyder_kernels.console',
        '-f', '{connection_file}'
    ]

    # Part of spyder-ide/spyder#11819
    is_different = is_different_interpreter(pyexec)
    if is_different and is_conda_env(pyexec=pyexec):
        # If executable is a conda environment and different from Spyder's
        # runtime environment, we need to activate the environment to run
        # spyder-kernels
        kernel_cmd[:0] = [
            find_conda(), 'run',
            '-p', get_conda_env_path(pyexec),
        ]
    kernel_spec.argv = kernel_cmd

    return kernel_spec


# All the functions below are used to activate conda
# They are copied here from spyder for now to avoid importing spyder

WINDOWS = os.name == 'nt'


def is_different_interpreter(pyexec):
    """Check that pyexec is a different interpreter from sys.executable."""
    # Paths may be symlinks
    real_pyexe = osp.realpath(pyexec)
    real_sys_exe = osp.realpath(sys.executable)
    executable_validation = osp.basename(real_pyexe).startswith('python')
    directory_validation = osp.dirname(real_pyexe) != osp.dirname(real_sys_exe)
    return directory_validation and executable_validation


def add_quotes(path):
    """Return quotes if needed for spaces on path."""
    quotes = '"' if ' ' in path and '"' not in path else ''
    return '{quotes}{path}{quotes}'.format(quotes=quotes, path=path)


def get_conda_env_path(pyexec, quote=False):
    """
    Return the full path to the conda environment from give python executable.

    If `quote` is True, then quotes are added if spaces are found in the path.
    """
    pyexec = pyexec.replace('\\', '/')
    if os.name == 'nt':
        conda_env = os.path.dirname(pyexec)
    else:
        conda_env = os.path.dirname(os.path.dirname(pyexec))

    if quote:
        conda_env = add_quotes(conda_env)

    return conda_env


def is_conda_env(prefix=None, pyexec=None):
    """Check if prefix or python executable are in a conda environment."""
    if pyexec is not None:
        pyexec = pyexec.replace('\\', '/')

    if (prefix is None and pyexec is None) or (prefix and pyexec):
        raise ValueError('Only `prefix` or `pyexec` should be provided!')

    if pyexec and prefix is None:
        prefix = get_conda_env_path(pyexec).replace('\\', '/')

    return os.path.exists(os.path.join(prefix, 'conda-meta'))


def is_conda_based_app(pyexec=sys.executable):
    """
    Check if Spyder is running from the conda-based installer by looking for
    the `spyder-menu.json` file.

    If a Python executable is provided, checks if it is in a conda-based
    installer environment or the root environment thereof.
    """
    real_pyexec = osp.realpath(pyexec)  # pyexec may be symlink
    if os.name == 'nt':
        env_path = osp.dirname(real_pyexec)
    else:
        env_path = osp.dirname(osp.dirname(real_pyexec))

    menu_rel_path = '/Menu/spyder-menu.json'
    if (
        osp.exists(env_path + menu_rel_path)
        or glob(env_path + '/envs/*' + menu_rel_path)
    ):
        return True
    else:
        return False

def is_type_text_string(obj):
    """Return True if `obj` is type text string, False if it is anything else,
    like an instance of a class that extends the basestring class."""
    return type(obj) in [str, bytes]

def is_text_string(obj):
    """Return True if `obj` is a text string, False if it is anything else,
    like binary data (Python 3) or QString (PyQt API #1)"""
    return isinstance(obj, str)

def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    return isinstance(obj, bytes)

def is_string(obj):
    """Return True if `obj` is a text or binary Python string object,
    False if it is anything else, like a QString (PyQt API #1)"""
    return is_text_string(obj) or is_binary_string(obj)

def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if encoding is None:
        return str(obj)
    elif isinstance(obj, str):
        # In case this function is not used properly, this could happen
        return obj
    else:
        return str(obj, encoding)

# The default encoding for file paths and environment variables should be set
# to match the default encoding that the OS is using.
def getfilesystemencoding():
    """
    Query the filesystem for the encoding used to encode filenames
    and environment variables.
    """
    encoding = sys.getfilesystemencoding()
    if encoding is None:
        # Must be Linux or Unix and nl_langinfo(CODESET) failed.
        encoding = PREFERRED_ENCODING
    return encoding

PREFERRED_ENCODING = locale.getpreferredencoding()
FS_ENCODING = getfilesystemencoding()

def to_unicode_from_fs(string):
    """
    Return a unicode version of string decoded using the file system encoding.
    """
    if not is_string(string): # string is a QString
        string = to_text_string(string.toUtf8(), 'utf-8')
    else:
        if is_binary_string(string):
            try:
                unic = string.decode(FS_ENCODING)
            except (UnicodeError, TypeError):
                pass
            else:
                return unic
    return string

def get_home_dir():
    """Return user home directory."""
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent
        # file paths.
        path = to_unicode_from_fs(osp.expanduser('~'))
    except Exception:
        path = ''

    if osp.isdir(path):
        return path
    else:
        # Get home from alternative locations
        for env_var in ('HOME', 'USERPROFILE', 'TMP'):
            # os.environ.get() returns a raw byte string which needs to be
            # decoded with the codec that the OS is using to represent
            # environment variables.
            path = to_unicode_from_fs(os.environ.get(env_var, ''))
            if osp.isdir(path):
                return path
            else:
                path = ''

        if not path:
            raise RuntimeError('Please set the environment variable HOME to '
                               'your user/home directory path so Spyder can '
                               'start properly.')
            
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
    if (
        sys.platform == 'darwin'
        and basename.endswith('.app')
        and osp.exists(basename)
    ):
        return basename

    if os.name == 'posix':
        pyenv = [
            osp.join(home, '.pyenv', 'bin'),
            osp.join('/usr', 'local', 'bin'),
        ]

        a = [home, osp.join(home, 'opt'), '/opt']
        b = ['mambaforge', 'miniforge3', 'miniforge',
             'miniconda3', 'anaconda3', 'miniconda', 'anaconda']
    else:
        pyenv = [osp.join(home, '.pyenv', 'pyenv-win', 'bin')]

        a = [home, osp.join(home, 'AppData', 'Local'),
             'C:\\', osp.join('C:\\', 'ProgramData')]
        b = ['Mambaforge', 'Miniforge3', 'Miniforge',
             'Miniconda3', 'Anaconda3', 'Miniconda', 'Anaconda']

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
            names = [basename + ext for ext in extensions] + [basename]
    for name in names:
        path = is_program_installed(name)
        if path:
            return path
        
def find_conda():
    """Find conda executable."""
    conda = None

    # First try Spyder's conda executable
    if is_conda_based_app():
        root = osp.dirname(os.environ['CONDA_EXE'])
        conda = osp.join(root, 'mamba.exe' if WINDOWS else 'mamba')

    # Next try the environment variables
    if conda is None:
        conda = os.environ.get('CONDA_EXE') or os.environ.get('MAMBA_EXE')

    # Next try searching for the executable
    if conda is None:
        conda_exec = 'conda.bat' if WINDOWS else 'conda'
        conda = find_program(conda_exec)

    return conda