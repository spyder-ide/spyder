# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Appearance entry in Preferences."""

import configparser
import sys

import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QFontComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
)

from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.config.manager import CONF
from spyder.plugins.appearance.widgets import SchemeEditor
from spyder.utils.fonts import get_font, set_font
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.theme_manager import COLOR_SCHEME_KEYS, THEME_MANAGER
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


PREVIEW_TEXT = (
    '"""A string"""\n\n'
    '# A comment\n\n'
    'class Foo(object):\n'
    '    def __init__(self):\n'
    '        bar = 42\n'
    '        print(bar)\n'
)


class AppearanceConfigPage(PluginConfigPage):

    def __init__(self, plugin, parent):
        super().__init__(plugin, parent)
        self._is_shown = False

        self._theme_changed_during_apply = False
        self.pre_apply_callback = self.check_theme_changed
        self.apply_callback = self.apply_theme_changes

        for variant_name in THEME_MANAGER.get_available_theme_variants():
            try:
                self.get_option(f"{variant_name}/name")
            except configparser.NoOptionError:
                display_name = THEME_MANAGER.get_theme_display_name(
                    variant_name
                )
                self.set_option(f"{variant_name}/name", display_name)

        selected = self.get_option(
            "selected", default="spyder_themes.spyder/dark"
        )
        resolved = THEME_MANAGER.canonical_theme_variant_id(selected)
        if resolved != selected:
            self.set_option("selected", resolved)
            selected = resolved

        if selected and "/" in selected:
            try:
                self.get_option(f"{selected}/name")
            except configparser.NoOptionError:
                display_name = THEME_MANAGER.get_theme_display_name(
                    selected
                )
                self.set_option(f"{selected}/name", display_name)

    def _builtin_theme_variants(self):
        """Registered theme variant ids.

        Excludes placeholder ``Custom`` when present.
        """
        names = list(THEME_MANAGER.get_available_theme_variants())

        try:
            names.remove("Custom")
        except ValueError:
            pass

        return names

    def _remove_temp_syntax_options(self):
        """Drop legacy ``temp/...`` syntax keys (preview scratch space)."""
        for key in COLOR_SCHEME_KEYS:
            try:
                self.remove_option(f"temp/{key}")
            except Exception:
                pass

    def setup_page(self):
        for variant_name in THEME_MANAGER.get_available_theme_variants():
            try:
                self.get_option(f"{variant_name}/name")
            except configparser.NoOptionError:
                display_name = THEME_MANAGER.get_theme_display_name(
                    variant_name
                )
                self.set_option(f"{variant_name}/name", display_name)

        # Ensure every variant has full syntax keys in config so scheme editor
        # stacks can be built (only fills missing keys; see ThemeManager).
        THEME_MANAGER.export_all_themes_to_config()

        names = self._builtin_theme_variants()
        self._remove_temp_syntax_options()

        # UI theme options
        ui_group = QGroupBox(_("Interface Theme"))

        # UI theme Widgets
        edit_button = self.create_button(
            icon=ima.icon("edit"),
            callback=self.edit_scheme,
            tooltip=_("Edit syntax highlighting colors"),
        )
        self.reset_button = self.create_button(
            icon=ima.icon("restart"),
            callback=self.reset_to_default,
            tooltip=_("Reset customized colors to defaults"),
        )

        self.stacked_widget = QStackedWidget(self)
        self.scheme_editor_dialog = SchemeEditor(
            parent=self,
            stack=self.stacked_widget
        )

        self.scheme_choices_dict = {}
        schemes_combobox_widget = self.create_combobox(
            '',
            [('', '')],
            'selected',
            items_elide_mode=Qt.ElideNone,
            restart=True,
        )
        self.schemes_combobox = schemes_combobox_widget.combobox

        # UI theme layout
        ui_layout = QVBoxLayout(ui_group)
        if sys.platform == "darwin":
            # Default spacing is too big on Mac
            ui_layout.setVerticalSpacing(2 * AppStyle. MarginSize)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addStretch()

        ui_layout.addWidget(self.schemes_combobox)
        ui_layout.addLayout(buttons_layout)
        ui_layout.setContentsMargins(12, 12, 12, 12)

        # Fonts options
        fonts_group = QGroupBox(_("Fonts"))

        # Fonts widgets
        self.plain_text_font = self.create_fontgroup(
            option='font',
            title=_("Monospace"),
            fontfilters=QFontComboBox.MonospacedFonts,
            without_group=True)

        self.app_font = self.create_fontgroup(
            option='app_font',
            title=_("Interface"),
            fontfilters=QFontComboBox.ProportionalFonts,
            restart=True,
            without_group=True)

        # System font checkbox
        if sys.platform == 'darwin':
            system_font_tip = _("Changing the interface font does not work "
                                "reliably on macOS")
        else:
            system_font_tip = None

        system_font_checkbox = self.create_checkbox(
            _("Use the system default interface font"),
            'use_system_font',
            restart=True,
            tip=system_font_tip
        )

        # Preview widgets
        preview_editor_label = QLabel(_("Editor"))
        self.preview_editor = SimpleCodeEditor(self)
        self.preview_editor.setFixedSize(260, 280)
        self.preview_editor.set_language('Python')
        self.preview_editor.set_text(PREVIEW_TEXT)
        self.preview_editor.set_blanks_enabled(False)
        self.preview_editor.set_scrollpastend_enabled(False)

        preview_interface_label = QLabel(_("Interface font"))
        self.preview_interface = QLabel("Sample text")
        self.preview_interface.setFixedWidth(260)
        self.preview_interface.setFixedHeight(45)
        self.preview_interface.setWordWrap(True)
        self.preview_interface.setTextInteractionFlags(
            Qt.TextEditorInteraction
        )
        self.preview_interface.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        preview_interface_label_css = qstylizer.style.StyleSheet()
        preview_interface_label_css.QLabel.setValues(
            border=f"1px solid {SpyderPalette.COLOR_BACKGROUND_4}",
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_2,
        )
        self.preview_interface.setStyleSheet(
            preview_interface_label_css.toString()
        )

        # Fonts layout
        fonts_grid_layout = QGridLayout()
        fonts_grid_layout.addWidget(self.plain_text_font.fontlabel, 0, 0)
        fonts_grid_layout.addWidget(self.plain_text_font.fontbox, 0, 1)
        fonts_grid_layout.addWidget(self.plain_text_font.sizebox, 0, 2)
        fonts_grid_layout.addWidget(self.app_font.fontlabel, 2, 0)
        fonts_grid_layout.addWidget(self.app_font.fontbox, 2, 1)
        fonts_grid_layout.addWidget(self.app_font.sizebox, 2, 2)
        fonts_grid_layout.setRowStretch(fonts_grid_layout.rowCount(), 1)

        fonts_layout = QVBoxLayout()
        fonts_layout.addLayout(fonts_grid_layout)
        fonts_layout.addSpacing(3)
        fonts_layout.addWidget(system_font_checkbox)
        fonts_layout.addStretch()

        fonts_group.setLayout(fonts_layout)

        # Left options layout
        options_layout = QVBoxLayout()
        options_layout.addWidget(ui_group)
        options_layout.addWidget(fonts_group)
        options_layout.addStretch()

        # Right previews layout
        preview_group = QGroupBox(_("Previews"))
        preview_layout = QVBoxLayout()
        preview_layout.addSpacing(AppStyle.MarginSize)
        preview_layout.addWidget(preview_editor_label)
        preview_layout.addWidget(self.preview_editor)
        preview_layout.addSpacing(2 * AppStyle.MarginSize)
        preview_layout.addWidget(preview_interface_label)
        preview_layout.addWidget(self.preview_interface)
        preview_group.setLayout(preview_layout)

        # Combined layout
        combined_layout = QGridLayout()
        combined_layout.setHorizontalSpacing(AppStyle.MarginSize * 5)
        combined_layout.addLayout(options_layout, 0, 0)
        combined_layout.addWidget(preview_group, 0, 1)

        # Final layout
        # Note: This is necessary to prevent the layout from growing downward
        # indefinitely.
        final_layout = QVBoxLayout()
        final_layout.addLayout(combined_layout)
        final_layout.addStretch()
        self.setLayout(final_layout)

        # Signals and slots
        self.schemes_combobox.currentIndexChanged.connect(
            lambda index: self.update_editor_preview()
        )
        self.schemes_combobox.sig_popup_is_hidden.connect(
            self.update_editor_preview
        )
        self.schemes_combobox.sig_item_in_popup_changed.connect(
            lambda scheme_name: self.update_editor_preview(
                scheme_name=scheme_name
            )
        )
        self.schemes_combobox.currentIndexChanged.connect(self.update_buttons)
        self.schemes_combobox.currentIndexChanged.connect(
            self.on_scheme_changed
        )
        self.plain_text_font.fontbox.currentFontChanged.connect(
            lambda font: self.update_editor_preview()
        )
        self.plain_text_font.fontbox.sig_popup_is_hidden.connect(
            self.update_editor_preview
        )
        self.plain_text_font.fontbox.sig_item_in_popup_changed.connect(
            lambda font_family: self.update_editor_preview(
                scheme_name=None, font_family=font_family
            )
        )
        self.plain_text_font.sizebox.valueChanged.connect(
            lambda value: self.update_editor_preview()
        )
        self.app_font.fontbox.currentFontChanged.connect(
            lambda font: self.update_interface_preview()
        )
        self.app_font.fontbox.sig_popup_is_hidden.connect(
            self.update_interface_preview
        )
        self.app_font.fontbox.sig_item_in_popup_changed.connect(
            self.update_interface_preview
        )
        self.app_font.sizebox.valueChanged.connect(
            lambda value: self.update_interface_preview()
        )
        system_font_checkbox.checkbox.stateChanged.connect(
            self.update_app_font_group
        )

        # Now load the schemes into the editor dialog
        for name in names:
            try:
                self.scheme_editor_dialog.add_color_scheme_stack(name)
            except configparser.NoOptionError:
                # Skip themes that can't be loaded
                pass

        if sys.platform == 'darwin':
            system_font_checkbox.checkbox.setEnabled(False)
        self.update_app_font_group(system_font_checkbox.checkbox.isChecked())
        self.update_combobox()
        self.update_editor_preview()

    def get_font(self, option):
        """Return global font used in Spyder."""
        return get_font(option=option)

    def set_font(self, font, option):
        """Set global font used in Spyder."""
        set_font(font, option=option)

        # The app font can't be set in place. Instead, it requires a restart
        if option != 'app_font':
            # Update fonts for all plugins
            plugins = self.main.widgetlist + self.main.thirdparty_plugins
            for plugin in plugins:
                plugin.update_font()

    def check_theme_changed(self):
        """
        Check if theme actually changed before apply_settings.

        This avoids requesting for a restart if the theme didn't actually
        change.
        """
        current_scheme = self.current_scheme
        saved_scheme = self.get_option('selected', default='')
        theme_changed = (current_scheme != saved_scheme)
        self._theme_changed_during_apply = theme_changed

    def apply_theme_changes(self):
        """Apply changes to theme options."""
        if not self._theme_changed_during_apply:
            # Drop 'selected' from changed_options if theme didn't change.
            # Avoids restart prompt when only font or other options changed.
            self.changed_options.discard('selected')

            # Update preview and plugins font/color scheme
            self.update_editor_preview()
            for plugin_name in PLUGIN_REGISTRY:
                plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
                plugin.update_font()

    # ---- Helpers
    # -------------------------------------------------------------------------
    @property
    def current_scheme_name(self):
        return self.schemes_combobox.currentText()

    @property
    def current_scheme(self):
        return self.scheme_choices_dict[self.current_scheme_name]

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the page is shown."""
        super().showEvent(event)

        if not self._is_shown:
            # Set the right interface font for Mac in the respective combobox,
            # so that preview_interface shows it appropriately.
            if sys.platform == "darwin":
                index = self.app_font.fontbox.findText("SF Pro")
                if index != -1:
                    self.app_font.fontbox.setCurrentIndex(index)

        self._is_shown = True

    # ---- Update contents
    # -------------------------------------------------------------------------
    def update_combobox(self):
        """Populate the combobox contents."""
        # Save currently selected theme (not index, since order may change)
        current_scheme = self.get_option(
            'selected', default='spyder_themes.spyder/dark'
        )

        self.schemes_combobox.blockSignals(True)

        # Use theme manager to get available themes dynamically
        names = THEME_MANAGER.get_available_theme_variants()
        try:
            names.pop(names.index(u'Custom'))
        except ValueError:
            pass

        # Clear existing data
        self.scheme_choices_dict.clear()
        combobox = self.schemes_combobox
        combobox.clear()

        for name in names:
            # Get display name (from config or generate it)
            try:
                display_name = str(self.get_option('{0}/name'.format(name)))
            except configparser.NoOptionError:
                display_name = THEME_MANAGER.get_theme_display_name(name)

            # Add to dictionary and combobox
            self.scheme_choices_dict[display_name] = name
            combobox.addItem(display_name, name)

        # Find and select the current theme (by value, not index)
        index = combobox.findData(current_scheme)

        # Theme not found, default to bundled dark variant
        if index == -1:
            index = combobox.findData('spyder_themes.spyder/dark')

        # Still not found, just use first item
        if index == -1:
            index = 0

        self.schemes_combobox.blockSignals(False)
        self.schemes_combobox.setCurrentIndex(index)

    def update_buttons(self):
        """Enable reset only for built-in theme variants."""
        names = self._builtin_theme_variants()
        self.reset_button.setEnabled(self.current_scheme in names)

    def update_editor_preview(self, scheme_name=None, font_family=None):
        """Update the color scheme of the preview editor and adds text."""
        if scheme_name is None:
            scheme_name = self.current_scheme
        else:
            scheme_name = self.scheme_choices_dict[scheme_name]

        if font_family is None:
            plain_text_font = self.plain_text_font.fontbox.currentFont()
        else:
            plain_text_font = QFont(font_family)

        plain_text_font.setPointSize(self.plain_text_font.sizebox.value())
        self.preview_editor.setup_editor(
            font=plain_text_font,
            color_scheme=scheme_name
        )

    def update_interface_preview(self, font_family=None):
        """Update the interface preview label."""
        if font_family is None:
            app_font = self.app_font.fontbox.currentFont()
        else:
            app_font = QFont(font_family)

        app_font.setPointSize(self.app_font.sizebox.value())
        self.preview_interface.setFont(app_font)

    def update_app_font_group(self, state):
        """Update app font group enabled state."""
        subwidgets = ['fontlabel', 'fontbox', 'sizebox']

        if state:
            for widget in subwidgets:
                getattr(self.app_font, widget).setEnabled(False)
        else:
            for widget in subwidgets:
                getattr(self.app_font, widget).setEnabled(True)

    # ---- Actions
    # -------------------------------------------------------------------------
    def on_scheme_changed(self):
        """
        Handle scheme selection change.

        Only update the preview, don't save to config yet. The theme will be
        saved when user clicks Apply/OK.
        """
        self.update_editor_preview()

    def edit_scheme(self):
        """Edit current scheme."""
        dlg = self.scheme_editor_dialog
        dlg.set_scheme(self.current_scheme)
        dlg.rejected.connect(lambda: self.apply_button_enabled.emit(False))

        if dlg.exec_():
            # Syntax values stay in widgets and ``changed_options`` until the
            # user clicks Apply or OK, which runs save_to_conf/apply_changes.
            self._remove_temp_syntax_options()
            self.scheme_choices_dict.pop("temp", None)
            self.update_editor_preview()

    def set_scheme(self, scheme_name):
        """
        Set the current stack in the dialog to the scheme with 'scheme_name'.
        """
        dlg = self.scheme_editor_dialog
        dlg.set_scheme(scheme_name)

    def reset_to_default(self):
        """Restore initial values for default color schemes."""
        answer = QMessageBox.question(
            self,
            _("Reset to defaults"),
            _(
                "Do you want to reset all syntax highlighting colors to "
                "default values?"
            )
        )

        if answer == QMessageBox.No:
            return

        # Checks that this is indeed a default scheme
        scheme = self.current_scheme
        names = self._builtin_theme_variants()

        if scheme in names:
            try:
                theme_name, ui_mode = scheme.rsplit('/', 1)
                THEME_MANAGER.export_theme_to_config(
                    theme_name, ui_mode, replace=True
                )
            except Exception:
                for key in COLOR_SCHEME_KEYS:
                    option = "{0}/{1}".format(scheme, key)
                    value = CONF.get_default(self.CONF_SECTION, option)
                    self.set_option(option, value)

            self.load_from_conf()
