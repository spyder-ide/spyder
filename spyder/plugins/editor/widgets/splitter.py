# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""EditorSplitter Widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import logging

# Third party imports
import qstylizer.style
from qtpy import PYQT5, PYQT6
from qtpy.QtCore import QByteArray, Qt, Slot
from qtpy.QtWidgets import QSplitter

# Local imports
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import running_under_pytest
from spyder.plugins.editor.widgets.editorstack.editorstack import EditorStack
from spyder.py3compat import qbytearray_to_str
from spyder.utils.palette import SpyderPalette


logger = logging.getLogger(__name__)


class EditorSplitter(QSplitter, SpyderWidgetMixin):
    """QSplitter for editor windows."""

    CONF_SECTION = "editor"

    def __init__(self, parent, main_widget, menu_actions, first=False,
                 register_editorstack_cb=None, unregister_editorstack_cb=None,
                 use_switcher=True):
        """Create a splitter for dividing an editor window into panels.

        Adds a new EditorStack instance to this splitter.  If it's not
        the first splitter, clones the current EditorStack from the
        EditorMainWidget.

        Args:
            parent: Parent widget.
            main_widget: PluginMainWidget this widget belongs to.
            menu_actions: QActions to include from the parent.
            first: Boolean if this is the first splitter in the editor.
            register_editorstack_cb: Callback to register the EditorStack.
                        Defaults to main_widget.register_editorstack() to
                        register the EditorStack with the EditorMainWidget.
            unregister_editorstack_cb: Callback to unregister the EditorStack.
                        Defaults to main_widget.unregister_editorstack() to
                        unregister the EditorStack with the EditorMainWidget.
        """
        if PYQT5 or PYQT6:
            super().__init__(parent, class_parent=main_widget)
        else:
            QSplitter.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=main_widget)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setChildrenCollapsible(False)

        self.toolbar_list = None
        self.menu_list = None

        self.main_widget = main_widget

        if register_editorstack_cb is None:
            register_editorstack_cb = self.main_widget.register_editorstack
        self.register_editorstack_cb = register_editorstack_cb
        if unregister_editorstack_cb is None:
            unregister_editorstack_cb = self.main_widget.unregister_editorstack
        self.unregister_editorstack_cb = unregister_editorstack_cb

        self.menu_actions = menu_actions
        self.editorstack = EditorStack(self, menu_actions, use_switcher)
        self.register_editorstack_cb(self.editorstack)
        if not first:
            self.main_widget.clone_editorstack(editorstack=self.editorstack)
        self.editorstack.destroyed.connect(self.editorstack_closed)
        self.editorstack.sig_split_vertically.connect(
            lambda: self.split(orientation=Qt.Vertical))
        self.editorstack.sig_split_horizontally.connect(
            lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)

        if not running_under_pytest():
            self.editorstack.set_color_scheme(main_widget._get_color_scheme())

        self.setStyleSheet(self._stylesheet)

    def closeEvent(self, event):
        """Override QWidget closeEvent().

        This event handler is called with the given event when Qt
        receives a window close request from a top-level widget.
        """
        QSplitter.closeEvent(self, event)

    def __give_focus_to_remaining_editor(self):
        focus_widget = self.main_widget.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()

    @Slot()
    def editorstack_closed(self):
        logger.debug("Closing EditorStack")

        try:
            self.unregister_editorstack_cb(self.editorstack)
            self.editorstack = None
            close_splitter = self.count() == 1
            if close_splitter:
                # editorstack just closed was the last widget in this QSplitter
                self.close()
                return
            self.__give_focus_to_remaining_editor()
        except (RuntimeError, AttributeError):
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return

    def editorsplitter_closed(self):
        logger.debug("Closing EditorSplitter")
        try:
            close_splitter = self.count() == 1 and self.editorstack is None
        except RuntimeError:
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return

        if close_splitter:
            # editorsplitter just closed was the last widget in this QSplitter
            self.close()
            return
        elif self.count() == 2 and self.editorstack:
            # back to the initial state: a single editorstack instance,
            # as a single widget in this QSplitter: orientation may be changed
            self.editorstack.reset_orientation()

        self.__give_focus_to_remaining_editor()

    def split(self, orientation=Qt.Vertical):
        """
        Create and attach a new EditorSplitter to the current EditorSplitter.

        The new EditorSplitter widget will contain an EditorStack that
        is a clone of the current EditorStack.

        A single EditorSplitter instance can be split multiple times, but the
        orientation will be the same for all the direct splits.  If one of
        the child splits is split, then that split can have a different
        orientation.
        """
        logger.debug("Create a new EditorSplitter")
        self.setOrientation(orientation)
        self.editorstack.set_orientation(orientation)
        editorsplitter = EditorSplitter(
            self.parent(),
            self.main_widget,
            self.menu_actions,
            register_editorstack_cb=self.register_editorstack_cb,
            unregister_editorstack_cb=self.unregister_editorstack_cb
        )
        self.addWidget(editorsplitter)
        editorsplitter.destroyed.connect(self.editorsplitter_closed)
        current_editor = editorsplitter.editorstack.get_current_editor()
        if current_editor is not None:
            current_editor.setFocus()

    def iter_editorstacks(self):
        """Return the editor stacks for this splitter and every first child.

        Note: If a splitter contains more than one splitter as a direct
              child, only the first child's editor stack is included.

        Returns:
            List of tuples containing (EditorStack instance, orientation).
        """
        editorstacks = [(self.widget(0), self.orientation())]
        if self.count() > 1:
            editorsplitter = self.widget(1)
            editorstacks += editorsplitter.iter_editorstacks()
        return editorstacks

    def get_layout_settings(self):
        """Return the layout state for this splitter and its children.

        Record the current state, including file names and current line
        numbers, of the splitter panels.

        Returns:
            A dictionary containing keys {hexstate, sizes, splitsettings}.
                hexstate: String of saveState() for self.
                sizes: List for size() for self.
                splitsettings: List of tuples of the form
                       (orientation, cfname, clines) for each EditorSplitter
                       and its EditorStack.
                           orientation: orientation() for the editor
                                 splitter (which may be a child of self).
                           cfname: EditorStack current file name.
                           clines: Current line number for each file in the
                               EditorStack.
        """
        splitsettings = []
        for editorstack, orientation in self.iter_editorstacks():
            clines = []
            cfname = ''
            # XXX - this overrides value from the loop to always be False?
            orientation = False
            if hasattr(editorstack, 'data'):
                clines = [finfo.editor.get_cursor_line_number()
                          for finfo in editorstack.data]
                cfname = editorstack.get_current_filename()
            splitsettings.append((orientation == Qt.Vertical, cfname, clines))
        return dict(hexstate=qbytearray_to_str(self.saveState()),
                    sizes=self.sizes(), splitsettings=splitsettings)

    def set_layout_settings(self, settings, dont_goto=None):
        """Restore layout state for the splitter panels.

        Apply the settings to restore a saved layout within the editor.  If
        the splitsettings key doesn't exist, then return without restoring
        any settings.

        The current EditorSplitter (self) calls split() for each element
        in split_settings, thus recreating the splitter panels from the saved
        state.  split() also clones the editorstack, which is then
        iterated over to restore the saved line numbers on each file.

        The size and positioning of each splitter panel is restored from
        hexstate.

        Args:
            settings: A dictionary with keys {hexstate, sizes, orientation}
                    that define the layout for the EditorSplitter panels.
            dont_goto: Defaults to None, which positions the cursor to the
                    end of the editor.  If there's a value, positions the
                    cursor on the saved line number for each editor.
        """
        splitsettings = settings.get('splitsettings')
        if splitsettings is None:
            return
        splitter = self
        editor = None
        for i, (is_vertical, cfname, clines) in enumerate(splitsettings):
            if i > 0:
                splitter.split(Qt.Vertical if is_vertical else Qt.Horizontal)
                splitter = splitter.widget(1)
            editorstack = splitter.widget(0)
            for j, finfo in enumerate(editorstack.data):
                editor = finfo.editor
                # TODO: go_to_line is not working properly (the line it jumps
                # to is not the corresponding to that file). This will be fixed
                # in a future PR (which will fix spyder-ide/spyder#3857).
                if dont_goto is not None:
                    # Skip go to line for first file because is already there.
                    pass
                else:
                    try:
                        editor.go_to_line(clines[j])
                    except IndexError:
                        pass
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState(
                QByteArray().fromHex(str(hexstate).encode('utf-8'))
            )
        sizes = settings.get('sizes')
        if sizes is not None:
            self.setSizes(sizes)
        if editor is not None:
            editor.clearFocus()
            editor.setFocus()

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()
        css.QSplitter.setValues(
            background=SpyderPalette.COLOR_BACKGROUND_1
        )
        return css.toString()
