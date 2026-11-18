# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""View-local preferences for the secondary editor."""

from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.plugins.editor.confpage import (
    create_editor_display_groups, create_editor_view_checkbox)


class ReferenceEditorConfigPage(PluginConfigPage):
    """Reuse native controls without duplicating source-editing policies."""

    def setup_page(self):
        self.follow_primary = self.create_checkbox(
            _('Use primary editor settings'), 'use_primary_settings',
            tip=_('Disable this option to customize the secondary editor.'))
        self.custom_groups = create_editor_display_groups(self)
        self.custom_groups[1].layout().addWidget(
            create_editor_view_checkbox(self, 'edge_line'))
        self.create_tab(_('Display'), self.custom_groups)
        editing = QGroupBox(_('Behavior'))
        QVBoxLayout(editing).addWidget(
            create_editor_view_checkbox(self, 'automatic_completions'))
        self.custom_groups.append(editing)
        session = QGroupBox(_('Files'))
        QVBoxLayout(session).addWidget(self.create_checkbox(
            _('Restore previously opened reference files'), 'restore_files'))
        shared = QLabel(_(
            'Font, colors, line wrapping and source-editing rules are shared '
            'with the primary editor.'))
        shared.setWordWrap(True)
        self.create_tab(_('Behavior'), [editing, session, shared])
        self.layout().insertWidget(0, self.follow_primary)
        self.follow_primary.checkbox.toggled.connect(self._set_follow_primary)

    def _set_follow_primary(self, checked):
        """Preserve custom factory/user values while following the primary."""
        for group in self.custom_groups:
            group.setEnabled(not checked)

    def load_from_conf(self):
        super().load_from_conf()
        self._set_follow_primary(self.follow_primary.checkbox.isChecked())
        self.set_modified(False)
