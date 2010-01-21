# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""pydoc widget"""

from PyQt4.QtCore import QThread, QUrl

import sys, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.widgets.browser import WebBrowser


class PydocServer(QThread):
    """Pydoc server"""
    def __init__(self, port=7464):
        super(PydocServer, self).__init__()
        self.port = port
        
    def run(self):
        import pydoc
        pydoc.serve(self.port)


class PydocWidget(WebBrowser):
    """
    pydoc widget
    """
    PORT = 1234
    def __init__(self, parent):
        super(PydocWidget, self).__init__(parent)
        self.server = None
        self.start_server()
        self.set_home_url('http://localhost:%d/' % self.PORT)
        
    #------ Public API -----------------------------------------------------
    def start_server(self):
        """Start pydoc server"""
        if self.server is not None and self.server.isRunning():
            self.server.quit()
        self.server = PydocServer(port=self.PORT)
        self.server.start()

    #------ WebBrowser API -----------------------------------------------------
    def get_label(self):
        """Return address label text"""
        return self.tr("Module or package:")
    
    def reload(self):
        """Reload page"""
        self.start_server()
        super(PydocWidget, self).reload()
        
    def text_to_url(self, text):
        """Convert text address into QUrl object"""
        if text.startsWith('/'):
            text = text[1:]
        return QUrl(self.home_url.toString()+text+'.html')
    
    def url_to_text(self, url):
        """Convert QUrl object to displayed text in combo box"""
        return osp.splitext(unicode(url.path()))[0][1:]


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    widget = PydocWidget(None)
    widget.show()
    
    sys.exit(app.exec_())
