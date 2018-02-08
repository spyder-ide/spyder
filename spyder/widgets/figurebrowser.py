# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Figure browser widget

This is the main widget used in the Figure Explorer plugin
"""


# ---- Standard library imports

import os.path as osp


# ---- Third library imports

from qtpy.compat import getsavefilename, getopenfilenames
from qtpy.QtCore import Qt, Signal, Slot, QRect, QEvent
from qtpy.QtGui import QCursor, QImage, QPixmap, QPainter
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QMenu,
                            QMessageBox, QToolButton, QVBoxLayout, QWidget,
                            QLabel, QGridLayout, QFrame, QScrollArea,
                            QGraphicsScene, QGraphicsView, QSplitter,
                            QSizePolicy, QSpinBox,QPushButton,
                            QStyleOptionSlider, QStyle, QScrollBar,
                            QCheckBox)


# ---- Local library imports

from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout)

