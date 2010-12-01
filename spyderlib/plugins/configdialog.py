# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Configuration dialog / Preferences"""

import os, os.path as osp

from spyderlib.config import (get_icon, CONF, CUSTOM_COLOR_SCHEME_NAME,
                              set_default_color_scheme, COLOR_SCHEME_NAMES)
from spyderlib.utils.qthelpers import translate, get_std_icon
from spyderlib.userconfig import NoDefault
from spyderlib.widgets.colors import ColorLayout

from PyQt4.QtGui import (QWidget, QDialog, QListWidget, QListWidgetItem,
                         QVBoxLayout, QStackedWidget, QListView, QHBoxLayout,
                         QDialogButtonBox, QCheckBox, QMessageBox, QLabel,
                         QLineEdit, QSpinBox, QPushButton, QFontComboBox,
                         QGroupBox, QComboBox, QColor, QGridLayout, QTabWidget,
                         QRadioButton, QButtonGroup, QFileDialog)
from PyQt4.QtCore import Qt, QSize, SIGNAL, SLOT, QVariant


class ConfigPage(QWidget):
    """Configuration page base class"""
    def __init__(self, parent, apply_callback=None):
        QWidget.__init__(self, parent)
        self.apply_callback = apply_callback
        self.is_modified = False
        
    def initialize(self):
        """
        Initialize configuration page:
            * setup GUI widgets
            * load settings and change widgets accordingly
        """
        self.setup_page()
        self.load_from_conf()
        
    def get_name(self):
        """Return page name"""
        raise NotImplementedError
    
    def get_icon(self):
        """Return page icon"""
        raise NotImplementedError
    
    def setup_page(self):
        """Setup configuration page widget"""
        raise NotImplementedError
        
    def set_modified(self, state):
        self.is_modified = state
        self.emit(SIGNAL("apply_button_enabled(bool)"), state)
        
    def is_valid(self):
        """Return True if all widget contents are valid"""
        raise NotImplementedError
    
    def apply_changes(self):
        """Apply changes callback"""
        if self.is_modified:
            self.save_to_conf()
            if self.apply_callback is not None:
                self.apply_callback()
            self.set_modified(False)
    
    def load_from_conf(self):
        """Load settings from configuration file"""
        raise NotImplementedError
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        raise NotImplementedError


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.contents_widget = QListWidget()
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setMaximumWidth(200)
        self.contents_widget.setSpacing(1)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Apply
                                     |QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        self.connect(bbox, SIGNAL("clicked(QAbstractButton*)"),
                     self.button_clicked)

        self.pages_widget = QStackedWidget()
        self.connect(self.pages_widget, SIGNAL("currentChanged(int)"),
                     self.current_page_changed)

        self.connect(self.contents_widget, SIGNAL("currentRowChanged(int)"),
                     self.pages_widget.setCurrentIndex)
        self.contents_widget.setCurrentRow(0)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.contents_widget)
        hlayout.addWidget(self.pages_widget, 1)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addStretch(1)
        vlayout.addSpacing(12)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        self.setWindowTitle(self.tr("Preferences"))
        self.setWindowIcon(get_icon("configure.png"))
        
    def get_current_index(self):
        """Return current page index"""
        return self.contents_widget.currentRow()
        
    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)
        
    def accept(self):
        """Reimplement Qt method"""
        for index in range(self.pages_widget.count()):
            configpage = self.pages_widget.widget(index)
            if not configpage.is_valid():
                return
            configpage.apply_changes()
        QDialog.accept(self)
        
    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            configpage = self.pages_widget.currentWidget()
            if not configpage.is_valid():
                return
            configpage.apply_changes()
            
    def current_page_changed(self, index):
        widget = self.pages_widget.widget(index)
        self.apply_btn.setVisible(widget.apply_callback is not None)
        self.apply_btn.setEnabled(widget.is_modified)
        
    def add_page(self, widget):
        self.connect(widget, SIGNAL("apply_button_enabled(bool)"),
                     self.apply_btn.setEnabled)
        self.pages_widget.addWidget(widget)
        item = QListWidgetItem(self.contents_widget)
        item.setIcon(widget.get_icon())
        item.setText(widget.get_name())
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        item.setSizeHint(QSize(0, 25))


class SpyderConfigPage(ConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, parent):
        ConfigPage.__init__(self, parent,
                            apply_callback=lambda:
                            self.apply_settings(self.changed_options))
        self.checkboxes = {}
        self.radiobuttons = {}
        self.lineedits = {}
        self.validate_data = {}
        self.spinboxes = {}
        self.comboboxes = {}
        self.fontboxes = {}
        self.coloredits = {}
        self.scedits = {}
        self.changed_options = set()
        self.default_button_group = None
        
    def apply_settings(self, options):
        raise NotImplementedError
        
    def set_modified(self, state):
        ConfigPage.set_modified(self, state)
        if not state:
            self.changed_options = set()
        
    def is_valid(self):
        """Return True if all widget contents are valid"""
        for lineedit in self.lineedits:
            if lineedit in self.validate_data and lineedit.isEnabled():
                validator, invalid_msg = self.validate_data[lineedit]
                text = unicode(lineedit.text())
                if not validator(text):
                    QMessageBox.critical(self, self.get_name(),
                                     "%s:<br><b>%s</b>" % (invalid_msg, text),
                                     QMessageBox.Ok)
                    return False
        return True
        
    def load_from_conf(self):
        """Load settings from configuration file"""
        for checkbox, (option, default) in self.checkboxes.items():
            checkbox.setChecked(self.get_option(option, default))
            checkbox.setProperty("option", QVariant(option))
            self.connect(checkbox, SIGNAL("clicked(bool)"),
                         lambda checked: self.has_been_modified())
        for radiobutton, (option, default) in self.radiobuttons.items():
            radiobutton.setChecked(self.get_option(option, default))
            radiobutton.setProperty("option", QVariant(option))
            self.connect(radiobutton, SIGNAL("toggled(bool)"),
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
        for radiobutton, (option, _default) in self.radiobuttons.items():
            self.set_option(option, radiobutton.isChecked())
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
            self.set_font(font, option)
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
    
    def create_radiobutton(self, text, option, default=NoDefault,
                           tip=None, msg_warning=None, msg_info=None,
                           msg_if_enabled=False, button_group=None):
        radiobutton = QRadioButton(text)
        if button_group is None:
            if self.default_button_group is None:
                self.default_button_group = QButtonGroup(self)
            button_group = self.default_button_group
        button_group.addButton(radiobutton)
        if tip is not None:
            radiobutton.setToolTip(tip)
        self.radiobuttons[radiobutton] = (option, default)
        if msg_warning is not None or msg_info is not None:
            def show_message(is_checked):
                if is_checked or not msg_if_enabled:
                    if msg_warning is not None:
                        QMessageBox.warning(self, self.get_name(),
                                            msg_warning, QMessageBox.Ok)
                    if msg_info is not None:
                        QMessageBox.information(self, self.get_name(),
                                                msg_info, QMessageBox.Ok)
            self.connect(radiobutton, SIGNAL("toggled(bool)"), show_message)
        return radiobutton
    
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
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_browsedir(self, text, option, default=NoDefault, tip=None):
        widget = self.create_lineedit(text, option, default,
                                      alignment=Qt.Horizontal)
        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break
        msg = translate("PluginConfigPage", "Invalid directory path")
        self.validate_data[edit] = (osp.isdir, msg)
        browse_btn = QPushButton(get_std_icon('DirOpenIcon'), "", self)
        browse_btn.setToolTip(translate("PluginConfigPage", "Select directory"))
        self.connect(browse_btn, SIGNAL("clicked()"),
                     lambda: self.select_directory(edit))
        layout = QHBoxLayout()
        layout.addWidget(widget)
        layout.addWidget(browse_btn)
        layout.setContentsMargins(0, 0, 0, 0)
        browsedir = QWidget(self)
        browsedir.setLayout(layout)
        return browsedir

    def select_directory(self, edit):
        """Select directory"""
        basedir = unicode(edit.text())
        if not osp.isdir(basedir):
            basedir = os.getcwdu()
        title = translate("PluginConfigPage", "Select directory")
        directory = QFileDialog.getExistingDirectory(self, title, basedir)
        if not directory.isEmpty():
            edit.setText(directory)
    
    def create_browsefile(self, text, option, default=NoDefault, tip=None,
                          filters=None):
        widget = self.create_lineedit(text, option, default,
                                      alignment=Qt.Horizontal)
        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break
        msg = translate("PluginConfigPage", "Invalid file path")
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(get_std_icon('FileIcon'), "", self)
        browse_btn.setToolTip(translate("PluginConfigPage", "Select file"))
        self.connect(browse_btn, SIGNAL("clicked()"),
                     lambda: self.select_file(edit, filters))
        layout = QHBoxLayout()
        layout.addWidget(widget)
        layout.addWidget(browse_btn)
        layout.setContentsMargins(0, 0, 0, 0)
        browsedir = QWidget(self)
        browsedir.setLayout(layout)
        return browsedir

    def select_file(self, edit, filters=None):
        """Select File"""
        basedir = osp.dirname(unicode(edit.text()))
        if not osp.isdir(basedir):
            basedir = os.getcwdu()
        if filters is None:
            filters = translate("PluginConfigPage", "All files (*.*)")
        title = translate("PluginConfigPage", "Select file")
        filename = QFileDialog.getOpenFileName(self, title, basedir, filters)
        if filename:
            edit.setText(filename)
    
    def create_spinbox(self, prefix, suffix, option, default=NoDefault,
                       min_=None, max_=None, step=None, tip=None):
        if prefix:
            plabel = QLabel(prefix)
        else:
            plabel = None
        if suffix:
            slabel = QLabel(suffix)
        else:
            slabel = None
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
            if subwidget is not None:
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
        cb_bold = QCheckBox()
        cb_bold.setIcon(get_icon("bold.png"))
        cb_bold.setToolTip(translate("PluginConfigPage", "Bold"))
        cb_italic = QCheckBox()
        cb_italic.setIcon(get_icon("italic.png"))
        cb_italic.setToolTip(translate("PluginConfigPage", "Italic"))
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


class MainConfigPage(GeneralConfigPage):
    CONF_SECTION = "main"
    def get_name(self):
        return self.tr("General")
    
    def get_icon(self):
        return get_icon("genprefs.png")
    
    def setup_page(self):
        interface_group = QGroupBox(self.tr("Interface"))
        newcb = self.create_checkbox
        vertdock_box = newcb(self.tr("Vertical dockwidget title bars"),
                             'vertical_dockwidget_titlebars')
        verttabs_box = newcb(self.tr("Vertical dockwidget tabs"),
                             'vertical_tabs')
        animated_box = newcb(self.tr("Animated toolbars and dockwidgets"),
                             'animated_docks')
        margin_box = newcb(self.tr("Custom dockwidget margin:"),
                           'use_custom_margin')
        margin_spin = self.create_spinbox("", "pixels", 'custom_margin',
                                          0, 0, 30)
        self.connect(margin_box, SIGNAL("toggled(bool)"),
                     margin_spin.setEnabled)
        margins_layout = QHBoxLayout()
        margins_layout.addWidget(margin_box)
        margins_layout.addWidget(margin_spin)
        
        interface_layout = QVBoxLayout()
        interface_layout.addWidget(vertdock_box)
        interface_layout.addWidget(verttabs_box)
        interface_layout.addWidget(animated_box)
        interface_layout.addLayout(margins_layout)
        interface_group.setLayout(interface_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(interface_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
        
    def apply_settings(self, options):
        self.main.apply_settings()


class ColorSchemeConfigPage(GeneralConfigPage):
    CONF_SECTION = "color_schemes"
    def get_name(self):
        return self.tr("Syntax coloring")
    
    def get_icon(self):
        return get_icon("genprefs.png")
    
    def setup_page(self):
        tabs = QTabWidget()
        names = self.get_option("names")
        names.pop(names.index(CUSTOM_COLOR_SCHEME_NAME))
        names.insert(0, CUSTOM_COLOR_SCHEME_NAME)
        fieldnames = {
                      "background":     self.tr("Background:"),
                      "currentline":    self.tr("Current line:"),
                      "occurence":      self.tr("Occurence:"),
                      "ctrlclick":      self.tr("Link:"),
                      "sideareas":      self.tr("Side areas:"),
                      "matched_p":      self.tr("Matched parentheses:"),
                      "unmatched_p":    self.tr("Unmatched parentheses:"),
                      "normal":         self.tr("Normal text:"),
                      "keyword":        self.tr("Keyword:"),
                      "builtin":        self.tr("Builtin:"),
                      "definition":     self.tr("Definition:"),
                      "comment":        self.tr("Comment:"),
                      "string":         self.tr("String:"),
                      "number":         self.tr("Number:"),
                      "instance":       self.tr("Instance:"),
                      }
        from spyderlib.widgets.codeeditor import syntaxhighlighters
        assert all([key in fieldnames
                    for key in syntaxhighlighters.COLOR_SCHEME_KEYS])
        for tabname in names:
            cs_group = QGroupBox(self.tr("Color scheme"))
            cs_layout = QGridLayout()
            for row, key in enumerate(syntaxhighlighters.COLOR_SCHEME_KEYS):
                option = "%s/%s" % (tabname, key)
                value = self.get_option(option)
                name = fieldnames[key]
                if isinstance(value, basestring):
                    label, clayout = self.create_coloredit(name, option,
                                                           without_layout=True)
                    label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
                    cs_layout.addWidget(label, row+1, 0)
                    cs_layout.addLayout(clayout, row+1, 1)
                else:
                    label, clayout, cb_bold, cb_italic = self.create_scedit(
                                            name, option, without_layout=True)
                    label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
                    cs_layout.addWidget(label, row+1, 0)
                    cs_layout.addLayout(clayout, row+1, 1)
                    cs_layout.addWidget(cb_bold, row+1, 2)
                    cs_layout.addWidget(cb_italic, row+1, 3)
            cs_group.setLayout(cs_layout)
            if tabname in COLOR_SCHEME_NAMES:
                def_btn = self.create_button(self.tr("Reset to default values"),
                                             self.reset_to_default)
                def_btn.setProperty("name", QVariant(tabname))
                tabs.addTab(self.create_tab(cs_group, def_btn), tabname)
            else:
                tabs.addTab(self.create_tab(cs_group), tabname)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)
        
    def reset_to_default(self):
        name = unicode(self.sender().property("name").toString())
        set_default_color_scheme(name, replace=True)
        self.load_from_conf()
            
    def apply_settings(self, options):
        self.main.editor.apply_plugin_settings(['color_scheme_name'])
        if self.main.historylog is not None:
            self.main.historylog.apply_plugin_settings(['color_scheme_name'])
        if self.main.inspector is not None:
            self.main.inspector.apply_plugin_settings(['color_scheme_name'])
