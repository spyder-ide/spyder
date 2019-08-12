# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Simple web browser widget"""

# Standard library imports
import re
import sre_constants
import sys

# Third party imports
from qtpy.QtCore import QUrl, Signal, Slot
from qtpy.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar, QMenu,
                            QWidget)
from qtpy.QtWebEngineWidgets import (QWebEnginePage, QWebEngineSettings,
                                     QWebEngineView, WEBENGINE)
from qtpy.QtGui import QFontInfo

# Local imports
from spyder.config.base import _, DEV
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils.qthelpers import (action2button, add_actions,
                                    create_action, create_toolbutton,
                                    create_plugin_layout)
from spyder.utils import icon_manager as ima
from spyder.widgets.comboboxes import UrlComboBox
from spyder.widgets.findreplace import FindReplace


class WebPage(QWebEnginePage):
    """
    Web page subclass to manage hyperlinks for WebEngine

    Note: This can't be used for WebKit because the
    acceptNavigationRequest method has a different
    functionality for it.
    """
    linkClicked = Signal(QUrl)

    def acceptNavigationRequest(self, url, navigation_type, isMainFrame):
        """
        Overloaded method to handle links ourselves
        """
        if navigation_type == QWebEnginePage.NavigationTypeLinkClicked:
            self.linkClicked.emit(url)
            return False
        return True


class WebView(QWebEngineView):
    """Web view"""
    def __init__(self, parent):
        QWebEngineView.__init__(self, parent)
        self.zoom_factor = 1.
        self.zoom_out_action = create_action(self, _("Zoom out"),
                                             icon=ima.icon('zoom_out'),
                                             triggered=self.zoom_out)
        self.zoom_in_action = create_action(self, _("Zoom in"),
                                            icon=ima.icon('zoom_in'),
                                            triggered=self.zoom_in)
        if WEBENGINE:
            web_page = WebPage(self)
            self.setPage(web_page)
            self.source_text = ''

    def find_text(self, text, changed=True, forward=True, case=False,
                  word=False, regexp=False):
        """Find text"""
        if not WEBENGINE:
            findflag = QWebEnginePage.FindWrapsAroundDocument
        else:
            findflag = 0

        if not forward:
            findflag = findflag | QWebEnginePage.FindBackward
        if case:
            findflag = findflag | QWebEnginePage.FindCaseSensitively

        return self.findText(text, QWebEnginePage.FindFlags(findflag))

    def get_selected_text(self):
        """Return text selected by current text cursor"""
        return self.selectedText()

    def set_source_text(self, source_text):
        """Set source text of the page. Callback for QWebEngineView."""
        self.source_text = source_text

    def get_number_matches(self, pattern, source_text='', case=False,
                           regexp=False, word=False):
        """Get the number of matches for the searched text."""
        pattern = to_text_string(pattern)
        if not pattern:
            return 0
        if not regexp:
            pattern = re.escape(pattern)
        if not source_text:
            if WEBENGINE:
                self.page().toPlainText(self.set_source_text)
                source_text = to_text_string(self.source_text)
            else:
                source_text = to_text_string(
                        self.page().mainFrame().toPlainText())

        if word:  # match whole words only
            pattern = r'\b{pattern}\b'.format(pattern=pattern)

        try:
            if case:
                regobj = re.compile(pattern, re.MULTILINE)
            else:
                regobj = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
        except sre_constants.error:
            return

        number_matches = 0
        for match in regobj.finditer(source_text):
            number_matches += 1

        return number_matches

    def set_font(self, font, fixed_font=None):
        font = QFontInfo(font)
        settings = self.page().settings()
        for fontfamily in (settings.StandardFont, settings.SerifFont,
                           settings.SansSerifFont, settings.CursiveFont,
                           settings.FantasyFont):
            settings.setFontFamily(fontfamily, font.family())
        if fixed_font is not None:
            settings.setFontFamily(settings.FixedFont, fixed_font.family())
        size = font.pixelSize()
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

    #------ QWebEngineView API -------------------------------------------------------
    def createWindow(self, webwindowtype):
        import webbrowser
        # See: spyder-ide/spyder#9849
        try:
            webbrowser.open(to_text_string(self.url().toString()))
        except ValueError:
            pass

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        actions = [self.pageAction(QWebEnginePage.Back),
                   self.pageAction(QWebEnginePage.Forward), None,
                   self.pageAction(QWebEnginePage.SelectAll),
                   self.pageAction(QWebEnginePage.Copy), None,
                   self.zoom_in_action, self.zoom_out_action]
        if DEV and not WEBENGINE:
            settings = self.page().settings()
            settings.setAttribute(QWebEngineSettings.DeveloperExtrasEnabled, True)
            actions += [None, self.pageAction(QWebEnginePage.InspectElement)]
        add_actions(menu, actions)
        menu.popup(event.globalPos())
        event.accept()

    def setHtml(self, html, baseUrl=QUrl()):
        """
        Reimplement Qt method to prevent WebEngine to steal focus
        when setting html on the page

        Solution taken from
        https://bugreports.qt.io/browse/QTBUG-52999
        """
        if WEBENGINE:
            self.setEnabled(False)
            super(WebView, self).setHtml(html, baseUrl)
            self.setEnabled(True)
        else:
            super(WebView, self).setHtml(html, baseUrl)


class WebBrowser(QWidget):
    """
    Web browser widget
    """
    def __init__(self, parent=None, options_button=None):
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
        refresh_button = pageact2btn(QWebEnginePage.Reload)
        stop_button = pageact2btn(QWebEnginePage.Stop)
        previous_button = pageact2btn(QWebEnginePage.Back)
        next_button = pageact2btn(QWebEnginePage.Forward)

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
        if not WEBENGINE:
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

        if options_button:
            hlayout.addWidget(options_button)

        layout = create_plugin_layout(hlayout)
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


class FrameWebView(QFrame):
    """
    Framed QWebEngineView for UI consistency in Spyder.
    """
    linkClicked = Signal(QUrl)

    def __init__(self, parent):
        QFrame.__init__(self, parent)

        self._webview = WebView(self)

        layout = QHBoxLayout()
        layout.addWidget(self._webview)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        if WEBENGINE:
            self._webview.page().linkClicked.connect(self.linkClicked)
        else:
            self._webview.linkClicked.connect(self.linkClicked)

    def __getattr__(self, name):
        return getattr(self._webview, name)

    @property
    def web_widget(self):
        return self._webview


def test():
    """Run web browser"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=8)
    widget = WebBrowser()
    widget.show()
    widget.set_home_url('https://www.google.com/')
    widget.go_home()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
