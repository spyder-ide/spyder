# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import fnmatch
import math
import os.path as osp
import re

# Third party imports
from qtpy import PYQT5, PYQT6
from qtpy.QtCore import Signal
from qtpy.QtGui import QFontMetricsF
from qtpy.QtWidgets import QInputDialog, QLabel, QStackedWidget, QVBoxLayout

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.findinfiles.widgets.results_browser import (
    ON, ResultsBrowser)
from spyder.plugins.findinfiles.widgets.combobox import (
    MAX_PATH_HISTORY, SearchInComboBox)
from spyder.plugins.findinfiles.widgets.search_thread import SearchThread
from spyder.utils.misc import regexp_error_msg
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.comboboxes import PatternComboBox
from spyder.widgets.helperwidgets import PaneEmptyWidget


# ---- Constants
# -----------------------------------------------------------------------------
MAIN_TEXT_COLOR = SpyderPalette.COLOR_TEXT_1
MAX_COMBOBOX_WIDTH = AppStyle.FindMinWidth + 80  # In pixels
MIN_COMBOBOX_WIDTH = AppStyle.FindMinWidth - 80  # In pixels


# ---- Enums
# -----------------------------------------------------------------------------
class FindInFilesWidgetActions:
    # Triggers
    Find = 'find_action'
    MaxResults = 'max_results_action'

    # Toggles
    ToggleCase = 'toggle_case_action'
    ToggleExcludeCase = 'toggle_exclude_case_action'
    ToggleExcludeRegex = 'togle_use_regex_on_exlude_action'
    ToggleMoreOptions = 'toggle_more_options_action'
    ToggleSearchRegex = 'toggle_use_regex_on_search_action'


class FindInFilesWidgetToolbars:
    Exclude = 'exclude_toolbar'
    Location = 'location_toolbar'


class FindInFilesWidgetMainToolbarSections:
    Main = 'main_section'


class FindInFilesWidgetExcludeToolbarSections:
    Main = 'main_section'


class FindInFilesWidgetLocationToolbarSections:
    Main = 'main_section'


class FindInFilesWidgetToolbarItems:
    SearchPatternCombo = 'pattern_combo'
    SearchInLabel = 'search_in_label'
    ExcludeLabel = 'exclude_label'
    ExcludePatternCombo = 'exclude_pattern_combo'
    Stretcher1 = 'stretcher_1'
    SearchInCombo = 'search_in_combo'
    Stretcher2 = 'stretcher_2'


# ---- Main widget
# -----------------------------------------------------------------------------
class FindInFilesWidget(PluginMainWidget):
    """
    Find in files main widget.
    """

    # PluginMainWidget constants
    ENABLE_SPINNER = True
    MARGIN_TOP = AppStyle.MarginSize + 5

    # Other constants
    REGEX_INVALID = f"background-color:{SpyderPalette.COLOR_ERROR_2};"
    REGEX_ERROR = _("Regular expression error")

    # Signals
    sig_edit_goto_requested = Signal(str, int, str, int, int)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    start_column: int
        Starting column of found word.
    end_column:
        Ending column of found word.
    """

    sig_finished = Signal()
    """
    This signal is emitted to inform the search process has finished.
    """

    sig_max_results_reached = Signal()
    """
    This signal is emitted to inform the search process has finished due
    to reaching the maximum number of results.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        if PYQT5 or PYQT6:
            super().__init__(name, plugin, parent=parent)
        else:
            PluginMainWidget.__init__(self, name, plugin, parent=parent)
        self.set_conf('text_color', MAIN_TEXT_COLOR)
        self.set_conf('hist_limit', MAX_PATH_HISTORY)

        # Attributes
        self.text_color = self.get_conf('text_color')
        self.supported_encodings = self.get_conf('supported_encodings')
        self.search_thread = None
        self.running = False
        self.more_options_action = None
        self.extras_toolbar = None
        self._search_in_label_width = None
        self._exclude_label_width = None
        self._is_shown = False
        self._is_first_time = False

        search_text = self.get_conf('search_text', '')
        path_history = self.get_conf('path_history', [])
        exclude = self.get_conf('exclude')

        if not isinstance(search_text, (list, tuple)):
            search_text = [search_text]

        if not isinstance(exclude, (list, tuple)):
            exclude = [exclude]

        if not isinstance(path_history, (list, tuple)):
            path_history = [path_history]

        # Widgets
        self.pane_empty = PaneEmptyWidget(
            self,
            "find_empty",
            _("Nothing searched for yet"),
            _("Search the content of text files in any directory using the "
              "search box.")
        )

        self.search_text_edit = PatternComboBox(
            self,
            items=search_text,
            adjust_to_minimum=False,
            id_=FindInFilesWidgetToolbarItems.SearchPatternCombo
        )
        self.search_text_edit.lineEdit().setPlaceholderText(
            _('Write text to search'))

        self.search_in_label = QLabel(_('Search in:'))
        self.search_in_label.ID = FindInFilesWidgetToolbarItems.SearchInLabel

        self.exclude_label = QLabel(_('Exclude:'))
        self.exclude_label.ID = FindInFilesWidgetToolbarItems.ExcludeLabel

        self.path_selection_combo = SearchInComboBox(
            path_history,
            self,
            id_=FindInFilesWidgetToolbarItems.SearchInCombo
        )
        self.path_selection_combo.setMinimumSize(
            MIN_COMBOBOX_WIDTH, AppStyle.FindHeight
        )
        self.path_selection_combo.setMaximumWidth(MAX_COMBOBOX_WIDTH)

        self.exclude_pattern_edit = PatternComboBox(
            self,
            exclude,
            _("Exclude pattern"),
            id_=FindInFilesWidgetToolbarItems.ExcludePatternCombo
        )
        self.exclude_pattern_edit.setMinimumSize(
            MIN_COMBOBOX_WIDTH, AppStyle.FindHeight
        )
        self.exclude_pattern_edit.setMaximumWidth(MAX_COMBOBOX_WIDTH)

        self.result_browser = ResultsBrowser(
            self,
            text_color=self.text_color,
            max_results=self.get_conf('max_results'),
        )

        # Setup
        exclude_idx = self.get_conf('exclude_index', None)
        if (exclude_idx is not None and exclude_idx >= 0
                and exclude_idx < self.exclude_pattern_edit.count()):
            self.exclude_pattern_edit.setCurrentIndex(exclude_idx)

        search_in_index = self.get_conf('search_in_index', None)
        self.path_selection_combo.set_current_searchpath_index(
            search_in_index)

        # Layout
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.addWidget(self.result_browser)
        self.stacked_widget.addWidget(self.pane_empty)

        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

        # Signals
        self.path_selection_combo.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        self.search_text_edit.valid.connect(lambda valid: self.find())
        self.exclude_pattern_edit.valid.connect(lambda valid: self.find())
        self.result_browser.sig_edit_goto_requested.connect(
            self.sig_edit_goto_requested)
        self.result_browser.sig_max_results_reached.connect(
            self.sig_max_results_reached)
        self.result_browser.sig_max_results_reached.connect(
            self._stop_and_reset_thread)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Find")

    def get_focus_widget(self):
        return self.search_text_edit

    def setup(self):
        self.search_regexp_action = self.create_action(
            FindInFilesWidgetActions.ToggleSearchRegex,
            text=_('Regular expression'),
            tip=_('Use regular expressions'),
            icon=self.create_icon('regex'),
            toggled=True,
            initial=self.get_conf('search_text_regexp'),
            option='search_text_regexp'
        )
        self.case_action = self.create_action(
            FindInFilesWidgetActions.ToggleExcludeCase,
            text=_("Case sensitive"),
            tip=_("Case sensitive search"),
            icon=self.create_icon("format_letter_case"),
            toggled=True,
            initial=self.get_conf('case_sensitive'),
            option='case_sensitive'
        )
        self.find_action = self.create_action(
            FindInFilesWidgetActions.Find,
            text=_("&Find in files"),
            tip=_("Search text"),
            icon=self.create_icon('find'),
            triggered=self.find,
            register_shortcut=False,
        )
        self.exclude_regexp_action = self.create_action(
            FindInFilesWidgetActions.ToggleExcludeRegex,
            text=_('Regular expression'),
            tip=_('Use regular expressions'),
            icon=self.create_icon('regex'),
            toggled=True,
            initial=self.get_conf('exclude_regexp'),
            option='exclude_regexp'
        )
        self.exclude_case_action = self.create_action(
            FindInFilesWidgetActions.ToggleCase,
            text=_("Exclude case sensitive"),
            tip=_("Exclude case sensitive"),
            icon=self.create_icon("format_letter_case"),
            toggled=True,
            initial=self.get_conf('exclude_case_sensitive'),
            option='exclude_case_sensitive'
        )
        self.more_options_action = self.create_action(
            FindInFilesWidgetActions.ToggleMoreOptions,
            text=_('Show advanced options'),
            tip=_('Show advanced options'),
            icon=self.create_icon("options_more"),
            toggled=True,
            initial=self.get_conf('more_options'),
            option='more_options'
        )
        self.set_max_results_action = self.create_action(
            FindInFilesWidgetActions.MaxResults,
            text=_('Set maximum number of results'),
            icon=self.create_icon("transparent"),
            tip=_('Set maximum number of results'),
            triggered=lambda x=None: self.set_max_results(),
        )

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.search_text_edit, self.find_action,
                     self.search_regexp_action, self.case_action,
                     self.more_options_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=FindInFilesWidgetMainToolbarSections.Main,
            )

        # Exclude Toolbar
        self.extras_toolbar = self.create_toolbar(
            FindInFilesWidgetToolbars.Exclude)

        stretcher1 = self.create_stretcher(
            FindInFilesWidgetToolbarItems.Stretcher1)
        for item in [self.exclude_label, self.exclude_pattern_edit,
                     self.exclude_regexp_action, stretcher1]:
            self.add_item_to_toolbar(
                item,
                toolbar=self.extras_toolbar,
                section=FindInFilesWidgetExcludeToolbarSections.Main,
            )

        # Location toolbar
        location_toolbar = self.create_toolbar(
            FindInFilesWidgetToolbars.Location)
        stretcher2 = self.create_stretcher(
            FindInFilesWidgetToolbarItems.Stretcher2)
        for item in [self.search_in_label, self.path_selection_combo,
                     stretcher2]:
            self.add_item_to_toolbar(
                item,
                toolbar=location_toolbar,
                section=FindInFilesWidgetLocationToolbarSections.Main,
            )

        menu = self.get_options_menu()
        self.add_item_to_menu(
            self.set_max_results_action,
            menu=menu,
        )

        # Set pane_empty widget at the beginning
        self.stacked_widget.setCurrentWidget(self.pane_empty)

    def update_actions(self):
        self.find_action.setIcon(self.create_icon(
            'stop' if self.running else 'find')
        )

        if self.extras_toolbar and self.more_options_action:
            self.extras_toolbar.setVisible(
                self.more_options_action.isChecked())

    @on_conf_change(option='more_options')
    def on_more_options_update(self, value):
        if value:
            icon = self.create_icon('options_less')
            tip = _('Hide advanced options')
        else:
            icon = self.create_icon('options_more')
            tip = _('Show advanced options')

        if self.extras_toolbar:
            self.extras_toolbar.setVisible(value)

        # These adjustments can only be done when the widget is visible.
        if self._is_shown:
            if value:
                # Resize either the search_in or exclude label so that their
                # comboboxes are aligned to the left.
                if self._search_in_label_width > self._exclude_label_width:
                    self.exclude_label.setMinimumSize(
                        self._exclude_label_width +
                        (self._search_in_label_width -
                         self._exclude_label_width),
                        AppStyle.FindHeight
                    )
                else:
                    self.search_in_label.setMinimumSize(
                        self._search_in_label_width +
                        (self._exclude_label_width -
                         self._search_in_label_width),
                        AppStyle.FindHeight
                    )
            else:
                # Restore initial search_in label width when it's shorter than
                # exclude_label to not show an empty space next to it.
                if self._search_in_label_width < self._exclude_label_width:
                    self.search_in_label.setMinimumSize(
                        self._search_in_label_width,
                        AppStyle.FindHeight
                    )

        if self.more_options_action:
            self.more_options_action.setIcon(icon)
            self.more_options_action.setToolTip(tip)

    @on_conf_change(option='max_results')
    def on_max_results_update(self, value):
        self.result_browser.set_max_results(value)

    # ---- Qt methods
    # ------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            # Save default widths of search_in and exclude labels
            self._search_in_label_width = self.search_in_label.size().width()

            if not self.extras_toolbar.isVisible():
                # This correctly computes the exclude label width when the
                # extras_toolbar is not visible.
                metrics = QFontMetricsF(self.font())
                exclude_text_width = metrics.width(self.exclude_label.text())
                self._exclude_label_width = (
                    math.ceil(exclude_text_width) + self.font().pointSize()
                )
            else:
                self._exclude_label_width = self.exclude_label.size().width()

            self._is_shown = True

        super().showEvent(event)

    def resizeEvent(self, event):
        """Adjustments when the widget is resized."""
        super().resizeEvent(event)

        # This recomputes the result items width according to this widget's
        # width, which makes the UI be rendered as expected.
        # NOTE: Don't debounce or throttle `set_width` because then it wouldn't
        # do its job as expected.
        self.result_browser.set_width()

    # ---- Private API
    # ------------------------------------------------------------------------
    def _get_options(self):
        """
        Get search options.
        """
        text_re = self.search_regexp_action.isChecked()
        exclude_re = self.exclude_regexp_action.isChecked()
        case_sensitive = self.case_action.isChecked()

        # Clear fields
        self.search_text_edit.lineEdit().setStyleSheet("")
        self.exclude_pattern_edit.lineEdit().setStyleSheet("")
        self.exclude_pattern_edit.setToolTip("")
        self.search_text_edit.setToolTip("")

        utext = str(self.search_text_edit.currentText())
        if not utext:
            return

        try:
            texts = [(utext.encode('utf-8'), 'utf-8')]
        except UnicodeEncodeError:
            texts = []
            for enc in self.supported_encodings:
                try:
                    texts.append((utext.encode(enc), enc))
                except UnicodeDecodeError:
                    pass

        exclude = str(self.exclude_pattern_edit.currentText())

        if not case_sensitive:
            texts = [(text[0].lower(), text[1]) for text in texts]

        file_search = self.path_selection_combo.is_file_search()
        path = self.path_selection_combo.get_current_searchpath()

        if not exclude_re:
            items = [fnmatch.translate(item.strip())
                     for item in exclude.split(",")
                     if item.strip() != '']
            exclude = '|'.join(items)

        # Validate exclude regular expression
        if exclude:
            error_msg = regexp_error_msg(exclude)
            if error_msg:
                exclude_edit = self.exclude_pattern_edit.lineEdit()
                exclude_edit.setStyleSheet(self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + ': ' + str(error_msg)
                self.exclude_pattern_edit.setToolTip(tooltip)
                return None
            else:
                exclude = re.compile(exclude)

        # Validate text regular expression
        if text_re:
            error_msg = regexp_error_msg(texts[0][0])
            if error_msg:
                self.search_text_edit.lineEdit().setStyleSheet(
                    self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + ': ' + str(error_msg)
                self.search_text_edit.setToolTip(tooltip)
                return None
            else:
                texts = [(re.compile(x[0]), x[1]) for x in texts]

        return (path, file_search, exclude, texts, text_re, case_sensitive)

    def _update_options(self):
        """
        Extract search options from widgets and set the corresponding option.
        """
        hist_limit = self.get_conf('hist_limit')
        search_texts = [str(self.search_text_edit.itemText(index))
                        for index in range(self.search_text_edit.count())]
        excludes = [str(self.exclude_pattern_edit.itemText(index))
                    for index in range(self.exclude_pattern_edit.count())]
        path_history = self.path_selection_combo.get_external_paths()

        self.set_conf('path_history', path_history)
        self.set_conf('search_text', search_texts[:hist_limit])
        self.set_conf('exclude', excludes[:hist_limit])
        self.set_conf('path_history', path_history[-hist_limit:])
        self.set_conf(
            'exclude_index', self.exclude_pattern_edit.currentIndex())
        self.set_conf(
            'search_in_index', self.path_selection_combo.currentIndex())

    def _handle_search_complete(self, completed):
        """
        Current search thread has finished.
        """
        self.result_browser.set_sorting(ON)
        self.result_browser.set_width()
        self.result_browser.expandAll()
        if self.search_thread is None:
            return

        self.sig_finished.emit()
        found = self.search_thread.get_results()
        self._stop_and_reset_thread()
        if found is not None:
            self.result_browser.show()

        self.stop_spinner()
        self.update_actions()

    def _stop_and_reset_thread(self, ignore_results=False):
        """Stop current search thread and clean-up."""
        if self.search_thread is not None:
            if self.search_thread.isRunning():
                if ignore_results:
                    self.search_thread.sig_finished.disconnect(
                        self._handle_search_complete)
                self.search_thread.stop()
                self.search_thread.wait()

            self.search_thread.setParent(None)
            self.search_thread = None

        self.running = False
        self.stop_spinner()
        self.update_actions()

    # ---- Public API
    # ------------------------------------------------------------------------
    @property
    def path(self):
        """Return the current path."""
        return self.path_selection_combo.path

    @property
    def project_path(self):
        """Return the current project path."""
        return self.path_selection_combo.project_path

    @property
    def file_path(self):
        """Return the current file path."""
        return self.path_selection_combo.file_path

    def set_directory(self, directory):
        """
        Set directory as current path.

        Parameters
        ----------
        directory: str
            Directory path string.
        """
        self.path_selection_combo.path = osp.abspath(directory)

    def set_project_path(self, path):
        """
        Set path as current project path.

        Parameters
        ----------
        path: str
            Project path string.
        """
        self.path_selection_combo.set_project_path(path)

    def disable_project_search(self):
        """Disable project search path in combobox."""
        self.path_selection_combo.set_project_path(None)

    def set_file_path(self, path):
        """
        Set path as current file path.

        Parameters
        ----------
        path: str
            File path string.
        """
        self.path_selection_combo.file_path = path

    def set_search_text(self, text):
        """
        Set current search text.

        Parameters
        ----------
        text: str
            Search string.

        Notes
        -----
        If `text` is empty, focus will be given to the search lineedit and no
        search will be performed.
        """
        if text:
            self.search_text_edit.add_text(text)
            self.search_text_edit.lineEdit().selectAll()

        self.search_text_edit.setFocus()

    def find(self):
        """
        Start/stop find action.

        Notes
        -----
        If there is no search running, this will start the search. If there is
        a search running, this will stop it.
        """
        # Show result_browser the first time a user performs a search and leave
        # it shown afterwards.
        if not self._is_first_time:
            self.stacked_widget.setCurrentWidget(self.result_browser)
            self._is_first_time = True

        if self.running:
            self.stop()
        else:
            self.start()

    def stop(self):
        """Stop find thread."""
        self._stop_and_reset_thread()

    def start(self):
        """Start find thread."""
        options = self._get_options()
        if options is None:
            return

        self._stop_and_reset_thread(ignore_results=True)
        search_text = self.search_text_edit.currentText()

        # Update and set options
        self._update_options()

        # Setup result_browser
        self.result_browser.set_path(options[0])
        self.result_browser.longest_file_item = ''
        self.result_browser.longest_line_item = ''

        # Start
        self.running = True
        self.start_spinner()
        self.search_thread = SearchThread(
            None,
            search_text,
            self.text_color,
            self.get_conf('max_results')
        )
        self.search_thread.sig_finished.connect(self._handle_search_complete)
        self.search_thread.sig_file_match.connect(
            self.result_browser.append_file_result
        )
        self.search_thread.sig_line_match.connect(
            self.result_browser.append_result
        )
        self.result_browser.clear_title(search_text)
        self.search_thread.initialize(*self._get_options())
        self.search_thread.start()
        self.update_actions()

    def add_external_path(self, path):
        """
        Parameters
        ----------
        path: str
            Path to add to combobox.
        """
        self.path_selection_combo.add_external_path(path)

    def set_max_results(self, value=None):
        """
        Set maximum amount of results to add to the result browser.

        Parameters
        ----------
        value: int, optional
            Number of results. If None an input dialog will be used.
            Default is None.
        """
        if value is None:
            # Create dialog
            dialog = QInputDialog(self)

            # Set dialog properties
            dialog.setModal(False)
            dialog.setWindowTitle(_('Max results'))
            dialog.setLabelText(_('Set maximum number of results: '))
            dialog.setInputMode(QInputDialog.IntInput)
            dialog.setIntStep(1)
            dialog.setIntValue(self.get_conf('max_results'))

            # In order to show the right number of results when max_results is
            # reached, we can't allow users to introduce less than 2 in this
            # dialog. Since that value seems a bit arbitrary, we decided to set
            # it to 5.
            # See spyder-ide/spyder#16256
            dialog.setIntRange(5, 10000)

            # Connect slot
            dialog.intValueSelected.connect(
                lambda value: self.set_conf('max_results', value))

            dialog.show()
        else:
            self.set_conf('max_results', value)


# ---- Test
# -----------------------------------------------------------------------------
def test():
    """
    Run Find in Files widget test.
    """
    # Standard library imports
    from os.path import dirname
    import sys
    from unittest.mock import MagicMock

    # Local imports
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'find_in_files'
    widget = FindInFilesWidget('find_in_files', plugin=plugin_mock)
    widget.CONF_SECTION = 'find_in_files'
    widget._setup()
    widget.setup()
    widget.resize(640, 480)
    widget.show()
    external_paths = [
        dirname(__file__),
        dirname(dirname(__file__)),
        dirname(dirname(dirname(__file__))),
        dirname(dirname(dirname(dirname(__file__)))),
    ]
    for path in external_paths:
        widget.add_external_path(path)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
