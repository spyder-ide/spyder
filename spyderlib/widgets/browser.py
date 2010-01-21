# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Simple web browser widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QHBoxLayout, QWidget, QVBoxLayout, QProgressBar
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtCore import SIGNAL, QUrl

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import create_toolbutton, translate
from spyderlib.config import get_icon
from spyderlib.widgets.comboboxes import UrlComboBox
from spyderlib.widgets.findreplace import FindReplace


class WebView(QWebView):
    """Web page"""
    def __init__(self, parent):
        super(WebView, self).__init__(parent)
        
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        findflag = QWebPage.FindWrapsAroundDocument
        if not forward:
            findflag = findflag | QWebPage.FindBackward
        if case:
            findflag = findflag | QWebPage.FindCaseSensitively
        return self.findText(text, findflag)
        

class WebBrowser(QWidget):
    """
    Web browser widget
    """
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        
        self.home_url = None
        
        self.webview = WebView(self)
        self.connect(self.webview, SIGNAL("loadFinished(bool)"),
                     self.load_finished)
        self.connect(self.webview, SIGNAL("linkClicked(QUrl)"),
                     self.link_clicked)
        
        previous_button = create_toolbutton(self, get_icon('previous.png'),
                                            tip=self.tr("Previous"),
                                            triggered=self.webview.back)
        next_button = create_toolbutton(self, get_icon('next.png'),
                                        tip=self.tr("Next"),
                                        triggered=self.webview.forward)
        home_button = create_toolbutton(self, get_icon('home.png'),
                                        tip=self.tr("Home"),
                                        triggered=self.go_home)
        refresh_button = create_toolbutton(self, get_icon('reload.png'),
                                           tip=self.tr("Reload"),
                                           triggered=self.reload)
        stop_button = create_toolbutton(self, get_icon('stop.png'),
                                        tip=self.tr("Stop"),
                                        triggered=self.webview.stop)
        stop_button.setEnabled(False)
        self.connect(self.webview, SIGNAL("loadStarted()"),
                     lambda: stop_button.setEnabled(True))
        self.connect(self.webview, SIGNAL("loadFinished(bool)"),
                     lambda: stop_button.setEnabled(False))
        
        progressbar = QProgressBar(self)
        progressbar.setTextVisible(False)
        progressbar.hide()
        self.connect(self.webview, SIGNAL("loadStarted()"), progressbar.show)
        self.connect(self.webview, SIGNAL("loadProgress(int)"),
                     progressbar.setValue)
        self.connect(self.webview, SIGNAL("loadFinished(bool)"),
                     progressbar.hide)
        
        self.url_combo = UrlComboBox(self)
        self.connect(self.url_combo, SIGNAL('valid(bool)'), self.refresh)
        self.connect(self.webview, SIGNAL("iconChanged()"), self.icon_changed)
        
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()

        find_button = create_toolbutton(self,
                                    tip=translate("FindReplace", "Find text"),
                                    shortcut="Ctrl+F", icon='find.png',
                                    toggled=self.toggle_find_widget)
        self.connect(self.find_widget, SIGNAL("visibility_changed(bool)"),
                     find_button.setChecked)

        hlayout = QHBoxLayout()
        for widget in (previous_button, next_button, home_button, find_button,
                       self.url_combo, refresh_button, stop_button):
            hlayout.addWidget(widget)
        
        layout = QVBoxLayout()
        layout.addLayout(hlayout)
        layout.addWidget(self.webview)
        layout.addWidget(progressbar)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.connect(self.webview, SIGNAL("titleChanged(QString)"),
                     self.setWindowTitle)
        
    def set_home_url(self, home_url):
        """Set home URL"""
        self.home_url = home_url
        self.go_home()
        
    def set_url(self, address):
        """Set current URL"""
        self.url_combo.add_text(address)
        self.go_to(address)
        
    def go_to(self, address):
        """Go to page *address*"""
        self.webview.setUrl(QUrl(address))
        
    def go_home(self):
        """Go to home page"""
        if self.home_url is not None:
            self.set_url(self.home_url)
            
    def reload(self):
        """Reload page"""
        self.webview.reload()
        
    def refresh(self, valid):
        """Refresh widget"""
        self.go_to(self.url_combo.currentText())
        
    def load_finished(self, ok):
        if not ok:
            self.webview.setHtml(self.tr("Unable to load page"))
            
    def link_clicked(self, url):
        self.url_combo.addItem(url.path())
            
    def icon_changed(self):
        self.url_combo.setItemIcon(self.url_combo.currentIndex(),
                                   self.webview.icon())
        self.setWindowIcon(self.webview.icon())
        
    def toggle_find_widget(self, state):
        if state:
            self.find_widget.show()
        else:
            self.find_widget.hide()


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    widget = WebBrowser()
    widget.show()
    widget.set_home_url('http://localhost:7464/')
    
    sys.exit(app.exec_())
