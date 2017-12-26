# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Help Plugin"""

# Standard library imports
import re
import os.path as osp
import socket
import sys

# Third party imports
from qtpy.QtCore import QThread, QUrl, Signal, Slot
from qtpy.QtWidgets import (QActionGroup, QComboBox, QGroupBox, QHBoxLayout,
                            QLabel, QLineEdit, QMenu, QMessageBox, QSizePolicy,
                            QToolButton, QVBoxLayout, QWidget)
from qtpy.QtWebEngineWidgets import QWebEnginePage, WEBENGINE

# Local imports
from spyder import dependencies
from spyder.config.base import _, get_conf_path, get_module_source_path
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.py3compat import get_meth_class_inst, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import programs
from spyder.utils.help.sphinxify import (CSS_PATH, generate_context,
                                         sphinxify, usage, warning)
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout,
                                    MENU_SEPARATOR)
from spyder.widgets.browser import FrameWebView
from spyder.widgets.comboboxes import EditableComboBox
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.sourcecode import codeeditor


# Sphinx dependency
dependencies.add("sphinx", _("Show help for objects in the Editor and "
                             "Consoles in a dedicated pane"),
                 required_version='>=0.6.6')



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
        if not re.search('^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        objtxt = to_text_string(qstr)
        if self.help.get_option('automatic_import'):
            shell = self.help.internal_shell
            if shell is not None:
                return shell.is_defined(objtxt, force_import=True)
        shell = self.help.get_shell()
        if shell is not None:
            try:
                return shell.is_defined(objtxt)
            except socket.error:
                shell = self.help.get_shell()
                try:
                    return shell.is_defined(objtxt)
                except socket.error:
                    # Well... too bad!
                    pass

    def validate_current_text(self):
        self.validate(self.currentText())

    def validate(self, qstr, editing=True):
        """Reimplemented to avoid formatting actions"""
        valid = self.is_valid(qstr)
        if self.hasFocus() and valid is not None:
            if editing:
                # Combo box text is being modified: invalidate the entry
                self.show_tip(self.tips[valid])
                self.valid.emit(False, False)
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                else:
                    self.valid.emit(False, False)


class HelpConfigPage(PluginConfigPage):
    def setup_page(self):
        # Connections group
        connections_group = QGroupBox(_("Automatic connections"))
        connections_label = QLabel(_("This pane can automatically "
                                     "show an object's help information after "
                                     "a left parenthesis is written next to it. "
                                     "Below you can decide to which plugin "
                                     "you want to connect it to turn on this "
                                     "feature."))
        connections_label.setWordWrap(True)
        editor_box = self.create_checkbox(_("Editor"), 'connect/editor')
        rope_installed = programs.is_module_installed('rope')
        jedi_installed = programs.is_module_installed('jedi', '>=0.8.1')
        editor_box.setEnabled(rope_installed or jedi_installed)
        if not rope_installed and not jedi_installed:
            editor_tip = _("This feature requires the Rope or Jedi libraries.\n"
                           "It seems you don't have either installed.")
            editor_box.setToolTip(editor_tip)
        ipython_box = self.create_checkbox(_("IPython Console"),
                                           'connect/ipython_console')

        connections_layout = QVBoxLayout()
        connections_layout.addWidget(connections_label)
        connections_layout.addWidget(editor_box)
        connections_layout.addWidget(ipython_box)
        connections_group.setLayout(connections_layout)

        # Features group
        features_group = QGroupBox(_("Additional features"))
        math_box = self.create_checkbox(_("Render mathematical equations"),
                                        'math')
        req_sphinx = programs.is_module_installed('sphinx', '>=1.1')
        math_box.setEnabled(req_sphinx)
        if not req_sphinx:
            sphinx_ver = programs.get_module_version('sphinx')
            sphinx_tip = _("This feature requires Sphinx 1.1 or superior.")
            sphinx_tip += "\n" + _("Sphinx %s is currently installed.") % sphinx_ver
            math_box.setToolTip(sphinx_tip)

        features_layout = QVBoxLayout()
        features_layout.addWidget(math_box)
        features_group.setLayout(features_layout)

        # Source code group
        sourcecode_group = QGroupBox(_("Source code"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_group.setLayout(sourcecode_layout)

        # Final layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(connections_group)
        vlayout.addWidget(features_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class RichText(QWidget):
    """
    WebView widget with find dialog
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.webview = FrameWebView(self)
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview.web_widget)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webview)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

    def set_font(self, font, fixed_font=None):
        """Set font"""
        self.webview.set_font(font, fixed_font=fixed_font)

    def set_html(self, html_text, base_url):
        """Set html text"""
        self.webview.setHtml(html_text, base_url)

    def clear(self):
        self.set_html('', self.webview.url())


class PlainText(QWidget):
    """
    Read-only editor widget with find dialog
    """
    # Signals
    focus_changed = Signal()

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None

        # Read-only editor
        self.editor = codeeditor.CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 scrollflagarea=False, edge_line=False)
        self.editor.focus_changed.connect(lambda: self.focus_changed.emit())
        self.editor.setReadOnly(True)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

    def set_font(self, font, color_scheme=None):
        """Set font"""
        self.editor.set_font(font, color_scheme=color_scheme)

    def set_color_scheme(self, color_scheme):
        """Set color scheme"""
        self.editor.set_color_scheme(color_scheme)

    def set_text(self, text, is_code):
        self.editor.set_highlight_current_line(is_code)
        self.editor.set_occurrence_highlighting(is_code)
        if is_code:
            self.editor.set_language('py')
        else:
            self.editor.set_language(None)
        self.editor.set_text(text)
        self.editor.set_cursor_position('sof')

    def clear(self):
        self.editor.clear()


class SphinxThread(QThread):
    """
    A worker thread for handling rich text rendering.

    Parameters
    ----------
    doc : str or dict
        A string containing a raw rst text or a dict containing
        the doc string components to be rendered.
        See spyder.utils.dochelpers.getdoc for description.
    context : dict
        A dict containing the substitution variables for the
        layout template
    html_text_no_doc : unicode
        Text to be rendered if doc string cannot be extracted.
    math_option : bool
        Use LaTeX math rendering.

    """
    # Signals
    error_msg = Signal(str)
    html_ready = Signal(str)

    def __init__(self, html_text_no_doc=''):
        super(SphinxThread, self).__init__()
        self.doc = None
        self.context = None
        self.html_text_no_doc = html_text_no_doc
        self.math_option = False

    def render(self, doc, context=None, math_option=False, img_path=''):
        """Start thread to render a given documentation"""
        # If the thread is already running wait for it to finish before
        # starting it again.
        if self.wait():
            self.doc = doc
            self.context = context
            self.math_option = math_option
            self.img_path = img_path
            # This causes run() to be executed in separate thread
            self.start()

    def run(self):
        html_text = self.html_text_no_doc
        doc = self.doc
        if doc is not None:
            if type(doc) is dict and 'docstring' in doc.keys():
                try:
                    context = generate_context(name=doc['name'],
                                               argspec=doc['argspec'],
                                               note=doc['note'],
                                               math=self.math_option,
                                               img_path=self.img_path)
                    html_text = sphinxify(doc['docstring'], context)
                    if doc['docstring'] == '' and \
                      any([doc['name'], doc['argspec'], doc['note']]):
                        msg = _("No further documentation available")
                        html_text += '<div class="hr"></div>'
                        html_text += '<div id="doc-warning">%s</div>' % msg
                except Exception as error:
                    self.error_msg.emit(to_text_string(error))
                    return
            elif self.context is not None:
                try:
                    html_text = sphinxify(doc, self.context)
                except Exception as error:
                    self.error_msg.emit(to_text_string(error))
                    return
        self.html_ready.emit(html_text)


class Help(SpyderPluginWidget):
    """
    Docstrings viewer widget
    """
    CONF_SECTION = 'help'
    CONFIGWIDGET_CLASS = HelpConfigPage
    LOG_PATH = get_conf_path(CONF_SECTION)
    FONT_SIZE_DELTA = DEFAULT_SMALL_DELTA

    # Signals
    focus_changed = Signal()

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        self.internal_shell = None

        # Initialize plugin
        self.initialize_plugin()

        self.no_doc_string = _("No documentation available")

        self._last_console_cb = None
        self._last_editor_cb = None

        self.plain_text = PlainText(self)
        self.rich_text = RichText(self)

        color_scheme = self.get_color_scheme()
        self.set_plain_text_font(self.get_plugin_font(), color_scheme)
        self.plain_text.editor.toggle_wrap_mode(self.get_option('wrap'))

        # Add entries to read-only editor context-menu
        self.wrap_action = create_action(self, _("Wrap lines"),
                                         toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked(self.get_option('wrap'))
        self.plain_text.editor.readonly_menu.addSeparator()
        add_actions(self.plain_text.editor.readonly_menu, (self.wrap_action,))

        self.set_rich_text_font(self.get_plugin_font('rich_text'))

        self.shell = None

        # locked = disable link with Console
        self.locked = False
        self._last_texts = [None, None]
        self._last_editor_doc = None

        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.setContentsMargins(0, 0, 0, 0)
        txt = _("Source")
        if sys.platform == 'darwin':
            source_label = QLabel("  " + txt)
        else:
            source_label = QLabel(txt)
        layout_edit.addWidget(source_label)
        self.source_combo = QComboBox(self)
        self.source_combo.addItems([_("Console"), _("Editor")])
        self.source_combo.currentIndexChanged.connect(self.source_changed)
        if (not programs.is_module_installed('rope') and
                not programs.is_module_installed('jedi', '>=0.8.1')):
            self.source_combo.hide()
            source_label.hide()
        layout_edit.addWidget(self.source_combo)
        layout_edit.addSpacing(10)
        layout_edit.addWidget(QLabel(_("Object")))
        self.combo = ObjectComboBox(self)
        layout_edit.addWidget(self.combo)
        self.object_edit = QLineEdit(self)
        self.object_edit.setReadOnly(True)
        layout_edit.addWidget(self.object_edit)
        self.combo.setMaxCount(self.get_option('max_history_entries'))
        self.combo.addItems( self.load_history() )
        self.combo.setItemText(0, '')
        self.combo.valid.connect(lambda valid: self.force_refresh())

        # Plain text docstring option
        self.docstring = True
        self.rich_help = self.get_option('rich_mode', True)
        self.plain_text_action = create_action(self, _("Plain Text"),
                                               toggled=self.toggle_plain_text)

        # Source code option
        self.show_source_action = create_action(self, _("Show Source"),
                                                toggled=self.toggle_show_source)

        # Rich text option
        self.rich_text_action = create_action(self, _("Rich Text"),
                                         toggled=self.toggle_rich_text)

        # Add the help actions to an exclusive QActionGroup
        help_actions = QActionGroup(self)
        help_actions.setExclusive(True)
        help_actions.addAction(self.plain_text_action)
        help_actions.addAction(self.rich_text_action)

        # Automatic import option
        self.auto_import_action = create_action(self, _("Automatic import"),
                                                toggled=self.toggle_auto_import)
        auto_import_state = self.get_option('automatic_import')
        self.auto_import_action.setChecked(auto_import_state)

        # Lock checkbox
        self.locked_button = create_toolbutton(self,
                                               triggered=self.toggle_locked)
        layout_edit.addWidget(self.locked_button)
        self._update_lock_icon()

        # Option menu
        self.menu = QMenu(self)
        add_actions(self.menu, [self.rich_text_action, self.plain_text_action,
                                self.show_source_action, MENU_SEPARATOR,
                                self.auto_import_action, MENU_SEPARATOR,
                                self.undock_action])
        self.options_button.setMenu(self.menu)
        layout_edit.addWidget(self.options_button)

        if self.rich_help:
            self.switch_to_rich_text()
        else:
            self.switch_to_plain_text()
        self.plain_text_action.setChecked(not self.rich_help)
        self.rich_text_action.setChecked(self.rich_help)
        self.source_changed()

        # Main layout
        layout = create_plugin_layout(layout_edit)
        # we have two main widgets, but only one of them is shown at a time
        layout.addWidget(self.plain_text)
        layout.addWidget(self.rich_text)
        self.setLayout(layout)

        # Add worker thread for handling rich text rendering
        self._sphinx_thread = SphinxThread(
                                  html_text_no_doc=warning(self.no_doc_string))
        self._sphinx_thread.html_ready.connect(
                                             self._on_sphinx_thread_html_ready)
        self._sphinx_thread.error_msg.connect(self._on_sphinx_thread_error_msg)

        # Handle internal and external links
        view = self.rich_text.webview
        if not WEBENGINE:
            view.page().setLinkDelegationPolicy(QWebEnginePage.DelegateAllLinks)
        view.linkClicked.connect(self.handle_link_clicks)

        self._starting_up = True

    #------ SpyderPluginWidget API ---------------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.variableexplorer, self)

    def get_plugin_title(self):
        """Return widget title"""
        return _('Help')

    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('help')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.combo.lineEdit().selectAll()
        return self.combo

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
        self.main.console.set_help(self)
        self.internal_shell = self.main.console.shell

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
            self.switch_to_rich_text()
            self.show_intro_message()

    def update_font(self):
        """Update font from Preferences"""
        color_scheme = self.get_color_scheme()
        font = self.get_plugin_font()
        rich_font = self.get_plugin_font(rich_text=True)

        self.set_plain_text_font(font, color_scheme=color_scheme)
        self.set_rich_text_font(rich_font)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = self.get_color_scheme()
        connect_n = 'connect_to_oi'
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        math_n = 'math'
        math_o = self.get_option(math_n)

        if color_scheme_n in options:
            self.set_plain_text_color_scheme(color_scheme_o)
        if wrap_n in options:
            self.toggle_wrap_mode(wrap_o)
        if math_n in options:
            self.toggle_math_mode(math_o)

        # To make auto-connection changes take place instantly
        self.main.editor.apply_plugin_settings(options=[connect_n])
        self.main.ipyconsole.apply_plugin_settings(options=[connect_n])

    #------ Public API (related to Help's source) -------------------------
    def source_is_console(self):
        """Return True if source is Console"""
        return self.source_combo.currentIndex() == 0

    def switch_to_editor_source(self):
        self.source_combo.setCurrentIndex(1)

    def switch_to_console_source(self):
        self.source_combo.setCurrentIndex(0)

    def source_changed(self, index=None):
        if self.source_is_console():
            # Console
            self.combo.show()
            self.object_edit.hide()
            self.show_source_action.setEnabled(True)
            self.auto_import_action.setEnabled(True)
        else:
            # Editor
            self.combo.hide()
            self.object_edit.show()
            self.show_source_action.setDisabled(True)
            self.auto_import_action.setDisabled(True)
        self.restore_text()

    def save_text(self, callback):
        if self.source_is_console():
            self._last_console_cb = callback
        else:
            self._last_editor_cb = callback

    def restore_text(self):
        if self.source_is_console():
            cb = self._last_console_cb
        else:
            cb = self._last_editor_cb
        if cb is None:
            if self.is_plain_text_mode():
                self.plain_text.clear()
            else:
                self.rich_text.clear()
        else:
            func = cb[0]
            args = cb[1:]
            func(*args)
            if get_meth_class_inst(func) is self.rich_text:
                self.switch_to_rich_text()
            else:
                self.switch_to_plain_text()

    #------ Public API (related to rich/plain text widgets) --------------------
    @property
    def find_widget(self):
        if self.plain_text.isVisible():
            return self.plain_text.find_widget
        else:
            return self.rich_text.find_widget

    def set_rich_text_font(self, font):
        """Set rich text mode font"""
        self.rich_text.set_font(font, fixed_font=self.get_plugin_font())

    def set_plain_text_font(self, font, color_scheme=None):
        """Set plain text mode font"""
        self.plain_text.set_font(font, color_scheme=color_scheme)

    def set_plain_text_color_scheme(self, color_scheme):
        """Set plain text mode color scheme"""
        self.plain_text.set_color_scheme(color_scheme)

    @Slot(bool)
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.plain_text.editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)

    def toggle_math_mode(self, checked):
        """Toggle math mode"""
        self.set_option('math', checked)

    def is_plain_text_mode(self):
        """Return True if plain text mode is active"""
        return self.plain_text.isVisible()

    def is_rich_text_mode(self):
        """Return True if rich text mode is active"""
        return self.rich_text.isVisible()

    def switch_to_plain_text(self):
        """Switch to plain text mode"""
        self.rich_help = False
        self.plain_text.show()
        self.rich_text.hide()
        self.plain_text_action.setChecked(True)

    def switch_to_rich_text(self):
        """Switch to rich text mode"""
        self.rich_help = True
        self.plain_text.hide()
        self.rich_text.show()
        self.rich_text_action.setChecked(True)
        self.show_source_action.setChecked(False)

    def set_plain_text(self, text, is_code):
        """Set plain text docs"""

        # text is coming from utils.dochelpers.getdoc
        if type(text) is dict:
            name = text['name']
            if name:
                rst_title = ''.join(['='*len(name), '\n', name, '\n',
                                    '='*len(name), '\n\n'])
            else:
                rst_title = ''

            if text['argspec']:
                definition = ''.join(['Definition: ', name, text['argspec'],
                                      '\n'])
            else:
                definition = ''

            if text['note']:
                note = ''.join(['Type: ', text['note'], '\n\n----\n\n'])
            else:
                note = ''

            full_text = ''.join([rst_title, definition, note,
                                 text['docstring']])
        else:
            full_text = text

        self.plain_text.set_text(full_text, is_code)
        self.save_text([self.plain_text.set_text, full_text, is_code])

    def set_rich_text_html(self, html_text, base_url):
        """Set rich text"""
        self.rich_text.set_html(html_text, base_url)
        self.save_text([self.rich_text.set_html, html_text, base_url])

    def show_intro_message(self):
        intro_message = _("Here you can get help of any object by pressing "
                          "%s in front of it, either on the Editor or the "
                          "Console.%s"
                          "Help can also be shown automatically after writing "
                          "a left parenthesis next to an object. You can "
                          "activate this behavior in %s.")
        prefs = _("Preferences > Help")
        if sys.platform == 'darwin':
            shortcut = "Cmd+I"
        else:
            shortcut = "Ctrl+I"

        if self.is_rich_text_mode():
            title = _("Usage")
            tutorial_message = _("New to Spyder? Read our")
            tutorial = _("tutorial")
            intro_message = intro_message % ("<b>"+shortcut+"</b>", "<br><br>",
                                             "<i>"+prefs+"</i>")
            self.set_rich_text_html(usage(title, intro_message,
                                          tutorial_message, tutorial),
                                    QUrl.fromLocalFile(CSS_PATH))
        else:
            install_sphinx = "\n\n%s" % _("Please consider installing Sphinx "
                                          "to get documentation rendered in "
                                          "rich text.")
            intro_message = intro_message % (shortcut, "\n\n", prefs)
            intro_message += install_sphinx
            self.set_plain_text(intro_message, is_code=False)

    def show_rich_text(self, text, collapse=False, img_path=''):
        """Show text in rich mode"""
        self.visibility_changed(True)
        self.raise_()
        self.switch_to_rich_text()
        context = generate_context(collapse=collapse, img_path=img_path)
        self.render_sphinx_doc(text, context)

    def show_plain_text(self, text):
        """Show text in plain mode"""
        self.visibility_changed(True)
        self.raise_()
        self.switch_to_plain_text()
        self.set_plain_text(text, is_code=False)

    @Slot()
    def show_tutorial(self):
        tutorial_path = get_module_source_path('spyder.utils.help')
        tutorial = osp.join(tutorial_path, 'tutorial.rst')
        text = open(tutorial).read()
        self.show_rich_text(text, collapse=True)

    def handle_link_clicks(self, url):
        url = to_text_string(url.toString())
        if url == "spy://tutorial":
            self.show_tutorial()
        elif url.startswith('http'):
            programs.start_file(url)
        else:
            self.rich_text.webview.load(QUrl(url))

    #------ Public API ---------------------------------------------------------
    def force_refresh(self):
        if self.source_is_console():
            self.set_object_text(None, force_refresh=True)
        elif self._last_editor_doc is not None:
            self.set_editor_doc(self._last_editor_doc, force_refresh=True)

    def set_object_text(self, text, force_refresh=False, ignore_unknown=False):
        """Set object analyzed by Help"""
        if (self.locked and not force_refresh):
            return
        self.switch_to_console_source()

        add_to_combo = True
        if text is None:
            text = to_text_string(self.combo.currentText())
            add_to_combo = False

        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return

        if add_to_combo:
            self.combo.add_text(text)
        if found:
            self.save_history()

        if self.dockwidget is not None:
            self.dockwidget.blockSignals(True)
        self.__eventually_raise_help(text, force=force_refresh)
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(False)

    def set_editor_doc(self, doc, force_refresh=False):
        """
        Use the help plugin to show docstring dictionary computed
        with introspection plugin from the Editor plugin
        """
        if (self.locked and not force_refresh):
            return
        self.switch_to_editor_source()
        self._last_editor_doc = doc
        self.object_edit.setText(doc['obj_text'])

        if self.rich_help:
            self.render_sphinx_doc(doc)
        else:
            self.set_plain_text(doc, is_code=False)

        if self.dockwidget is not None:
            self.dockwidget.blockSignals(True)
        self.__eventually_raise_help(doc['docstring'], force=force_refresh)
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(False)

    def __eventually_raise_help(self, text, force=False):
        index = self.source_combo.currentIndex()
        if hasattr(self.main, 'tabifiedDockWidgets'):
            # 'QMainWindow.tabifiedDockWidgets' was introduced in PyQt 4.5
            if self.dockwidget and (force or self.dockwidget.isVisible()) \
               and not self.ismaximized \
               and (force or text != self._last_texts[index]):
                dockwidgets = self.main.tabifiedDockWidgets(self.dockwidget)
                if self.main.console.dockwidget not in dockwidgets and \
                   (hasattr(self.main, 'ipyconsole') and \
                    self.main.ipyconsole.dockwidget not in dockwidgets):
                    self.dockwidget.show()
                    self.dockwidget.raise_()
        self._last_texts[index] = text

    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n', '')
                       for line in open(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history

    def save_history(self):
        """Save history to a text file in user home directory"""
        open(self.LOG_PATH, 'w').write("\n".join( \
                [to_text_string(self.combo.itemText(index))
                 for index in range(self.combo.count())] ))

    @Slot(bool)
    def toggle_plain_text(self, checked):
        """Toggle plain text docstring"""
        if checked:
            self.docstring = checked
            self.switch_to_plain_text()
            self.force_refresh()
        self.set_option('rich_mode', not checked)

    @Slot(bool)
    def toggle_show_source(self, checked):
        """Toggle show source code"""
        if checked:
            self.switch_to_plain_text()
        self.docstring = not checked
        self.force_refresh()
        self.set_option('rich_mode', not checked)

    @Slot(bool)
    def toggle_rich_text(self, checked):
        """Toggle between sphinxified docstrings or plain ones"""
        if checked:
            self.docstring = not checked
            self.switch_to_rich_text()
        self.set_option('rich_mode', checked)

    @Slot(bool)
    def toggle_auto_import(self, checked):
        """Toggle automatic import feature"""
        self.combo.validate_current_text()
        self.set_option('automatic_import', checked)
        self.force_refresh()

    @Slot()
    def toggle_locked(self):
        """
        Toggle locked state
        locked = disable link with Console
        """
        self.locked = not self.locked
        self._update_lock_icon()

    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = ima.icon('lock') if self.locked else ima.icon('lock_open')
        self.locked_button.setIcon(icon)
        tip = _("Unlock") if self.locked else _("Lock")
        self.locked_button.setToolTip(tip)

    def set_shell(self, shell):
        """Bind to shell"""
        self.shell = shell

    def get_shell(self):
        """
        Return shell which is currently bound to Help,
        or another running shell if it has been terminated
        """
        if (not hasattr(self.shell, 'get_doc') or
                (hasattr(self.shell, 'is_running') and
                 not self.shell.is_running())):
            self.shell = None
            if self.main.ipyconsole is not None:
                shell = self.main.ipyconsole.get_current_shellwidget()
                if shell is not None and shell.kernel_client is not None:
                    self.shell = shell
            if self.shell is None:
                self.shell = self.internal_shell
        return self.shell

    def render_sphinx_doc(self, doc, context=None):
        """Transform doc string dictionary to HTML and show it"""
        # Math rendering option could have changed
        fname = self.parent().parent().editor.get_current_filename()
        dname = osp.dirname(fname)
        self._sphinx_thread.render(doc, context, self.get_option('math'),
                                   dname)

    def _on_sphinx_thread_html_ready(self, html_text):
        """Set our sphinx documentation based on thread result"""
        self._sphinx_thread.wait()
        self.set_rich_text_html(html_text, QUrl.fromLocalFile(CSS_PATH))

    def _on_sphinx_thread_error_msg(self, error_msg):
        """ Display error message on Sphinx rich text failure"""
        self._sphinx_thread.wait()
        self.plain_text_action.setChecked(True)
        sphinx_ver = programs.get_module_version('sphinx')
        QMessageBox.critical(self,
                    _('Help'),
                    _("The following error occured when calling "
                      "<b>Sphinx %s</b>. <br>Incompatible Sphinx "
                      "version or doc string decoding failed."
                      "<br><br>Error message:<br>%s"
                      ) % (sphinx_ver, error_msg))

    def show_help(self, obj_text, ignore_unknown=False):
        """Show help"""
        shell = self.get_shell()
        if shell is None:
            return
        obj_text = to_text_string(obj_text)

        if not shell.is_defined(obj_text):
            if self.get_option('automatic_import') and \
               self.internal_shell.is_defined(obj_text, force_import=True):
                shell = self.internal_shell
            else:
                shell = None
                doc = None
                source_text = None

        if shell is not None:
            doc = shell.get_doc(obj_text)
            source_text = shell.get_source(obj_text)

        is_code = False

        if self.rich_help:
            self.render_sphinx_doc(doc)
            return doc is not None
        elif self.docstring:
            hlp_text = doc
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    hlp_text = self.no_doc_string
                    if ignore_unknown:
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
