# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Help Plugin Configuration Page."""

# Standard library imports

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QLabel

# Local imports
from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage
from spyder.utils import programs


class HelpConfigPage(PluginConfigPage):
    def setup_page(self):
        # Connections group
        connections_group = QGroupBox(_("Automatic connections"))
        connections_label = QLabel(_("This pane can automatically "
                                     "show an object's help information after "
                                     "a left parenthesis is written next to it. "
                                     "Below you can decide to which plugin "
                                     "you want to connect it to turn on this "
                                     "feature."))
        connections_label.setWordWrap(True)
        editor_box = self.create_checkbox(_("Editor"), 'connect/editor')

        ipython_box = self.create_checkbox(_("IPython Console"),
                                           'connect/ipython_console')

        connections_layout = QVBoxLayout()
        connections_layout.addWidget(connections_label)
        connections_layout.addWidget(editor_box)
        connections_layout.addWidget(ipython_box)
        connections_group.setLayout(connections_layout)

        # Features group
        features_group = QGroupBox(_("Additional features"))
        math_box = self.create_checkbox(_("Render mathematical equations"),
                                        'math')
        req_sphinx = programs.is_module_installed('sphinx', '>=1.1')
        math_box.setEnabled(req_sphinx)
        if not req_sphinx:
            sphinx_ver = programs.get_module_version('sphinx')
            sphinx_tip = _("This feature requires Sphinx 1.1 or superior.")
            sphinx_tip += "\n" + _("Sphinx %s is currently installed.") % sphinx_ver
            math_box.setToolTip(sphinx_tip)

        features_layout = QVBoxLayout()
        features_layout.addWidget(math_box)
        features_group.setLayout(features_layout)

        # Source code group
        sourcecode_group = QGroupBox(_("Source code"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_group.setLayout(sourcecode_layout)

        # Final layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(connections_group)
        vlayout.addWidget(features_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

