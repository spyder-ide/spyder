# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Namespace browser widget.

This is the main widget used in the Variable Explorer plugin
"""

# Standard library imports
import os
import os.path as osp

# Third library imports
from qtpy import PYQT5
from qtpy.compat import getopenfilenames, getsavefilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QInputDialog,
                            QMessageBox, QVBoxLayout, QWidget)
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.misc import fix_reference_name
from spyder_kernels.utils.nsview import REMOTE_SETTINGS

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.widgets.collectionseditor import RemoteCollectionsEditorTableView
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard
from spyder.utils import encoding
from spyder.utils.misc import getcwd_or_home, remove_backslashes
from spyder.widgets.helperwidgets import FinderWidget


# Localization
_ = get_translation('spyder')

# Constants
VALID_VARIABLE_CHARS = r"[^\w+*=¡!¿?'\"#$%&()/<>\-\[\]{}^`´;,|¬]*\w"


class NamespaceBrowser(QWidget, SpyderWidgetMixin):
    """
    Namespace browser (global variables explorer widget).
    """
    # This is necessary to test the widget separately from its plugin
    CONF_SECTION = 'variable_explorer'

    # Signals
    sig_free_memory_requested = Signal()
    sig_start_spinner_requested = Signal()
    sig_stop_spinner_requested = Signal()
    sig_hide_finder_requested = Signal()

    def __init__(self, parent):
        if PYQT5:
            super().__init__(parent=parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Attributes
        self.filename = None

        # Widgets
        self.editor = None
        self.shellwidget = None
        self.finder = None

    def toggle_finder(self, show):
        """Show and hide the finder."""
        self.finder.set_visible(show)
        if not show:
            self.editor.setFocus()

    def do_find(self, text):
        """Search for text."""
        if self.editor is not None:
            self.editor.do_find(text)

    def finder_is_visible(self):
        """Check if the finder is visible."""
        if self.finder is None:
            return False
        return self.finder.isVisible()

    def setup(self):
        """
        Setup the namespace browser with provided options.
        """
        assert self.shellwidget is not None

        if self.editor is not None:
            self.shellwidget.set_namespace_view_settings()
            self.refresh_table()
        else:
            # Widgets
            self.editor = RemoteCollectionsEditorTableView(
                self,
                data=None,
                shellwidget=self.shellwidget,
                create_menu=False,
            )
            key_filter_dict = {
                Qt.Key_Up: self.editor.previous_row,
                Qt.Key_Down: self.editor.next_row
                }
            self.finder = FinderWidget(
                self, find_on_change=True,
                regex_base=VALID_VARIABLE_CHARS,
                key_filter_dict=key_filter_dict)

            # Signals
            self.editor.sig_files_dropped.connect(self.import_data)
            self.editor.sig_free_memory_requested.connect(
                self.sig_free_memory_requested)
            self.editor.sig_editor_creation_started.connect(
                self.sig_start_spinner_requested)
            self.editor.sig_editor_shown.connect(
                self.sig_stop_spinner_requested)

            self.finder.sig_find_text.connect(self.do_find)
            self.finder.sig_hide_finder_requested.connect(
                self.sig_hide_finder_requested)

            # Layout
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.editor)
            layout.addSpacing(1)
            layout.addWidget(self.finder)
            self.setLayout(layout)

    def get_view_settings(self):
        """Return dict editor view settings"""
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = self.get_conf(name)

        return settings

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to namespace browser"""
        self.shellwidget = shellwidget
        shellwidget.set_namespacebrowser(self)

    def refresh_table(self):
        """Refresh variable table."""
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
        elif isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            self.filename = str(filename)
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
                    ext = iofunctions.load_extensions[str(item)]
                else:
                    return

            load_func = iofunctions.load_funcs[ext]
                
            # 'import_wizard' (self.setup_io)
            if isinstance(load_func, str):
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

    def reset_namespace(self):
        warning = self.get_conf(
            section='ipython_console',
            option='show_reset_namespace_warning'
        )
        self.shellwidget.reset_namespace(warning=warning, message=True)
        self.editor.automatic_column_width = True

    def save_data(self, filename=None):
        """Save data"""
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
