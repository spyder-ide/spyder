# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Scroll flag panel for the editor.
"""

# Standard library imports
import logging
from math import ceil
import sys

# Third party imports
from qtpy.QtCore import QSize, Qt, QThread
from qtpy.QtGui import QColor, QCursor, QPainter
from qtpy.QtWidgets import QApplication, QStyle, QStyleOptionSlider
from superqt.utils import qdebounced

# Local imports
from spyder.plugins.completion.api import DiagnosticSeverity
from spyder.plugins.editor.api.panel import Panel
from spyder.plugins.editor.utils.editor import is_block_safe


# For logging
logger = logging.getLogger(__name__)

# Time to wait before refreshing flags
REFRESH_RATE = 1000

# Maximum number of flags to paint in a file
MAX_FLAGS = 1000


class ScrollFlagArea(Panel):
    """Source code editor's scroll flag area"""
    WIDTH = 24 if sys.platform == 'darwin' else 12
    FLAGS_DX = 4
    FLAGS_DY = 2

    def __init__(self):
        Panel.__init__(self)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.scrollable = True
        self.setMouseTracking(True)

        # Define some attributes to be used for unit testing.
        self._unit_testing = False
        self._range_indicator_is_visible = False
        self._alt_key_is_down = False
        self._ctrl_key_is_down = False

        self._slider_range_color = QColor(Qt.gray)
        self._slider_range_color.setAlphaF(.85)
        self._slider_range_brush = QColor(Qt.gray)
        self._slider_range_brush.setAlphaF(.5)

        # Dictionary with flag lists
        self._dict_flag_list = {}

        # Thread to update flags on it.
        self._update_flags_thread = QThread(None)
        self._update_flags_thread.run = self._update_flags
        self._update_flags_thread.finished.connect(self.update)

    def on_install(self, editor):
        """Manages install setup of the pane."""
        super().on_install(editor)
        # Define permanent Qt colors that are needed for painting the flags
        # and the slider range.
        self._facecolors = {
            'warning': QColor(editor.warning_color),
            'error': QColor(editor.error_color),
            'todo': QColor(editor.todo_color),
            'breakpoint': QColor(editor.breakpoint_color),
            'occurrence': QColor(editor.occurrence_color),
            'found_results': QColor(editor.found_results_color)
            }
        self._edgecolors = {key: color.darker(120) for
                            key, color in self._facecolors.items()}

        # Signals
        editor.sig_focus_changed.connect(self.update)
        editor.sig_key_pressed.connect(self.keyPressEvent)
        editor.sig_key_released.connect(self.keyReleaseEvent)
        editor.sig_alt_left_mouse_pressed.connect(self.mousePressEvent)
        editor.sig_alt_mouse_moved.connect(self.mouseMoveEvent)
        editor.sig_leave_out.connect(self.update)
        editor.sig_flags_changed.connect(self.update_flags)
        editor.sig_theme_colors_changed.connect(self.update_flag_colors)

        # This prevents that flags are updated while the user is moving the
        # cursor, e.g. when typing.
        editor.sig_cursor_position_changed.connect(self.update_flags)

    @property
    def slider(self):
        """This property holds whether the vertical scrollbar is visible."""
        return self.editor.verticalScrollBar().isVisible()

    def closeEvent(self, event):
        self._update_flags_thread.quit()
        self._update_flags_thread.wait()
        super().closeEvent(event)

    def sizeHint(self):
        """Override Qt method"""
        return QSize(self.WIDTH, 0)

    def update_flag_colors(self, color_dict):
        """
        Update the permanent Qt colors that are used for painting the flags
        and the slider range with the new colors defined in the given dict.
        """
        for name, color in color_dict.items():
            self._facecolors[name] = QColor(color)
            self._edgecolors[name] = self._facecolors[name].darker(120)

    @qdebounced(timeout=REFRESH_RATE)
    def update_flags(self):
        """Update flags list in a thread."""
        logger.debug("Updating current flags")

        self._dict_flag_list = {
            'error': [],
            'warning': [],
            'todo': [],
            'breakpoint': [],
        }

        # Run this computation in a different thread to prevent freezing
        # the interface
        if not self._update_flags_thread.isRunning():
            self._update_flags_thread.start()

    def _update_flags(self):
        """Update flags list."""
        editor = self.editor
        block = editor.document().firstBlock()
        while block.isValid():
            # Parse all lines in the file looking for something to flag.
            data = block.userData()
            if data:
                if data.code_analysis:
                    for _, _, severity, _ in data.code_analysis:
                        if severity == DiagnosticSeverity.ERROR:
                            flag_type = 'error'
                            break
                    else:
                        flag_type = 'warning'
                elif data.todo:
                    flag_type = 'todo'
                elif data.breakpoint:
                    flag_type = 'breakpoint'
                else:
                    flag_type = None

                if flag_type is not None:
                    self._dict_flag_list[flag_type].append(block)

            block = block.next()

    def paintEvent(self, event):
        """
        Override Qt method.
        Painting the scroll flag area

        There is two cases:
            - The scroll bar is moving, in which case paint all flags.
            - The scroll bar is not moving, only paint flags corresponding
              to visible lines.
        """
        # The area in which the slider handle of the scrollbar may move.
        groove_rect = self.get_scrollbar_groove_rect()

        # This is necessary to catch a possible error when the scrollbar
        # has zero height.
        # Fixes spyder-ide/spyder#21600
        try:
            # The scrollbar's scale factor ratio between pixel span height and
            # value span height
            scale_factor = (
                groove_rect.height() / self.get_scrollbar_value_height()
            )
        except ZeroDivisionError:
            scale_factor = 1

        # The vertical offset of the scroll flag area relative to the
        # top of the text editor.
        offset = groove_rect.y()

        # Note that we calculate the pixel metrics required to draw the flags
        # here instead of using the convenience methods of the ScrollFlagArea
        # for performance reason.
        rect_x = ceil(self.FLAGS_DX / 2)
        rect_w = self.WIDTH - self.FLAGS_DX
        rect_h = self.FLAGS_DY

        # Fill the whole painting area
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

        editor = self.editor

        # Define compute_flag_ypos to position the flags:
        # Paint flags for the entire document
        last_line = editor.document().lastBlock().firstLineNumber()
        # The 0.5 offset is used to align the flags with the center of
        # their corresponding text edit block before scaling.
        first_y_pos = self.value_to_position(
            0.5, scale_factor, offset) - self.FLAGS_DY / 2
        last_y_pos = self.value_to_position(
            last_line + 0.5, scale_factor, offset) - self.FLAGS_DY / 2

        # Compute the height of a line and of a flag in lines.
        line_height = last_y_pos - first_y_pos
        if line_height > 0:
            flag_height_lines = rect_h * last_line / line_height
        else:
            flag_height_lines = 0

        # All the lists of block numbers for flags
        dict_flag_lists = {
            "occurrence": editor.occurrences,
            "found_results": editor.found_results
        }
        dict_flag_lists.update(self._dict_flag_list)

        # The ability to reverse dictionaries was added in Python 3.8.
        # Fixes spyder-ide/spyder#21286
        if sys.version_info[:2] > (3, 7):
            # This is necessary to paint find matches above errors and
            # warnings.
            # See spyder-ide/spyder#20970
            dict_flag_lists_iter = reversed(dict_flag_lists)
        else:
            dict_flag_lists_iter = dict_flag_lists

        for flag_type in dict_flag_lists_iter:
            painter.setBrush(self._facecolors[flag_type])
            painter.setPen(self._edgecolors[flag_type])
            if editor.verticalScrollBar().maximum() == 0:
                # No scroll
                for block in dict_flag_lists[flag_type]:
                    if not is_block_safe(block):
                        continue
                    geometry = editor.blockBoundingGeometry(block)
                    rect_y = ceil(
                        geometry.y() +
                        geometry.height() / 2 +
                        rect_h / 2
                    )
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
            elif last_line == 0:
                # Only one line
                for block in dict_flag_lists[flag_type]:
                    if not is_block_safe(block):
                        continue
                    rect_y = ceil(first_y_pos)
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
            else:
                # Many lines
                if len(dict_flag_lists[flag_type]) < MAX_FLAGS:
                    # If the file is too long, do not freeze the editor
                    next_line = 0
                    for block in dict_flag_lists[flag_type]:
                        if not is_block_safe(block):
                            continue
                        block_line = block.firstLineNumber()
                        # block_line = -1 if invalid
                        if block_line < next_line:
                            # Don't print flags on top of flags
                            continue
                        next_line = block_line + flag_height_lines / 2
                        frac = block_line / last_line
                        rect_y = ceil(first_y_pos + frac * line_height)
                        painter.drawRect(rect_x, rect_y, rect_w, rect_h)

        # Paint the slider range
        if not self._unit_testing:
            modifiers = QApplication.queryKeyboardModifiers()
            alt = modifiers & Qt.KeyboardModifier.AltModifier
            ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        else:
            alt = self._alt_key_is_down
            ctrl = self._ctrl_key_is_down

        if self.slider:
            cursor_pos = self.mapFromGlobal(QCursor().pos())
            is_over_self = self.rect().contains(cursor_pos)
            is_over_editor = editor.rect().contains(
                editor.mapFromGlobal(QCursor().pos()))
            # We use QRect.contains instead of QWidget.underMouse method to
            # determined if the cursor is over the editor or the flag scrollbar
            # because the later gives a wrong result when a mouse button
            # is pressed.
            if is_over_self or (alt and not ctrl and is_over_editor):
                painter.setPen(self._slider_range_color)
                painter.setBrush(self._slider_range_brush)
                x, y, width, height = self.make_slider_range(
                    cursor_pos, scale_factor, offset, groove_rect)
                painter.drawRect(x, y, width, height)
                self._range_indicator_is_visible = True
            else:
                self._range_indicator_is_visible = False

    def enterEvent(self, event):
        """Override Qt method"""
        self.update()

    def leaveEvent(self, event):
        """Override Qt method"""
        self.update()

    def mouseMoveEvent(self, event):
        """Override Qt method"""
        self.update()

    def mousePressEvent(self, event):
        """Override Qt method"""
        if self.slider and event.button() == Qt.LeftButton:
            vsb = self.editor.verticalScrollBar()
            value = self.position_to_value(event.pos().y())
            vsb.setValue(int(value-vsb.pageStep()/2))

    def keyReleaseEvent(self, event):
        """Override Qt method."""
        if event.key() == Qt.Key.Key_Alt:
            self._alt_key_is_down = False
            self.update()
        elif event.key() == Qt.Key.Key_Control:
            self._ctrl_key_is_down = False
            self.update()

    def keyPressEvent(self, event):
        """Override Qt method"""
        if event.key() == Qt.Key_Alt:
            self._alt_key_is_down = True
            self.update()
        elif event.key() == Qt.Key.Key_Control:
            self._ctrl_key_is_down = True
            self.update()

    def get_vertical_offset(self):
        """
        Return the vertical offset of the scroll flag area relative to the
        top of the text editor.
        """
        groove_rect = self.get_scrollbar_groove_rect()
        return groove_rect.y()

    def get_slider_min_height(self):
        """
        Return the minimum height of the slider range based on that set for
        the scroll bar's slider.
        """
        return QApplication.instance().style().pixelMetric(
            QStyle.PM_ScrollBarSliderMin)

    def get_scrollbar_groove_rect(self):
        """Return the area in which the slider handle may move."""
        vsb = self.editor.verticalScrollBar()
        style = QApplication.instance().style()
        opt = QStyleOptionSlider()
        vsb.initStyleOption(opt)

        # Get the area in which the slider handle may move.
        groove_rect = style.subControlRect(
            QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)

        return groove_rect

    def get_scrollbar_position_height(self):
        """Return the pixel span height of the scrollbar area in which
        the slider handle may move"""
        groove_rect = self.get_scrollbar_groove_rect()
        return float(groove_rect.height())

    def get_scrollbar_value_height(self):
        """Return the value span height of the scrollbar"""
        vsb = self.editor.verticalScrollBar()
        return vsb.maximum() - vsb.minimum() + vsb.pageStep()

    def get_scale_factor(self):
        """Return scrollbar's scale factor:
        ratio between pixel span height and value span height"""
        return (self.get_scrollbar_position_height() /
                self.get_scrollbar_value_height())

    def value_to_position(self, y, scale_factor, offset):
        """Convert value to position in pixels"""
        vsb = self.editor.verticalScrollBar()
        return int((y - vsb.minimum()) * scale_factor + offset)

    def position_to_value(self, y):
        """Convert position in pixels to value"""
        vsb = self.editor.verticalScrollBar()
        offset = self.get_vertical_offset()
        return vsb.minimum() + max([0, (y - offset) / self.get_scale_factor()])

    def make_slider_range(self, cursor_pos, scale_factor, offset, groove_rect):
        """
        Return the slider x and y positions and the slider width and height.
        """
        # The slider range indicator position follows the mouse vertical
        # position while its height corresponds to the part of the file that
        # is currently visible on screen.

        vsb = self.editor.verticalScrollBar()
        slider_height = self.value_to_position(
            vsb.pageStep(), scale_factor, offset) - offset
        slider_height = max(slider_height, self.get_slider_min_height())

        # Calculate the minimum and maximum y-value to constraint the slider
        # range indicator position to the height span of the scrollbar area
        # where the slider may move.
        min_ypos = offset
        max_ypos = groove_rect.height() + offset - slider_height

        # Determine the bounded y-position of the slider rect.
        slider_y = max(min_ypos, min(max_ypos,
                                     ceil(cursor_pos.y()-slider_height/2)))

        return 1, slider_y, self.WIDTH - 2, slider_height

    def wheelEvent(self, event):
        """Override Qt method"""
        self.editor.wheelEvent(event)

    def set_enabled(self, state):
        """Toggle scroll flag area visibility"""
        self.enabled = state
        self.setVisible(state)
