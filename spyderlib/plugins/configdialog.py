# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Configuration dialog / Preferences"""

import os.path as osp

from spyderlib.baseconfig import _, running_in_mac_app
from spyderlib.config import CONF, is_gtk_desktop
from spyderlib.guiconfig import (CUSTOM_COLOR_SCHEME_NAME,
                                 set_default_color_scheme)
from spyderlib.utils.qthelpers import get_icon, get_std_icon
from spyderlib.userconfig import NoDefault
from spyderlib.widgets.colors import ColorLayout
from spyderlib.widgets.sourcecode import syntaxhighlighters as sh

from spyderlib.qt.QtGui import (QWidget, QDialog, QListWidget, QListWidgetItem,
                                QVBoxLayout, QStackedWidget, QListView,
                                QHBoxLayout, QDialogButtonBox, QCheckBox,
                                QMessageBox, QLabel, QLineEdit, QSpinBox,
                                QPushButton, QFontComboBox, QGroupBox,
                                QComboBox, QColor, QGridLayout, QTabWidget,
                                QRadioButton, QButtonGroup, QSplitter,
                                QStyleFactory, QScrollArea, QDoubleSpinBox)
from spyderlib.qt.QtCore import Qt, QSize, SIGNAL, SLOT, Slot
from spyderlib.qt.compat import (to_qvariant, from_qvariant,
                                 getexistingdirectory, getopenfilename)
from spyderlib.py3compat import to_text_string, is_text_string, getcwd


class ConfigAccessMixin(object):
    """Namespace for methods that access config storage"""
    CONF_SECTION = None

    def set_option(self, option, value):
        CONF.set(self.CONF_SECTION, option, value)

    def get_option(self, option, default=NoDefault):
        return CONF.get(self.CONF_SECTION, option, default)


class ConfigPage(QWidget):
    """Base class for configuration page in Preferences"""

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
        """Return configuration page name"""
        raise NotImplementedError
    
    def get_icon(self):
        """Return configuration page icon (24x24)"""
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
    """Spyder configuration ('Preferences') dialog box"""
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.contents_widget = QListWidget()
        self.contents_widget.setMovement(QListView.Static)
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

        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        self.setWindowTitle(_("Preferences"))
        self.setWindowIcon(get_icon("configure.png"))
        
    def get_current_index(self):
        """Return current page index"""
        return self.contents_widget.currentRow()
        
    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)
        
    def get_page(self, index=None):
        """Return page widget"""
        if index is None:
            widget = self.pages_widget.currentWidget()
        else:
            widget = self.pages_widget.widget(index)
        return widget.widget()
        
    def accept(self):
        """Reimplement Qt method"""
        for index in range(self.pages_widget.count()):
            configpage = self.get_page(index)
            if not configpage.is_valid():
                return
            configpage.apply_changes()
        QDialog.accept(self)
        
    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            configpage = self.get_page()
            if not configpage.is_valid():
                return
            configpage.apply_changes()
            
    def current_page_changed(self, index):
        widget = self.get_page(index)
        self.apply_btn.setVisible(widget.apply_callback is not None)
        self.apply_btn.setEnabled(widget.is_modified)
        
    def add_page(self, widget):
        self.connect(self, SIGNAL('check_settings()'), widget.check_settings)
        self.connect(widget, SIGNAL('show_this_page()'),
                     lambda row=self.contents_widget.count():
                     self.contents_widget.setCurrentRow(row))
        self.connect(widget, SIGNAL("apply_button_enabled(bool)"),
                     self.apply_btn.setEnabled)
        scrollarea = QScrollArea(self)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.pages_widget.addWidget(scrollarea)
        item = QListWidgetItem(self.contents_widget)
        item.setIcon(widget.get_icon())
        item.setText(widget.get_name())
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        item.setSizeHint(QSize(0, 25))
        
    def check_all_settings(self):
        """This method is called to check all configuration page settings
        after configuration dialog has been shown"""
        self.emit(SIGNAL('check_settings()'))
    
    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        QDialog.resizeEvent(self, event)
        self.emit(SIGNAL("size_change(QSize)"), self.size())


class SpyderConfigPage(ConfigPage, ConfigAccessMixin):
    """Plugin configuration dialog box page widget"""
    CONF_SECTION = None

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
    
    def check_settings(self):
        """This method is called to check settings after configuration 
        dialog has been shown"""
        pass
        
    def set_modified(self, state):
        ConfigPage.set_modified(self, state)
        if not state:
            self.changed_options = set()
        
    def is_valid(self):
        """Return True if all widget contents are valid"""
        for lineedit in self.lineedits:
            if lineedit in self.validate_data and lineedit.isEnabled():
                validator, invalid_msg = self.validate_data[lineedit]
                text = to_text_string(lineedit.text())
                if not validator(text):
                    QMessageBox.critical(self, self.get_name(),
                                     "%s:<br><b>%s</b>" % (invalid_msg, text),
                                     QMessageBox.Ok)
                    return False
        return True
        
    def load_from_conf(self):
        """Load settings from configuration file"""
        for checkbox, (option, default) in list(self.checkboxes.items()):
            checkbox.setChecked(self.get_option(option, default))
            self.connect(checkbox, SIGNAL("clicked(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
        for radiobutton, (option, default) in list(self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default))
            self.connect(radiobutton, SIGNAL("toggled(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
        for lineedit, (option, default) in list(self.lineedits.items()):
            lineedit.setText(self.get_option(option, default))
            self.connect(lineedit, SIGNAL("textChanged(QString)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
        for spinbox, (option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default))
            if type(spinbox) is QSpinBox:
                self.connect(spinbox, SIGNAL('valueChanged(int)'),
                             lambda _foo, opt=option: self.has_been_modified(opt))
            else:
                self.connect(spinbox, SIGNAL('valueChanged(double)'),
                             lambda _foo, opt=option: self.has_been_modified(opt))
        for combobox, (option, default) in list(self.comboboxes.items()):
            value = self.get_option(option, default)
            for index in range(combobox.count()):
                data = from_qvariant(combobox.itemData(index), to_text_string)
                # For PyQt API v2, it is necessary to convert `data` to 
                # unicode in case the original type was not a string, like an 
                # integer for example (see spyderlib.qt.compat.from_qvariant):
                if to_text_string(data) == to_text_string(value):
                    break
            combobox.setCurrentIndex(index)
            self.connect(combobox, SIGNAL('currentIndexChanged(int)'),
                         lambda _foo, opt=option: self.has_been_modified(opt))
        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            font = self.get_font(option)
            fontbox.setCurrentFont(font)
            sizebox.setValue(font.pointSize())
            if option is None:
                property = 'plugin_font'
            else:
                property = option
            self.connect(fontbox, SIGNAL('currentIndexChanged(int)'),
                         lambda _foo, opt=property: self.has_been_modified(opt))
            self.connect(sizebox, SIGNAL('valueChanged(int)'),
                         lambda _foo, opt=property: self.has_been_modified(opt))
        for clayout, (option, default) in list(self.coloredits.items()):
            property = to_qvariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default))
            self.connect(btn, SIGNAL('clicked()'),
                         lambda opt=option: self.has_been_modified(opt))
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
        for (clayout, cb_bold, cb_italic
             ), (option, default) in list(self.scedits.items()):
            edit = clayout.lineedit
            btn = clayout.colorbtn
            color, bold, italic = self.get_option(option, default)
            edit.setText(color)
            cb_bold.setChecked(bold)
            cb_italic.setChecked(italic)
            self.connect(btn, SIGNAL('clicked()'),
                         lambda opt=option: self.has_been_modified(opt))
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
            self.connect(cb_bold, SIGNAL("clicked(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
            self.connect(cb_italic, SIGNAL("clicked(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        for checkbox, (option, _default) in list(self.checkboxes.items()):
            self.set_option(option, checkbox.isChecked())
        for radiobutton, (option, _default) in list(self.radiobuttons.items()):
            self.set_option(option, radiobutton.isChecked())
        for lineedit, (option, _default) in list(self.lineedits.items()):
            self.set_option(option, to_text_string(lineedit.text()))
        for spinbox, (option, _default) in list(self.spinboxes.items()):
            self.set_option(option, spinbox.value())
        for combobox, (option, _default) in list(self.comboboxes.items()):
            data = combobox.itemData(combobox.currentIndex())
            self.set_option(option, from_qvariant(data, to_text_string))
        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            font = fontbox.currentFont()
            font.setPointSize(sizebox.value())
            self.set_font(font, option)
        for clayout, (option, _default) in list(self.coloredits.items()):
            self.set_option(option, to_text_string(clayout.lineedit.text()))
        for (clayout, cb_bold, cb_italic), (option, _default) in list(self.scedits.items()):
            color = to_text_string(clayout.lineedit.text())
            bold = cb_bold.isChecked()
            italic = cb_italic.isChecked()
            self.set_option(option, (color, bold, italic))
    
    @Slot(str)
    def has_been_modified(self, option):
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
        msg = _("Invalid directory path")
        self.validate_data[edit] = (osp.isdir, msg)
        browse_btn = QPushButton(get_std_icon('DirOpenIcon'), "", self)
        browse_btn.setToolTip(_("Select directory"))
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
        basedir = to_text_string(edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd()
        title = _("Select directory")
        directory = getexistingdirectory(self, title, basedir)
        if directory:
            edit.setText(directory)
    
    def create_browsefile(self, text, option, default=NoDefault, tip=None,
                          filters=None):
        widget = self.create_lineedit(text, option, default,
                                      alignment=Qt.Horizontal)
        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break
        msg = _("Invalid file path")
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(get_std_icon('FileIcon'), "", self)
        browse_btn.setToolTip(_("Select file"))
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
        basedir = osp.dirname(to_text_string(edit.text()))
        if not osp.isdir(basedir):
            basedir = getcwd()
        if filters is None:
            filters = _("All files (*)")
        title = _("Select file")
        filename, _selfilter = getopenfilename(self, title, basedir, filters)
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
        if step is not None:
            if type(step) is int:
                spinbox = QSpinBox()
            else:
                spinbox = QDoubleSpinBox()
                spinbox.setDecimals(1)
            spinbox.setSingleStep(step)
        else:
            spinbox = QSpinBox()
        if min_ is not None:
            spinbox.setMinimum(min_)
        if max_ is not None:
            spinbox.setMaximum(max_)
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
        cb_bold.setToolTip(_("Bold"))
        cb_italic = QCheckBox()
        cb_italic.setIcon(get_icon("italic.png"))
        cb_italic.setToolTip(_("Italic"))
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
            combobox.addItem(name, to_qvariant(key))
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
        fontlabel = QLabel(_("Font: "))
        fontbox = QFontComboBox()
        if fontfilters is not None:
            fontbox.setFontFilters(fontfilters)
        sizelabel = QLabel("  "+_("Size: "))
        sizebox = QSpinBox()
        sizebox.setRange(7, 100)
        self.fontboxes[(fontbox, sizebox)] = option
        layout = QHBoxLayout()
        for subwidget in (fontlabel, fontbox, sizelabel, sizebox):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        if text is None:
            text = _("Font style")
        group = QGroupBox(text)
        group.setLayout(layout)
        if tip is not None:
            group.setToolTip(tip)
        return group
    
    def create_button(self, text, callback):
        btn = QPushButton(text)
        self.connect(btn, SIGNAL('clicked()'), callback)
        self.connect(btn, SIGNAL('clicked()'),
                     lambda opt='': self.has_been_modified(opt))
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
    """Config page that maintains reference to main Spyder window
       and allows to specify page name and icon declaratively
    """
    CONF_SECTION = None

    NAME = None    # configuration page name, e.g. _("General")
    ICON = None    # name of icon resource (24x24)

    def __init__(self, parent, main):
        SpyderConfigPage.__init__(self, parent)
        self.main = main

    def get_name(self):
        """Configuration page name"""
        return self.NAME
    
    def get_icon(self):
        """Loads page icon named by self.ICON"""
        return get_icon(self.ICON)

    def apply_settings(self, options):
        raise NotImplementedError


class MainConfigPage(GeneralConfigPage):
    CONF_SECTION = "main"
    
    NAME = _("General")
    ICON = "genprefs.png"
    
    def setup_page(self):
        newcb = self.create_checkbox

        # --- Interface
        interface_group = QGroupBox(_("Interface"))
        styles = [str(txt) for txt in list(QStyleFactory.keys())]
        # Don't offer users the possibility to change to a different
        # style in Gtk-based desktops
        # Fixes Issue 2036
        if is_gtk_desktop() and ('GTK+' in styles):
            styles = ['GTK+']
        choices = list(zip(styles, [style.lower() for style in styles]))
        style_combo = self.create_combobox(_('Qt windows style'), choices,
                                           'windows_style',
                                           default=self.main.default_style)

        single_instance_box = newcb(_("Use a single instance"),
                                    'single_instance',
                                    tip=_("Set this to open external<br> "
                                          "Python files in an already running "
                                          "instance (Requires a restart)"))
        vertdock_box = newcb(_("Vertical dockwidget title bars"),
                             'vertical_dockwidget_titlebars')
        verttabs_box = newcb(_("Vertical dockwidget tabs"),
                             'vertical_tabs')
        animated_box = newcb(_("Animated toolbars and dockwidgets"),
                             'animated_docks')
        tear_off_box = newcb(_("Tear off menus"), 'tear_off_menus',
                             tip=_("Set this to detach any<br> "
                                   "menu from the main window"))
        margin_box = newcb(_("Custom dockwidget margin:"),
                           'use_custom_margin')
        margin_spin = self.create_spinbox("", "pixels", 'custom_margin',
                                          0, 0, 30)
        self.connect(margin_box, SIGNAL("toggled(bool)"),
                     margin_spin.setEnabled)
        margin_spin.setEnabled(self.get_option('use_custom_margin'))
        margins_layout = QHBoxLayout()
        margins_layout.addWidget(margin_box)
        margins_layout.addWidget(margin_spin)

        # Decide if it's possible to activate or not singie instance mode
        if running_in_mac_app():
            self.set_option("single_instance", True)
            single_instance_box.setEnabled(False)
        
        interface_layout = QVBoxLayout()
        interface_layout.addWidget(style_combo)
        interface_layout.addWidget(single_instance_box)
        interface_layout.addWidget(vertdock_box)
        interface_layout.addWidget(verttabs_box)
        interface_layout.addWidget(animated_box)
        interface_layout.addWidget(tear_off_box)
        interface_layout.addLayout(margins_layout)
        interface_group.setLayout(interface_layout)

        # --- Status bar
        sbar_group = QGroupBox(_("Status bar"))
        memory_box = newcb(_("Show memory usage every"), 'memory_usage/enable',
                           tip=self.main.mem_status.toolTip())
        memory_spin = self.create_spinbox("", " ms", 'memory_usage/timeout',
                                          min_=100, max_=1000000, step=100)
        self.connect(memory_box, SIGNAL("toggled(bool)"),
                     memory_spin.setEnabled)
        memory_spin.setEnabled(self.get_option('memory_usage/enable'))
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(memory_box)
        memory_layout.addWidget(memory_spin)
        memory_layout.setEnabled(self.main.mem_status.is_supported())
        cpu_box = newcb(_("Show CPU usage every"), 'cpu_usage/enable',
                        tip=self.main.cpu_status.toolTip())
        cpu_spin = self.create_spinbox("", " ms", 'cpu_usage/timeout',
                                       min_=100, max_=1000000, step=100)
        self.connect(cpu_box, SIGNAL("toggled(bool)"), cpu_spin.setEnabled)
        cpu_spin.setEnabled(self.get_option('cpu_usage/enable'))
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(cpu_box)
        cpu_layout.addWidget(cpu_spin)
        cpu_layout.setEnabled(self.main.cpu_status.is_supported())
        
        sbar_layout = QVBoxLayout()
        sbar_layout.addLayout(memory_layout)
        sbar_layout.addLayout(cpu_layout)
        sbar_group.setLayout(sbar_layout)

        # --- Debugging
        debug_group = QGroupBox(_("Debugging"))
        popup_console_box = newcb(_("Pop up internal console when internal "
                                    "errors appear"),
                                  'show_internal_console_if_traceback')
        
        debug_layout = QVBoxLayout()
        debug_layout.addWidget(popup_console_box)
        debug_group.setLayout(debug_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(interface_group)
        vlayout.addWidget(sbar_group)
        vlayout.addWidget(debug_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
        
    def apply_settings(self, options):
        self.main.apply_settings()


class ColorSchemeConfigPage(GeneralConfigPage):
    CONF_SECTION = "color_schemes"
    
    NAME = _("Syntax coloring")
    ICON = "genprefs.png"
    
    def setup_page(self):
        tabs = QTabWidget()
        names = self.get_option("names")
        names.pop(names.index(CUSTOM_COLOR_SCHEME_NAME))
        names.insert(0, CUSTOM_COLOR_SCHEME_NAME)
        fieldnames = {
                      "background":     _("Background:"),
                      "currentline":    _("Current line:"),
                      "currentcell":    _("Current cell:"),
                      "occurence":      _("Occurence:"),
                      "ctrlclick":      _("Link:"),
                      "sideareas":      _("Side areas:"),
                      "matched_p":      _("Matched parentheses:"),
                      "unmatched_p":    _("Unmatched parentheses:"),
                      "normal":         _("Normal text:"),
                      "keyword":        _("Keyword:"),
                      "builtin":        _("Builtin:"),
                      "definition":     _("Definition:"),
                      "comment":        _("Comment:"),
                      "string":         _("String:"),
                      "number":         _("Number:"),
                      "instance":       _("Instance:"),
                      }
        from spyderlib.widgets.sourcecode import syntaxhighlighters
        assert all([key in fieldnames
                    for key in syntaxhighlighters.COLOR_SCHEME_KEYS])
        for tabname in names:
            cs_group = QGroupBox(_("Color scheme"))
            cs_layout = QGridLayout()
            for row, key in enumerate(syntaxhighlighters.COLOR_SCHEME_KEYS):
                option = "%s/%s" % (tabname, key)
                value = self.get_option(option)
                name = fieldnames[key]
                if is_text_string(value):
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
            if tabname in sh.COLOR_SCHEME_NAMES:
                def_btn = self.create_button(_("Reset to default values"),
                                         lambda: self.reset_to_default(tabname))
                tabs.addTab(self.create_tab(cs_group, def_btn), tabname)
            else:
                tabs.addTab(self.create_tab(cs_group), tabname)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)
        
    @Slot(str)
    def reset_to_default(self, name):
        set_default_color_scheme(name, replace=True)
        self.load_from_conf()
            
    def apply_settings(self, options):
        self.main.editor.apply_plugin_settings(['color_scheme_name'])
        if self.main.historylog is not None:
            self.main.historylog.apply_plugin_settings(['color_scheme_name'])
        if self.main.inspector is not None:
            self.main.inspector.apply_plugin_settings(['color_scheme_name'])
