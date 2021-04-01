# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""History Widget."""

# Standard library imports
import os.path as osp
import re
import sys

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils.sourcecode import normalize_eols
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.simplecodeeditor import SimpleCodeEditor
from spyder.widgets.tabs import Tabs
from spyder.utils.stylesheet import PANES_TABBAR_STYLESHEET

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
# Maximum number of lines to show
MAX_LINES = 1000

class HistoryWidgetActions:
    # Triggers
    MaximumHistoryEntries = 'maximum_history_entries_action'

    # Toggles
    ToggleWrap = 'toggle_wrap_action'
    ToggleLineNumbers = 'toggle_line_numbers_action'


class HistoryWidgetOptionsMenuSections:
    Main = 'main_section'


# --- Widgets
# ----------------------------------------------------------------------------
class HistoryWidget(PluginMainWidget):
    """
    History plugin main widget.
    """

    # Signals
    sig_focus_changed = Signal()
    """
    This signal is emitted when the focus of the code editor storing history
    changes.
    """

    def __init__(self, name, plugin, parent):
        super().__init__(name, plugin, parent)

        # Attributes
        self.editors = []
        self.filenames = []
        self.tabwidget = None
        self.dockviewer = None
        self.wrap_action = None
        self.linenumbers_action = None
        self.editors = []
        self.filenames = []
        self.font = None

        # Widgets
        self.tabwidget = Tabs(self)
        self.find_widget = FindReplace(self)

        # Setup
        self.tabwidget.setStyleSheet(self._tabs_stylesheet)
        self.find_widget.hide()

        # Layout
        layout = QVBoxLayout()

        # TODO: Move this to the tab container directly
        if sys.platform == 'darwin':
            tab_container = QWidget(self)
            tab_container.setObjectName('tab-container')
            tab_layout = QVBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        layout.addWidget(self.find_widget)
        self.setLayout(layout)

        # Signals
        self.tabwidget.currentChanged.connect(self.refresh)
        self.tabwidget.move_data.connect(self.move_tab)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('History')

    def get_focus_widget(self):
        return self.tabwidget.currentWidget()

    def setup(self):
        # Actions
        self.wrap_action = self.create_action(
            HistoryWidgetActions.ToggleWrap,
            text=_("Wrap lines"),
            toggled=True,
            initial=self.get_conf('wrap'),
            option='wrap'
        )
        self.linenumbers_action = self.create_action(
            HistoryWidgetActions.ToggleLineNumbers,
            text=_("Show line numbers"),
            toggled=True,
            initial=self.get_conf('line_numbers'),
            option='line_numbers'
        )

        # Menu
        menu = self.get_options_menu()
        for item in [self.wrap_action, self.linenumbers_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=HistoryWidgetOptionsMenuSections.Main,
            )

    def update_actions(self):
        pass

    @on_conf_change(option='wrap')
    def on_wrap_update(self, value):
        for editor in self.editors:
            editor.toggle_wrap_mode(value)

    @on_conf_change(option='line_numbers')
    def on_line_numbers_update(self, value):
        for editor in self.editors:
            editor.toggle_line_numbers(value)

    @on_conf_change(option='selected', section='appearance')
    def on_color_scheme_change(self, value):
        for editor in self.editors:
            editor.set_font(self.font)

    # --- Public API
    # ------------------------------------------------------------------------
    def update_font(self, font, color_scheme):
        """
        Update font of the code editor.

        Parameters
        ----------
        font: QFont
            Font object.
        color_scheme: str
            Name of the color scheme to use.
        """
        self.color_scheme = color_scheme
        self.font = font

        for editor in self.editors:
            editor.set_font(font)
            editor.set_color_scheme(color_scheme)

    def move_tab(self, index_from, index_to):
        """
        Move tab.

        Parameters
        ----------
        index_from: int
            Move tab from this index.
        index_to: int
            Move tab to this index.

        Notes
        -----
        Tabs themselves have already been moved by the history.tabwidget.
        """
        filename = self.filenames.pop(index_from)
        editor = self.editors.pop(index_from)

        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)

    def get_filename_text(self, filename):
        """
        Read and return content from filename.

        Parameters
        ----------
        filename: str
            The file path to read.

        Returns
        -------
        str
            Content of the filename.
        """
        # Avoid a possible error when reading the history file
        try:
            text, _ = encoding.read(filename)
        except (IOError, OSError):
            text = "# Previous history could not be read from disk, sorry\n\n"

        text = normalize_eols(text)
        linebreaks = [m.start() for m in re.finditer('\n', text)]

        if len(linebreaks) > MAX_LINES:
            text = text[linebreaks[-MAX_LINES - 1] + 1:]
            # Avoid an error when trying to write the trimmed text to disk.
            # See spyder-ide/spyder#9093.
            try:
                encoding.write(text, filename)
            except (IOError, OSError):
                pass

        return text

    def add_history(self, filename):
        """
        Create a history tab for `filename`.

        Parameters
        ----------
        filename: str
            History filename.
        """

        filename = encoding.to_unicode_from_fs(filename)
        if filename in self.filenames:
            return

        # Widgets
        editor = SimpleCodeEditor(self)

        # Setup
        language = 'py' if osp.splitext(filename)[1] == '.py' else 'bat'
        editor.setup_editor(
            linenumbers=self.get_conf('line_numbers'),
            language=language,
            color_scheme=self.get_conf('selected', section='appearance'),
            font=self.font,
            wrap=self.get_conf('wrap'),
        )
        editor.setReadOnly(True)
        editor.set_text(self.get_filename_text(filename))
        editor.set_cursor_position('eof')
        self.find_widget.set_editor(editor)

        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.filenames.append(filename)
        self.editors.append(editor)
        self.tabwidget.setCurrentIndex(index)
        self.tabwidget.setTabToolTip(index, filename)

        # Signals
        editor.sig_focus_changed.connect(lambda: self.sig_focus_changed.emit())

    @Slot(str, str)
    def append_to_history(self, filename, command):
        """
        Append command to history tab.

        Parameters
        ----------
        filename: str
            History file.
        command: str
            Command to append to history file.
        """
        if not is_text_string(filename):  # filename is a QString
            filename = to_text_string(filename.toUtf8(), 'utf-8')

        index = self.filenames.index(filename)
        command = to_text_string(command)
        self.editors[index].append(command)

        if self.get_conf('go_to_eof'):
            self.editors[index].set_cursor_position('eof')

        self.tabwidget.setCurrentIndex(index)

    def refresh(self):
        """Refresh widget and update find widget on current editor."""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget()
        else:
            editor = None

        self.find_widget.set_editor(editor)

    @property
    def _tabs_stylesheet(self):
        """
        Change style of tabs because we don't have a close button here.
        """
        tabs_stylesheet = PANES_TABBAR_STYLESHEET.get_copy()
        css = tabs_stylesheet.get_stylesheet()
        css['QTabBar::tab'].setValues(padding='4px')
        return tabs_stylesheet.to_string()


def test():
    """Run history widget."""
    from spyder.utils.qthelpers import qapplication
    from unittest.mock import MagicMock

    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'historylog'

    app = qapplication(test_time=8)
    widget = HistoryWidget('historylog', plugin_mock, None)
    widget._setup()
    widget.setup()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
