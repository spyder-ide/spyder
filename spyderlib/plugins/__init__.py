# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.plugins
=================

Here, 'plugins' are widgets designed specifically for Spyder
These plugins inherit the following classes
(SpyderPluginMixin & SpyderPluginWidget)
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QDockWidget, QWidget, QFontDialog, QShortcut, QCursor,
                         QKeySequence, QMainWindow, QApplication, QCheckBox,
                         QMessageBox, QLabel, QLineEdit, QSpinBox, QVBoxLayout,
                         QHBoxLayout, QPushButton, QFontComboBox, QGroupBox,
                         QComboBox, QColor, QGridLayout, QTabWidget)
from PyQt4.QtCore import SIGNAL, Qt, QObject, QVariant

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import (toggle_actions, create_action,
                                       add_actions, translate)
from spyderlib.config import (CONF, get_font, set_font, get_icon,
                              is_shortcut_available, CUSTOM_COLOR_SCHEME_NAME)
from spyderlib.userconfig import NoDefault
from spyderlib.plugins.configdialog import ConfigPage
from spyderlib.widgets.editor import CodeEditor
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.colors import ColorLayout


class SpyderConfigPage(ConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, parent):
        ConfigPage.__init__(self, parent,
                            apply_callback=lambda:
                            self.apply_settings(self.changed_options))
        self.checkboxes = {}
        self.lineedits = {}
        self.spinboxes = {}
        self.comboboxes = {}
        self.fontboxes = {}
        self.coloredits = {}
        self.scedits = {}
        self.changed_options = set()
        
    def apply_settings(self, options):
        raise NotImplementedError
        
    def set_modified(self, state):
        ConfigPage.set_modified(self, state)
        if not state:
            self.changed_options = set()
        
    def load_from_conf(self):
        """Load settings from configuration file"""
        for checkbox, (option, default) in self.checkboxes.items():
            checkbox.setChecked(self.get_option(option, default))
            checkbox.setProperty("option", QVariant(option))
            self.connect(checkbox, SIGNAL("clicked(bool)"),
                         lambda checked: self.has_been_modified())
        for lineedit, (option, default) in self.lineedits.items():
            lineedit.setText(self.get_option(option, default))
            lineedit.setProperty("option", QVariant(option))
            self.connect(lineedit, SIGNAL("textChanged(QString)"),
                         lambda text: self.has_been_modified())
        for spinbox, (option, default) in self.spinboxes.items():
            spinbox.setValue(self.get_option(option, default))
            spinbox.setProperty("option", QVariant(option))
            self.connect(spinbox, SIGNAL('valueChanged(int)'),
                         lambda value: self.has_been_modified())
        for combobox, (option, default) in self.comboboxes.items():
            value = self.get_option(option, default)
            for index in range(combobox.count()):
                if unicode(combobox.itemData(index).toString()
                           ) == unicode(value):
                    break
            combobox.setCurrentIndex(index)
            combobox.setProperty("option", QVariant(option))
            self.connect(combobox, SIGNAL('currentIndexChanged(int)'),
                         lambda index: self.has_been_modified())
        for (fontbox, sizebox), option in self.fontboxes.items():
            font = self.get_font(option)
            fontbox.setCurrentFont(font)
            sizebox.setValue(font.pointSize())
            if option is None:
                property = QVariant('plugin_font')
            else:
                property = QVariant(option)
            fontbox.setProperty("option", property)
            self.connect(fontbox, SIGNAL('currentIndexChanged(int)'),
                         lambda index: self.has_been_modified())
            sizebox.setProperty("option", property)
            self.connect(sizebox, SIGNAL('valueChanged(int)'),
                         lambda value: self.has_been_modified())
        for clayout, (option, default) in self.coloredits.items():
            property = QVariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default))
            edit.setProperty("option", property)
            btn.setProperty("option", property)
            self.connect(btn, SIGNAL('clicked()'), self.has_been_modified)
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda text: self.has_been_modified())
        for (clayout, cb_bold, cb_italic), (option, default) in self.scedits.items():
            edit = clayout.lineedit
            btn = clayout.colorbtn
            color, bold, italic = self.get_option(option, default)
            edit.setText(color)
            cb_bold.setChecked(bold)
            cb_italic.setChecked(italic)
            for _w in (edit, btn, cb_bold, cb_italic):
                _w.setProperty("option", QVariant(option))
            self.connect(btn, SIGNAL('clicked()'), self.has_been_modified)
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda text: self.has_been_modified())
            self.connect(cb_bold, SIGNAL("clicked(bool)"),
                         lambda checked: self.has_been_modified())
            self.connect(cb_italic, SIGNAL("clicked(bool)"),
                         lambda checked: self.has_been_modified())
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        for checkbox, (option, _default) in self.checkboxes.items():
            self.set_option(option, checkbox.isChecked())
        for lineedit, (option, _default) in self.lineedits.items():
            self.set_option(option, unicode(lineedit.text()))
        for spinbox, (option, _default) in self.spinboxes.items():
            self.set_option(option, spinbox.value())
        for combobox, (option, _default) in self.comboboxes.items():
            data = combobox.itemData(combobox.currentIndex())
            self.set_option(option, unicode(data.toString()))
        for (fontbox, sizebox), option in self.fontboxes.items():
            font = fontbox.currentFont()
            font.setPointSize(sizebox.value())
            self.set_font(font)
        for clayout, (option, _default) in self.coloredits.items():
            self.set_option(option, unicode(clayout.lineedit.text()))
        for (clayout, cb_bold, cb_italic), (option, _default) in self.scedits.items():
            color = unicode(clayout.lineedit.text())
            bold = cb_bold.isChecked()
            italic = cb_italic.isChecked()
            self.set_option(option, (color, bold, italic))
    
    def has_been_modified(self):
        option = unicode(self.sender().property("option").toString())
        self.set_modified(True)
        self.changed_options.add(option)
    
    def create_checkbox(self, text, option, default=NoDefault,
                        tip=None, msg_warning=None, msg_info=None,
                        msg_if_enabled=False):
        checkbox = QCheckBox(text)
        if tip is not None:
            checkbox.setToolTip(tip)
        self.checkboxes[checkbox] = (option, default)
        if msg_warning is not None or msg_info is not None:
            def show_message(is_checked):
                if is_checked or not msg_if_enabled:
                    if msg_warning is not None:
                        QMessageBox.warning(self, self.get_name(),
                                            msg_warning, QMessageBox.Ok)
                    if msg_info is not None:
                        QMessageBox.information(self, self.get_name(),
                                                msg_info, QMessageBox.Ok)
            self.connect(checkbox, SIGNAL("clicked(bool)"), show_message)
        return checkbox
    
    def create_lineedit(self, text, option, default=NoDefault,
                        tip=None, alignment=Qt.Vertical):
        label = QLabel(text)
        label.setWordWrap(True)
        edit = QLineEdit()
        layout = QVBoxLayout() if alignment == Qt.Vertical else QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip:
            edit.setToolTip(tip)
        self.lineedits[edit] = (option, default)
        lineedit = QWidget(self)
        lineedit.setLayout(layout)
        return lineedit
    
    def create_spinbox(self, prefix, suffix, option, default=NoDefault,
                       min_=None, max_=None, step=None, tip=None):
        plabel = QLabel(prefix)
        slabel = QLabel(suffix)
        spinbox = QSpinBox()
        if min_ is not None:
            spinbox.setMinimum(min_)
        if max_ is not None:
            spinbox.setMaximum(max_)
        if step is not None:
            spinbox.setSingleStep(step)
        if tip is not None:
            spinbox.setToolTip(tip)
        self.spinboxes[spinbox] = (option, default)
        layout = QHBoxLayout()
        for subwidget in (plabel, spinbox, slabel):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_coloredit(self, text, option, default=NoDefault, tip=None,
                         without_layout=False):
        label = QLabel(text)
        clayout = ColorLayout(QColor(Qt.black), self)
        clayout.lineedit.setMaximumWidth(80)
        if tip is not None:
            clayout.setToolTip(tip)
        self.coloredits[clayout] = (option, default)
        if without_layout:
            return label, clayout
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addLayout(clayout)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_scedit(self, text, option, default=NoDefault, tip=None,
                      without_layout=False):
        label = QLabel(text)
        clayout = ColorLayout(QColor(Qt.black), self)
        clayout.lineedit.setMaximumWidth(80)
        if tip is not None:
            clayout.setToolTip(tip)
        cb_bold = QCheckBox(self.tr("Bold"))
        cb_italic = QCheckBox(self.tr("Italic"))
        self.scedits[(clayout, cb_bold, cb_italic)] = (option, default)
        if without_layout:
            return label, clayout, cb_bold, cb_italic
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addLayout(clayout)
        layout.addSpacing(10)
        layout.addWidget(cb_bold)
        layout.addWidget(cb_italic)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_combobox(self, text, choices, option, default=NoDefault,
                        tip=None):
        """choices: couples (name, key)"""
        label = QLabel(text)
        combobox = QComboBox()
        if tip is not None:
            combobox.setToolTip(tip)
        for name, key in choices:
            combobox.addItem(name, QVariant(key))
        self.comboboxes[combobox] = (option, default)
        layout = QHBoxLayout()
        for subwidget in (label, combobox):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_fontgroup(self, option=None, text=None,
                         tip=None, fontfilters=None):
        """Option=None -> setting plugin font"""
        fontlabel = QLabel(translate("PluginConfigPage", "Font: "))
        fontbox = QFontComboBox()
        if fontfilters is not None:
            fontbox.setFontFilters(fontfilters)
        sizelabel = QLabel("  "+translate("PluginConfigPage", "Size: "))
        sizebox = QSpinBox()
        sizebox.setRange(7, 100)
        self.fontboxes[(fontbox, sizebox)] = option
        layout = QHBoxLayout()
        for subwidget in (fontlabel, fontbox, sizelabel, sizebox):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        if text is None:
            text = translate("PluginConfigPage", "Font style")
        group = QGroupBox(text)
        group.setLayout(layout)
        if tip is not None:
            group.setToolTip(tip)
        return group
    
    def create_button(self, text, callback):
        btn = QPushButton(text)
        self.connect(btn, SIGNAL('clicked()'), callback)
        btn.setProperty("option", QVariant(""))
        self.connect(btn, SIGNAL('clicked()'), self.has_been_modified)
        return btn
    
    def create_tab(self, *widgets):
        """Create simple tab widget page: widgets added in a vertical layout"""
        widget = QWidget()
        layout = QVBoxLayout()
        for widg in widgets:
            layout.addWidget(widg)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget
    

class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.get_option = plugin.get_option
        self.set_option = plugin.set_option
        self.get_name = plugin.get_plugin_title
        self.get_icon = plugin.get_plugin_icon
        self.get_font = plugin.get_plugin_font
        self.set_font = plugin.set_plugin_font
        self.apply_settings = plugin.apply_plugin_settings
        SpyderConfigPage.__init__(self, parent)


class GeneralConfigPage(SpyderConfigPage):
    CONF_SECTION = None
    def __init__(self, parent, main):
        SpyderConfigPage.__init__(self, parent)
        self.main = main

    def set_option(self, option, value):
        CONF.set(self.CONF_SECTION, option, value)

    def get_option(self, option, default=NoDefault):
        return CONF.get(self.CONF_SECTION, option, default)
            
    def apply_settings(self, options):
        raise NotImplementedError


class SpyderPluginMixin(object):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface
    
    Signals:
        'option_changed'
            Example:
            self.emit(SIGNAL('option_changed'), 'show_all', checked)
        'show_message(QString,int)'
    """
    CONF_SECTION = None
    CONFIGWIDGET_CLASS = None
    FLAGS = Qt.Window
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | \
               QDockWidget.DockWidgetFloatable | \
               QDockWidget.DockWidgetMovable
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    def __init__(self, main):
        """Bind widget to a QMainWindow instance"""
        super(SpyderPluginMixin, self).__init__()
        assert self.CONF_SECTION is not None
        self.main = main
        self.plugin_actions = self.get_plugin_actions()
        self.dockwidget = None
        self.ismaximized = False
        QObject.connect(self, SIGNAL('option_changed'), self.set_option)
        QObject.connect(self, SIGNAL('show_message(QString,int)'),
                        self.show_message)
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        dock = QDockWidget(self.get_plugin_title(), self.main)#, self.FLAGS) -> bug in Qt 4.4
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.ALLOWED_AREAS)
        dock.setFeatures(self.FEATURES)
        dock.setWidget(self)
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.dockwidget = dock
        self.refresh_plugin()
        short = self.get_option("shortcut", None)
        if short is not None and is_shortcut_available(short):
            QShortcut(QKeySequence(short), self.main, self.switch_to_plugin)
        return (dock, self.LOCATION)
    
    def create_mainwindow(self):
        """
        Create a QMainWindow instance containing this plugin
        Note: this method is currently not used
        """
        mainwindow = QMainWindow()
        mainwindow.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_widget_icon()
        if isinstance(icon, basestring):
            icon = get_icon(icon)
        mainwindow.setWindowIcon(icon)
        mainwindow.setWindowTitle(self.get_plugin_title())
        mainwindow.setCentralWidget(self)
        self.refresh_plugin()
        return mainwindow
    
    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        raise NotImplementedError
    
    def switch_to_plugin(self):
        """Switch to plugin
        This method is called when pressing plugin's shortcut key"""
        self.dockwidget.show()
        self.visibility_changed(True)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self.ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self.plugin_actions, visible)
        if visible:
            self.refresh_plugin() #XXX Is it a good idea?

    def set_option(self, option, value):
        """
        Set a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        self.emit(SIGNAL('option_changed'), 'show_all', checked)
        """
        CONF.set(self.CONF_SECTION, option, value)

    def get_option(self, option, default=NoDefault):
        """Get a plugin option from configuration file"""
        return CONF.get(self.CONF_SECTION, option, default)
    
    def get_plugin_font(self, option=None):
        """Return plugin font option"""
        return get_font(self.CONF_SECTION, option)
    
    def set_plugin_font(self, font, option=None):
        """Set plugin font option"""
        set_font(font, self.CONF_SECTION, option)
        
    def show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar
        and changing mouse cursor to Qt.WaitCursor
        """
        self.show_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        
    def ending_long_process(self, message=""):
        """
        Clearing main window's status bar
        and restoring mouse cursor
        """
        QApplication.restoreOverrideCursor()
        self.show_message(message, timeout=2000)
        QApplication.processEvents()


class SpyderPluginWidget(QWidget, SpyderPluginMixin):
    """
    Spyder base widget class
    Spyder's widgets either inherit this class or reimplement its interface
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        self.setWindowTitle(self.get_plugin_title())
        
    def get_plugin_title(self):
        """
        Return plugin title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError
    
    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance)
        Note: this is required for plugins creating a main window
              (see SpyderPluginMixin.create_mainwindow)
              and for configuration dialog widgets creation
        """
        return get_icon('qt.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        pass
        
    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed
        Return True or False whether the plugin may be closed immediately or not
        Note: returned value is ignored if *cancelable* is False
        """
        raise NotImplementedError
        
    def refresh_plugin(self):
        """Refresh widget"""
        raise NotImplementedError
    
    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin
        Note: these actions will be enabled when plugin's dockwidget is visible
              and they will be disabled when it's hidden
        """
        raise NotImplementedError
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        raise NotImplementedError


class ReadOnlyEditor(SpyderPluginWidget):
    """
    Read-only editor plugin widget
    (see example of child class in inspector.py)
    """
    def __init__(self, parent):
        self.editor = None
        
        SpyderPluginWidget.__init__(self, parent)

        # Read-only editor
        self.editor = CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 scrollflagarea=False)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)
        self.editor.set_font(self.get_plugin_font())
        self.editor.toggle_wrap_mode(self.get_option('wrap'))
        
        # Add entries to read-only editor context-menu
        font_action = create_action(self, translate("Editor", "&Font..."), None,
                                    'font.png',
                                    translate("Editor", "Set font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, translate("Editor", "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.get_option('wrap'))
        self.editor.readonly_menu.addSeparator()
        add_actions(self.editor.readonly_menu, (font_action, wrap_action))
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()
        
        # <!> Layout will have to be implemented in child class!
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.editor
            
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.CONF_SECTION), self,
                                      translate("Editor", "Select a new font"))
        if valid:
            self.editor.set_font(font)
            set_font(font, self.CONF_SECTION)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)


class ColorSchemeConfigPage(GeneralConfigPage):
    CONF_SECTION = "color_schemes"
    def get_name(self):
        return self.tr("Syntax coloring")
    
    def get_icon(self):
        return get_icon("advanced.png")
    
    def setup_page(self):
        tabs = QTabWidget()
        for tabname in self.get_option("names"):
            cs_group = QGroupBox(self.tr("Color scheme"))
            cs_layout = QGridLayout()
            if tabname == CUSTOM_COLOR_SCHEME_NAME:
                text = self.tr("Note: this is the custom and editable syntax "
                               "color scheme")
            else:
                text = self.tr("Note: this syntax color scheme will not be "
                               "saved when closing Spyder. You may however "
                               "use it to help you defining your own custom "
                               "syntax color scheme")
            tlabel = QLabel(text)
            tlabel.setWordWrap(True)
            from spyderlib.widgets.codeeditor.syntaxhighlighters import BaseSH
            for row, key in enumerate(BaseSH.COLOR_SCHEME_KEYS):
                option = "%s/%s" % (tabname, key)
                value = self.get_option(option)
                if isinstance(value, basestring):
                    label, clayout = self.create_coloredit(key, option,
                                                           without_layout=True)
                    cs_layout.addWidget(label, row+1, 0)
                    cs_layout.addLayout(clayout, row+1, 1)
                else:
                    label, clayout, cb_bold, cb_italic = self.create_scedit(
                                                key, option, without_layout=True)
                    cs_layout.addWidget(label, row+1, 0)
                    cs_layout.addLayout(clayout, row+1, 1)
                    cs_layout.addWidget(cb_bold, row+1, 2)
                    cs_layout.addWidget(cb_italic, row+1, 3)
            cs_group.setLayout(cs_layout)
            tabs.addTab(self.create_tab(cs_group, tlabel), tabname)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)
            
    def apply_settings(self, options):
        # Editor plugin
        self.main.editor.apply_plugin_settings(['color_scheme_name'])
