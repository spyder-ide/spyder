# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Configuration dialog / Preferences"""

import os.path as osp

<<<<<<< HEAD
from spyderlib.baseconfig import _, running_in_mac_app
from spyderlib.start_app import CONF
#from spyderlib.config import CONF
from spyderlib.guiconfig import (CUSTOM_COLOR_SCHEME_NAME,
                                 set_default_color_scheme)
from spyderlib.utils.qthelpers import get_icon, get_std_icon
from spyderlib.userconfig import NoDefault
from spyderlib.widgets.colors import ColorLayout
from spyderlib.widgets.sourcecode import syntaxhighlighters as sh

=======
from spyderlib.qt import API
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
from spyderlib.qt.QtGui import (QWidget, QDialog, QListWidget, QListWidgetItem,
                                QVBoxLayout, QStackedWidget, QListView,
                                QHBoxLayout, QDialogButtonBox, QCheckBox,
                                QMessageBox, QLabel, QLineEdit, QSpinBox,
                                QPushButton, QFontComboBox, QGroupBox,
                                QComboBox, QColor, QGridLayout, QTabWidget,
                                QRadioButton, QButtonGroup, QSplitter,
                                QStyleFactory, QScrollArea, QDoubleSpinBox)
<<<<<<< HEAD
from spyderlib.qt.QtCore import Qt, QSize, SIGNAL, SLOT, Slot
from spyderlib.qt.compat import (to_qvariant, from_qvariant,
                                 getexistingdirectory, getopenfilename)
=======
from spyderlib.qt.QtCore import Qt, QSize, Signal, Slot
from spyderlib.qt.compat import (to_qvariant, from_qvariant,
                                 getexistingdirectory, getopenfilename)
import spyderlib.utils.icon_manager as ima

from spyderlib.config.base import (_, running_in_mac_app, LANGUAGE_CODES,
                                   save_lang_conf, load_lang_conf)
from spyderlib.config.main import CONF
from spyderlib.config.gui import (CUSTOM_COLOR_SCHEME_NAME,
                                  set_default_color_scheme)
from spyderlib.config.user import NoDefault
from spyderlib.widgets.colors import ColorLayout
from spyderlib.widgets.sourcecode import syntaxhighlighters as sh
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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

<<<<<<< HEAD
=======
    # Signals
    apply_button_enabled = Signal(bool)
    show_this_page = Signal()

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.emit(SIGNAL("apply_button_enabled(bool)"), state)
        
=======
        self.apply_button_enabled.emit(state)
    
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def is_valid(self):
        """Return True if all widget contents are valid"""
        raise NotImplementedError
    
    def apply_changes(self):
        """Apply changes callback"""
        if self.is_modified:
            self.save_to_conf()
            if self.apply_callback is not None:
                self.apply_callback()
<<<<<<< HEAD
            self.set_modified(False)
    
=======

            # Since the language cannot be retrieved by CONF and the language
            # is needed before loading CONF, this is an extra method needed to
            # ensure that when changes are applied, they are copied to a
            # specific file storing the language value. This only applies to
            # the main section config.
            if self.CONF_SECTION == u'main':
                self._save_lang()

            for restart_option in self.restart_options:
                if restart_option in self.changed_options:
                    self.prompt_restart_required()
                    break  # Ensure a single popup is displayed
            self.set_modified(False)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def load_from_conf(self):
        """Load settings from configuration file"""
        raise NotImplementedError
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        raise NotImplementedError


class ConfigDialog(QDialog):
    """Spyder configuration ('Preferences') dialog box"""
<<<<<<< HEAD
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        
=======
    
    # Signals
    check_settings = Signal()
    size_change = Signal(QSize)
    
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.main = parent

        # Widgets
        self.pages_widget = QStackedWidget()
        self.contents_widget = QListWidget()
        self.button_reset = QPushButton(_('Reset to defaults'))

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply |
                                QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)

        # Widgets setup
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
<<<<<<< HEAD

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

=======
        self.setWindowTitle(_('Preferences'))
        self.setWindowIcon(ima.icon('configure'))
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(1)
        self.contents_widget.setCurrentRow(0)

        # Layout
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)

        btnlayout = QHBoxLayout()
<<<<<<< HEAD
=======
        btnlayout.addWidget(self.button_reset)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

<<<<<<< HEAD
        self.setWindowTitle(_("Preferences"))
        self.setWindowIcon(get_icon("configure.png"))
        
=======
        # Signals and slots
        self.button_reset.clicked.connect(self.main.reset_spyder)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
                                             self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)

        # Ensures that the config is present on spyder first run
        CONF.set('main', 'interface_language', load_lang_conf())

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        
=======
    
    @Slot()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.connect(self, SIGNAL('check_settings()'), widget.check_settings)
        self.connect(widget, SIGNAL('show_this_page()'),
                     lambda row=self.contents_widget.count():
                     self.contents_widget.setCurrentRow(row))
        self.connect(widget, SIGNAL("apply_button_enabled(bool)"),
                     self.apply_btn.setEnabled)
=======
        self.check_settings.connect(widget.check_settings)
        widget.show_this_page.connect(lambda row=self.contents_widget.count():
                                      self.contents_widget.setCurrentRow(row))
        widget.apply_button_enabled.connect(self.apply_btn.setEnabled)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.emit(SIGNAL('check_settings()'))
=======
        self.check_settings.emit()
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    
    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        QDialog.resizeEvent(self, event)
<<<<<<< HEAD
        self.emit(SIGNAL("size_change(QSize)"), self.size())
=======
        self.size_change.emit(self.size())
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f


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
<<<<<<< HEAD
=======
        self.restart_options = dict()  # Dict to store name and localized text
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
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
=======
            # Checkboxes work differently for PySide and PyQt
            if API == 'pyqt':
                checkbox.clicked.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
            else:
                checkbox.clicked.connect(lambda opt=option:
                                         self.has_been_modified(opt))
        for radiobutton, (option, default) in list(self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default))
            radiobutton.toggled.connect(lambda _foo, opt=option:
                                        self.has_been_modified(opt))
        for lineedit, (option, default) in list(self.lineedits.items()):
            lineedit.setText(self.get_option(option, default))
            lineedit.textChanged.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
        for spinbox, (option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default))
            spinbox.valueChanged.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
            self.connect(combobox, SIGNAL('currentIndexChanged(int)'),
                         lambda _foo, opt=option: self.has_been_modified(opt))
=======
            combobox.currentIndexChanged.connect(lambda _foo, opt=option:
                                                 self.has_been_modified(opt))
            if combobox.restart_required:
                self.restart_options[option] = combobox.label_text

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            font = self.get_font(option)
            fontbox.setCurrentFont(font)
            sizebox.setValue(font.pointSize())
            if option is None:
                property = 'plugin_font'
            else:
                property = option
<<<<<<< HEAD
            self.connect(fontbox, SIGNAL('currentIndexChanged(int)'),
                         lambda _foo, opt=property: self.has_been_modified(opt))
            self.connect(sizebox, SIGNAL('valueChanged(int)'),
                         lambda _foo, opt=property: self.has_been_modified(opt))
=======
            fontbox.currentIndexChanged.connect(lambda _foo, opt=property:
                                                self.has_been_modified(opt))
            sizebox.valueChanged.connect(lambda _foo, opt=property:
                                         self.has_been_modified(opt))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        for clayout, (option, default) in list(self.coloredits.items()):
            property = to_qvariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default))
<<<<<<< HEAD
            self.connect(btn, SIGNAL('clicked()'),
                         lambda opt=option: self.has_been_modified(opt))
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
=======
            btn.clicked.connect(lambda opt=option: self.has_been_modified(opt))
            edit.textChanged.connect(lambda _foo, opt=option:
                                     self.has_been_modified(opt))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        for (clayout, cb_bold, cb_italic
             ), (option, default) in list(self.scedits.items()):
            edit = clayout.lineedit
            btn = clayout.colorbtn
            color, bold, italic = self.get_option(option, default)
            edit.setText(color)
            cb_bold.setChecked(bold)
            cb_italic.setChecked(italic)
<<<<<<< HEAD
            self.connect(btn, SIGNAL('clicked()'),
                         lambda opt=option: self.has_been_modified(opt))
            self.connect(edit, SIGNAL("textChanged(QString)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
            self.connect(cb_bold, SIGNAL("clicked(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
            self.connect(cb_italic, SIGNAL("clicked(bool)"),
                         lambda _foo, opt=option: self.has_been_modified(opt))
    
=======
            btn.clicked.connect(lambda opt=option: self.has_been_modified(opt))
            edit.textChanged.connect(lambda _foo, opt=option:
                                     self.has_been_modified(opt))
            if API == 'pyqt':
                cb_bold.clicked.connect(lambda _foo, opt=option:
                                        self.has_been_modified(opt))
            else:
                cb_bold.clicked.connect(lambda opt=option:
                                        self.has_been_modified(opt))
            if API == 'pyqt':
                cb_italic.clicked.connect(lambda _foo, opt=option:
                                          self.has_been_modified(opt))
            else:
                cb_italic.clicked.connect(lambda opt=option:
                                          self.has_been_modified(opt))

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
    
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
            self.connect(checkbox, SIGNAL("clicked(bool)"), show_message)
=======
            checkbox.clicked.connect(show_message)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
            self.connect(radiobutton, SIGNAL("toggled(bool)"), show_message)
=======
            radiobutton.toggled.connect(show_message)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
=======
        widget.label = label
        widget.textbox = edit 
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        browse_btn = QPushButton(get_std_icon('DirOpenIcon'), "", self)
        browse_btn.setToolTip(_("Select directory"))
        self.connect(browse_btn, SIGNAL("clicked()"),
                     lambda: self.select_directory(edit))
=======
        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(lambda: self.select_directory(edit))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        msg = _("Invalid file path")
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(get_std_icon('FileIcon'), "", self)
        browse_btn.setToolTip(_("Select file"))
        self.connect(browse_btn, SIGNAL("clicked()"),
                     lambda: self.select_file(edit, filters))
=======
        msg = _('Invalid file path')
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(ima.icon('FileIcon'), '', self)
        browse_btn.setToolTip(_("Select file"))
        browse_btn.clicked.connect(lambda: self.select_file(edit, filters))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        if prefix:
            plabel = QLabel(prefix)
=======
        widget = QWidget(self)
        if prefix:
            plabel = QLabel(prefix)
            widget.plabel = plabel
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        else:
            plabel = None
        if suffix:
            slabel = QLabel(suffix)
<<<<<<< HEAD
=======
            widget.slabel = slabel
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        widget = QWidget(self)
=======
        widget.spinbox = spinbox
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        cb_bold.setIcon(get_icon("bold.png"))
        cb_bold.setToolTip(_("Bold"))
        cb_italic = QCheckBox()
        cb_italic.setIcon(get_icon("italic.png"))
=======
        cb_bold.setIcon(ima.icon('bold'))
        cb_bold.setToolTip(_("Bold"))
        cb_italic = QCheckBox()
        cb_italic.setIcon(ima.icon('italic'))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
                        tip=None):
=======
                        tip=None, restart=False):
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        """choices: couples (name, key)"""
        label = QLabel(text)
        combobox = QComboBox()
        if tip is not None:
            combobox.setToolTip(tip)
        for name, key in choices:
            combobox.addItem(name, to_qvariant(key))
        self.comboboxes[combobox] = (option, default)
        layout = QHBoxLayout()
<<<<<<< HEAD
        for subwidget in (label, combobox):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
=======
        layout.addWidget(label)
        layout.addWidget(combobox)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.label = label
        widget.combobox = combobox
        widget.setLayout(layout)
        combobox.restart_required = restart
        combobox.label_text = text
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        self.connect(btn, SIGNAL('clicked()'), callback)
        self.connect(btn, SIGNAL('clicked()'),
                     lambda opt='': self.has_been_modified(opt))
=======
        btn.clicked.connect(callback)
        btn.clicked.connect(lambda opt='': self.has_been_modified(opt))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
<<<<<<< HEAD
        return get_icon(self.ICON)
=======
        return self.ICON
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

    def apply_settings(self, options):
        raise NotImplementedError

<<<<<<< HEAD
=======
    def prompt_restart_required(self):
        """Prompt the user with a request to restart."""
        restart_opts = self.restart_options
        changed_opts = self.changed_options
        options = [restart_opts[o] for o in changed_opts if o in restart_opts]

        if len(options) == 1:
            msg_start = _("Spyder needs to restart to change the following "
                          "setting:")
        else:
            msg_start = _("Spyder needs to restart to change the following "
                          "settings:")
        msg_end = _("Do you wish to restart now?")

        msg_options = ""
        for option in options:
            msg_options += "<li>{0}</li>".format(option)

        msg_title = _("Information")
        msg = "{0}<ul>{1}</ul><br>{2}".format(msg_start, msg_options, msg_end)
        answer = QMessageBox.information(self, msg_title, msg,
                                         QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.restart()

    def restart(self):
        """Restart Spyder."""
        self.main.restart()

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

class MainConfigPage(GeneralConfigPage):
    CONF_SECTION = "main"
    
    NAME = _("General")
<<<<<<< HEAD
    ICON = "genprefs.png"
    
=======
    ICON = ima.icon('genprefs')

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def setup_page(self):
        newcb = self.create_checkbox

        # --- Interface
        interface_group = QGroupBox(_("Interface"))
        styles = [str(txt) for txt in list(QStyleFactory.keys())]
        choices = list(zip(styles, [style.lower() for style in styles]))
        style_combo = self.create_combobox(_('Qt windows style'), choices,
                                           'windows_style',
                                           default=self.main.default_style)

<<<<<<< HEAD
=======
        themes = ['Spyder 2', 'Spyder 3']
        icon_choices = list(zip(themes, [theme.lower() for theme in themes]))
        icons_combo = self.create_combobox(_('Icon theme'), icon_choices,
                                           'icon_theme', restart=True)

        languages = LANGUAGE_CODES.items()
        language_choices = sorted([(val, key) for key, val in languages])
        language_combo = self.create_combobox(_('Language'), language_choices,
                                              'interface_language',
                                              restart=True)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        single_instance_box = newcb(_("Use a single instance"),
                                    'single_instance',
                                    tip=_("Set this to open external<br> "
                                          "Python files in an already running "
                                          "instance (Requires a restart)"))
<<<<<<< HEAD
        vertdock_box = newcb(_("Vertical dockwidget title bars"),
                             'vertical_dockwidget_titlebars')
        verttabs_box = newcb(_("Vertical dockwidget tabs"),
                             'vertical_tabs')
        animated_box = newcb(_("Animated toolbars and dockwidgets"),
=======
        vertdock_box = newcb(_("Vertical title bars in panes"),
                             'vertical_dockwidget_titlebars')
        verttabs_box = newcb(_("Vertical tabs in panes"),
                             'vertical_tabs')
        animated_box = newcb(_("Animated toolbars and panes"),
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
                             'animated_docks')
        tear_off_box = newcb(_("Tear off menus"), 'tear_off_menus',
                             tip=_("Set this to detach any<br> "
                                   "menu from the main window"))
<<<<<<< HEAD
        margin_box = newcb(_("Custom dockwidget margin:"),
                           'use_custom_margin')
        margin_spin = self.create_spinbox("", "pixels", 'custom_margin',
                                          0, 0, 30)
        self.connect(margin_box, SIGNAL("toggled(bool)"),
                     margin_spin.setEnabled)
=======
        margin_box = newcb(_("Custom margin for panes:"),
                           'use_custom_margin')
        margin_spin = self.create_spinbox("", "pixels", 'custom_margin',
                                          0, 0, 30)
        margin_box.toggled.connect(margin_spin.setEnabled)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        margin_spin.setEnabled(self.get_option('use_custom_margin'))
        margins_layout = QHBoxLayout()
        margins_layout.addWidget(margin_box)
        margins_layout.addWidget(margin_spin)
<<<<<<< HEAD

        # Decide if it's possible to activate or not singie instance mode
        if running_in_mac_app():
            self.set_option("single_instance", True)
            single_instance_box.setEnabled(False)
        
        interface_layout = QVBoxLayout()
        interface_layout.addWidget(style_combo)
=======
        prompt_box = newcb(_("Prompt when exiting"), 'prompt_on_exit')

        # Decide if it's possible to activate or not single instance mode
        if running_in_mac_app():
            self.set_option("single_instance", True)
            single_instance_box.setEnabled(False)

        # Layout interface
        comboboxes_layout = QHBoxLayout()
        cbs_layout = QGridLayout()
        cbs_layout.addWidget(style_combo.label, 0, 0)
        cbs_layout.addWidget(style_combo.combobox, 0, 1)
        cbs_layout.addWidget(icons_combo.label, 1, 0)
        cbs_layout.addWidget(icons_combo.combobox, 1, 1)
        cbs_layout.addWidget(language_combo.label, 2, 0)
        cbs_layout.addWidget(language_combo.combobox, 2, 1)
        comboboxes_layout.addLayout(cbs_layout)
        comboboxes_layout.addStretch(1)
        
        interface_layout = QVBoxLayout()
        interface_layout.addLayout(comboboxes_layout)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        interface_layout.addWidget(single_instance_box)
        interface_layout.addWidget(vertdock_box)
        interface_layout.addWidget(verttabs_box)
        interface_layout.addWidget(animated_box)
        interface_layout.addWidget(tear_off_box)
        interface_layout.addLayout(margins_layout)
<<<<<<< HEAD
=======
        interface_layout.addWidget(prompt_box)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        interface_group.setLayout(interface_layout)

        # --- Status bar
        sbar_group = QGroupBox(_("Status bar"))
<<<<<<< HEAD
=======
        show_status_bar = newcb(_("Show status bar"), 'show_status_bar')

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        memory_box = newcb(_("Show memory usage every"), 'memory_usage/enable',
                           tip=self.main.mem_status.toolTip())
        memory_spin = self.create_spinbox("", " ms", 'memory_usage/timeout',
                                          min_=100, max_=1000000, step=100)
<<<<<<< HEAD
        self.connect(memory_box, SIGNAL("toggled(bool)"),
                     memory_spin.setEnabled)
        memory_spin.setEnabled(self.get_option('memory_usage/enable'))
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(memory_box)
        memory_layout.addWidget(memory_spin)
        memory_layout.setEnabled(self.main.mem_status.is_supported())
=======
        memory_box.toggled.connect(memory_spin.setEnabled)
        memory_spin.setEnabled(self.get_option('memory_usage/enable'))
        memory_box.setEnabled(self.main.mem_status.is_supported())
        memory_spin.setEnabled(self.main.mem_status.is_supported())

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        cpu_box = newcb(_("Show CPU usage every"), 'cpu_usage/enable',
                        tip=self.main.cpu_status.toolTip())
        cpu_spin = self.create_spinbox("", " ms", 'cpu_usage/timeout',
                                       min_=100, max_=1000000, step=100)
<<<<<<< HEAD
        self.connect(cpu_box, SIGNAL("toggled(bool)"), cpu_spin.setEnabled)
        cpu_spin.setEnabled(self.get_option('cpu_usage/enable'))
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(cpu_box)
        cpu_layout.addWidget(cpu_spin)
        cpu_layout.setEnabled(self.main.cpu_status.is_supported())
        
        sbar_layout = QVBoxLayout()
        sbar_layout.addLayout(memory_layout)
        sbar_layout.addLayout(cpu_layout)
=======
        cpu_box.toggled.connect(cpu_spin.setEnabled)
        cpu_spin.setEnabled(self.get_option('cpu_usage/enable'))

        cpu_box.setEnabled(self.main.cpu_status.is_supported())
        cpu_spin.setEnabled(self.main.cpu_status.is_supported())
        
        status_bar_o = self.get_option('show_status_bar')
        show_status_bar.toggled.connect(memory_box.setEnabled)
        show_status_bar.toggled.connect(memory_spin.setEnabled)
        show_status_bar.toggled.connect(cpu_box.setEnabled)
        show_status_bar.toggled.connect(cpu_spin.setEnabled)
        memory_box.setEnabled(status_bar_o)
        memory_spin.setEnabled(status_bar_o)
        cpu_box.setEnabled(status_bar_o)
        cpu_spin.setEnabled(status_bar_o)

        # Layout status bar
        cpu_memory_layout = QGridLayout()
        cpu_memory_layout.addWidget(memory_box, 0, 0)
        cpu_memory_layout.addWidget(memory_spin, 0, 1)
        cpu_memory_layout.addWidget(cpu_box, 1, 0)
        cpu_memory_layout.addWidget(cpu_spin, 1, 1)

        sbar_layout = QVBoxLayout()
        sbar_layout.addWidget(show_status_bar)
        sbar_layout.addLayout(cpu_memory_layout)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        sbar_group.setLayout(sbar_layout)

        # --- Debugging
        debug_group = QGroupBox(_("Debugging"))
        popup_console_box = newcb(_("Pop up internal console when internal "
                                    "errors appear"),
                                  'show_internal_console_if_traceback')
        
        debug_layout = QVBoxLayout()
        debug_layout.addWidget(popup_console_box)
        debug_group.setLayout(debug_layout)
<<<<<<< HEAD
=======

        # --- Spyder updates
        update_group = QGroupBox(_("Updates"))
        check_updates = newcb(_("Check for updates on startup"),
                              'check_updates_on_startup')
        update_layout = QVBoxLayout()
        update_layout.addWidget(check_updates)
        update_group.setLayout(update_layout)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(interface_group)
        vlayout.addWidget(sbar_group)
        vlayout.addWidget(debug_group)
<<<<<<< HEAD
        vlayout.addStretch(1)
        self.setLayout(vlayout)
        
    def apply_settings(self, options):
        self.main.apply_settings()

=======
        vlayout.addWidget(update_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def apply_settings(self, options):
        self.main.apply_settings()

    def _save_lang(self):
        """
        Get selected language setting and save to language configuration file.
        """
        for combobox, (option, _default) in list(self.comboboxes.items()):
            if option == 'interface_language':
                data = combobox.itemData(combobox.currentIndex())
                value = from_qvariant(data, to_text_string)
                break
        save_lang_conf(value)
        self.set_option('interface_language', value)

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

class ColorSchemeConfigPage(GeneralConfigPage):
    CONF_SECTION = "color_schemes"
    
    NAME = _("Syntax coloring")
<<<<<<< HEAD
    ICON = "genprefs.png"
=======
    ICON = ima.icon('eyedropper')
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    
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
