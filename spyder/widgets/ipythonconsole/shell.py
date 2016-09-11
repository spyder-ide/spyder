# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

import sys

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

from spyder.config.base import _
from spyder.config.gui import config_shortcut, fixed_shortcut
from spyder.py3compat import to_text_string
from spyder.utils import programs
from spyder.widgets.arraybuilder import SHORTCUT_INLINE, SHORTCUT_TABLE
from spyder.widgets.ipythonconsole import (ControlWidget, HelpWidget,
                                           NamepaceBrowserWidget,
                                           PageControlWidget)


class ShellWidget(NamepaceBrowserWidget, HelpWidget):
    """
    Shell widget for the IPython Console

    This is the widget in charge of executing code
    """
    focus_changed = Signal()
    new_client = Signal()

    def __init__(self, additional_options, interpreter_versions, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        super(ShellWidget, self).__init__(*args, **kw)
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions

        self.set_background_color()

        # --- Spyder variables ---
        self.ipyclient = None

        # --- Keyboard shortcuts ---
        self.shortcuts = self.create_shortcuts()

    #---- Public API ----------------------------------------------------------
    def set_ipyclient(self, ipyclient):
        """Bind this shell widget to an IPython client one"""
        self.ipyclient = ipyclient
        self.exit_requested.connect(ipyclient.exit_callback)

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

    def write_to_stdin(self, line):
        """Send raw characters to the IPython kernel through stdin"""
        self.kernel_client.input(line)

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
        fixed_shortcut("Ctrl+R", self, lambda: self.reset_namespace())
        fixed_shortcut(SHORTCUT_INLINE, self,
                       lambda: self._control.enter_array_inline())
        fixed_shortcut(SHORTCUT_TABLE, self,
                       lambda: self._control.enter_array_table())

        return [inspect, clear_console]

    def silent_execute(self, code):
        """Execute code in the kernel without increasing the prompt"""
        self.kernel_client.execute(to_text_string(code), silent=True)

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
