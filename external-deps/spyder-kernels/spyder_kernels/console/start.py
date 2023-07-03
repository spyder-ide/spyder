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
import os
import os.path as osp
import sys
import site

# Third-party imports
from traitlets import DottedObjectName

# Local imports
from spyder_kernels.utils.misc import is_module_installed


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
    import spydercustomize  # noqa

    # Remove our customize path from sys.path
    try:
        sys.path.remove(customize_dir)
    except ValueError:
        pass

def kernel_config():
    """Create a config object with IPython kernel options."""
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

    # Jedi completer.
    jedi_o = os.environ.get('SPY_JEDI_O') == 'True'
    spy_cfg.IPCompleter.use_jedi = jedi_o

    # Clear terminal arguments input.
    # This needs to be done before adding the exec_lines that come from
    # Spyder, to avoid deleting the sys module if users want to import
    # it through them.
    # See spyder-ide/spyder#15788
    clear_argv = "import sys; sys.argv = ['']; del sys"
    spy_cfg.IPKernelApp.exec_lines = [clear_argv]

    # Prevent other libraries to change the breakpoint builtin.
    # This started to be a problem since IPykernel 6.3.0.
    if sys.version_info[0:2] >= (3, 7):
        spy_cfg.IPKernelApp.exec_lines.append(
            "import sys; import pdb; "
            "sys.breakpointhook = pdb.set_trace; "
            "del sys; del pdb"
        )

    # Run lines of code at startup
    run_lines_o = os.environ.get('SPY_RUN_LINES_O')
    if run_lines_o is not None:
        spy_cfg.IPKernelApp.exec_lines += (
            [x.strip() for x in run_lines_o.split(';')]
        )

    # Load %autoreload magic
    spy_cfg.IPKernelApp.exec_lines.append(
        "get_ipython().kernel._load_autoreload_magic()")

    # Load wurlitzer extension
    spy_cfg.IPKernelApp.exec_lines.append(
        "get_ipython().kernel._load_wurlitzer()")

    # Default inline backend configuration.
    # This is useful to have when people doesn't
    # use our config system to configure the
    # inline backend but want to use
    # '%matplotlib inline' at runtime
    spy_cfg.InlineBackend.rc = {
        # The typical default figure size is too large for inline use,
        # so we shrink the figure size to 6x4, and tweak fonts to
        # make that fit.
        'figure.figsize': (6.0, 4.0),
        # 72 dpi matches SVG/qtconsole.
        # This only affects PNG export, as SVG has no dpi setting.
        'figure.dpi': 72,
        # 12pt labels get cutoff on 6x4 logplots, so use 10pt.
        'font.size': 10,
        # 10pt still needs a little more room on the xlabel
        'figure.subplot.bottom': .125,
        # Play nicely with any background color.
        'figure.facecolor': 'white',
        'figure.edgecolor': 'white'
    }

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

    # To handle the banner by ourselves
    spy_cfg.ZMQInteractiveShell.banner1 = ''

    # Greedy completer
    greedy_o = os.environ.get('SPY_GREEDY_O') == 'True'
    spy_cfg.IPCompleter.greedy = greedy_o

    # Disable the new mechanism to capture and forward low-level output
    # in IPykernel 6. For that we have Wurlitzer.
    spy_cfg.IPKernelApp.capture_fd_output = False

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
    pyplot.figure();
    getattr(pyplot, funcname[2:])(ip._get_current_namespace()[name])
    pyplot.show()


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

    # Main imports
    from ipykernel.kernelapp import IPKernelApp
    from spyder_kernels.console.kernel import SpyderKernel

    class SpyderKernelApp(IPKernelApp):

        outstream_class = DottedObjectName(
            'spyder_kernels.console.outstream.TTYOutStream')

        def init_pdb(self):
            """
            This method was added in IPykernel 5.3.1 and it replaces
            the debugger used by the kernel with a new class
            introduced in IPython 7.15 during kernel's initialization.
            Therefore, it doesn't allow us to use our debugger.
            """
            pass

        def close(self):
            """Close the loopback socket."""
            socket = self.kernel.loopback_socket
            if socket and not socket.closed:
                socket.close()
            return super().close()

    # Fire up the kernel instance.
    kernel = SpyderKernelApp.instance()
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
