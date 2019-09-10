# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
General entry in Preferences.

For historical reasons (dating back to Spyder 2) the main class here is called
`MainConfigPage` and its associated entry in our config system is called
`main`.
"""

import traceback

from qtpy.compat import from_qvariant
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QApplication, QButtonGroup, QGridLayout, QGroupBox,
                            QHBoxLayout, QLabel, QMessageBox, QTabWidget,
                            QVBoxLayout)

from spyder.config.base import (_, LANGUAGE_CODES, running_in_mac_app,
                                save_lang_conf)
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.py3compat import to_text_string
import spyder.utils.icon_manager as ima


HDPI_QT_PAGE = "https://doc.qt.io/qt-5/highdpi.html"


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
        if running_in_mac_app(check_file=True):
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
        cursor_spin = self.create_spinbox(
            "", _("ms"),
            'custom_cursor_blinking',
            default=QApplication.cursorFlashTime(),
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
        interface_layout = QVBoxLayout()
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
        screen_resolution_label.setOpenExternalLinks(True)

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

        custom_scaling_edit = self.create_lineedit(
            "",
            'high_dpi_custom_scale_factors',
            tip=_("Enter values for different screens "
                  "separated by semicolons ';'.\n"
                  "Float values are supported"),
            alignment=Qt.Horizontal,
            regex=r"[0-9]+(?:\.[0-9]*)(;[0-9]+(?:\.[0-9]*))*",
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

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(screen_resolution_group, interface_group),
                    _("Interface"))
        tabs.addTab(self.create_tab(general_group, sbar_group),
                    _("Advanced settings"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
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
        try:
            save_lang_conf(value)
            self.set_option('interface_language', value)
        except Exception:
            QMessageBox.critical(
                self, _("Error"),
                _("We're sorry but the following error occurred while trying "
                  "to set your selected language:<br><br>"
                  "<tt>{}</tt>").format(traceback.format_exc()),
                QMessageBox.Ok)
            return
