# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""Reuse Spyder's outline with secondary-only view state and navigation."""

from spyder.api.plugin_registration.decorators import on_plugin_available, on_plugin_teardown
from spyder.api.plugins import Plugins
from spyder.api.translations import _
from spyder.plugins.outlineexplorer.main_widget import (
    OutlineExplorerActions, OutlineExplorerWidget)
from spyder.plugins.outlineexplorer.plugin import OutlineExplorer
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerTreeWidget


class ReferenceOutlineTree(OutlineExplorerTreeWidget):
    CONF_SECTION = 'reference_outline'


class ReferenceOutlineWidget(OutlineExplorerWidget):
    CONF_SECTION = 'reference_outline'
    CONTEXT_NAME = 'reference_outline'
    TREE_CLASS = ReferenceOutlineTree

    def get_title(self):
        return _('Secondary outline')

    def setup(self):
        super().setup()
        # Parsing policies belong to the shared language server, not a view.
        for action in (OutlineExplorerActions.ShowSpecialComments,
                       OutlineExplorerActions.GroupCodeCells):
            self.get_action(action).setVisible(False)


class ReferenceOutline(OutlineExplorer):
    """A standard dock; the existing outline implementation owns its tree."""

    NAME = 'reference_outline'
    CONF_SECTION = NAME
    REQUIRES = [Plugins.Completions, Plugins.Editor, Plugins.ReferenceEditor]
    TABIFY = [Plugins.Editor]
    WIDGET_CLASS = ReferenceOutlineWidget

    @staticmethod
    def get_name():
        return _('Secondary outline')

    @staticmethod
    def get_description():
        return _('Explore the structure of files in the secondary editor.')

    @on_plugin_available(plugin=Plugins.ReferenceEditor)
    def on_editor_available(self):
        pane = self.get_plugin(Plugins.ReferenceEditor).get_widget()
        widget = self.get_widget()
        pane.set_outlineexplorer(widget)
        widget.edit.connect(self._load_editor)
        widget.edit_goto.connect(self._load_editor)
        manager = self.get_plugin(Plugins.Editor).get_widget()
        for language, capabilities in manager.completion_capabilities.items():
            if language not in widget.get_supported_languages():
                self.start_symbol_services(capabilities, language)

    @on_plugin_teardown(plugin=Plugins.ReferenceEditor)
    def on_editor_teardown(self):
        self.get_plugin(Plugins.ReferenceEditor).get_widget().set_outlineexplorer(None)
        self.get_widget().edit.disconnect(self._load_editor)
        self.get_widget().edit_goto.disconnect(self._load_editor)

    def _load_editor(self, filename, line=None, word=''):
        editor = self.get_plugin(Plugins.ReferenceEditor)
        editor.switch_to_plugin()
        editor.get_widget().load(filename, goto=line, word=word, from_outline=True)
