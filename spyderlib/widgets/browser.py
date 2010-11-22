# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Simple web browser widget"""

from PyQt4.QtGui import (QHBoxLayout, QWidget, QVBoxLayout, QProgressBar,
                         QLabel, QMenu)
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtCore import SIGNAL, QUrl

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import (translate, create_action, add_actions,
                                       create_toolbutton, action2button)
from spyderlib.config import get_icon
from spyderlib.widgets.comboboxes import UrlComboBox
from spyderlib.widgets.findreplace import FindReplace


class WebView(QWebView):
    """Web page"""
    def __init__(self, parent):
        QWebView.__init__(self, parent)
        self.zoom_factor = 1.
        self.zoom_out_action = create_action(self, self.tr("Zoom out"),
                                             icon=get_icon('zoom_out.png'),
                                             triggered=self.zoom_out)
        self.zoom_in_action = create_action(self, self.tr("Zoom in"),
                                            icon=get_icon('zoom_in.png'),
                                            triggered=self.zoom_in)
        
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False,
                  regexp=False):
        """Find text"""
        findflag = QWebPage.FindWrapsAroundDocument
        if not forward:
            findflag = findflag | QWebPage.FindBackward
        if case:
            findflag = findflag | QWebPage.FindCaseSensitively
        return self.findText(text, findflag)
    
    def get_selected_text(self):
        """Return text selected by current text cursor"""
        return self.selectedText()
        
    def set_font(self, font): 
        family = font.family() 
        settings = self.page().settings() 
        settings.setFontFamily(settings.StandardFont, family) 
        settings.setFontFamily(settings.SerifFont, family) 
        settings.setFontFamily(settings.SansSerifFont, family) 
        settings.setFontFamily(settings.CursiveFont, family) 
        size = font.pointSize() 
        settings.setFontSize(settings.DefaultFontSize, size) 
        settings.setFontSize(settings.DefaultFixedFontSize, size) 
            
    def apply_zoom_factor(self):
        """Apply zoom factor"""
        if hasattr(self, 'setZoomFactor'):
            # Assuming Qt >=v4.5
            self.setZoomFactor(self.zoom_factor)
        else:
            # Qt v4.4
            self.setTextSizeMultiplier(self.zoom_factor)
        
    def set_zoom_factor(self, zoom_factor):
        """Set zoom factor"""
        self.zoom_factor = zoom_factor
        self.apply_zoom_factor()
    
    def get_zoom_factor(self):
        """Return zoom factor"""
        return self.zoom_factor
            
    def zoom_out(self):
        """Zoom out"""
        self.zoom_factor = max(.1, self.zoom_factor-.1)
        self.apply_zoom_factor()
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom_factor += .1
        self.apply_zoom_factor()
    
    #------ QWebView API -------------------------------------------------------
    def createWindow(self, webwindowtype):
        import webbrowser
        webbrowser.open(unicode(self.url().toString()))
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        add_actions( menu, (self.pageAction(QWebPage.Back),
                            self.pageAction(QWebPage.Forward), None,
                            self.pageAction(QWebPage.SelectAll),
                            self.pageAction(QWebPage.Copy), None,
                            self.pageAction(QWebPage.Reload), None,
                            self.zoom_in_action, self.zoom_out_action) )
        menu.popup(event.globalPos())
        event.accept()
                

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
        self.connect(self.webview, SIGNAL("titleChanged(QString)"),
                     self.setWindowTitle)
        self.connect(self.webview, SIGNAL("urlChanged(QUrl)"), self.url_changed)
                
        home_button = create_toolbutton(self, get_icon('home.png'),
                                        tip=self.tr("Home"),
                                        triggered=self.go_home)
        
        zoom_out_button = action2button(self.webview.zoom_out_action)
        zoom_in_button = action2button(self.webview.zoom_in_action)
        
        pageact2btn = lambda prop: action2button(self.webview.pageAction(prop),
                                                 parent=self.webview)
        refresh_button = pageact2btn(QWebPage.Reload)
        stop_button = pageact2btn(QWebPage.Stop)
        previous_button = pageact2btn(QWebPage.Back)
        next_button = pageact2btn(QWebPage.Forward)
        
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
        
        label = QLabel(self.get_label())
        
        self.url_combo = UrlComboBox(self)
        self.connect(self.url_combo, SIGNAL('valid(bool)'),
                     self.url_combo_activated)
        self.connect(self.webview, SIGNAL("iconChanged()"), self.icon_changed)
        
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()

        find_button = create_toolbutton(self, icon='find.png',
                                    tip=translate("FindReplace", "Find text"),
                                    toggled=self.toggle_find_widget)
        self.connect(self.find_widget, SIGNAL("visibility_changed(bool)"),
                     find_button.setChecked)

        hlayout = QHBoxLayout()
        for widget in (previous_button, next_button, home_button, find_button,
                       label, self.url_combo, zoom_out_button, zoom_in_button,
                       refresh_button, progressbar, stop_button):
            hlayout.addWidget(widget)
        
        layout = QVBoxLayout()
        layout.addLayout(hlayout)
        layout.addWidget(self.webview)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
                
    def get_label(self):
        """Return address label text"""
        return self.tr("Address:")
            
    def set_home_url(self, text):
        """Set home URL"""
        self.home_url = QUrl(text)
        
    def set_url(self, url):
        """Set current URL"""
        self.url_changed(url)
        self.go_to(url)
        
    def go_to(self, url_or_text):
        """Go to page *address*"""
        if isinstance(url_or_text, basestring):
            url = QUrl(url_or_text)
        else:
            url = url_or_text
        self.webview.load(url)
        
    def go_home(self):
        """Go to home page"""
        if self.home_url is not None:
            self.set_url(self.home_url)
        
    def text_to_url(self, text):
        """Convert text address into QUrl object"""
        return QUrl(text)
        
    def url_combo_activated(self, valid):
        """Load URL from combo box first item"""
        self.go_to(self.text_to_url(self.url_combo.currentText()))
        
    def load_finished(self, ok):
        if not ok:
            self.webview.setHtml(self.tr("Unable to load page"))
            
    def url_to_text(self, url):
        """Convert QUrl object to displayed text in combo box"""
        return url.toString()
            
    def url_changed(self, url):
        """Displayed URL has changed -> updating URL combo box"""
        self.url_combo.add_text(self.url_to_text(url))
            
    def icon_changed(self):
        self.url_combo.setItemIcon(self.url_combo.currentIndex(),
                                   self.webview.icon())
        self.setWindowIcon(self.webview.icon())
        
    def toggle_find_widget(self, state):
        if state:
            self.find_widget.show()
        else:
            self.find_widget.hide()


def main():
    """Run web browser"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = WebBrowser()
    widget.show()
    widget.set_home_url('http://localhost:7464/')
    widget.go_home()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
