# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
PyDoc widget.
"""

# Standard library imports
import os.path as osp
import pydoc
import sys

# Third party imports
from qtpy.QtCore import Qt, QThread, QUrl, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.onlinehelp.pydoc_patch import _start_server, _url_handler
from spyder.widgets.browser import WebView, WebViewActions
from spyder.widgets.comboboxes import UrlComboBox
from spyder.widgets.findreplace import FindReplace


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
PORT = 30128


class PydocBrowserActions:
    # Triggers
    Home = 'home_action'
    Find = 'find_action'


class PydocBrowserMainToolbarSections:
    Main = 'main_section'


# =============================================================================
# Pydoc adjustments
# =============================================================================
# This is needed to prevent pydoc raise an ErrorDuringImport when
# trying to import numpy.
# See spyder-ide/spyder#10740
DIRECT_PYDOC_IMPORT_MODULES = ['numpy', 'numpy.core']
try:
    from pydoc import safeimport

    def spyder_safeimport(path, forceload=0, cache={}):
        if path in DIRECT_PYDOC_IMPORT_MODULES:
            forceload = 0
        return safeimport(path, forceload=forceload, cache=cache)

    pydoc.safeimport = spyder_safeimport
except Exception:
    pass


class PydocServer(QThread):
    """
    Pydoc server.
    """
    sig_server_started = Signal()

    def __init__(self, port):
        QThread.__init__(self)

        self.port = port
        self.server = None
        self.complete = False
        self.closed = False

    def run(self):
        self.callback(
            _start_server(
                _url_handler,
                hostname='127.0.0.1',
                port=self.port,
            )
        )

    def callback(self, server):
        self.server = server
        if self.closed:
            self.quit_server()
        else:
            self.sig_server_started.emit()

    def completer(self):
        self.complete = True

    def is_running(self):
        """Check if the server is running"""
        if self.isRunning():
            # Startup
            return True

        if self.server is None:
            return False

        return self.server.serving

    def quit_server(self):
        self.closed = True
        if self.server is None:
            return

        if self.server.serving:
            self.server.stop()


class PydocBrowser(PluginMainWidget):
    """PyDoc browser widget."""

    ENABLE_SPINNER = True

    # --- Signals
    # ------------------------------------------------------------------------
    sig_load_finished = Signal()
    """
    This signal is emitted to indicate the help page has finished loading.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent=parent)

        self._is_running = False
        self.home_url = None
        self.server = None

        # Widgets
        self.label = QLabel(_("Package:"))
        self.url_combo = UrlComboBox(self)
        self.webview = WebView(self,
                               handle_links=self.get_conf('handle_links'))
        self.find_widget = FindReplace(self)

        # Setup
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()
        self.url_combo.setMaxCount(self.get_conf('max_history_entries'))
        tip = _('Write a package name here, e.g. pandas')
        self.url_combo.lineEdit().setPlaceholderText(tip)
        self.url_combo.lineEdit().setToolTip(tip)
        self.webview.setup()
        self.webview.set_zoom_factor(self.get_conf('zoom_factor'))

        # Layout
        spacing = 10
        layout = QVBoxLayout()
        layout.addWidget(self.webview)
        layout.addSpacing(spacing)
        layout.addWidget(self.find_widget)
        layout.addSpacing(int(spacing / 2))
        self.setLayout(layout)

        # Signals
        self.url_combo.valid.connect(
            lambda x: self._handle_url_combo_activation())
        self.webview.loadStarted.connect(self._start)
        self.webview.loadFinished.connect(self._finish)
        self.webview.titleChanged.connect(self.setWindowTitle)
        self.webview.urlChanged.connect(self._change_url)

        if not WEBENGINE:
            self.webview.iconChanged.connect(self._handle_icon_change)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Online help')

    def get_focus_widget(self):
        self.url_combo.lineEdit().selectAll()
        return self.url_combo

    def setup(self):
        # Actions
        home_action = self.create_action(
            PydocBrowserActions.Home,
            text=_("Home"),
            tip=_("Home"),
            icon=self.create_icon('home'),
            triggered=self.go_home,
        )
        find_action = self.create_action(
            PydocBrowserActions.Find,
            text=_("Find"),
            tip=_("Find text"),
            icon=self.create_icon('find'),
            toggled=self.toggle_find_widget,
            initial=False,
        )
        stop_action = self.get_action(WebViewActions.Stop)
        refresh_action = self.get_action(WebViewActions.Refresh)

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.get_action(WebViewActions.Back),
                     self.get_action(WebViewActions.Forward), refresh_action,
                     stop_action, home_action, self.label, self.url_combo,
                     self.get_action(WebViewActions.ZoomIn),
                     self.get_action(WebViewActions.ZoomOut), find_action,
                     ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=PydocBrowserMainToolbarSections.Main,
            )

        # Signals
        self.find_widget.visibility_changed.connect(find_action.setChecked)

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                self.webview.addAction(action)

        self.sig_toggle_view_changed.connect(self.initialize)

    def update_actions(self):
        stop_action = self.get_action(WebViewActions.Stop)
        refresh_action = self.get_action(WebViewActions.Refresh)

        refresh_action.setVisible(not self._is_running)
        stop_action.setVisible(self._is_running)

    # --- Private API
    # ------------------------------------------------------------------------
    def _start(self):
        """Webview load started."""
        self._is_running = True
        self.start_spinner()
        self.update_actions()

    def _finish(self, code):
        """Webview load finished."""
        self._is_running = False
        self.stop_spinner()
        self.update_actions()
        self.sig_load_finished.emit()

    def _continue_initialization(self):
        """Load home page."""
        self.go_home()
        QApplication.restoreOverrideCursor()

    def _handle_url_combo_activation(self):
        """Load URL from combo box first item."""
        if not self._is_running:
            text = str(self.url_combo.currentText())
            self.go_to(self.text_to_url(text))
        else:
            self.get_action(WebViewActions.Stop).trigger()

        self.get_focus_widget().setFocus()

    def _change_url(self, url):
        """
        Displayed URL has changed -> updating URL combo box.
        """
        self.url_combo.add_text(self.url_to_text(url))

    def _handle_icon_change(self):
        """
        Handle icon changes.
        """
        self.url_combo.setItemIcon(self.url_combo.currentIndex(),
                                   self.webview.icon())
        self.setWindowIcon(self.webview.icon())

    # --- Qt overrides
    # ------------------------------------------------------------------------
    def closeEvent(self, event):
        self.server.quit_server()
        event.accept()

    # --- Public API
    # ------------------------------------------------------------------------
    def load_history(self, history):
        """
        Load history.

        Parameters
        ----------
        history: list
            List of searched items.
        """
        self.url_combo.addItems(history)

    @Slot(bool)
    def initialize(self, checked=True):
        """
        Start pydoc server.

        Parameters
        ----------
        checked: bool, optional
            This method is connected to the `sig_toggle_view_changed` signal,
            so that the first time the widget is made visible it will start
            the server. Default is True.
        """
        if checked and self.server is None:
            self.sig_toggle_view_changed.disconnect(self.initialize)
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            QApplication.processEvents()
            self.start_server()

    def is_server_running(self):
        """Return True if pydoc server is already running."""
        return self.server is not None

    def start_server(self):
        """Start pydoc server."""
        if self.server is None:
            self.set_home_url('http://127.0.0.1:{}/'.format(PORT))
        elif self.server.isRunning():
            self.server.sig_server_started.disconnect(
                self._continue_initialization)
            self.server.quit()

        self.server = PydocServer(port=PORT)
        self.server.sig_server_started.connect(
            self._continue_initialization)
        self.server.start()

    def quit_server(self):
        """Quit the server."""
        if self.server is None:
            return

        if self.server.is_running():
            self.server.sig_server_started.disconnect(
                self._continue_initialization)
            self.server.quit_server()
            self.server.quit()

    def get_label(self):
        """Return address label text"""
        return _("Package:")

    def reload(self):
        """Reload page."""
        if self.server:
            self.webview.reload()

    def text_to_url(self, text):
        """
        Convert text address into QUrl object.

        Parameters
        ----------
        text: str
            Url address.
        """
        if text != 'about:blank':
            text += '.html'

        if text.startswith('/'):
            text = text[1:]

        return QUrl(self.home_url.toString() + text)

    def url_to_text(self, url):
        """
        Convert QUrl object to displayed text in combo box.

        Parameters
        ----------
        url: QUrl
            Url address.
        """
        string_url = url.toString()
        if 'about:blank' in string_url:
            return 'about:blank'
        elif 'get?key=' in string_url or 'search?key=' in string_url:
            return url.toString().split('=')[-1]

        return osp.splitext(str(url.path()))[0][1:]

    def set_home_url(self, text):
        """
        Set home URL.

        Parameters
        ----------
        text: str
            Home url address.
        """
        self.home_url = QUrl(text)

    def set_url(self, url):
        """
        Set current URL.

        Parameters
        ----------
        url: QUrl or str
            Url address.
        """
        self._change_url(url)
        self.go_to(url)

    def go_to(self, url_or_text):
        """
        Go to page URL.
        """
        if isinstance(url_or_text, str):
            url = QUrl(url_or_text)
        else:
            url = url_or_text

        self.webview.load(url)

    @Slot()
    def go_home(self):
        """
        Go to home page.
        """
        if self.home_url is not None:
            self.set_url(self.home_url)

    def get_zoom_factor(self):
        """
        Get the current zoom factor.

        Returns
        -------
        int
            Zoom factor.
        """
        return self.webview.get_zoom_factor()

    def get_history(self):
        """
        Return the list of history items in the combobox.

        Returns
        -------
        list
            List of strings.
        """
        history = []
        for index in range(self.url_combo.count()):
            history.append(str(self.url_combo.itemText(index)))

        return history

    @Slot(bool)
    def toggle_find_widget(self, state):
        """
        Show/hide the find widget.

        Parameters
        ----------
        state: bool
            True to show and False to hide the find widget.
        """
        if state:
            self.find_widget.show()
        else:
            self.find_widget.hide()


def test():
    """Run web browser."""
    from spyder.utils.qthelpers import qapplication
    from unittest.mock import MagicMock

    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'onlinehelp'
    app = qapplication(test_time=8)
    widget = PydocBrowser(None, plugin=plugin_mock)
    widget._setup()
    widget.setup()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
