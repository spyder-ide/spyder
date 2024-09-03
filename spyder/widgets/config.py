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
from qtpy.QtCore import Qt, QRegularExpression, QSize, Signal, Slot
from qtpy.QtGui import QColor, QRegularExpressionValidator, QTextOption
from qtpy.QtWidgets import (QAction, QButtonGroup, QCheckBox, QDoubleSpinBox,
                            QFileDialog, QGridLayout, QGroupBox,
                            QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                            QPlainTextEdit, QPushButton, QRadioButton,
                            QSpinBox, QTabWidget, QVBoxLayout, QWidget)

# Local imports
from spyder.api.widgets.comboboxes import SpyderComboBox, SpyderFontComboBox
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.user import NoDefault
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.colors import ColorLayout
from spyder.widgets.helperwidgets import TipWidget, ValidationLineEdit
from spyder.widgets.comboboxes import FileComboBox
from spyder.widgets.sidebardialog import SidebarPage


class BaseConfigTab(QWidget):
    """Stub class to declare a config tab."""
    pass


class ConfigAccessMixin:
    """Mixin to access config options in SpyderConfigPages."""
    CONF_SECTION = None

    def set_option(
        self,
        option,
        value,
        section=None,
        recursive_notification=False,
        secure=False,
    ):
        section = self.CONF_SECTION if section is None else section
        CONF.set(
            section,
            option,
            value,
            recursive_notification=recursive_notification,
            secure=secure,
        )

    def get_option(
        self, option, default=NoDefault, section=None, secure=False
    ):
        section = self.CONF_SECTION if section is None else section
        return CONF.get(section, option, default=default, secure=secure)

    def remove_option(self, option, section=None, secure=False):
        section = self.CONF_SECTION if section is None else section
        CONF.remove_option(section, option, secure=secure)


class SpyderConfigPage(SidebarPage, ConfigAccessMixin):
    """
    Page that can display graphical elements connected to our config system.
    """

    # Signals
    apply_button_enabled = Signal(bool)

    # Constants
    CONF_SECTION = None
    LOAD_FROM_CONFIG = True

    def __init__(self, parent):
        SidebarPage.__init__(self, parent)

        # Callback to call before saving settings to disk
        self.pre_apply_callback = None

        # Callback to call after saving settings to disk
        self.apply_callback = lambda: self._apply_settings_tabs(
            self.changed_options
        )

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
        self.tabs = None
        self.is_modified = False

        if getattr(parent, "main", None):
            self.main = parent.main
        else:
            self.main = None

    def initialize(self):
        """Initialize configuration page."""
        self.setup_page()
        if self.LOAD_FROM_CONFIG:
            self.load_from_conf()

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

    def apply_changes(self):
        """Apply changes callback"""
        if self.is_modified:
            if self.pre_apply_callback is not None:
                self.pre_apply_callback()

            self.save_to_conf()

            if self.apply_callback is not None:
                self.apply_callback()

            # Since the language cannot be retrieved by CONF and the language
            # is needed before loading CONF, this is an extra method needed to
            # ensure that when changes are applied, they are copied to a
            # specific file storing the language value. This only applies to
            # the main section config.
            if self.CONF_SECTION == 'main':
                self._save_lang()

            for restart_option in self.restart_options:
                if restart_option in self.changed_options:
                    self.prompt_restart_required()
                    break  # Ensure a single popup is displayed
            self.set_modified(False)

    def check_settings(self):
        """This method is called to check settings after configuration
        dialog has been shown"""
        pass

    def set_modified(self, state):
        self.is_modified = state
        self.apply_button_enabled.emit(state)
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
                                         f"{invalid_msg}:<br><b>{text}</b>",
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

    def reset_widget_dicts(self):
        """Reset the dicts of widgets tracked in the page."""
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

    def load_from_conf(self):
        """Load settings from configuration file."""
        for checkbox, (sec, option, default) in list(self.checkboxes.items()):
            checkbox.setChecked(self.get_option(option, default, section=sec))
            checkbox.clicked[bool].connect(lambda _, opt=option, sect=sec:
                                           self.has_been_modified(sect, opt))
            if checkbox.restart_required:
                if sec is None:
                    self.restart_options[option] = checkbox.text()
                else:
                    self.restart_options[(sec, option)] = checkbox.text()

        for radiobutton, (sec, option, default) in list(
                self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default,
                                                   section=sec))
            radiobutton.toggled.connect(lambda _foo, opt=option, sect=sec:
                                        self.has_been_modified(sect, opt))
            if radiobutton.restart_required:
                if sec is None:
                    self.restart_options[option] = radiobutton.label_text
                else:
                    self.restart_options[(sec, option)] = radiobutton.label_text

        for lineedit, (sec, option, default) in list(self.lineedits.items()):
            data = self.get_option(
                option,
                default,
                section=sec,
                secure=True
                if (hasattr(lineedit, "password") and lineedit.password)
                else False,
            )

            if getattr(lineedit, 'content_type', None) == list:
                data = ', '.join(data)
            else:
                # Make option value a string to prevent errors when using it
                # as widget text.
                # See spyder-ide/spyder#18929
                data = str(data)
            lineedit.setText(data)
            lineedit.textChanged.connect(lambda _, opt=option, sect=sec:
                                         self.has_been_modified(sect, opt))
            if lineedit.restart_required:
                if sec is None:
                    self.restart_options[option] = lineedit.label_text
                else:
                    self.restart_options[(sec, option)] = lineedit.label_text

        for textedit, (sec, option, default) in list(self.textedits.items()):
            data = self.get_option(option, default, section=sec)
            if getattr(textedit, 'content_type', None) == list:
                data = ', '.join(data)
            elif getattr(textedit, 'content_type', None) == dict:
                data = to_text_string(data)
            textedit.setPlainText(data)
            textedit.textChanged.connect(lambda opt=option, sect=sec:
                                         self.has_been_modified(sect, opt))
            if textedit.restart_required:
                if sec is None:
                    self.restart_options[option] = textedit.label_text
                else:
                    self.restart_options[(sec, option)] = textedit.label_text

        for spinbox, (sec, option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default, section=sec))
            spinbox.valueChanged.connect(lambda _foo, opt=option, sect=sec:
                                         self.has_been_modified(sect, opt))

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
            combobox.currentIndexChanged.connect(
                lambda _foo, opt=option, sect=sec:
                    self.has_been_modified(sect, opt))
            if combobox.restart_required:
                if sec is None:
                    self.restart_options[option] = combobox.label_text
                else:
                    self.restart_options[(sec, option)] = combobox.label_text

        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            font = self.get_font(option)
            fontbox.setCurrentFont(font)
            sizebox.setValue(font.pointSize())

            fontbox.currentIndexChanged.connect(
                lambda _foo, opt=option: self.has_been_modified(None, opt))
            sizebox.valueChanged.connect(
                lambda _foo, opt=option: self.has_been_modified(None, opt))

            if fontbox.restart_required:
                self.restart_options[option] = fontbox.label_text

            if sizebox.restart_required:
                self.restart_options[option] = sizebox.label_text

        for clayout, (sec, option, default) in list(self.coloredits.items()):
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default, section=sec))
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                btn.clicked.connect(lambda _foo, opt=option, sect=sec:
                                    self.has_been_modified(sect, opt))
            else:
                btn.clicked.connect(lambda opt=option, sect=sec:
                                    self.has_been_modified(sect, opt))
            edit.textChanged.connect(lambda _foo, opt=option, sect=sec:
                                     self.has_been_modified(sect, opt))

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

            edit.textChanged.connect(lambda _foo, opt=option, sect=sec:
                                     self.has_been_modified(sect, opt))
            btn.clicked[bool].connect(lambda _foo, opt=option, sect=sec:
                                      self.has_been_modified(sect, opt))
            cb_bold.clicked[bool].connect(lambda _foo, opt=option, sect=sec:
                                          self.has_been_modified(sect, opt))
            cb_italic.clicked[bool].connect(lambda _foo, opt=option, sect=sec:
                                            self.has_been_modified(sect, opt))

    def save_to_conf(self):
        """Save settings to configuration file"""
        for checkbox, (sec, option, _default) in list(
                self.checkboxes.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                value = checkbox.isChecked()
                self.set_option(option, value, section=sec,
                                recursive_notification=False)

        for radiobutton, (sec, option, _default) in list(
                self.radiobuttons.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                self.set_option(option, radiobutton.isChecked(), section=sec,
                                recursive_notification=False)

        for lineedit, (sec, option, _default) in list(self.lineedits.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                data = lineedit.text()
                content_type = getattr(lineedit, 'content_type', None)
                if content_type == list:
                    data = [item.strip() for item in data.split(',')]
                else:
                    data = to_text_string(data)

                self.set_option(
                    option,
                    data,
                    section=sec,
                    recursive_notification=False,
                    secure=True
                    if (hasattr(lineedit, "password") and lineedit.password)
                    else False,
                )

        for textedit, (sec, option, _default) in list(self.textedits.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
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
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                self.set_option(option, spinbox.value(), section=sec,
                                recursive_notification=False)

        for combobox, (sec, option, _default) in list(self.comboboxes.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                data = combobox.itemData(combobox.currentIndex())
                self.set_option(option, from_qvariant(data, to_text_string),
                                section=sec, recursive_notification=False)

        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            if option in self.changed_options or not self.LOAD_FROM_CONFIG:
                font = fontbox.currentFont()
                font.setPointSize(sizebox.value())
                self.set_font(font, option)

        for clayout, (sec, option, _default) in list(self.coloredits.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                self.set_option(option,
                                to_text_string(clayout.lineedit.text()),
                                section=sec, recursive_notification=False)

        for (clayout, cb_bold, cb_italic), (sec, option, _default) in list(
                self.scedits.items()):
            if (
                option in self.changed_options
                or (sec, option) in self.changed_options
                or not self.LOAD_FROM_CONFIG
            ):
                color = to_text_string(clayout.lineedit.text())
                bold = cb_bold.isChecked()
                italic = cb_italic.isChecked()
                self.set_option(option, (color, bold, italic), section=sec,
                                recursive_notification=False)

    @Slot(str)
    def has_been_modified(self, section, option):
        self.set_modified(True)
        if section is None:
            self.changed_options.add(option)
        else:
            self.changed_options.add((section, option))

    def add_help_info_label(self, layout, tip_text):
        help_label = TipWidget(
            tip_text=tip_text,
            icon=ima.icon('question_tip'),
            hover_icon=ima.icon('question_tip_hover')
        )

        layout.addWidget(help_label)
        layout.addStretch(100)

        return layout, help_label

    def create_checkbox(self, text, option, default=NoDefault,
                        tip=None, msg_warning=None, msg_info=None,
                        msg_if_enabled=False, section=None, restart=False):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox(text)
        layout.addWidget(checkbox)

        self.checkboxes[checkbox] = (section, option, default)
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
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
        checkbox.restart_required = restart

        widget = QWidget(self)
        widget.checkbox = checkbox
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            widget.help_label = help_label
        widget.setLayout(layout)
        return widget

    def create_radiobutton(self, text, option, default=NoDefault,
                           tip=None, msg_warning=None, msg_info=None,
                           msg_if_enabled=False, button_group=None,
                           restart=False, section=None):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        radiobutton = QRadioButton(text)
        layout.addWidget(radiobutton)

        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        if button_group is None:
            if self.default_button_group is None:
                self.default_button_group = QButtonGroup(self)
            button_group = self.default_button_group
        button_group.addButton(radiobutton)
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

        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            radiobutton.help_label = help_label
        widget = QWidget(self)
        widget.radiobutton = radiobutton
        widget.setLayout(layout)
        return widget

    def create_lineedit(self, text, option, default=NoDefault,
                        tip=None, alignment=Qt.Vertical, regex=None,
                        restart=False, word_wrap=True, placeholder=None,
                        content_type=None, section=None, status_icon=None,
                        password=False, validate_callback=None,
                        validate_reason=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section

        label = QLabel(text)
        label.setWordWrap(word_wrap)

        if validate_callback:
            if not validate_reason:
                raise RuntimeError(
                    "You need to provide a validate_reason if you want to use "
                    "a validate_callback"
                )

            edit = ValidationLineEdit(
                validate_callback=validate_callback,
                validate_reason=validate_reason,
            )
            status_action = edit.error_action
        else:
            edit = QLineEdit()
        edit.content_type = content_type
        if password:
            edit.setEchoMode(QLineEdit.Password)

        if status_icon is not None:
            status_action = QAction(self)
            edit.addAction(status_action, QLineEdit.TrailingPosition)
            status_action.setIcon(status_icon)
            status_action.setVisible(False)

        if alignment == Qt.Vertical:
            layout = QVBoxLayout()

            # This is necessary to correctly align `label` and `edit` to the
            # left when they are displayed vertically.
            edit.setStyleSheet("margin-left: 5px")

            if tip is not None:
                label_layout = QHBoxLayout()
                label_layout.setSpacing(0)
                label_layout.addWidget(label)
                label_layout, help_label = self.add_help_info_label(
                    label_layout, tip
                )
                layout.addLayout(label_layout)
            else:
                layout.addWidget(label)

            layout.addWidget(edit)
        else:
            layout = QHBoxLayout()
            layout.addWidget(label)
            layout.addWidget(edit)
            if tip is not None:
                layout, help_label = self.add_help_info_label(layout, tip)

        layout.setContentsMargins(0, 0, 0, 0)

        if regex:
            edit.setValidator(
                QRegularExpressionValidator(QRegularExpression(regex))
            )

        if placeholder:
            edit.setPlaceholderText(placeholder)

        self.lineedits[edit] = (section, option, default)

        widget = QWidget(self)
        widget.label = label
        widget.textbox = edit
        if tip is not None:
            widget.help_label = help_label
        if status_icon is not None or validate_callback is not None:
            widget.status_action = status_action

        widget.setLayout(layout)
        edit.restart_required = restart
        edit.label_text = text
        edit.password = password

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
        self.textedits[edit] = (section, option, default)

        widget = QWidget(self)
        widget.label = label
        widget.textbox = edit
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            widget.help_label = help_label
        widget.setLayout(layout)
        edit.restart_required = restart
        edit.label_text = text
        return widget

    def create_browsedir(self, text, option, default=NoDefault, section=None,
                         tip=None, alignment=Qt.Horizontal, status_icon=None):
        widget = self.create_lineedit(
            text,
            option,
            default,
            section=section,
            alignment=alignment,
            # We need the tip to be added by the lineedit if the alignment is
            # vertical. If not, it'll be added below when setting the layout.
            tip=tip if (tip and alignment == Qt.Vertical) else None,
            status_icon=status_icon,
        )

        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break

        msg = _("Invalid directory path")
        self.validate_data[edit] = (osp.isdir, msg)

        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(lambda: self.select_directory(edit))
        browse_btn.setIconSize(
            QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
        )

        if alignment == Qt.Vertical:
            # This is necessary to position browse_btn vertically centered with
            # respect to the lineedit.
            browse_btn.setStyleSheet("margin-top: 28px")

            layout = QGridLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, 0, 0)
            layout.addWidget(browse_btn, 0, 1)
        else:
            # This is necessary to position browse_btn vertically centered with
            # respect to the lineedit.
            browse_btn.setStyleSheet("margin-top: 2px")

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget)
            layout.addWidget(browse_btn)
            if tip is not None:
                layout, help_label = self.add_help_info_label(layout, tip)

        browsedir = QWidget(self)
        browsedir.textbox = widget.textbox
        if status_icon:
            browsedir.status_action = widget.status_action

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

    def create_browsefile(self, text, option, default=NoDefault, section=None,
                          tip=None, filters=None, alignment=Qt.Horizontal,
                          status_icon=None):
        widget = self.create_lineedit(
            text,
            option,
            default,
            section=section,
            alignment=alignment,
            # We need the tip to be added by the lineedit if the alignment is
            # vertical. If not, it'll be added below when setting the layout.
            tip=tip if (tip and alignment == Qt.Vertical) else None,
            status_icon=status_icon,
        )

        for edit in self.lineedits:
            if widget.isAncestorOf(edit):
                break

        msg = _('Invalid file path')
        self.validate_data[edit] = (osp.isfile, msg)

        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select file"))
        browse_btn.clicked.connect(lambda: self.select_file(edit, filters))
        browse_btn.setIconSize(
           QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
        )

        if alignment == Qt.Vertical:
            # This is necessary to position browse_btn vertically centered with
            # respect to the lineedit.
            browse_btn.setStyleSheet("margin-top: 28px")

            layout = QGridLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, 0, 0)
            layout.addWidget(browse_btn, 0, 1)
        else:
            # This is necessary to position browse_btn vertically centered with
            # respect to the lineedit.
            browse_btn.setStyleSheet("margin-top: 2px")

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget)
            layout.addWidget(browse_btn)
            if tip is not None:
                layout, help_label = self.add_help_info_label(layout, tip)

        browsefile = QWidget(self)
        browsefile.textbox = widget.textbox
        if status_icon:
            browsefile.status_action = widget.status_action

        browsefile.setLayout(layout)
        return browsefile

    def select_file(self, edit, filters=None, **kwargs):
        """Select File"""
        basedir = osp.dirname(to_text_string(edit.text()))
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        if filters is None:
            filters = _("All files (*)")
        title = _("Select file")
        filename, _selfilter = getopenfilename(self, title, basedir, filters,
                                               **kwargs)
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
        self.spinboxes[spinbox] = (section, option, default)
        layout = QHBoxLayout()
        for subwidget in (plabel, spinbox, slabel):
            if subwidget is not None:
                layout.addWidget(subwidget)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.spinbox = spinbox
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            widget.help_label = help_label
        widget.setLayout(layout)
        return widget

    def create_coloredit(self, text, option, default=NoDefault, tip=None,
                         without_layout=False, section=None):
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        label = QLabel(text)
        clayout = ColorLayout(QColor(Qt.black), self)
        clayout.lineedit.setMaximumWidth(80)
        self.coloredits[clayout] = (section, option, default)
        if without_layout:
            return label, clayout
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addLayout(clayout)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)

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
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget

    def create_combobox(self, text, choices, option, default=NoDefault,
                        tip=None, restart=False, section=None):
        """choices: couples (name, key)"""
        if section is not None and section != self.CONF_SECTION:
            self.cross_section_options[option] = section
        label = QLabel(text)
        combobox = SpyderComboBox()
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
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            widget.help_label = help_label
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
        combobox.addItems(choices)
        combobox.choices = choices

        msg = _('Invalid file path')
        self.validate_data[edit] = (
            validate_callback if validate_callback else osp.isfile,
            msg
        )

        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select file"))
        options = QFileDialog.DontResolveSymlinks
        browse_btn.clicked.connect(
            lambda: self.select_file(edit, filters, options=options)
        )
        browse_btn.setIconSize(
           QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(combobox)
        layout.addWidget(browse_btn)
        layout.addStretch()

        widget = QWidget(self)
        widget.combobox = combobox
        widget.browse_btn = browse_btn
        if tip is not None:
            layout, help_label = self.add_help_info_label(layout, tip)
            widget.help_label = help_label
        widget.setLayout(layout)

        return widget

    def create_fontgroup(self, option=None, text=None, title=None,
                         tip=None, fontfilters=None, without_group=False,
                         restart=False):
        """Option=None -> setting plugin font"""

        if title:
            fontlabel = QLabel(title)
        else:
            fontlabel = QLabel(_("Font"))

        fontbox = SpyderFontComboBox()
        fontbox.restart_required = restart
        fontbox.label_text = _("{} font").format(title)

        if fontfilters is not None:
            fontbox.setFontFilters(fontfilters)

        sizebox = QSpinBox()
        sizebox.setRange(7, 100)
        sizebox.restart_required = restart
        sizebox.label_text = _("{} font size").format(title)

        self.fontboxes[(fontbox, sizebox)] = option

        layout = QHBoxLayout()
        for subwidget in (fontlabel, fontbox, sizebox):
            layout.addWidget(subwidget)
        layout.addStretch(1)

        if not without_group:
            if text is None:
                text = _("Font style")

            group = QGroupBox(text)
            group.setLayout(layout)

            if tip is not None:
                layout, help_label = self.add_help_info_label(layout, tip)

            return group
        else:
            widget = QWidget(self)
            widget.fontlabel = fontlabel
            widget.fontbox = fontbox
            widget.sizebox = sizebox
            widget.setLayout(layout)

            return widget

    def create_button(
        self,
        callback,
        text=None,
        icon=None,
        tooltip=None,
        set_modified_on_click=False,
    ):
        if icon is not None:
            btn = QPushButton(icon, "", parent=self)
            btn.setIconSize(
                QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
            )
        else:
            btn = QPushButton(text, parent=self)

        btn.clicked.connect(callback)
        if tooltip is not None:
            btn.setToolTip(tooltip)

        if set_modified_on_click:
            btn.clicked.connect(
                lambda checked=False, opt="": self.has_been_modified(
                    self.CONF_SECTION, opt
                )
            )

        return btn

    def create_tab(self, name, widgets):
        """
        Create a tab widget page.

        Parameters
        ----------
        name: str
            Name of the tab
        widgets: list or QWidget
            List of widgets to add to the tab. This can be also a single
            widget.

        Notes
        -----
        * Widgets are added in a vertical layout.
        """
        if self.tabs is None:
            self.tabs = QTabWidget(self)
            self.tabs.setUsesScrollButtons(True)
            self.tabs.setElideMode(Qt.ElideNone)

            vlayout = QVBoxLayout()
            vlayout.addWidget(self.tabs)
            self.setLayout(vlayout)

        if not isinstance(widgets, list):
            widgets = [widgets]

        tab = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            layout.addWidget(w)
        layout.addStretch(1)
        tab.setLayout(layout)

        self.tabs.addTab(tab, name)

    def prompt_restart_required(self):
        """Prompt the user with a request to restart."""
        message = _(
            "One or more of the settings you changed requires a restart to be "
            "applied.<br><br>"
            "Do you wish to restart now?"
        )

        answer = QMessageBox.information(
            self,
            _("Information"),
            message,
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.Yes:
            self.restart()

    def restart(self):
        """Restart Spyder."""
        self.main.restart(close_immediately=True)

    def _add_tab(self, Widget):
        widget = Widget(self)

        if self.tabs is None:
            # In case a preference page does not have any tabs, we need to
            # add a tab with the widgets that already exist and then add the
            # new tab.
            layout = self.layout()
            main_widget = QWidget(self)
            main_widget.setLayout(layout)

            self.create_tab(_('General'), main_widget)
            self.create_tab(Widget.TITLE, widget)
        else:
            self.create_tab(Widget.TITLE, widget)

        self.load_from_conf()
