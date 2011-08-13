# -*- coding:utf-8 -*-
"""
IPython v0.11+ frontend widget
"""

#import os
#os.environ['QT_API'] = 'pyqt'
#from IPython.external import qt

# IPython imports
from IPython.utils.localinterfaces import LOCAL_IPS
from IPython.frontend.qt.console.qtconsoleapp import IPythonQtConsoleApp


class IPythonApp(IPythonQtConsoleApp):
    def init_qt_elements(self):
        # Create the widget.
        local_kernel = (not self.existing) or self.ip in LOCAL_IPS
        self.widget = self.widget_factory(config=self.config,
                                          local_kernel=local_kernel)
        self.widget.kernel_manager = self.kernel_manager


def create_widget(argv=None):
    app = IPythonApp()
    app.initialize(argv)
    return app.widget
    
    
def test():
    from spyderlib.qt.QtGui import QApplication
    app = QApplication([])
    widget = create_widget()
    widget.show()
    # Start the application main loop.
    app.exec_()

if __name__ == '__main__':
    test()
