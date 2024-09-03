# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

# Standard library imports
import logging
import traceback
from typing import Any, Callable, Optional

# Third-party imports
from qtpy.QtCore import Slot, QModelIndex, QPoint, QSize, Qt
from qtpy.QtGui import QTextOption
from qtpy.QtWidgets import (
    QAbstractItemView, QButtonGroup, QGroupBox, QHBoxLayout, QHeaderView,
    QMessageBox, QPushButton, QRadioButton, QSplitter, QStyle, QToolButton,
    QVBoxLayout, QWidget)

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.plugins.variableexplorer.widgets.objectexplorer import (
    DEFAULT_ATTR_COLS, DEFAULT_ATTR_DETAILS, ToggleColumnTreeView,
    TreeItem, TreeModel, TreeProxyModel)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import qapplication
from spyder.utils.stylesheet import AppStyle, MAC
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


logger = logging.getLogger(__name__)


class ObjectExplorerActions:
    Refresh = 'refresh_action'
    ShowCallable = 'show_callable_action'
    ShowSpecialAttributes = 'show_special_attributes_action'


class ObjectExplorerMenus:
    Options = 'options_menu'


class ObjectExplorerWidgets:
    OptionsToolButton = 'options_button_widget'
    Toolbar = 'toolbar'
    ToolbarStretcher = 'toolbar_stretcher'

# About message
EDITOR_NAME = 'Object'


class ObjectExplorer(BaseDialog, SpyderFontsMixin, SpyderWidgetMixin):
    """Object explorer main widget window."""
    CONF_SECTION = 'variable_explorer'

    def __init__(self,
                 obj,
                 name='',
                 expanded=False,
                 resize_to_contents=True,
                 parent=None,
                 namespacebrowser=None,
                 data_function: Optional[Callable[[], Any]] = None,
                 attribute_columns=DEFAULT_ATTR_COLS,
                 attribute_details=DEFAULT_ATTR_DETAILS,
                 readonly=None,
                 reset=False):
        """
        Constructor

        :param obj: any Python object or variable
        :param name: name of the object as it will appear in the root node
        :param expanded: show the first visible root element expanded
        :param resize_to_contents: resize columns to contents ignoring width
            of the attributes
        :param namespacebrowser: the NamespaceBrowser that the object
            originates from, if any
        :param attribute_columns: list of AttributeColumn objects that
            define which columns are present in the table and their defaults
        :param attribute_details: list of AttributeDetails objects that define
            which attributes can be selected in the details pane.
        :param reset: If true the persistent settings, such as column widths,
            are reset.
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Model
        self.name = name
        self.expanded = expanded
        self.namespacebrowser = namespacebrowser
        self.data_function = data_function
        self._attr_cols = attribute_columns
        self._attr_details = attribute_details
        self.readonly = readonly

        self.obj_tree = None
        self._proxy_tree_model = None
        self.btn_save_and_close = None
        self.btn_close = None

        # Views
        self._setup_toolbar()
        self._setup_views()
        if self.name:
            self.setWindowTitle(f'{self.name} - {EDITOR_NAME}')
        else:
            self.setWindowTitle(EDITOR_NAME)
        self.setWindowFlags(Qt.Window)

        # Load object into editor
        self.set_value(obj)

        self._resize_to_contents = resize_to_contents
        self._readViewSettings(reset=reset)

    def get_value(self):
        """Get editor current object state."""
        return self._tree_model.inspectedItem.obj

    def set_value(self, obj):
        """Set object displayed in the editor."""
        self._tree_model = TreeModel(obj, obj_name=self.name,
                                     attr_cols=self._attr_cols)

        show_callable_attributes = self.get_conf('show_callable_attributes')
        show_special_attributes = self.get_conf('show_special_attributes')
        self._proxy_tree_model = TreeProxyModel(
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes
        )

        self._proxy_tree_model.setSourceModel(self._tree_model)
        # self._proxy_tree_model.setSortRole(RegistryTableModel.SORT_ROLE)
        self._proxy_tree_model.setDynamicSortFilter(True)
        # self._proxy_tree_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        # Tree widget
        old_obj_tree = self.obj_tree
        self.obj_tree = ToggleColumnTreeView(
            self.namespacebrowser,
            self.data_function
        )
        self.obj_tree.setAlternatingRowColors(True)
        self.obj_tree.setModel(self._proxy_tree_model)
        self.obj_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.obj_tree.setUniformRowHeights(True)
        self.obj_tree.add_header_context_menu()

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

        # Select first row so that a hidden root node will not be selected.
        first_row_index = self._proxy_tree_model.firstItemIndex()
        self.obj_tree.setCurrentIndex(first_row_index)
        if self._tree_model.inspectedNodeIsVisible or self.expanded:
            self.obj_tree.expand(first_row_index)

        # Stretch last column?
        # It doesn't play nice when columns are hidden and then shown again.
        obj_tree_header = self.obj_tree.header()
        obj_tree_header.setSectionsMovable(True)
        obj_tree_header.setStretchLastSection(False)

        # Add menu item for toggling columns to the Options menu
        for action in self.obj_tree.toggle_column_actions_group.actions():
            self.add_item_to_menu(action, self.show_cols_submenu)
        column_visible = [col.col_visible for col in self._attr_cols]
        for idx, visible in enumerate(column_visible):
            elem = self.obj_tree.toggle_column_actions_group.actions()[idx]
            elem.setChecked(visible)

        # Place tree widget in editor
        if old_obj_tree:
            self.central_splitter.replaceWidget(0, self.obj_tree)
            old_obj_tree.deleteLater()
        else:
            self.central_splitter.insertWidget(0, self.obj_tree)
            self.central_splitter.setCollapsible(0, False)
            self.central_splitter.setCollapsible(1, True)
            self.central_splitter.setSizes([500, 320])

    def _make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.obj_tree.setColumnHidden(
            column_idx, not checked)
        return show_column

    def _setup_toolbar(self, show_callable_attributes=False,
                       show_special_attributes=False):
        """
        Sets up the toolbar and the actions in it.
        """
        def do_nothing():
            # .create_action() needs a toggled= parameter, but we can only
            # set it later in the set_value method, so we use this function as
            # a placeholder here.
            pass

        self.toggle_show_callable_action = self.create_action(
            name=ObjectExplorerActions.ShowCallable,
            text=_("Show callable attributes"),
            icon=ima.icon("class"),
            tip=_("Shows/hides attributes that are callable "
                  "(functions, methods etc)"),
            toggled=self._show_callable_attributes,
            option='show_callable_attributes',
            register_action=False
        )

        self.toggle_show_special_attribute_action = self.create_action(
            name=ObjectExplorerActions.ShowSpecialAttributes,
            text=_("Show __special__ attributes"),
            icon=ima.icon("private2"),
            tip=_("Shows or hides __special__ attributes"),
            toggled=self._show_special_attributes,
            option='show_special_attributes',
            register_action=False
        )

        stretcher = self.create_stretcher(
            ObjectExplorerWidgets.ToolbarStretcher
        )

        self.refresh_action = self.create_action(
            name=ObjectExplorerActions.Refresh,
            text=_('Refresh editor with current value of variable in console'),
            icon=ima.icon('refresh'),
            triggered=self.refresh_editor,
            register_action=False
        )
        self.refresh_action.setEnabled(self.data_function is not None)

        self.show_cols_submenu = self.create_menu(
            ObjectExplorerMenus.Options,
            register=False
        )
        self.options_button = self.create_toolbutton(
            name=ObjectExplorerWidgets.OptionsToolButton,
            text=_('Options'),
            icon=ima.icon('tooloptions'),
            register=False
        )
        self.options_button.setPopupMode(QToolButton.InstantPopup)
        self.options_button.setMenu(self.show_cols_submenu)

        self.toolbar = self.create_toolbar(
            ObjectExplorerWidgets.Toolbar,
            register=False
        )

        for item in [
            self.toggle_show_callable_action,
            self.toggle_show_special_attribute_action,
            stretcher,
            self.refresh_action,
            self.options_button
        ]:
            self.add_item_to_toolbar(item, self.toolbar)

        self.toolbar.render()

    def _show_callable_attributes(self, value: bool):
        """
        Called when user toggles "show special attributes" option.
        """
        if self._proxy_tree_model:
            self._proxy_tree_model.setShowCallables(value)
        if self.obj_tree:
            self.obj_tree.resize_columns_to_contents()

    def _show_special_attributes(self, value: bool):
        """
        Called when user toggles "show callable attributes" option.
        """
        if self._proxy_tree_model:
            self._proxy_tree_model.setShowSpecialAttributes(value)
        if self.obj_tree:
            self.obj_tree.resize_columns_to_contents()

    def _setup_views(self):
        """Creates the UI widgets."""

        self.central_splitter = QSplitter(self, orientation=Qt.Vertical)

        # Bottom pane
        bottom_pane_widget = QWidget()
        bottom_pane_widget.setContentsMargins(0, 2*AppStyle.MarginSize, 0, 0)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_pane_widget.setLayout(bottom_layout)
        self.central_splitter.addWidget(bottom_pane_widget)

        group_box = QGroupBox(_("Details"))
        group_box.setStyleSheet(
            'QGroupBox {margin-bottom: 0px; margin-right: -2px;}'
        )
        bottom_layout.addWidget(group_box)

        h_group_layout = QHBoxLayout()
        top_margin = self.style().pixelMetric(QStyle.PM_LayoutTopMargin)
        h_group_layout.setContentsMargins(0, top_margin, 0, 0)
        group_box.setLayout(h_group_layout)

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

        self.button_group.idClicked.connect(
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

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)

        # Remove vertical space between toolbar and data from object
        style = self.style()
        default_spacing = style.pixelMetric(QStyle.PM_LayoutVerticalSpacing)
        layout.addSpacing(-default_spacing)

        layout.addWidget(self.central_splitter)
        layout.addSpacing((-1 if MAC else 2) * AppStyle.MarginSize)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

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
            for idx, size in enumerate(column_sizes):
                if not self._resize_to_contents and size > 0:  # Just in case
                    header.resizeSection(idx, size)
                else:
                    header.resizeSections(QHeaderView.ResizeToContents)
                    break

        self.resize(window_size)

        button = self.button_group.button(details_button_idx)
        if button is not None:
            button.setChecked(True)

    def refresh_editor(self) -> None:
        """
        Refresh data in editor.
        """
        assert self.data_function is not None

        try:
            data = self.data_function()
        except (IndexError, KeyError):
            QMessageBox.critical(
                self,
                _('Object explorer'),
                _('The variable no longer exists.')
            )
            self.reject()
            return

        self.set_value(data)

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
                font=self.get_font(SpyderFontType.MonospaceInterface),
                show_blanks=False,
                color_scheme=self.get_conf('selected', section='appearance'),
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
