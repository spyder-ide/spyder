# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Simple web browser widget"""

from spyderlib.qt.QtGui import (QHBoxLayout, QWidget, QVBoxLayout,
                                QProgressBar, QLabel, QMenu)
from spyderlib.qt.QtWebKit import QWebView, QWebPage, QWebSettings
from spyderlib.qt.QtCore import QUrl, Slot
import spyderlib.qt.icon_manager as ima
import sys

# Local imports
from spyderlib.utils.qthelpers import (create_action, add_actions,
                                       create_toolbutton, action2button)
from spyderlib.baseconfig import DEV, _
from spyderlib.widgets.comboboxes import UrlComboBox
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.py3compat import to_text_string, is_text_string


class WebView(QWebView):
    """Web page"""
    def __init__(self, parent):
        QWebView.__init__(self, parent)
        self.zoom_factor = 1.
        self.zoom_out_action = create_action(self, _("Zoom out"),
                                             icon=ima.icon('zoom_out'),
                                             triggered=self.zoom_out)
        self.zoom_in_action = create_action(self, _("Zoom in"),
                                            icon=ima.icon('zoom_in'),
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
        
    def set_font(self, font, fixed_font=None):
        settings = self.page().settings()
        for fontfamily in (settings.StandardFont, settings.SerifFont,
                           settings.SansSerifFont, settings.CursiveFont,
                           settings.FantasyFont):
            settings.setFontFamily(fontfamily, font.family())
        if fixed_font is not None:
            settings.setFontFamily(settings.FixedFont, fixed_font.family())
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

    @Slot()
    def zoom_out(self):
        """Zoom out"""
        self.zoom_factor = max(.1, self.zoom_factor-.1)
        self.apply_zoom_factor()

    @Slot()
    def zoom_in(self):
        """Zoom in"""
        self.zoom_factor += .1
        self.apply_zoom_factor()
    
    #------ QWebView API -------------------------------------------------------
    def createWindow(self, webwindowtype):
        import webbrowser
        webbrowser.open(to_text_string(self.url().toString()))
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        actions = [self.pageAction(QWebPage.Back),
                   self.pageAction(QWebPage.Forward), None,
                   self.pageAction(QWebPage.SelectAll),
                   self.pageAction(QWebPage.Copy), None,
                   self.zoom_in_action, self.zoom_out_action]
        if DEV:
            settings = self.page().settings()
            settings.setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
            actions += [None, self.pageAction(QWebPage.InspectElement)]
        add_actions(menu, actions)
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
        self.webview.loadFinished.connect(self.load_finished)
        self.webview.titleChanged.connect(self.setWindowTitle)
        self.webview.urlChanged.connect(self.url_changed)
                
        home_button = create_toolbutton(self, icon=ima.icon('home'),
                                        tip=_("Home"),
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
        self.webview.loadStarted.connect(lambda: stop_button.setEnabled(True))
        self.webview.loadFinished.connect(lambda: stop_button.setEnabled(False))
        
        progressbar = QProgressBar(self)
        progressbar.setTextVisible(False)
        progressbar.hide()
        self.webview.loadStarted.connect(progressbar.show)
        self.webview.loadProgress.connect(progressbar.setValue)
        self.webview.loadFinished.connect(lambda _state: progressbar.hide())
        
        label = QLabel(self.get_label())
        
        self.url_combo = UrlComboBox(self)
        self.url_combo.valid.connect(self.url_combo_activated)
        self.webview.iconChanged.connect(self.icon_changed)
        
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()

        find_button = create_toolbutton(self, icon=ima.icon('find'),
                                        tip=_("Find text"),
                                        toggled=self.toggle_find_widget)
        self.find_widget.visibility_changed.connect(find_button.setChecked)

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
        return _("Address:")
            
    def set_home_url(self, text):
        """Set home URL"""
        self.home_url = QUrl(text)
        
    def set_url(self, url):
        """Set current URL"""
        self.url_changed(url)
        self.go_to(url)
        
    def go_to(self, url_or_text):
        """Go to page *address*"""
        if is_text_string(url_or_text):
            url = QUrl(url_or_text)
        else:
            url = url_or_text
        self.webview.load(url)

    @Slot()
    def go_home(self):
        """Go to home page"""
        if self.home_url is not None:
            self.set_url(self.home_url)
        
    def text_to_url(self, text):
        """Convert text address into QUrl object"""
        return QUrl(text)
        
    def url_combo_activated(self, valid):
        """Load URL from combo box first item"""
        text = to_text_string(self.url_combo.currentText())
        self.go_to(self.text_to_url(text))
        
    def load_finished(self, ok):
        if not ok:
            self.webview.setHtml(_("Unable to load page"))
            
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

    @Slot(bool)
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
