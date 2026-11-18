# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""A standard dockable secondary editor, backed by the existing editor stack."""

import os.path as osp
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QApplication, QSizePolicy, QVBoxLayout
from superqt import QElidingLabel

from spyder.api.config.decorators import on_conf_change
from spyder.api.plugin_registration.decorators import on_plugin_available, on_plugin_teardown
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.editor.widgets.splitter import EditorSplitter
from spyder.plugins.referenceeditor.confpage import ReferenceEditorConfigPage
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.findreplace import FindReplace


class ReferenceEditorWidget(PluginMainWidget):
    """Own the dock's find bar and lazily cloned editing views."""

    editor_options = {
        'show_tab_bar': 'set_tabbar_visible',
        'show_filename_toolbar': 'set_toptoolbar_visible',
        'show_class_func_dropdown': 'set_classfunc_dropdown_visible',
        'line_numbers': 'set_linenumbers_enabled',
        'indent_guides': 'set_indent_guides',
        'code_folding': 'set_code_folding_enabled',
        'edge_line': 'set_edgeline_enabled',
        'highlight_current_line': 'set_highlight_current_line_enabled',
        'highlight_current_cell': 'set_highlight_current_cell_enabled',
        'automatic_completions': 'set_automatic_completions_enabled',
        'scroll_past_end': 'set_scrollpastend_enabled',
    }

    def __init__(self, name, plugin, parent):
        super().__init__(name, plugin, parent)
        self.editor_main = None
        self.outlineexplorer = None
        self.splitter = None
        self._restore_primary_membership = False
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        self.editor_layout = QVBoxLayout()
        self.editor_layout.setSpacing(0)
        self.editor_layout.addWidget(self.find_widget)
        self.setLayout(self.editor_layout)

    def get_title(self):
        """Return the pane and dock-tab title."""
        return _('Secondary editor')

    def setup(self):
        """Define the pane's menu entry for opening a reference file."""
        self.create_action(
            'open_reference_file', text=_('Open file'),
            icon=self.create_icon('fileopen'), triggered=self.open_file)
        # Like Editor, reuse the stack header rather than a second toolbar row.
        self._main_toolbar.hide()
        self._corner_toolbar.hide()
        self.get_options_menu_button().hide()

    def update_actions(self):
        """File and editing actions are managed by the primary Editor."""

    def set_editor_manager(self, editor_main):
        """Attach the shared document manager without creating editors."""
        self.editor_main = editor_main
        if editor_main is not None:
            editor_main.reference_editor = self

    def transfer_actions(self, stack):
        """Reuse the tab menu, with an explicit destination for each pane."""
        if not hasattr(stack, '_reference_transfer_actions'):
            secondary = stack.editor_owner is self
            labels = ((_('Move to primary editor'), _('Copy to primary editor'))
                      if secondary else
                      (_('Move to secondary editor'), _('Copy to secondary editor')))
            stack._reference_transfer_actions = [
                stack.create_action(
                    'transfer_view_' + str(copy), text=label,
                    triggered=lambda checked=False, copy=copy: self.transfer_tab(stack, copy),
                    register_action=False)
                for copy, label in zip((False, True), labels)]
        return stack._reference_transfer_actions

    def transfer_tab(self, source, copy=False):
        """Ensure a shared target view before removing source membership."""
        info = source.get_current_finfo()
        if info is None:
            return
        filename = info.filename
        if source.editor_owner is self:
            target = self.editor_main.get_last_focused_editorstack(self.editor_main)
            target = target or self.editor_main.editorstacks[0]
            index = target.has_filename(filename)
            existed = index is not None and target.tabs.isTabVisible(index)
            self.editor_main.load(filename, editorwindow=self.editor_main)
        else:
            self.ensure_editor()
            target = self.editor_main.get_last_focused_editorstack(self)
            existed = target.has_filename(filename) is not None
            self.load(filename)
        editor = target.get_current_editor()
        if editor is None or editor.document() is not info.editor.document():
            return
        if not existed:
            editor.setTextCursor(info.editor.textCursor())
            editor.verticalScrollBar().setValue(info.editor.verticalScrollBar().value())
            editor.horizontalScrollBar().setValue(info.editor.horizontalScrollBar().value())
        if not copy:
            if source.editor_owner is self:
                source.close_file(source.has_filename(filename))
            else:
                source.set_tab_visible(source.has_filename(filename), False)
        if target.editor_owner is self:
            self._plugin.switch_to_plugin()
        else:
            self.editor_main.switch_to_plugin()
        target.get_current_view().setFocus()
        return editor

    def close_tab(self, source, index):
        """Close a view locally; let the last view use native document closing."""
        info = source.data[index]
        filename = info.filename
        others = [stack for stack in self.editor_main.editorstacks
                  if stack is not source and (position := stack.has_filename(filename)) is not None
                  and stack.tabs.isTabVisible(position)]
        if source.editor_owner is None:
            if any(stack.editor_owner is self for stack in others):
                source.set_tab_visible(index, False)
                source.add_last_closed_file(filename)
                return True
        elif not others:
            if (not self.editor_main.can_close_file(filename)
                    or not source.save_if_changed(cancelable=True, index=index)):
                return False
            primary = self.editor_main.editorstacks[0]
            position = primary.has_filename(info.filename)
            return primary.close_file(position, force=True) if position is not None else False

    def recover_primary_view(self, filename):
        """Do not leave a document without any accessible tab after local close."""
        manager = self.editor_main
        if getattr(manager, '_closing', False):
            return
        for stack in manager.editorstacks:
            index = stack.has_filename(filename)
            if index is not None and stack.tabs.isTabVisible(index):
                return
        primary = manager.editorstacks[0]
        index = primary.has_filename(filename)
        if index is not None:
            primary.set_tab_visible(index, True)
            primary.set_stack_index(index)

    def set_outlineexplorer(self, outline):
        """Attach/detach only this pane's proxies, including existing views."""
        if self.outlineexplorer is outline:
            return
        self.outlineexplorer = outline
        if self.editor_main is not None:
            for stack in self.editor_main.editorstacks:
                if stack.editor_owner is self:
                    previous = stack.outlineexplorer
                    for info in stack.data:
                        if previous is not None:
                            previous.remove_editor(info.editor.oe_proxy)
                        if outline is not None:
                            info.editor.oe_proxy.is_tree_updated = False
                            outline.register_editor(info.editor.oe_proxy)
                    stack.set_outlineexplorer(outline)
                    stack._refresh_outlineexplorer()

    def get_editor_option(self, option, primary_value=None):
        """Follow primary preferences until the user chooses custom values."""
        following = self.get_conf('use_primary_settings')
        if following and primary_value is not None:
            return primary_value
        section = 'editor' if following else None
        return self.get_conf(option, section=section)

    @on_conf_change(option=[*editor_options, 'use_primary_settings'])
    def on_view_options_changed(self, option, value):
        """Apply preferences to existing views without constructing new ones."""
        if self.editor_main is not None:
            options = self.editor_options if option == 'use_primary_settings' else [option]
            for stack in self.editor_main.editorstacks:
                if stack.editor_owner is self:
                    for key in options:
                        getattr(stack, self.editor_options[key])(self.get_editor_option(key))

    def ensure_editor(self):
        """Create a secondary view only when this pane is first used."""
        if self.splitter is None and self.editor_main is not None:
            focus_widget = QApplication.focusWidget()
            last_stack = self.editor_main.get_current_editorstack()
            self.splitter = EditorSplitter(
                self, self.editor_main,
                [self.get_action('open_reference_file'), *self.editor_main.stack_menu_actions],
                register_editorstack_cb=self.register_editorstack)
            self.editor_layout.insertWidget(0, self.splitter)
            # Refresh native header margins/border after late splitter styling.
            toolbar = self.splitter.editorstack.top_toolbar
            toolbar.setStyleSheet(toolbar.styleSheet())
            settings = self.get_conf('layout_settings', default=None)
            if not self.get_conf('restore_files'):
                settings = None
            if settings is not None:
                self.splitter.set_layout_settings(settings)
                saved_files = settings.get('filenames')
                for position, ((stack, _), (_, filename, lines)) in enumerate(zip(
                        self.splitter.iter_editorstacks(),
                        settings.get('splitsettings', []))):
                    filenames = (saved_files[position] if saved_files is not None
                                 else [filename] if filename else [])
                    self.editor_main.set_last_focused_editorstack(self, stack)
                    if filenames:
                        self.load(filenames)
                    for saved_filename, line in zip(filenames, lines):
                        index = stack.has_filename(saved_filename)
                        if index is not None:
                            stack.data[index].editor.go_to_line(line)
                    if filename:
                        stack.set_current_filename(filename)
                primary_membership = (settings.get('primary_visible_files', [])
                                      if self._restore_primary_membership else [])
                for (stack, _), visible in zip(
                        self.editor_main.editorsplitter.iter_editorstacks(), primary_membership):
                    for index, info in enumerate(stack.data):
                        if info.filename not in visible and any(
                                other.editor_owner is self
                                and other.has_filename(info.filename) is not None
                                for other in self.editor_main.editorstacks):
                            stack.set_tab_visible(index, False)
            elif last_stack is not None and last_stack.get_current_filename():
                self.load(last_stack.get_current_filename())
            self.editor_main.last_focused_editorstack[None] = last_stack
            if focus_widget is not None:
                focus_widget.setFocus()

    def register_editorstack(self, stack):
        """Reuse Editor registration with this pane as the focus owner."""
        stack.fname_label = QElidingLabel()
        stack.fname_label.setElideMode(Qt.ElideMiddle)
        stack.fname_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        path_action = stack.top_toolbar.actions()[0]
        stack.top_toolbar.removeAction(path_action)
        path_action.setDefaultWidget(stack.fname_label)
        stack.top_toolbar.insertAction(stack.top_toolbar.actions()[0], path_action)
        self.editor_main.register_editorstack(stack, owner=self)
        for option, setter in self.editor_options.items():
            getattr(stack, setter)(self.get_editor_option(option))
        stack.create_new_file_if_empty = False
        stack.set_closable(self.splitter is not None)

    def get_focus_widget(self):
        """Return the last active reference editor rather than the left view."""
        if self.splitter is not None:
            stack = self.editor_main.get_last_focused_editorstack(self)
            if stack is not None and stack.get_current_editor() is not None:
                return stack.get_current_view()
        return self

    def open_file(self):
        """Use Spyder's normal file chooser with this pane as the target."""
        self.ensure_editor()
        filename = getattr(self.get_focus_widget(), 'filename', None)
        basedir = osp.dirname(filename) if filename else getcwd_or_home()
        application = self._plugin.get_plugin(Plugins.Application)
        application.get_container().open_file_using_dialog(
            filename, basedir, opener=self.load)

    def load(self, filenames, goto=None, word='', from_outline=False):
        """Open supported text files using the shared Editor file workflow."""
        self.ensure_editor()
        self.editor_main.load(filenames=filenames, goto=goto, word=word,
                              editorwindow=self, from_outline=from_outline)

    def showEvent(self, event):
        """Initialize visible views after startup, not during layout setup."""
        super().showEvent(event)
        if self.splitter is None and not self._plugin.main.is_setting_up:
            # Loading files processes events; let QDockWidget finish showing
            # before changing its child layout.
            QTimer.singleShot(0, self._ensure_visible_editor)

    def _ensure_visible_editor(self):
        if self.isVisible() and not self._plugin.main.is_setting_up:
            self.ensure_editor()

    def on_close(self):
        """Save view state without closing or discarding shared documents."""
        if not self.get_conf('restore_files'):
            self.set_conf('layout_settings', None)
        elif self.splitter is not None:
            settings = self.splitter.get_layout_settings()
            settings['filenames'] = [
                [info.filename for info in stack.data]
                for stack, _ in self.splitter.iter_editorstacks()]
            settings['primary_visible_files'] = [
                [stack.data[index].filename for index in stack.visible_tab_indexes()]
                for stack, _ in self.editor_main.editorsplitter.iter_editorstacks()]
            self.set_conf('layout_settings', settings)
        return True


class ReferenceEditor(SpyderDockablePlugin):
    """Expose the reference editor through Panes and plugin preferences."""

    NAME = 'reference_editor'
    CONF_SECTION = NAME
    CONF_FILE = False
    REQUIRES = [Plugins.Application, Plugins.Editor, Plugins.Preferences]
    TABIFY = [Plugins.VariableExplorer, Plugins.OutlineExplorer, Plugins.Explorer]
    WIDGET_CLASS = ReferenceEditorWidget
    CONF_WIDGET_CLASS = ReferenceEditorConfigPage

    @staticmethod
    def get_name():
        """Return the translated plugin name."""
        return _('Secondary editor')

    @staticmethod
    def get_description():
        """Describe the pane in the standard plugin preferences list."""
        return _('View and edit files alongside the primary editor.')

    @classmethod
    def get_icon(cls):
        """Identify the secondary pane with a theme-aware side-by-side glyph."""
        return cls.create_icon('secondary_editor')

    def on_initialize(self):
        """Restore only after Editor has reopened its previous session."""
        self.main.sig_setup_finished.connect(self.on_mainwindow_visible)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        """Connect to the normal Editor document and action manager."""
        self.get_widget().set_editor_manager(
            self.get_plugin(Plugins.Editor).get_widget())

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        self.get_plugin(Plugins.Preferences).register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        self.get_plugin(Plugins.Preferences).deregister_plugin_preferences(self)

    def on_mainwindow_visible(self):
        """Restore an active reference pane after primary files are loaded."""
        if not self.main.is_setting_up:
            widget = self.get_widget()
            widget._restore_primary_membership = widget.isVisible()
            try:
                if widget.isVisible():
                    widget.ensure_editor()
            finally:
                widget._restore_primary_membership = False

    def on_close(self, cancelable=False):
        """Let Editor handle shared unsaved documents exactly once."""
        return self.get_widget().on_close()
