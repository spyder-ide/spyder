# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Help plugin widgets.
"""

# Standard library imports
import os
import re
import socket
import sys

# Third party imports
from qtpy.QtCore import Qt, QUrl, Signal, Slot, QPoint
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE, QWebEnginePage
from qtpy.QtWidgets import (QActionGroup, QComboBox, QLabel, QLineEdit,
                            QMessageBox, QSizePolicy, QStackedLayout,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import get_module_source_path
from spyder.plugins.help.utils.sphinxify import (CSS_PATH, generate_context,
                                                 loading, usage, warning)
from spyder.plugins.help.utils.sphinxthread import SphinxThread
from spyder.py3compat import get_meth_class_inst, to_text_string
from spyder.utils import programs
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import start_file
from spyder.widgets.browser import FrameWebView
from spyder.widgets.comboboxes import EditableComboBox
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1


class HelpWidgetActions:
    # Toggles
    ToggleAutomaticImport = 'toggle_automatic_import_action'
    ToggleLocked = 'toggle_locked_action'
    TogglePlainMode = 'toggle_plain_mode_action'
    ToggleRichMode = 'toggle_rich_mode_action'
    ToggleShowSource = 'toggle_show_source_action'
    ToggleWrap = 'toggle_wrap_action'
    CopyAction = "help_widget_copy_action"
    SelectAll = "select_all_action",
    Home = 'home_action'


class HelpWidgetOptionsMenuSections:
    Display = 'display_section'
    Other = 'other_section'


class HelpWidgetMainToolbarSections:
    Main = 'main_section'


# --- Widgets
# ----------------------------------------------------------------------------
class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
    # Signals
    valid = Signal(bool, bool)

    def __init__(self, parent):
        EditableComboBox.__init__(self, parent)
        self.help = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: '', False: ''}

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if not self.help.source_is_console():
            return True
        if qstr is None:
            qstr = self.currentText()
        if not re.search(r'^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        objtxt = to_text_string(qstr)
        shell_is_defined = False
        if self.help.get_conf('automatic_import'):
            shell = self.help.internal_shell
            if shell is not None:
                shell_is_defined = shell.is_defined(objtxt, force_import=True)
        if not shell_is_defined:
            shell = self.help.get_shell()
            if shell is not None:
                try:
                    shell_is_defined = shell.is_defined(objtxt)
                except socket.error:
                    shell = self.help.get_shell()
                    try:
                        shell_is_defined = shell.is_defined(objtxt)
                    except socket.error:
                        # Well... too bad!
                        pass
        return shell_is_defined

    def validate_current_text(self):
        self.validate(self.currentText())

    def validate(self, qstr, editing=True):
        """Reimplemented to avoid formatting actions"""
        valid = self.is_valid(qstr)
        if self.hasFocus() and valid is not None:
            if editing and not valid:
                # Combo box text is being modified: invalidate the entry
                self.show_tip(self.tips[valid])
                self.valid.emit(False, False)
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                    # See spyder-ide/spyder#9542.
                    self.lineEdit().cursorWordForward(False)
                else:
                    self.valid.emit(False, False)


class RichText(QWidget, SpyderWidgetMixin):
    """
    WebView widget with find dialog
    """
    sig_link_clicked = Signal(QUrl)

    def __init__(self, parent):
        super().__init__(parent, class_parent=parent)

        self.webview = FrameWebView(self)
        self.webview.setup()

        if WEBENGINE:
            self.webview.web_widget.page().setBackgroundColor(
                QColor(MAIN_BG_COLOR))
        else:
            self.webview.web_widget.setStyleSheet(
                "background:{}".format(MAIN_BG_COLOR))
            self.webview.page().setLinkDelegationPolicy(
                QWebEnginePage.DelegateAllLinks)

        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview.web_widget)
        self.find_widget.hide()

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webview)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

        # Signals
        self.webview.linkClicked.connect(self.sig_link_clicked)

    def set_font(self, font, fixed_font=None):
        """Set font"""
        self.webview.set_font(font, fixed_font=fixed_font)

    def set_html(self, html_text, base_url):
        """Set html text"""
        self.webview.setHtml(html_text, base_url)

    def load_url(self, url):
        if isinstance(url, QUrl):
            qurl = url
        else:
            qurl = QUrl(url)

        self.load(qurl)

    def clear(self):
        self.set_html('', self.webview.url())


class PlainText(QWidget):
    """
    Read-only editor widget with find dialog
    """
    # Signals
    focus_changed = Signal()

    sig_custom_context_menu_requested = Signal(QPoint)

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None

        # Read-only simple code editor
        self.editor = SimpleCodeEditor(self)
        self.editor.setup_editor(
            language='py',
            highlight_current_line=False,
            linenumbers=False,
        )
        self.editor.sig_focus_changed.connect(self.focus_changed)
        self.editor.setReadOnly(True)
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

        self.editor.customContextMenuRequested.connect(
            self.sig_custom_context_menu_requested)

    def set_font(self, font, color_scheme=None):
        """Set font"""
        self.editor.set_color_scheme(color_scheme)
        self.editor.set_font(font)

    def set_color_scheme(self, color_scheme):
        """Set color scheme"""
        self.editor.set_color_scheme(color_scheme)

    def set_text(self, text, is_code):
        if is_code:
            self.editor.set_language('py')
        else:
            self.editor.set_language(None)

        self.editor.set_text(text)
        self.editor.set_cursor_position('sof')

    def clear(self):
        self.editor.clear()

    def set_wrap_mode(self, value):
        self.editor.toggle_wrap_mode(value)

    def copy(self):
        self.editor.copy()

    def select_all(self):
        self.editor.selectAll()


class HelpWidget(PluginMainWidget):

    ENABLE_SPINNER = True

    # Signals
    sig_item_found = Signal()
    """This signal is emitted when an item is found."""

    sig_render_started = Signal()
    """This signal is emitted to inform a help text rendering has started."""

    sig_render_finished = Signal()
    """This signal is emitted to inform a help text rendering has finished."""

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Attributes
        self._starting_up = True
        self._current_color_scheme = None
        self._last_texts = [None, None]
        self._last_editor_doc = None
        self._last_console_cb = None
        self._last_editor_cb = None
        self.css_path = self.get_conf('css_path')
        self.no_docs = _("No documentation available")
        self.docstring = True  # TODO: What is this used for?

        # Widgets
        self._sphinx_thread = SphinxThread(
            html_text_no_doc=warning(self.no_docs, css_path=self.css_path),
            css_path=self.css_path,
        )
        self.shell = None
        self.internal_console = None
        self.internal_shell = None
        self.plain_text = PlainText(self)
        self.rich_text = RichText(self)
        self.source_label = QLabel(_("Source"))
        self.source_combo = QComboBox(self)
        self.object_label = QLabel(_("Object"))
        self.object_combo = ObjectComboBox(self)
        self.object_edit = QLineEdit(self)

        # Setup
        self.object_edit.setReadOnly(True)
        self.object_combo.setMaxCount(self.get_conf('max_history_entries'))
        self.object_combo.setItemText(0, '')
        self.plain_text.set_wrap_mode(self.get_conf('wrap'))
        self.source_combo.addItems([_("Console"), _("Editor")])
        if (not programs.is_module_installed('rope') and
                not programs.is_module_installed('jedi', '>=0.11.0')):
            self.source_combo.hide()
            self.source_label.hide()

        # Layout
        self.stack_layout = layout = QStackedLayout()
        layout.addWidget(self.rich_text)
        layout.addWidget(self.plain_text)
        self.setLayout(layout)

        # Signals
        self._sphinx_thread.html_ready.connect(
            self._on_sphinx_thread_html_ready)
        self._sphinx_thread.error_msg.connect(
            self._on_sphinx_thread_error_msg)
        self.object_combo.valid.connect(self.force_refresh)
        self.rich_text.sig_link_clicked.connect(self.handle_link_clicks)
        self.source_combo.currentIndexChanged.connect(
            lambda x: self.source_changed())
        self.sig_render_started.connect(self.start_spinner)
        self.sig_render_finished.connect(self.stop_spinner)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Help')

    def setup(self):
        self.wrap_action = self.create_action(
            name=HelpWidgetActions.ToggleWrap,
            text=_("Wrap lines"),
            toggled=True,
            initial=self.get_conf('wrap'),
            option='wrap'
        )
        self.copy_action = self.create_action(
            name=HelpWidgetActions.CopyAction,
            text=_("Copy"),
            triggered=lambda value: self.plain_text.copy(),
            register_shortcut=False,
        )
        self.select_all_action = self.create_action(
            name=HelpWidgetActions.SelectAll,
            text=_("Select All"),
            triggered=lambda value: self.plain_text.select_all(),
            register_shortcut=False,
        )
        self.auto_import_action = self.create_action(
            name=HelpWidgetActions.ToggleAutomaticImport,
            text=_("Automatic import"),
            toggled=True,
            initial=self.get_conf('automatic_import'),
            option='automatic_import'
        )
        self.show_source_action = self.create_action(
            name=HelpWidgetActions.ToggleShowSource,
            text=_("Show Source"),
            toggled=True,
            option='show_source'
        )
        self.rich_text_action = self.create_action(
            name=HelpWidgetActions.ToggleRichMode,
            text=_("Rich Text"),
            toggled=True,
            initial=self.get_conf('rich_mode'),
            option='rich_mode'
        )
        self.plain_text_action = self.create_action(
            name=HelpWidgetActions.TogglePlainMode,
            text=_("Plain Text"),
            toggled=True,
            initial=self.get_conf('plain_mode'),
            option='plain_mode'
        )
        self.locked_action = self.create_action(
            name=HelpWidgetActions.ToggleLocked,
            text=_("Lock/Unlock"),
            toggled=True,
            icon=self.create_icon('lock_open'),
            initial=self.get_conf('locked'),
            option='locked'
        )
        self.home_action = self.create_action(
            name=HelpWidgetActions.Home,
            text=_("Home"),
            triggered=self.show_intro_message,
            icon=self.create_icon('home'),
        )

        # Add the help actions to an exclusive QActionGroup
        help_actions = QActionGroup(self)
        help_actions.setExclusive(True)
        help_actions.addAction(self.plain_text_action)
        help_actions.addAction(self.rich_text_action)

        # Menu
        menu = self.get_options_menu()
        for item in [self.rich_text_action, self.plain_text_action,
                     self.show_source_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=HelpWidgetOptionsMenuSections.Display,
            )

        self.add_item_to_menu(
            self.auto_import_action,
            menu=menu,
            section=HelpWidgetOptionsMenuSections.Other,
        )

        # Plain text menu
        self._plain_text_context_menu = self.create_menu(
            "plain_text_context_menu")
        self.add_item_to_menu(
            self.copy_action,
            self._plain_text_context_menu,
            section="copy_section",
        )
        self.add_item_to_menu(
            self.select_all_action,
            self._plain_text_context_menu,
            section="select_section",
        )
        self.add_item_to_menu(
            self.wrap_action,
            self._plain_text_context_menu,
            section="wrap_section",
        )

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.source_label, self.source_combo, self.object_label,
                     self.object_combo, self.object_edit, self.home_action,
                     self.locked_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=HelpWidgetMainToolbarSections.Main,
            )

        self.source_changed()
        self.switch_to_rich_text()
        self.show_intro_message()

        # Signals
        self.plain_text.sig_custom_context_menu_requested.connect(
            self._show_plain_text_context_menu)

    def _should_display_welcome_page(self):
        """Determine if the help welcome page should be displayed."""
        return (self._last_editor_doc is None or
                self._last_console_cb is None or
                self._last_editor_cb is None)

    @on_conf_change(option='wrap')
    def on_wrap_option_update(self, value):
        self.plain_text.set_wrap_mode(value)

    @on_conf_change(option='locked')
    def on_lock_update(self, value):
        if value:
            icon = self.create_icon('lock')
            tip = _("Unlock")
        else:
            icon = self.create_icon('lock_open')
            tip = _("Lock")

        action = self.get_action(HelpWidgetActions.ToggleLocked)
        action.setIcon(icon)
        action.setToolTip(tip)

    @on_conf_change(option='automatic_import')
    def on_automatic_import_update(self, value):
        self.object_combo.validate_current_text()
        if self._should_display_welcome_page():
            self.show_intro_message()
        else:
            self.force_refresh()

    @on_conf_change(option='rich_mode')
    def on_rich_mode_update(self, value):
        if value:
            # Plain Text OFF / Rich text ON
            self.docstring = not value
            self.stack_layout.setCurrentWidget(self.rich_text)
            self.get_action(HelpWidgetActions.ToggleShowSource).setChecked(
                False)
        else:
            # Plain Text ON / Rich text OFF
            self.docstring = value
            self.stack_layout.setCurrentWidget(self.plain_text)

        if self._should_display_welcome_page():
            self.show_intro_message()
        else:
            self.force_refresh()

    @on_conf_change(option='show_source')
    def on_show_source_update(self, value):
        if value:
            self.switch_to_plain_text()
            self.get_action(HelpWidgetActions.ToggleRichMode).setChecked(
                False)

        self.docstring = not value
        if self._should_display_welcome_page():
            self.show_intro_message()
        else:
            self.force_refresh()

    def update_actions(self):
        for __, action in self.get_actions().items():
            # IMPORTANT: Since we are defining the main actions in here
            # and the context is WidgetWithChildrenShortcut we need to
            # assign the same actions to the children widgets in order
            # for shortcuts to work
            for widget in [self.plain_text,
                           self.rich_text,
                           self.source_combo,
                           self.object_combo,
                           self.object_edit]:
                if action not in widget.actions():
                    widget.addAction(action)

    def get_focus_widget(self):
        self.object_combo.lineEdit().selectAll()
        return self.object_combo

    # --- Private API
    # ------------------------------------------------------------------------
    @Slot(QPoint)
    def _show_plain_text_context_menu(self, point):
        point = self.plain_text.mapToGlobal(point)
        self._plain_text_context_menu.popup(point)

    def _on_sphinx_thread_html_ready(self, html_text):
        """
        Set our sphinx documentation based on thread result.

        Parameters
        ----------
        html_text: str
            Html results text.
        """
        self._sphinx_thread.wait()
        self.set_rich_text_html(html_text, QUrl.fromLocalFile(self.css_path))
        self.sig_render_finished.emit()
        self.stop_spinner()

    def _on_sphinx_thread_error_msg(self, error_msg):
        """
        Display error message on Sphinx rich text failure.

        Parameters
        ----------
        error_msg: str
            Error message text.
        """
        self._sphinx_thread.wait()
        self.plain_text_action.setChecked(True)
        sphinx_ver = programs.get_module_version('sphinx')
        QMessageBox.critical(
            self,
            _('Help'),
            _("The following error occurred when calling "
              "<b>Sphinx %s</b>. <br>Incompatible Sphinx "
              "version or doc string decoding failed."
              "<br><br>Error message:<br>%s"
              ) % (sphinx_ver, error_msg),
        )
        self.sig_render_finished.emit()

    # --- Public API
    # ------------------------------------------------------------------------
    def source_is_console(self):
        """Return True if source is Console."""
        return self.source_combo.currentIndex() == 0

    def switch_to_editor_source(self):
        """Switch to editor view of the help viewer."""
        self.source_combo.setCurrentIndex(1)

    def switch_to_console_source(self):
        """Switch to console view of the help viewer."""
        self.source_combo.setCurrentIndex(0)

    def source_changed(self):
        """Handle a source (plain/rich) change."""
        is_console = self.source_is_console()
        if is_console:
            self.object_combo.show()
            self.object_edit.hide()
        else:
            # Editor
            self.object_combo.hide()
            self.object_edit.show()

        self.get_action(HelpWidgetActions.ToggleShowSource).setEnabled(
            is_console)
        self.get_action(HelpWidgetActions.ToggleAutomaticImport).setEnabled(
            is_console)
        self.restore_text()

    def save_text(self, callback):
        """
        Save help text.

        Parameters
        ----------
        callback: callable
            Method to call on save.
        """
        if self.source_is_console():
            self._last_console_cb = callback
        else:
            self._last_editor_cb = callback

    def restore_text(self):
        """Restore last text using callback."""
        if self.source_is_console():
            cb = self._last_console_cb
        else:
            cb = self._last_editor_cb

        if cb is None:
            if self.get_conf('plain_mode'):
                self.switch_to_plain_text()
            else:
                self.switch_to_rich_text()
        else:
            func = cb[0]
            args = cb[1:]
            func(*args)
            if get_meth_class_inst(func) is self.rich_text:
                self.switch_to_rich_text()
            else:
                self.switch_to_plain_text()

    @property
    def find_widget(self):
        """Show find widget."""
        if self.get_conf('plain_mode'):
            return self.plain_text.find_widget
        else:
            return self.rich_text.find_widget

    def switch_to_plain_text(self):
        """Switch to plain text mode."""
        self.get_action(HelpWidgetActions.TogglePlainMode).setChecked(True)

    def switch_to_rich_text(self):
        """Switch to rich text mode."""
        self.get_action(HelpWidgetActions.ToggleRichMode).setChecked(True)

    def set_plain_text(self, text, is_code):
        """
        Set plain text docs.

        Parameters
        ----------
        text: str
            Text content.
        is_code: bool
            True if it is code text.

        Notes
        -----
        Text is coming from utils.dochelpers.getdoc
        """
        if type(text) is dict:
            name = text['name']
            if name:
                rst_title = ''.join(['='*len(name), '\n', name, '\n',
                                    '='*len(name), '\n\n'])
            else:
                rst_title = ''
            try:
                if text['argspec']:
                    definition = ''.join(
                        ['Definition: ', name, text['argspec'], '\n\n'])
                else:
                    definition = ''

                if text['note']:
                    note = ''.join(['Type: ', text['note'], '\n\n----\n\n'])
                else:
                    note = ''
            except TypeError:
                definition = self.no_docs
                note = ''

            full_text = ''.join([rst_title, definition, note,
                                 text['docstring']])
        else:
            full_text = text

        self.plain_text.set_text(full_text, is_code)
        self.save_text([self.plain_text.set_text, full_text, is_code])

    def set_rich_text_html(self, html_text, base_url):
        """
        Set rich text.

        Parameters
        ----------
        html_text: str
            Html string.
        base_url: str
            Location of stylesheets and images to load in the page.
        """
        self.rich_text.set_html(html_text, base_url)
        self.save_text([self.rich_text.set_html, html_text, base_url])

    def show_loading_message(self):
        """Create html page to show while the documentation is generated."""
        self.sig_render_started.emit()
        loading_message = _("Retrieving documentation")
        loading_img = get_image_path('loading_sprites')
        if os.name == 'nt':
            loading_img = loading_img.replace('\\', '/')

        self.set_rich_text_html(
            loading(loading_message, loading_img, css_path=self.css_path),
            QUrl.fromLocalFile(self.css_path),
        )

    def show_intro_message(self):
        """Show message on Help with the right shortcuts."""
        intro_message_eq = _(
            "Here you can get help of any object by pressing "
            "%s in front of it, either on the Editor or the "
            "Console.%s")
        intro_message_dif = _(
            "Here you can get help of any object by pressing "
            "%s in front of it on the Editor, or %s in front "
            "of it on the Console.%s")
        intro_message_common = _(
            "Help can also be shown automatically after writing "
            "a left parenthesis next to an object. You can "
            "activate this behavior in %s.")
        prefs = _("Preferences > Help")

        shortcut_editor = self.get_conf('editor/inspect current object',
                                        section='shortcuts')
        shortcut_console = self.get_conf('console/inspect current object',
                                         section='shortcuts')

        if sys.platform == 'darwin':
            shortcut_editor = shortcut_editor.replace('Ctrl', 'Cmd')
            shortcut_console = shortcut_console.replace('Ctrl', 'Cmd')

        if self.get_conf('rich_mode'):
            title = _("Usage")
            tutorial_message = _("New to Spyder? Read our")
            tutorial = _("tutorial")
            if shortcut_editor == shortcut_console:
                intro_message = (intro_message_eq + intro_message_common) % (
                    "<b>"+shortcut_editor+"</b>", "<br><br>",
                    "<i>"+prefs+"</i>")
            else:
                intro_message = (intro_message_dif + intro_message_common) % (
                    "<b>"+shortcut_editor+"</b>",
                    "<b>"+shortcut_console+"</b>",
                    "<br><br>", "<i>"+prefs+"</i>")

            self.set_rich_text_html(usage(title, intro_message,
                                          tutorial_message, tutorial,
                                          css_path=self.css_path),
                                    QUrl.fromLocalFile(self.css_path))
        else:
            install_sphinx = "\n\n%s" % _("Please consider installing Sphinx "
                                          "to get documentation rendered in "
                                          "rich text.")
            if shortcut_editor == shortcut_console:
                intro_message = (intro_message_eq + intro_message_common) % (
                    shortcut_editor, "\n\n", prefs)
            else:
                intro_message = (intro_message_dif + intro_message_common) % (
                    shortcut_editor, shortcut_console, "\n\n", prefs)

            intro_message += install_sphinx
            self.set_plain_text(intro_message, is_code=False)

    def show_rich_text(self, text, collapse=False, img_path=''):
        """
        Show text in rich mode.

        Parameters
        ----------
        text: str
            Plain text to display.
        collapse: bool, optional
            Show collapsable sections as collapsed/expanded. Default is False.
        img_path: str, optional
            Path to folder with additional images needed to correctly
            display the rich text help. Default is ''.
        """
        self.switch_to_rich_text()
        context = generate_context(collapse=collapse, img_path=img_path,
                                   css_path=self.css_path)
        self.render_sphinx_doc(text, context)

    def show_plain_text(self, text):
        """
        Show text in plain mode.

        Parameters
        ----------
        text: str
            Plain text to display.
        """
        self.switch_to_plain_text()
        self.set_plain_text(text, is_code=False)

    @Slot()
    def show_tutorial(self):
        """Show the Spyder tutorial."""
        tutorial_path = get_module_source_path('spyder.plugins.help.utils')
        tutorial = os.path.join(tutorial_path, 'tutorial.rst')

        with open(tutorial, 'r') as fh:
            text = fh.read()

        self.show_rich_text(text, collapse=True)

    def handle_link_clicks(self, url):
        """
        Handle how url links should be opened.

        Parameters
        ----------
        url: QUrl
            QUrl object containing the link to open.
        """
        url = to_text_string(url.toString())
        if url == "spy://tutorial":
            self.show_tutorial()
        elif url.startswith('http'):
            start_file(url)
        else:
            self.rich_text.load_url(url)

    @Slot()
    @Slot(bool)
    @Slot(bool, bool)
    def force_refresh(self, valid=True, editing=True):
        """
        Force a refresh/rerender of the help viewer content.

        Parameters
        ----------
        valid: bool, optional
            Default is True.
        editing: bool, optional
            Default is True.
        """
        if valid:
            if self.source_is_console():
                self.set_object_text(None, force_refresh=True)
            elif self._last_editor_doc is not None:
                self.set_editor_doc(self._last_editor_doc, force_refresh=True)

    def set_object_text(self, text, force_refresh=False, ignore_unknown=False):
        """
        Set object's name in Help's combobox.

        Parameters
        ----------
        text: str
            Object name.
        force_refresh: bool, optional
            Force a refresh with the rendering.
        ignore_unknown: bool, optional
            Ignore not found object names.

        See Also
        --------
        :py:meth:spyder.widgets.mixins.GetHelpMixin.show_object_info
        """
        if self.get_conf('locked') and not force_refresh:
            return

        self.switch_to_console_source()
        add_to_combo = True
        if text is None:
            text = to_text_string(self.object_combo.currentText())
            add_to_combo = False

        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return

        if add_to_combo:
            self.object_combo.add_text(text)

        if found:
            self.sig_item_found.emit()

        index = self.source_combo.currentIndex()
        self._last_texts[index] = text

    def set_editor_doc(self, help_data, force_refresh=False):
        """
        Set content for help data sent from the editor.

        Parameters
        ----------
        help_data: dict
            Dictionary with editor introspection information.
        force_refresh: bool, optional
            Force a refresh with the rendering.

        Examples
        --------
        >>> help_data = {
            'obj_text': str,
            'name': str,
            'argspec': str,
            'note': str,
            'docstring': str,
            'path': str,
        }
        """
        if self.get_conf('locked') and not force_refresh:
            return

        self.switch_to_editor_source()
        self._last_editor_doc = help_data
        self.object_edit.setText(help_data['obj_text'])

        if self.get_conf('rich_mode'):
            self.render_sphinx_doc(help_data)
        else:
            self.set_plain_text(help_data, is_code=False)

        index = self.source_combo.currentIndex()
        self._last_texts[index] = help_data['docstring']

    def set_shell(self, shell):
        """
        Bind to shell.

        Parameters
        ----------
        shell: object
            internal shell or ipython console shell
        """
        self.shell = shell

    def get_shell(self):
        """
        Return shell which is currently bound to Help.
        """
        if self.shell is None:
            self.shell = self.internal_shell

        return self.shell

    def render_sphinx_doc(self, help_data, context=None, css_path=CSS_PATH):
        """
        Transform help_data dictionary to HTML and show it.

        Parameters
        ----------
        help_data: str or dict
            Dictionary with editor introspection information.
        context: dict
            Sphinx context.
        css_path: str
            Path to CSS file for styling.
        """
        if isinstance(help_data, dict):
            path = help_data.pop('path', '')
            dname = os.path.dirname(path)
        else:
            dname = ''

        # Math rendering option could have changed
        self._sphinx_thread.render(help_data, context, self.get_conf('math'),
                                   dname, css_path=self.css_path)
        self.show_loading_message()

    def show_help(self, obj_text, ignore_unknown=False):
        """
        Show help for an object's name.

        Parameters
        ----------
        obj_text: str
            Object's name.
        ignore_unknown: bool, optional
            Ignore unknown object's name.
        """
        # TODO: This method makes active use of the shells. It would be better
        # to use signals and pass information this way for better decoupling.
        shell = self.get_shell()
        if shell is None:
            return

        obj_text = to_text_string(obj_text)

        if not shell.is_defined(obj_text):
            if (self.get_conf('automatic_import')
                    and self.internal_shell.is_defined(obj_text,
                                                       force_import=True)):
                shell = self.internal_shell
            else:
                shell = None
                doc = None
                source_text = None

        if shell is not None:
            doc = shell.get_doc(obj_text)
            source_text = shell.get_source(obj_text)

        is_code = False

        if self.get_conf('rich_mode'):
            self.render_sphinx_doc(doc, css_path=self.css_path)
            return doc is not None
        elif self.docstring:
            hlp_text = doc
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    return False
        else:
            hlp_text = source_text
            if hlp_text is None:
                hlp_text = doc
                if hlp_text is None:
                    hlp_text = _("No source code available.")
                    if ignore_unknown:
                        return False
            else:
                is_code = True

        self.set_plain_text(hlp_text, is_code=is_code)
        return True

    def set_rich_text_font(self, font, fixed_font):
        """
        Set rich text mode font.

        Parameters
        ----------
        fixed_font: QFont
            The current rich text font to use.
        """

        self.rich_text.set_font(font, fixed_font=fixed_font)

    def set_plain_text_font(self, font, color_scheme=None):
        """
        Set plain text mode font.

        Parameters
        ----------
        font: QFont
            The current plain text font to use.
        color_scheme: str
            The selected color scheme.
        """
        if color_scheme is None:
            color_scheme = self._current_color_scheme

        self.plain_text.set_font(font, color_scheme=color_scheme)

    def set_plain_text_color_scheme(self, color_scheme):
        """
        Set plain text mode color scheme.

        Parameters
        ----------
        color_scheme: str
            The selected color scheme.
        """
        self._current_color_scheme = color_scheme
        self.plain_text.set_color_scheme(color_scheme)

    def set_history(self, history):
        """
        Set list of strings on object combo box.

        Parameters
        ----------
        history: list
            List of strings of objects.
        """
        self.object_combo.addItems(history)

    def get_history(self):
        """
        Return list of strings on object combo box.
        """
        history = []
        for index in range(self.object_combo.count()):
            history.append(to_text_string(self.object_combo.itemText(index)))

        return history

    def set_internal_console(self, console):
        """
        Set the internal console shell.

        Parameters
        ----------
        console: :py:class:spyder.plugins.console.plugin.Console
            Console plugin.
        """
        self.internal_console = console
        self.internal_shell = console.get_widget().shell
