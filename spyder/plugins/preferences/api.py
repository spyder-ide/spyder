# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Preferences plugin public facing API
"""

# Standard library imports
import ast
import os.path as osp

# Third party imports
from qtpy import API
from qtpy.compat import (getexistingdirectory, getopenfilename, from_qvariant,
                         to_qvariant)
from qtpy.QtCore import QSize, Qt, Signal, Slot, QRegExp
from qtpy.QtGui import QColor, QRegExpValidator, QTextOption
from qtpy.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                            QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                            QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                            QLineEdit, QListView, QListWidget, QListWidgetItem,
                            QMessageBox, QPushButton, QRadioButton,
                            QScrollArea, QSpinBox, QSplitter, QStackedWidget,
                            QVBoxLayout, QWidget, QPlainTextEdit, QTabWidget)

# Local imports
from spyder.config.base import _, load_lang_conf
from spyder.config.manager import CONF
from spyder.config.user import NoDefault
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.colors import ColorLayout
from spyder.widgets.comboboxes import FileComboBox


class BaseConfigTab(QWidget):
    """Stub class to declare a config tab."""
    pass


class ConfigAccessMixin(object):
    """Namespace for methods that access config storage"""
    CONF_SECTION = None

    def set_option(self, option, value, section=None,
                   recursive_notification=False):
        section = self.CONF_SECTION if section is None else section
        CONF.set(section, option, value,
                 recursive_notification=recursive_notification)

    def get_option(self, option, default=NoDefault, section=None):
        section = self.CONF_SECTION if section is None else section
        return CONF.get(section, option, default)

    def remove_option(self, option, section=None):
        section = self.CONF_SECTION if section is None else section
        CONF.remove_option(section, option)


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


class SpyderConfigPage(ConfigPage, ConfigAccessMixin):
    """Plugin configuration dialog box page widget"""
    CONF_SECTION = None

    def __init__(self, parent):
        ConfigPage.__init__(self, parent,
                            apply_callback=lambda:
                            self._apply_settings_tabs(self.changed_options))
        self.checkboxes = {}
        self.radiobuttons = {}
        self.lineedits = {}
        self.textedits = {}
        self.validate_data = {}
        self.spinboxes = {}
        self.comboboxes = {}
        self.fontboxes = {}
        self.coloredits = {}
        self.scedits = {}
        self.cross_section_options = {}
        self.changed_options = set()
        self.restart_options = dict()  # Dict to store name and localized text
        self.default_button_group = None
        self.main = parent.main
        self.tabs = None

    def _apply_settings_tabs(self, options):
        if self.tabs is not None:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                layout = tab.layout()
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if hasattr(widget, 'apply_settings'):
                        if issubclass(type(widget), BaseConfigTab):
                            options |= widget.apply_settings()
        self.apply_settings(options)

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
        status = True
        for lineedit in self.lineedits:
            if lineedit in self.validate_data and lineedit.isEnabled():
                validator, invalid_msg = self.validate_data[lineedit]
                text = to_text_string(lineedit.text())
                if not validator(text):
                    QMessageBox.critical(self, self.get_name(),
                                     "%s:<br><b>%s</b>" % (invalid_msg, text),
                                     QMessageBox.Ok)
                    return False

        if self.tabs is not None and status:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                layout = tab.layout()
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if issubclass(type(widget), BaseConfigTab):
                        status &= widget.is_valid()
                        if not status:
                            return status
        return status

    def load_from_conf(self):
        """Load settings from configuration file."""
        for checkbox, (sec, option, default) in list(self.checkboxes.items()):
            checkbox.setChecked(self.get_option(option, default, section=sec))
            checkbox.clicked.connect(lambda _, opt=option:
                                     self.has_been_modified(opt))
        for radiobutton, (sec, option, default) in list(
                self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default,
                                                   section=sec))
            radiobutton.toggled.connect(lambda _foo, opt=option:
                                        self.has_been_modified(opt))
            if radiobutton.restart_required:
                self.restart_options[option] = radiobutton.label_text
        for lineedit, (sec, option, default) in list(self.lineedits.items()):
            data = self.get_option(option, default, section=sec)
            if getattr(lineedit, 'content_type', None) == list:
                data = ', '.join(data)
            lineedit.setText(data)
            lineedit.textChanged.connect(lambda _, opt=option:
                                         self.has_been_modified(opt))
            if lineedit.restart_required:
                self.restart_options[option] = lineedit.label_text
        for textedit, (sec, option, default) in list(self.textedits.items()):
            data = self.get_option(option, default, section=sec)
            if getattr(textedit, 'content_type', None) == list:
                data = ', '.join(data)
            elif getattr(textedit, 'content_type', None) == dict:
                data = to_text_string(data)
            textedit.setPlainText(data)
            textedit.textChanged.connect(lambda opt=option:
                                         self.has_been_modified(opt))
            if textedit.restart_required:
                self.restart_options[option] = textedit.label_text
        for spinbox, (sec, option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default, section=sec))
            spinbox.valueChanged.connect(lambda _foo, opt=option:
                                         self.has_been_modified(opt))
        for combobox, (sec, option, default) in list(self.comboboxes.items()):
            value = self.get_option(option, default, section=sec)
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
            rich_font = True if "rich" in option.lower() else False
            font = self.get_font(rich_font)
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
        for clayout, (sec, option, default) in list(self.coloredits.items()):
            property = to_qvariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default, section=sec))
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
             ), (sec, option, default) in list(self.scedits.items()):
            edit = clayout.lineedit
            btn = clayout.colorbtn
            options = self.get_option(option, default, section=sec)
            if options:
                color, bold, italic = options
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
        for checkbox, (sec, option, _default) in list(
                self.checkboxes.items()):
            if option in self.changed_options:
                value = checkbox.isChecked()
                self.set_option(option, value, section=sec,
                                recursive_notification=False)
        for radiobutton, (sec, option, _default) in list(
                self.radiobuttons.items()):
            if option in self.changed_options:
                self.set_option(option, radiobutton.isChecked(), section=sec,
                                recursive_notification=False)
        for lineedit, (sec, option, _default) in list(self.lineedits.items()):
            if option in self.changed_options:
                data = lineedit.text()
                content_type = getattr(lineedit, 'content_type', None)
                if content_type == list:
                    data = [item.strip() for item in data.split(',')]
                else:
                    data = to_text_string(data)
                self.set_option(option, data, section=sec,
                                recursive_notification=False)
        for textedit, (sec, option, _default) in list(self.textedits.items()):
            if option in self.changed_options:
                data = textedit.toPlainText()
                content_type = getattr(textedit, 'content_type', None)
                if content_type == dict:
                    if data:
                        data = ast.literal_eval(data)
                    else:
                        data = textedit.content_type()
                elif content_type in (tuple, list):
                    data = [item.strip() for item in data.split(',')]
                else:
                    data = to_text_string(data)
                self.set_option(option, data, section=sec,
                                recursive_notification=False)
        for spinbox, (sec, option, _default) in list(self.spinboxes.items()):
            if option in self.changed_options:
                self.set_option(option, spinbox.value(), section=sec,
                                recursive_notification=False)
        for combobox, (sec, option, _default) in list(self.comboboxes.items()):
            if option in self.changed_options:
                data = combobox.itemData(combobox.currentIndex())
                self.set_option(option, from_qvariant(data, to_text_string),
                                section=sec, recursive_notification=False)
        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            if option in self.changed_options:
                font = fontbox.currentFont()
                font.setPointSize(sizebox.value())
                self.set_font(font, option)
        for clayout, (sec, option, _default) in list(self.coloredits.items()):
            if option in self.changed_options:
                self.set_option(option,
                                to_text_string(clayout.lineedit.text()),
                                section=sec, recursive_notification=False)
        for (clayout, cb_bold, cb_italic), (sec, option, _default) in list(
                self.scedits.items()):
            if option in self.changed_options:
                color = to_text_string(clayout.lineedit.text())
                bold = cb_bold.isChecked()
                italic = cb_italic.isChecked()
                self.set_option(option, (color, bold, italic), section=sec,
                                recursive_notification=False)

    @Slot(str)
    def has_been_modified(self, option):
        self.set_modified(True)
        self.changed_options.add(option)

    def create_checkbox(self, text, option, default=NoDefault,
                        tip=None, msg_warning=None, msg_info=None,
                        msg_if_enabled=False, section=None):
        checkbox = QCheckBox(text)
        self.checkboxes[checkbox] = (section, option, default)
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        if tip is not None:
            checkbox.setToolTip(tip)
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
                           restart=False, section=None):
        radiobutton = QRadioButton(text)
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        if button_group is None:
            if self.default_button_group is None:
                self.default_button_group = QButtonGroup(self)
            button_group = self.default_button_group
        button_group.addButton(radiobutton)
        if tip is not None:
            radiobutton.setToolTip(tip)
        self.radiobuttons[radiobutton] = (section, option, default)
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
                        restart=False, word_wrap=True, placeholder=None,
                        content_type=None, section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        label = QLabel(text)
        label.setWordWrap(word_wrap)
        edit = QLineEdit()
        edit.content_type = content_type
        layout = QVBoxLayout() if alignment == Qt.Vertical else QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip:
            edit.setToolTip(tip)
        if regex:
            edit.setValidator(QRegExpValidator(QRegExp(regex)))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        self.lineedits[edit] = (section, option, default)
        widget = QWidget(self)
        widget.label = label
        widget.textbox = edit
        widget.setLayout(layout)
        edit.restart_required = restart
        edit.label_text = text
        return widget

    def create_textedit(self, text, option, default=NoDefault,
                        tip=None, restart=False, content_type=None,
                        section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        label = QLabel(text)
        label.setWordWrap(True)
        edit = QPlainTextEdit()
        edit.content_type = content_type
        edit.setWordWrapMode(QTextOption.WordWrap)
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip:
            edit.setToolTip(tip)
        self.textedits[edit] = (section, option, default)
        widget = QWidget(self)
        widget.label = label
        widget.textbox = edit
        widget.setLayout(layout)
        edit.restart_required = restart
        edit.label_text = text
        return widget

    def create_browsedir(self, text, option, default=NoDefault, tip=None,
                         section=None):
        widget = self.create_lineedit(text, option, default, section=section,
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
                          filters=None, section=None):
        widget = self.create_lineedit(text, option, default, section=section,
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
                       min_=None, max_=None, step=None, tip=None,
                       section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
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
        self.spinboxes[spinbox] = (section, option, default)
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
                         without_layout=False, section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        label = QLabel(text)
        clayout = ColorLayout(QColor(Qt.black), self)
        clayout.lineedit.setMaximumWidth(80)
        if tip is not None:
            clayout.setToolTip(tip)
        self.coloredits[clayout] = (section, option, default)
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
                      without_layout=False, section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
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
        self.scedits[(clayout, cb_bold, cb_italic)] = (section, option,
                                                       default)
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
                        tip=None, restart=False, section=None):
        """choices: couples (name, key)"""
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
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
        self.comboboxes[combobox] = (section, option, default)
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
                             default_line_edit=False, section=None,
                             validate_callback=None):
        """choices: couples (name, key)"""
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        combobox = FileComboBox(self, adjust_to_contents=adjust_to_contents,
                                default_line_edit=default_line_edit)
        combobox.restart_required = restart
        combobox.label_text = text
        edit = combobox.lineEdit()
        edit.label_text = text
        edit.restart_required = restart
        self.lineedits[edit] = (section, option, default)

        if tip is not None:
            combobox.setToolTip(tip)
        combobox.addItems(choices)
        combobox.choices = choices

        msg = _('Invalid file path')
        self.validate_data[edit] = (
            validate_callback if validate_callback else osp.isfile,
            msg)
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
            fontlabel = QLabel(_("Font"))
        fontbox = QFontComboBox()

        if fontfilters is not None:
            fontbox.setFontFilters(fontfilters)

        sizelabel = QLabel("  "+_("Size"))
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
        btn.clicked.connect(
            lambda checked=False, opt='': self.has_been_modified(opt))
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

    def add_tab(self, Widget):
        widget = Widget(self)
        if self.tabs is None:
            # In case a preference page does not have any tabs, we need to
            # add a tab with the widgets that already exist and then add the
            # new tab.
            self.tabs = QTabWidget()
            layout = self.layout()
            main_widget = QWidget()
            main_widget.setLayout(layout)
            self.tabs.addTab(self.create_tab(main_widget),
                             _('General'))
            self.tabs.addTab(self.create_tab(widget),
                             Widget.TITLE)
            vlayout = QVBoxLayout()
            vlayout.addWidget(self.tabs)
            self.setLayout(vlayout)
        else:
            self.tabs.addTab(self.create_tab(widget),
                             Widget.TITLE)
        self.load_from_conf()


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


class PreferencePages:
    General = 'main'
