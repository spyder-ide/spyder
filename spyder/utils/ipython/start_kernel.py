# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File used to start kernels for the IPython Console
"""

# Standard library imports
from distutils.version import LooseVersion
import os
import os.path as osp
import sys


PY2 = sys.version[0] == '2'


def is_module_installed(module_name):
    """
    Simpler version of spyder.utils.programs.is_module_installed
    to improve startup time.
    """
    try:
        __import__(module_name)
        return True
    except:
        # Module is not installed
        return False


def sympy_config(mpl_backend):
    """Sympy configuration"""
    if mpl_backend is not None:
        lines = """
from sympy.interactive import init_session
init_session()
%matplotlib {0}
""".format(mpl_backend)
    else:
        lines = """
from sympy.interactive import init_session
init_session()
"""

    return lines


def kernel_config():
    """Create a config object with IPython kernel options."""
    import ipykernel
    from IPython.core.application import get_ipython_dir
    from traitlets.config.loader import Config, load_pyconfig_files

    # ---- IPython config ----
    try:
        profile_path = osp.join(get_ipython_dir(), 'profile_default')
        cfg = load_pyconfig_files(['ipython_config.py',
                                   'ipython_kernel_config.py'],
                                  profile_path)
    except:
        cfg = Config()

    # ---- Spyder config ----
    spy_cfg = Config()

    # Until we implement Issue 1052
    spy_cfg.InteractiveShell.xmode = 'Plain'

    # Jedi completer
    jedi_o = os.environ.get('SPY_JEDI_O') == 'True'
    # - Using Jedi slow completions a lot for objects with big repr's.
    # - Jedi completions are not available in Python 2.
    if not PY2:
        spy_cfg.IPCompleter.use_jedi = jedi_o

    # Run lines of code at startup
    run_lines_o = os.environ.get('SPY_RUN_LINES_O')
    if run_lines_o is not None:
        spy_cfg.IPKernelApp.exec_lines = [x.strip() for x in run_lines_o.split(',')]
    else:
        spy_cfg.IPKernelApp.exec_lines = []

    # Clean terminal arguments input
    clear_argv = "import sys;sys.argv = [''];del sys"
    spy_cfg.IPKernelApp.exec_lines.append(clear_argv)

    # Load %autoreload magic
    spy_cfg.IPKernelApp.exec_lines.append(
        "get_ipython().kernel._load_autoreload_magic()")

    # Default inline backend configuration
    # This is useful to have when people doesn't
    # use our config system to configure the
    # inline backend but want to use
    # '%matplotlib inline' at runtime
    if LooseVersion(ipykernel.__version__) < LooseVersion('4.5'):
        dpi_option = 'savefig.dpi'
    else:
        dpi_option = 'figure.dpi'

    spy_cfg.InlineBackend.rc = {'figure.figsize': (6.0, 4.0),
                                dpi_option: 72,
                                'font.size': 10,
                                'figure.subplot.bottom': .125,
                                'figure.facecolor': 'white',
                                'figure.edgecolor': 'white'}

    # Pylab configuration
    mpl_backend = None
    pylab_o = os.environ.get('SPY_PYLAB_O')

    if pylab_o == 'True' and is_module_installed('matplotlib'):
        # Set Matplotlib backend
        backend_o = os.environ.get('SPY_BACKEND_O')
        if backend_o is not None:
            if backend_o == '1':
                if is_module_installed('PyQt5'):
                    auto_backend = 'qt5'
                elif is_module_installed('PyQt4'):
                    auto_backend = 'qt4'
                elif is_module_installed('_tkinter'):
                    auto_backend = 'tk'
                else:
                    auto_backend = 'inline'
            else:
                auto_backend = ''
            backends = {'0': 'inline',
                        '1': auto_backend,
                        '2': 'qt5',
                        '3': 'qt4',
                        '4': 'osx',
                        '5': 'gtk3',
                        '6': 'gtk',
                        '7': 'wx',
                        '8': 'tk'}
            mpl_backend = backends[backend_o]

            # Automatically load Pylab and Numpy, or only set Matplotlib
            # backend
            autoload_pylab_o = os.environ.get('SPY_AUTOLOAD_PYLAB_O') == 'True'
            command = "get_ipython().kernel._set_mpl_backend('{0}', {1})"
            spy_cfg.IPKernelApp.exec_lines.append(
                command.format(mpl_backend, autoload_pylab_o))

            # Inline backend configuration
            if mpl_backend == 'inline':
                # Figure format
                format_o = os.environ.get('SPY_FORMAT_O')
                formats = {'0': 'png',
                           '1': 'svg'}
                if format_o is not None:
                    spy_cfg.InlineBackend.figure_format = formats[format_o]

                # Resolution
                resolution_o = os.environ.get('SPY_RESOLUTION_O')
                if resolution_o is not None:
                    spy_cfg.InlineBackend.rc[dpi_option] = float(resolution_o)

                # Figure size
                width_o = float(os.environ.get('SPY_WIDTH_O'))
                height_o = float(os.environ.get('SPY_HEIGHT_O'))
                if width_o is not None and height_o is not None:
                    spy_cfg.InlineBackend.rc['figure.figsize'] = (width_o,
                                                                  height_o)

    # Enable Cython magic
    run_cython = os.environ.get('SPY_RUN_CYTHON') == 'True'
    if run_cython and is_module_installed('Cython'):
        spy_cfg.IPKernelApp.exec_lines.append('%reload_ext Cython')

    # Run a file at startup
    use_file_o = os.environ.get('SPY_USE_FILE_O')
    run_file_o = os.environ.get('SPY_RUN_FILE_O')
    if use_file_o == 'True' and run_file_o is not None:
        spy_cfg.IPKernelApp.file_to_run = run_file_o

    # Autocall
    autocall_o = os.environ.get('SPY_AUTOCALL_O')
    if autocall_o is not None:
        spy_cfg.ZMQInteractiveShell.autocall = int(autocall_o)

    # To handle the banner by ourselves in IPython 3+
    spy_cfg.ZMQInteractiveShell.banner1 = ''

    # Greedy completer
    greedy_o = os.environ.get('SPY_GREEDY_O') == 'True'
    spy_cfg.IPCompleter.greedy = greedy_o

    # Sympy loading
    sympy_o = os.environ.get('SPY_SYMPY_O') == 'True'
    if sympy_o and is_module_installed('sympy'):
        lines = sympy_config(mpl_backend)
        spy_cfg.IPKernelApp.exec_lines.append(lines)

    # Merge IPython and Spyder configs. Spyder prefs will have prevalence
    # over IPython ones
    cfg._merge(spy_cfg)
    return cfg


def varexp(line):
    """
    Spyder's variable explorer magic

    Used to generate plots, histograms and images of the variables displayed
    on it.
    """
    ip = get_ipython()       #analysis:ignore
    funcname, name = line.split()
    import spyder.pyplot
    __fig__ = spyder.pyplot.figure();
    __items__ = getattr(spyder.pyplot, funcname[2:])(ip.user_ns[name])
    spyder.pyplot.show()
    del __fig__, __items__


def main():
    # Remove this module's path from sys.path:
    try:
        sys.path.remove(osp.dirname(__file__))
    except ValueError:
        pass

    try:
        locals().pop('__file__')
    except KeyError:
        pass
    __doc__ = ''
    __name__ = '__main__'

    # Add current directory to sys.path (like for any standard Python interpreter
    # executed in interactive mode):
    sys.path.insert(0, '')

    # Fire up the kernel instance.
    from ipykernel.kernelapp import IPKernelApp

    if not os.environ.get('SPY_EXTERNAL_INTERPRETER') == "True":
        from spyder.utils.ipython.spyder_kernel import SpyderKernel
    else:
        # We add "spyder" to sys.path for external interpreters,
        # so this works!
        # See create_kernel_spec of plugins/ipythonconsole
        from utils.ipython.spyder_kernel import SpyderKernel

    kernel = IPKernelApp.instance()
    kernel.kernel_class = SpyderKernel
    try:
        kernel.config = kernel_config()
    except:
        pass
    kernel.initialize()

    # Set our own magics
    kernel.shell.register_magic_function(varexp)

    # Set Pdb class to be used by %debug and %pdb.
    # This makes IPython consoles to use the class defined in our
    # sitecustomize instead of their default one.
    import pdb
    kernel.shell.InteractiveTB.debugger_cls = pdb.Pdb

    # Start the (infinite) kernel event loop.
    kernel.start()


if __name__ == '__main__':
    main()
