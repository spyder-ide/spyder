# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""History Widget."""

# Standard library imports
import sys

# Third party imports
from IPython.core.history import HistoryAccessor
from qtpy.QtCore import Signal

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.api.translations import _
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


# --- Constants
# ----------------------------------------------------------------------------
# Maximum number of commands to load from the IPython history
MAX_HISTORY_ENTRIES = 1000


# --- Helpers
# ----------------------------------------------------------------------------
def load_ipython_history(max_entries=MAX_HISTORY_ENTRIES):
    """
    Return the last `max_entries` commands saved in the IPython history.

    An empty list is returned if the history can't be read.
    """
    accessor = None
    try:
        accessor = HistoryAccessor()
        entries = accessor.get_tail(max_entries, include_latest=True)
        return [source for __, __, source in entries]
    except Exception:
        return []
    finally:
        if accessor is not None:
            try:
                accessor.db.close()
            except Exception:
                pass


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
class HistoryWidget(ShellConnectMainWidget):
    """
    History plugin main widget.
    """

    HELP_URL = "https://docs.spyder-ide.org/current/panes/historylog"

    # Signals
    sig_focus_changed = Signal()
    """
    This signal is emitted when the focus of the code editor storing history
    changes.
    """

    def __init__(self, name, plugin, parent):
        super().__init__(name, plugin, parent)

        # Attributes
        self.wrap_action = None
        self.linenumbers_action = None
        self.font = None

        # Commands to show in each new editor. They are loaded only once, when
        # the widget is created.
        self._ipython_history = load_ipython_history()

        # Widgets
        self.find_widget = FindReplace(self)

        # Setup
        self.find_widget.hide()

        # Layout
        # The stack (self._stack) and its layout are created by
        # ShellConnectMainWidget, so we only need to add the find widget.
        layout = self.layout()
        layout.setSpacing(0)
        layout.addWidget(self.find_widget)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('History')

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
        for editor in self._editors():
            editor.toggle_wrap_mode(value)

    @on_conf_change(option='line_numbers')
    def on_line_numbers_update(self, value):
        for editor in self._editors():
            editor.toggle_line_numbers(value)

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

        for editor in self._editors():
            editor.set_font(font)
            editor.set_color_scheme(color_scheme)

    # --- ShellConnectMainWidget API
    # ------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        """Create the (read-only) editor that shows a console's history."""
        editor = SimpleCodeEditor(self)
        editor.setup_editor(
            linenumbers=self.get_conf('line_numbers'),
            language='py',
            color_scheme=self.get_conf('selected', section='appearance'),
            font=self.font,
            wrap=self.get_conf('wrap'),
        )
        editor.setReadOnly(True)
        editor.set_text("\n".join(self._ipython_history))
        editor.set_cursor_position('eof')
        editor.sig_focus_changed.connect(self.sig_focus_changed)
        return editor

    def close_widget(self, editor):
        """Close the editor associated to a console that was closed."""
        editor.sig_focus_changed.disconnect(self.sig_focus_changed)
        editor.close()
        editor.setParent(None)

    def switch_widget(self, editor, old_editor):
        """Point the find widget to the editor of the current console."""
        self.find_widget.set_editor(editor)

    def append_to_history(self, shellwidget, command):
        """
        Append a command to the history of a console.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            Shell widget of the console where the command was entered.
        command: str
            Command to append.
        """
        editor = self.get_widget_for_shellwidget(shellwidget)

        # The widget can be an error message if the kernel failed to start
        if not isinstance(editor, SimpleCodeEditor):
            return

        if not editor.document().isEmpty():
            command = "\n" + command
        editor.append(command)

        if self.get_conf('go_to_eof'):
            editor.set_cursor_position('eof')

    def refresh(self):
        """Update the find widget to use the current editor."""
        if self.count():
            self.find_widget.set_editor(self.current_widget())
        else:
            self.find_widget.set_editor(None)

    # --- Private API
    # ------------------------------------------------------------------------
    def _editors(self):
        """
        Return all editors in the stack.

        Error messages shown for consoles whose kernel failed to start are
        also in the stack, so they are left out.
        """
        widgets = [self._stack.widget(i) for i in range(self._stack.count())]
        return [w for w in widgets if isinstance(w, SimpleCodeEditor)]


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
