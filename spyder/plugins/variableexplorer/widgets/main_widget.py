# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Variable Explorer Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import QTimer, Signal, Slot
from qtpy.QtWidgets import (
    QAction, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.variableexplorer.widgets.namespacebrowser import (
    NamespaceBrowser, NamespacesBrowserFinder, VALID_VARIABLE_CHARS)
from spyder.utils.programs import is_module_installed

# Localization
_ = get_translation('spyder')


# =============================================================================
# ---- Constants
# =============================================================================
class VariableExplorerWidgetActions:
    # Triggers
    ImportData = 'import_data_action'
    SaveData = 'save_data_action'
    SaveDataAs = 'save_data_as_action'
    ResetNamespace = 'reset_namespaces_action'
    Search = 'search'
    Refresh = 'refresh'

    # Toggles
    ToggleExcludePrivate = 'toggle_exclude_private_action'
    ToggleExcludeUpperCase = 'toggle_exclude_uppercase_action'
    ToggleExcludeCapitalized = 'toggle_exclude_capitalized_action'
    ToggleExcludeUnsupported = 'toggle_exclude_unsupported_action'
    ToggleExcludeCallablesAndModules = (
        'toggle_exclude_callables_and_modules_action')
    ToggleMinMax = 'toggle_minmax_action'


class VariableExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class VariableExplorerWidgetMainToolBarSections:
    Main = 'main_section'


class VariableExplorerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class VariableExplorerContextMenuActions:
    ResizeRowsAction = 'resize_rows_action'
    ResizeColumnsAction = 'resize_columns_action'
    PasteAction = 'paste_action'
    CopyAction = 'copy'
    EditAction = 'edit_action'
    PlotAction = 'plot_action'
    HistogramAction = 'histogram_action'
    ImshowAction = 'imshow_action'
    SaveArrayAction = 'save_array_action'
    InsertAction = 'insert_action'
    InsertActionAbove = 'insert_action_above'
    InsertActionBelow = 'insert_action_below'
    RemoveAction = 'remove_action'
    RenameAction = 'rename_action'
    DuplicateAction = 'duplicate_action'
    ViewAction = 'view_action'


class VariableExplorerContextMenuSections:
    Edit = 'edit_section'
    Rename = 'rename_section'
    Resize = 'resize_section'


# =============================================================================
# ---- Widgets
# =============================================================================
class NamespaceStackedWidget(QStackedWidget):
    # Signals
    sig_free_memory_requested = Signal()
    sig_start_spinner_requested = Signal()
    sig_stop_spinner_requested = Signal()
    sig_hide_finder_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

    def addWidget(self, widget):
        """
        Override Qt method.
        """
        if isinstance(widget, NamespaceBrowser):
            widget.sig_free_memory_requested.connect(
                self.sig_free_memory_requested)
            widget.sig_start_spinner_requested.connect(
                self.sig_start_spinner_requested)
            widget.sig_stop_spinner_requested.connect(
                self.sig_stop_spinner_requested)
            widget.sig_hide_finder_requested.connect(
                self.sig_hide_finder_requested)

        super().addWidget(widget)


class VariableExplorerWidget(PluginMainWidget):

    # PluginMainWidget class constants
    ENABLE_SPINNER = True

    # Other class constants
    INITIAL_FREE_MEMORY_TIME_TRIGGER = 60 * 1000  # ms
    SECONDARY_FREE_MEMORY_TIME_TRIGGER = 180 * 1000  # ms

    # Signals
    sig_free_memory_requested = Signal()

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self._stack = NamespaceStackedWidget(self)
        self._shellwidgets = {}
        self.context_menu = None
        self.empty_context_menu = None

        # --- Finder
        self.finder = None

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self._stack)
        # Note: Later with the addition of the first NamespaceBrowser the
        # find/search widget is added. See 'set_current_widget'
        self.setLayout(layout)

        # Signals
        self._stack.sig_free_memory_requested.connect(self.free_memory)
        self._stack.sig_start_spinner_requested.connect(self.start_spinner)
        self._stack.sig_stop_spinner_requested.connect(self.stop_spinner)
        self._stack.sig_hide_finder_requested.connect(self.hide_finder)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Variable Explorer')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self):
        # ---- Options menu actions
        exclude_private_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludePrivate,
            text=_("Exclude private variables"),
            tip=_("Exclude variables that start with an underscore"),
            toggled=True,
            option='exclude_private',
        )

        exclude_uppercase_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUpperCase,
            text=_("Exclude all-uppercase variables"),
            tip=_("Exclude variables whose name is uppercase"),
            toggled=True,
            option='exclude_uppercase',
        )

        exclude_capitalized_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCapitalized,
            text=_("Exclude capitalized variables"),
            tip=_("Exclude variables whose name starts with a capital "
                  "letter"),
            toggled=True,
            option='exclude_capitalized',
        )

        exclude_unsupported_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUnsupported,
            text=_("Exclude unsupported data types"),
            tip=_("Exclude references to data types that don't have "
                  "an specialized viewer or can't be edited."),
            toggled=True,
            option='exclude_unsupported',
        )

        exclude_callables_and_modules_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCallablesAndModules,
            text=_("Exclude callables and modules"),
            tip=_("Exclude references to functions, modules and "
                  "any other callable."),
            toggled=True,
            option='exclude_callables_and_modules'
        )

        self.show_minmax_action = self.create_action(
            VariableExplorerWidgetActions.ToggleMinMax,
            text=_("Show arrays min/max"),
            tip=_("Show minimum and maximum of arrays"),
            toggled=True,
            option='minmax'
        )

        # ---- Toolbar actions
        import_data_action = self.create_action(
            VariableExplorerWidgetActions.ImportData,
            text=_('Import data'),
            icon=self.create_icon('fileimport'),
            triggered=lambda x: self.import_data(),
        )

        save_action = self.create_action(
            VariableExplorerWidgetActions.SaveData,
            text=_("Save data"),
            icon=self.create_icon('filesave'),
            triggered=lambda x: self.save_data(),
        )

        save_as_action = self.create_action(
            VariableExplorerWidgetActions.SaveDataAs,
            text=_("Save data as..."),
            icon=self.create_icon('filesaveas'),
            triggered=lambda x: self.save_data(),
        )

        reset_namespace_action = self.create_action(
            VariableExplorerWidgetActions.ResetNamespace,
            text=_("Remove all variables"),
            icon=self.create_icon('editdelete'),
            triggered=lambda x: self.reset_namespace(),
        )

        search_action = self.create_action(
            VariableExplorerWidgetActions.Search,
            text=_("Search variable names and types"),
            icon=self.create_icon('find'),
            toggled=self.show_finder,
            register_shortcut=True
        )

        refresh_action = self.create_action(
            VariableExplorerWidgetActions.Refresh,
            text=_("Refresh variables"),
            icon=self.create_icon('refresh'),
            triggered=self.refresh_table,
            register_shortcut=True,
        )

        # ---- Context menu actions
        resize_rows_action = self.create_action(
            VariableExplorerContextMenuActions.ResizeRowsAction,
            text=_("Resize rows to contents"),
            triggered=self.resize_rows
        )

        resize_columns_action = self.create_action(
            VariableExplorerContextMenuActions.ResizeColumnsAction,
            _("Resize columns to contents"),
            triggered=self.resize_columns
        )

        self.paste_action = self.create_action(
            VariableExplorerContextMenuActions.PasteAction,
            _("Paste"),
            icon=self.create_icon('editpaste'),
            triggered=self.paste
        )

        self.copy_action = self.create_action(
            VariableExplorerContextMenuActions.CopyAction,
            _("Copy"),
            icon=self.create_icon('editcopy'),
            triggered=self.copy
        )

        self.edit_action = self.create_action(
            VariableExplorerContextMenuActions.EditAction,
            _("Edit"),
            icon=self.create_icon('edit'),
            triggered=self.edit_item
        )

        self.plot_action = self.create_action(
            VariableExplorerContextMenuActions.PlotAction,
            _("Plot"),
            icon=self.create_icon('plot'),
            triggered=self.plot_item
        )
        self.plot_action.setVisible(False)

        self.hist_action = self.create_action(
            VariableExplorerContextMenuActions.HistogramAction,
            _("Histogram"),
            icon=self.create_icon('hist'),
            triggered=self.histogram_item
        )
        self.hist_action.setVisible(False)

        self.imshow_action = self.create_action(
            VariableExplorerContextMenuActions.ImshowAction,
            _("Show image"),
            icon=self.create_icon('imshow'),
            triggered=self.imshow_item
        )
        self.imshow_action.setVisible(False)

        self.save_array_action = self.create_action(
            VariableExplorerContextMenuActions.SaveArrayAction,
            _("Save array"),
            icon=self.create_icon('filesave'),
            triggered=self.save_array
        )
        self.save_array_action.setVisible(False)

        self.insert_action = self.create_action(
            VariableExplorerContextMenuActions.InsertAction,
            _("Insert"),
            icon=self.create_icon('insert'),
            triggered=self.insert_item
        )

        self.remove_action = self.create_action(
            VariableExplorerContextMenuActions.RemoveAction,
            _("Remove"),
            icon=self.create_icon('editdelete'),
            triggered=self.remove_item
        )

        self.rename_action = self.create_action(
            VariableExplorerContextMenuActions.RenameAction,
            _("Rename"),
            icon=self.create_icon('rename'),
            triggered=self.rename_item
        )

        self.duplicate_action = self.create_action(
            VariableExplorerContextMenuActions.DuplicateAction,
            _("Duplicate"),
            icon=self.create_icon('edit_add'),
            triggered=self.duplicate_item
        )

        self.view_action = self.create_action(
            VariableExplorerContextMenuActions.ViewAction,
            _("View with the Object Explorer"),
            icon=self.create_icon('outline_explorer'),
            triggered=self.view_item
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [exclude_private_action, exclude_uppercase_action,
                     exclude_capitalized_action, exclude_unsupported_action,
                     exclude_callables_and_modules_action,
                     self.show_minmax_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=VariableExplorerWidgetOptionsMenuSections.Display,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [import_data_action, save_action, save_as_action,
                     reset_namespace_action, search_action, refresh_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=VariableExplorerWidgetMainToolBarSections.Main,
            )
        save_action.setEnabled(False)

        # ---- Context menu to show when there are variables present
        self.context_menu = self.create_menu(
            VariableExplorerWidgetMenus.PopulatedContextMenu)
        for item in [self.edit_action, self.plot_action, self.hist_action,
                     self.imshow_action, self.save_array_action,
                     self.insert_action, self.remove_action, self.copy_action,
                     self.paste_action, self.view_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Edit,
            )

        for item in [self.rename_action, self.duplicate_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Rename,
            )

        for item in [resize_rows_action, resize_columns_action,
                     self.show_minmax_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Resize,
            )

        # ---- Context menu when the variable explorer is empty
        self.empty_context_menu = self.create_menu(
            VariableExplorerWidgetMenus.EmptyContextMenu)
        for item in [self.insert_action, self.paste_action]:
            self.add_item_to_menu(
                item,
                menu=self.empty_context_menu,
                section=VariableExplorerContextMenuSections.Edit,
            )

    def update_style(self):
        self._stack.setStyleSheet(
            "NamespaceStackedWidget {padding: 0px; border: 0px}")

    def update_actions(self):
        action = self.get_action(VariableExplorerWidgetActions.ToggleMinMax)
        action.setEnabled(is_module_installed('numpy'))
        nsb = self.current_widget()

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                if nsb:
                    save_data_action = self.get_action(
                        VariableExplorerWidgetActions.SaveData)
                    save_data_action.setEnabled(nsb.filename is not None)

                    nsb_actions = nsb.actions()
                    if action not in nsb_actions:
                        nsb.addAction(action)

    @on_conf_change
    def on_section_conf_change(self, section):
        for index in range(self.count()):
            widget = self._stack.widget(index)
            if widget:
                widget.setup()

    # ---- Stack accesors
    # ------------------------------------------------------------------------
    def add_widget(self, nsb):
        self._stack.addWidget(nsb)

    def count(self):
        return self._stack.count()

    def current_widget(self):
        return self._stack.currentWidget()

    def remove_widget(self, nsb):
        self._stack.removeWidget(nsb)

    def update_finder(self, nsb, old_nsb):
        """Initialize or update finder widget."""
        if self.finder is None:
            # Initialize finder/search related widgets
            self.finder = QWidget(self)
            self.text_finder = NamespacesBrowserFinder(
                nsb.editor,
                callback=nsb.editor.set_regex,
                main=nsb,
                regex_base=VALID_VARIABLE_CHARS)
            self.finder.text_finder = self.text_finder
            self.finder_close_button = self.create_toolbutton(
                'close_finder',
                triggered=self.hide_finder,
                icon=self.create_icon('DialogCloseButton'),
            )

            finder_layout = QHBoxLayout()
            finder_layout.addWidget(self.finder_close_button)
            finder_layout.addWidget(self.text_finder)
            finder_layout.setContentsMargins(0, 0, 0, 0)
            self.finder.setLayout(finder_layout)

            layout = self.layout()
            layout.addSpacing(1)
            layout.addWidget(self.finder)
        else:
            # Just update references to the same text_finder (Custom QLineEdit)
            # widget to the new current NamespaceBrowser and save current
            # finder state in the previous NamespaceBrowser
            if old_nsb is not None:
                self.save_finder_state(old_nsb)
            self.text_finder.update_parent(
                nsb.editor,
                callback=nsb.editor.set_regex,
                main=nsb,
            )

    def set_current_widget(self, nsb, old_nsb):
        """
        Set the current NamespaceBrowser.

        This also setup the finder widget to work with the current
        NamespaceBrowser.
        """
        self.update_finder(nsb, old_nsb)
        finder_visible = nsb.set_text_finder(self.text_finder)
        self._stack.setCurrentWidget(nsb)
        self.finder.setVisible(finder_visible)
        search_action = self.get_action(VariableExplorerWidgetActions.Search)
        search_action.setChecked(finder_visible)

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell with variable explorer.

        This function creates a new NamespaceBrowser for browsing
        variables in the shell.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            old_nsb = self.current_widget()
            nsb = NamespaceBrowser(self)
            nsb.set_shellwidget(shellwidget)
            nsb.setup()
            self.add_widget(nsb)
            self._set_actions_and_menus(nsb)
            self._shellwidgets[shellwidget_id] = nsb
            self.set_current_widget(nsb, old_nsb)
            self.update_actions()
            return nsb

    def remove_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets.pop(shellwidget_id)
            self.remove_widget(nsb)
            nsb.close()

    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        old_nsb = self.current_widget()
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets[shellwidget_id]
            self.set_current_widget(nsb, old_nsb)

    def import_data(self, filenames=None):
        """
        Import data in current namespace.
        """
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table()
            nsb.import_data(filenames=filenames)

    def save_data(self):
        if self.count():
            nsb = self.current_widget()
            nsb.save_data()
            self.update_actions()

    def reset_namespace(self):
        if self.count():
            nsb = self.current_widget()
            nsb.reset_namespace()

    @Slot(bool)
    def show_finder(self, checked):
        if self.count():
            nsb = self.current_widget()
            if checked:
                self.finder.text_finder.setText(nsb.last_find)
            else:
                self.save_finder_state(nsb)
                self.finder.text_finder.setText('')
            self.finder.setVisible(checked)
            if self.finder.isVisible():
                self.finder.text_finder.setFocus()
            else:
                nsb.editor.setFocus()

    @Slot()
    def hide_finder(self):
        action = self.get_action(VariableExplorerWidgetActions.Search)
        action.setChecked(False)
        nsb = self.current_widget()
        self.save_finder_state(nsb)
        self.finder.text_finder.setText('')

    def save_finder_state(self, nsb):
        """
        Save finder state (last input text and visibility).

        The values are saved in the given NamespaceBrowser.
        """
        last_find = self.text_finder.text()
        finder_visibility = self.finder.isVisible()
        nsb.save_finder_state(last_find, finder_visibility)

    def refresh_table(self):
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table()

    @Slot()
    def free_memory(self):
        """
        Free memory signal.
        """
        self.sig_free_memory_requested.emit()
        QTimer.singleShot(self.INITIAL_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory_requested.emit)
        QTimer.singleShot(self.SECONDARY_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory_requested.emit)

    def resize_rows(self):
        self._current_editor.resizeRowsToContents()

    def resize_columns(self):
        self._current_editor.resize_column_contents()

    def paste(self):
        self._current_editor.paste()

    def copy(self):
        self._current_editor.copy()

    def edit_item(self):
        self._current_editor.edit_item()

    def plot_item(self):
        self._current_editor.plot_item('plot')

    def histogram_item(self):
        self._current_editor.plot_item('hist')

    def imshow_item(self):
        self._current_editor.imshow_item()

    def save_array(self):
        self._current_editor.save_array()

    def insert_item(self):
        self._current_editor.insert_item(below=False)

    def remove_item(self):
        self._current_editor.remove_item()

    def rename_item(self):
        self._current_editor.rename_item()

    def duplicate_item(self):
        self._current_editor.duplicate_item()

    def view_item(self):
        self._current_editor.view_item()

    # ---- Private API
    # ------------------------------------------------------------------------
    @property
    def _current_editor(self):
        editor = None
        if self.count():
            nsb = self.current_widget()
            editor = nsb.editor
        return editor

    def _set_actions_and_menus(self, nsb):
        """
        Set actions and menus created here and used by the namespace
        browser editor.

        Although this is not ideal, it's necessary to be able to use
        the CollectionsEditor widget separately from this plugin.
        """
        editor = nsb.editor

        # Actions
        editor.paste_action = self.paste_action
        editor.copy_action = self.copy_action
        editor.edit_action = self.edit_action
        editor.plot_action = self.plot_action
        editor.hist_action = self.hist_action
        editor.imshow_action = self.imshow_action
        editor.save_array_action = self.save_array_action
        editor.insert_action = self.insert_action
        editor.remove_action = self.remove_action
        editor.minmax_action = self.show_minmax_action
        editor.rename_action = self.rename_action
        editor.duplicate_action = self.duplicate_action
        editor.view_action = self.view_action

        # Menus
        editor.menu = self.context_menu
        editor.empty_ws_menu = self.empty_context_menu

        # These actions are not used for dictionaries (so we don't need them
        # for namespaces) but we have to create them so they can be used in
        # several places in CollectionsEditor.
        editor.insert_action_above = QAction()
        editor.insert_action_below = QAction()
