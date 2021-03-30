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
from qtpy.QtCore import Slot, Signal, QModelIndex, QPoint, QSize, Qt
from qtpy.QtGui import QKeySequence, QTextOption
from qtpy.QtWidgets import (QAbstractItemView, QAction, QButtonGroup,
                            QDialog, QGroupBox, QHBoxLayout, QHeaderView,
                            QMenu, QPushButton, QRadioButton, QSplitter,
                            QToolButton, QVBoxLayout, QWidget)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import _
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font
from spyder.config.manager import CONF
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.plugins.variableexplorer.widgets.objectexplorer import (
    DEFAULT_ATTR_COLS, DEFAULT_ATTR_DETAILS, ToggleColumnTreeView,
    TreeItem, TreeModel, TreeProxyModel)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import (add_actions, create_plugin_layout,
                                    create_toolbutton, qapplication)
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


logger = logging.getLogger(__name__)


# About message
EDITOR_NAME = 'Object'


class ObjectExplorer(BaseDialog, SpyderConfigurationAccessor):
    """Object explorer main widget window."""
    CONF_SECTION = 'variable_explorer'

    def __init__(self,
                 obj,
                 name='',
                 expanded=False,
                 resize_to_contents=True,
                 parent=None,
                 attribute_columns=DEFAULT_ATTR_COLS,
                 attribute_details=DEFAULT_ATTR_DETAILS,
                 readonly=None,
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
        :param reset: If true the persistent settings, such as column widths,
            are reset.
        """
        QDialog.__init__(self, parent=parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Options
        show_callable_attributes = self.get_conf('show_callable_attributes')
        show_special_attributes = self.get_conf('show_special_attributes')

        # Model
        self._attr_cols = attribute_columns
        self._attr_details = attribute_details
        self.readonly = readonly

        self.btn_save_and_close = None
        self.btn_close = None

        self._tree_model = TreeModel(obj, obj_name=name,
                                     attr_cols=self._attr_cols)

        self._proxy_tree_model = TreeProxyModel(
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes
        )

        self._proxy_tree_model.setSourceModel(self._tree_model)
        # self._proxy_tree_model.setSortRole(RegistryTableModel.SORT_ROLE)
        self._proxy_tree_model.setDynamicSortFilter(True)
        # self._proxy_tree_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        # Tree widget
        self.obj_tree = ToggleColumnTreeView()
        self.obj_tree.setAlternatingRowColors(True)
        self.obj_tree.setModel(self._proxy_tree_model)
        self.obj_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.obj_tree.setUniformRowHeights(True)
        self.obj_tree.add_header_context_menu()

        # Views
        self._setup_actions()
        self._setup_menu(show_callable_attributes=show_callable_attributes,
                         show_special_attributes=show_special_attributes)
        self._setup_views()
        if name:
            name = "{} -".format(name)
        self.setWindowTitle("{} {}".format(name, EDITOR_NAME))
        self.setWindowFlags(Qt.Window)

        self._resize_to_contents = resize_to_contents
        self._readViewSettings(reset=reset)

        # Update views with model
        self.toggle_show_special_attribute_action.setChecked(
            show_special_attributes)
        self.toggle_show_callable_action.setChecked(show_callable_attributes)

        # Select first row so that a hidden root node will not be selected.
        first_row_index = self._proxy_tree_model.firstItemIndex()
        self.obj_tree.setCurrentIndex(first_row_index)
        if self._tree_model.inspectedNodeIsVisible or expanded:
            self.obj_tree.expand(first_row_index)

    def get_value(self):
        """Get editor current object state."""
        return self._tree_model.inspectedItem.obj

    def _make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.obj_tree.setColumnHidden(
            column_idx, not checked)
        return show_column

    def _setup_actions(self):
        """Creates the main window actions."""
        # Show/hide callable objects
        self.toggle_show_callable_action = QAction(
            _("Show callable attributes"),
            self,
            checkable=True,
            shortcut=QKeySequence("Alt+C"),
            statusTip=_("Shows/hides attributes that are callable "
                        "(functions, methods, etc)")
        )
        self.toggle_show_callable_action.toggled.connect(
            self._proxy_tree_model.setShowCallables)
        self.toggle_show_callable_action.toggled.connect(
            self.obj_tree.resize_columns_to_contents)

        # Show/hide special attributes
        self.toggle_show_special_attribute_action = QAction(
            _("Show __special__ attributes"),
            self,
            checkable=True,
            shortcut=QKeySequence("Alt+S"),
            statusTip=_("Shows or hides __special__ attributes")
        )
        self.toggle_show_special_attribute_action.toggled.connect(
            self._proxy_tree_model.setShowSpecialAttributes)
        self.toggle_show_special_attribute_action.toggled.connect(
            self.obj_tree.resize_columns_to_contents)

    def _setup_menu(self, show_callable_attributes=False,
                    show_special_attributes=False):
        """Sets up the main menu."""
        self.tools_layout = QHBoxLayout()

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
        self.options_button.setStyleSheet(
            ("QToolButton::menu-indicator{image: none;}\n"
             "QToolButton{padding: 3px;}"))
        self.tools_layout.addWidget(self.options_button)

    @Slot()
    def _toggle_show_callable_attributes_action(self):
        """Toggle show callable atributes action."""
        action_checked = not self.toggle_show_callable_action.isChecked()
        self.toggle_show_callable_action.setChecked(action_checked)
        self.set_conf('show_callable_attributes', action_checked)

    @Slot()
    def _toggle_show_special_attributes_action(self):
        """Toggle show special attributes action."""
        action_checked = (
            not self.toggle_show_special_attribute_action.isChecked())
        self.toggle_show_special_attribute_action.setChecked(action_checked)
        self.set_conf('show_special_attributes', action_checked)

    def _setup_views(self):
        """Creates the UI widgets."""
        self.central_splitter = QSplitter(self, orientation=Qt.Vertical)
        layout = create_plugin_layout(self.tools_layout,
                                      self.central_splitter)
        self.setLayout(layout)

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

        v_group_layout = QVBoxLayout()
        h_group_layout = QHBoxLayout()
        h_group_layout.setContentsMargins(2, 2, 2, 2)  # left top right bottom
        group_box.setLayout(v_group_layout)
        v_group_layout.addLayout(h_group_layout)

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
        h_group_layout.addWidget(radio_widget)

        # Editor widget
        self.editor = SimpleCodeEditor(self)
        self.editor.setReadOnly(True)
        h_group_layout.addWidget(self.editor)

        # Save and close buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not self.readonly:
            self.btn_save_and_close = QPushButton(_('Save and Close'))
            self.btn_save_and_close.setDisabled(True)
            self.btn_save_and_close.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)
        v_group_layout.addLayout(btn_layout)

        # Splitter parameters
        self.central_splitter.setCollapsible(0, False)
        self.central_splitter.setCollapsible(1, True)
        self.central_splitter.setSizes([500, 320])

        # Connect signals
        # Keep a temporary reference of the selection_model to prevent
        # segfault in PySide.
        # See http://permalink.gmane.org/gmane.comp.lib.qt.pyside.devel/222
        selection_model = self.obj_tree.selectionModel()
        selection_model.currentChanged.connect(self._update_details)

        # Check if the values of the model have been changed
        self._proxy_tree_model.sig_setting_data.connect(
            self.save_and_close_enable)

        self._proxy_tree_model.sig_update_details.connect(
            self._update_details_for_item)

    # End of setup_methods
    def _readViewSettings(self, reset=False):
        """
        Reads the persistent program settings.

        :param reset: If True, the program resets to its default settings.
        """
        pos = QPoint(20, 20)
        window_size = QSize(825, 650)
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
                    header.resizeSections(QHeaderView.ResizeToContents)
                    break

            for idx, visible in enumerate(column_visible):
                elem = self.obj_tree.toggle_column_actions_group.actions()[idx]
                elem.setChecked(visible)

        self.resize(window_size)

        button = self.button_group.button(details_button_idx)
        if button is not None:
            button.setChecked(True)

    @Slot()
    def save_and_close_enable(self):
        """Handle the data change event to enable the save and close button."""
        if self.btn_save_and_close:
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

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

    @Slot(TreeItem)
    def _update_details_for_item(self, tree_item):
        """Shows the object details in the editor given an tree_item."""
        try:
            # obj = tree_item.obj
            button_id = self.button_group.checkedId()
            assert button_id >= 0, ("No radio button selected. "
                                    "Please report this bug.")
            attr_details = self._attr_details[button_id]
            data = attr_details.data_fn(tree_item)
            self.editor.setPlainText(data)
            self.editor.setWordWrapMode(attr_details.line_wrap)
            self.editor.setup_editor(
                font=get_font(font_size_delta=DEFAULT_SMALL_DELTA),
                show_blanks=False,
                color_scheme=CONF.get('appearance', 'selected'),
                scroll_past_end=False,
            )
            self.editor.set_text(data)

            if attr_details.name == 'Source code':
                self.editor.set_language('Python')
            else:
                self.editor.set_language('Rst')

        except Exception as ex:
            self.editor.setStyleSheet("color: red;")
            stack_trace = traceback.format_exc()
            self.editor.setPlainText("{}\n\n{}".format(ex, stack_trace))
            self.editor.setWordWrapMode(
                QTextOption.WrapAtWordBoundaryOrAnywhere)

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

    data = np.random.randint(1, 256, size=(100, 100)).astype('uint8')
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
    ObjectExplorer.create_explorer(example, 'Example')


if __name__ == "__main__":
    test()
