# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project config page."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QGridLayout, QVBoxLayout
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
import spyder.utils.icon_manager as ima


class ProjectConfigPage(PluginConfigPage):
    def get_name(self):
        return _("Project")

    def get_icon(self):
        return ima.icon('project')

    def setup_page(self):
        newcb = self.create_checkbox

        vcs_group = QGroupBox(_("Version control"))
        use_version_control = newcb(_("Highlight files based on vcs status"),
                                    'use_version_control')
        color_group = QGroupBox("Colors")
        color_layout = QGridLayout()
        names = ['untracked', 'ignored', 'modified', 'added', 'conflict']
        for row, key in enumerate(names):
            option = "color/{0}".format(key)
            label, clayout = self.create_coloredit(
                    key.capitalize(),
                    option,
                    without_layout=True,
                    )
            color_layout.addWidget(label, row+1, 0)
            color_layout.addLayout(clayout, row+1, 1, alignment=Qt.AlignLeft)
        color_group.setLayout(color_layout)
        use_version_control.toggled.connect(color_group.setEnabled)
        if not self.get_option('use_version_control'):
            color_group.setEnabled(False)

        vcs_layout = QVBoxLayout()
        vcs_layout.addWidget(use_version_control)
        vcs_layout.addWidget(color_group)
        vcs_group.setLayout(vcs_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(vcs_group)
        vlayout.addWidget(color_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
