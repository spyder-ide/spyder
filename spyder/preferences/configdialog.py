# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Configuration dialog / Preferences.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy import API
from qtpy.compat import (getexistingdirectory, getopenfilename, from_qvariant,
                         to_qvariant)
from qtpy.QtCore import QSize, Qt, Signal, Slot, QRegExp
from qtpy.QtGui import QColor, QRegExpValidator
from qtpy.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                            QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                            QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                            QLineEdit, QListView, QListWidget, QListWidgetItem,
                            QMessageBox, QPushButton, QRadioButton,
                            QScrollArea, QSpinBox, QSplitter, QStackedWidget,
                            QStyleFactory, QTabWidget, QVBoxLayout, QWidget,
                            QApplication)

# Local imports
from spyder.config.base import (_, LANGUAGE_CODES, load_lang_conf,
                                running_in_mac_app, save_lang_conf)
from spyder.config.gui import get_font, set_font
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from spyder.config.utils import is_gtk_desktop
from spyder.py3compat import to_text_string, is_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import syntaxhighlighters
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.colors import ColorLayout
from spyder.widgets.comboboxes import FileComboBox
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.config.gui import is_dark_font_color


HDPI_QT_PAGE = "https://doc.qt.io/qt-5/highdpi.html"


class ConfigAccessMixin(object):
    """Namespace for methods that access config storage"""
    CONF_SECTION = None

    def set_option(self, option, value):
        CONF.set(self.CONF_SECTION, option, value)

    def get_option(self, option, default=NoDefault):
        return CONF.get(self.CONF_SECTION, option, default)


class ConfigPage(QWidget):
    """Base class for configuration page in Preferences"""

    # Signals
    apply_button_enabled = Signal(bool)
    show_this_page = Signal()

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
        self.apply_button_enabled.emit(state)
    
    def is_valid(self):
        """Return True if all widget contents are valid"""
        raise NotImplementedError
    
    def apply_changes(self):
        """Apply changes callback"""
        if self.is_modified:
            self.save_to_conf()
            if self.apply_callback is not None:
                self.apply_callback()

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

    def load_from_conf(self):
        """Load settings from configuration file"""
        raise NotImplementedError
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        raise NotImplementedError


class ConfigDialog(QDialog):
    """Spyder configuration ('Preferences') dialog box"""
    
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
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(_('Preferences'))
        self.setWindowIcon(ima.icon('configure'))
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(1)
        self.contents_widget.setCurrentRow(0)

        # Layout
        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)

        btnlayout = QHBoxLayout()
        btnlayout.addWidget(self.button_reset)
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        # Signals and slots
        if self.main:
            self.button_reset.clicked.connect(self.main.reset_spyder)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
                                             self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)

        # Ensures that the config is present on spyder first run
        CONF.set('main', 'interface_language', load_lang_conf())

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
    
    @Slot()
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
        self.check_settings.connect(widget.check_settings)
        widget.show_this_page.connect(lambda row=self.contents_widget.count():
                                      self.contents_widget.setCurrentRow(row))
        widget.apply_button_enabled.connect(self.apply_btn.setEnabled)
        scrollarea = QScrollArea(self)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.pages_widget.addWidget(scrollarea)
        item = QListWidgetItem(self.contents_widget)
        try:
            item.setIcon(widget.get_icon())
        except TypeError:
            pass
        item.setText(widget.get_name())
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        item.setSizeHint(QSize(0, 25))
        
    def check_all_settings(self):
        """This method is called to check all configuration page settings
        after configuration dialog has been shown"""
        self.check_settings.emit()
    
    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        QDialog.resizeEvent(self, event)
        self.size_change.emit(self.size())


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
        self.restart_options = dict()  # Dict to store name and localized text
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
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                checkbox.clicked.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
            else:
                checkbox.clicked.connect(lambda opt=option:
                                         self.has_been_modified(opt))
        for radiobutton, (option, default) in list(self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default))
            radiobutton.toggled.connect(lambda _foo, opt=option:
                                        self.has_been_modified(opt))
            if radiobutton.restart_required:
                self.restart_options[option] = radiobutton.label_text
        for lineedit, (option, default) in list(self.lineedits.items()):
            lineedit.setText(self.get_option(option, default))
            lineedit.textChanged.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
            if lineedit.restart_required:
                self.restart_options[option] = lineedit.label_text
        for spinbox, (option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default))
            spinbox.valueChanged.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
        for combobox, (option, default) in list(self.comboboxes.items()):
            value = self.get_option(option, default)
            for index in range(combobox.count()):
                data = from_qvariant(combobox.itemData(index), to_text_string)
                # For PyQt API v2, it is necessary to convert `data` to
                # unicode in case the original type was not a string, like an
                # integer for example (see qtpy.compat.from_qvariant):
                if to_text_string(data) == to_text_string(value):
                    break
            else:
                if combobox.count() == 0:
                    index = None
            if index:
                combobox.setCurrentIndex(index)
            combobox.currentIndexChanged.connect(lambda _foo, opt=option:
                                                 self.has_been_modified(opt))
            if combobox.restart_required:
                self.restart_options[option] = combobox.label_text

        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            font = self.get_font(option)
            fontbox.setCurrentFont(font)
            sizebox.setValue(font.pointSize())
            if option is None:
                property = 'plugin_font'
            else:
                property = option
            fontbox.currentIndexChanged.connect(lambda _foo, opt=property:
                                                self.has_been_modified(opt))
            sizebox.valueChanged.connect(lambda _foo, opt=property:
                                         self.has_been_modified(opt))
        for clayout, (option, default) in list(self.coloredits.items()):
            property = to_qvariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default))
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                btn.clicked.connect(lambda _foo, opt=option:
                                    self.has_been_modified(opt))
            else:
                btn.clicked.connect(lambda opt=option:
                                    self.has_been_modified(opt))
            edit.textChanged.connect(lambda _foo, opt=option:
                                     self.has_been_modified(opt))
        for (clayout, cb_bold, cb_italic
             ), (option, default) in list(self.scedits.items()):
            edit = clayout.lineedit
            btn = clayout.colorbtn
            color, bold, italic = self.get_option(option, default)
            edit.setText(color)
            cb_bold.setChecked(bold)
            cb_italic.setChecked(italic)
            edit.textChanged.connect(lambda _foo, opt=option:
                                     self.has_been_modified(opt))
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                btn.clicked.connect(lambda _foo, opt=option:
                                    self.has_been_modified(opt))
                cb_bold.clicked.connect(lambda _foo, opt=option:
                                        self.has_been_modified(opt))
                cb_italic.clicked.connect(lambda _foo, opt=option:
                                          self.has_been_modified(opt))
            else:
                btn.clicked.connect(lambda opt=option:
                                    self.has_been_modified(opt))
                cb_bold.clicked.connect(lambda opt=option:
                                        self.has_been_modified(opt))
                cb_italic.clicked.connect(lambda opt=option:
                                          self.has_been_modified(opt))

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
            def show_message(is_checked=False):
                if is_checked or not msg_if_enabled:
                    if msg_warning is not None:
                        QMessageBox.warning(self, self.get_name(),
                                            msg_warning, QMessageBox.Ok)
                    if msg_info is not None:
                        QMessageBox.information(self, self.get_name(),
                                                msg_info, QMessageBox.Ok)
            checkbox.clicked.connect(show_message)
        return checkbox
    
    def create_radiobutton(self, text, option, default=NoDefault,
                           tip=None, msg_warning=None, msg_info=None,
                           msg_if_enabled=False, button_group=None,
                           restart=False):
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
            radiobutton.toggled.connect(show_message)
        radiobutton.restart_required = restart
        radiobutton.label_text = text
        return radiobutton
    
    def create_lineedit(self, text, option, default=NoDefault,
                        tip=None, alignment=Qt.Vertical, regex=None, 
                        restart=False):
        label = QLabel(text)
        label.setWordWrap(True)
        edit = QLineEdit()
        layout = QVBoxLayout() if alignment == Qt.Vertical else QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip:
            edit.setToolTip(tip)
        if regex:
            edit.setValidator(QRegExpValidator(QRegExp(regex)))
        self.lineedits[edit] = (option, default)
        widget = QWidget(self)
        widget.label = label
        widget.textbox = edit 
        widget.setLayout(layout)
        edit.restart_required = restart
        edit.label_text = text
        return widget
    
    def create_browsedir(self, text, option, default=NoDefault, tip=None):
        widget = self.create_lineedit(text, option, default,
                                      alignment=Qt.Horizontal)
        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break
        msg = _("Invalid directory path")
        self.validate_data[edit] = (osp.isdir, msg)
        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(lambda: self.select_directory(edit))
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
            basedir = getcwd_or_home()
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
        msg = _('Invalid file path')
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(ima.icon('FileIcon'), '', self)
        browse_btn.setToolTip(_("Select file"))
        browse_btn.clicked.connect(lambda: self.select_file(edit, filters))
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
            basedir = getcwd_or_home()
        if filters is None:
            filters = _("All files (*)")
        title = _("Select file")
        filename, _selfilter = getopenfilename(self, title, basedir, filters)
        if filename:
            edit.setText(filename)
    
    def create_spinbox(self, prefix, suffix, option, default=NoDefault,
                       min_=None, max_=None, step=None, tip=None):
        widget = QWidget(self)
        if prefix:
            plabel = QLabel(prefix)
            widget.plabel = plabel
        else:
            plabel = None
        if suffix:
            slabel = QLabel(suffix)
            widget.slabel = slabel
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
        widget.spinbox = spinbox
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
        cb_bold.setIcon(ima.icon('bold'))
        cb_bold.setToolTip(_("Bold"))
        cb_italic = QCheckBox()
        cb_italic.setIcon(ima.icon('italic'))
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
                        tip=None, restart=False):
        """choices: couples (name, key)"""
        label = QLabel(text)
        combobox = QComboBox()
        if tip is not None:
            combobox.setToolTip(tip)
        for name, key in choices:
            if not (name is None and key is None):
                combobox.addItem(name, to_qvariant(key))
        # Insert separators
        count = 0
        for index, item in enumerate(choices):
            name, key = item
            if name is None and key is None:
                combobox.insertSeparator(index + count)
                count += 1
        self.comboboxes[combobox] = (option, default)
        layout = QHBoxLayout()
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
        return widget

    def create_file_combobox(self, text, choices, option, default=NoDefault,
                             tip=None, restart=False, filters=None,
                             adjust_to_contents=False,
                             default_line_edit=False):
        """choices: couples (name, key)"""
        combobox = FileComboBox(self, adjust_to_contents=adjust_to_contents,
                                default_line_edit=default_line_edit)
        combobox.restart_required = restart
        combobox.label_text = text
        edit = combobox.lineEdit()
        edit.label_text = text
        edit.restart_required = restart
        self.lineedits[edit] = (option, default)

        if tip is not None:
            combobox.setToolTip(tip)
        combobox.addItems(choices)
        self.comboboxes[combobox] = (option, default)

        msg = _('Invalid file path')
        self.validate_data[edit] = (osp.isfile, msg)
        browse_btn = QPushButton(ima.icon('FileIcon'), '', self)
        browse_btn.setToolTip(_("Select file"))
        browse_btn.clicked.connect(lambda: self.select_file(edit, filters))

        layout = QGridLayout()
        layout.addWidget(combobox, 0, 0, 0, 9)
        layout.addWidget(browse_btn, 0, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.combobox = combobox
        widget.browse_btn = browse_btn
        widget.setLayout(layout)

        return widget

    def create_fontgroup(self, option=None, text=None, title=None,
                         tip=None, fontfilters=None, without_group=False):
        """Option=None -> setting plugin font"""

        if title:
            fontlabel = QLabel(title)
        else:
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

        widget = QWidget(self)
        widget.fontlabel = fontlabel
        widget.sizelabel = sizelabel        
        widget.fontbox = fontbox
        widget.sizebox = sizebox
        widget.setLayout(layout)

        if not without_group:
            if text is None:
                text = _("Font style")

            group = QGroupBox(text)
            group.setLayout(layout)

            if tip is not None:
                group.setToolTip(tip)

            return group
        else:
            return widget

    def create_button(self, text, callback):
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.clicked.connect(lambda checked=False, opt='': self.has_been_modified(opt))
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
        return self.ICON

    def apply_settings(self, options):
        raise NotImplementedError

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

        msg_options = u""
        for option in options:
            msg_options += u"<li>{0}</li>".format(option)

        msg_title = _("Information")
        msg = u"{0}<ul>{1}</ul><br>{2}".format(msg_start, msg_options, msg_end)
        answer = QMessageBox.information(self, msg_title, msg,
                                         QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.restart()

    def restart(self):
        """Restart Spyder."""
        self.main.restart()


class MainConfigPage(GeneralConfigPage):
    CONF_SECTION = "main"
    NAME = _("General")

    def setup_page(self):
        self.ICON = ima.icon('genprefs')
        newcb = self.create_checkbox

        # --- Interface
        general_group = QGroupBox(_("General"))

        languages = LANGUAGE_CODES.items()
        language_choices = sorted([(val, key) for key, val in languages])
        language_combo = self.create_combobox(_('Language:'),
                                              language_choices,
                                              'interface_language',
                                              restart=True)

        opengl_options = ['Automatic', 'Desktop', 'Software', 'GLES']
        opengl_choices = list(zip(opengl_options,
                                  [c.lower() for c in opengl_options]))
        opengl_combo = self.create_combobox(_('Rendering engine:'),
                                            opengl_choices,
                                            'opengl',
                                            restart=True)

        single_instance_box = newcb(_("Use a single instance"),
                                    'single_instance',
                                    tip=_("Set this to open external<br> "
                                          "Python files in an already running "
                                          "instance (Requires a restart)"))

        prompt_box = newcb(_("Prompt when exiting"), 'prompt_on_exit')
        popup_console_box = newcb(_("Show internal Spyder errors to report "
                                    "them to Github"), 'show_internal_errors')
        check_updates = newcb(_("Check for updates on startup"),
                              'check_updates_on_startup')

        # Decide if it's possible to activate or not single instance mode
        if running_in_mac_app():
            self.set_option("single_instance", True)
            single_instance_box.setEnabled(False)

        comboboxes_advanced_layout = QHBoxLayout()
        cbs_adv_grid = QGridLayout()
        cbs_adv_grid.addWidget(language_combo.label, 0, 0)
        cbs_adv_grid.addWidget(language_combo.combobox, 0, 1)
        cbs_adv_grid.addWidget(opengl_combo.label, 1, 0)
        cbs_adv_grid.addWidget(opengl_combo.combobox, 1, 1)
        comboboxes_advanced_layout.addLayout(cbs_adv_grid)
        comboboxes_advanced_layout.addStretch(1)

        general_layout = QVBoxLayout()
        general_layout.addLayout(comboboxes_advanced_layout)
        general_layout.addWidget(single_instance_box)
        general_layout.addWidget(prompt_box)
        general_layout.addWidget(popup_console_box)
        general_layout.addWidget(check_updates)
        general_group.setLayout(general_layout)

        # --- Theme
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

        themes = ['Spyder 2', 'Spyder 3']
        icon_choices = list(zip(themes, [theme.lower() for theme in themes]))
        icons_combo = self.create_combobox(_('Icon theme'), icon_choices,
                                           'icon_theme', restart=True)

        vertdock_box = newcb(_("Vertical title bars in panes"),
                             'vertical_dockwidget_titlebars')
        verttabs_box = newcb(_("Vertical tabs in panes"),
                             'vertical_tabs')
        animated_box = newcb(_("Animated toolbars and panes"),
                             'animated_docks')
        tear_off_box = newcb(_("Tear off menus"), 'tear_off_menus',
                             tip=_("Set this to detach any<br> "
                                   "menu from the main window"))
        margin_box = newcb(_("Custom margin for panes:"),
                           'use_custom_margin')
        margin_spin = self.create_spinbox("", _("pixels"), 'custom_margin',
                                          0, 0, 30)
        margin_box.toggled.connect(margin_spin.spinbox.setEnabled)
        margin_box.toggled.connect(margin_spin.slabel.setEnabled)
        margin_spin.spinbox.setEnabled(self.get_option('use_custom_margin'))
        margin_spin.slabel.setEnabled(self.get_option('use_custom_margin'))
        
        cursor_box = newcb(_("Cursor blinking:"),
                           'use_custom_cursor_blinking')
        cursor_spin = self.create_spinbox("", _("ms"), 'custom_cursor_blinking',
                                          default = QApplication.cursorFlashTime(),
                                          min_=0, max_=5000, step=100)
        cursor_box.toggled.connect(cursor_spin.spinbox.setEnabled)
        cursor_box.toggled.connect(cursor_spin.slabel.setEnabled)
        cursor_spin.spinbox.setEnabled(
                self.get_option('use_custom_cursor_blinking'))
        cursor_spin.slabel.setEnabled(
                self.get_option('use_custom_cursor_blinking'))
        
        margins_cursor_layout = QGridLayout()
        margins_cursor_layout.addWidget(margin_box, 0, 0)
        margins_cursor_layout.addWidget(margin_spin.spinbox, 0, 1)
        margins_cursor_layout.addWidget(margin_spin.slabel, 0, 2)        
        margins_cursor_layout.addWidget(cursor_box, 1, 0)
        margins_cursor_layout.addWidget(cursor_spin.spinbox, 1, 1)
        margins_cursor_layout.addWidget(cursor_spin.slabel, 1, 2)
        margins_cursor_layout.setColumnStretch(2, 100)

        # Layout interface
        comboboxes_layout = QHBoxLayout()
        cbs_layout = QGridLayout()
        cbs_layout.addWidget(style_combo.label, 0, 0)
        cbs_layout.addWidget(style_combo.combobox, 0, 1)
        cbs_layout.addWidget(icons_combo.label, 1, 0)
        cbs_layout.addWidget(icons_combo.combobox, 1, 1)
        comboboxes_layout.addLayout(cbs_layout)
        comboboxes_layout.addStretch(1)
        
        interface_layout = QVBoxLayout()
        interface_layout.addLayout(comboboxes_layout)
        interface_layout.addWidget(vertdock_box)
        interface_layout.addWidget(verttabs_box)
        interface_layout.addWidget(animated_box)
        interface_layout.addWidget(tear_off_box)
        interface_layout.addLayout(margins_cursor_layout)
        interface_group.setLayout(interface_layout)

        # --- Status bar
        sbar_group = QGroupBox(_("Status bar"))
        show_status_bar = newcb(_("Show status bar"), 'show_status_bar')

        memory_box = newcb(_("Show memory usage every"), 'memory_usage/enable',
                           tip=self.main.mem_status.toolTip())
        memory_spin = self.create_spinbox("", _(" ms"), 'memory_usage/timeout',
                                          min_=100, max_=1000000, step=100)
        memory_box.toggled.connect(memory_spin.setEnabled)
        memory_spin.setEnabled(self.get_option('memory_usage/enable'))
        memory_box.setEnabled(self.main.mem_status.is_supported())
        memory_spin.setEnabled(self.main.mem_status.is_supported())

        cpu_box = newcb(_("Show CPU usage every"), 'cpu_usage/enable',
                        tip=self.main.cpu_status.toolTip())
        cpu_spin = self.create_spinbox("", _(" ms"), 'cpu_usage/timeout',
                                       min_=100, max_=1000000, step=100)
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
        sbar_group.setLayout(sbar_layout)

        # --- Screen resolution Group (hidpi)
        screen_resolution_group = QGroupBox(_("Screen resolution"))
        screen_resolution_bg = QButtonGroup(screen_resolution_group)
        screen_resolution_label = QLabel(_("Configuration for high DPI "
                                           "screens<br><br>"
                                           "Please see "
                                           "<a href=\"{0}\">{0}</a><> "
                                           "for more information about "
                                           "these options (in "
                                           "English).").format(HDPI_QT_PAGE))
        screen_resolution_label.setWordWrap(True)

        normal_radio = self.create_radiobutton(
                                _("Normal"),
                                'normal_screen_resolution',
                                button_group=screen_resolution_bg)
        auto_scale_radio = self.create_radiobutton(
                                _("Enable auto high DPI scaling"),
                                'high_dpi_scaling',
                                button_group=screen_resolution_bg,
                                tip=_("Set this for high DPI displays"),
                                restart=True)

        custom_scaling_radio = self.create_radiobutton(
                                _("Set a custom high DPI scaling"),
                                'high_dpi_custom_scale_factor',
                                button_group=screen_resolution_bg,
                                tip=_("Set this for high DPI displays when "
                                      "auto scaling does not work"),
                                restart=True)

        custom_scaling_edit = self.create_lineedit("",
                                'high_dpi_custom_scale_factors',
                                tip=_("Enter values for different screens "
                                      "separated by semicolons ';', "
                                      "float values are supported"),
                                alignment=Qt.Horizontal,
                                regex="[0-9]+(?:\.[0-9]*)(;[0-9]+(?:\.[0-9]*))*",
                                restart=True)

        normal_radio.toggled.connect(custom_scaling_edit.setDisabled)
        auto_scale_radio.toggled.connect(custom_scaling_edit.setDisabled)
        custom_scaling_radio.toggled.connect(custom_scaling_edit.setEnabled)

        # Layout Screen resolution
        screen_resolution_layout = QVBoxLayout()
        screen_resolution_layout.addWidget(screen_resolution_label)

        screen_resolution_inner_layout = QGridLayout()
        screen_resolution_inner_layout.addWidget(normal_radio, 0, 0)
        screen_resolution_inner_layout.addWidget(auto_scale_radio, 1, 0)
        screen_resolution_inner_layout.addWidget(custom_scaling_radio, 2, 0)
        screen_resolution_inner_layout.addWidget(custom_scaling_edit, 2, 1)

        screen_resolution_layout.addLayout(screen_resolution_inner_layout)
        screen_resolution_group.setLayout(screen_resolution_layout)

        # --- Theme and fonts
        plain_text_font = self.create_fontgroup(
            option='font',
            title=_("Plain text font"),
            fontfilters=QFontComboBox.MonospacedFonts,
            without_group=True)

        rich_text_font = self.create_fontgroup(
            option='rich_font',
            title=_("Rich text font"),
            without_group=True)

        fonts_group = QGroupBox(_("Fonts"))
        fonts_layout = QGridLayout()
        fonts_layout.addWidget(plain_text_font.fontlabel, 0, 0)
        fonts_layout.addWidget(plain_text_font.fontbox, 0, 1)
        fonts_layout.addWidget(plain_text_font.sizelabel, 0, 2)
        fonts_layout.addWidget(plain_text_font.sizebox, 0, 3)
        fonts_layout.addWidget(rich_text_font.fontlabel, 1, 0)
        fonts_layout.addWidget(rich_text_font.fontbox, 1, 1)
        fonts_layout.addWidget(rich_text_font.sizelabel, 1, 2)
        fonts_layout.addWidget(rich_text_font.sizebox, 1, 3)
        fonts_group.setLayout(fonts_layout)

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(fonts_group, screen_resolution_group,
                    interface_group), _("Appearance"))
        tabs.addTab(self.create_tab(general_group, sbar_group),
                    _("Advanced Settings"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)

    def get_font(self, option):
        """Return global font used in Spyder."""
        return get_font(option=option)

    def set_font(self, font, option):
        """Set global font used in Spyder."""
        # Update fonts in all plugins
        set_font(font, option=option)
        plugins = self.main.widgetlist + self.main.thirdparty_plugins
        for plugin in plugins:
            plugin.update_font()

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


class ColorSchemeConfigPage(GeneralConfigPage):
    CONF_SECTION = "color_schemes"
    NAME = _("Syntax coloring")

    def setup_page(self):
        self.ICON = ima.icon('eyedropper')

        names = self.get_option("names")
        try:
            names.pop(names.index(u'Custom'))
        except ValueError:
            pass
        custom_names = self.get_option("custom_names", [])

        # Widgets
        about_label = QLabel(_("Here you can select the color scheme used in "
                               "the Editor and all other Spyder plugins.<br><br>"
                               "You can also edit the color schemes provided "
                               "by Spyder or create your own ones by using "
                               "the options provided below.<br>"))
        edit_button = QPushButton(_("Edit selected"))
        create_button = QPushButton(_("Create new scheme"))
        self.delete_button = QPushButton(_("Delete"))
        self.preview_editor = CodeEditor(self)
        self.stacked_widget = QStackedWidget(self)
        self.reset_button = QPushButton(_("Reset"))
        self.scheme_editor_dialog = SchemeEditor(parent=self,
                                                 stack=self.stacked_widget)

        # Widget setup
        self.scheme_choices_dict = {}
        about_label.setWordWrap(True)
        schemes_combobox_widget = self.create_combobox(_('Scheme:'),
                                                       [('', '')],
                                                       'selected')
        self.schemes_combobox = schemes_combobox_widget.combobox

        color_themes = ['Automatic', 'Light', 'Dark']
        color_theme_choices = list(zip(color_themes,
                                       [color_theme.lower()
                                        for color_theme in color_themes]))
        color_theme_combo = self.create_combobox(_('User interface theme'),
                                                 color_theme_choices,
                                                 'color_theme',
                                                 restart=True)

        # Layouts
        vlayout = QVBoxLayout()

        manage_layout = QVBoxLayout()
        manage_layout.addWidget(about_label)

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(schemes_combobox_widget.label)
        combo_layout.addWidget(schemes_combobox_widget.combobox)

        color_theme_combo_layout = QHBoxLayout()
        color_theme_combo_layout.addWidget(color_theme_combo.label)
        color_theme_combo_layout.addWidget(color_theme_combo.combobox)

        buttons_layout = QVBoxLayout()
        buttons_layout.addLayout(combo_layout)
        buttons_layout.addLayout(color_theme_combo_layout)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(create_button)

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_editor)

        buttons_preview_layout = QHBoxLayout()
        buttons_preview_layout.addLayout(buttons_layout)
        buttons_preview_layout.addLayout(preview_layout)

        manage_layout.addLayout(buttons_preview_layout)
        manage_group = QGroupBox(_("Manage color schemes"))
        manage_group.setLayout(manage_layout)

        vlayout.addWidget(manage_group)
        self.setLayout(vlayout)

        # Signals and slots
        create_button.clicked.connect(self.create_new_scheme)
        edit_button.clicked.connect(self.edit_scheme)
        self.reset_button.clicked.connect(self.reset_to_default)
        self.delete_button.clicked.connect(self.delete_scheme)
        self.schemes_combobox.currentIndexChanged.connect(self.update_preview)
        self.schemes_combobox.currentIndexChanged.connect(self.update_buttons)

        # Setup
        for name in names:
            self.scheme_editor_dialog.add_color_scheme_stack(name)

        for name in custom_names:
            self.scheme_editor_dialog.add_color_scheme_stack(name, custom=True)

        self.update_combobox()
        self.update_preview()

    def apply_settings(self, options):
        self.set_option('selected', self.current_scheme)
        color_scheme = self.get_option('selected')
        color_theme = CONF.get('color_schemes', 'color_theme')
        style_sheet = self.main.styleSheet()
        if ((not is_dark_font_color(color_scheme) and not style_sheet)
                or (is_dark_font_color(color_scheme) and style_sheet)
                and color_theme == 'automatic'):
            self.changed_options.add('color_theme')
        else:
            self.main.editor.apply_plugin_settings(['color_scheme_name'])
            if self.main.ipyconsole is not None:
                self.main.ipyconsole.apply_plugin_settings(
                    ['color_scheme_name'])
            if self.main.historylog is not None:
                self.main.historylog.apply_plugin_settings(
                    ['color_scheme_name'])
            if self.main.help is not None:
                self.main.help.apply_plugin_settings(['color_scheme_name'])
            if 'color_theme' in self.changed_options:
                if ((is_dark_font_color(color_scheme) and not style_sheet) or
                        (not is_dark_font_color(color_scheme) and style_sheet)):
                    self.changed_options.remove('color_theme')

        self.update_combobox()
        self.update_preview()

    # Helpers
    # -------------------------------------------------------------------------
    @property
    def current_scheme_name(self):
        return self.schemes_combobox.currentText()

    @property
    def current_scheme(self):
        return self.scheme_choices_dict[self.current_scheme_name]

    @property
    def current_scheme_index(self):
        return self.schemes_combobox.currentIndex()

    def update_combobox(self):
        """Recreates the combobox contents."""
        index = self.current_scheme_index
        self.schemes_combobox.blockSignals(True)
        names = self.get_option("names")
        try:
            names.pop(names.index(u'Custom'))
        except ValueError:
            pass
        custom_names = self.get_option("custom_names", [])

        # Useful for retrieving the actual data
        for n in names + custom_names:
            self.scheme_choices_dict[self.get_option('{0}/name'.format(n))] = n

        if custom_names:
            choices = names + [None] + custom_names
        else:
            choices = names

        combobox = self.schemes_combobox
        combobox.clear()

        for name in choices:
            if name is None:
                continue
            combobox.addItem(self.get_option('{0}/name'.format(name)), name)

        if custom_names:
            combobox.insertSeparator(len(names))

        self.schemes_combobox.blockSignals(False)
        self.schemes_combobox.setCurrentIndex(index)

    def update_buttons(self):
        """Updates the enable status of delete and reset buttons."""
        current_scheme = self.current_scheme
        names = self.get_option("names")
        try:
            names.pop(names.index(u'Custom'))
        except ValueError:
            pass
        delete_enabled = current_scheme not in names
        self.delete_button.setEnabled(delete_enabled)
        self.reset_button.setEnabled(not delete_enabled)

    def update_preview(self, index=None, scheme_name=None):
        """
        Update the color scheme of the preview editor and adds text.

        Note
        ----
        'index' is needed, because this is triggered by a signal that sends
        the selected index.
        """
        text = ('"""A string"""\n\n'
                '# A comment\n\n'
                '# %% A cell\n\n'
                'class Foo(object):\n'
                '    def __init__(self):\n'
                '        bar = 42\n'
                '        print(bar)\n'
                )
        show_blanks = CONF.get('editor', 'blank_spaces')
        update_scrollbar = CONF.get('editor', 'scroll_past_end')
        if scheme_name is None:
            scheme_name = self.current_scheme
        self.preview_editor.setup_editor(linenumbers=True,
                                         markers=True,
                                         tab_mode=False,
                                         font=get_font(),
                                         show_blanks=show_blanks,
                                         color_scheme=scheme_name,
                                         scroll_past_end=update_scrollbar)
        self.preview_editor.set_text(text)
        self.preview_editor.set_language('Python')

    # Actions
    # -------------------------------------------------------------------------
    def create_new_scheme(self):
        """Creates a new color scheme with a custom name."""
        names = self.get_option('names')
        custom_names = self.get_option('custom_names', [])

        # Get the available number this new color scheme
        counter = len(custom_names) - 1
        custom_index = [int(n.split('-')[-1]) for n in custom_names]
        for i in range(len(custom_names)):
            if custom_index[i] != i:
                counter = i - 1
                break
        custom_name = "custom-{0}".format(counter+1)

        # Add the config settings, based on the current one.
        custom_names.append(custom_name)
        self.set_option('custom_names', custom_names)
        for key in syntaxhighlighters.COLOR_SCHEME_KEYS:
            name = "{0}/{1}".format(custom_name, key)
            default_name = "{0}/{1}".format(self.current_scheme, key)
            option = self.get_option(default_name)
            self.set_option(name, option)
        self.set_option('{0}/name'.format(custom_name), custom_name)

        # Now they need to be loaded! how to make a partial load_from_conf?
        dlg = self.scheme_editor_dialog
        dlg.add_color_scheme_stack(custom_name, custom=True)
        dlg.set_scheme(custom_name)
        self.load_from_conf()

        if dlg.exec_():
            # This is needed to have the custom name updated on the combobox
            name = dlg.get_scheme_name()
            self.set_option('{0}/name'.format(custom_name), name)

            # The +1 is needed because of the separator in the combobox
            index = (names + custom_names).index(custom_name) + 1
            self.update_combobox()
            self.schemes_combobox.setCurrentIndex(index)
        else:
            # Delete the config ....
            custom_names.remove(custom_name)
            self.set_option('custom_names', custom_names)
            dlg.delete_color_scheme_stack(custom_name)

    def edit_scheme(self):
        """Edit current scheme."""
        dlg = self.scheme_editor_dialog
        dlg.set_scheme(self.current_scheme)

        if dlg.exec_():
            # Update temp scheme to reflect instant edits on the preview
            temporal_color_scheme = dlg.get_edited_color_scheme()
            for key in temporal_color_scheme:
                option = "temp/{0}".format(key)
                value = temporal_color_scheme[key]
                self.set_option(option, value)
            self.update_preview(scheme_name='temp')

    def delete_scheme(self):
        """Deletes the currently selected custom color scheme."""
        scheme_name = self.current_scheme

        answer = QMessageBox.warning(self, _("Warning"),
                                           _("Are you sure you want to delete "
                                             "this scheme?"),
                                           QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            # Put the combobox in Spyder by default, when deleting a scheme
            names = self.get_option('names')
            self.set_scheme('spyder')
            self.schemes_combobox.setCurrentIndex(names.index('spyder'))
            self.set_option('selected', 'spyder')
    
            # Delete from custom_names
            custom_names = self.get_option('custom_names', [])
            if scheme_name in custom_names:
                custom_names.remove(scheme_name)
            self.set_option('custom_names', custom_names)
    
            # Delete config options
            for key in syntaxhighlighters.COLOR_SCHEME_KEYS:
                option = "{0}/{1}".format(scheme_name, key)
                CONF.remove_option(self.CONF_SECTION, option)
            CONF.remove_option(self.CONF_SECTION, "{0}/name".format(scheme_name))
    
            self.update_combobox()
            self.update_preview()

    def set_scheme(self, scheme_name):
        """
        Set the current stack in the dialog to the scheme with 'scheme_name'.
        """
        dlg = self.scheme_editor_dialog
        dlg.set_scheme(scheme_name)

    @Slot()
    def reset_to_default(self):
        """Restore initial values for default color schemes."""
        # Checks that this is indeed a default scheme
        scheme = self.current_scheme
        names = self.get_option('names')
        if scheme in names:
            for key in syntaxhighlighters.COLOR_SCHEME_KEYS:
                option = "{0}/{1}".format(scheme, key)
                value = CONF.get_default(self.CONF_SECTION, option)
                self.set_option(option, value)

            self.load_from_conf()


class SchemeEditor(QDialog):
    """A color scheme editor dialog."""
    def __init__(self, parent=None, stack=None):
        super(SchemeEditor, self).__init__(parent)
        self.parent = parent
        self.stack = stack
        self.order = []    # Uses scheme names

        # Needed for self.get_edited_color_scheme()
        self.widgets = {}
        self.scheme_name_textbox = {}
        self.last_edited_color_scheme = None
        self.last_used_scheme = None

        # Widgets
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        layout.addWidget(bbox)
        self.setLayout(layout)

        # Signals
        bbox.accepted.connect(self.accept)
        bbox.accepted.connect(self.get_edited_color_scheme)
        bbox.rejected.connect(self.reject)

    # Helpers
    # -------------------------------------------------------------------------
    def set_scheme(self, scheme_name):
        """Set the current stack by 'scheme_name'."""
        self.stack.setCurrentIndex(self.order.index(scheme_name))
        self.last_used_scheme = scheme_name

    def get_scheme_name(self):
        """
        Returns the edited scheme name, needed to update the combobox on
        scheme creation.
        """
        return self.scheme_name_textbox[self.last_used_scheme].text()

    def get_edited_color_scheme(self):
        """
        Get the values of the last edited color scheme to be used in an instant
        preview in the preview editor, without using `apply`.
        """
        color_scheme = {}
        scheme_name = self.last_used_scheme

        for key in self.widgets[scheme_name]:
            items = self.widgets[scheme_name][key]

            if len(items) == 1:
                # ColorLayout
                value = items[0].text()
            else:
                # ColorLayout + checkboxes
                value = (items[0].text(), items[1].isChecked(),
                         items[2].isChecked())

            color_scheme[key] = value

        return color_scheme

    # Actions
    # -------------------------------------------------------------------------
    def add_color_scheme_stack(self, scheme_name, custom=False):
        """Add a stack for a given scheme and connects the CONF values."""
        color_scheme_groups = [
            (_('Text'), ["normal", "comment", "string", "number", "keyword",
                         "builtin", "definition", "instance", ]),
            (_('Highlight'), ["currentcell", "currentline", "occurrence",
                              "matched_p", "unmatched_p", "ctrlclick"]),
            (_('Background'), ["background", "sideareas"])
            ]

        parent = self.parent
        line_edit = parent.create_lineedit(_("Scheme name:"),
                                           '{0}/name'.format(scheme_name))

        self.widgets[scheme_name] = {}

        # Widget setup
        line_edit.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setWindowTitle(_('Color scheme editor'))

        # Layout
        name_layout = QHBoxLayout()
        name_layout.addWidget(line_edit.label)
        name_layout.addWidget(line_edit.textbox)
        self.scheme_name_textbox[scheme_name] = line_edit.textbox

        if not custom:
            line_edit.textbox.setDisabled(True)

        cs_layout = QVBoxLayout()
        cs_layout.addLayout(name_layout)

        h_layout = QHBoxLayout()
        v_layout = QVBoxLayout()

        for index, item in enumerate(color_scheme_groups):
            group_name, keys = item
            group_layout = QGridLayout()

            for row, key in enumerate(keys):
                option = "{0}/{1}".format(scheme_name, key)
                value = self.parent.get_option(option)
                name = syntaxhighlighters.COLOR_SCHEME_KEYS[key]

                if is_text_string(value):
                    label, clayout = parent.create_coloredit(
                        name,
                        option,
                        without_layout=True,
                        )
                    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    group_layout.addWidget(label, row+1, 0)
                    group_layout.addLayout(clayout, row+1, 1)

                    # Needed to update temp scheme to obtain instant preview
                    self.widgets[scheme_name][key] = [clayout]
                else:
                    label, clayout, cb_bold, cb_italic = parent.create_scedit(
                        name,
                        option,
                        without_layout=True,
                        )
                    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    group_layout.addWidget(label, row+1, 0)
                    group_layout.addLayout(clayout, row+1, 1)
                    group_layout.addWidget(cb_bold, row+1, 2)
                    group_layout.addWidget(cb_italic, row+1, 3)

                    # Needed to update temp scheme to obtain instant preview
                    self.widgets[scheme_name][key] = [clayout, cb_bold,
                                                      cb_italic]

            group_box = QGroupBox(group_name)
            group_box.setLayout(group_layout)

            if index == 0:
                h_layout.addWidget(group_box)
            else:
                v_layout.addWidget(group_box)

        h_layout.addLayout(v_layout)
        cs_layout.addLayout(h_layout)

        stackitem = QWidget()
        stackitem.setLayout(cs_layout)
        self.stack.addWidget(stackitem)
        self.order.append(scheme_name)

    def delete_color_scheme_stack(self, scheme_name):
        """Remove stack widget by 'scheme_name'."""
        self.set_scheme(scheme_name)
        widget = self.stack.currentWidget()
        self.stack.removeWidget(widget)
        index = self.order.index(scheme_name)
        self.order.pop(index)
