# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

from __future__ import absolute_import
from __future__ import print_function

# Standard library imports
import logging
import traceback

# Third-party imports
from qtpy.QtCore import (Slot, Signal, QModelIndex, QPoint, QSize, Qt, QTimer)
from qtpy.QtGui import QFont, QKeySequence, QTextOption
from qtpy.QtWidgets import (QAbstractItemView, QAction,
                            QButtonGroup, QHBoxLayout, QGroupBox,
                            QMenu, QPlainTextEdit, QRadioButton,
                            QSplitter, QToolButton, QVBoxLayout, QWidget,
                            QDialog, QHeaderView)

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import (add_actions, create_plugin_layout,
                                    create_toolbutton, qapplication)
from spyder.plugins.variableexplorer.widgets.objectexplorer.attribute_model \
    import DEFAULT_ATTR_COLS, DEFAULT_ATTR_DETAILS
from spyder.plugins.variableexplorer.widgets.objectexplorer.tree_model import (
    TreeModel, TreeProxyModel)
from spyder.plugins.variableexplorer.widgets.objectexplorer.\
    toggle_column_mixin import ToggleColumnTreeView
from spyder.utils import icon_manager as ima

logger = logging.getLogger(__name__)

# About message
PROGRAM_NAME = 'Object Explorer'


class ObjectExplorer(QDialog):
    """Object explorer main widget window."""
    # TODO: Use signal to trigger update of configs
    sig_option_changed = Signal(str, object)

    _browsers = []  # Keep lists of browser windows.

    def __init__(self,
                 obj,
                 name='',
                 expanded=False,
                 resize_to_contents=True,
                 parent=None,
                 attribute_columns=DEFAULT_ATTR_COLS,
                 attribute_details=DEFAULT_ATTR_DETAILS,
                 show_callable_attributes=False,
                 show_special_attributes=False,
                 auto_refresh=False,
                 refresh_rate=2,
                 reset=False):
        """
        Constructor

        :param name: name of the object as it will appear in the root node
        :param expanded: show the first visible root element expanded
        :param resize_to_contents: resize columns to contents ignoring width
            of the attributes
        :param obj: any Python object or variable
        :param attribute_columns: list of AttributeColumn objects that
            define which columns are present in the table and their defaults
        :param attribute_details: list of AttributeDetails objects that define
            which attributes can be selected in the details pane.
        :param show_callable_attributes: if True rows where the 'is attribute'
            and 'is callable' columns are both True, are displayed.
            Otherwise they are hidden.
        :param show_special_attributes: if True rows where the 'is attribute'
            is True and the object name starts and ends with two underscores,
            are displayed. Otherwise they are hidden.
        :param auto_refresh: If True, the contents refershes itsef every
            <refresh_rate> seconds.
        :param refresh_rate: number of seconds between automatic refreshes.
            Default = 2 .
        :param reset: If true the persistent settings, such as column widths,
            are reset.
        """
        QDialog.__init__(self, parent=parent)

        self._instance_nr = self._add_instance()

        # Model
        self._attr_cols = attribute_columns
        self._attr_details = attribute_details

        # Settings
        self._auto_refresh = auto_refresh
        self._refresh_rate = refresh_rate

        self._tree_model = TreeModel(obj, obj_name=name,
                                     attr_cols=self._attr_cols)

        self._proxy_tree_model = TreeProxyModel(
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes)

        self._proxy_tree_model.setSourceModel(self._tree_model)
        # self._proxy_tree_model.setSortRole(RegistryTableModel.SORT_ROLE)
        self._proxy_tree_model.setDynamicSortFilter(True)
        # self._proxy_tree_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        # Views
        self._setup_actions()
        self._setup_menu(show_callable_attributes=show_callable_attributes,
                         show_special_attributes=show_special_attributes)
        self._setup_views()
        if name:
            name = "- {}".format(name)
        self.setWindowTitle("{} {}".format(PROGRAM_NAME, name))
        self.setWindowFlags(Qt.Window)

        self._resize_to_contents = resize_to_contents
        self._readViewSettings(reset=reset)

        assert self._refresh_rate > 0, ("refresh_rate must be > 0."
                                        " Got: {}".format(self._refresh_rate))
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(self._refresh_rate * 1000)
        self._refresh_timer.timeout.connect(self.refresh)

        # Update views with model
        self.toggle_show_special_attribute_action.setChecked(
            show_special_attributes)
        self.toggle_show_callable_action.setChecked(show_callable_attributes)
        self.toggle_auto_refresh_action.setChecked(self._auto_refresh)

        # Select first row so that a hidden root node will not be selected.
        first_row_index = self._proxy_tree_model.firstItemIndex()
        self.obj_tree.setCurrentIndex(first_row_index)
        if self._tree_model.inspectedNodeIsVisible or expanded:
            self.obj_tree.expand(first_row_index)

    def refresh(self):
        """Refreshes object brawser contents."""
        logger.debug("Refreshing")
        self._tree_model.refreshTree()

    def _add_instance(self):
        """
        Adds the browser window to the list of browser references.
        If a None is present in the list it is inserted at that position,
        otherwise it is appended to the list. The index number is returned.

        This mechanism is used so that repeatedly creating and closing windows
        does not increase the instance number, which is used in writing
        the persistent settings.
        """
        try:
            idx = self._browsers.index(None)
        except ValueError:
            self._browsers.append(self)
            idx = len(self._browsers) - 1
        else:
            self._browsers[idx] = self

        return idx

    def _remove_instance(self):
        """Sets the reference in the browser list to None."""
        idx = self._browsers.index(self)
        self._browsers[idx] = None

    def _make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.obj_tree.setColumnHidden(
            column_idx, not checked)
        return show_column

    def _setup_actions(self):
        """Creates the main window actions."""
        # Show/hide callable objects
        self.toggle_show_callable_action = \
            QAction(_("Show callable attributes"), self, checkable=True,
                    shortcut=QKeySequence("Alt+C"),
                    statusTip=_("Shows/hides attributes "
                                "that are callable (functions, methods, etc)"))
        self.toggle_show_callable_action.toggled.connect(
            self._proxy_tree_model.setShowCallables)

        # Show/hide special attributes
        self.toggle_show_special_attribute_action = \
            QAction(_("Show __special__ attributes"), self, checkable=True,
                    shortcut=QKeySequence("Alt+S"),
                    statusTip=_("Shows or hides __special__ attributes"))
        self.toggle_show_special_attribute_action.toggled.connect(
            self._proxy_tree_model.setShowSpecialAttributes)

        # Toggle auto-refresh on/off
        self.toggle_auto_refresh_action = \
            QAction(_("Auto-refresh"), self, checkable=True,
                    statusTip=_("Auto refresh every "
                                "{} seconds").format(self._refresh_rate))
        self.toggle_auto_refresh_action.toggled.connect(
            self.toggle_auto_refresh)

        # Add another refresh action with a different short cut. An action
        # must be added to a visible widget for it to receive events.
        # from being displayed again in the menu
        self.refresh_action_f5 = QAction(self, text="&Refresh2", shortcut="F5")
        self.refresh_action_f5.triggered.connect(self.refresh)
        self.addAction(self.refresh_action_f5)

    def _setup_menu(self, show_callable_attributes=False,
                    show_special_attributes=False):
        """Sets up the main menu."""
        self.tools_layout = QHBoxLayout()

        refresh = create_toolbutton(self, text=_("Refresh"),
                                    icon=ima.icon("reload"),
                                    triggered=lambda: self.refresh())
        self.tools_layout.addWidget(refresh)

        auto_refresh = create_toolbutton(
            self, text=_("Auto-refresh"),
            icon=ima.icon("auto_reload"),
            toggled=self._toggle_auto_refresh_action)
        auto_refresh.setCheckable(True)
        self.tools_layout.addWidget(auto_refresh)

        callable_attributes = create_toolbutton(
            self, text=_("Show callable attributes"),
            icon=ima.icon("class"),
            toggled=self._toggle_show_callable_attributes_action)
        callable_attributes.setCheckable(True)
        callable_attributes.setChecked(show_callable_attributes)
        self.tools_layout.addWidget(callable_attributes)

        special_attributes = create_toolbutton(
            self, text=_("Show __special__ attributes"),
            icon=ima.icon("private2"),
            toggled=self._toggle_show_special_attributes_action)
        special_attributes.setCheckable(True)
        special_attributes.setChecked(show_special_attributes)
        self.tools_layout.addWidget(special_attributes)

        self.tools_layout.addStretch()

        self.options_button = create_toolbutton(
                self, text=_('Options'), icon=ima.icon('tooloptions'))
        self.options_button.setPopupMode(QToolButton.InstantPopup)

        self.show_cols_submenu = QMenu(self)
        self.options_button.setMenu(self.show_cols_submenu)
        # Don't show menu arrow and remove padding
        if is_dark_interface():
            self.options_button.setStyleSheet(
                ("QToolButton::menu-indicator{image: none;}\n"
                 "QToolButton{padding: 3px;}"))
        else:
            self.options_button.setStyleSheet(
                "QToolButton::menu-indicator{image: none;}")
        self.tools_layout.addWidget(self.options_button)

    @Slot()
    def _toggle_show_callable_attributes_action(self):
        """Toggle show callable atributes action."""
        action_checked = not self.toggle_show_callable_action.isChecked()
        self.toggle_show_callable_action.setChecked(action_checked)
        self.sig_option_changed.emit('show_callable_attributes',
                                     action_checked)

    @Slot()
    def _toggle_auto_refresh_action(self):
        """Toggle auto-refresh action."""
        action_checked = not self.toggle_auto_refresh_action.isChecked()
        self.toggle_auto_refresh_action.setChecked(action_checked)
        self.sig_option_changed.emit('auto_refresh', action_checked)

    @Slot()
    def _toggle_show_special_attributes_action(self):
        """Toggle show special attributes action."""
        action_checked = (
            not self.toggle_show_special_attribute_action.isChecked())
        self.toggle_show_special_attribute_action.setChecked(action_checked)
        self.sig_option_changed.emit('show_special_attributes', action_checked)

    def _setup_views(self):
        """Creates the UI widgets."""
        self.central_splitter = QSplitter(self, orientation=Qt.Vertical)
        layout = create_plugin_layout(self.tools_layout,
                                      self.central_splitter)
        self.setLayout(layout)

        # Tree widget
        self.obj_tree = ToggleColumnTreeView()
        self.obj_tree.setAlternatingRowColors(True)
        self.obj_tree.setModel(self._proxy_tree_model)
        self.obj_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.obj_tree.setUniformRowHeights(True)
        self.obj_tree.setAnimated(True)
        self.obj_tree.add_header_context_menu()

        # Stretch last column?
        # It doesn't play nice when columns are hidden and then shown again.
        obj_tree_header = self.obj_tree.header()
        obj_tree_header.setSectionsMovable(True)
        obj_tree_header.setStretchLastSection(False)
        add_actions(self.show_cols_submenu,
                    self.obj_tree.toggle_column_actions_group.actions())

        self.central_splitter.addWidget(self.obj_tree)

        # Bottom pane
        bottom_pane_widget = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(5, 5, 5, 5)  # left top right bottom
        bottom_pane_widget.setLayout(bottom_layout)
        self.central_splitter.addWidget(bottom_pane_widget)

        group_box = QGroupBox(_("Details"))
        bottom_layout.addWidget(group_box)

        group_layout = QHBoxLayout()
        group_layout.setContentsMargins(2, 2, 2, 2)  # left top right bottom
        group_box.setLayout(group_layout)

        # Radio buttons
        radio_widget = QWidget()
        radio_layout = QVBoxLayout()
        radio_layout.setContentsMargins(0, 0, 0, 0)  # left top right bottom
        radio_widget.setLayout(radio_layout)

        self.button_group = QButtonGroup(self)
        for button_id, attr_detail in enumerate(self._attr_details):
            radio_button = QRadioButton(attr_detail.name)
            radio_layout.addWidget(radio_button)
            self.button_group.addButton(radio_button, button_id)

        self.button_group.buttonClicked[int].connect(
            self._change_details_field)
        self.button_group.button(0).setChecked(True)

        radio_layout.addStretch(1)
        group_layout.addWidget(radio_widget)

        # Editor widget
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        # font.setPointSize(14)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(font)
        group_layout.addWidget(self.editor)

        # Splitter parameters
        self.central_splitter.setCollapsible(0, False)
        self.central_splitter.setCollapsible(1, True)
        self.central_splitter.setSizes([400, 200])
        self.central_splitter.setStretchFactor(0, 10)
        self.central_splitter.setStretchFactor(1, 0)

        # Connect signals
        # Keep a temporary reference of the selection_model to prevent
        # segfault in PySide.
        # See http://permalink.gmane.org/gmane.comp.lib.qt.pyside.devel/222
        selection_model = self.obj_tree.selectionModel()
        selection_model.currentChanged.connect(self._update_details)

    # End of setup_methods
    def _readViewSettings(self, reset=False):
        """
        Reads the persistent program settings.

        :param reset: If True, the program resets to its default settings.
        """
        pos = QPoint(20 * self._instance_nr, 20 * self._instance_nr)
        window_size = QSize(825, 500)
        details_button_idx = 0

        header = self.obj_tree.header()
        header_restored = False

        if reset:
            logger.debug("Resetting persistent view settings")
        else:
            pos = pos
            window_size = window_size
            details_button_idx = details_button_idx
#            splitter_state = settings.value("central_splitter/state")
            splitter_state = None
            if splitter_state:
                self.central_splitter.restoreState(splitter_state)
#            header_restored = self.obj_tree.read_view_settings(
#                'table/header_state',
#                settings, reset)
            header_restored = False

        if not header_restored:
            column_sizes = [col.width for col in self._attr_cols]
            column_visible = [col.col_visible for col in self._attr_cols]

            for idx, size in enumerate(column_sizes):
                if not self._resize_to_contents and size > 0:  # Just in case
                    header.resizeSection(idx, size)
                else:
                    header.setSectionResizeMode(QHeaderView.ResizeToContents)

            for idx, visible in enumerate(column_visible):
                elem = self.obj_tree.toggle_column_actions_group.actions()[idx]
                elem.setChecked(visible)

        self.resize(window_size)

        button = self.button_group.button(details_button_idx)
        if button is not None:
            button.setChecked(True)

    def _writeViewSettings(self):
        """Writes the view settings to the persistent store."""
        logger.debug("Writing view settings "
                     "for window: {:d}".format(self._instance_nr))
#
#        settings = get_qsettings()
#        settings.beginGroup(self._settings_group_name('view'))
#        self.obj_tree.write_view_settings("table/header_state", settings)
#        settings.setValue("central_splitter/state",
#                          self.central_splitter.saveState())
#        settings.setValue("details_button_idx", self.button_group.checkedId())
#        settings.setValue("main_window/pos", self.pos())
#        settings.setValue("main_window/size", self.size())
#        settings.endGroup()

    @Slot(QModelIndex, QModelIndex)
    def _update_details(self, current_index, _previous_index):
        """Shows the object details in the editor given an index."""
        tree_item = self._proxy_tree_model.treeItem(current_index)
        self._update_details_for_item(tree_item)

    def _change_details_field(self, _button_id=None):
        """Changes the field that is displayed in the details pane."""
        # logger.debug("_change_details_field: {}".format(_button_id))
        current_index = self.obj_tree.selectionModel().currentIndex()
        tree_item = self._proxy_tree_model.treeItem(current_index)
        self._update_details_for_item(tree_item)

    def _update_details_for_item(self, tree_item):
        """Shows the object details in the editor given an tree_item."""
        self.editor.setStyleSheet("color: {};".format(ima.MAIN_FG_COLOR))
        try:
            # obj = tree_item.obj
            button_id = self.button_group.checkedId()
            assert button_id >= 0, ("No radio button selected. "
                                    "Please report this bug.")
            attr_details = self._attr_details[button_id]
            data = attr_details.data_fn(tree_item)
            self.editor.setPlainText(data)
            self.editor.setWordWrapMode(attr_details.line_wrap)
        except Exception as ex:
            self.editor.setStyleSheet("color: red;")
            stack_trace = traceback.format_exc()
            self.editor.setPlainText("{}\n\n{}".format(ex, stack_trace))
            self.editor.setWordWrapMode(
                QTextOption.WrapAtWordBoundaryOrAnywhere)

    def toggle_auto_refresh(self, checked):
        """Toggles auto-refresh on/off."""
        if checked:
            logger.info("Auto-refresh on. "
                        "Rate {:g} seconds".format(self._refresh_rate))
            self._refresh_timer.start()
        else:
            logger.info("Auto-refresh off")
            self._refresh_timer.stop()
        self._auto_refresh = checked

    def _finalize(self):
        """
        Cleans up resources when this window is closed.
        Disconnects all signals for this window.
        """
        self._refresh_timer.stop()
        self._refresh_timer.timeout.disconnect(self.refresh)
        self.toggle_show_callable_action.toggled.disconnect(
            self._proxy_tree_model.setShowCallables)
        self.toggle_show_special_attribute_action.toggled.disconnect(
            self._proxy_tree_model.setShowSpecialAttributes)
        self.toggle_auto_refresh_action.toggled.disconnect(
            self.toggle_auto_refresh)
        self.refresh_action_f5.triggered.disconnect(self.refresh)
        self.button_group.buttonClicked[int].disconnect(
            self._change_details_field)
        selection_model = self.obj_tree.selectionModel()
        selection_model.currentChanged.disconnect(self._update_details)

    def closeEvent(self, event):
        """Called when the window is closed."""
        logger.debug("closeEvent")
        self._writeViewSettings()
        self._finalize()
        self.close()
        event.accept()
        self._remove_instance()
        self.about_to_quit()
        logger.debug("Closed {} window {}".format(PROGRAM_NAME,
                                                  self._instance_nr))

    def about_to_quit(self):
        """Called when application is about to quit."""
        # Sanity check
        for idx, bw in enumerate(self._browsers):
            if bw is not None:
                raise AssertionError("Reference not"
                                     " cleaned up: {}".format(idx))

    @classmethod
    def create_explorer(cls, *args, **kwargs):
        """
        Creates and shows and ObjectExplorer window.

        The *args and **kwargs will be passed to the ObjectExplorer constructor

        A (class attribute) reference to the browser window is kept to prevent
        it from being garbage-collected.
        """
        object_explorer = cls(*args, **kwargs)
        object_explorer.exec_()
        return object_explorer


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run object editor test"""
    import datetime
    import numpy as np
    from spyder.pil_patch import Image

    app = qapplication()

    data = np.random.random_integers(255, size=(100, 100)).astype('uint8')
    image = Image.fromarray(data)

    class Foobar(object):
        def __init__(self):
            self.text = "toto"

        def get_text(self):
            return self.text
    foobar = Foobar()
    example = {'str': 'kjkj kj k j j kj k jkj',
               'list': [1, 3, 4, 'kjkj', None],
               'set': {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
               'dict': {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
               'float': 1.2233,
               'array': np.random.rand(10, 10),
               'image': image,
               'date': datetime.date(1945, 5, 8),
               'datetime': datetime.datetime(1945, 5, 8),
               'foobar': foobar}
    ObjectExplorer.create_explorer(example, 'Example',
                                   show_callable_attributes=True,
                                   show_special_attributes=True,
                                   auto_refresh=False,
                                   refresh_rate=2)


if __name__ == "__main__":
    test()
