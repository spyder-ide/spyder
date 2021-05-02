# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

# Standard library imports
import os
import os.path as osp
import uuid
from textwrap import dedent

# Third party imports
from qtpy.QtCore import Signal, QThread
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import _, running_under_pytest
from spyder.config.manager import CONF
from spyder.py3compat import to_text_string
from spyder.utils import programs, encoding
from spyder.utils import syntaxhighlighters as sh
from spyder.plugins.ipythonconsole.utils.style import create_qss_style, create_style_class
from spyder.widgets.helperwidgets import MessageCheckBox
from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder.plugins.ipythonconsole.widgets import (
        ControlWidget, DebuggingWidget, FigureBrowserWidget,
        HelpWidget, NamepaceBrowserWidget, PageControlWidget)


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
    sig_pdb_state = Signal(bool, dict)
    sig_pdb_prompt_ready = Signal()

    # For ShellWidget
    focus_changed = Signal()
    new_client = Signal()
    sig_is_spykernel = Signal(object)
    sig_kernel_restarted_message = Signal(str)
    sig_kernel_restarted = Signal()
    sig_prompt_ready = Signal()
    sig_remote_execute = Signal()

    # For global working directory
    sig_change_cwd = Signal(str)

    # For printing internal errors
    sig_exception_occurred = Signal(dict)

    def __init__(self, ipyclient, additional_options, interpreter_versions,
                 external_kernel, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        self.custom_edit = True
        self.spyder_kernel_comm = KernelComm()
        self.spyder_kernel_comm.sig_exception_occurred.connect(
            self.sig_exception_occurred)
        super(ShellWidget, self).__init__(*args, **kw)

        self.ipyclient = ipyclient
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions
        self.external_kernel = external_kernel
        self._cwd = ''

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # Set the color of the matched parentheses here since the qtconsole
        # uses a hard-coded value that is not modified when the color scheme is
        # set in the qtconsole constructor. See spyder-ide/spyder#4806.
        self.set_bracket_matcher_color_scheme(self.syntax_style)

        self.shutdown_called = False
        self.kernel_manager = None
        self.kernel_client = None
        self.shutdown_thread = None
        handlers = {
            'pdb_state': self.set_pdb_state,
            'pdb_execute': self.pdb_execute,
            'get_pdb_settings': self.get_pdb_settings,
            'run_cell': self.handle_run_cell,
            'cell_count': self.handle_cell_count,
            'current_filename': self.handle_current_filename,
            'get_file_code': self.handle_get_file_code,
            'set_debug_state': self.set_debug_state,
            'update_syspath': self.update_syspath,
            'do_where': self.do_where,
            'pdb_input': self.pdb_input,
            'request_interrupt_eventloop': self.request_interrupt_eventloop,
        }
        for request_id in handlers:
            self.spyder_kernel_comm.register_call_handler(
                request_id, handlers[request_id])

        self._execute_queue = []
        self.executed.connect(self.pop_execute_queue)

        # Internal kernel are always spyder kernels
        self._is_spyder_kernel = not external_kernel

    def __del__(self):
        """Avoid destroying shutdown_thread."""
        if (self.shutdown_thread is not None
                and self.shutdown_thread.isRunning()):
            self.shutdown_thread.wait()

    # ---- Public API ---------------------------------------------------------
    def is_spyder_kernel(self):
        """Is the widget a spyder kernel."""
        return self._is_spyder_kernel

    def shutdown(self):
        """Shutdown kernel"""
        self.shutdown_called = True
        self.spyder_kernel_comm.close()
        self.kernel_manager.stop_restarter()

        self.shutdown_thread = QThread()
        self.shutdown_thread.run = self.kernel_manager.shutdown_kernel
        if self.kernel_client is not None:
            self.shutdown_thread.finished.connect(
                self.kernel_client.stop_channels)
        self.shutdown_thread.start()
        super(ShellWidget, self).shutdown()

    def will_close(self, externally_managed):
        """
        Close communication channels with the kernel if shutdown was not
        called. If the kernel is not externally managed, shutdown the kernel
        as well.
        """
        if not self.shutdown_called and not externally_managed:
            # Make sure the channels are stopped
            self.spyder_kernel_comm.close()
            self.kernel_manager.stop_restarter()
            self.kernel_manager.shutdown_kernel(now=True)
            if self.kernel_client is not None:
                self.kernel_client.stop_channels()
        if externally_managed:
            self.spyder_kernel_comm.close()
            if self.kernel_client is not None:
                self.kernel_client.stop_channels()
        super(ShellWidget, self).will_close(externally_managed)

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
        return self.spyder_kernel_comm.remote_call(
            interrupt=interrupt,
            blocking=blocking,
            callback=callback,
            timeout=timeout,
            display_error=display_error
        )

    def set_kernel_client_and_manager(self, kernel_client, kernel_manager):
        """Set the kernel client and manager"""
        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client
        self.spyder_kernel_comm.open_comm(kernel_client)

        # Redefine the complete method to work while debugging.
        self._redefine_complete_for_dbg(self.kernel_client)

    def pop_execute_queue(self):
        """Pop one waiting instruction."""
        if self._execute_queue:
            self.execute(*self._execute_queue.pop(0))

    # ---- Public API ---------------------------------------------------------
    def interrupt_kernel(self):
        """Attempts to interrupt the running kernel."""
        # Empty queue when interrupting
        # Fixes spyder-ide/spyder#7293.
        self._execute_queue = []
        super(ShellWidget, self).interrupt_kernel()

    def execute(self, source=None, hidden=False, interactive=False):
        """
        Executes source or the input buffer, possibly prompting for more
        input.
        """
        if self._executing:
            self._execute_queue.append((source, hidden, interactive))
            return
        super(ShellWidget, self).execute(source, hidden, interactive)

    def request_interrupt_eventloop(self):
        """Send a message to the kernel to interrupt the eventloop."""
        self.call_kernel()._interrupt_eventloop()

    def set_exit_callback(self):
        """Set exit callback for this shell."""
        self.exit_requested.connect(self.ipyclient.exit_callback)

    def is_running(self):
        if self.kernel_client is not None and \
          self.kernel_client.channels_running:
            return True
        else:
            return False

    def check_spyder_kernel(self):
        """Determine if the kernel is from Spyder."""
        code = u"getattr(get_ipython().kernel, 'set_value', False)"
        if self._reading:
            return
        else:
            self.silent_exec_method(code)

    def set_cwd(self, dirname):
        """Set shell current working directory."""
        if os.name == 'nt':
            # Use normpath instead of replacing '\' with '\\'
            # See spyder-ide/spyder#10785
            dirname = osp.normpath(dirname)

        if self.ipyclient.hostname is None:
            self.call_kernel(interrupt=self.is_debugging()).set_cwd(dirname)
            self._cwd = dirname

    def update_cwd(self):
        """Update current working directory in the kernel."""
        if self.kernel_client is None:
            return
        self.call_kernel(callback=self.remote_set_cwd).get_cwd()

    def remote_set_cwd(self, cwd):
        """Get current working directory from kernel."""
        self._cwd = cwd
        self.sig_change_cwd.emit(self._cwd)

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
            'Type "copyright", "credits" or "license" for more information.\n\n',
            'IPython %s -- An enhanced Interactive Python.\n' % ipy_ver
        ]
        banner = ''.join(banner_parts)

        # Pylab additions
        pylab_o = self.additional_options['pylab']
        autoload_pylab_o = self.additional_options['autoload_pylab']
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed and (pylab_o and autoload_pylab_o):
            pylab_message = ("\nPopulating the interactive namespace from "
                             "numpy and matplotlib\n")
            banner = banner + pylab_message

        # Sympy additions
        sympy_o = self.additional_options['sympy']
        if sympy_o:
            lines = """
These commands were executed:
>>> from __future__ import division
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

    def _reset_namespace(self):
        warning = CONF.get('ipython_console', 'show_reset_namespace_warning')
        self.reset_namespace(warning=warning)

    def reset_namespace(self, warning=False, message=False):
        """Reset the namespace by removing all names defined by the user."""
        reset_str = _("Remove all variables")
        warn_str = _("All user-defined variables will be removed. "
                     "Are you sure you want to proceed?")

        # Don't show the warning when running our tests.
        if running_under_pytest():
            warning = False

        # This is necessary to make resetting variables work in external
        # kernels.
        # See spyder-ide/spyder#9505.
        try:
            kernel_env = self.kernel_manager._kernel_spec.env
        except AttributeError:
            kernel_env = {}

        if warning:
            box = MessageCheckBox(icon=QMessageBox.Warning, parent=self)
            box.setWindowTitle(reset_str)
            box.set_checkbox_text(_("Don't show again."))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.Yes)

            box.set_checked(False)
            box.set_check_visible(True)
            box.setText(warn_str)

            answer = box.exec_()

            # Update checkbox based on user interaction
            CONF.set('ipython_console', 'show_reset_namespace_warning',
                     not box.is_checked())
            self.ipyclient.reset_warning = not box.is_checked()

            if answer != QMessageBox.Yes:
                return

        try:
            if self.is_waiting_pdb_input():
                self.execute('%reset -f')
            else:
                if message:
                    self.reset()
                    self._append_html(_("<br><br>Removing all variables..."
                                        "\n<hr>"),
                                      before_prompt=False)
                self.silent_execute("%reset -f")
                if kernel_env.get('SPY_AUTOLOAD_PYLAB_O') == 'True':
                    self.silent_execute("from pylab import *")
                if kernel_env.get('SPY_SYMPY_O') == 'True':
                    sympy_init = """
                        from __future__ import division
                        from sympy import *
                        x, y, z, t = symbols('x y z t')
                        k, m, n = symbols('k m n', integer=True)
                        f, g, h = symbols('f g h', cls=Function)
                        init_printing()"""
                    self.silent_execute(dedent(sympy_init))
                if kernel_env.get('SPY_RUN_CYTHON') == 'True':
                    self.silent_execute("%reload_ext Cython")

                # This doesn't need to interrupt the kernel because
                # "%reset -f" is being executed before it.
                # Fixes spyder-ide/spyder#12689
                self.refresh_namespacebrowser(interrupt=False)

                if not self.external_kernel:
                    self.call_kernel().close_all_mpl_figures()
        except AttributeError:
            pass

    def create_shortcuts(self):
        """Create shortcuts for ipyconsole."""
        inspect = CONF.config_shortcut(
            self._control.inspect_current_object,
            context='Console',
            name='Inspect current object',
            parent=self)

        clear_console = CONF.config_shortcut(
            self.clear_console,
            context='Console',
            name='Clear shell',
            parent=self)

        restart_kernel = CONF.config_shortcut(
            self.ipyclient.restart_kernel,
            context='ipython_console',
            name='Restart kernel',
            parent=self)

        new_tab = CONF.config_shortcut(
            lambda: self.new_client.emit(),
            context='ipython_console',
            name='new tab',
            parent=self)

        reset_namespace = CONF.config_shortcut(
            lambda: self._reset_namespace(),
            context='ipython_console',
            name='reset namespace',
            parent=self)

        array_inline = CONF.config_shortcut(
            self._control.enter_array_inline,
            context='array_builder',
            name='enter array inline',
            parent=self)

        array_table = CONF.config_shortcut(
            self._control.enter_array_table,
            context='array_builder',
            name='enter array table',
            parent=self)

        clear_line = CONF.config_shortcut(
            self.ipyclient.clear_line,
            context='console',
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

    def silent_exec_method(self, code):
        """Silently execute a kernel method and save its reply

        The methods passed here **don't** involve getting the value
        of a variable but instead replies that can be handled by
        ast.literal_eval.

        To get a value see `get_value`

        Parameters
        ----------
        code : string
            Code that contains the kernel method as part of its
            string

        See Also
        --------
        handle_exec_method : Method that deals with the reply

        Note
        ----
        This is based on the _silent_exec_callback method of
        RichJupyterWidget. Therefore this is licensed BSD
        """
        # Generate uuid, which would be used as an indication of whether or
        # not the unique request originated from here
        local_uuid = to_text_string(uuid.uuid1())
        code = to_text_string(code)
        if self.kernel_client is None:
            return

        msg_id = self.kernel_client.execute('', silent=True,
                                            user_expressions={ local_uuid:code })
        self._kernel_methods[local_uuid] = code
        self._request_info['execute'][msg_id] = self._ExecutionRequest(msg_id,
                                                          'silent_exec_method')

    def handle_exec_method(self, msg):
        """
        Handle data returned by silent executions of kernel methods

        This is based on the _handle_exec_callback of RichJupyterWidget.
        Therefore this is licensed BSD.
        """
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression in self._kernel_methods:
                # Process kernel reply
                method = self._kernel_methods[expression]
                reply = user_exp[expression]
                data = reply.get('data')
                if 'getattr' in method:
                    if data is not None and 'text/plain' in data:
                        is_spyder_kernel = data['text/plain']
                        if 'SpyderKernel' in is_spyder_kernel:
                            self._is_spyder_kernel = True
                            self.sig_is_spykernel.emit(self)

                # Remove method after being processed
                self._kernel_methods.pop(expression)

    def set_backend_for_mayavi(self, command):
        """
        Mayavi plots require the Qt backend, so we try to detect if one is
        generated to change backends
        """
        calling_mayavi = False
        lines = command.splitlines()
        for l in lines:
            if not l.startswith('#'):
                if 'import mayavi' in l or 'from mayavi' in l:
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
        if command.startswith('%matplotlib') and \
          len(command.splitlines()) == 1:
            if not 'inline' in command:
                self.silent_execute(command)

    # ---- Spyder-kernels methods ---------------------------------------------
    def get_editor(self, filename):
        """Get editor for filename and set it as the current editor."""
        editorstack = self.get_editorstack()
        if editorstack is None:
            return None

        if not filename:
            return None

        index = editorstack.has_filename(filename)
        if index is None:
            return None

        return editorstack.data[index].editor

    def get_editorstack(self):
        """Get the current editorstack."""
        plugin = self.ipyclient.plugin
        if plugin.main.editor is not None:
            editor = plugin.main.editor
            return editor.get_current_editorstack()
        raise RuntimeError('No editorstack found.')

    def handle_get_file_code(self, filename, save_all=True):
        """
        Return the bytes that compose the file.

        Bytes are returned instead of str to support non utf-8 files.
        """
        editorstack = self.get_editorstack()
        if save_all and CONF.get('editor', 'save_all_before_run', True):
            editorstack.save_all(save_new_files=False)
        editor = self.get_editor(filename)

        if editor is None:
            # Load it from file instead
            text, _enc = encoding.read(filename)
            return text

        return editor.toPlainText()

    def handle_run_cell(self, cell_name, filename):
        """
        Get cell code from cell name and file name.
        """
        editorstack = self.get_editorstack()
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        editorstack.last_cell_call = (filename, cell_name)

        # The file is open, load code from editor
        return editor.get_cell_code(cell_name)

    def handle_cell_count(self, filename):
        """Get number of cells in file to loop."""
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        # The file is open, get cell count from editor
        return editor.get_cell_count()

    def handle_current_filename(self):
        """Get the current filename."""
        return self.get_editorstack().get_current_finfo().filename

    # ---- Public methods (overrode by us) ------------------------------------
    def request_restart_kernel(self):
        """Reimplemented to call our own restart mechanism."""
        self.ipyclient.restart_kernel()

    # ---- Private methods (overrode by us) -----------------------------------
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
        if self.external_kernel:
            return ''
        show_banner_o = self.additional_options['show_banner']
        if show_banner_o:
            return self.long_banner()
        else:
            return self.short_banner()

    def _kernel_restarted_message(self, died=True):
        msg = _("Kernel died, restarting") if died else _("Kernel restarting")
        self.sig_kernel_restarted_message.emit(msg)

    def _handle_kernel_restarted(self, *args, **kwargs):
        super(ShellWidget, self)._handle_kernel_restarted(*args, **kwargs)
        self.sig_kernel_restarted.emit()

    def _syntax_style_changed(self):
        """Refresh the highlighting with the current syntax style by class."""
        if self._highlighter is None:
            # ignore premature calls
            return
        if self.syntax_style:
            self._highlighter._style = create_style_class(self.syntax_style)
            self._highlighter._clear_caches()
        else:
            self._highlighter.set_style_sheet(self.style_sheet)

    def _prompt_started_hook(self):
        """Emit a signal when the prompt is ready."""
        if not self._reading:
            self._highlighter.highlighting_on = True
            self.sig_prompt_ready.emit()

    def _handle_execute_input(self, msg):
        """Handle an execute_input message"""
        super(ShellWidget, self)._handle_execute_input(msg)
        self.sig_remote_execute.emit()

    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusOutEvent(event)
