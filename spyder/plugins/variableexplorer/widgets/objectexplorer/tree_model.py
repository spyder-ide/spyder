# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Based on: PySide examples/itemviews/simpletreemodel
# See: http://harmattan-dev.nokia.com/docs/library/html/qt4/
# itemviews-simpletreemodel.html
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

# Standard library imports
import logging
from difflib import SequenceMatcher

# Third-party imports
from qtpy.QtCore import (QAbstractItemModel, QModelIndex, Qt,
                         QSortFilterProxyModel, Signal)
from qtpy.QtGui import QBrush, QColor
from spyder_kernels.utils.nsview import is_editable_type

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.plugins.variableexplorer.widgets.objectexplorer.utils import (
    cut_off_str)
from spyder.plugins.variableexplorer.widgets.objectexplorer.tree_item import (
    TreeItem)
from spyder.py3compat import to_unichr
from spyder.utils import icon_manager as ima

logger = logging.getLogger(__name__)


# TODO: a lot of methods (e.g. rowCount) test if parent.column() > 0.
# This should probably be replaced with an assert.

# Keep the method names camelCase since it inherits from a Qt object.
# Disabled need for docstrings. For a good explanation of the methods,
# take a look at the Qt simple tree model example.
# See: http://harmattan-dev.nokia.com/docs/
# library/html/qt4/itemviews-simpletreemodel.html

# The main window inherits from a Qt class, therefore it has many
# ancestors public methods and attributes.
class TreeModel(QAbstractItemModel):
    """
    Model that provides an interface to an objectree
    that is build of TreeItems.
    """
    def __init__(self,
                 obj,
                 obj_name='',
                 attr_cols=None,
                 parent=None,
                 regular_font=None,
                 special_attribute_font=None):
        """
        Constructor

        :param obj: any Python object or variable
        :param obj_name: name of the object as it will appear in the root node
                         If empty, no root node will be drawn.
        :param attr_cols: list of AttributeColumn definitions
        :param parent: the parent widget
        """
        super(TreeModel, self).__init__(parent)
        self._attr_cols = attr_cols

        # Font for members (non-functions)
        self.regular_font = regular_font if regular_font else get_font()
        # Font for __special_attributes__
        self.special_attribute_font = (special_attribute_font
                                       if special_attribute_font
                                       else get_font())
        self.special_attribute_font.setItalic(False)

        self.regular_color = QBrush(QColor(ima.MAIN_FG_COLOR))
        self.callable_color = QBrush(
            QColor(ima.MAIN_FG_COLOR))  # for functions, methods, etc.

        # The following members will be initialized by populateTree
        # The rootItem is always invisible. If the obj_name
        # is the empty string, the inspectedItem
        # will be the rootItem (and therefore be invisible).
        # If the obj_name is given, an
        # invisible root item will be added and the
        # inspectedItem will be its only child.
        # In that case the inspected item will be visible.
        self._inspected_node_is_visible = None
        self._inspected_item = None
        self._root_item = None
        self.populateTree(obj, obj_name=obj_name)

    @property
    def inspectedNodeIsVisible(self):
        """
        Returns True if the inspected node is visible.
        In that case an invisible root node has been added.
        """
        return self._inspected_node_is_visible

    @property
    def rootItem(self):
        """ The root TreeItem.
        """
        return self._root_item

    @property
    def inspectedItem(self):
        """The TreeItem that contains the item under inspection."""
        return self._inspected_item

    def rootIndex(self):  # TODO: needed?
        """
        The index that returns the root element
        (same as an invalid index).
        """
        return QModelIndex()

    def inspectedIndex(self):
        """The model index that point to the inspectedItem."""
        if self.inspectedNodeIsVisible:
            return self.createIndex(0, 0, self._inspected_item)
        else:
            return self.rootIndex()

    def columnCount(self, _parent=None):
        """ Returns the number of columns in the tree """
        return len(self._attr_cols)

    def data(self, index, role):
        """Returns the tree item at the given index and role."""
        if not index.isValid():
            return None

        col = index.column()
        tree_item = index.internalPointer()
        obj = tree_item.obj

        if role == Qt.DisplayRole:
            try:
                attr = self._attr_cols[col].data_fn(tree_item)
                # Replace carriage returns and line feeds with unicode glyphs
                # so that all table rows fit on one line.
                return (attr.replace('\r\n', to_unichr(0x21B5))
                            .replace('\n', to_unichr(0x21B5))
                            .replace('\r', to_unichr(0x21B5)))
            except Exception as ex:
                # logger.exception(ex)
                return "**ERROR**: {}".format(ex)

        elif role == Qt.TextAlignmentRole:
            return self._attr_cols[col].alignment

        elif role == Qt.ForegroundRole:
            if tree_item.is_callable:
                return self.callable_color
            else:
                return self.regular_color

        elif role == Qt.FontRole:
            if tree_item.is_attribute:
                return self.special_attribute_font
            else:
                return self.regular_font
        elif role == Qt.EditRole:
            return obj
        else:
            return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._attr_cols[section].name
        else:
            return None

    def treeItem(self, index):
        if not index.isValid():
            return self.rootItem
        else:
            return index.internalPointer()

    def index(self, row, column, parent=None):

        if parent is None:
            logger.debug("parent is None")
            parent = QModelIndex()

        parentItem = self.treeItem(parent)

        if not self.hasIndex(row, column, parent):
            logger.debug("hasIndex "
                         "is False: ({}, {}) {!r}".format(row,
                                                          column, parentItem))
            # logger.warn("Parent index model"
            #             ": {!r} != {!r}".format(parent.model(), self))

            return QModelIndex()

        childItem = parentItem.child(row)
        # logger.debug("  {}".format(childItem.obj_path))
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            logger.warn("no childItem")
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None or parent_item == self.rootItem:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=None):
        parent = QModelIndex() if parent is None else parent

        if parent.column() > 0:
            # This is taken from the PyQt simpletreemodel example.
            return 0
        else:
            return self.treeItem(parent).child_count()

    def hasChildren(self, parent=None):
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return 0
        else:
            return self.treeItem(parent).has_children

    def canFetchMore(self, parent=None):
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return 0
        else:
            result = not self.treeItem(parent).children_fetched
            # logger.debug("canFetchMore: {} = {}".format(parent, result))
            return result

    def fetchMore(self, parent=None):
        """
        Fetches the children given the model index of a parent node.
        Adds the children to the parent.
        """
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return

        parent_item = self.treeItem(parent)
        if parent_item.children_fetched:
            return

        tree_items = self._fetchObjectChildren(parent_item.obj,
                                               parent_item.obj_path)

        self.beginInsertRows(parent, 0, len(tree_items) - 1)
        for tree_item in tree_items:
            parent_item.append_child(tree_item)

        parent_item.children_fetched = True
        self.endInsertRows()

    def _fetchObjectChildren(self, obj, obj_path):
        """
        Fetches the children of a Python object.
        Returns: list of TreeItems
        """
        obj_children = []
        path_strings = []
        tree_items = []

        # Only populate children for objects without their own editor
        if not is_editable_type(obj):
            is_attr_list = [False] * len(obj_children)

            # Object attributes
            # Needed to handle errors while getting object's attributes
            # Related with spyder-ide/spyder#6728 and spyder-ide/spyder#9959
            for attr_name in dir(obj):
                try:
                    attr_value = getattr(obj, attr_name)
                    obj_children.append((attr_name, attr_value))
                    path_strings.append('{}.{}'.format(obj_path, attr_name)
                                        if obj_path else attr_name)
                    is_attr_list.append(True)
                except Exception:
                    # Attribute could not be get
                    pass
            assert len(obj_children) == len(path_strings), "sanity check"

            for item, path_str, is_attr in zip(obj_children, path_strings,
                                               is_attr_list):
                name, child_obj = item
                tree_items.append(TreeItem(child_obj, name, path_str, is_attr))

        return tree_items

    def populateTree(self, obj, obj_name='', inspected_node_is_visible=None):
        """Fills the tree using a python object. Sets the rootItem."""
        logger.debug("populateTree with object id = 0x{:x}".format(id(obj)))
        if inspected_node_is_visible is None:
            inspected_node_is_visible = (obj_name != '')
        self._inspected_node_is_visible = inspected_node_is_visible

        if self._inspected_node_is_visible:
            self._root_item = TreeItem(None, _('<invisible_root>'),
                                       _('<invisible_root>'), None)
            self._root_item.children_fetched = True
            self._inspected_item = TreeItem(obj, obj_name,
                                            obj_name, is_attribute=None)
            self._root_item.append_child(self._inspected_item)
        else:
            # The root itself will be invisible
            self._root_item = TreeItem(obj, obj_name,
                                       obj_name, is_attribute=None)
            self._inspected_item = self._root_item

            # Fetch all items of the root so we can
            # select the first row in the constructor.
            root_index = self.index(0, 0)
            self.fetchMore(root_index)

    def _auxRefreshTree(self, tree_index):
        """
        Auxiliary function for refreshTree that recursively refreshes the
        tree nodes.

        If the underlying Python object has been changed, we don't want to
        delete the old tree model and create a new one from scratch because
        this loses all information about which nodes are fetched and expanded.
        Instead the old tree model is updated. Using the difflib from the
        standard library it is determined for a parent node which child nodes
        should be added or removed. This is done based on the node names only,
        not on the node contents (the underlying Python objects). Testing the
        underlying nodes for equality is potentially slow. It is faster to
        let the refreshNode function emit the dataChanged signal for all cells.
        """
        tree_item = self.treeItem(tree_index)
        logger.debug("_auxRefreshTree({}): {}{}".format(
            tree_index, tree_item.obj_path,
            "*" if tree_item.children_fetched else ""))

        if tree_item.children_fetched:

            old_items = tree_item.child_items
            new_items = self._fetchObjectChildren(tree_item.obj,
                                                  tree_item.obj_path)

            old_item_names = [(item.obj_name,
                               item.is_attribute) for item in old_items]
            new_item_names = [(item.obj_name,
                               item.is_attribute) for item in new_items]
            seqMatcher = SequenceMatcher(isjunk=None, a=old_item_names,
                                         b=new_item_names,
                                         autojunk=False)
            opcodes = seqMatcher.get_opcodes()

            logger.debug("(reversed) "
                         "opcodes: {}".format(list(reversed(opcodes))))

            for tag, i1, i2, j1, j2 in reversed(opcodes):

                if 1 or tag != 'equal':
                    logger.debug("  {:7s}, a[{}:{}] ({}), b[{}:{}] ({})"
                                 .format(tag, i1, i2,
                                         old_item_names[i1:i2], j1, j2,
                                         new_item_names[j1:j2]))

                if tag == 'equal':
                    # Only when node names are equal is _auxRefreshTree
                    # called recursively.
                    assert i2-i1 == j2-j1, ("equal sanity "
                                            "check failed "
                                            "{} != {}".format(i2-i1, j2-j1))
                    for old_row, new_row in zip(range(i1, i2), range(j1, j2)):
                        old_items[old_row].obj = new_items[new_row].obj
                        child_index = self.index(old_row, 0, parent=tree_index)
                        self._auxRefreshTree(child_index)

                elif tag == 'replace':
                    # Explicitly remove the old item and insert the new.
                    # The old item may have child nodes which indices must be
                    # removed by Qt, otherwise it crashes.
                    assert i2-i1 == j2-j1, ("replace sanity "
                                            "check failed "
                                            "{} != {}").format(i2-i1, j2-j1)

                    # row number of first removed
                    first = i1
                    # row number of last element after insertion
                    last = i1 + i2 - 1
                    logger.debug("     calling "
                                 "beginRemoveRows({}, {}, {})".format(
                                    tree_index, first, last))
                    self.beginRemoveRows(tree_index, first, last)
                    del tree_item.child_items[i1:i2]
                    self.endRemoveRows()

                    # row number of first element after insertion
                    first = i1
                    # row number of last element after insertion
                    last = i1 + j2 - j1 - 1
                    logger.debug("     calling "
                                 "beginInsertRows({}, {}, {})".format(
                                    tree_index, first, last))
                    self.beginInsertRows(tree_index, first, last)
                    tree_item.insert_children(i1, new_items[j1:j2])
                    self.endInsertRows()

                elif tag == 'delete':
                    assert j1 == j2, ("delete"
                                      " sanity check "
                                      "failed. {} != {}".format(j1, j2))
                    # row number of first that will be removed
                    first = i1
                    # row number of last element after insertion
                    last = i1 + i2 - 1
                    logger.debug("     calling "
                                 "beginRemoveRows"
                                 "({}, {}, {})".format(tree_index,
                                                       first, last))
                    self.beginRemoveRows(tree_index, first, last)
                    del tree_item.child_items[i1:i2]
                    self.endRemoveRows()

                elif tag == 'insert':
                    assert i1 == i2, ("insert "
                                      "sanity check "
                                      "failed. {} != {}".format(i1, i2))
                    # row number of first element after insertion
                    first = i1
                    # row number of last element after insertion
                    last = i1 + j2 - j1 - 1
                    logger.debug("     "
                                 "calling beginInsertRows"
                                 "({}, {}, {})".format(tree_index,
                                                       first, last))
                    self.beginInsertRows(tree_index, first, last)
                    tree_item.insert_children(i1, new_items[j1:j2])
                    self.endInsertRows()
                else:
                    raise ValueError("Invalid tag: {}".format(tag))

    def refreshTree(self):
        """
        Refreshes the tree model from the underlying root object
        (which may have been changed).
        """
        logger.info("")
        logger.info("refreshTree: {}".format(self.rootItem))

        root_item = self.treeItem(self.rootIndex())
        logger.info("  root_item:      {} (idx={})".format(root_item,
                                                           self.rootIndex()))
        inspected_item = self.treeItem(self.inspectedIndex())
        logger.info("  inspected_item: {} (idx={})".format(
            inspected_item,
            self.inspectedIndex()))

        assert (root_item is inspected_item) != self.inspectedNodeIsVisible, \
            "sanity check"

        self._auxRefreshTree(self.inspectedIndex())

        root_obj = self.rootItem.obj
        logger.debug("After _auxRefreshTree, "
                     "root_obj: {}".format(cut_off_str(root_obj, 80)))
        self.rootItem.pretty_print()

        # Emit the dataChanged signal for all cells.
        # This is faster than checking which nodes
        # have changed, which may be slow for some underlying Python objects.
        n_rows = self.rowCount()
        n_cols = self.columnCount()
        top_left = self.index(0, 0)
        bottom_right = self.index(n_rows-1, n_cols-1)

        logger.debug("bottom_right: ({}, {})".format(bottom_right.row(),
                                                     bottom_right.column()))
        self.dataChanged.emit(top_left, bottom_right)


class TreeProxyModel(QSortFilterProxyModel):
    """Proxy model that overrides the sorting and can filter out items."""
    sig_setting_data = Signal()
    sig_update_details = Signal(object)

    def __init__(self,
                 show_callable_attributes=True,
                 show_special_attributes=True,
                 dataframe_format=None,
                 parent=None):
        """
        Constructor

        :param show_callable_attributes: if True the callables objects,
            i.e. objects (such as function) that  a __call__ method,
            will be displayed (in brown). If False they are hidden.
        :param show_special_attributes: if True the objects special attributes,
            i.e. methods with a name that starts and ends with two underscores,
            will be displayed (in italics). If False they are hidden.
        :param dataframe_format: the dataframe format from config.
        :param parent: the parent widget
        """
        super(TreeProxyModel, self).__init__(parent)

        self._show_callables = show_callable_attributes
        self._show_special_attributes = show_special_attributes
        self.dataframe_format = dataframe_format

    def get_key(self, proxy_index):
        """Get item handler for the given index."""
        return self.treeItem(proxy_index)

    def treeItem(self, proxy_index):
        index = self.mapToSource(proxy_index)
        return self.sourceModel().treeItem(index)

    def set_value(self, proxy_index, value):
        """Set item value."""
        index = self.mapToSource(proxy_index)
        tree_item = self.sourceModel().treeItem(index)
        tree_item.obj = value
        obj_name = tree_item.obj_name
        parent = tree_item.parent_item.obj
        setattr(parent, obj_name, value)
        self.sig_setting_data.emit()
        self.sig_update_details.emit(tree_item)

    def firstItemIndex(self):
        """Returns the first child of the root item."""
        # We cannot just call the same function of the source model
        # because the first node there may be hidden.
        source_root_index = self.sourceModel().rootIndex()
        proxy_root_index = self.mapFromSource(source_root_index)
        first_item_index = self.index(0, 0, proxy_root_index)
        return first_item_index

    def filterAcceptsRow(self, sourceRow, sourceParentIndex):
        """
        Returns true if the item in the row indicated by the given source_row
        and source_parent should be included in the model.
        """
        parent_item = self.sourceModel().treeItem(sourceParentIndex)
        tree_item = parent_item.child(sourceRow)

        accept = ((self._show_special_attributes or
                   not tree_item.is_special_attribute) and
                  (self._show_callables or
                   not tree_item.is_callable_attribute))

        return accept

    def getShowCallables(self):
        return self._show_callables

    def setShowCallables(self, show_callables):
        """
        Shows/hides show_callables, which have a __call__ attribute.
        Repopulates the tree.
        """
        logger.debug("setShowCallables: {}".format(show_callables))
        self._show_callables = show_callables
        self.invalidateFilter()

    def getShowSpecialAttributes(self):
        return self._show_special_attributes

    def setShowSpecialAttributes(self, show_special_attributes):
        """
        Shows/hides special attributes, which begin with an underscore.
        Repopulates the tree.
        """
        logger.debug("setShowSpecialAttributes:"
                     " {}".format(show_special_attributes))
        self._show_special_attributes = show_special_attributes
        self.invalidateFilter()
