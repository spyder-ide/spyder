# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2010 IPython Development Team
# Copyright (c) 2013- Spyder Project Contributors
#
# Distributed under the terms of the Modified BSD License
# (BSD 3-clause; see NOTICE.txt in the Spyder root directory for details).
# -----------------------------------------------------------------------------

"""
Calltip widget used only to show signatures.

Adapted from IPython/frontend/qt/console/call_tip_widget.py of the
`IPython Project <https://github.com/ipython/ipython>`_.
Now located at qtconsole/call_tip_widget.py as part of the
`Jupyter QtConsole Project <https://github.com/jupyter/qtconsole>`_.
"""

# Standard library imports
from unicodedata import category
import sys

# Third party imports
import qstylizer.style
from qtpy.QtCore import (QBasicTimer, QCoreApplication, QEvent, Qt, QTimer,
                         Signal)
from qtpy.QtGui import QCursor, QFontMetrics, QPalette
from qtpy.QtWidgets import (QApplication, QFrame, QLabel, QTextEdit,
                            QPlainTextEdit, QStyle, QStyleOptionFrame,
                            QStylePainter, QToolTip)

# Local imports
from spyder.config.gui import is_dark_interface
from spyder.utils.palette import SpyderPalette


BACKGROUND_COLOR = (
    SpyderPalette.COLOR_BACKGROUND_4 if is_dark_interface() else
    SpyderPalette.COLOR_BACKGROUND_2
)


class ToolTipWidget(QLabel):
    """
    Shows tooltips that can be styled with the different themes.
    """

    # Delay in miliseconds before hiding the tooltip
    HIDE_DELAY = 50

    # Signals
    sig_completion_help_requested = Signal(str, str)
    sig_help_requested = Signal(str)

    def __init__(self, parent=None):
        """
        Shows tooltips that can be styled with the different themes.
        """
        super().__init__(parent, Qt.ToolTip)

        # Variables
        self.completion_doc = None
        self._url = ''
        self.app = QCoreApplication.instance()
        self._as_hover = False
        self._as_hint = False
        self._hovered = False
        self._timer_hide = QTimer()
        self._text_edit = parent
        self.show_help_on_click = False

        # Setup
        # This keeps the hints below other applications
        if sys.platform == 'darwin':
            self.setWindowFlags(Qt.SplashScreen)
        else:
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)

        self._timer_hide.setInterval(self.HIDE_DELAY)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(False)
        self.setForegroundRole(QPalette.ToolTipText)
        self.setBackgroundRole(QPalette.ToolTipBase)
        self.setPalette(QToolTip.palette())
        self.setAlignment(Qt.AlignLeft)
        self.setIndent(1)
        self.setFrameStyle(QFrame.NoFrame)
        style = self.style()
        delta_margin = style.pixelMetric(QStyle.PM_ToolTipLabelFrameWidth,
                                         None, self)
        self.setMargin(1 + delta_margin)

        # Signals
        self.linkHovered.connect(self._update_hover_html_link_style)
        self._timer_hide.timeout.connect(self._hide)
        QApplication.instance().applicationStateChanged.connect(
            self._should_hide
        )

        # Style
        self.setStyleSheet(self._stylesheet)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _update_hover_html_link_style(self, url):
        """Update style of labels that include rich text and html links."""
        link = 'text-decoration:none;'
        link_hovered = 'text-decoration:underline;'
        self._url = url

        if url:
            self.setCursor(Qt.PointingHandCursor)
            new_text, old_text = link_hovered, link
        else:
            new_text, old_text = link, link_hovered

        text = self.text()
        new_text = text.replace(old_text, new_text)

        self.setText(new_text)

    def _should_hide(self, state):
        """
        This widget should hide itself if the application is not active.
        """
        if state != Qt.ApplicationActive:
            self._hide()

    def _hide(self):
        """Call the actual hide method."""
        super().hide()

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()

        css["ToolTipWidget"].setValues(
            backgroundColor=BACKGROUND_COLOR,
            border=f"1px solid {SpyderPalette.COLOR_TEXT_4}"
        )

        return css.toString()

    # ---- Public API
    # -------------------------------------------------------------------------
    def show_tip(self, point, tip, cursor=None, completion_doc=None,
                 vertical_position='bottom', show_help_on_click=False):
        """Attempt to show the tip at the current mouse location."""

        # Don't show the widget if the main window is not focused
        if QApplication.instance().applicationState() != Qt.ApplicationActive:
            return

        # Set the text and resize the widget accordingly.
        self.setText(tip)
        self.resize(self.sizeHint())

        self.completion_doc = completion_doc
        self.show_help_on_click = show_help_on_click

        text_edit = self._text_edit
        screen_rect = self.screen().geometry()

        tip_height = self.size().height()
        tip_width = self.size().width()

        text_edit_height = text_edit.size().height()
        text_edit_gpos = (
            # If text_edit is a window in itself (e.g. when used indenpendently
            # in our tests) we don't need to get its global position because
            # text_edit.pos() already gives it.
            text_edit.mapToGlobal(text_edit.pos())
            if not text_edit.isWindow()
            else text_edit.pos()
        )

        vertical = vertical_position
        horizontal = 'Right'

        # Check if tip is vertically off text_edit
        if (
            # Tip is off at text_edit's bottom
            point.y() + tip_height > text_edit_gpos.y() + text_edit_height
            # Tip is off at the top
            or point.y() - tip_height < text_edit_gpos.y()
        ):
            if point.y() - tip_height < text_edit_gpos.y():
                vertical = 'bottom'
            else:
                vertical = 'top'

        # Check if tip is horizontally off screen to the right
        if point.x() + tip_width > screen_rect.x() + screen_rect.width():
            if 2 * point.x() < screen_rect.width():
                horizontal = 'Right'
            else:
                horizontal = 'Left'

        # Set coordinates where the tip will be placed
        if vertical == 'top':
            # The +2 below is necessary to leave no vertical space between the
            # tooltip and the text.
            point.setY(point.y() - tip_height + 2)
        else:
            font = text_edit.font()
            text_height = QFontMetrics(font).capHeight()

            # Ubuntu Mono has a strange behavior regarding its height that we
            # need to account for. Other monospaced fonts behave as expected.
            if font.family() == 'Ubuntu Mono':
                padding = 2
            else:
                padding = 1 if sys.platform == "darwin" else 5

            # Qt sets the mouse coordinates (given by `point`) a bit above the
            # line where it's placed, i.e. not exactly where the text
            # vertically starts. So, we need to add an extra height (twice the
            # cap height plus some padding) to place the tip at the line's
            # bottom.
            point.setY(point.y() + 2 * text_height + padding)

        if horizontal == 'Left':
            point.setX(point.x() - tip_width)
        else:
            # The -2 below is necessary to horizontally align the hover to
            # the text.
            point.setX(point.x() - (2 if self._as_hover else 0))

        # Move tip to new coordinates
        self.move(point)

        # Show tip
        if not self.isVisible():
            self._timer_hide.stop()
            self.show()

        return True

    def set_as_tooltip(self):
        """Make the widget work as a tooltip."""
        self.reset_state()

    def set_as_hint(self):
        """Make the widget work to display code completion hints."""
        self._as_hint = True
        self._as_hover = False

    def set_as_hover(self):
        """Make the widget work to display hovers."""
        self._as_hover = True
        self._as_hint = False

    def is_hint(self):
        """Check if the widget is used as a completion hint."""
        return self._as_hint

    def is_hover(self):
        """Check if the widget is used as a hover."""
        return self._as_hover

    def is_hovered(self):
        """Check if the the mouse is on top of this widget."""
        return self._hovered

    def reset_state(self):
        """Reset widget state as a hover, tooltip or hint."""
        self._as_hint = False
        self._as_hover = False

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        """Reimplemented to paint the background."""
        painter = QStylePainter(self)
        option = QStyleOptionFrame()
        option.initFrom(self)
        painter.drawPrimitive(QStyle.PE_PanelTipLabel, option)
        painter.end()

        super().paintEvent(event)

    def mousePressEvent(self, event):
        """Reimplemented to handle mouse press events."""
        if self.completion_doc:
            name = self.completion_doc.get('name', '')
            signature = self.completion_doc.get('signature', '')
            self.sig_completion_help_requested.emit(name, signature)
        elif self.show_help_on_click:
            self.sig_help_requested.emit('')
        elif self._url:
            self.sig_help_requested.emit(self._url)

        super().mousePressEvent(event)

        # Prevent to hide the widget when it's used as a completion hint and
        # users click on it
        if not self._as_hint:
            self._hide()

    def focusOutEvent(self, event):
        """Reimplemented to hide tooltip when focus goes out."""
        self._hide()

    def enterEvent(self, event):
        """Reimplemented to keep tooltip visible and change cursor shape."""
        if self.show_help_on_click:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        self._hovered = True
        self._timer_hide.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reimplemented to hide tooltip on leave."""
        # This is necessary to set the cursor correctly in enterEvent on Mac
        self.unsetCursor()

        self._hovered = False
        super().leaveEvent(event)

        # Prevent to hide the widget when it's used as a completion hint and
        # the cursor lays on top of it when browsing different completions.
        if not self._as_hint:
            self._hide()

    def hide(self):
        """
        Reimplemented to wait for a little bit before hiding the tooltip.

        This is necessary to leave time to users to hover over the tooltip if
        they want to click on it. If not, the tooltip hides too quickly because
        Qt can emit a hideEvent in the meantime.
        """
        self._timer_hide.start()


class CallTipWidget(QLabel):
    """ Shows call tips by parsing the current text of Q[Plain]TextEdit.
    """

    def __init__(self, text_edit, hide_timer_on=False, as_tooltip=False):
        """ Create a call tip manager that is attached to the specified Qt
            text edit widget.
        """
        assert isinstance(text_edit, (QTextEdit, QPlainTextEdit))
        super().__init__(text_edit, Qt.ToolTip)
        self.app = QCoreApplication.instance()
        self.as_tooltip = as_tooltip

        self.hide_timer_on = hide_timer_on
        self.tip = None
        self._hide_timer = QBasicTimer()
        self._text_edit = text_edit
        self._start_position = -1

        # Setup
        if sys.platform == 'darwin':
            # This keeps the hints below other applications
            self.setWindowFlags(Qt.SplashScreen)
        else:
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)

        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setFont(text_edit.document().defaultFont())
        self.setForegroundRole(QPalette.ToolTipText)
        self.setBackgroundRole(QPalette.ToolTipBase)
        self.setPalette(QToolTip.palette())

        self.setAlignment(Qt.AlignLeft)
        self.setIndent(1)
        self.setFrameStyle(QFrame.NoFrame)
        self.setMargin(1 + self.style().pixelMetric(
                QStyle.PM_ToolTipLabelFrameWidth, None, self))

        # Signals
        QApplication.instance().applicationStateChanged.connect(
            self._should_hide
        )

        # Style
        self.setStyleSheet(self._stylesheet)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        """ Reimplemented to hide on certain key presses and on text edit focus
            changes.
        """
        if obj == self._text_edit:
            etype = event.type()

            if etype == QEvent.KeyPress:
                key = event.key()
                cursor = self._text_edit.textCursor()
                prev_char = self._text_edit.get_character(cursor.position(),
                                                          offset=-1)
                if key in (Qt.Key_Enter, Qt.Key_Return,
                           Qt.Key_Down, Qt.Key_Up):
                    self.hide()
                elif key == Qt.Key_Escape:
                    self.hide()
                    return True
                elif prev_char == ')':
                    self.hide()

            elif etype == QEvent.FocusOut:
                self.hide()

            elif etype == QEvent.Enter:
                if (self._hide_timer.isActive() and
                  self.app.topLevelAt(QCursor.pos()) == self):
                    self._hide_timer.stop()

            elif etype == QEvent.Leave:
                self._leave_event_hide()

            elif etype == QEvent.WindowBlocked:
                self.hide()

        return super(CallTipWidget, self).eventFilter(obj, event)

    def timerEvent(self, event):
        """ Reimplemented to hide the widget when the hide timer fires.
        """
        if event.timerId() == self._hide_timer.timerId():
            self._hide_timer.stop()
            self.hide()

    def enterEvent(self, event):
        """ Reimplemented to cancel the hide timer.
        """
        super(CallTipWidget, self).enterEvent(event)
        if self.as_tooltip:
            self.hide()

        if (self._hide_timer.isActive() and
          self.app.topLevelAt(QCursor.pos()) == self):
            self._hide_timer.stop()

    def hideEvent(self, event):
        """ Reimplemented to disconnect signal handlers and event filter.
        """
        super(CallTipWidget, self).hideEvent(event)
        # This is needed for issue spyder-ide/spyder#9221,
        try:
            self._text_edit.cursorPositionChanged.disconnect(
                self._cursor_position_changed)
        except (TypeError, RuntimeError):
            pass
        else:
            self._text_edit.removeEventFilter(self)

    def leaveEvent(self, event):
        """ Reimplemented to start the hide timer.
        """
        super(CallTipWidget, self).leaveEvent(event)
        self._leave_event_hide()

    def mousePressEvent(self, event):
        super(CallTipWidget, self).mousePressEvent(event)
        self.hide()

    def paintEvent(self, event):
        """ Reimplemented to paint the background panel.
        """
        painter = QStylePainter(self)
        option = QStyleOptionFrame()
        option.initFrom(self)
        painter.drawPrimitive(QStyle.PE_PanelTipLabel, option)
        painter.end()

        super(CallTipWidget, self).paintEvent(event)

    def setFont(self, font):
        """ Reimplemented to allow use of this method as a slot.
        """
        super(CallTipWidget, self).setFont(font)

    def showEvent(self, event):
        """ Reimplemented to connect signal handlers and event filter.
        """
        super(CallTipWidget, self).showEvent(event)
        self._text_edit.cursorPositionChanged.connect(
            self._cursor_position_changed)
        self._text_edit.installEventFilter(self)

    def focusOutEvent(self, event):
        """ Reimplemented to hide it when focus goes out of the main
            window.
        """
        self.hide()

    # ---- Public API
    # -------------------------------------------------------------------------
    def show_tip(self, point, tip, wrapped_tiplines):
        """ Attempts to show the specified tip at the current cursor location.
        """
        # Don't show the widget if the main window is not focused
        if QApplication.instance().applicationState() != Qt.ApplicationActive:
            return

        # Don't attempt to show it if it's already visible and the text
        # to be displayed is the same as the one displayed before.
        if self.isVisible():
            if self.tip == tip:
                return True
            else:
                self.hide()

        # Attempt to find the cursor position at which to show the call tip.
        text_edit = self._text_edit
        cursor = text_edit.textCursor()
        search_pos = cursor.position() - 1
        self._start_position, _ = self._find_parenthesis(search_pos,
                                                         forward=False)
        if self._start_position == -1:
            return False

        if self.hide_timer_on:
            self._hide_timer.stop()
            # Logic to decide how much time to show the calltip depending
            # on the amount of text present
            if len(wrapped_tiplines) == 1:
                args = wrapped_tiplines[0].split('(')[1]
                nargs = len(args.split(','))
                if nargs == 1:
                    hide_time = 1400
                elif nargs == 2:
                    hide_time = 1600
                else:
                    hide_time = 1800
            elif len(wrapped_tiplines) == 2:
                args1 = wrapped_tiplines[1].strip()
                nargs1 = len(args1.split(','))
                if nargs1 == 1:
                    hide_time = 2500
                else:
                    hide_time = 2800
            else:
                hide_time = 3500
            self._hide_timer.start(hide_time, self)

        # Set the text and resize the widget accordingly.
        self.tip = tip
        self.setText(tip)
        self.resize(self.sizeHint())

        # Locate and show the widget. Place the tip below the current line
        # unless it would be off the window or screen. In that case, decide the
        # best location based trying to minimize the area that goes off-screen.
        cursor_rect = text_edit.cursorRect(cursor)
        screen_rect = self.screen().geometry()
        if self.app.activeWindow():
            window_rect = self.app.activeWindow().geometry()
        else:
            window_rect = screen_rect
        tip_height = self.size().height()
        tip_width = self.size().width()

        vertical = 'bottom'
        horizontal = 'Right'

        if point.y() + tip_height > window_rect.height() + window_rect.y():
            point_ = text_edit.mapToGlobal(cursor_rect.topRight())
            # If tip is still off screen, check if point is in top or bottom
            # half of screen.
            if point_.y() < tip_height:
                # If point is in upper half of screen, show tip below it.
                # otherwise above it.
                if 2 * point.y() < window_rect.height():
                    vertical = 'bottom'
                else:
                    vertical = 'top'
            else:
                vertical = 'top'

        if point.x() + tip_width > screen_rect.width() + screen_rect.x():
            point_ = text_edit.mapToGlobal(cursor_rect.topRight())
            # If tip is still off-screen, check if point is in the right or
            # left half of the screen.
            if point_.x() < tip_width:
                if 2 * point.x() < screen_rect.width():
                    horizontal = 'Right'
                else:
                    horizontal = 'Left'
            else:
                horizontal = 'Left'

        if vertical == 'top':
            point.setY(point.y() - tip_height)
        else:
            font = text_edit.font()
            text_height = QFontMetrics(font).capHeight()

            # Ubuntu Mono has a strange behavior regarding its height that we
            # need to account for. Other monospaced fonts behave as expected.
            if font.family() == 'Ubuntu Mono':
                padding = 0
            else:
                padding = 3

            # Qt sets the mouse coordinates (given by `point`) a bit above the
            # line where it's placed, i.e. not exactly where the text
            # vertically starts. So, we need to add an extra height (twice the
            # cap height plus some padding) to place the tip at the line's
            # bottom.
            point.setY(point.y() + 2 * text_height + padding)

        if horizontal == 'Left':
            point.setX(point.x() - tip_width)

        self.move(point)
        self.show()
        return True

    # ---- Private API
    # -------------------------------------------------------------------------
    def _find_parenthesis(self, position, forward=True):
        """ If 'forward' is True (resp. False), proceed forwards
            (resp. backwards) through the line that contains 'position' until an
            unmatched closing (resp. opening) parenthesis is found. Returns a
            tuple containing the position of this parenthesis (or -1 if it is
            not found) and the number commas (at depth 0) found along the way.
        """
        commas = depth = 0
        document = self._text_edit.document()
        char = str(document.characterAt(position))
        # Search until a match is found or a non-printable character is
        # encountered.
        while category(char) != 'Cc' and position > 0:
            if char == ',' and depth == 0:
                commas += 1
            elif char == ')':
                if forward and depth == 0:
                    break
                depth += 1
            elif char == '(':
                if not forward and depth == 0:
                    break
                depth -= 1
            position += 1 if forward else -1
            char = str(document.characterAt(position))
        else:
            position = -1
        return position, commas

    def _leave_event_hide(self):
        """ Hides the tooltip after some time has passed (assuming the cursor is
            not over the tooltip).
        """
        if (self.hide_timer_on and not self._hide_timer.isActive() and
            # If Enter events always came after Leave events, we wouldn't need
            # this check. But on Mac OS, it sometimes happens the other way
            # around when the tooltip is created.
            self.app.topLevelAt(QCursor.pos()) != self):
            self._hide_timer.start(800, self)

    def _cursor_position_changed(self):
        """ Updates the tip based on user cursor movement.
        """
        cursor = self._text_edit.textCursor()
        position = cursor.position()
        document = self._text_edit.document()
        char = str(document.characterAt(position - 1))
        if position <= self._start_position:
            self.hide()
        elif char == ')':
            pos, _ = self._find_parenthesis(position - 1, forward=False)
            if pos == -1:
                self.hide()

    def _should_hide(self, state):
        """
        This widget should hide itself if the application is not active.
        """
        if state != Qt.ApplicationActive:
            self.hide()

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()

        css["CallTipWidget"].setValues(
            backgroundColor=BACKGROUND_COLOR,
            border=f"1px solid {SpyderPalette.COLOR_TEXT_4}"
        )

        return css.toString()
