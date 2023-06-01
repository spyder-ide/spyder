# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

# Standard library imports
import ast
import os
import os.path as osp
import time
from textwrap import dedent

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMessageBox
from qtpy import QtCore, QtWidgets, QtGui
from traitlets import observe

# Local imports
from spyder.config.base import _, is_conda_based_app, running_under_pytest
from spyder.config.gui import get_color_scheme, is_dark_interface
from spyder.py3compat import to_text_string
from spyder.utils.palette import QStylePalette, SpyderPalette
from spyder.utils.clipboard_helper import CLIPBOARD_HELPER
from spyder.utils import syntaxhighlighters as sh
from spyder.plugins.ipythonconsole.utils.style import (
    create_qss_style, create_style_class)
from spyder.plugins.ipythonconsole.utils.kernel_handler import (
    KernelConnectionState)
from spyder.widgets.helperwidgets import MessageCheckBox
from spyder.plugins.ipythonconsole.widgets import (
    ControlWidget, DebuggingWidget, FigureBrowserWidget, HelpWidget,
    NamepaceBrowserWidget, PageControlWidget)


MODULES_FAQ_URL = (
    "https://docs.spyder-ide.org/5/faq.html#using-packages-installer")


class ShellWidget(NamepaceBrowserWidget, HelpWidget, DebuggingWidget,
                  FigureBrowserWidget):
    """
    Shell widget for the IPython Console

    This is the widget in charge of executing code
    """
    # NOTE: Signals can't be assigned separately to each widget
    #       That's why we define all needed signals here.

    # For NamepaceBrowserWidget
    sig_show_syspath = Signal(object)
    sig_show_env = Signal(object)

    # For FigureBrowserWidget
    sig_new_inline_figure = Signal(object, str)

    # For DebuggingWidget
    sig_pdb_step = Signal(str, int)
    """
    This signal is emitted when Pdb reaches a new line.

    Parameters
    ----------
    filename: str
        The filename the debugger stepped in.
    line_number: int
        The line number the debugger stepped in.
    """

    sig_pdb_stack = Signal(object, int)
    """
    This signal is emitted when the Pdb stack changed.

    Parameters
    ----------
    pdb_stack: traceback.StackSummary
        The current pdb stack.
    pdb_index: int
        The index in the stack.
    """

    sig_pdb_state_changed = Signal(bool)
    """
    This signal is emitted every time a Pdb interaction happens.

    Parameters
    ----------
    pdb_state: bool
        Whether the debugger is waiting for input.
    """

    sig_pdb_prompt_ready = Signal()
    """Called when pdb request new input"""

    # For ShellWidget
    sig_focus_changed = Signal()
    sig_new_client = Signal()
    sig_kernel_restarted_message = Signal(str)

    # Kernel died and restarted (not user requested)
    sig_prompt_ready = Signal()
    sig_remote_execute = Signal()

    # For global working directory
    sig_working_directory_changed = Signal(str)

    # For printing internal errors
    sig_exception_occurred = Signal(dict)

    # To save values and messages returned by the kernel
    _kernel_is_starting = True

    # Request plugins to send additional configuration to the Spyder kernel
    sig_config_spyder_kernel = Signal()

    # To notify of kernel connection / disconnection
    sig_shellwidget_created = Signal(object)
    sig_shellwidget_deleted = Signal(object)

    # To request restart
    sig_restart_kernel = Signal()

    sig_kernel_state_arrived = Signal(dict)
    """
    A new kernel state, which needs to be processed.

    Parameters
    ----------
    state: dict
        Kernel state. The structure of this dictionary is defined in the
        `SpyderKernel.get_state` method of Spyder-kernels.
    """

    def __init__(self, ipyclient, additional_options, interpreter_versions,
                 handlers, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        self.custom_edit = True

        super(ShellWidget, self).__init__(*args, **kw)
        self.ipyclient = ipyclient
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions
        self.kernel_handler = None
        self._cwd = ''

        # Keyboard shortcuts
        # Registered here to use shellwidget as the parent
        self.shortcuts = self.create_shortcuts()

        # Set the color of the matched parentheses here since the qtconsole
        # uses a hard-coded value that is not modified when the color scheme is
        # set in the qtconsole constructor. See spyder-ide/spyder#4806.
        self.set_bracket_matcher_color_scheme(self.syntax_style)

        self.shutting_down = False
        self.kernel_manager = None
        self.kernel_client = None
        self._init_kernel_setup = False
        handlers.update({
            'show_pdb_output': self.show_pdb_output,
            'set_debug_state': self.set_debug_state,
            'do_where': self.do_where,
            'pdb_input': self.pdb_input,
            'update_state': self.update_state,
        })
        self.kernel_comm_handlers = handlers

        self._execute_queue = []
        self.executed.connect(self.pop_execute_queue)

        # Show a message in our installers to explain users how to use
        # modules that don't come with them.
        self.show_modules_message = is_conda_based_app()

    # ---- Public API ---------------------------------------------------------
    @property
    def is_spyder_kernel(self):
        if self.kernel_handler is None:
            return False
        return self.kernel_handler.known_spyder_kernel

    @property
    def spyder_kernel_ready(self):
        """
        Check if Spyder kernel is ready.

        Notes
        -----
        This is used for our tests.
        """
        if self.kernel_handler is None:
            return False
        return (
            self.kernel_handler.connection_state ==
            KernelConnectionState.SpyderKernelReady)

    def connect_kernel(self, kernel_handler, first_connect=True):
        """Connect to the kernel using our handler."""
        # Kernel client
        kernel_client = kernel_handler.kernel_client
        kernel_client.stopped_channels.connect(self.notify_deleted)
        self.kernel_client = kernel_client

        self.kernel_manager = kernel_handler.kernel_manager
        self.kernel_handler = kernel_handler

        if first_connect:
            # Let plugins know that a new kernel is connected
            self.sig_shellwidget_created.emit(self)
        else:
            # Set _starting to False to avoid reset at first prompt
            self._starting = False

        # Connect signals
        kernel_handler.sig_kernel_is_ready.connect(
            self.handle_kernel_is_ready)
        kernel_handler.sig_kernel_connection_error.connect(
            self.handle_kernel_connection_error)

        kernel_handler.connect()

    def disconnect_kernel(self, shutdown_kernel=True, will_reconnect=True):
        """
        Disconnect from current kernel.

        Parameters:
        -----------
        shutdown_kernel: bool
            If True, the kernel is shut down.
        will_reconnect: bool
            If False, emits `sig_shellwidget_deleted` so the plugins can close
            related widgets.
        """
        kernel_handler = self.kernel_handler
        if not kernel_handler:
            return
        kernel_client = kernel_handler.kernel_client

        kernel_handler.sig_kernel_is_ready.disconnect(
            self.handle_kernel_is_ready)
        kernel_handler.sig_kernel_connection_error.disconnect(
            self.handle_kernel_connection_error)
        kernel_handler.kernel_client.stopped_channels.disconnect(
            self.notify_deleted)

        if self._init_kernel_setup:
            self._init_kernel_setup = False

            kernel_handler.kernel_comm.sig_exception_occurred.disconnect(
                self.sig_exception_occurred)
            kernel_client.control_channel.message_received.disconnect(
                self._dispatch)

        kernel_handler.close(shutdown_kernel)
        if not will_reconnect:
            self.notify_deleted()
        # Reset state
        self.reset_kernel_state()

        self.kernel_client = None
        self.kernel_manager = None
        self.kernel_handler = None

    def handle_kernel_is_ready(self):
        """The kernel is ready"""
        if (
            self.kernel_handler.connection_state ==
            KernelConnectionState.SpyderKernelReady
        ):
            self.setup_spyder_kernel()
            return

    def handle_kernel_connection_error(self):
        """An error occurred when connecting to the kernel."""
        if self.kernel_handler.connection_state == KernelConnectionState.Error:
            # A wrong version is connected
            self.append_html_message(
                self.kernel_handler.kernel_error_message, before_prompt=True)

    def notify_deleted(self):
        """Notify that the shellwidget was deleted."""
        self.sig_shellwidget_deleted.emit(self)

    def shutdown(self, shutdown_kernel=True):
        """Shutdown connection and kernel."""
        if self.shutting_down:
            return
        self.shutting_down = True
        if self.kernel_handler is not None:
            self.kernel_handler.close(shutdown_kernel)
        super().shutdown()

    def reset_kernel_state(self):
        """Reset the kernel state."""
        self._prompt_requested = False
        self._pdb_recursion_level = 0
        self._reading = False

    def print_restart_message(self):
        """Print restart message."""
        self._append_html(
            _("<br>Restarting kernel...<br>"), before_prompt=True)
        self.insert_horizontal_ruler()

    def call_kernel(self, interrupt=False, blocking=False, callback=None,
                    timeout=None, display_error=False):
        """
        Send message to Spyder kernel connected to this console.

        Parameters
        ----------
        interrupt: bool
            Interrupt the kernel while running or in Pdb to perform
            the call.
        blocking: bool
            Make a blocking call, i.e. wait on this side until the
            kernel sends its response.
        callback: callable
            Callable to process the response sent from the kernel
            on the Spyder side.
        timeout: int or None
            Maximum time (in seconds) before giving up when making a
            blocking call to the kernel. If None, a default timeout
            (defined in commbase.py, present in spyder-kernels) is
            used.
        display_error: bool
            If an error occurs, should it be printed to the console.
        """
        return self.kernel_handler.kernel_comm.remote_call(
            interrupt=interrupt,
            blocking=blocking,
            callback=callback,
            timeout=timeout,
            display_error=display_error
        )

    @property
    def is_external_kernel(self):
        """Check if this is an external kernel."""
        return self.kernel_manager is None

    def setup_spyder_kernel(self):
        """Setup spyder kernel"""
        if not self._init_kernel_setup:
            # Only do this setup once
            self._init_kernel_setup = True

            # For errors
            self.kernel_handler.kernel_comm.sig_exception_occurred.connect(
                self.sig_exception_occurred)

            # For completions
            self.kernel_client.control_channel.message_received.connect(
                self._dispatch)

            # Redefine the complete method to work while debugging.
            self._redefine_complete_for_dbg(self.kernel_client)

            for request_id, handler in self.kernel_comm_handlers.items():
                self.kernel_handler.kernel_comm.register_call_handler(
                    request_id, handler)

        # Setup to do after restart
        # Check for fault and send config
        self.kernel_handler.poll_fault_text()

        # Show possible errors when setting Matplotlib backend
        self.call_kernel().show_mpl_backend_errors()

        # Check if the dependecies for special consoles are available.
        self.call_kernel(
            callback=self.ipyclient._show_special_console_error
            ).is_special_kernel_valid()

        self.send_spyder_kernel_configuration()

    def send_spyder_kernel_configuration(self):
        """Send kernel configuration to spyder kernel."""
        # Set current cwd
        self.set_cwd()

        # To apply style
        self.set_color_scheme(self.syntax_style, reset=False)

        # Enable faulthandler
        self.kernel_handler.enable_faulthandler()

        # Give a chance to plugins to configure the kernel
        self.sig_config_spyder_kernel.emit()

    def pop_execute_queue(self):
        """Pop one waiting instruction."""
        if self._execute_queue:
            self.execute(*self._execute_queue.pop(0))

    def interrupt_kernel(self):
        """Attempts to interrupt the running kernel."""
        # Empty queue when interrupting
        # Fixes spyder-ide/spyder#7293.
        self._execute_queue = []

        if self.spyder_kernel_ready:
            self._reading = False

            # Check if there is a kernel that can be interrupted before trying
            # to do it.
            # Fixes spyder-ide/spyder#20212
            if self.kernel_manager and self.kernel_manager.has_kernel:
                self.call_kernel(interrupt=True).raise_interrupt_signal()
            else:
                self._append_html(
                    _("<br><br>The kernel appears to be dead, so it can't be "
                      "interrupted. Please open a new console to keep "
                      "working.<br>")
                )
        else:
            self._append_html(
                _("<br><br>It is not possible to interrupt a non-Spyder "
                  "kernel I did not start.<br>")
            )

    def execute(self, source=None, hidden=False, interactive=False):
        """
        Executes source or the input buffer, possibly prompting for more
        input.
        """
        # Needed for cases where there is no kernel initialized but
        # an execution is triggered like when setting initial configs.
        # See spyder-ide/spyder#16896
        if self.kernel_client is None:
            return
        if self._executing:
            self._execute_queue.append((source, hidden, interactive))
            return
        super(ShellWidget, self).execute(source, hidden, interactive)

    def is_running(self):
        """Check if shell is running."""
        return (
            self.kernel_client is not None and
            self.kernel_client.channels_running
        )

    def set_cwd(self, dirname=None, emit_cwd_change=False):
        """
        Set shell current working directory.

        Parameters
        ----------
        dirname: str
            Path to the new current working directory.
        emit_cwd_change: bool
            Whether to emit a Qt signal that informs other panes in Spyder that
            the current working directory has changed.
        """
        if self.ipyclient.hostname is not None:
            # Only sync for local kernels
            return

        if dirname is None:
            if not self._cwd:
                return
            dirname = self._cwd
        elif os.name == 'nt':
            # Use normpath instead of replacing '\' with '\\'
            # See spyder-ide/spyder#10785
            dirname = osp.normpath(dirname)

        if self.spyder_kernel_ready:
            # Otherwise cwd will be sent later
            self.call_kernel(
                interrupt=self.is_debugging()
            ).set_cwd(dirname)

        self._cwd = dirname
        if emit_cwd_change:
            self.sig_working_directory_changed.emit(self._cwd)

    def get_cwd(self):
        """
        Get current working directory.

        Notes
        -----
        * This doesn't ask the kernel for its working directory. Instead, it
          returns the last value of it saved here.
        * We do it for performance reasons because we call this method when
          switching consoles to update the Working Directory toolbar.
        """
        return self._cwd

    def update_state(self, state):
        """
        New state received from kernel.
        """
        cwd = state.pop("cwd", None)
        if cwd and self._cwd and cwd != self._cwd:
            # Only set it if self._cwd is already set
            self._cwd = cwd
            self.sig_working_directory_changed.emit(self._cwd)

        if state:
            self.sig_kernel_state_arrived.emit(state)

    def set_bracket_matcher_color_scheme(self, color_scheme):
        """Set color scheme for matched parentheses."""
        bsh = sh.BaseSH(parent=self, color_scheme=color_scheme)
        mpcolor = bsh.get_matched_p_color()
        self._bracket_matcher.format.setBackground(mpcolor)

    def set_color_scheme(self, color_scheme, reset=True):
        """Set color scheme of the shell."""
        self.set_bracket_matcher_color_scheme(color_scheme)
        self.style_sheet, dark_color = create_qss_style(color_scheme)
        self.syntax_style = color_scheme
        self._style_sheet_changed()
        self._syntax_style_changed()
        if reset:
            self.reset(clear=True)
        if not self.spyder_kernel_ready:
            # Will be sent later
            return
        if not dark_color:
            # Needed to change the colors of tracebacks
            self.silent_execute("%colors linux")
            self.call_kernel().set_sympy_forecolor(background_color='dark')
        else:
            self.silent_execute("%colors lightbg")
            self.call_kernel().set_sympy_forecolor(background_color='light')

    def update_syspath(self, path_dict, new_path_dict):
        """Update sys.path contents on kernel."""
        self.call_kernel(
            interrupt=True,
            blocking=False).update_syspath(path_dict, new_path_dict)

    def request_syspath(self):
        """Ask the kernel for sys.path contents."""
        self.call_kernel(
            interrupt=True, callback=self.sig_show_syspath.emit).get_syspath()

    def request_env(self):
        """Ask the kernel for environment variables."""
        self.call_kernel(
            interrupt=True, callback=self.sig_show_env.emit).get_env()

    def set_show_calltips(self, show_calltips):
        """Enable/Disable showing calltips."""
        self.enable_calltips = show_calltips

    def set_buffer_size(self, buffer_size):
        """Set buffer size for the shell."""
        self.buffer_size = buffer_size

    def set_completion_type(self, completion_type):
        """Set completion type (Graphical, Terminal, Plain) for the shell."""
        self.gui_completion = completion_type

    def set_in_prompt(self, in_prompt):
        """Set appereance of the In prompt."""
        self.in_prompt = in_prompt

    def set_out_prompt(self, out_prompt):
        """Set appereance of the Out prompt."""
        self.out_prompt = out_prompt

    def get_matplotlib_backend(self):
        """Call kernel to get current backend."""
        return self.call_kernel(
            interrupt=True,
            blocking=True).get_matplotlib_backend()

    def get_mpl_interactive_backend(self):
        """Call kernel to get current interactive backend."""
        return self.call_kernel(
            interrupt=True,
            blocking=True).get_mpl_interactive_backend()

    def set_matplotlib_backend(self, backend_option, pylab=False):
        """Set matplotlib backend given a backend name."""
        cmd = "get_ipython().kernel.set_matplotlib_backend('{}', {})"
        self.execute(cmd.format(backend_option, pylab), hidden=True)

    def set_mpl_inline_figure_format(self, figure_format):
        """Set matplotlib inline figure format."""
        cmd = "get_ipython().kernel.set_mpl_inline_figure_format('{}')"
        self.execute(cmd.format(figure_format), hidden=True)

    def set_mpl_inline_resolution(self, resolution):
        """Set matplotlib inline resolution (savefig.dpi/figure.dpi)."""
        cmd = "get_ipython().kernel.set_mpl_inline_resolution({})"
        self.execute(cmd.format(resolution), hidden=True)

    def set_mpl_inline_figure_size(self, width, height):
        """Set matplotlib inline resolution (savefig.dpi/figure.dpi)."""
        cmd = "get_ipython().kernel.set_mpl_inline_figure_size({}, {})"
        self.execute(cmd.format(width, height), hidden=True)

    def set_mpl_inline_bbox_inches(self, bbox_inches):
        """Set matplotlib inline print figure bbox_inches ('tight' or not)."""
        cmd = "get_ipython().kernel.set_mpl_inline_bbox_inches({})"
        self.execute(cmd.format(bbox_inches), hidden=True)

    def set_jedi_completer(self, use_jedi):
        """Set if jedi completions should be used."""
        cmd = "get_ipython().kernel.set_jedi_completer({})"
        self.execute(cmd.format(use_jedi), hidden=True)

    def set_greedy_completer(self, use_greedy):
        """Set if greedy completions should be used."""
        cmd = "get_ipython().kernel.set_greedy_completer({})"
        self.execute(cmd.format(use_greedy), hidden=True)

    def set_autocall(self, autocall):
        """Set if autocall functionality is enabled or not."""
        cmd = "get_ipython().kernel.set_autocall({})"
        self.execute(cmd.format(autocall), hidden=True)

    # --- To handle the banner
    def long_banner(self):
        """Banner for clients with additional content."""
        # Default banner
        py_ver = self.interpreter_versions['python_version'].split('\n')[0]
        ipy_ver = self.interpreter_versions['ipython_version']

        banner_parts = [
            'Python %s\n' % py_ver,
            'Type "copyright", "credits" or "license" for more information.',
            '\n\n',
            'IPython %s -- An enhanced Interactive Python.\n' % ipy_ver
        ]
        banner = ''.join(banner_parts)

        # Pylab additions
        pylab_o = self.additional_options['pylab']
        autoload_pylab_o = self.additional_options['autoload_pylab']
        if pylab_o and autoload_pylab_o:
            pylab_message = ("\nPopulating the interactive namespace from "
                             "numpy and matplotlib\n")
            banner = banner + pylab_message

        # Sympy additions
        sympy_o = self.additional_options['sympy']
        if sympy_o:
            lines = """
These commands were executed:
>>> from sympy import *
>>> x, y, z, t = symbols('x y z t')
>>> k, m, n = symbols('k m n', integer=True)
>>> f, g, h = symbols('f g h', cls=Function)
"""
            banner = banner + lines
        if (pylab_o and sympy_o):
            lines = """
Warning: pylab (numpy and matplotlib) and symbolic math (sympy) are both
enabled at the same time. Some pylab functions are going to be overrided by
the sympy module (e.g. plot)
"""
            banner = banner + lines

        return banner

    def short_banner(self):
        """Short banner with Python and IPython versions only."""
        py_ver = self.interpreter_versions['python_version'].split(' ')[0]
        ipy_ver = self.interpreter_versions['ipython_version']
        banner = 'Python %s -- IPython %s' % (py_ver, ipy_ver)
        return banner

    # --- To define additional shortcuts
    def clear_console(self):
        self.execute("%clear")
        # Stop reading as any input has been removed.
        self._reading = False

    @Slot()
    def _reset_namespace(self):
        warning = self.get_conf('show_reset_namespace_warning')
        self.reset_namespace(warning=warning)

    def reset_namespace(self, warning=False, message=False):
        """Reset the namespace by removing all names defined by the user."""
        # Don't show the warning when running our tests.
        if running_under_pytest():
            warning = False

        if warning:
            reset_str = _("Remove all variables")
            warn_str = _("All user-defined variables will be removed. "
                         "Are you sure you want to proceed?")
            box = MessageCheckBox(icon=QMessageBox.Warning, parent=self)
            box.setWindowTitle(reset_str)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.Yes)

            box.set_checkbox_text(_("Don't show again."))
            box.set_checked(False)
            box.set_check_visible(True)
            box.setText(warn_str)

            box.buttonClicked.connect(
                lambda button: self.handle_reset_message_answer(
                    box, button, message)
            )
            box.show()
        else:
            self._perform_reset(message)

    def handle_reset_message_answer(self, message_box, button, message):
        """
        Handle the answer of the reset namespace message box.

        Parameters
        ----------
        message_box
            Instance of the message box shown to the user.
        button: QPushButton
            Instance of the button clicked by the user on the dialog.
        message: bool
            Whether to show a message in the console telling users the
            namespace was reset.
        """
        if message_box.buttonRole(button) == QMessageBox.YesRole:
            self._update_reset_options(message_box)
            self._perform_reset(message)
        else:
            self._update_reset_options(message_box)

    def _perform_reset(self, message):
        """
        Perform the reset namespace operation.

        Parameters
        ----------
        message: bool
            Whether to show a message in the console telling users the
            namespace was reset.
        """
        # This is necessary to make resetting variables work in external
        # kernels.
        # See spyder-ide/spyder#9505.
        try:
            kernel_env = self.kernel_manager._kernel_spec.env
        except AttributeError:
            kernel_env = {}

        try:
            if self.is_waiting_pdb_input():
                self.execute('%reset -f')
            else:
                if message:
                    self.reset()
                    self._append_html(
                        _("<br><br>Removing all variables...<br>"),
                        before_prompt=False
                    )
                    self.insert_horizontal_ruler()
                self.silent_execute("%reset -f")
                if kernel_env.get('SPY_AUTOLOAD_PYLAB_O') == 'True':
                    self.silent_execute("from pylab import *")
                if kernel_env.get('SPY_SYMPY_O') == 'True':
                    sympy_init = """
                        from sympy import *
                        x, y, z, t = symbols('x y z t')
                        k, m, n = symbols('k m n', integer=True)
                        f, g, h = symbols('f g h', cls=Function)
                        init_printing()"""
                    self.silent_execute(dedent(sympy_init))
                if kernel_env.get('SPY_RUN_CYTHON') == 'True':
                    self.silent_execute("%reload_ext Cython")

                if self.spyder_kernel_ready:
                    self.call_kernel().close_all_mpl_figures()
                    self.send_spyder_kernel_configuration()
        except AttributeError:
            pass

    def _update_reset_options(self, message_box):
        """
        Update options and variables based on the interaction in the
        reset warning message box shown to the user.
        """
        self.set_conf(
            'show_reset_namespace_warning',
            not message_box.is_checked()
        )
        self.ipyclient.reset_warning = not message_box.is_checked()

    def create_shortcuts(self):
        """Create shortcuts for ipyconsole."""
        inspect = self.config_shortcut(
            self._control.inspect_current_object,
            context='ipython_console',
            name='Inspect current object',
            parent=self)

        clear_console = self.config_shortcut(
            self.clear_console,
            context='ipython_console',
            name='Clear shell',
            parent=self)

        restart_kernel = self.config_shortcut(
            self.sig_restart_kernel,
            context='ipython_console',
            name='Restart kernel',
            parent=self)

        new_tab = self.config_shortcut(
            self.sig_new_client,
            context='ipython_console',
            name='new tab',
            parent=self)

        reset_namespace = self.config_shortcut(
            self._reset_namespace,
            context='ipython_console',
            name='reset namespace',
            parent=self)

        array_inline = self.config_shortcut(
            self._control.enter_array_inline,
            context='ipython_console',
            name='enter array inline',
            parent=self)

        array_table = self.config_shortcut(
            self._control.enter_array_table,
            context='ipython_console',
            name='enter array table',
            parent=self)

        clear_line = self.config_shortcut(
            self.ipyclient.clear_line,
            context='ipython_console',
            name='clear line',
            parent=self)

        return [inspect, clear_console, restart_kernel, new_tab,
                reset_namespace, array_inline, array_table, clear_line]

    # --- To communicate with the kernel
    def silent_execute(self, code):
        """Execute code in the kernel without increasing the prompt"""
        try:
            if self.is_debugging():
                self.pdb_execute(code, hidden=True)
            else:
                self.kernel_client.execute(to_text_string(code), silent=True)
        except AttributeError:
            pass

    def set_backend_for_mayavi(self, command):
        """
        Mayavi plots require the Qt backend, so we try to detect if one is
        generated to change backends
        """
        calling_mayavi = False
        lines = command.splitlines()
        for line in lines:
            if not line.startswith('#'):
                if 'import mayavi' in line or 'from mayavi' in line:
                    calling_mayavi = True
                    break
        if calling_mayavi:
            message = _("Changing backend to Qt for Mayavi")
            self._append_plain_text(message + '\n')
            self.silent_execute("%gui inline\n%gui qt")

    def change_mpl_backend(self, command):
        """
        If the user is trying to change Matplotlib backends with
        %matplotlib, send the same command again to the kernel to
        correctly change it.

        Fixes spyder-ide/spyder#4002.
        """
        if (command.startswith('%matplotlib') and
                len(command.splitlines()) == 1):
            if 'inline' not in command:
                self.silent_execute(command)

    def append_html_message(self, html, before_prompt=False,
                            msg_type='warning'):
        """
        Append an html message enclosed in a box.

        Parameters
        ----------
        before_prompt: bool
            Whether to add the message before the next prompt.
        msg_type: str
            Type of message to be showm. Possible values are
            'warning' and 'error'.
        """
        # The message is displayed in a table with a header and a single cell.
        table_properties = (
            "border='0.5'" +
            "width='90%'" +
            "cellpadding='8'" +
            "cellspacing='0'"
        )

        if msg_type == 'error':
            header = _("Error")
            bgcolor = SpyderPalette.COLOR_ERROR_2
        else:
            header = _("Important")
            bgcolor = SpyderPalette.COLOR_WARN_1

        # This makes the header text have good contrast against its background
        # for the light theme.
        if is_dark_interface():
            font_color = QStylePalette.COLOR_TEXT_1
        else:
            font_color = 'white'

        self._append_html(
            f"<div align='center'>"
            f"<table {table_properties}>"
            # Header
            f"<tr><th bgcolor='{bgcolor}'><font color='{font_color}'>"
            f"{header}"
            f"</th></tr>"
            # Cell with html message
            f"<tr><td>{html}</td></tr>"
            f"</table>"
            f"</div>",
            before_prompt=before_prompt
        )

    def insert_horizontal_ruler(self):
        """
        Insert a horizontal ruler at the current cursor position.

        Notes
        -----
        This only works when adding a single horizontal line to a
        message. For more complex messages, please use
        append_html_message.
        """
        self._control.insert_horizontal_ruler()

    # ---- Public methods (overrode by us) ------------------------------------
    def _event_filter_console_keypress(self, event):
        """Filter events to send to qtconsole code."""
        key = event.key()
        if self._control_key_down(event.modifiers(), include_command=False):
            if key == QtCore.Qt.Key_Period:
                # Do not use ctrl + . to restart kernel
                # Handled by IPythonConsoleWidget
                return False
        return super()._event_filter_console_keypress(event)

    def adjust_indentation(self, line, indent_adjustment):
        """Adjust indentation."""
        if indent_adjustment == 0 or line == "":
            return line

        if indent_adjustment > 0:
            return ' ' * indent_adjustment + line

        max_indent = CLIPBOARD_HELPER.get_line_indentation(line)
        indent_adjustment = min(max_indent, -indent_adjustment)

        return line[indent_adjustment:]

    def paste(self, mode=QtGui.QClipboard.Clipboard):
        """ Paste the contents of the clipboard into the input region.

        Parameters
        ----------
        mode : QClipboard::Mode, optional [default QClipboard::Clipboard]

            Controls which part of the system clipboard is used. This can be
            used to access the selection clipboard in X11 and the Find buffer
            in Mac OS. By default, the regular clipboard is used.
        """
        if self._control.textInteractionFlags() & QtCore.Qt.TextEditable:
            # Make sure the paste is safe.
            self._keep_cursor_in_buffer()
            cursor = self._control.textCursor()

            # Remove any trailing newline, which confuses the GUI and forces
            # the user to backspace.
            text = QtWidgets.QApplication.clipboard().text(mode).rstrip()

            # Adjust indentation of multilines pastes
            if len(text.splitlines()) > 1:
                lines_adjustment = CLIPBOARD_HELPER.remaining_lines_adjustment(
                    self._get_preceding_text())
                eol_chars = "\n"
                first_line, *remaining_lines = (text + eol_chars).splitlines()
                remaining_lines = [
                    self.adjust_indentation(line, lines_adjustment)
                    for line in remaining_lines]
                text = eol_chars.join([first_line, *remaining_lines])

            # dedent removes "common leading whitespace" but to preserve
            # relative indent of multiline code, we have to compensate for any
            # leading space on the first line, if we're pasting into
            # an indented position.
            cursor_offset = cursor.position() - self._get_line_start_pos()
            if text.startswith(' ' * cursor_offset):
                text = text[cursor_offset:]

            self._insert_plain_text_into_buffer(cursor, dedent(text))

    def _get_preceding_text(self):
        """Get preciding text."""
        cursor = self._control.textCursor()
        text = cursor.selection().toPlainText()
        if text == "":
            return ""
        first_line_selection = text.splitlines()[0]
        cursor.setPosition(cursor.selectionStart())
        cursor.setPosition(cursor.block().position(),
                           QtGui.QTextCursor.KeepAnchor)
        preceding_text = cursor.selection().toPlainText()
        first_line = preceding_text + first_line_selection
        len_with_prompt = len(first_line)
        # Remove prompt
        first_line = self._highlighter.transform_classic_prompt(first_line)
        first_line = self._highlighter.transform_ipy_prompt(first_line)

        prompt_len = len_with_prompt - len(first_line)
        if prompt_len >= len(preceding_text):
            return ""

        return preceding_text[prompt_len:]

    def _save_clipboard_indentation(self):
        """
        Save the indentation corresponding to the clipboard data.

        Must be called right after copying.
        """
        CLIPBOARD_HELPER.save_indentation(self._get_preceding_text(), 4)

    def copy(self):
        """
        Copy the currently selected text to the clipboard.
        """
        super().copy()
        self._save_clipboard_indentation()

    def cut(self):
        """
        Copy the currently selected text to the clipboard and delete it
        if it's inside the input buffer.
        """
        super().cut()
        self._save_clipboard_indentation()

    # ---- Private API (overrode by us) ---------------------------------------
    def _handle_execute_reply(self, msg):
        """
        Reimplemented to handle communications between Spyder
        and the kernel
        """
        # Notify that kernel has started
        exec_count = msg['content'].get('execution_count', '')
        if exec_count == 0 and self._kernel_is_starting:
            self.ipyclient.t0 = time.monotonic()
            self._kernel_is_starting = False

        # This catches an error when doing the teardown of a test.
        try:
            super()._handle_execute_reply(msg)
        except RuntimeError:
            pass

    def _handle_status(self, msg):
        """
        Reimplemented to refresh the namespacebrowser after kernel
        restarts
        """
        state = msg['content'].get('execution_state', '')
        msg_type = msg['parent_header'].get('msg_type', '')
        if state == 'starting':
            # This is needed to show the time a kernel
            # has been alive in each console.
            self.ipyclient.t0 = time.monotonic()
            self.ipyclient.timer.timeout.connect(self.ipyclient.show_time)
            self.ipyclient.timer.start(1000)

            # This handles restarts when the kernel dies
            # unexpectedly
            if not self._kernel_is_starting:
                self._kernel_is_starting = True
        elif state == 'idle' and msg_type == 'shutdown_request':
            # This handles restarts asked by the user
            self.ipyclient.t0 = time.monotonic()
        else:
            super()._handle_status(msg)

    def _handle_error(self, msg):
        """
        Reimplemented to reset the prompt if the error comes after the reply
        """
        self._process_execute_error(msg)

    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(ShellWidget, self)._context_menu_make(pos)
        return self.ipyclient.add_actions_to_context_menu(menu)

    def _banner_default(self):
        """
        Reimplement banner creation to let the user decide if he wants a
        banner or not
        """
        # Don't change banner for external kernels
        if self.is_external_kernel:
            return ''
        show_banner_o = self.additional_options['show_banner']
        if show_banner_o:
            return self.long_banner()
        else:
            return self.short_banner()

    def _kernel_restarted_message(self, died=True):
        msg = _("Kernel died, restarting") if died else _("Kernel restarting")

        if died and self.kernel_manager is None:
            # The kernel might never restart, show position of fault file
            msg += (
                "\n" + _("Its crash file is located at:") + " "
                + self.kernel_handler.fault_filename()
            )

        self.sig_kernel_restarted_message.emit(msg)

    def _handle_kernel_restarted(self, *args, **kwargs):
        """The kernel restarted."""
        super()._handle_kernel_restarted(*args, **kwargs)

        # Print restart message
        self.print_restart_message()

        # Reset Pdb state
        self.reset_kernel_state()

        # reset comm
        self.kernel_handler.reopen_comm()

        # In case anyone waits on end of execution
        self.executed.emit({})

    @observe('syntax_style')
    def _syntax_style_changed(self, changed=None):
        """Refresh the highlighting with the current syntax style by class."""
        if self._highlighter is None:
            # ignore premature calls
            return
        if self.syntax_style:
            self._highlighter._style = create_style_class(self.syntax_style)
            self._highlighter._clear_caches()
        else:
            self._highlighter.set_style_sheet(self.style_sheet)

    def _get_color(self, color):
        """
        Get a color as qtconsole.styles._get_color() would return from
        a builtin Pygments style.
        """
        color_scheme = get_color_scheme(self.syntax_style)
        return dict(
            bgcolor=color_scheme['background'],
            select=color_scheme['background'],
            fgcolor=color_scheme['normal'][0])[color]

    def _prompt_started_hook(self):
        """Emit a signal when the prompt is ready."""
        if not self._reading:
            self._highlighter.highlighting_on = True
            self.sig_prompt_ready.emit()

    def _handle_execute_input(self, msg):
        """Handle an execute_input message"""
        super(ShellWidget, self)._handle_execute_input(msg)
        self.sig_remote_execute.emit()

    def _process_execute_error(self, msg):
        """
        Display a message when using our installers to explain users
        how to use modules that doesn't come with them.
        """
        super(ShellWidget, self)._process_execute_error(msg)
        if self.show_modules_message:
            error = msg['content']['traceback']
            if any(['ModuleNotFoundError' in frame or 'ImportError' in frame
                    for frame in error]):
                self.append_html_message(
                    _("It seems you're trying to use a module that doesn't "
                      "come with our installer. Check "
                      "<a href='{}'>this FAQ</a> in our docs to learn how "
                      "to do this.").format(MODULES_FAQ_URL),
                    before_prompt=True
                )
            self.show_modules_message = False

    # --- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.sig_focus_changed.emit()
        return super(ShellWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.sig_focus_changed.emit()
        return super(ShellWidget, self).focusOutEvent(event)
