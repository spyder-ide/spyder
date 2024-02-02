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
from pickle import UnpicklingError
import tarfile

# Third library imports
from qtpy import PYQT5, PYQT6
from qtpy.compat import getopenfilenames, getsavefilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QInputDialog, QMessageBox,
                            QVBoxLayout, QStackedLayout, QWidget)
from spyder_kernels.comms.commbase import CommError
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.misc import fix_reference_name
from spyder_kernels.utils.nsview import REMOTE_SETTINGS

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.utils import IMPORT_EXT
from spyder.widgets.collectionseditor import RemoteCollectionsEditorTableView
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard
from spyder.utils import encoding
from spyder.utils.misc import getcwd_or_home, remove_backslashes
from spyder.widgets.helperwidgets import FinderWidget, PaneEmptyWidget


# Constants
VALID_VARIABLE_CHARS = r"[^\w+*=¡!¿?'\"#$%&()/<>\-\[\]{}^`´;,|¬]*\w"

# Max time before giving up when making a blocking call to the kernel
CALL_KERNEL_TIMEOUT = 30


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

    sig_show_figure_requested = Signal(bytes, str, object)
    """
    This is emitted to request that a figure be shown in the Plots plugin.

    Parameters
    ----------
    image: bytes
        The image to show.
    mime_type: str
        The image's mime type.
    shellwidget: ShellWidget
        The shellwidget associated with the figure.
    """

    def __init__(self, parent):
        if PYQT5 or PYQT6:
            super().__init__(parent=parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Attributes
        self.filename = None
        self.plots_plugin_enabled = False

        # Widgets
        self.editor = None
        self.shellwidget = None
        self.finder = None
        self.pane_empty = PaneEmptyWidget(
            self,
            "variable-explorer",
            _("No variables to show"),
            _("Run code in the Editor or IPython console to see any "
              "global variables listed here for exploration and editing.")
        )

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
            self.set_namespace_view_settings()
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
                self,
                find_on_change=True,
                regex_base=VALID_VARIABLE_CHARS,
                key_filter_dict=key_filter_dict
            )

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
            self.stack_layout = QStackedLayout()
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self.editor)
            layout.addWidget(self.finder)

            self.table_widget = QWidget(self)
            self.table_widget.setLayout(layout)
            self.stack_layout.addWidget(self.table_widget)
            self.stack_layout.addWidget(self.pane_empty)
            self.setLayout(self.stack_layout)
            self.set_pane_empty()
            self.editor.source_model.sig_setting_data.connect(
                self.set_pane_empty)

    def set_pane_empty(self):
        if not self.editor.source_model.get_data():
            self.stack_layout.setCurrentWidget(self.pane_empty)
        else:
            self.stack_layout.setCurrentWidget(self.table_widget)

    def get_view_settings(self):
        """Return dict editor view settings"""
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = self.get_conf(name)

        return settings

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to namespace browser"""
        self.shellwidget = shellwidget

    def refresh_table(self):
        """Refresh variable table."""
        self.refresh_namespacebrowser()
        try:
            self.editor.resizeRowToContents()
            self.set_pane_empty()
        except TypeError:
            pass

    @Slot(dict)
    def update_view(self, kernel_state):
        """
        Update namespace view and other properties from a new kernel state.

        Parameters
        ----------
        kernel_state: dict
            A new kernel state. The structure of this dictionary is defined in
            the `SpyderKernel.get_state` method of Spyder-kernels.
        """
        if "namespace_view" in kernel_state:
            self.process_remote_view(kernel_state.pop("namespace_view"))
        if "var_properties" in kernel_state:
            self.set_var_properties(kernel_state.pop("var_properties"))

    def refresh_namespacebrowser(self, *, interrupt=True):
        """Refresh namespace browser"""
        if not self.shellwidget.spyder_kernel_ready:
            return
        self.shellwidget.call_kernel(
            interrupt=interrupt,
            callback=self.process_remote_view
        ).get_namespace_view()

        self.shellwidget.call_kernel(
            interrupt=interrupt,
            callback=self.set_var_properties
        ).get_var_properties()

    def set_namespace_view_settings(self):
        """Set the namespace view settings"""
        if not self.shellwidget.spyder_kernel_ready:
            return
        settings = self.get_view_settings()
        self.shellwidget.set_kernel_configuration(
            "namespace_view_settings", settings
        )

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
            extension = osp.splitext(self.filename)[1].lower()

            if extension == '.spydata':
                buttons = QMessageBox.Yes | QMessageBox.Cancel
                answer = QMessageBox.warning(
                    self,
                    title,
                    _("<b>Warning: %s files can contain malicious code!</b>"
                      "<br><br>"
                      "Do not continue unless this file is from a trusted "
                      "source. Would you like to import it "
                      "anyway?") % extension,
                    buttons
                )

                if answer == QMessageBox.Cancel:
                    return
            if extension not in iofunctions.load_funcs:
                buttons = QMessageBox.Yes | QMessageBox.Cancel
                answer = QMessageBox.question(
                    self,
                    title,
                    _("<b>Unsupported file extension '%s'</b>"
                      "<br><br>"
                      "Would you like to import it anyway by selecting a "
                      "known file format?") % extension,
                    buttons
                )
                if answer == QMessageBox.Cancel:
                    return
                formats = list(iofunctions.load_extensions.keys())
                item, ok = QInputDialog.getItem(self, title,
                                                _('Open file as:'),
                                                formats, 0, False)
                if ok:
                    extension = iofunctions.load_extensions[str(item)]
                else:
                    return

            load_func = iofunctions.load_funcs[extension]

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
                error_message = self.load_data(self.filename, extension)
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()

            if error_message is not None:
                QMessageBox.critical(self, title,
                                     _("<b>Unable to load '%s'</b>"
                                       "<br><br>"
                                       "The error message was:<br>%s"
                                       ) % (self.filename, error_message))
            self.refresh_table()

    def load_data(self, filename, ext):
        """Load data from a file."""
        if not self.shellwidget.spyder_kernel_ready:
            return
        overwrite = False
        if self.editor.var_properties:
            message = _('Do you want to overwrite old '
                        'variables (if any) in the namespace '
                        'when loading the data?')
            buttons = QMessageBox.Yes | QMessageBox.No
            result = QMessageBox.question(
                self, _('Data loading'), message, buttons)
            overwrite = result == QMessageBox.Yes
        try:
            return self.shellwidget.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT).load_data(
                    filename, ext, overwrite=overwrite)
        except ImportError as msg:
            module = str(msg).split("'")[1]
            msg = _("Spyder is unable to open the file "
                    "you're trying to load because <tt>{module}</tt> is "
                    "not installed. Please install "
                    "this package in your working environment."
                    "<br>").format(module=module)
            return msg
        except TimeoutError:
            msg = _("Data is too big to be loaded")
            return msg
        except tarfile.ReadError:
            # Fixes spyder-ide/spyder#19126
            msg = _("The file could not be opened successfully. Recall that "
                    "the Variable Explorer supports the following file "
                    "extensions to import data:"
                    "<br><br><tt>{extensions}</tt>").format(
                        extensions=', '.join(IMPORT_EXT))
            return msg
        except (UnpicklingError, RuntimeError, CommError):
            return None

    def reset_namespace(self):
        warning = self.get_conf(
            section='ipython_console',
            option='show_reset_namespace_warning'
        )
        self.shellwidget.reset_namespace(warning=warning, message=True)
        self.editor.automatic_column_width = True

    def save_data(self):
        """Save data"""
        if not self.shellwidget.spyder_kernel_ready:
            return
        filename = self.filename
        if filename is None:
            filename = getcwd_or_home()
        extension = osp.splitext(filename)[1].lower()
        if not extension:
            # Needed to prevent trying to save a data file without extension
            # See spyder-ide/spyder#7196
            filename = filename + '.spydata'
        filename, _selfilter = getsavefilename(self, _("Save data"),
                                               filename,
                                               iofunctions.save_filters)
        if filename:
            self.filename = filename
        else:
            return False

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

        error_message = self.save_namespace(self.filename)

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

    def save_namespace(self, filename):
        try:
            return self.shellwidget.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT).save_namespace(filename)
        except TimeoutError:
            msg = _("Data is too big to be saved")
            return msg
        except (UnpicklingError, RuntimeError, CommError):
            return None

    def plot(self, data, funcname):
        """
        Plot data.

        If all the following conditions are met:
        * the Plots plugin is enabled, and
        * the setting "Mute inline plotting" in the Plots plugin is set, and
        * the graphics backend in the IPython Console preferences is set
          to "inline",
        then call `plot_in_plots_plugin`, else call `plot_in_window`.
        """
        if (
            self.plots_plugin_enabled
            and self.get_conf('mute_inline_plotting', section='plots')
            and (
                self.get_conf('pylab/backend', section='ipython_console')
                == 'inline'
            )
        ):
            self.plot_in_plots_plugin(data, funcname)
        else:
            self.plot_in_window(data, funcname)

    def plot_in_plots_plugin(self, data, funcname):
        """
        Plot data in Plots plugin.

        Plot the given data to a PNG or SVG image and show the plot in the
        Plots plugin.
        """
        import spyder.pyplot as plt
        from IPython.core.pylabtools import print_figure

        try:
            from matplotlib import rc_context
        except ImportError:
            # Ignore fontsize and bottom options if guiqwt is used
            # as plotting library
            from contextlib import nullcontext as rc_context

        if self.get_conf('pylab/inline/figure_format',
                         section='ipython_console') == 1:
            figure_format = 'svg'
            mime_type = 'image/svg+xml'
        else:
            figure_format = 'png'
            mime_type = 'image/png'
        resolution = self.get_conf('pylab/inline/resolution',
                                   section='ipython_console')
        width = self.get_conf('pylab/inline/width',
                              section='ipython_console')
        height = self.get_conf('pylab/inline/height',
                               section='ipython_console')
        if self.get_conf('pylab/inline/bbox_inches',
                         section='ipython_console'):
            bbox_inches = 'tight'
        else:
            bbox_inches = None

        matplotlib_rc = {
            'font.size': self.get_conf('pylab/inline/fontsize',
                                       section='ipython_console'),
            'figure.subplot.bottom': self.get_conf('pylab/inline/bottom',
                                                   section='ipython_console')
        }

        with rc_context(matplotlib_rc):
            fig, ax = plt.subplots(figsize=(width, height))
            getattr(ax, funcname)(data)
            image = print_figure(
                fig,
                fmt=figure_format,
                bbox_inches=bbox_inches,
                dpi=resolution
            )

        if figure_format == 'svg':
            image = image.encode()
        self.sig_show_figure_requested.emit(image, mime_type, self.shellwidget)

    def plot_in_window(self, data, funcname):
        """
        Plot data in new Qt window.
        """
        import spyder.pyplot as plt

        plt.figure()
        getattr(plt, funcname)(data)
        plt.show()
