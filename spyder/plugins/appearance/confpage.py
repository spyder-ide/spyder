# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Appearance entry in Preferences."""

from qtconsole.styles import dark_color
from qtpy.QtCore import Slot
from qtpy.QtWidgets import (QFontComboBox, QGridLayout, QGroupBox, QMessageBox,
                            QPushButton, QStackedWidget, QVBoxLayout)

from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.config.gui import get_font, is_dark_font_color, set_font
from spyder.config.manager import CONF
from spyder.plugins.appearance.widgets import SchemeEditor
from spyder.utils import syntaxhighlighters
from spyder.utils.palette import QStylePalette
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


class AppearanceConfigPage(PluginConfigPage):

    def __init__(self, plugin, parent):
        super().__init__(plugin, parent)
        self.pre_apply_callback = self.check_color_scheme_notification

        # Notifications for this option are disabled when the plugin is
        # initialized, so we need to restore them here.
        CONF.restore_notifications(section='appearance', option='ui_theme')

    def setup_page(self):
        names = self.get_option("names")
        try:
            names.pop(names.index(u'Custom'))
        except ValueError:
            pass
        custom_names = self.get_option("custom_names", [])

        # Interface options
        theme_group = QGroupBox(_("Main interface"))

        # Interface Widgets
        ui_theme_choices = [
            (_('Automatic'), 'automatic'),
            (_('Light'), 'light'),
            (_('Dark'), 'dark')
        ]
        ui_theme_combo = self.create_combobox(
            _('Interface theme'),
            ui_theme_choices,
            'ui_theme',
            restart=True
        )
        self.ui_combobox = ui_theme_combo.combobox

        themes = ['Spyder 2', 'Spyder 3']
        icon_choices = list(zip(themes, [theme.lower() for theme in themes]))
        icons_combo = self.create_combobox(_('Icon theme'), icon_choices,
                                           'icon_theme', restart=True)

        theme_comboboxes_layout = QGridLayout()
        theme_comboboxes_layout.addWidget(ui_theme_combo.label, 0, 0)
        theme_comboboxes_layout.addWidget(ui_theme_combo.combobox, 0, 1)
        theme_comboboxes_layout.addWidget(icons_combo.label, 1, 0)
        theme_comboboxes_layout.addWidget(icons_combo.combobox, 1, 1)

        theme_layout = QVBoxLayout()
        theme_layout.addLayout(theme_comboboxes_layout)
        theme_group.setLayout(theme_layout)

        # Syntax coloring options
        syntax_group = QGroupBox(_("Syntax highlighting theme"))

        # Syntax Widgets
        edit_button = QPushButton(_("Edit selected scheme"))
        create_button = QPushButton(_("Create new scheme"))
        self.delete_button = QPushButton(_("Delete scheme"))
        self.reset_button = QPushButton(_("Reset to defaults"))

        self.preview_editor = SimpleCodeEditor(self)
        self.stacked_widget = QStackedWidget(self)
        self.scheme_editor_dialog = SchemeEditor(parent=self,
                                                 stack=self.stacked_widget)

        self.scheme_choices_dict = {}
        schemes_combobox_widget = self.create_combobox('', [('', '')],
                                                       'selected')
        self.schemes_combobox = schemes_combobox_widget.combobox

        # Syntax layout
        syntax_layout = QGridLayout(syntax_group)
        btns = [self.schemes_combobox, edit_button, self.reset_button,
                create_button, self.delete_button]
        for i, btn in enumerate(btns):
            syntax_layout.addWidget(btn, i, 1)
        syntax_layout.setColumnStretch(0, 1)
        syntax_layout.setColumnStretch(1, 2)
        syntax_layout.setColumnStretch(2, 1)
        syntax_layout.setContentsMargins(0, 12, 0, 12)

        # Fonts options
        fonts_group = QGroupBox(_("Fonts"))

        # Fonts widgets
        self.plain_text_font = self.create_fontgroup(
            option='font',
            title=_("Plain text"),
            fontfilters=QFontComboBox.MonospacedFonts,
            without_group=True)

        self.rich_text_font = self.create_fontgroup(
            option='rich_font',
            title=_("Rich text"),
            without_group=True)

        # Fonts layouts
        fonts_layout = QGridLayout(fonts_group)
        fonts_layout.addWidget(self.plain_text_font.fontlabel, 0, 0)
        fonts_layout.addWidget(self.plain_text_font.fontbox, 0, 1)
        fonts_layout.addWidget(self.plain_text_font.sizelabel, 0, 2)
        fonts_layout.addWidget(self.plain_text_font.sizebox, 0, 3)
        fonts_layout.addWidget(self.rich_text_font.fontlabel, 1, 0)
        fonts_layout.addWidget(self.rich_text_font.fontbox, 1, 1)
        fonts_layout.addWidget(self.rich_text_font.sizelabel, 1, 2)
        fonts_layout.addWidget(self.rich_text_font.sizebox, 1, 3)
        fonts_layout.setRowStretch(fonts_layout.rowCount(), 1)

        # Left options layout
        options_layout = QVBoxLayout()
        options_layout.addWidget(theme_group)
        options_layout.addWidget(syntax_group)
        options_layout.addWidget(fonts_group)

        # Right preview layout
        preview_group = QGroupBox(_("Preview"))
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_editor)
        preview_group.setLayout(preview_layout)

        # Combined layout
        combined_layout = QGridLayout()
        combined_layout.setRowStretch(0, 1)
        combined_layout.setColumnStretch(1, 100)
        combined_layout.addLayout(options_layout, 0, 0)
        combined_layout.addWidget(preview_group, 0, 1)
        self.setLayout(combined_layout)

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

    def apply_settings(self):
        ui_theme = self.get_option('ui_theme')
        mismatch = self.color_scheme_and_ui_theme_mismatch(
            self.current_scheme, ui_theme)

        if ui_theme == 'automatic':
            if mismatch:
                # Ask for a restart
                self.changed_options.add('ui_theme')
            else:
                # Don't ask for a restart
                if 'ui_theme' in self.changed_options:
                    self.changed_options.remove('ui_theme')
        else:
            if 'ui_theme' in self.changed_options:
                if not mismatch:
                    # Don't ask for a restart
                    self.changed_options.remove('ui_theme')
            else:
                if mismatch:
                    # Ask for a restart
                    self.changed_options.add('ui_theme')

        # We need to restore notifications for these options so they can be
        # changed when the user selects other values for them.
        for option in ['selected', 'ui_theme']:
            CONF.restore_notifications(section='appearance', option=option)

        self.update_combobox()
        self.update_preview()

        return set(self.changed_options)

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

    @property
    def current_ui_theme_index(self):
        return self.ui_combobox.currentIndex()

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
            # Make option value a string to prevent errors when using it
            # as widget text.
            # See spyder-ide/spyder#18929
            self.scheme_choices_dict[
                str(self.get_option('{0}/name'.format(n)))
            ] = n

        if custom_names:
            choices = names + [None] + custom_names
        else:
            choices = names

        combobox = self.schemes_combobox
        combobox.clear()

        for name in choices:
            if name is None:
                continue
            # Make option value a string to prevent errors when using it
            # as widget text.
            # See spyder-ide/spyder#18929
            item_name = str(self.get_option('{0}/name'.format(name)))
            combobox.addItem(item_name, name)

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
                'class Foo(object):\n'
                '    def __init__(self):\n'
                '        bar = 42\n'
                '        print(bar)\n'
                )

        if scheme_name is None:
            scheme_name = self.current_scheme

        self.preview_editor.setup_editor(
            font=get_font(),
            color_scheme=scheme_name,
            show_blanks=False,
            scroll_past_end=False,
        )
        self.preview_editor.set_language('Python')
        self.preview_editor.set_text(text)

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
            default_theme = 'spyder'
            if self.is_dark_interface():
                default_theme = 'spyder/dark'
            self.schemes_combobox.setCurrentIndex(names.index(default_theme))
            self.set_option('selected', default_theme)

            # Delete from custom_names
            custom_names = self.get_option('custom_names', [])
            if scheme_name in custom_names:
                custom_names.remove(scheme_name)
            self.set_option('custom_names', custom_names)

            # Delete config options
            for key in syntaxhighlighters.COLOR_SCHEME_KEYS:
                option = "{0}/{1}".format(scheme_name, key)
                CONF.remove_option(self.CONF_SECTION, option)
            CONF.remove_option(self.CONF_SECTION,
                               "{0}/name".format(scheme_name))

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

    def is_dark_interface(self):
        """
        Check if our interface is dark independently from our config
        system.

        We need to do this because when applying settings we can't
        detect correctly the current theme.
        """
        return dark_color(QStylePalette.COLOR_BACKGROUND_1)

    def color_scheme_and_ui_theme_mismatch(self, color_scheme, ui_theme):
        """
        Detect if there is a mismatch between the current color scheme and
        UI theme.

        Parameters
        ----------
        color_scheme: str
            Name of one of Spyder's color schemes. For instance: 'Zenburn' or
            'Monokai'.
        ui_theme: str
            Name of the one of Spyder's interface themes. This can 'automatic',
            'dark' or 'light'.
        """
        # A dark color scheme is characterized by a light font and viceversa
        is_dark_color_scheme = not is_dark_font_color(color_scheme)
        if ui_theme == 'automatic':
            mismatch = (
                (self.is_dark_interface() and not is_dark_color_scheme) or
                (not self.is_dark_interface() and is_dark_color_scheme)
            )
        else:
            mismatch = (
                (self.is_dark_interface() and ui_theme == 'light') or
                (not self.is_dark_interface() and ui_theme == 'dark')
            )

        return mismatch

    def check_color_scheme_notification(self):
        """
        Check if it's necessary to notify plugins to update their color scheme.
        """
        ui_theme_map = {0: 'automatic', 1: 'light', 2: 'dark'}
        ui_theme = ui_theme_map[self.current_ui_theme_index]
        mismatch = self.color_scheme_and_ui_theme_mismatch(
            self.current_scheme, ui_theme)

        # We don't need to apply the selected color scheme if there's a
        # mismatch between it and the UI theme. Instead, we only we need to ask
        # for a restart.
        if mismatch:
            for option in ['selected', 'ui_theme']:
                CONF.disable_notifications(section='appearance', option=option)
