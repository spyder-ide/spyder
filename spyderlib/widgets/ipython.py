# -*- coding:utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.11+ frontend widget
"""

# IPython imports
from IPython.frontend.qt.kernelmanager import QtKernelManager
from IPython.frontend.qt.console.qtconsoleapp import IPythonQtConsoleApp
from IPython.lib.kernel import find_connection_file
from IPython.core.application import BaseIPythonApplication
from IPython.frontend.qt.console.qtconsoleapp import IPythonConsoleApp


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
        widget._existing = True
        widget._may_close = False
        widget._confirm_exit = False
        widget.kernel_manager = kernel_manager

#        widget.exit_requested.connect(self.close_tab)

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
