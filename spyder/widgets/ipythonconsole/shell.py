# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

import ast
import uuid

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

from spyder.config.base import _
from spyder.config.gui import config_shortcut, fixed_shortcut
from spyder.py3compat import to_text_string
from spyder.utils import programs
from spyder.widgets.arraybuilder import SHORTCUT_INLINE, SHORTCUT_TABLE
from spyder.widgets.ipythonconsole import (ControlWidget, DebuggingWidget,
                                           HelpWidget, NamepaceBrowserWidget,
                                           PageControlWidget)


class ShellWidget(NamepaceBrowserWidget, HelpWidget, DebuggingWidget):
    """
    Shell widget for the IPython Console

    This is the widget in charge of executing code
    """
    # NOTE: Signals can't be assigned separately to each widget
    #       That's why we define all needed signals here.

    # For NamepaceBrowserWidget
    sig_namespace_view = Signal(object)
    sig_var_properties = Signal(object)

    # For DebuggingWidget
    sig_input_reply = Signal()
    sig_pdb_step = Signal(str, int)
    sig_prompt_ready = Signal()

    # For ShellWidget
    focus_changed = Signal()
    new_client = Signal()
    sig_got_reply = Signal()

    def __init__(self, additional_options, interpreter_versions,
                 external_kernel, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        super(ShellWidget, self).__init__(*args, **kw)
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions

        self.set_background_color()

        # Additional variables
        self.ipyclient = None
        self.external_kernel = external_kernel

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # To save kernel replies in silent execution
        self._kernel_reply = None

    #---- Public API ----------------------------------------------------------
    def set_ipyclient(self, ipyclient):
        """Bind this shell widget to an IPython client one"""
        self.ipyclient = ipyclient
        self.exit_requested.connect(ipyclient.exit_callback)

    def is_running(self):
        if self.kernel_client is not None and \
          self.kernel_client.channels_running:
            return True
        else:
            return False

    # --- To handle the banner
    def long_banner(self):
        """Banner for IPython widgets with pylab message"""
        # Default banner
        from IPython.core.usage import quick_guide
        banner_parts = [
            'Python %s\n' % self.interpreter_versions['python_version'],
            'Type "copyright", "credits" or "license" for more information.\n\n',
            'IPython %s -- An enhanced Interactive Python.\n' % \
            self.interpreter_versions['ipython_version'],
            quick_guide
        ]
        banner = ''.join(banner_parts)

        # Pylab additions
        pylab_o = self.additional_options['pylab']
        autoload_pylab_o = self.additional_options['autoload_pylab']
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed and (pylab_o and autoload_pylab_o):
            pylab_message = ("\nPopulating the interactive namespace from "
                             "numpy and matplotlib")
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
        return banner

    def short_banner(self):
        """Short banner with Python and QtConsole versions"""
        banner = 'Python %s -- IPython %s' % (
                                  self.interpreter_versions['python_version'],
                                  self.interpreter_versions['ipython_version'])
        return banner

    # --- To define additional shortcuts
    def clear_console(self):
        self.execute("%clear")

    def reset_namespace(self):
        """Resets the namespace by removing all names defined by the user"""

        reply = QMessageBox.question(
            self,
            _("Reset IPython namespace"),
            _("All user-defined variables will be removed."
            "<br>Are you sure you want to reset the namespace?"),
            QMessageBox.Yes | QMessageBox.No,
            )

        if reply == QMessageBox.Yes:
            self.execute("%reset -f")

    def set_background_color(self):
        light_color_o = self.additional_options['light_color']
        if not light_color_o:
            self.set_default_style(colors='linux')

    def create_shortcuts(self):
        inspect = config_shortcut(self._control.inspect_current_object,
                                  context='Console', name='Inspect current object',
                                  parent=self)
        clear_console = config_shortcut(self.clear_console, context='Console',
                                        name='Clear shell', parent=self)

        # Fixed shortcuts
        fixed_shortcut("Ctrl+T", self, lambda: self.new_client.emit())
        fixed_shortcut("Ctrl+Alt+R", self, lambda: self.reset_namespace())
        fixed_shortcut(SHORTCUT_INLINE, self,
                       lambda: self._control.enter_array_inline())
        fixed_shortcut(SHORTCUT_TABLE, self,
                       lambda: self._control.enter_array_table())

        return [inspect, clear_console]

    # --- To communicate with the kernel
    def silent_execute(self, code):
        """Execute code in the kernel without increasing the prompt"""
        self.kernel_client.execute(to_text_string(code), silent=True)

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
                if 'get_namespace_view' in method:
                    view = ast.literal_eval(data['text/plain'])
                    self.sig_namespace_view.emit(view)
                elif 'get_var_properties' in method:
                    properties = ast.literal_eval(data['text/plain'])
                    self.sig_var_properties.emit(properties)
                else:
                    if data is not None:
                        self._kernel_reply = ast.literal_eval(data['text/plain'])
                    else:
                        self._kernel_reply = None
                    self.sig_got_reply.emit()

                # Remove method after being processed
                self._kernel_methods.pop(expression)

    #---- Private methods (overrode by us) ---------------------------------
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

    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusOutEvent(event)
