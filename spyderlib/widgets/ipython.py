# -*- coding:utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.11+ frontend widget
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
from spyderlib.utils.qthelpers import add_actions, create_action


def _context_menu_hack(widget, exit_callback, pos):
    """Add a "Quit" entry to IPython Qt console widget"""
    menu = widget._original_context_menu_make(pos)
    quit_action = create_action(widget, _("&Quit"), icon='exit.png',
                                triggered=exit_callback)
    add_actions(menu, (None, quit_action))
    return menu

def set_ipython_exit_callback(widget, exit_callback):
    """Set IPython widget exit callback"""
    # Monkey-patching the original context menu
    #XXX: this is very ugly, let's find another way anytime soon...
    widget._original_context_menu_make = widget._context_menu_make
    widget._context_menu_make = lambda pos:\
                        _context_menu_hack(widget, exit_callback, pos)

    widget.exit_requested.connect(exit_callback)


def _focusinevent_hack(widget, event):
    """Reimplement Qt method to send focus infos to parent class"""
    widget.emit(SIGNAL('focus_changed()'))
    return widget._original_focusInEvent(event)

def _focusoutevent_hack(widget, event):
    """Reimplement Qt method to send focus infos to parent class"""
    widget.emit(SIGNAL('focus_changed()'))
    return widget._original_focusOutEvent(event)


class IPythonApp(IPythonQtConsoleApp):
    def initialize_all_except_qt(self, argv=None):
        BaseIPythonApplication.initialize(self, argv=argv)
        IPythonConsoleApp.initialize(self, argv=argv)

    def new_frontend_from_existing(self):
        """Create and return new frontend from connection file basename"""
        cf = find_connection_file(self.existing, profile='default')
        kernel_manager = QtKernelManager(connection_file=cf,
                                         config=self.config)
        kernel_manager.load_connection_file()
        kernel_manager.start_channels()
        widget = self.widget_factory(config=self.config, local_kernel=False)
        widget.kernel_manager = kernel_manager
        
        # Monkey-patching the original focus in/out event methods
        #XXX: this is very ugly, let's find another way anytime soon...
        widget._original_focusInEvent = widget.focusInEvent
        widget._original_focusOutEvent = widget.focusOutEvent
        widget.focusInEvent = lambda event: _focusinevent_hack(widget, event)
        widget.focusOutEvent = lambda event: _focusoutevent_hack(widget, event)

        return widget


if __name__ == '__main__':
    from spyderlib.qt.QtGui import QApplication
    
    iapp = IPythonApp()
    iapp.initialize()
    
    widget1 = iapp.new_frontend_from_existing()
    widget1.show()

    # Ugly pause but that's just for testing    
    import time
    time.sleep(2)
    
    widget2 = iapp.new_frontend_from_existing()
    widget2.show()
    
    # Start the application main loop.
    QApplication.instance().exec_()
