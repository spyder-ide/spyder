# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File used to start kernels for the IPython Console
"""

# Standard library imports
import os
import os.path as osp
import sys


# Check if we are running under an external interpreter
IS_EXT_INTERPRETER = os.environ.get('EXTERNAL_INTERPRETER', '').lower() == "true"


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
    from IPython.core.application import get_ipython_dir
    from traitlets.config.loader import Config, load_pyconfig_files
    if not IS_EXT_INTERPRETER:
        from spyder.config.main import CONF
        from spyder.utils.programs import is_module_installed
    else:
        # We add "spyder" to sys.path for external interpreters,
        # so this works!
        # See create_kernel_spec of plugins/ipythonconsole
        from config.main import CONF
        from utils.programs import is_module_installed

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

    # Run lines of code at startup
    run_lines_o = CONF.get('ipython_console', 'startup/run_lines')
    if run_lines_o:
        spy_cfg.IPKernelApp.exec_lines = [x.strip() for x in run_lines_o.split(',')]
    else:
        spy_cfg.IPKernelApp.exec_lines = []

    # Clean terminal arguments input
    clear_argv = "import sys;sys.argv = [''];del sys"
    spy_cfg.IPKernelApp.exec_lines.append(clear_argv)

    # Pylab configuration
    mpl_backend = None
    mpl_installed = is_module_installed('matplotlib')
    pylab_o = CONF.get('ipython_console', 'pylab')

    if mpl_installed and pylab_o:
        # Get matplotlib backend
        backend_o = CONF.get('ipython_console', 'pylab/backend')
        if backend_o == 1:
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
        backends = {0: 'inline', 1: auto_backend, 2: 'qt5', 3: 'qt4',
                    4: 'osx', 5: 'gtk3', 6: 'gtk', 7: 'wx', 8: 'tk'}
        mpl_backend = backends[backend_o]

        # Automatically load Pylab and Numpy, or only set Matplotlib
        # backend
        autoload_pylab_o = CONF.get('ipython_console', 'pylab/autoload')
        if autoload_pylab_o:
            spy_cfg.IPKernelApp.exec_lines.append(
                                              "%pylab {0}".format(mpl_backend))
        else:
            spy_cfg.IPKernelApp.exec_lines.append(
                                         "%matplotlib {0}".format(mpl_backend))

        # Inline backend configuration
        if mpl_backend == 'inline':
            # Figure format
            format_o = CONF.get('ipython_console',
                                'pylab/inline/figure_format', 0)
            formats = {0: 'png', 1: 'svg'}
            spy_cfg.InlineBackend.figure_format = formats[format_o]

            # Resolution
            if is_module_installed('ipykernel', '<4.5'):
                dpi_option = 'savefig.dpi'
            else:
                dpi_option = 'figure.dpi'

            spy_cfg.InlineBackend.rc = {'figure.figsize': (6.0, 4.0),
                                        dpi_option: 72,
                                        'font.size': 10,
                                        'figure.subplot.bottom': .125,
                                        'figure.facecolor': 'white',
                                        'figure.edgecolor': 'white'}
            resolution_o = CONF.get('ipython_console',
                                    'pylab/inline/resolution')
            spy_cfg.InlineBackend.rc[dpi_option] = resolution_o

            # Figure size
            width_o = float(CONF.get('ipython_console', 'pylab/inline/width'))
            height_o = float(CONF.get('ipython_console', 'pylab/inline/height'))
            spy_cfg.InlineBackend.rc['figure.figsize'] = (width_o, height_o)


    # Enable Cython magic
    if is_module_installed('Cython'):
        spy_cfg.IPKernelApp.exec_lines.append('%load_ext Cython')

    # Run a file at startup
    use_file_o = CONF.get('ipython_console', 'startup/use_run_file')
    run_file_o = CONF.get('ipython_console', 'startup/run_file')
    if use_file_o and run_file_o:
        spy_cfg.IPKernelApp.file_to_run = run_file_o

    # Autocall
    autocall_o = CONF.get('ipython_console', 'autocall')
    spy_cfg.ZMQInteractiveShell.autocall = autocall_o

    # To handle the banner by ourselves in IPython 3+
    spy_cfg.ZMQInteractiveShell.banner1 = ''

    # Greedy completer
    greedy_o = CONF.get('ipython_console', 'greedy_completer')
    spy_cfg.IPCompleter.greedy = greedy_o

    # Sympy loading
    sympy_o = CONF.get('ipython_console', 'symbolic_math')
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

    if not IS_EXT_INTERPRETER:
        from spyder.plugins.ipythonconsole.utils.spyder_kernel import SpyderKernel
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
