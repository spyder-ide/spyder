# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Object Inspector Plugin"""

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QMenu,
                         QToolButton, QGroupBox, QFontComboBox)
from PyQt4.QtCore import SIGNAL

import sys, re, os.path as osp, socket

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_conf_path, get_icon, CONF, get_color_scheme
from spyderlib.utils.qthelpers import (create_toolbutton, add_actions,
                                       create_action)
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.plugins import ReadOnlyEditor, PluginConfigPage
from spyderlib.widgets.externalshell.pythonshell import ExtPythonShellWidget


class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
    def __init__(self, parent):
        super(ObjectComboBox, self).__init__(parent)
        self.object_inspector = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
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
        font_group = self.create_fontgroup(option=None,
                                    text=self.tr("Font style"),
                                    fontfilters=QFontComboBox.MonospacedFonts)
        names = CONF.get('color_schemes', 'names')
        choices = zip(names, names)
        cs_combo = self.create_combobox(self.tr("Syntax color scheme: "),
                                        choices, 'color_scheme_name')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(cs_combo)
        sourcecode_group.setLayout(sourcecode_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(font_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class ObjectInspector(ReadOnlyEditor):
    """
    Docstrings viewer widget
    """
    CONF_SECTION = 'inspector'
    CONFIGWIDGET_CLASS = ObjectInspectorConfigPage
    LOG_PATH = get_conf_path('.inspector')
    def __init__(self, parent):
        self.set_default_color_scheme()
        ReadOnlyEditor.__init__(self, parent)
        
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
        
        # Doc/source option
        help_or_doc = create_action(self, self.tr("Show source"),
                                    toggled=self.toggle_help)
        help_or_doc.setChecked(False)
        self.docstring = True
        
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
        add_actions(menu, [help_or_doc, auto_import])
        options_button.setMenu(menu)
        layout_edit.addWidget(options_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
            
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
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        if font_n in options:
            scs = color_scheme_o if color_scheme_n in options else None
            self.editor.set_font(font_o, scs)
        elif color_scheme_n in options:
            self.editor.set_color_scheme(color_scheme_o)
        if wrap_n in options:
            self.editor.toggle_wrap_mode(wrap_o)
        
    #------ Public API ---------------------------------------------------------
    def set_external_console(self, external_console):
        self.external_console = external_console
    
    def force_refresh(self):
        self.set_object_text(None, force_refresh=True)
    
    def set_object_text(self, text, force_refresh=False, ignore_unknown=False):
        """Set object analyzed by Object Inspector"""
        if (self.locked and not force_refresh):
            return
            
        found = self.show_help(text, ignore_unknown=ignore_unknown)
        if ignore_unknown and not found:
            return
        
        if text is None:
            text = self.combo.currentText()
        else:
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
        
    def toggle_help(self, checked):
        """Toggle between docstring and help()"""
        self.docstring = not checked
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
        if self.docstring:
            hlp_text = doc_text
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    hlp_text = self.tr("No documentation available.")
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
        self.editor.set_highlight_current_line(is_code)
        self.editor.set_occurence_highlighting(is_code)
        if is_code:
            self.editor.set_language('py')
        else:
            self.editor.set_language(None)
        self.editor.set_text(hlp_text)
        self.editor.set_cursor_position('sof')
        
        return found
