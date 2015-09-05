# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Object Inspector Plugin"""

<<<<<<< HEAD
=======
from spyderlib.qt import PYQT5
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
from spyderlib.qt.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
                                QMenu, QToolButton, QGroupBox, QFontComboBox,
                                QActionGroup, QFontDialog, QWidget, QComboBox,
                                QLineEdit, QMessageBox)
<<<<<<< HEAD
from spyderlib.qt.QtCore import SIGNAL, QUrl, QThread
from spyderlib.qt.QtWebKit import QWebPage
=======
from spyderlib.qt.QtCore import Signal, Slot, QUrl, QThread
from spyderlib.qt.QtWebKit import QWebPage
import spyderlib.utils.icon_manager as ima
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

import re
import os.path as osp
import socket
import sys

# Local imports
from spyderlib import dependencies
<<<<<<< HEAD
from spyderlib.baseconfig import get_conf_path, get_module_source_path, _
from spyderlib.ipythonconfig import IPYTHON_QT_INSTALLED
from spyderlib.start_app import CONF
#from spyderlib.config import CONF
from spyderlib.guiconfig import get_color_scheme, get_font, set_font
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import (get_icon, create_toolbutton,
                                       add_actions, create_action)
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.widgets.sourcecode import codeeditor
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.browser import WebView
=======
from spyderlib.config.base import get_conf_path, get_module_source_path, _
from spyderlib.config.ipython import IPYTHON_QT_INSTALLED
from spyderlib.config.main import CONF
from spyderlib.config.gui import get_color_scheme, get_font, set_font
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import (create_toolbutton, add_actions,
                                       create_action)
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.widgets.sourcecode import codeeditor
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.browser import FrameWebView
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
from spyderlib.widgets.externalshell.pythonshell import ExtPythonShellWidget
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage
from spyderlib.py3compat import to_text_string, get_meth_class_inst

#XXX: Hardcoded dependency on optional IPython plugin component
#     that requires the hack to make this work without IPython
if IPYTHON_QT_INSTALLED:
    from spyderlib.widgets.ipython import IPythonControlWidget
else:
    IPythonControlWidget = None  # analysis:ignore

# Check if we can import Sphinx to activate rich text mode
try:
    from spyderlib.utils.inspector.sphinxify import (CSS_PATH, sphinxify,
                                                     warning, generate_context,
                                                     usage)
    sphinx_version = programs.get_module_version('sphinx')
except (ImportError, TypeError):
    sphinxify = sphinx_version = None  # analysis:ignore

# To add sphinx dependency to the Dependencies dialog
SPHINX_REQVER = '>=0.6.6'
dependencies.add("sphinx", _("Rich text help on the Object Inspector"),
                 required_version=SPHINX_REQVER)


class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
<<<<<<< HEAD
=======
    # Signals
    valid = Signal(bool)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __init__(self, parent):
        EditableComboBox.__init__(self, parent)
        self.object_inspector = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: '', False: ''}
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if not self.object_inspector.source_is_console():
            return True
        if qstr is None:
            qstr = self.currentText()
        if not re.search('^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        objtxt = to_text_string(qstr)
        if self.object_inspector.get_option('automatic_import'):
            shell = self.object_inspector.internal_shell
            if shell is not None:
                return shell.is_defined(objtxt, force_import=True)
        shell = self.object_inspector.get_shell()
        if shell is not None:
            try:
                return shell.is_defined(objtxt)
            except socket.error:
                shell = self.object_inspector.get_shell()
                try:
                    return shell.is_defined(objtxt)
                except socket.error:
                    # Well... too bad!
                    pass
<<<<<<< HEAD
        
    def validate_current_text(self):
        self.validate(self.currentText())
    
=======

    def validate_current_text(self):
        self.validate(self.currentText())

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def validate(self, qstr, editing=True):
        """Reimplemented to avoid formatting actions"""
        valid = self.is_valid(qstr)
        if self.hasFocus() and valid is not None:
            if editing:
                # Combo box text is being modified: invalidate the entry
                self.show_tip(self.tips[valid])
<<<<<<< HEAD
                self.emit(SIGNAL('valid(bool)'), False)
=======
                self.valid.emit(False)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                else:
<<<<<<< HEAD
                    self.emit(SIGNAL('valid(bool)'), False)
=======
                    self.valid.emit(False)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        else:
            self.set_default_style()


class ObjectInspectorConfigPage(PluginConfigPage):
    def setup_page(self):
<<<<<<< HEAD
        # Fonts group        
=======
        # Fonts group
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        plain_text_font_group = self.create_fontgroup(option=None,
                                    text=_("Plain text font style"),
                                    fontfilters=QFontComboBox.MonospacedFonts)
        rich_text_font_group = self.create_fontgroup(option='rich_text',
                                text=_("Rich text font style"))
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Connections group
        connections_group = QGroupBox(_("Automatic connections"))
        connections_label = QLabel(_("The Object Inspector can automatically "
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
        python_box = self.create_checkbox(_("Python Console"),
                                          'connect/python_console')
        ipython_box = self.create_checkbox(_("IPython Console"),
                                           'connect/ipython_console')
        ipython_box.setEnabled(IPYTHON_QT_INSTALLED)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        connections_layout = QVBoxLayout()
        connections_layout.addWidget(connections_label)
        connections_layout.addWidget(editor_box)
        connections_layout.addWidget(python_box)
        connections_layout.addWidget(ipython_box)
        connections_group.setLayout(connections_layout)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Features group
        features_group = QGroupBox(_("Additional features"))
        math_box = self.create_checkbox(_("Render mathematical equations"),
                                        'math')
        req_sphinx = sphinx_version is not None and \
                     programs.is_module_installed('sphinx', '>=1.1')
        math_box.setEnabled(req_sphinx)
        if not req_sphinx:
            sphinx_tip = _("This feature requires Sphinx 1.1 or superior.")
            if sphinx_version is not None:
                sphinx_tip += "\n" + _("Sphinx %s is currently installed."
                                       ) % sphinx_version
            math_box.setToolTip(sphinx_tip)
<<<<<<< HEAD
        
        features_layout = QVBoxLayout()
        features_layout.addWidget(math_box)
        features_group.setLayout(features_layout)
        
=======

        features_layout = QVBoxLayout()
        features_layout.addWidget(math_box)
        features_group.setLayout(features_layout)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Source code group
        sourcecode_group = QGroupBox(_("Source code"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')
        names = CONF.get('color_schemes', 'names')
        choices = list(zip(names, names))
        cs_combo = self.create_combobox(_("Syntax color scheme: "),
                                        choices, 'color_scheme_name')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(cs_combo)
        sourcecode_group.setLayout(sourcecode_layout)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Final layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(rich_text_font_group)
        vlayout.addWidget(plain_text_font_group)
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
<<<<<<< HEAD
        
        self.webview = WebView(self)
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()
        
=======

        self.webview = FrameWebView(self)
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview)
        self.find_widget.hide()

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webview)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
<<<<<<< HEAD
        
    def set_font(self, font, fixed_font=None):
        """Set font"""
        self.webview.set_font(font, fixed_font=fixed_font)
        
    def set_html(self, html_text, base_url):
        """Set html text"""
        self.webview.setHtml(html_text, base_url)
        
    def clear(self):
        self.set_html('', self.webview.url())
        
        
=======

    def set_font(self, font, fixed_font=None):
        """Set font"""
        self.webview.set_font(font, fixed_font=fixed_font)

    def set_html(self, html_text, base_url):
        """Set html text"""
        self.webview.setHtml(html_text, base_url)

    def clear(self):
        self.set_html('', self.webview.url())


>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
class PlainText(QWidget):
    """
    Read-only editor widget with find dialog
    """
<<<<<<< HEAD
=======
    # Signals
    focus_changed = Signal()

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None

        # Read-only editor
        self.editor = codeeditor.CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 scrollflagarea=False, edge_line=False)
<<<<<<< HEAD
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)
        
=======
        self.editor.focus_changed.connect(lambda: self.focus_changed.emit())
        self.editor.setReadOnly(True)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
<<<<<<< HEAD
        
    def set_font(self, font, color_scheme=None):
        """Set font"""
        self.editor.set_font(font, color_scheme=color_scheme)
        
    def set_color_scheme(self, color_scheme):
        """Set color scheme"""
        self.editor.set_color_scheme(color_scheme)
        
=======

    def set_font(self, font, color_scheme=None):
        """Set font"""
        self.editor.set_font(font, color_scheme=color_scheme)

    def set_color_scheme(self, color_scheme):
        """Set color scheme"""
        self.editor.set_color_scheme(color_scheme)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_text(self, text, is_code):
        self.editor.set_highlight_current_line(is_code)
        self.editor.set_occurence_highlighting(is_code)
        if is_code:
            self.editor.set_language('py')
        else:
            self.editor.set_language(None)
        self.editor.set_text(text)
        self.editor.set_cursor_position('sof')
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def clear(self):
        self.editor.clear()


class SphinxThread(QThread):
    """
    A worker thread for handling rich text rendering.
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    Parameters
    ----------
    doc : str or dict
        A string containing a raw rst text or a dict containing
        the doc string components to be rendered.
        See spyderlib.utils.dochelpers.getdoc for description.
    context : dict
        A dict containing the substitution variables for the
        layout template
    html_text_no_doc : unicode
        Text to be rendered if doc string cannot be extracted.
    math_option : bool
        Use LaTeX math rendering.
<<<<<<< HEAD
        
    """
=======

    """
    # Signals
    error_msg = Signal(str)
    html_ready = Signal(str)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __init__(self, html_text_no_doc=''):
        super(SphinxThread, self).__init__()
        self.doc = None
        self.context = None
        self.html_text_no_doc = html_text_no_doc
        self.math_option = False
<<<<<<< HEAD
        
    def render(self, doc, context=None, math_option=False):
=======

    def render(self, doc, context=None, math_option=False, img_path=''):
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """Start thread to render a given documentation"""
        # If the thread is already running wait for it to finish before
        # starting it again.
        if self.wait():
            self.doc = doc
            self.context = context
            self.math_option = math_option
<<<<<<< HEAD
=======
            self.img_path = img_path
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
                                               math=self.math_option)
=======
                                               math=self.math_option,
                                               img_path=self.img_path)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                    html_text = sphinxify(doc['docstring'], context)
                    if doc['docstring'] == '':
                        html_text += '<div class="hr"></div>'
                        html_text += self.html_text_no_doc

                except Exception as error:
<<<<<<< HEAD
                    self.emit(SIGNAL('error_msg(QString)'),
                              to_text_string(error))
=======
                    self.error_msg.emit(to_text_string(error))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                    return
            elif self.context is not None:
                try:
                    html_text = sphinxify(doc, self.context)
                except Exception as error:
<<<<<<< HEAD
                    self.emit(SIGNAL('error_msg(QString)'),
                              to_text_string(error))
                    return
        self.emit(SIGNAL('html_ready(QString)'), html_text)
=======
                    self.error_msg.emit(to_text_string(error))
                    return
        self.html_ready.emit(html_text)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f


class ObjectInspector(SpyderPluginWidget):
    """
    Docstrings viewer widget
    """
    CONF_SECTION = 'inspector'
    CONFIGWIDGET_CLASS = ObjectInspectorConfigPage
    LOG_PATH = get_conf_path(CONF_SECTION)
<<<<<<< HEAD
    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)
        
=======
    focus_changed = Signal()

    def __init__(self, parent):
        if PYQT5:
            SpyderPluginWidget.__init__(self, parent, main = parent)
        else:
            SpyderPluginWidget.__init__(self, parent)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        self.internal_shell = None

        # Initialize plugin
        self.initialize_plugin()

        self.no_doc_string = _("No further documentation available")
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        self._last_console_cb = None
        self._last_editor_cb = None

        self.set_default_color_scheme()

        self.plain_text = PlainText(self)
        self.rich_text = RichText(self)
<<<<<<< HEAD
        
        color_scheme = get_color_scheme(self.get_option('color_scheme_name'))
        self.set_plain_text_font(self.get_plugin_font(), color_scheme)
        self.plain_text.editor.toggle_wrap_mode(self.get_option('wrap'))
        
        # Add entries to read-only editor context-menu
        font_action = create_action(self, _("&Font..."), None,
                                    'font.png', _("Set font style"),
=======

        color_scheme = get_color_scheme(self.get_option('color_scheme_name'))
        self.set_plain_text_font(self.get_plugin_font(), color_scheme)
        self.plain_text.editor.toggle_wrap_mode(self.get_option('wrap'))

        # Add entries to read-only editor context-menu
        font_action = create_action(self, _("&Font..."), None,
                                    ima.icon('font'), _("Set font style"),
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                                    triggered=self.change_font)
        self.wrap_action = create_action(self, _("Wrap lines"),
                                         toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked(self.get_option('wrap'))
        self.plain_text.editor.readonly_menu.addSeparator()
        add_actions(self.plain_text.editor.readonly_menu,
                    (font_action, self.wrap_action))

        self.set_rich_text_font(self.get_plugin_font('rich_text'))
<<<<<<< HEAD
        
        self.shell = None
        
        self.external_console = None
        
=======

        self.shell = None

        self.external_console = None

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # locked = disable link with Console
        self.locked = False
        self._last_texts = [None, None]
        self._last_editor_doc = None
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.connect(self.source_combo, SIGNAL('currentIndexChanged(int)'),
                     self.source_changed)
        if (not programs.is_module_installed('rope') and 
=======
        self.source_combo.currentIndexChanged.connect(self.source_changed)
        if (not programs.is_module_installed('rope') and
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.connect(self.combo, SIGNAL("valid(bool)"),
                     lambda valid: self.force_refresh())
        
=======
        self.combo.valid.connect(lambda valid: self.force_refresh())

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Plain text docstring option
        self.docstring = True
        self.rich_help = sphinxify is not None \
                         and self.get_option('rich_mode', True)
        self.plain_text_action = create_action(self, _("Plain Text"),
                                               toggled=self.toggle_plain_text)
<<<<<<< HEAD
        
        # Source code option
        self.show_source_action = create_action(self, _("Show Source"),
                                                toggled=self.toggle_show_source)
        
        # Rich text option
        self.rich_text_action = create_action(self, _("Rich Text"),
                                         toggled=self.toggle_rich_text)
                        
=======

        # Source code option
        self.show_source_action = create_action(self, _("Show Source"),
                                                toggled=self.toggle_show_source)

        # Rich text option
        self.rich_text_action = create_action(self, _("Rich Text"),
                                         toggled=self.toggle_rich_text)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Add the help actions to an exclusive QActionGroup
        help_actions = QActionGroup(self)
        help_actions.setExclusive(True)
        help_actions.addAction(self.plain_text_action)
        help_actions.addAction(self.rich_text_action)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Automatic import option
        self.auto_import_action = create_action(self, _("Automatic import"),
                                                toggled=self.toggle_auto_import)
        auto_import_state = self.get_option('automatic_import')
        self.auto_import_action.setChecked(auto_import_state)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Lock checkbox
        self.locked_button = create_toolbutton(self,
                                               triggered=self.toggle_locked)
        layout_edit.addWidget(self.locked_button)
        self._update_lock_icon()
<<<<<<< HEAD
        
        # Option menu
        options_button = create_toolbutton(self, text=_("Options"),
                                           icon=get_icon('tooloptions.png'))
=======

        # Option menu
        options_button = create_toolbutton(self, text=_('Options'),
                                           icon=ima.icon('tooloptions'))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, [self.rich_text_action, self.plain_text_action,
                           self.show_source_action, None,
                           self.auto_import_action])
        options_button.setMenu(menu)
        layout_edit.addWidget(options_button)

        if self.rich_help:
            self.switch_to_rich_text()
        else:
            self.switch_to_plain_text()
        self.plain_text_action.setChecked(not self.rich_help)
        self.rich_text_action.setChecked(self.rich_help)
        self.rich_text_action.setEnabled(sphinxify is not None)
        self.source_changed()

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_edit)
        layout.addWidget(self.plain_text)
        layout.addWidget(self.rich_text)
        self.setLayout(layout)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Add worker thread for handling rich text rendering
        if sphinxify is None:
            self._sphinx_thread = None
        else:
            self._sphinx_thread = SphinxThread(
                                  html_text_no_doc=warning(self.no_doc_string))
<<<<<<< HEAD
            self.connect(self._sphinx_thread, SIGNAL('html_ready(QString)'), 
                         self._on_sphinx_thread_html_ready)
            self.connect(self._sphinx_thread, SIGNAL('error_msg(QString)'),
                         self._on_sphinx_thread_error_msg)
        
=======
            self._sphinx_thread.html_ready.connect(
                                             self._on_sphinx_thread_html_ready)
            self._sphinx_thread.error_msg.connect(
                                              self._on_sphinx_thread_error_msg)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Render internal links
        view = self.rich_text.webview
        view.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        view.linkClicked.connect(self.handle_link_clicks)

        self._starting_up = True
<<<<<<< HEAD
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _('Object inspector')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('inspector.png')
    
=======

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('Object inspector')

    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('inspector')

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.combo.lineEdit().selectAll()
        return self.combo
<<<<<<< HEAD
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
        self.main.console.set_inspector(self)
        self.internal_shell = self.main.console.shell
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
=======

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
        self.main.console.set_inspector(self)
        self.internal_shell = self.main.console.shell

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
            if sphinxify is not None:
                self.switch_to_rich_text()
            self.show_intro_message()

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = get_color_scheme(self.get_option(color_scheme_n))
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        connect_n = 'connect_to_oi'
        rich_font_n = 'rich_text'
        rich_font_o = self.get_plugin_font('rich_text')
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        math_n = 'math'
        math_o = self.get_option(math_n)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if font_n in options:
            scs = color_scheme_o if color_scheme_n in options else None
            self.set_plain_text_font(font_o, color_scheme=scs)
        if rich_font_n in options:
            self.set_rich_text_font(rich_font_o)
        elif color_scheme_n in options:
            self.set_plain_text_color_scheme(color_scheme_o)
        if wrap_n in options:
            self.toggle_wrap_mode(wrap_o)
        if math_n in options:
            self.toggle_math_mode(math_o)

        # To make auto-connection changes take place instantly
        self.main.editor.apply_plugin_settings(options=[connect_n])
        self.main.extconsole.apply_plugin_settings(options=[connect_n])
        if self.main.ipyconsole is not None:
            self.main.ipyconsole.apply_plugin_settings(options=[connect_n])
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    #------ Public API (related to inspector's source) -------------------------
    def source_is_console(self):
        """Return True if source is Console"""
        return self.source_combo.currentIndex() == 0
<<<<<<< HEAD
    
    def switch_to_editor_source(self):
        self.source_combo.setCurrentIndex(1)
        
    def switch_to_console_source(self):
        self.source_combo.setCurrentIndex(0)
        
=======

    def switch_to_editor_source(self):
        self.source_combo.setCurrentIndex(1)

    def switch_to_console_source(self):
        self.source_combo.setCurrentIndex(0)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
            
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def save_text(self, callback):
        if self.source_is_console():
            self._last_console_cb = callback
        else:
            self._last_editor_cb = callback
<<<<<<< HEAD
            
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    #------ Public API (related to rich/plain text widgets) --------------------
    @property
    def find_widget(self):
        if self.plain_text.isVisible():
            return self.plain_text.find_widget
        else:
            return self.rich_text.find_widget
<<<<<<< HEAD
    
    def set_rich_text_font(self, font):
        """Set rich text mode font"""
        self.rich_text.set_font(font, fixed_font=self.get_plugin_font())
        
=======

    def set_rich_text_font(self, font):
        """Set rich text mode font"""
        self.rich_text.set_font(font, fixed_font=self.get_plugin_font())

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_plain_text_font(self, font, color_scheme=None):
        """Set plain text mode font"""
        self.plain_text.set_font(font, color_scheme=color_scheme)

    def set_plain_text_color_scheme(self, color_scheme):
        """Set plain text mode color scheme"""
        self.plain_text.set_color_scheme(color_scheme)
<<<<<<< HEAD
        
=======

    @Slot()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.CONF_SECTION), self,
                                      _("Select a new font"))
        if valid:
            self.set_plain_text_font(font)
            set_font(font, self.CONF_SECTION)
<<<<<<< HEAD
            
=======

    @Slot(bool)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.plain_text.editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)
<<<<<<< HEAD
    
    def toggle_math_mode(self, checked):
        """Toggle math mode"""
        self.set_option('math', checked)
    
=======

    def toggle_math_mode(self, checked):
        """Toggle math mode"""
        self.set_option('math', checked)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def switch_to_rich_text(self):
        """Switch to rich text mode"""
        self.rich_help = True
        self.plain_text.hide()
        self.rich_text.show()
        self.rich_text_action.setChecked(True)
        self.show_source_action.setChecked(False)
<<<<<<< HEAD
            
    def set_plain_text(self, text, is_code):
        """Set plain text docs"""
        
=======

    def set_plain_text(self, text, is_code):
        """Set plain text docs"""

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # text is coming from utils.dochelpers.getdoc
        if type(text) is dict:
            name = text['name']
            if name:
                rst_title = ''.join(['='*len(name), '\n', name, '\n',
                                    '='*len(name), '\n\n'])
            else:
                rst_title = ''
<<<<<<< HEAD
            
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            if text['argspec']:
                definition = ''.join(['Definition: ', name, text['argspec'],
                                      '\n'])
            else:
                definition = ''
<<<<<<< HEAD
            
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            if text['note']:
                note = ''.join(['Type: ', text['note'], '\n\n----\n\n'])
            else:
                note = ''

            full_text = ''.join([rst_title, definition, note,
                                 text['docstring']])
        else:
            full_text = text
<<<<<<< HEAD
        
        self.plain_text.set_text(full_text, is_code)
        self.save_text([self.plain_text.set_text, full_text, is_code])
        
=======

        self.plain_text.set_text(full_text, is_code)
        self.save_text([self.plain_text.set_text, full_text, is_code])

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_rich_text_html(self, html_text, base_url):
        """Set rich text"""
        self.rich_text.set_html(html_text, base_url)
        self.save_text([self.rich_text.set_html, html_text, base_url])
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def show_intro_message(self):
        intro_message = _("Here you can get help of any object by pressing "
                          "%s in front of it, either on the Editor or the "
                          "Console.%s"
                          "Help can also be shown automatically after writing "
                          "a left parenthesis next to an object. You can "
                          "activate this behavior in %s.")
        prefs = _("Preferences > Object Inspector")
<<<<<<< HEAD
=======
        if sys.platform == 'darwin':
            shortcut = "Cmd+I"
        else:
            shortcut = "Ctrl+I"

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if self.is_rich_text_mode():
            title = _("Usage")
            tutorial_message = _("New to Spyder? Read our")
            tutorial = _("tutorial")
<<<<<<< HEAD
            intro_message = intro_message % ("<b>Ctrl+I</b>", "<br><br>",
=======
            intro_message = intro_message % ("<b>"+shortcut+"</b>", "<br><br>",
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                                             "<i>"+prefs+"</i>")
            self.set_rich_text_html(usage(title, intro_message,
                                          tutorial_message, tutorial),
                                    QUrl.fromLocalFile(CSS_PATH))
        else:
            install_sphinx = "\n\n%s" % _("Please consider installing Sphinx "
                                          "to get documentation rendered in "
                                          "rich text.")
<<<<<<< HEAD
            intro_message = intro_message % ("Ctrl+I", "\n\n", prefs)
            intro_message += install_sphinx
            self.set_plain_text(intro_message, is_code=False)
    
=======
            intro_message = intro_message % (shortcut, "\n\n", prefs)
            intro_message += install_sphinx
            self.set_plain_text(intro_message, is_code=False)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def show_rich_text(self, text, collapse=False, img_path=''):
        """Show text in rich mode"""
        self.visibility_changed(True)
        self.raise_()
        self.switch_to_rich_text()
        context = generate_context(collapse=collapse, img_path=img_path)
        self.render_sphinx_doc(text, context)
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def show_plain_text(self, text):
        """Show text in plain mode"""
        self.visibility_changed(True)
        self.raise_()
        self.switch_to_plain_text()
        self.set_plain_text(text, is_code=False)
<<<<<<< HEAD
    
=======

    @Slot()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def show_tutorial(self):
        tutorial_path = get_module_source_path('spyderlib.utils.inspector')
        img_path = osp.join(tutorial_path, 'static', 'images')
        tutorial = osp.join(tutorial_path, 'tutorial.rst')
        text = open(tutorial).read()
        if sphinxify is not None:
            self.show_rich_text(text, collapse=True, img_path=img_path)
        else:
            self.show_plain_text(text)

    def handle_link_clicks(self, url):
        url = to_text_string(url.toString())
        if url == "spy://tutorial":
            self.show_tutorial()
        elif url.startswith('http'):
            programs.start_file(url)
        else:
            self.rich_text.webview.load(QUrl(url))
<<<<<<< HEAD
        
    #------ Public API ---------------------------------------------------------
    def set_external_console(self, external_console):
        self.external_console = external_console
    
=======

    #------ Public API ---------------------------------------------------------
    def set_external_console(self, external_console):
        self.external_console = external_console

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def force_refresh(self):
        if self.source_is_console():
            self.set_object_text(None, force_refresh=True)
        elif self._last_editor_doc is not None:
            self.set_editor_doc(self._last_editor_doc, force_refresh=True)
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_object_text(self, text, force_refresh=False, ignore_unknown=False):
        """Set object analyzed by Object Inspector"""
        if (self.locked and not force_refresh):
            return
        self.switch_to_console_source()

        add_to_combo = True
        if text is None:
            text = to_text_string(self.combo.currentText())
            add_to_combo = False
<<<<<<< HEAD
            
        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return
        
=======

        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if add_to_combo:
            self.combo.add_text(text)
        if found:
            self.save_history()
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(True)
        self.__eventually_raise_inspector(text, force=force_refresh)
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(False)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_editor_doc(self, doc, force_refresh=False):
        """
        Use the object inspector to show docstring dictionary computed
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
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(True)
        self.__eventually_raise_inspector(doc['docstring'],
                                          force=force_refresh)
        if self.dockwidget is not None:
            self.dockwidget.blockSignals(False)
<<<<<<< HEAD
            
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __eventually_raise_inspector(self, text, force=False):
        index = self.source_combo.currentIndex()
        if hasattr(self.main, 'tabifiedDockWidgets'):
            # 'QMainWindow.tabifiedDockWidgets' was introduced in PyQt 4.5
            if self.dockwidget and (force or self.dockwidget.isVisible()) \
               and not self.ismaximized \
               and (force or text != self._last_texts[index]):
                dockwidgets = self.main.tabifiedDockWidgets(self.dockwidget)
                if self.main.console.dockwidget not in dockwidgets and \
                   (hasattr(self.main, 'extconsole') and \
                    self.main.extconsole.dockwidget not in dockwidgets):
                    self.dockwidget.show()
                    self.dockwidget.raise_()
        self._last_texts[index] = text
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n', '')
                       for line in open(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def save_history(self):
        """Save history to a text file in user home directory"""
        open(self.LOG_PATH, 'w').write("\n".join( \
                [to_text_string(self.combo.itemText(index))
                 for index in range(self.combo.count())] ))
<<<<<<< HEAD
        
=======

    @Slot(bool)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_plain_text(self, checked):
        """Toggle plain text docstring"""
        if checked:
            self.docstring = checked
            self.switch_to_plain_text()
            self.force_refresh()
        self.set_option('rich_mode', not checked)
<<<<<<< HEAD
        
=======

    @Slot(bool)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_show_source(self, checked):
        """Toggle show source code"""
        if checked:
            self.switch_to_plain_text()
        self.docstring = not checked
        self.force_refresh()
        self.set_option('rich_mode', not checked)
<<<<<<< HEAD
        
=======

    @Slot(bool)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_rich_text(self, checked):
        """Toggle between sphinxified docstrings or plain ones"""
        if checked:
            self.docstring = not checked
            self.switch_to_rich_text()
        self.set_option('rich_mode', checked)
<<<<<<< HEAD
        
=======

    @Slot(bool)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_auto_import(self, checked):
        """Toggle automatic import feature"""
        self.combo.validate_current_text()
        self.set_option('automatic_import', checked)
        self.force_refresh()
<<<<<<< HEAD
        
=======

    @Slot()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def toggle_locked(self):
        """
        Toggle locked state
        locked = disable link with Console
        """
        self.locked = not self.locked
        self._update_lock_icon()
<<<<<<< HEAD
        
    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = get_icon("lock.png" if self.locked else "lock_open.png")
        self.locked_button.setIcon(icon)
        tip = _("Unlock") if self.locked else _("Lock")
        self.locked_button.setToolTip(tip)
        
=======

    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = ima.icon('lock') if self.locked else ima.icon('lock_open')
        self.locked_button.setIcon(icon)
        tip = _("Unlock") if self.locked else _("Lock")
        self.locked_button.setToolTip(tip)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def set_shell(self, shell):
        """Bind to shell"""
        if IPythonControlWidget is not None:
            # XXX(anatoli): hack to make Spyder run on systems without IPython
            #               there should be a better way
            if isinstance(shell, IPythonControlWidget):
                # XXX: this ignores passed argument completely
                self.shell = self.external_console.get_current_shell()
        else:
            self.shell = shell
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def get_shell(self):
        """Return shell which is currently bound to object inspector,
        or another running shell if it has been terminated"""
        if not isinstance(self.shell, ExtPythonShellWidget) \
           or not self.shell.externalshell.is_running():
            self.shell = None
            if self.external_console is not None:
                self.shell = self.external_console.get_running_python_shell()
            if self.shell is None:
                self.shell = self.internal_shell
        return self.shell
<<<<<<< HEAD
        
    def render_sphinx_doc(self, doc, context=None):
        """Transform doc string dictionary to HTML and show it"""
        # Math rendering option could have changed
        self._sphinx_thread.render(doc, context, self.get_option('math'))
        
=======

    def render_sphinx_doc(self, doc, context=None):
        """Transform doc string dictionary to HTML and show it"""
        # Math rendering option could have changed
        fname = self.parent().parent().editor.get_current_filename()
        dname = osp.dirname(fname)
        self._sphinx_thread.render(doc, context, self.get_option('math'),
                                   dname)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def _on_sphinx_thread_html_ready(self, html_text):
        """Set our sphinx documentation based on thread result"""
        self._sphinx_thread.wait()
        self.set_rich_text_html(html_text, QUrl.fromLocalFile(CSS_PATH))

    def _on_sphinx_thread_error_msg(self, error_msg):
        """ Display error message on Sphinx rich text failure"""
        self._sphinx_thread.wait()
        self.plain_text_action.setChecked(True)
        QMessageBox.critical(self,
                    _('Object inspector'),
                    _("The following error occured when calling "
                      "<b>Sphinx %s</b>. <br>Incompatible Sphinx "
                      "version or doc string decoding failed."
                      "<br><br>Error message:<br>%s"
                      ) % (sphinx_version, error_msg))

    def show_help(self, obj_text, ignore_unknown=False):
        """Show help"""
        shell = self.get_shell()
        if shell is None:
            return
        obj_text = to_text_string(obj_text)
<<<<<<< HEAD
        
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        if not shell.is_defined(obj_text):
            if self.get_option('automatic_import') and\
               self.internal_shell.is_defined(obj_text, force_import=True):
                shell = self.internal_shell
            else:
                shell = None
                doc = None
                source_text = None
<<<<<<< HEAD
            
        if shell is not None:
            doc = shell.get_doc(obj_text)
            source_text = shell.get_source(obj_text)
            
        is_code = False
        
=======

        if shell is not None:
            doc = shell.get_doc(obj_text)
            source_text = shell.get_source(obj_text)

        is_code = False

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
