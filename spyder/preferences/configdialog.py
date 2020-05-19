# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Configuration dialog / Preferences.
"""

# Standard library imports
import ast
import os.path as osp

# Third party imports
from qtpy import API
from qtpy.compat import (from_qvariant, getexistingdirectory, getopenfilename,
                         to_qvariant)
from qtpy.QtCore import QRegExp, QSize, Qt, Signal, Slot
from qtpy.QtGui import QColor, QRegExpValidator, QTextOption
from qtpy.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                            QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                            QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                            QLineEdit, QListView, QListWidget,
                            QListWidgetItem, QMessageBox, QPlainTextEdit,
                            QPushButton, QRadioButton, QScrollArea, QSpinBox,
                            QSplitter, QStackedWidget, QVBoxLayout, QWidget)

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.config.user import NoDefault
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.colors import ColorLayout
from spyder.widgets.comboboxes import FileComboBox


# Localization
_ = get_translation('spyder')


class ConfigDialog(QDialog):
    """Spyder configuration ('Preferences') dialog box."""

    # Signals
    check_settings = Signal()  # FIXME:
    sig_size_changed = Signal(QSize)
    sig_reset_requested = Signal()
    sig_restart_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.main = parent

        # Widgets
        self.pages_widget = QStackedWidget()
        self.pages_widget.setMinimumWidth(600)
        self.contents_widget = QListWidget()
        self.button_reset = QPushButton(_('Reset to defaults'))

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply |
                                QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)
        self.ok_btn = bbox.button(QDialogButtonBox.Ok)

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
        self.contents_widget.setMinimumWidth(220)
        self.contents_widget.setMinimumHeight(400)

        # Layout
        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)
        hsplitter.setStretchFactor(0, 1)
        hsplitter.setStretchFactor(1, 2)

        btnlayout = QHBoxLayout()
        btnlayout.addWidget(self.button_reset)
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        # Signals and slots
        self.button_reset.clicked.connect(self.sig_reset_requested)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
            self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)

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

        if widget:
            return widget.widget()

    def get_index_by_name(self, name):
        """Return page index by CONF_SECTION name."""
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget = widget.widget()
            if widget.CONF_SECTION == name:
                return idx
        else:
            return None

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
        self.apply_btn.setEnabled(widget.is_modified)

    def add_page(self, widget):
        self.check_settings.connect(widget.check_settings)
        widget.sig_restart_requested.connect(self.sig_restart_requested)
        # widget.show_this_page.connect(lambda row=self.contents_widget.count():
        #                               self.contents_widget.setCurrentRow(row))
        widget.sig_modified.connect(self.apply_btn.setEnabled)
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
        self.check_settings.emit()

    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        super().resizeEvent(event)
        self.sig_size_changed.emit(self.size())


class SpyderConfigPage(QWidget):
    """
    Plugin configuration dialog box page widget.
    """
    # Signals
    sig_modified = Signal(bool)  # Before: apply button
    sig_restart_requested = Signal()

    def __init__(self, parent=None, plugin=None):
        super().__init__(parent=parent)

        # FIXME: use this after moving to new API
        # if not isinstance(plugin, SpyderPluginV2):
        #     raise Exception('Plugin must be sublcass of SpyderPluginV2!')

        # Attributes
        # FIXME: use this after moving to new API
        # self._conf = None if plugin is None else plugin._conf
        self._conf = CONF
        self._parent = parent
        self.plugin = plugin
        self.is_modified = False
        self.changed_options = set()
        self.restart_options = dict()  # Dict to store name and localized text

        if plugin is not None:
            self.CONF_SECTION = plugin.CONF_SECTION

        # Widgets
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
        self.default_button_group = None

        # if plugin is not None:
        #     self.sig_restart_requested.connect(plugin.sig_restart_requested)

    def _set_state(self, state):
        """
        TODO:
        """
        self.is_modified = state
        self.sig_modified.emit(state)

        if not state:
            self.changed_options = set()

    @Slot(str)
    def _modify_option(self, option):
        """
        TODO:
        """
        self._set_state(True)
        self.changed_options.add(option)

    def get_name(self):
        """Configuration page name."""
        try:
            # New API
            name = self.plugin.get_name()
        except AttributeError:
            # Old API
            name = self.plugin.get_plugin_title()

        return name

    def get_icon(self):
        """Loads page icon named by self.ICON."""
        try:
            # New API
            icon = self.plugin.get_icon()
        except AttributeError:
            # Old API
            icon = self.plugin.get_plugin_icon()

        return icon

    def setup_page(self):
        """
        Setup configuration page widget.
        """
        raise NotImplementedError

    def apply_settings(self, options):
        raise NotImplementedError

    def initialize(self):
        """
        Initialize configuration page.

          * Setup GUI widgets.
          * Load settings and change widgets accordingly.
        """
        self.setup_page()
        self.load_from_conf()

    def check_settings(self):
        """
        This method is called to check settings after configuration
        dialog has been shown
        """
        pass

    def is_valid(self):
        """
        Return True if all widget contents are valid.
        """
        for lineedit in self.lineedits:
            if lineedit in self.validate_data and lineedit.isEnabled():
                validator, invalid_msg = self.validate_data[lineedit]
                text = str(lineedit.text())
                if not validator(text):
                    QMessageBox.critical(
                        self,
                        self.get_name(),
                        "%s:<br><b>%s</b>" % (invalid_msg, text),
                        QMessageBox.Ok,
                    )
                    return False

        return True

    # TODO: rename to set_conf_option
    def set_option(self, option, value, section=None):
        section = self.CONF_SECTION if section is None else section
        self._conf.set(section, option, value)

    # TODO: rename to get_conf_option
    def get_option(self, option, default=NoDefault, section=None):
        section = self.CONF_SECTION if section is None else section
        return self._conf.get(section, option, default)

    def load_from_conf(self):
        """
        Load settings from configuration file.
        """
        for checkbox, (sec, option, default) in list(self.checkboxes.items()):
            checkbox.setChecked(self.get_option(option, default, section=sec))
            checkbox.clicked.connect(lambda _, opt=option:
                                     self._modify_option(opt))

        for radiobutton, (sec, option, default) in list(
                self.radiobuttons.items()):
            radiobutton.setChecked(self.get_option(option, default,
                                                   section=sec))
            radiobutton.toggled.connect(lambda _foo, opt=option:
                                        self._modify_option(opt))
            if radiobutton.restart_required:
                self.restart_options[option] = radiobutton.label_text

        for lineedit, (sec, option, default) in list(self.lineedits.items()):
            data = self.get_option(option, default, section=sec)
            if getattr(lineedit, 'content_type', None) == list:
                data = ', '.join(data)
            lineedit.setText(data)
            lineedit.textChanged.connect(lambda _, opt=option:
                                         self._modify_option(opt))
            if lineedit.restart_required:
                self.restart_options[option] = lineedit.label_text

        for textedit, (sec, option, default) in list(self.textedits.items()):
            data = self.get_option(option, default, section=sec)
            if getattr(textedit, 'content_type', None) == list:
                data = ', '.join(data)
            elif getattr(textedit, 'content_type', None) == dict:
                data = str(data)
            textedit.setPlainText(data)
            textedit.textChanged.connect(lambda opt=option:
                                         self._modify_option(opt))
            if textedit.restart_required:
                self.restart_options[option] = textedit.label_text

        for spinbox, (sec, option, default) in list(self.spinboxes.items()):
            spinbox.setValue(self.get_option(option, default, section=sec))
            spinbox.valueChanged.connect(lambda _foo, opt=option:
                                         self._modify_option(opt))

        for combobox, (sec, option, default) in list(self.comboboxes.items()):
            value = self.get_option(option, default, section=sec)
            for index in range(combobox.count()):
                data = from_qvariant(combobox.itemData(index), str)
                # For PyQt API v2, it is necessary to convert `data` to
                # unicode in case the original type was not a string, like an
                # integer for example (see qtpy.compat.from_qvariant):
                if str(data) == str(value):
                    break
            else:
                if combobox.count() == 0:
                    index = None
            if index:
                combobox.setCurrentIndex(index)
            combobox.currentIndexChanged.connect(lambda _foo, opt=option:
                                                 self._modify_option(opt))
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
                                                self._modify_option(opt))
            sizebox.valueChanged.connect(lambda _foo, opt=property:
                                         self._modify_option(opt))

        for clayout, (sec, option, default) in list(self.coloredits.items()):
            property = to_qvariant(option)
            edit = clayout.lineedit
            btn = clayout.colorbtn
            edit.setText(self.get_option(option, default, section=sec))
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                btn.clicked.connect(lambda _foo, opt=option:
                                    self._modify_option(opt))
            else:
                btn.clicked.connect(lambda opt=option:
                                    self._modify_option(opt))
            edit.textChanged.connect(lambda _foo, opt=option:
                                     self._modify_option(opt))

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
                                     self._modify_option(opt))
            # QAbstractButton works differently for PySide and PyQt
            if not API == 'pyside':
                btn.clicked.connect(lambda _foo, opt=option:
                                    self._modify_option(opt))
                cb_bold.clicked.connect(lambda _foo, opt=option:
                                        self._modify_option(opt))
                cb_italic.clicked.connect(lambda _foo, opt=option:
                                          self._modify_option(opt))
            else:
                btn.clicked.connect(lambda opt=option:
                                    self._modify_option(opt))
                cb_bold.clicked.connect(lambda opt=option:
                                        self._modify_option(opt))
                cb_italic.clicked.connect(lambda opt=option:
                                          self._modify_option(opt))

    def save_to_conf(self):
        """
        Save settings to configuration file.
        """
        for checkbox, (sec, option, _default) in list(
                self.checkboxes.items()):
            if option in self.changed_options:
                value = checkbox.isChecked()
                self.set_option(option, value, section=sec)

        for radiobutton, (sec, option, _default) in list(
                self.radiobuttons.items()):
            if option in self.changed_options:
                self.set_option(option, radiobutton.isChecked(), section=sec)

        for lineedit, (sec, option, _default) in list(self.lineedits.items()):
            if option in self.changed_options:
                data = lineedit.text()
                content_type = getattr(lineedit, 'content_type', None)
                if content_type == list:
                    data = [item.strip() for item in data.split(',')]
                else:
                    data = str(data)
                self.set_option(option, data, section=sec)

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
                    data = str(data)

                self.set_option(option, data, section=sec)

        for spinbox, (sec, option, _default) in list(self.spinboxes.items()):
            if option in self.changed_options:
                self.set_option(option, spinbox.value(), section=sec)

        for combobox, (sec, option, _default) in list(self.comboboxes.items()):
            if option in self.changed_options:
                data = combobox.itemData(combobox.currentIndex())
                self.set_option(option, from_qvariant(data, str),
                                section=sec)

        for (fontbox, sizebox), option in list(self.fontboxes.items()):
            if option in self.changed_options:
                font = fontbox.currentFont()
                font.setPointSize(sizebox.value())
                self.set_font(font, option)

        for clayout, (sec, option, _default) in list(self.coloredits.items()):
            if option in self.changed_options:
                self.set_option(option,
                                str(clayout.lineedit.text()),
                                section=sec)

        for (clayout, cb_bold, cb_italic), (sec, option, _default) in list(
                self.scedits.items()):
            if option in self.changed_options:
                color = str(clayout.lineedit.text())
                bold = cb_bold.isChecked()
                italic = cb_italic.isChecked()
                self.set_option(option, (color, bold, italic), section=sec)

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
        answer = QMessageBox.information(
            self,
            msg_title,
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.sig_restart_requested.emit()

    def apply_changes(self):
        """Apply changes callback."""
        if self.is_modified:
            self.save_to_conf()
            # if self.apply_callback is not None:
            #     self.apply_callback()

            # Since the language cannot be retrieved by CONF and the language
            # is needed before loading CONF, this is an extra method needed to
            # ensure that when changes are applied, they are copied to a
            # specific file storing the language value. This only applies to
            # the main section config.
            # TODO: Use the Plugins.Core instead of hardcoding text
            if self.CONF_SECTION == u'main':
                self._save_lang()

            for restart_option in self.restart_options:
                if restart_option in self.changed_options:
                    self.prompt_restart_required()
                    break  # Ensure a single popup is displayed

            self._set_state(False)

    # --- Helper widget methods
    # ------------------------------------------------------------------------
    def create_checkbox(self, text, option, default=NoDefault,
                        tip=None, msg_warning=None, msg_info=None,
                        msg_if_enabled=False, section=None):
        checkbox = QCheckBox(text)
        self.checkboxes[checkbox] = (section, option, default)
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
        basedir = str(edit.text())
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
        basedir = osp.dirname(str(edit.text()))
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
                             default_line_edit=False, section=None):
        """choices: couples (name, key)"""
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
        btn.clicked.connect(lambda checked=False, opt='': self._modify_option(opt))
        return btn

    def create_tab(self, *widgets):
        """
        Create simple tab widget page: widgets added in a vertical layout.
        """
        widget = QWidget()
        layout = QVBoxLayout()
        for widg in widgets:
            layout.addWidget(widg)

        layout.addStretch(1)
        widget.setLayout(layout)
        return widget


class GeneralConfigPage(SpyderConfigPage):
    """
    Config page that maintains reference to main Spyder window.

    This widget allows to specify page name and icon declaratively.
    """
    NAME = None    # configuration page name, e.g. _("General")
    ICON = None    # name of icon resource (24x24)
    CONF_SECTION = None

    def __init__(self, parent, main, configuration):
        super().__init__(parent)

        self.main = main
        self._conf = configuration

    def get_name(self):
        """Configuration page name."""
        if self.NAME is None:
            raise Exception(
                'GeneralConfigPage must define a `NAME` class attribute!')

        return self.NAME

    def get_icon(self):
        """Loads page icon named by self.ICON."""
        if self.ICON is None:
            raise Exception(
                'GeneralConfigPage must define an `ICON` class attribute!')

        return self.ICON

    def apply_settings(self, options):
        raise NotImplementedError
