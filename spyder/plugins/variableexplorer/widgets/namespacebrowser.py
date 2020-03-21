# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Namespace browser widget

This is the main widget used in the Variable Explorer plugin
"""

# Standard library imports
import os
import os.path as osp

# Third library imports (qtpy)
from qtpy.compat import getopenfilenames, getsavefilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QLabel,
                            QMenu, QMessageBox, QVBoxLayout, QWidget)
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.misc import fix_reference_name
from spyder_kernels.utils.nsview import REMOTE_SETTINGS, get_supported_types

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import SpyderWidgetMixin
from spyder.config.base import CHECK_ALL, EXCLUDED_NAMES
from spyder.plugins.variableexplorer.widgets.collectionseditor import (
    RemoteCollectionsEditorTableView)
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard
from spyder.py3compat import PY2, is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils.misc import getcwd_or_home, remove_backslashes
from spyder.widgets.helperwidgets import FinderLineEdit


# Localization
_ = get_translation('spyder')


# Constants
SUPPORTED_TYPES = get_supported_types()
if PY2:
    VALID_VARIABLE_CHARS = r"[a-zA-z0-9_]"
else:
    VALID_VARIABLE_CHARS = r"[^\w+*=¡!¿?'\"#$%&()/<>\-\[\]{}^`´;,|¬]*\w"


class NamespaceBrowser(QWidget, SpyderWidgetMixin):
    """
    Namespace browser (global variables explorer widget).
    """
    DEFAULT_OPTIONS = {
        'dataframe_format': '%.6g',
        'minmax': False,
        'show_special_attributes': False,
        'show_callable_attributes': True,
        # blank_spaces=options['blank_spaces'],
        # scroll_past_end=options['scroll_past_end'],
        # selected=options['selected'],
    }

    # Signals
    sig_option_changed = Signal(str, object)
    sig_collapse = Signal()
    sig_free_memory_requested = Signal()

    def __init__(self, parent, options=DEFAULT_OPTIONS):
        super().__init__(parent)

        self.change_options(self.DEFAULT_OPTIONS)

        # Attributes
        self.is_visible = True
        self.filename = None

        # Widgets
        self.editor = None
        self.shellwidget = None
        self.finder = None

    def setup(self, options=DEFAULT_OPTIONS):
        """
        Setup the namespace browser with provided settings.

        Args:
            dataframe_format (string): default floating-point format for 
                DataFrame editor
        """
        assert self.shellwidget is not None
        self.change_options(options)

        if self.editor is not None:
            if 'minmax' in options:
                # TODO: This is weird...
                # Does it really make sense on that context menu?
                self.editor.setup_menu(self.get_option('minmax'))
            elif 'dataframe_format' in options:
                self.editor.set_dataframe_format(
                    self.get_option('dataframe_format'))
            elif 'blank_spaces' in options:
                pass
            elif 'scroll_past_end' in options:
                pass
            elif 'selected' in options:
                pass

            # TODO: weird call
            self.shellwidget.set_namespace_view_settings()
            self.refresh_table()
        else:
            # Widgets
            self.editor = RemoteCollectionsEditorTableView(
                self,
                data=None,
                shellwidget=self.shellwidget,
                minmax=self.get_option('minmax'),
                dataframe_format=self.get_option('dataframe_format'),
                show_callable_attributes=self.get_option(
                    'show_callable_attributes'),
                show_special_attributes=self.get_option(
                    'show_special_attributes'),
                # blank_spaces=options['blank_spaces'],
                # scroll_past_end=options['scroll_past_end'],
                # selected=options['selected'],
            )

            self.finder = QWidget(self)
            text_finder = NamespacesBrowserFinder(
                self.editor,
                callback=self.editor.set_regex,
                main=self,
                regex_base=VALID_VARIABLE_CHARS,
            )

            # Setup
            self.editor.finder = text_finder
            self.finder.text_finder = text_finder
            self.finder.setVisible(False)

            # Layout
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            finder_layout = QHBoxLayout()
            close_button = self.create_toolbutton(
                'close_finder',
                triggered=self.show_finder,
                icon=self.create_icon('DialogCloseButton'),
            )

            finder_layout.addWidget(close_button)
            finder_layout.addWidget(text_finder)
            finder_layout.setContentsMargins(0, 0, 0, 0)
            self.finder.setLayout(finder_layout)

            layout.addWidget(self.editor)
            layout.addWidget(self.finder)
            self.setLayout(layout)

            # Signals
            self.editor.sig_files_dropped.connect(self.import_data)
            self.editor.sig_free_memory.connect(self.sig_free_memory_requested)
            # self.editor.sig_option_changed.connect(self.sig_option_changed)
            # self.editor.sig_open_editor.connect(self.loading_widget.start)
            # self.editor.sig_editor_shown.connect(self.loading_widget.stop)

    def on_option_update(self, option, value):
        pass

    def get_view_settings(self):
        """
        Return dict editor view settings.
        """
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = self.get_option(name)

        return settings

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to namespace browser"""
        self.shellwidget = shellwidget
        shellwidget.set_namespacebrowser(self)

    # TODO: This feels more like a toggle method, so name should reflect that
    def show_finder(self, set_visible=False):
        """Handle showing/hiding the finder widget."""
        self.finder.text_finder.setText('')
        self.finder.setVisible(set_visible)

        if self.finder.isVisible():
            self.finder.text_finder.setFocus()
        else:
            self.editor.setFocus()

    def refresh_table(self):
        """Refresh variable table"""
        if self.is_visible and self.isVisible():
            self.shellwidget.refresh_namespacebrowser()
            try:
                self.editor.resizeRowToContents()
            except TypeError:
                pass

    def process_remote_view(self, remote_view):
        """Process remote view"""
        if remote_view is not None:
            self.set_data(remote_view)

    def set_var_properties(self, properties):
        """Set properties of variables"""
        if properties is not None:
            self.editor.var_properties = properties

    def set_data(self, data):
        """Set data."""
        if data != self.editor.source_model.get_data():
            self.editor.set_data(data)
            self.editor.adjust_columns()

    # TODO: Seems unused
    def collapse(self):
        """Collapse."""
        self.sig_collapse.emit()

    @Slot(bool)
    @Slot(list)
    def import_data(self, filenames=None):
        """Import data from text file."""
        title = _("Import data")
        if filenames is None:
            if self.filename is None:
                basedir = getcwd_or_home()
            else:
                basedir = osp.dirname(self.filename)
            filenames, _selfilter = getopenfilenames(self, title, basedir,
                                                     iofunctions.load_filters)
            if not filenames:
                return
        elif is_text_string(filenames):
            filenames = [filenames]

        for filename in filenames:
            self.filename = to_text_string(filename)
            if os.name == "nt":
                self.filename = remove_backslashes(self.filename)
            ext = osp.splitext(self.filename)[1].lower()

            if ext not in iofunctions.load_funcs:
                buttons = QMessageBox.Yes | QMessageBox.Cancel
                answer = QMessageBox.question(self, title,
                            _("<b>Unsupported file extension '%s'</b><br><br>"
                              "Would you like to import it anyway "
                              "(by selecting a known file format)?"
                              ) % ext, buttons)
                if answer == QMessageBox.Cancel:
                    return
                formats = list(iofunctions.load_extensions.keys())
                item, ok = QInputDialog.getItem(self, title,
                                                _('Open file as:'),
                                                formats, 0, False)
                if ok:
                    ext = iofunctions.load_extensions[to_text_string(item)]
                else:
                    return

            load_func = iofunctions.load_funcs[ext]
                
            # 'import_wizard' (self.setup_io)
            if is_text_string(load_func):
                # Import data with import wizard
                error_message = None
                try:
                    text, _encoding = encoding.read(self.filename)
                    base_name = osp.basename(self.filename)
                    editor = ImportWizard(self, text, title=base_name,
                                  varname=fix_reference_name(base_name))
                    if editor.exec_():
                        var_name, clip_data = editor.get_data()
                        self.editor.new_value(var_name, clip_data)
                except Exception as error:
                    error_message = str(error)
            else:
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                QApplication.processEvents()
                error_message = self.shellwidget.load_data(self.filename, ext)
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
    
            if error_message is not None:
                QMessageBox.critical(self, title,
                                     _("<b>Unable to load '%s'</b>"
                                       "<br><br>"
                                       "The error message was:<br>%s"
                                       ) % (self.filename, error_message))
            self.refresh_table()

    @Slot()
    def reset_namespace(self):
        # TODO: need to create options propagation from other plugins so that
        # this plugin can update this option as needed since it comes from
        # the ipython console plugin
        warning = self.get_option('show_reset_namespace_warning')
        self.shellwidget.reset_namespace(warning=warning, message=True)
        self.editor.automatic_column_width = True

    @Slot()
    def save_data(self, filename=None):
        """
        Save data.
        """
        if filename is None:
            filename = self.filename
            if filename is None:
                filename = getcwd_or_home()
            filename, _selfilter = getsavefilename(self, _("Save data"),
                                                   filename,
                                                   iofunctions.save_filters)
            if filename:
                self.filename = filename
            else:
                return False

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

        error_message = self.shellwidget.save_namespace(self.filename)

        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        if error_message is not None:
            if 'Some objects could not be saved:' in error_message:
                save_data_message = (
                    _("<b>Some objects could not be saved:</b>")
                    + "<br><br><code>{obj_list}</code>".format(
                        obj_list=error_message.split(': ')[1]))
            else:
                save_data_message = _(
                    "<b>Unable to save current workspace</b>"
                    "<br><br>"
                    "The error message was:<br>") + error_message

            QMessageBox.critical(self, _("Save data"), save_data_message)


class NamespacesBrowserFinder(FinderLineEdit):
    """Textbox for filtering listed variables in the table."""

    def keyPressEvent(self, event):
        """Qt and FilterLineEdit Override."""
        key = event.key()
        if key in [Qt.Key_Up]:
            self._parent.previous_row()
        elif key in [Qt.Key_Down]:
            self._parent.next_row()
        elif key in [Qt.Key_Escape]:
            self._parent.parent().show_finder(set_visible=False)
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            # TODO: Check if an editor needs to be shown
            pass
        else:
            super(NamespacesBrowserFinder, self).keyPressEvent(event)
