# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.12+ client widget
"""

# IPython imports
from IPython.frontend.qt.kernelmanager import QtKernelManager
from IPython.frontend.qt.console.qtconsoleapp import IPythonQtConsoleApp
from IPython.lib.kernel import find_connection_file
from IPython.core.application import BaseIPythonApplication
from IPython.frontend.qt.console.qtconsoleapp import IPythonConsoleApp
from IPython.frontend.qt.console.rich_ipython_widget import RichIPythonWidget

from spyderlib.qt.QtCore import SIGNAL, Qt

# Local imports
from spyderlib.widgets.sourcecode.base import TextEditBaseWidget


class SpyderIPythonWidget(RichIPythonWidget):
    """Spyder's IPython widget"""
    def __init__(self, *args, **kw):
        self.control_factory = TextEditBaseWidget
        super(RichIPythonWidget, self).__init__(*args, **kw)
        self.ipython_client = None
    
    #---- Public API ----------------------------------------------------------
    def set_ipython_client(self, ipython_client):
        """Bind this IPython widget to an IPython client widget
        (see spyderlib/plugins/ipythonconsole.py)"""
        self.ipython_client = ipython_client
        self.exit_requested.connect(ipython_client.exit_callback)

    #---- IPython private methods ---------------------------------------------
    def _create_control(self):
        """Reimplement the IPython text widget creation"""
        control = self.control_factory()
        
        #======================================================================
        # The following is a copy of the '_create_control' method taken from:
        # IPython.frontend.qt.console.console_widget.ConsoleWidget
        #
        # For future versions, we shall ask to IPython developers to add a 
        # factory attribute (e.g. "self.control_factory") that we would 
        # override to avoid this copy.
        #======================================================================
        # Install event filters. The filter on the viewport is needed for
        # mouse events and drag events.
        control.installEventFilter(self)
        control.viewport().installEventFilter(self)

        # Connect signals.
        control.cursorPositionChanged.connect(self._cursor_position_changed)
        control.customContextMenuRequested.connect(
            self._custom_context_menu_requested)
        control.copyAvailable.connect(self.copy_available)
        control.redoAvailable.connect(self.redo_available)
        control.undoAvailable.connect(self.undo_available)

        # Hijack the document size change signal to prevent Qt from adjusting
        # the viewport's scrollbar. We are relying on an implementation detail
        # of Q(Plain)TextEdit here, which is potentially dangerous, but without
        # this functionality we cannot create a nice terminal interface.
        layout = control.document().documentLayout()
        layout.documentSizeChanged.disconnect()
        layout.documentSizeChanged.connect(self._adjust_scrollbars)

        # Configure the control.
        control.setAttribute(Qt.WA_InputMethodEnabled, True)
        control.setContextMenuPolicy(Qt.CustomContextMenu)
        control.setReadOnly(True)
        control.setUndoRedoEnabled(False)
        control.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        return control
        #======================================================================

    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(SpyderIPythonWidget, self)._context_menu_make(pos)
        return self.ipython_client.add_actions_to_context_menu(menu)
    
    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(SpyderIPythonWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(SpyderIPythonWidget, self).focusOutEvent(event)


class IPythonApp(IPythonQtConsoleApp):
    def initialize_all_except_qt(self, argv=None):
        BaseIPythonApplication.initialize(self, argv=argv)
        IPythonConsoleApp.initialize(self, argv=argv)

    #TODO: We have to ask an IPython developer to read this, I'm sure that 
    # we don't use the IPython API as it should be... at least I hope so!

    def create_kernel_manager(self):
        """Create a kernel manager"""
        cf = find_connection_file(self.existing, profile='default')
        kernel_manager = QtKernelManager(connection_file=cf,
                                         config=self.config)
        kernel_manager.load_connection_file()
        kernel_manager.start_channels()
        return kernel_manager

    def create_new_client(self, connection_file=None):
        """Create and return new client (frontend)
        from connection file basename"""
        if connection_file is not None:
            self.parse_command_line(argv=['--existing']+[connection_file])
        kernel_manager = self.create_kernel_manager()
        widget = SpyderIPythonWidget(config=self.config, local_kernel=False)
        widget.kernel_manager = kernel_manager
        return widget


if __name__ == '__main__':
    from spyderlib.qt.QtGui import QApplication
    
    iapp = IPythonApp()
    iapp.initialize()
    
    widget1 = iapp.create_new_client()
    widget1.show()

    # Ugly pause but that's just for testing    
    import time
    time.sleep(2)
    
    widget2 = iapp.create_new_client()
    widget2.show()
    
    # Start the application main loop.
    QApplication.instance().exec_()
