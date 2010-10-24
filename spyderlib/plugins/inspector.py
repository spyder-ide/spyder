# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Object Inspector Plugin"""

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QMenu,
                         QToolButton, QGroupBox, QFontComboBox, QActionGroup)
from PyQt4.QtCore import SIGNAL, QUrl, QTimer

import sys, re, os.path as osp, socket

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_conf_path, get_icon, CONF, get_color_scheme
from spyderlib.utils.qthelpers import (create_toolbutton, add_actions,
                                       create_action)
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.plugins import RichAndPlainText, PluginConfigPage
from spyderlib.widgets.externalshell.pythonshell import ExtPythonShellWidget

try:
    from spyderlib.utils.sphinxify import CSS_PATH, sphinxify
    HTML_HEAD = '<html> \
    <head> \
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> \
    <link rel="stylesheet" href="%s/default.css" type="text/css" /> \
    <link rel="stylesheet" href="%s/pygments.css" type="text/css" /> \
    </head> \
    <body>' % (CSS_PATH, CSS_PATH)
    
    HTML_TAIL = '</body> \
    </html>'
except ImportError:
    sphinxify = None


class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
    def __init__(self, parent):
        EditableComboBox.__init__(self, parent)
        self.object_inspector = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr(''), False: self.tr('')}
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        if not re.search('^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        shell = self.object_inspector.shell
        if shell is not None:
            self.object_inspector._check_if_shell_is_running()
            force_import = self.object_inspector.get_option('automatic_import')
            try:
                return shell.is_defined(unicode(qstr),
                                        force_import=force_import)
            except socket.error:
                self.object_inspector._check_if_shell_is_running()
                try:
                    return shell.is_defined(unicode(qstr),
                                            force_import=force_import)
                except socket.error:
                    # Well... too bad!
                    pass
        
    def validate_current_text(self):
        self.validate(self.currentText())

class ObjectInspectorConfigPage(PluginConfigPage):
    def setup_page(self):
        sourcecode_group = QGroupBox(self.tr("Source code"))
        wrap_mode_box = self.create_checkbox(self.tr("Wrap lines"), 'wrap')
        plain_text_font_group = self.create_fontgroup(option=None,
                                    text=self.tr("Plain text font style"),
                                    fontfilters=QFontComboBox.MonospacedFonts)
        rich_text_font_group = self.create_fontgroup(option='rich_text',
                                text=self.tr("Rich text font style"))
        names = CONF.get('color_schemes', 'names')
        choices = zip(names, names)
        cs_combo = self.create_combobox(self.tr("Syntax color scheme: "),
                                        choices, 'color_scheme_name')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(cs_combo)
        sourcecode_group.setLayout(sourcecode_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(rich_text_font_group)
        vlayout.addWidget(plain_text_font_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class ObjectInspector(RichAndPlainText):
    """
    Docstrings viewer widget
    """
    CONF_SECTION = 'inspector'
    CONFIGWIDGET_CLASS = ObjectInspectorConfigPage
    LOG_PATH = get_conf_path('.inspector')
    def __init__(self, parent):
        self.set_default_color_scheme()
        RichAndPlainText.__init__(self, parent)
        self.rich_text.webview.set_font(self.get_plugin_font('rich_text'))
        
        self.shell = None
        
        self.external_console = None
        
        # locked = disable link with Console
        self.locked = False
        self._last_text = None
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.combo = ObjectComboBox(self)
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(self.get_option('max_history_entries'))
        self.combo.addItems( self.load_history() )
        self.connect(self.combo, SIGNAL("valid(bool)"),
                     lambda valid: self.force_refresh())
        
        # Plain text docstring option
        self.docstring = True
        self.rich_help = sphinxify is not None
        self.rich_text.setVisible(self.rich_help)
        self.plain_text.setVisible(not self.rich_help)        
        plain_text_action = create_action(self, self.tr("Plain Text"),
                                          toggled=self.toggle_plain_text)
        plain_text_action.setChecked(not self.rich_help)
        
        # Source code option
        show_source = create_action(self, self.tr("Show Source"),
                                    toggled=self.toggle_show_source)
        
        # Rich text option
        rich_text_action = create_action(self, self.tr("Rich Text"),
                                         toggled=self.toggle_rich_text)
        rich_text_action.setChecked(self.rich_help)
        rich_text_action.setEnabled(sphinxify is not None)
                        
        # Add the help actions to an exclusive QActionGroup
        help_actions = QActionGroup(self)
        help_actions.setExclusive(True)
        help_actions.addAction(plain_text_action)
        help_actions.addAction(show_source)
        help_actions.addAction(rich_text_action)
        
        # Automatic import option
        auto_import = create_action(self, self.tr("Automatic import"),
                                    toggled=self.toggle_auto_import)
        auto_import_state = self.get_option('automatic_import')
        auto_import.setChecked(auto_import_state)
        
        # Lock checkbox
        self.locked_button = create_toolbutton(self,
                                               triggered=self.toggle_locked)
        layout_edit.addWidget(self.locked_button)
        self._update_lock_icon()
        
        # Option menu
        options_button = create_toolbutton(self, text=self.tr("Options"),
                                           icon=get_icon('tooloptions.png'))
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, [rich_text_action, plain_text_action, show_source,
                           None, auto_import])
        options_button.setMenu(menu)
        layout_edit.addWidget(options_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.plain_text)
        layout.addWidget(self.rich_text)
        self.setLayout(layout)
        
        QTimer.singleShot(8000, self.refresh_plugin)
            
    #------ ReadOnlyEditor API -------------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Object inspector')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('inspector.png')
    
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
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
        self.main.console.set_inspector(self)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def refresh_plugin(self):
        """Refresh widget"""
        self.set_object_text(None, force_refresh=False)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = get_color_scheme(self.get_option(color_scheme_n))
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        rich_font_n = 'rich_text'
        rich_font_o = self.get_plugin_font('rich_text')
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        if font_n in options:
            scs = color_scheme_o if color_scheme_n in options else None
            self.plain_text.editor.set_font(font_o, scs)
        if rich_font_n in options:
            self.rich_text.webview.set_font(rich_font_o)
        elif color_scheme_n in options:
            self.plain_text.editor.set_color_scheme(color_scheme_o)
        if wrap_n in options:
            self.plain_text.editor.toggle_wrap_mode(wrap_o)
        
    #------ Public API ---------------------------------------------------------
    def set_external_console(self, external_console):
        self.external_console = external_console
    
    def force_refresh(self):
        self.set_object_text(None, force_refresh=True)
    
    def set_object_text(self, text, force_refresh=False, ignore_unknown=False):
        """Set object analyzed by Object Inspector"""
        if (self.locked and not force_refresh):
            return

        add_to_combo = True
        if text is None:
            text = unicode(self.combo.currentText())
            add_to_combo = False
            
        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return
        
        if add_to_combo:
            self.combo.add_text(text)
        
        self.save_history()
        if hasattr(self.main, 'tabifiedDockWidgets'):
            # 'QMainWindow.tabifiedDockWidgets' was introduced in PyQt 4.5
            if self.dockwidget and self.dockwidget.isVisible() \
               and not self.ismaximized and text != self._last_text:
                dockwidgets = self.main.tabifiedDockWidgets(self.dockwidget)
                if self.main.console.dockwidget not in dockwidgets and \
                   (hasattr(self.main, 'extconsole') and \
                    self.main.extconsole.dockwidget not in dockwidgets):
                    self.dockwidget.raise_()
        self._last_text = text
    
    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n','')
                       for line in file(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history
    
    def save_history(self):
        """Save history to a text file in user home directory"""
        file(self.LOG_PATH, 'w').write("\n".join( \
            [ unicode( self.combo.itemText(index) )
                for index in range(self.combo.count()) ] ))
        
    def toggle_plain_text(self, checked):
        """Toggle plain text docstring"""
        if checked:
            self.docstring = checked
            self.rich_help = not checked
        
            if self.plain_text.isHidden():
                self.plain_text.show()
                self.rich_text.hide()
            self.force_refresh()
        
    def toggle_show_source(self, checked):
        """Toggle show source code"""
        if checked:
            self.docstring = not checked
            self.rich_help = not checked
        
            if self.plain_text.isHidden():
                self.plain_text.show()
                self.rich_text.hide()
            self.force_refresh()
        
    def toggle_rich_text(self, checked):
        """Toggle between sphinxified docstrings or plain ones"""
        if checked:
            self.rich_help = checked
            self.docstring = not checked
            
            if self.rich_text.isHidden():
                self.plain_text.hide()
                self.rich_text.show()
            self.force_refresh()
        
    def toggle_auto_import(self, checked):
        """Toggle automatic import feature"""
        self.force_refresh()
        self.combo.validate_current_text()
        self.set_option('automatic_import', checked)
        
    def toggle_locked(self):
        """
        Toggle locked state
        locked = disable link with Console
        """
        self.locked = not self.locked
        self._update_lock_icon()
        
    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = get_icon("lock.png" if self.locked else "lock_open.png")
        self.locked_button.setIcon(icon)
        tip = self.tr("Unlock") if self.locked else self.tr("Lock")
        self.locked_button.setToolTip(tip)
        
    def set_shell(self, shell):
        """Bind to shell"""
        self.shell = shell

    def get_running_python_shell(self):
        shell = None
        if self.external_console is not None:
            shell = self.external_console.get_running_python_shell()
        if shell is None:
            shell = self.main.console.shell
        return shell
        
    def shell_terminated(self, shell):
        """
        External shall has terminated:
        binding object inspector to another shell
        """
        if self.shell is shell:
            self.shell = self.get_running_python_shell()
        
    def _check_if_shell_is_running(self):
        """
        Checks if bound external shell is still running.
        Otherwise, switch to internal console
        """
        if isinstance(self.shell, ExtPythonShellWidget) \
           and not self.shell.externalshell.is_running():
            self.shell = self.get_running_python_shell()
        
    def show_help(self, obj_text, ignore_unknown=False):
        """Show help"""
        if self.shell is None:
            return
        self._check_if_shell_is_running()
        obj_text = unicode(obj_text)

        if self.get_option('automatic_import'):
            self.shell.is_defined(obj_text, force_import=True) # force import
        
        if self.shell.is_defined(obj_text):
            doc_text = self.shell.get_doc(obj_text)
            if isinstance(doc_text, bool):
                doc_text = None
            source_text = self.shell.get_source(obj_text)
        else:
            doc_text = None
            source_text = None
            
        is_code = False
        found = True
        no_doc = self.tr("No documentation available")
        
        if self.rich_help:
            if doc_text is not None:
                html_text = sphinxify(doc_text)
            else:
                html_text = '<div id=\"warning\">' + no_doc + '</div>'
                if ignore_unknown:
                    return False
            
            html_text = HTML_HEAD + html_text + HTML_TAIL
            self.rich_text.webview.setHtml(html_text,
                                           QUrl.fromLocalFile(CSS_PATH))
        
        elif self.docstring:
            hlp_text = doc_text
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    hlp_text = no_doc
                    if ignore_unknown:
                        return False
        else:
            hlp_text = source_text
            if hlp_text is None:
                hlp_text = doc_text
                if hlp_text is None:
                    hlp_text = self.tr("No source code available.")
                    if ignore_unknown:
                        return False
            else:
                is_code = True
        
        if self.plain_text.editor.isVisible():
            self.plain_text.editor.set_highlight_current_line(is_code)
            self.plain_text.editor.set_occurence_highlighting(is_code)
            if is_code:
                self.plain_text.editor.set_language('py')
            else:
                self.plain_text.editor.set_language(None)
            self.plain_text.editor.set_text(hlp_text)
            self.plain_text.editor.set_cursor_position('sof')
        
        return found
