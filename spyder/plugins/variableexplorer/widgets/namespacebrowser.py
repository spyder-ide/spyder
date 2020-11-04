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
from qtpy.compat import getsavefilename, getopenfilenames
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QMenu,
                            QMessageBox, QLabel, QWidget)

from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.misc import fix_reference_name
from spyder_kernels.utils.nsview import get_supported_types, REMOTE_SETTINGS

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.py3compat import PY2, is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home, remove_backslashes
from spyder.utils.programs import is_module_installed
from spyder.utils.qthelpers import (
    add_actions, create_action, create_toolbutton, create_plugin_layout,
    create_waitspinner, MENU_SEPARATOR)
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard
from spyder.widgets.collectionseditor import RemoteCollectionsEditorTableView
from spyder.widgets.helperwidgets import FinderLineEdit


SUPPORTED_TYPES = get_supported_types()

if PY2:
    VALID_VARIABLE_CHARS = r"[a-zA-z0-9_]"
else:
    VALID_VARIABLE_CHARS = r"[^\w+*=¡!¿?'\"#$%&()/<>\-\[\]{}^`´;,|¬]*\w"


class NamespaceBrowser(QWidget):
    """Namespace browser (global variables explorer widget)"""
    sig_option_changed = Signal(str, object)
    sig_collapse = Signal()
    sig_free_memory = Signal()

    def __init__(self, parent, options_button=None, plugin_actions=[]):
        QWidget.__init__(self, parent)
        
        self.shellwidget = None
        self.is_visible = True
        self.setup_in_progress = None

        # Remote dict editor settings
        self.check_all = None
        self.exclude_private = None
        self.exclude_uppercase = None
        self.exclude_capitalized = None
        self.exclude_unsupported = None
        self.exclude_callables_and_modules = None
        self.excluded_names = None
        self.minmax = None

        # Other setting
        self.dataframe_format = None
        self.show_callable_attributes = None
        self.show_special_attributes = None

        self.editor = None
        self.exclude_private_action = None
        self.exclude_uppercase_action = None
        self.exclude_capitalized_action = None
        self.exclude_unsupported_action = None
        self.exclude_callables_and_modules_action = None
        self.finder = None
        self.options_button = options_button
        self.actions = None
        self.plugin_actions = plugin_actions

        self.filename = None

    def setup(self, check_all=None, exclude_private=None,
              exclude_uppercase=None, exclude_capitalized=None,
              exclude_unsupported=None, excluded_names=None,
              exclude_callables_and_modules=None,
              minmax=None, dataframe_format=None,
              show_callable_attributes=None,
              show_special_attributes=None,):
        """
        Setup the namespace browser with provided settings.

        Args:
            dataframe_format (string): default floating-point format for 
                DataFrame editor
        """
        assert self.shellwidget is not None
        
        self.check_all = check_all
        self.exclude_private = exclude_private
        self.exclude_uppercase = exclude_uppercase
        self.exclude_capitalized = exclude_capitalized
        self.exclude_unsupported = exclude_unsupported
        self.exclude_callables_and_modules = exclude_callables_and_modules
        self.excluded_names = excluded_names
        self.minmax = minmax
        self.dataframe_format = dataframe_format
        self.show_callable_attributes = show_callable_attributes
        self.show_special_attributes = show_special_attributes

        if self.editor is not None:
            self.editor.setup_menu(minmax)
            self.editor.set_dataframe_format(dataframe_format)
            self.exclude_private_action.setChecked(exclude_private)
            self.exclude_uppercase_action.setChecked(exclude_uppercase)
            self.exclude_capitalized_action.setChecked(exclude_capitalized)
            self.exclude_unsupported_action.setChecked(exclude_unsupported)
            self.exclude_callables_and_modules_action.setChecked(
                exclude_callables_and_modules)
            self.refresh_table()
            return

        self.editor = RemoteCollectionsEditorTableView(
            self,
            data=None,
            minmax=minmax,
            shellwidget=self.shellwidget,
            dataframe_format=dataframe_format,
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes
        )

        self.editor.sig_option_changed.connect(self.sig_option_changed.emit)
        self.editor.sig_files_dropped.connect(self.import_data)
        self.editor.sig_free_memory.connect(self.sig_free_memory.emit)

        self.setup_option_actions(
            exclude_private,
            exclude_uppercase,
            exclude_capitalized,
            exclude_unsupported,
            exclude_callables_and_modules
        )

        # Setup toolbar layout.

        self.tools_layout = QHBoxLayout()
        toolbar = self.setup_toolbar()
        for widget in toolbar:
            self.tools_layout.addWidget(widget)
        self.tools_layout.addStretch()

        # Show loading widget
        self.loading_widget = create_waitspinner(size=16, parent=self)
        self.editor.sig_open_editor.connect(self.loading_widget.start)
        self.editor.sig_editor_shown.connect(self.loading_widget.stop)
        self.tools_layout.addWidget(self.loading_widget)

        # Options button actions addition and addition to layout
        self.setup_options_button()

        # Setup layout.

        layout = create_plugin_layout(self.tools_layout, self.editor)

        # Fuzzy search layout
        finder_layout = QHBoxLayout()
        close_button = create_toolbutton(self, triggered=self.show_finder,
                                         icon=ima.icon('DialogCloseButton'))
        text_finder = NamespacesBrowserFinder(self.editor,
                                              callback=self.editor.set_regex,
                                              main=self,
                                              regex_base=VALID_VARIABLE_CHARS)
        self.editor.finder = text_finder
        finder_layout.addWidget(close_button)
        finder_layout.addWidget(text_finder)
        finder_layout.setContentsMargins(0, 0, 0, 0)
        self.finder = QWidget(self)
        self.finder.text_finder = text_finder
        self.finder.setLayout(finder_layout)
        self.finder.setVisible(False)

        layout.addWidget(self.finder)

        self.setLayout(layout)

        # Local shortcuts
        self.shortcuts = self.create_shortcuts()

        self.sig_option_changed.connect(self.option_changed)

    def create_shortcuts(self):
        """Create local shortcut for the nsbrowser."""
        search = CONF.config_shortcut(
            lambda: self.show_finder(set_visible=True),
            context='variable_explorer',
            name='search',
            parent=self)
        refresh = CONF.config_shortcut(
            self.refresh_table,
            context='variable_explorer',
            name='refresh',
            parent=self)
        copy = CONF.config_shortcut(
            self.editor.copy,
            context='variable_explorer',
            name='copy',
            parent=self)

        return [search, refresh, copy]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to namespace browser"""
        self.shellwidget = shellwidget
        shellwidget.set_namespacebrowser(self)

    def get_actions(self):
        """Get actions of the widget."""
        return self.actions

    def setup_toolbar(self):
        """Setup toolbar"""
        load_button = create_toolbutton(
            self,
            text=_('Import data'),
            icon=ima.icon('fileimport'),
            triggered=lambda: self.import_data())

        self.save_button = create_toolbutton(
            self, text=_("Save data"),
            icon=ima.icon('filesave'),
            triggered=lambda: self.save_data(self.filename))

        self.save_button.setEnabled(False)

        save_as_button = create_toolbutton(
            self,
            text=_("Save data as..."),
            icon=ima.icon('filesaveas'),
            triggered=self.save_data)

        reset_namespace_button = create_toolbutton(
            self, text=_("Remove all variables"),
            icon=ima.icon('editdelete'),
            triggered=self.reset_namespace)

        self.search_button = create_toolbutton(
            self,
            text=_("Search variable names and types"),
            icon=ima.icon('find'),
            toggled=self.show_finder)

        self.refresh_button = create_toolbutton(
            self,
            text=_("Refresh variables"),
            icon=ima.icon('refresh'),
            triggered=self.refresh_table)

        return [load_button, self.save_button, save_as_button,
                reset_namespace_button, self.search_button,
                self.refresh_button]

    def setup_option_actions(self, exclude_private, exclude_uppercase,
                             exclude_capitalized, exclude_unsupported,
                             exclude_callables_and_modules):
        """Setup the actions to show in the cog menu."""
        self.setup_in_progress = True

        self.exclude_private_action = create_action(self,
                _("Exclude private references"),
                tip=_("Exclude references which name starts"
                            " with an underscore"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_private', state))
        self.exclude_private_action.setChecked(exclude_private)
        
        self.exclude_uppercase_action = create_action(self,
                _("Exclude all-uppercase references"),
                tip=_("Exclude references which name is uppercase"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_uppercase', state))
        self.exclude_uppercase_action.setChecked(exclude_uppercase)
        
        self.exclude_capitalized_action = create_action(self,
                _("Exclude capitalized references"),
                tip=_("Exclude references which name starts with an "
                      "uppercase character"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_capitalized', state))
        self.exclude_capitalized_action.setChecked(exclude_capitalized)
        
        self.exclude_unsupported_action = create_action(self,
                _("Exclude unsupported data types"),
                tip=_("Exclude references to data types that don't have "
                      "an specialized viewer or can't be edited."),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_unsupported', state))
        self.exclude_unsupported_action.setChecked(exclude_unsupported)

        self.exclude_callables_and_modules_action = create_action(self,
                _("Exclude callables and modules"),
                tip=_("Exclude references to functions, modules and "
                      "any other callable."),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_callables_and_modules',
                                             state))
        self.exclude_callables_and_modules_action.setChecked(
            exclude_callables_and_modules)

        self.actions = [
            self.exclude_private_action,
            self.exclude_uppercase_action,
            self.exclude_capitalized_action,
            self.exclude_unsupported_action,
            self.exclude_callables_and_modules_action
        ]
        if is_module_installed('numpy'):
            self.actions.extend([MENU_SEPARATOR, self.editor.minmax_action])

        self.setup_in_progress = False

    def setup_options_button(self):
        """Add the cog menu button to the toolbar."""
        if not self.options_button:
            self.options_button = create_toolbutton(
                self, text=_('Options'), icon=ima.icon('tooloptions'))

            actions = self.actions + [MENU_SEPARATOR] + self.plugin_actions
            self.options_menu = QMenu(self)
            add_actions(self.options_menu, actions)
            self.options_button.setMenu(self.options_menu)

        if self.tools_layout.itemAt(self.tools_layout.count() - 1) is None:
            self.tools_layout.insertWidget(
                self.tools_layout.count() - 1, self.options_button)
        else:
            self.tools_layout.addWidget(self.options_button)

    def option_changed(self, option, value):
        """Option has changed"""
        setattr(self, to_text_string(option), value)
        self.shellwidget.set_namespace_view_settings()
        self.refresh_table()

    def get_view_settings(self):
        """Return dict editor view settings"""
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = getattr(self, name)
        return settings

    def show_finder(self, set_visible=False):
        """Handle showing/hiding the finder widget."""
        self.finder.text_finder.setText('')
        self.finder.setVisible(set_visible)
        self.search_button.setChecked(set_visible)

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
        # To load all variables when a new filtering search is
        # started.
        self.finder.text_finder.load_all = False

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
        warning = CONF.get('ipython_console', 'show_reset_namespace_warning')
        self.shellwidget.reset_namespace(warning=warning, message=True)
        self.editor.automatic_column_width = True

    @Slot()
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
        self.save_button.setEnabled(self.filename is not None)


class NamespacesBrowserFinder(FinderLineEdit):
    """Textbox for filtering listed variables in the table."""
    # To load all variables when filtering.
    load_all = False

    def load_all_variables(self):
        """Load all variables to correctly filter them."""
        if not self.load_all:
            self._parent.parent().editor.source_model.load_all()
        self.load_all = True

    def keyPressEvent(self, event):
        """Qt and FilterLineEdit Override."""
        key = event.key()
        if key in [Qt.Key_Up]:
            self.load_all_variables()
            self._parent.previous_row()
        elif key in [Qt.Key_Down]:
            self.load_all_variables()
            self._parent.next_row()
        elif key in [Qt.Key_Escape]:
            self._parent.parent().show_finder(set_visible=False)
        elif key in [Qt.Key_Enter, Qt.Key_Return]:
            # TODO: Check if an editor needs to be shown
            pass
        else:
            self.load_all_variables()
            super(NamespacesBrowserFinder, self).keyPressEvent(event)
