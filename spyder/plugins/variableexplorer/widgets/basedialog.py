# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Base variable explorer dialog
"""

# Third party imports
from qtpy.QtWidgets import QDialog


class BaseDialog(QDialog):
    def set_dynamic_width_and_height(self, screen_geometry, width_ratio=0.5,
                                     height_ratio=0.5):
        """
        Update width and height using an updated screen geometry.
        Use a ratio for the width and height of the dialog.
        """
        screen_width = int(screen_geometry.width() * width_ratio)
        screen_height = int(screen_geometry.height() * height_ratio)
        self.resize(screen_width, screen_height)

        # Make the dialog window appear in the center of the screen
        x = int(screen_geometry.center().x() - self.width() / 2)
        y = int(screen_geometry.center().y() - self.height() / 2)
        self.move(x, y)

    def show(self):
        super(BaseDialog, self).show()
        window = self.window()
        windowHandle = window.windowHandle()
        screen = windowHandle.screen()
        geometry = screen.geometry()
        self.set_dynamic_width_and_height(geometry)
        screen.geometryChanged.connect(self.set_dynamic_width_and_height)
