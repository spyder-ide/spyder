# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.12+ client widget
"""

from spyderlib.qt.QtCore import SIGNAL

# IPython imports
from IPython.frontend.qt.kernelmanager import QtKernelManager
from IPython.frontend.qt.console.qtconsoleapp import IPythonQtConsoleApp
from IPython.lib.kernel import find_connection_file
from IPython.core.application import BaseIPythonApplication
from IPython.frontend.qt.console.qtconsoleapp import IPythonConsoleApp

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils.misc import monkeypatch_method
from spyderlib.utils.qthelpers import add_actions, create_action

# Monkey patching
from IPython.frontend.qt.console import ipython_widget

# Methods to be implemented in IPython client object (ipython_client):
#   ipython_client.add_actions_to_context_menu(menu)

@monkeypatch_method(ipython_widget.IPythonWidget, 'IPW')
def _context_menu_make(self, pos):
    menu = self._old_IPW__context_menu_make(pos)
    return self.ipython_client.add_actions_to_context_menu(menu)

@monkeypatch_method(ipython_widget.IPythonWidget, 'IPW')
def focusInEvent(self, event):
    self.emit(SIGNAL('focus_changed()'))
    return self._old_IPW_focusInEvent(event)

@monkeypatch_method(ipython_widget.IPythonWidget, 'IPW')
def focusOutEvent(self, event):
    self.emit(SIGNAL('focus_changed()'))
    return self._old_IPW_focusOutEvent(event)


def set_ipython_exit_callback(widget, exit_callback):
    """Set IPython widget exit callback"""
    widget.exit_requested.connect(exit_callback)


class IPythonApp(IPythonQtConsoleApp):
    def initialize_all_except_qt(self, argv=None):
        BaseIPythonApplication.initialize(self, argv=argv)
        IPythonConsoleApp.initialize(self, argv=argv)

    def new_client_from_existing(self):
        """Create and return new client (frontend)
        from connection file basename"""
        cf = find_connection_file(self.existing, profile='default')
        kernel_manager = QtKernelManager(connection_file=cf,
                                         config=self.config)
        kernel_manager.load_connection_file()
        kernel_manager.start_channels()
        widget = self.widget_factory(config=self.config, local_kernel=False)
        widget.kernel_manager = kernel_manager
        return widget


if __name__ == '__main__':
    from spyderlib.qt.QtGui import QApplication
    
    iapp = IPythonApp()
    iapp.initialize()
    
    widget1 = iapp.new_client_from_existing()
    widget1.show()

    # Ugly pause but that's just for testing    
    import time
    time.sleep(2)
    
    widget2 = iapp.new_client_from_existing()
    widget2.show()
    
    # Start the application main loop.
    QApplication.instance().exec_()
