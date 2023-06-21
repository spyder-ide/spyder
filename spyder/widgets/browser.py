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
import qstylizer.style
from qtpy import PYQT5
from qtpy.QtCore import QEvent, Qt, QUrl, Signal, Slot
from qtpy.QtGui import QFontInfo
from qtpy.QtWebEngineWidgets import (WEBENGINE, QWebEnginePage,
                                     QWebEngineSettings, QWebEngineView)
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QWidget

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import DEV
from spyder.config.gui import OLD_PYQT
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (action2button, create_plugin_layout,
                                    create_toolbutton)
from spyder.widgets.comboboxes import UrlComboBox
from spyder.widgets.findreplace import FindReplace


# --- Constants
# ----------------------------------------------------------------------------
class WebViewActions:
    ZoomIn = 'zoom_in_action'
    ZoomOut = 'zoom_out_action'
    Back = 'back_action'
    Forward = 'forward_action'
    SelectAll = 'select_all_action'
    Copy = 'copy_action'
    Inspect = 'inspect_action'
    Stop = 'stop_action'
    Refresh = 'refresh_action'


class WebViewMenuSections:
    Move = 'move_section'
    Select = 'select_section'
    Zoom = 'zoom_section'
    Extras = 'extras_section'


class WebViewMenus:
    Context = 'context_menu'


# --- Widgets
# ----------------------------------------------------------------------------
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

        return super(WebPage, self).acceptNavigationRequest(
            url, navigation_type, isMainFrame)


class WebView(QWebEngineView, SpyderWidgetMixin):
    """
    Web view.
    """
    sig_focus_in_event = Signal()
    """
    This signal is emitted when the widget receives focus.
    """

    sig_focus_out_event = Signal()
    """
    This signal is emitted when the widget loses focus.
    """

    def __init__(self, parent, handle_links=True, class_parent=None):
        class_parent = parent if class_parent is None else class_parent
        if PYQT5:
            super().__init__(parent, class_parent=class_parent)
        else:
            QWebEngineView.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=class_parent)

        self.zoom_factor = 1.
        self.context_menu = None

        if WEBENGINE:
            if handle_links:
                web_page = WebPage(self)
            else:
                web_page = QWebEnginePage(self)

            self.setPage(web_page)
            self.source_text = ''

    def setup(self, options={}):
        # Actions
        original_back_action = self.pageAction(QWebEnginePage.Back)
        back_action = self.create_action(
            name=WebViewActions.Back,
            text=_("Back"),
            icon=self.create_icon('previous'),
            triggered=original_back_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_forward_action = self.pageAction(QWebEnginePage.Forward)
        forward_action = self.create_action(
            name=WebViewActions.Forward,
            text=_("Forward"),
            icon=self.create_icon('next'),
            triggered=original_forward_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_select_action = self.pageAction(QWebEnginePage.SelectAll)
        select_all_action = self.create_action(
            name=WebViewActions.SelectAll,
            text=_("Select all"),
            triggered=original_select_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_copy_action = self.pageAction(QWebEnginePage.Copy)
        copy_action = self.create_action(
            name=WebViewActions.Copy,
            text=_("Copy"),
            triggered=original_copy_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        self.zoom_in_action = self.create_action(
            name=WebViewActions.ZoomIn,
            text=_("Zoom in"),
            icon=self.create_icon('zoom_in'),
            triggered=self.zoom_in,
            context=Qt.WidgetWithChildrenShortcut,
        )

        self.zoom_out_action = self.create_action(
            name=WebViewActions.ZoomOut,
            text=_("Zoom out"),
            icon=self.create_icon('zoom_out'),
            triggered=self.zoom_out,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_inspect_action = self.pageAction(
            QWebEnginePage.InspectElement)
        inspect_action = self.create_action(
            name=WebViewActions.Inspect,
            text=_("Inspect"),
            triggered=original_inspect_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_refresh_action = self.pageAction(QWebEnginePage.Reload)
        self.create_action(
            name=WebViewActions.Refresh,
            text=_("Refresh"),
            icon=self.create_icon('refresh'),
            triggered=original_refresh_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        original_stop_action = self.pageAction(QWebEnginePage.Stop)
        self.create_action(
            name=WebViewActions.Stop,
            text=_("Stop"),
            icon=self.create_icon('stop'),
            triggered=original_stop_action.trigger,
            context=Qt.WidgetWithChildrenShortcut,
        )

        menu = self.create_menu(WebViewMenus.Context)
        self.context_menu = menu
        for item in [back_action, forward_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=WebViewMenuSections.Move,
            )

        for item in [select_all_action, copy_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=WebViewMenuSections.Select,
            )

        for item in [self.zoom_in_action, self.zoom_out_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=WebViewMenuSections.Zoom,
            )

        self.add_item_to_menu(
            inspect_action,
            menu=menu,
            section=WebViewMenuSections.Extras,
        )

        if DEV and not WEBENGINE:
            settings = self.page().settings()
            settings.setAttribute(QWebEngineSettings.DeveloperExtrasEnabled,
                                  True)
            inspect_action.setVisible(True)
        else:
            inspect_action.setVisible(False)

    def find_text(self, text, changed=True, forward=True, case=False,
                  word=False, regexp=False):
        """Find text."""
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
        """Apply zoom factor."""
        if hasattr(self, 'setZoomFactor'):
            # Assuming Qt >=v4.5
            self.setZoomFactor(self.zoom_factor)
        else:
            # Qt v4.4
            self.setTextSizeMultiplier(self.zoom_factor)

    def set_zoom_factor(self, zoom_factor):
        """Set zoom factor."""
        self.zoom_factor = zoom_factor
        self.apply_zoom_factor()

    def get_zoom_factor(self):
        """Return zoom factor."""
        return self.zoom_factor

    @Slot()
    def zoom_out(self):
        """Zoom out."""
        self.zoom_factor = max(.1, self.zoom_factor-.1)
        self.apply_zoom_factor()

    @Slot()
    def zoom_in(self):
        """Zoom in."""
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
        if self.context_menu:
            self.context_menu.popup(event.globalPos())
            event.accept()

    def setHtml(self, html, baseUrl=QUrl()):
        """
        Reimplement Qt method to prevent WebEngine to steal focus
        when setting html on the page

        Solution taken from
        https://bugreports.qt.io/browse/QTBUG-52999
        """
        if WEBENGINE:
            if OLD_PYQT:
                self.setEnabled(False)
            super(WebView, self).setHtml(html, baseUrl)
            if OLD_PYQT:
                self.setEnabled(True)
        else:
            super(WebView, self).setHtml(html, baseUrl)

        # This is required to catch an error with PyQt 5.9, for which
        # it seems this functionality is not working.
        # Fixes spyder-ide/spyder#16703
        try:
            # The event filter needs to be installed every time html is set
            # because the proxy changes with new content.
            self.focusProxy().installEventFilter(self)
        except AttributeError:
            pass

    def load(self, url):
        """
        Load url.

        This is reimplemented to install our event filter after the
        url is loaded.
        """
        super().load(url)

        # This is required to catch an error with some compilations of Qt/PyQt
        # packages, for which it seems this functionality is not working.
        # Fixes spyder-ide/spyder#19818
        try:
            self.focusProxy().installEventFilter(self)
        except AttributeError:
            pass

    def eventFilter(self, widget, event):
        """
        Handle events that affect the view.

        All events (e.g. focus in/out) reach the focus proxy, not this
        widget itself. That's why this event filter is necessary.
        """
        if self.focusProxy() is widget:
            if event.type() == QEvent.FocusIn:
                self.sig_focus_in_event.emit()
            elif event.type() == QEvent.FocusOut:
                self.sig_focus_out_event.emit()
        return super().eventFilter(widget, event)


class WebBrowser(QWidget):
    """
    Web browser widget.
    """
    def __init__(self, parent=None, options_button=None, handle_links=True):
        QWidget.__init__(self, parent)

        self.home_url = None

        self.webview = WebView(self, handle_links=handle_links)
        self.webview.setup()
        self.webview.loadFinished.connect(self.load_finished)
        self.webview.titleChanged.connect(self.setWindowTitle)
        self.webview.urlChanged.connect(self.url_changed)

        home_button = create_toolbutton(self, icon=ima.icon('home'),
                                        tip=_("Home"),
                                        triggered=self.go_home)

        zoom_out_button = action2button(self.webview.zoom_out_action)
        zoom_in_button = action2button(self.webview.zoom_in_action)

        def pageact2btn(prop, icon=None):
            return action2button(
                self.webview.pageAction(prop), parent=self.webview, icon=icon)

        refresh_button = pageact2btn(
            QWebEnginePage.Reload, icon=ima.icon('refresh'))
        stop_button = pageact2btn(
            QWebEnginePage.Stop, icon=ima.icon('stop'))
        previous_button = pageact2btn(
            QWebEnginePage.Back, icon=ima.icon('previous'))
        next_button = pageact2btn(
            QWebEnginePage.Forward, icon=ima.icon('next'))

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
    Framed WebView for UI consistency in Spyder.
    """
    linkClicked = Signal(QUrl)

    def __init__(self, parent, handle_links=True):
        super().__init__(parent)

        self._webview = WebView(
            self,
            handle_links=handle_links,
            class_parent=parent
        )
        self._webview.sig_focus_in_event.connect(
            lambda: self._apply_stylesheet(focus=True))
        self._webview.sig_focus_out_event.connect(
            lambda: self._apply_stylesheet(focus=False))

        layout = QHBoxLayout()
        layout.addWidget(self._webview)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._apply_stylesheet()

        if handle_links:
            if WEBENGINE:
                self._webview.page().linkClicked.connect(self.linkClicked)
            else:
                self._webview.linkClicked.connect(self.linkClicked)

    def __getattr__(self, name):
        if name == '_webview':
            return super().__getattr__(name)

        if hasattr(self._webview, name):
            return getattr(self._webview, name)
        else:
            return super().__getattr__(name)

    @property
    def web_widget(self):
        return self._webview

    def _apply_stylesheet(self, focus=False):
        """Apply stylesheet according to the current focus."""
        if focus:
            border_color = QStylePalette.COLOR_ACCENT_3
        else:
            border_color = QStylePalette.COLOR_BACKGROUND_4

        css = qstylizer.style.StyleSheet()
        css.QFrame.setValues(
            border=f'1px solid {border_color}',
            margin='0px 1px 0px 1px',
            padding='0px 0px 1px 0px',
            borderRadius='3px'
        )

        self.setStyleSheet(css.toString())


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
