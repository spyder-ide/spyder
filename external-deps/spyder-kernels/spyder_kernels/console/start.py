# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
File used to start kernels for the IPython Console
"""

# Standard library imports
from distutils.version import LooseVersion
import os
import os.path as osp
import sys
import site


PY2 = sys.version[0] == '2'


def import_spydercustomize():
    """Import our customizations into the kernel."""
    here = osp.dirname(__file__)
    parent = osp.dirname(here)
    customize_dir = osp.join(parent, 'customize')

    # Remove current directory from sys.path to prevent kernel
    # crashes when people name Python files or modules with
    # the same name as standard library modules.
    # See spyder-ide/spyder#8007
    while '' in sys.path:
        sys.path.remove('')

    # Import our customizations
    site.addsitedir(customize_dir)
    import spydercustomize

    # Remove our customize path from sys.path
    try:
        sys.path.remove(customize_dir)
    except ValueError:
        pass


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

    # Enable/disable certain features for testing
    testing = os.environ.get('SPY_TESTING') == 'True'
    if testing:
        # Don't load nor save history in our IPython consoles.
        spy_cfg.HistoryAccessor.enabled = False

    # Until we implement Issue 1052
    spy_cfg.InteractiveShell.xmode = 'Plain'

    # Jedi completer. It's only available in Python 3
    jedi_o = os.environ.get('SPY_JEDI_O') == 'True'
    if not PY2:
        spy_cfg.IPCompleter.use_jedi = jedi_o

    # Run lines of code at startup
    run_lines_o = os.environ.get('SPY_RUN_LINES_O')
    if run_lines_o is not None:
        spy_cfg.IPKernelApp.exec_lines = [x.strip() for x in run_lines_o.split(';')]
    else:
        spy_cfg.IPKernelApp.exec_lines = []

    # Clean terminal arguments input
    clear_argv = "import sys;sys.argv = [''];del sys"
    spy_cfg.IPKernelApp.exec_lines.append(clear_argv)

    # Load %autoreload magic
    spy_cfg.IPKernelApp.exec_lines.append(
        "get_ipython().kernel._load_autoreload_magic()")

    # Load wurlitzer extension
    spy_cfg.IPKernelApp.exec_lines.append(
        "get_ipython().kernel._load_wurlitzer()")

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
    if is_module_installed('matplotlib'):
        # Set Matplotlib backend with Spyder options
        pylab_o = os.environ.get('SPY_PYLAB_O')
        backend_o = os.environ.get('SPY_BACKEND_O')
        if pylab_o == 'True' and backend_o is not None:
            # Select the automatic backend
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

            # Mapping of Spyder options to backends
            backends = {'0': 'inline',
                        '1': auto_backend,
                        '2': 'qt5',
                        '3': 'qt4',
                        '4': 'osx',
                        '5': 'gtk3',
                        '6': 'gtk',
                        '7': 'wx',
                        '8': 'tk'}

            # Select backend
            mpl_backend = backends[backend_o]

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

                # Print figure kwargs
                bbox_inches_o = os.environ.get('SPY_BBOX_INCHES_O')
                bbox_inches = 'tight' if bbox_inches_o == 'True' else None
                spy_cfg.InlineBackend.print_figure_kwargs.update(
                    {'bbox_inches': bbox_inches})
        else:
            # Set Matplotlib backend to inline for external kernels.
            # Fixes issue 108
            mpl_backend = 'inline'

        # Automatically load Pylab and Numpy, or only set Matplotlib
        # backend
        autoload_pylab_o = os.environ.get('SPY_AUTOLOAD_PYLAB_O') == 'True'
        command = "get_ipython().kernel._set_mpl_backend('{0}', {1})"
        spy_cfg.IPKernelApp.exec_lines.append(
            command.format(mpl_backend, autoload_pylab_o))

    # Enable Cython magic
    run_cython = os.environ.get('SPY_RUN_CYTHON') == 'True'
    if run_cython and is_module_installed('Cython'):
        spy_cfg.IPKernelApp.exec_lines.append('%reload_ext Cython')

    # Run a file at startup
    use_file_o = os.environ.get('SPY_USE_FILE_O')
    run_file_o = os.environ.get('SPY_RUN_FILE_O')
    if use_file_o == 'True' and run_file_o is not None:
        if osp.exists(run_file_o):
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
    try:
        import guiqwt.pyplot as pyplot
    except:
        import matplotlib.pyplot as pyplot
    __fig__ = pyplot.figure();
    __items__ = getattr(pyplot, funcname[2:])(
        ip.kernel._get_current_namespace()[name])
    pyplot.show()
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

    # Import our customizations into the kernel
    import_spydercustomize()

    # Remove current directory from sys.path to prevent kernel
    # crashes when people name Python files or modules with
    # the same name as standard library modules.
    # See spyder-ide/spyder#8007
    while '' in sys.path:
        sys.path.remove('')

    # Fire up the kernel instance.
    from ipykernel.kernelapp import IPKernelApp
    from spyder_kernels.console.kernel import SpyderKernel

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
