# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder interactive tours"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from __future__ import division

import sys
from math import ceil

# Third party imports
from qtpy.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt,
                         Signal)
from qtpy.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen,
                        QPixmap, QRegion)
from qtpy.QtWidgets import (QAction, QApplication, QComboBox, QDialog,
                            QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                            QLayout, QMainWindow, QMenu, QPushButton,
                            QSpacerItem, QToolButton, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, get_image_path
from spyder.config.gui import is_dark_interface
from spyder.py3compat import to_binary_string
from spyder.utils.qthelpers import add_actions, create_action
from spyder.utils import icon_manager as ima


if is_dark_interface():
    MAIN_TOP_COLOR = MAIN_BG_COLOR = QColor.fromRgb(25, 35, 45)
else:
    MAIN_TOP_COLOR = QColor.fromRgb(230, 230, 230)
    MAIN_BG_COLOR = QColor.fromRgb(255, 255, 255)

# FIXME: Known issues
# How to handle if an specific dockwidget does not exists/load, like ipython
# on python3.3, should that frame be removed? should it display a warning?

class SpyderWidgets(object):
    """List of supported widgets to highlight/decorate"""
    # Panes
    ipython_console = 'ipyconsole'
    editor = 'editor'
    editor_line_number_area = 'editor.get_current_editor().linenumberarea'
    editor_scroll_flag_area = 'editor.get_current_editor().scrollflagarea'
    file_explorer = 'explorer'
    help_plugin = 'help'
    variable_explorer = 'variableexplorer'
    history_log = "historylog"

    # Toolbars
    toolbars = ''
    toolbars_active = ''
    toolbar_file = ''
    toolbar_edit = ''
    toolbar_run = ''
    toolbar_debug = ''
    toolbar_main = ''

    status_bar = ''
    menu_bar = ''
    menu_file = ''
    menu_edit = ''


def get_tours(index=None):
    """
    Get the list of available tours (if index=None), or the your given by
    index
    """
    return get_tour(index)


def get_tour(index):
    """
    This function generates a list of tours.

    The index argument is used to retrieve a particular tour. If None is
    passed, it will return the full list of tours. If instead -1 is given,
    this function will return a test tour

    To add more tours a new variable needs to be created to hold the list of
    dicts and the tours variable at the bottom of this function needs to be
    updated accordingly
    """
    sw = SpyderWidgets
    qtconsole_link = "https://qtconsole.readthedocs.io/en/stable/index.html"

    # This test should serve as example of keys to use in the tour frame dics
    test = [{'title': "Welcome to Spyder introduction tour",
             'content': "<b>Spyder</b> is an interactive development \
                         environment. This tip panel supports rich text. <br>\
                         <br> it also supports image insertion to the right so\
                         far",
             'image': 'tour-spyder-logo.png'},

            {'title': "Widget display",
             'content': ("This show how a widget is displayed. The tip panel "
                         "is adjusted based on the first widget in the list"),
             'widgets': ['button1'],
             'decoration': ['button2'],
             'interact': True},

            {'title': "Widget display",
             'content': ("This show how a widget is displayed. The tip panel "
                         "is adjusted based on the first widget in the list"),
             'widgets': ['button1'],
             'decoration': ['button1'],
             'interact': True},

            {'title': "Widget display",
             'content': ("This show how a widget is displayed. The tip panel "
                         "is adjusted based on the first widget in the list"),
             'widgets': ['button1'],
             'interact': True},

            {'title': "Widget display and highlight",
             'content': "This shows how a highlighted widget looks",
             'widgets': ['button'],
             'decoration': ['button'],
             'interact': False},
            ]

    intro = [{'title': _("Welcome to the Introduction tour"),
              'content': _("<b>Spyder</b> is a powerful Interactive "
                           "Development Environment (or IDE) for the Python "
                           "programming language.<br><br>"
                           "Here we are going to guide you through its most "
                           "important features.<br><br>"
                           "Please use the arrow keys or click on the buttons "
                           "below to move along the tour."),
              'image': 'tour-spyder-logo.png'},

             {'title': _("The Editor"),
              'content': _("This is the pane where you write Python code before "
                           "evaluating it. You can get automatic suggestions "
                           "and completions while writing, by pressing the "
                           "<b>Tab</b> key next to a given text.<br><br>"
                           "The Editor comes "
                           "with a line number area (highlighted here in red), "
                           "where Spyder shows warnings and syntax errors. They "
                           "can help you to detect potential problems before "
                           "running the code.<br><br>"
                           "You can also set debug breakpoints in the line "
                           "number area, by doing a double click next to "
                           "a non-empty line."),
              'widgets': [sw.editor],
              'decoration': [sw.editor_line_number_area]},

             {'title': _("The IPython console"),
              'content': _("This is one of panes where you can run or "
                           "execute the code you wrote on the Editor. To do it "
                           "you need to press the <b>F5</b> key.<br><br>"
                           "This console comes with several "
                           "useful features that greatly improve your "
                           "programming workflow (like syntax highlighting and "
                           "inline plots). If you want to know more about them, "
                           "please follow this <a href=\"{0}\">link</a>.<br><br>"
                           "Please click on the button below to run some simple "
                           "code in this console. This will be useful to show "
                           "you other important features.").format(
                           qtconsole_link),
              'widgets': [sw.ipython_console],
              'run': ["li = list(range(100))", "d = {'a': 1, 'b': 2}"]
              },

             {'title': _("The Variable Explorer"),
              'content': _("In this pane you can view and edit the variables "
                           "generated during the execution of a program, or "
                           "those entered directly in one of Spyder "
                           "consoles.<br><br>"
                           "As you can see, the Variable Explorer is showing "
                           "the variables generated during the last step of "
                           "this tour. By doing a double-click on any "
                           "of them, a new window will be opened, where you "
                           "can inspect and modify their contents."),
              'widgets': [sw.variable_explorer],
              'interact': True},

             {'title': _("Help"),
              'content': _("This pane displays documentation of the "
                           "functions, classes, methods or modules you are "
                           "currently using in the Editor or the Consoles.<br><br>"
                           "To use it, you need to press <b>Ctrl+I</b> in "
                           "front of an object. If that object has some "
                           "documentation associated with it, it will be "
                           "displayed here."),
              'widgets': [sw.help_plugin],
              'interact': True},

             {'title': _("The File Explorer"),
              'content': _("This pane lets you navigate through the directories "
                           "and files present in your computer.<br><br>"
                           "You can also open any of these files with its "
                           "corresponding application, by doing a double "
                           "click on it.<br><br>"
                           "There is one exception to this rule: plain-text "
                           "files will always be opened in the Spyder Editor."),
              'widgets': [sw.file_explorer],
              'interact': True},

             {'title': _("The History Log"),
              'content': _("This pane records all commands introduced in "
                           "the Python and IPython consoles."),
              'widgets': [sw.history_log],
              'interact': True},
             ]

#                   ['The run toolbar',
#                       'Should be short',
#                       ['self.run_toolbar'], None],
#                   ['The debug toolbar',
#                       '',
#                       ['self.debug_toolbar'], None],
#                   ['The main toolbar',
#                       '',
#                       ['self.main_toolbar'], None],
#                   ['The editor',
#                       'Spyder has differnet bla bla bla',
#                       ['self.editor.dockwidget'], None],
#                   ['The editor',
#                       'Spyder has differnet bla bla bla',
#                       ['self.outlineexplorer.dockwidget'], None],
#
#                   ['The menu bar',
#                       'Spyder has differnet bla bla bla',
#                       ['self.menuBar()'], None],
#
#                   ['The menu bar',
#                       'Spyder has differnet bla bla bla',
#                       ['self.statusBar()'], None],
#
#
#                   ['The toolbars!',
#                       'Spyder has differnet bla bla bla',
#                       ['self.variableexplorer.dockwidget'], None],
#                   ['The toolbars MO!',
#                       'Spyder has differnet bla bla bla',
#                       ['self.extconsole.dockwidget'], None],
#                   ['The whole window?!',
#                       'Spyder has differnet bla bla bla',
#                       ['self'], None],
#                   ['Lets try something!',
#                       'Spyder has differnet bla bla bla',
#                       ['self.extconsole.dockwidget',
#                        'self.variableexplorer.dockwidget'], None]
#
#                      ]

    feat30 = [{'title': "New features in Spyder 3.0",
               'content': _("<b>Spyder</b> is an interactive development "
                            "environment based on bla"),
               'image': 'spyder.png'},

              {'title': _("Welcome to Spyder introduction tour"),
               'content': _("Spyder is an interactive development environment "
                            "based on bla"),
               'widgets': ['variableexplorer']},
              ]

    tours = [{'name': _('Introduction tour'), 'tour': intro},
             {'name': _('New features in version 3.0'), 'tour': feat30}]

    if index is None:
        return tours
    elif index == -1:
        return [test]
    else:
        return [tours[index]]


class FadingDialog(QDialog):
    """A general fade in/fade out QDialog with some builtin functions"""
    sig_key_pressed = Signal()

    def __init__(self, parent, opacity, duration, easing_curve):
        super(FadingDialog, self).__init__(parent)

        self.parent = parent
        self.opacity_min = min(opacity)
        self.opacity_max = max(opacity)
        self.duration_fadein = duration[0]
        self.duration_fadeout = duration[-1]
        self.easing_curve_in = easing_curve[0]
        self.easing_curve_out = easing_curve[-1]
        self.effect = None
        self.anim = None

        self._fade_running = False
        self._funcs_before_fade_in = []
        self._funcs_after_fade_in = []
        self._funcs_before_fade_out = []
        self._funcs_after_fade_out = []

        self.setModal(False)

    def _run(self, funcs):
        """ """
        for func in funcs:
            func()

    def _run_before_fade_in(self):
        """ """
        self._run(self._funcs_before_fade_in)

    def _run_after_fade_in(self):
        """ """
        self._run(self._funcs_after_fade_in)

    def _run_before_fade_out(self):
        """ """
        self._run(self._funcs_before_fade_out)

    def _run_after_fade_out(self):
        """ """
        self._run(self._funcs_after_fade_out)

    def _set_fade_finished(self):
        """ """
        self._fade_running = False

    def _fade_setup(self):
        """ """
        self._fade_running = True
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, to_binary_string("opacity"))

    # --- public api
    def fade_in(self, on_finished_connect):
        """ """
        self._run_before_fade_in()
        self._fade_setup()
        self.show()
        self.raise_()
        self.anim.setEasingCurve(self.easing_curve_in)
        self.anim.setStartValue(self.opacity_min)
        self.anim.setEndValue(self.opacity_max)
        self.anim.setDuration(self.duration_fadein)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_fade_finished)
        self.anim.finished.connect(self._run_after_fade_in)
        self.anim.start()

    def fade_out(self, on_finished_connect):
        """ """
        self._run_before_fade_out()
        self._fade_setup()
        self.anim.setEasingCurve(self.easing_curve_out)
        self.anim.setStartValue(self.opacity_max)
        self.anim.setEndValue(self.opacity_min)
        self.anim.setDuration(self.duration_fadeout)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_fade_finished)
        self.anim.finished.connect(self._run_after_fade_out)
        self.anim.start()

    def is_fade_running(self):
        """ """
        return self._fade_running

    def set_funcs_before_fade_in(self, funcs):
        """ """
        self._funcs_before_fade_in = funcs

    def set_funcs_after_fade_in(self, funcs):
        """ """
        self._funcs_after_fade_in = funcs

    def set_funcs_before_fade_out(self, funcs):
        """ """
        self._funcs_before_fade_out = funcs

    def set_funcs_after_fade_out(self, funcs):
        """ """
        self._funcs_after_fade_out = funcs


class FadingCanvas(FadingDialog):
    """The black semi transparent canvas that covers the application"""
    def __init__(self, parent, opacity, duration, easing_curve, color,
                 tour=None):
        """Create a black semi transparent canvas that covers the app."""
        super(FadingCanvas, self).__init__(parent, opacity, duration,
                                           easing_curve)
        self.parent = parent
        self.tour = tour

        self.color = color              # Canvas color
        self.color_decoration = Qt.red  # Decoration color
        self.stroke_decoration = 2      # width in pixels for decoration

        self.region_mask = None
        self.region_subtract = None
        self.region_decoration = None

        self.widgets = None             # The widget to uncover
        self.decoration = None          # The widget to draw decoration
        self.interaction_on = False

        self.path_current = None
        self.path_subtract = None
        self.path_full = None
        self.path_decoration = None

        # widget setup
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setModal(False)
        self.setFocusPolicy(Qt.NoFocus)

        self.set_funcs_before_fade_in([self.update_canvas])
        self.set_funcs_after_fade_out([lambda: self.update_widgets(None),
                                       lambda: self.update_decoration(None)])

    def set_interaction(self, value):
        """ """
        self.interaction_on = value

    def update_canvas(self):
        """ """
        w, h = self.parent.size().width(), self.parent.size().height()

        self.path_full = QPainterPath()
        self.path_subtract = QPainterPath()
        self.path_decoration = QPainterPath()
        self.region_mask = QRegion(0, 0, w, h)

        self.path_full.addRect(0, 0, w, h)

        # Add the path
        if self.widgets is not None:
            for widget in self.widgets:
                temp_path = QPainterPath()
                # if widget is not found... find more general way to handle
                if widget is not None:
                    widget.raise_()
                    widget.show()
                    geo = widget.frameGeometry()
                    width, height = geo.width(), geo.height()
                    point = widget.mapTo(self.parent, QPoint(0, 0))
                    x, y = point.x(), point.y()

                    temp_path.addRect(QRectF(x, y, width, height))

                    temp_region = QRegion(x, y, width, height)

                if self.interaction_on:
                    self.region_mask = self.region_mask.subtracted(temp_region)
                self.path_subtract = self.path_subtract.united(temp_path)

            self.path_current = self.path_full.subtracted(self.path_subtract)
        else:
            self.path_current = self.path_full

        if self.decoration is not None:
            for widget in self.decoration:
                temp_path = QPainterPath()
                widget.raise_()
                widget.show()
                geo = widget.frameGeometry()
                width, height = geo.width(), geo.height()
                point = widget.mapTo(self.parent, QPoint(0, 0))
                x, y = point.x(), point.y()
                temp_path.addRect(QRectF(x, y, width, height))

                temp_region_1 = QRegion(x-1, y-1, width+2, height+2)
                temp_region_2 = QRegion(x+1, y+1, width-2, height-2)
                temp_region = temp_region_1.subtracted(temp_region_2)

                if self.interaction_on:
                    self.region_mask = self.region_mask.united(temp_region)

                self.path_decoration = self.path_decoration.united(temp_path)
        else:
            self.path_decoration.addRect(0, 0, 0, 0)

        # Add a decoration stroke around widget
        self.setMask(self.region_mask)
        self.update()
        self.repaint()

    def update_widgets(self, widgets):
        """ """
        self.widgets = widgets

    def update_decoration(self, widgets):
        """ """
        self.decoration = widgets

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Decoration
        painter.fillPath(self.path_current, QBrush(self.color))
        painter.strokePath(self.path_decoration, QPen(self.color_decoration,
                                                      self.stroke_decoration))
#        decoration_fill = QColor(self.color_decoration)
#        decoration_fill.setAlphaF(0.25)
#        painter.fillPath(self.path_decoration, decoration_fill)

    def reject(self):
        """Override Qt method"""
        if not self.is_fade_running():
            key = Qt.Key_Escape
            self.key_pressed = key
            self.sig_key_pressed.emit()

    def mousePressEvent(self, event):
        """Override Qt method"""
        pass

    def focusInEvent(self, event):
        """Override Qt method."""
        # To be used so tips do not appear outside spyder
        if self.hasFocus():
            self.tour.gain_focus()

    def focusOutEvent(self, event):
        """Override Qt method."""
        # To be used so tips do not appear outside spyder
        if self.tour.step_current != 0:
            self.tour.lost_focus()


class FadingTipBox(FadingDialog):
    """ """
    def __init__(self, parent, opacity, duration, easing_curve, tour=None,
                 color_top=None, color_back=None, combobox_background=None):
        super(FadingTipBox, self).__init__(parent, opacity, duration,
                                           easing_curve)
        self.holder = self.anim  # needed for qt to work
        self.parent = parent
        self.tour = tour

        self.frames = None
        self.offset_shadow = 0
        self.fixed_width = 300

        self.key_pressed = None

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint)
        self.setModal(False)

        # Widgets
        def toolbutton(icon):
            bt = QToolButton()
            bt.setAutoRaise(True)
            bt.setIcon(icon)
            return bt

        self.button_close = toolbutton(ima.icon("tour.close"))
        self.button_home = toolbutton(ima.icon("tour.home"))
        self.button_previous = toolbutton(ima.icon("tour.previous"))
        self.button_end = toolbutton(ima.icon("tour.end"))
        self.button_next = toolbutton(ima.icon("tour.next"))
        self.button_run = QPushButton(_('Run code'))
        self.button_disable = None
        self.button_current = QToolButton()
        self.label_image = QLabel()

        self.label_title = QLabel()
        self.combo_title = QComboBox()
        self.label_current = QLabel()
        self.label_content = QLabel()

        self.label_content.setMinimumWidth(self.fixed_width)
        self.label_content.setMaximumWidth(self.fixed_width)

        self.label_current.setAlignment(Qt.AlignCenter)

        self.label_content.setWordWrap(True)

        self.widgets = [self.label_content, self.label_title,
                        self.label_current, self.combo_title,
                        self.button_close, self.button_run, self.button_next,
                        self.button_previous, self.button_end,
                        self.button_home, self.button_current]

        arrow = get_image_path('hide.png')

        self.color_top = color_top
        self.color_back = color_back
        self.combobox_background = combobox_background
        self.stylesheet = '''QComboBox {{
                             padding-left: 5px;
                             background-color: {}
                             border-width: 0px;
                             border-radius: 0px;
                             min-height:20px;
                             max-height:20px;
                             }}

                             QComboBox::drop-down  {{
                             subcontrol-origin: padding;
                             subcontrol-position: top left;
                             border-width: 0px;
                             }}

                             QComboBox::down-arrow {{
                             image: url({});
                             }}

                             '''.format(self.combobox_background.name(), arrow)
        # Windows fix, slashes should be always in unix-style
        self.stylesheet = self.stylesheet.replace('\\', '/')

        self.setFocusPolicy(Qt.StrongFocus)
        for widget in self.widgets:
            widget.setFocusPolicy(Qt.NoFocus)
            widget.setStyleSheet(self.stylesheet)

        layout_top = QHBoxLayout()
        layout_top.addWidget(self.combo_title)
        layout_top.addStretch()
        layout_top.addWidget(self.button_close)
        layout_top.addSpacerItem(QSpacerItem(self.offset_shadow,
                                             self.offset_shadow))

        layout_content = QHBoxLayout()
        layout_content.addWidget(self.label_content)
        layout_content.addWidget(self.label_image)
        layout_content.addSpacerItem(QSpacerItem(5, 5))

        layout_run = QHBoxLayout()
        layout_run.addStretch()
        layout_run.addWidget(self.button_run)
        layout_run.addStretch()
        layout_run.addSpacerItem(QSpacerItem(self.offset_shadow,
                                             self.offset_shadow))

        layout_navigation = QHBoxLayout()
        layout_navigation.addWidget(self.button_home)
        layout_navigation.addWidget(self.button_previous)
        layout_navigation.addStretch()
        layout_navigation.addWidget(self.label_current)
        layout_navigation.addStretch()
        layout_navigation.addWidget(self.button_next)
        layout_navigation.addWidget(self.button_end)
        layout_navigation.addSpacerItem(QSpacerItem(self.offset_shadow,
                                                    self.offset_shadow))

        layout = QVBoxLayout()
        layout.addLayout(layout_top)
        layout.addStretch()
        layout.addSpacerItem(QSpacerItem(15, 15))
        layout.addLayout(layout_content)
        layout.addLayout(layout_run)
        layout.addStretch()
        layout.addSpacerItem(QSpacerItem(15, 15))
        layout.addLayout(layout_navigation)
        layout.addSpacerItem(QSpacerItem(self.offset_shadow,
                                         self.offset_shadow))

        layout.setSizeConstraint(QLayout.SetFixedSize)

        self.setLayout(layout)

        self.set_funcs_before_fade_in([self._disable_widgets])
        self.set_funcs_after_fade_in([self._enable_widgets, self.setFocus])
        self.set_funcs_before_fade_out([self._disable_widgets])

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # signals and slots
        # These are defined every time by the AnimatedTour Class

    def _disable_widgets(self):
        """ """
        for widget in self.widgets:
            widget.setDisabled(True)

    def _enable_widgets(self):
        """ """
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint)
        for widget in self.widgets:
            widget.setDisabled(False)

        if self.button_disable == 'previous':
            self.button_previous.setDisabled(True)
            self.button_home.setDisabled(True)
        elif self.button_disable == 'next':
            self.button_next.setDisabled(True)
            self.button_end.setDisabled(True)

    def set_data(self, title, content, current, image, run, frames=None,
                 step=None):
        """ """
        self.label_title.setText(title)
        self.combo_title.clear()
        self.combo_title.addItems(frames)
        self.combo_title.setCurrentIndex(step)
#        min_content_len = max([len(f) for f in frames])
#        self.combo_title.setMinimumContentsLength(min_content_len)

        # Fix and try to see how it looks with a combo box
        self.label_current.setText(current)
        self.button_current.setText(current)
        self.label_content.setText(content)
        self.image = image

        if image is None:
            self.label_image.setFixedHeight(1)
            self.label_image.setFixedWidth(1)
        else:
            extension = image.split('.')[-1]
            self.image = QPixmap(get_image_path(image), extension)
            self.label_image.setPixmap(self.image)
            self.label_image.setFixedSize(self.image.size())

        if run is None:
            self.button_run.setVisible(False)
        else:
            self.button_run.setDisabled(False)
            self.button_run.setVisible(True)

        # Refresh layout
        self.layout().activate()

    def set_pos(self, x, y):
        """ """
        self.x = ceil(x)
        self.y = ceil(y)
        self.move(QPoint(self.x, self.y))

    def build_paths(self):
        """ """
        geo = self.geometry()
        radius = 0
        shadow = self.offset_shadow
        x0, y0 = geo.x(), geo.y()
        width, height = geo.width() - shadow, geo.height() - shadow

        left, top = 0, 0
        right, bottom = width, height

        self.round_rect_path = QPainterPath()
        self.round_rect_path.moveTo(right, top + radius)
        self.round_rect_path.arcTo(right-radius, top, radius, radius, 0.0,
                                   90.0)
        self.round_rect_path.lineTo(left+radius, top)
        self.round_rect_path.arcTo(left, top, radius, radius, 90.0, 90.0)
        self.round_rect_path.lineTo(left, bottom-radius)
        self.round_rect_path.arcTo(left, bottom-radius, radius, radius, 180.0,
                                   90.0)
        self.round_rect_path.lineTo(right-radius, bottom)
        self.round_rect_path.arcTo(right-radius, bottom-radius, radius, radius,
                                   270.0, 90.0)
        self.round_rect_path.closeSubpath()

        # Top path
        header = 36
        offset = 2
        left, top = offset, offset
        right = width - (offset)
        self.top_rect_path = QPainterPath()
        self.top_rect_path.lineTo(right, top + radius)
        self.top_rect_path.moveTo(right, top + radius)
        self.top_rect_path.arcTo(right-radius, top, radius, radius, 0.0, 90.0)
        self.top_rect_path.lineTo(left+radius, top)
        self.top_rect_path.arcTo(left, top, radius, radius, 90.0, 90.0)
        self.top_rect_path.lineTo(left, top + header)
        self.top_rect_path.lineTo(right, top + header)

    def paintEvent(self, event):
        """ """
        self.build_paths()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillPath(self.round_rect_path, self.color_back)
        painter.fillPath(self.top_rect_path, self.color_top)
        painter.strokePath(self.round_rect_path, QPen(Qt.gray, 1))

        # TODO: Build the pointing arrow?

    def keyReleaseEvent(self, event):
        """ """
        key = event.key()
        self.key_pressed = key

        keys = [Qt.Key_Right, Qt.Key_Left, Qt.Key_Down, Qt.Key_Up,
                Qt.Key_Escape, Qt.Key_PageUp, Qt.Key_PageDown,
                Qt.Key_Home, Qt.Key_End, Qt.Key_Menu]

        if key in keys:
            if not self.is_fade_running():
                self.sig_key_pressed.emit()

    def mousePressEvent(self, event):
        """override Qt method"""
        # Raise the main application window on click
        self.parent.raise_()
        self.raise_()

        if event.button() == Qt.RightButton:
            pass
#            clicked_widget = self.childAt(event.x(), event.y())
#            if clicked_widget == self.label_current:
#            self.context_menu_requested(event)

    def focusOutEvent(self, event):
        """Override Qt method."""
        # To be used so tips do not appear outside spyder
        self.tour.lost_focus()

    def context_menu_requested(self, event):
        """ """
        pos = QPoint(event.x(), event.y())
        menu = QMenu(self)

        actions = []
        action_title = create_action(self, _('Go to step: '), icon=QIcon())
        action_title.setDisabled(True)
        actions.append(action_title)
#        actions.append(create_action(self, _(': '), icon=QIcon()))

        add_actions(menu, actions)

        menu.popup(self.mapToGlobal(pos))

    def reject(self):
        """Qt method to handle escape key event"""
        if not self.is_fade_running():
            key = Qt.Key_Escape
            self.key_pressed = key
            self.sig_key_pressed.emit()


class AnimatedTour(QWidget):
    """ """

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.parent = parent

        # Variables to adjust
        self.duration_canvas = [666, 666]
        self.duration_tips = [333, 333]
        self.opacity_canvas = [0.0, 0.7]
        self.opacity_tips = [0.0, 1.0]
        self.color = Qt.black
        self.easing_curve = [QEasingCurve.Linear]

        self.current_step = 0
        self.step_current = 0
        self.steps = 0
        self.canvas = None
        self.tips = None
        self.frames = None
        self.spy_window = None

        self.widgets = None
        self.dockwidgets = None
        self.decoration = None
        self.run = None

        self.is_tour_set = False
        self.is_running = False

        # Widgets
        self.canvas = FadingCanvas(self.parent, self.opacity_canvas,
                                   self.duration_canvas, self.easing_curve,
                                   self.color, tour=self)
        self.tips = FadingTipBox(self.parent, self.opacity_tips,
                                 self.duration_tips, self.easing_curve,
                                 tour=self, color_top=MAIN_TOP_COLOR,
                                 color_back=MAIN_BG_COLOR,
                                 combobox_background=MAIN_TOP_COLOR)

        # Widgets setup
        # Needed to fix spyder-ide/spyder#2204.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Signals and slots
        self.tips.button_next.clicked.connect(self.next_step)
        self.tips.button_previous.clicked.connect(self.previous_step)
        self.tips.button_close.clicked.connect(self.close_tour)
        self.tips.button_run.clicked.connect(self.run_code)
        self.tips.button_home.clicked.connect(self.first_step)
        self.tips.button_end.clicked.connect(self.last_step)
        self.tips.button_run.clicked.connect(
            lambda: self.tips.button_run.setDisabled(True))
        self.tips.combo_title.currentIndexChanged.connect(self.go_to_step)

        # Main window move or resize
        self.parent.sig_resized.connect(self._resized)
        self.parent.sig_moved.connect(self._moved)

        # To capture the arrow keys that allow moving the tour
        self.tips.sig_key_pressed.connect(self._key_pressed)

        # To control the focus of tour
        self.setting_data = False
        self.hidden = False

    def _resized(self, event):
        """ """
        if self.is_running:
            size = event.size()
            self.canvas.setFixedSize(size)
            self.canvas.update_canvas()

            if self.is_tour_set:
                self._set_data()

    def _moved(self, event):
        """ """
        if self.is_running:
            pos = event.pos()
            self.canvas.move(QPoint(pos.x(), pos.y()))

            if self.is_tour_set:
                self._set_data()

    def _close_canvas(self):
        """ """
        self.tips.hide()
        self.canvas.fade_out(self.canvas.hide)

    def _clear_canvas(self):
        """ """
        # TODO: Add option to also make it white... might be usefull?
        # Make canvas black before transitions
        self.canvas.update_widgets(None)
        self.canvas.update_decoration(None)
        self.canvas.update_canvas()

    def _move_step(self):
        """ """
        self._set_data()

        # Show/raise the widget so it is located first!
        widgets = self.dockwidgets
        if widgets is not None:
            widget = widgets[0]
            if widget is not None:
                widget.show()
                widget.raise_()

        self._locate_tip_box()

        # Change in canvas only after fadein finishes, for visual aesthetics
        self.tips.fade_in(self.canvas.update_canvas)
        self.tips.raise_()

    def _set_modal(self, value, widgets):
        """ """
        platform = sys.platform.lower()

        if 'linux' in platform:
            pass
        elif 'win' in platform:
            for widget in widgets:
                widget.setModal(value)
                widget.hide()
                widget.show()
        elif 'darwin' in platform:
            pass
        else:
            pass

    def _process_widgets(self, names, spy_window):
        """ """
        widgets = []
        dockwidgets = []

        for name in names:
            base = name.split('.')[0]
            temp = getattr(spy_window, base)

            # Check if it is the current editor
            if 'get_current_editor()' in name:
                temp = temp.get_current_editor()
                temp = getattr(temp, name.split('.')[-1])

            widgets.append(temp)

            # Check if it is a dockwidget and make the widget a dockwidget
            # If not return the same widget
            temp = getattr(temp, 'dockwidget', temp)
            dockwidgets.append(temp)

        return widgets, dockwidgets

    def _set_data(self):
        """Set data that is displayed in each step of the tour."""
        self.setting_data = True
        step, steps, frames = self.step_current, self.steps, self.frames
        current = '{0}/{1}'.format(step + 1, steps)
        frame = frames[step]

        combobox_frames = [u"{0}. {1}".format(i+1, f['title'])
                           for i, f in enumerate(frames)]

        title, content, image = '', '', None
        widgets, dockwidgets, decoration = None, None, None
        run = None

        # Check if entry exists in dic and act accordingly
        if 'title' in frame:
            title = frame['title']

        if 'content' in frame:
            content = frame['content']

        if 'widgets' in frame:
            widget_names = frames[step]['widgets']
            # Get the widgets based on their name
            widgets, dockwidgets = self._process_widgets(widget_names,
                                                         self.spy_window)
        self.widgets = widgets
        self.dockwidgets = dockwidgets

        if 'decoration' in frame:
            widget_names = frames[step]['decoration']
            deco, decoration = self._process_widgets(widget_names,
                                                     self.spy_window)
            self.decoration = decoration

        if 'image' in frame:
            image = frames[step]['image']

        if 'interact' in frame:
            self.canvas.set_interaction(frame['interact'])
            if frame['interact']:
                self._set_modal(False, [self.tips])
            else:
                self._set_modal(True, [self.tips])
        else:
            self.canvas.set_interaction(False)
            self._set_modal(True, [self.tips])

        if 'run' in frame:
            # Asume that the frist widget is the console
            run = frame['run']
            self.run = run

        self.tips.set_data(title, content, current, image, run,
                           frames=combobox_frames, step=step)
        self._check_buttons()

        # Make canvas black when starting a new place of decoration
        self.canvas.update_widgets(dockwidgets)
        self.canvas.update_decoration(decoration)
        self.setting_data = False

    def _locate_tip_box(self):
        """ """
        dockwidgets = self.dockwidgets

        # Store the dimensions of the main window
        geo = self.parent.frameGeometry()
        x, y, width, height = geo.x(), geo.y(), geo.width(), geo.height()
        self.width_main = width
        self.height_main = height
        self.x_main = x
        self.y_main = y

        delta = 20

        # Here is the tricky part to define the best position for the
        # tip widget
        if dockwidgets is not None:
            if dockwidgets[0] is not None:
                geo = dockwidgets[0].geometry()
                x, y, width, height = geo.x(), geo.y(), geo.width(), geo.height()

                point = dockwidgets[0].mapToGlobal(QPoint(0, 0))
                x_glob, y_glob = point.x(), point.y()

                # Check if is too tall and put to the side
                y_fac = (height / self.height_main) * 100

                if y_fac > 60:  # FIXME:
                    if x < self.tips.width():
                        x = x_glob + width + delta
                        y = y_glob + height/2 - self.tips.height()/2
                    else:
                        x = x_glob - self.tips.width() - delta
                        y = y_glob + height/2 - self.tips.height()/2
                else:
                    if y < self.tips.height():
                        x = x_glob + width/2 - self.tips.width()/2
                        y = y_glob + height + delta
                    else:
                        x = x_glob + width/2 - self.tips.width()/2
                        y = y_glob - delta - self.tips.height()
        else:
            # Center on parent
            x = self.x_main + self.width_main/2 - self.tips.width()/2
            y = self.y_main + self.height_main/2 - self.tips.height()/2

        self.tips.set_pos(x, y)

    def _check_buttons(self):
        """ """
        step, steps = self.step_current, self.steps
        self.tips.button_disable = None

        if step == 0:
            self.tips.button_disable = 'previous'

        if step == steps - 1:
            self.tips.button_disable = 'next'

    def _key_pressed(self):
        """ """
        key = self.tips.key_pressed

        if ((key == Qt.Key_Right or key == Qt.Key_Down or
             key == Qt.Key_PageDown) and self.step_current != self.steps - 1):
            self.next_step()
        elif ((key == Qt.Key_Left or key == Qt.Key_Up or
               key == Qt.Key_PageUp) and self.step_current != 0):
            self.previous_step()
        elif key == Qt.Key_Escape:
            self.close_tour()
        elif key == Qt.Key_Home and self.step_current != 0:
            self.first_step()
        elif key == Qt.Key_End and self.step_current != self.steps - 1:
            self.last_step()
        elif key == Qt.Key_Menu:
            pos = self.tips.label_current.pos()
            self.tips.context_menu_requested(pos)

    def _hiding(self):
        self.hidden = True
        self.tips.hide()

    # --- public api
    def run_code(self):
        """ """
        codelines = self.run
        console = self.widgets[0]
        for codeline in codelines:
            console.execute_code(codeline)

    def set_tour(self, index, frames, spy_window):
        """ """
        self.spy_window = spy_window
        self.active_tour_index = index
        self.last_frame_active = frames['last']
        self.frames = frames['tour']
        self.steps = len(self.frames)

        self.is_tour_set = True

    def start_tour(self):
        """ """
        geo = self.parent.geometry()
        x, y, width, height = geo.x(), geo.y(), geo.width(), geo.height()
#        self.parent_x = x
#        self.parent_y = y
#        self.parent_w = width
#        self.parent_h = height

        # FIXME: reset step to last used value
        # Reset step to begining
        self.step_current = self.last_frame_active

        # Adjust the canvas size to match the main window size
        self.canvas.setFixedSize(width, height)
        self.canvas.move(QPoint(x, y))
        self.canvas.fade_in(self._move_step)
        self._clear_canvas()

        self.is_running = True

    def close_tour(self):
        """ """
        self.tips.fade_out(self._close_canvas)
        self.canvas.set_interaction(False)
        self._set_modal(True, [self.tips])
        self.canvas.hide()

        try:
            # set the last played frame by updating the available tours in
            # parent. This info will be lost on restart.
            self.parent.tours_available[self.active_tour_index]['last'] =\
                self.step_current
        except:
            pass

        self.is_running = False

    def hide_tips(self):
        """Hide tips dialog when the main window loses focus."""
        self._clear_canvas()
        self.tips.fade_out(self._hiding)

    def unhide_tips(self):
        """Unhide tips dialog when the main window loses focus."""
        self._clear_canvas()
        self._move_step()
        self.hidden = False

    def next_step(self):
        """ """
        self._clear_canvas()
        self.step_current += 1
        self.tips.fade_out(self._move_step)

    def previous_step(self):
        """ """
        self._clear_canvas()
        self.step_current -= 1
        self.tips.fade_out(self._move_step)

    def go_to_step(self, number, id_=None):
        """ """
        self._clear_canvas()
        self.step_current = number
        self.tips.fade_out(self._move_step)

    def last_step(self):
        """ """
        self.go_to_step(self.steps - 1)

    def first_step(self):
        """ """
        self.go_to_step(0)

    def lost_focus(self):
        """Confirm if the tour loses focus and hides the tips."""
        if (self.is_running and not self.any_has_focus() and
            not self.setting_data and not self.hidden):
            self.hide_tips()

    def gain_focus(self):
        """Confirm if the tour regains focus and unhides the tips."""
        if (self.is_running and self.any_has_focus() and
            not self.setting_data and self.hidden):
            self.unhide_tips()

    def any_has_focus(self):
        """Returns if tour or any of its components has focus."""
        f = (self.hasFocus() or self.parent.hasFocus() or
             self.tips.hasFocus() or self.canvas.hasFocus())
        return f

# ----------------------------------------------------------------------------
# Used for testing the functionality


class TourTestWindow(QMainWindow):
    """ """
    sig_resized = Signal("QResizeEvent")
    sig_moved = Signal("QMoveEvent")

    def __init__(self):
        super(TourTestWindow, self).__init__()
        self.setGeometry(300, 100, 400, 600)
        self.setWindowTitle('Exploring QMainWindow')

        self.exit = QAction('Exit', self)
        self.exit.setStatusTip('Exit program')

        # create the menu bar
        menubar = self.menuBar()
        file_ = menubar.addMenu('&File')
        file_.addAction(self.exit)

        # create the status bar
        self.statusBar()

        # QWidget or its instance needed for box layout
        self.widget = QWidget(self)

        self.button = QPushButton('test')
        self.button1 = QPushButton('1')
        self.button2 = QPushButton('2')

        effect = QGraphicsOpacityEffect(self.button2)
        self.button2.setGraphicsEffect(effect)
        self.anim = QPropertyAnimation(effect, to_binary_string("opacity"))
        self.anim.setStartValue(0.01)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(500)

        lay = QVBoxLayout()
        lay.addWidget(self.button)
        lay.addStretch()
        lay.addWidget(self.button1)
        lay.addWidget(self.button2)

        self.widget.setLayout(lay)

        self.setCentralWidget(self.widget)
        self.button.clicked.connect(self.action1)
        self.button1.clicked.connect(self.action2)

        self.tour = AnimatedTour(self)

    def action1(self):
        """ """
        frames = get_tour('test')
        index = 0
        dic = {'last': 0, 'tour': frames}
        self.tour.set_tour(index, dic, self)
        self.tour.start_tour()

    def action2(self):
        """ """
        self.anim.start()

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.resizeEvent(self, event)
        self.sig_resized.emit(event)

    def moveEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.moveEvent(self, event)
        self.sig_moved.emit(event)


def test():
    """ """
    app = QApplication([])
    win = TourTestWindow()
    win.show()
    app.exec_()


if __name__ == '__main__':
    test()
