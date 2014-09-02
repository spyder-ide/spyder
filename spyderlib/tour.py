# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Spyder tours"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import division

import os.path as osp

from spyderlib.qt import is_pyqt46
from spyderlib.qt.QtGui import (QColor, QMenu, QApplication, QSplitter, QFont,
                                QTextEdit, QTextFormat, QPainter, QTextCursor,
                                QBrush, 
                                QPixmap, QLabel,
                                QWidget, QVBoxLayout,
                                QHBoxLayout, QDialog, QIntValidator,
                                QMainWindow,
                                QAction, QPushButton, QGraphicsDropShadowEffect,
                                QPainterPath, QSpacerItem, QPen, QMessageBox,
                                QGraphicsOpacityEffect,
                                QMouseEvent, QRegion)
from spyderlib.qt.QtCore import (Qt, SIGNAL, QTimer, QRect, QRegExp, QSize,
                                 SLOT, Slot, QPointF, QPoint, QRectF,
                                 QTimeLine, QEvent, QPropertyAnimation,
                                 QEasingCurve, QEvent)

#%% This line is for cell execution testing
# Local import
#TODO: Try to separate this module from spyderlib to create a self
#      consistent editor module (Qt source code and shell widgets library)
from spyderlib.baseconfig import get_conf_path, _, DEBUG, get_image_path
from spyderlib.config import CONF
from spyderlib.guiconfig import get_font, create_shortcut
from spyderlib.utils.qthelpers import (add_actions, create_action, keybinding,
                                       mimedata2url, get_icon)
from spyderlib.utils.dochelpers import getobj
from spyderlib.utils import encoding, sourcecode


# FIXME: ISSUES:
# On Linux the Tip panel after transitions (although appears on top) needs to
# clicked to get the focus back... seems to be an issue of Qt and the window
# Manager in Linux.

def get_tours():
    """ """
    return get_tour(None)


def get_tour(index):
    """For now this fucntion stores and retrieves the tours.

    To add more tours a new variable needs to be created to hold the list of
    dics and the tours variable at the bottom of this function needs to be
    updated accordingly"""

    # List of supported widgets to highlight/decorate
    object_explorer = 'objectexplorer'
    variable_explorer = 'variableexplorer'
    file_explorer = 'filexplorer'
    editor = 'editor'
    internal_console = 'console'
    console = 'extconsole'
    ipython_console = 'ipyconsole'
    line_number_area = 'editor.get_current_editor().linenumberarea'
    scroll_flag_area = 'editor.get_current_editor().scrollflagarea'
    toolbars = ''
    active_toolbars = ''
    file_toolbar = ''
    edit_toolbar = ''
    run_toolbar = ''
    debug_toolbar = ''
    main_toolbar = ''
    

    status_bar = ''
    menu_bar = ''
    file_menu = ''
    edit_menu = ''
        

    # This test should serve as example of keys to use in the tour frame dics
    test = [{'title': "Welcome to Spyder introduction tour",
             'content': "<b>Spyder</b> is an interactive development \
                         environment. This tip panel supports rich text. <br>\
                         <br> it also supports image insertion to the right so\
                         far",
             'image': 'spyder.png'},

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
             'decoration': ['button1', 'button2'],
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

    intro = [{'title': _("Welcome to Spyder introduction tour"),
              'content': _("<b>Spyder</b> is a powerful interactive "
                           "development environment for the Python language. "
                           "<br><br>Use the arrow keys or the mouse to move "
                           "into the tour."),
              'image' : 'spyder.png'},

             {'title': _("The Editor"),
              'content': _("A powerful editor is a central piece of any good IDE."
                           "<br><br> No interaction example." ),
              'widgets': [editor]},

             {'title': _("The Editor"),
              'content': _("Decoration here is used to highlight the "
                           "<b>Line Number Area</b> "
                           "<br><br> No interaction example."),
              'widgets': [line_number_area, editor],
              'decoration': [line_number_area]},

             {'title': _("The IPython console"),
              'content': _("Now lets try to run some code to show the nice things "
                           "in <b>Spyder</b>.<br><br>"
                           "Click when ready and pay close attention to the "
                           "variable explorer"),
              'widgets': [ipython_console, variable_explorer],
              'run': ['a = 2', 'b = 4']
              },

             {'title': _("The IPython console"),
              'content': _("Now lets interact with the <b>IPython Console</b>."
                           "<br><br><i>Decoration</i> included also."),
              'widgets': [ipython_console, variable_explorer],
              'decoration': [variable_explorer],
              'interact': True}
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

    feat24 = [{'title': "New features in Spyder 2.4",
             'content': "<b>Spyder</b> is an interactive development environment \
                         based on bla",
             'image' : 'spyder.png'},

            {'title': "Welcome to Spyder introduction tour",
             'content': "Spyder is an interactive development environment \
                         based on bla",
             'widgets': ['variableexplorer']},
            ]

    tours = [{'name': _('Introduction tour'), 'tour': intro},
             {'name': _('New features in version 2.4'), 'tour': feat24}]

    if index is None:
        return tours
    elif index == 'test':
        return test
    else:
        return tours[index]['tour']


class FadingDialog(QDialog):
    """A general fade in/fade out QDialog with some builtin functions"""

    def __init__(self, parent, opacitiy_min, opacity_max, duration,
                 easing_curve):
        QDialog.__init__(self, parent)
        
        self.parent = parent
        self.opacity_min = opacitiy_min
        self.opacity_max = opacity_max
        self.duration = duration
        self.easing_curve = QEasingCurve.Linear
        self.effect = None
        self.anim = None
        self.fade_running = False
        self.funcs_before_fade_in = []
        self.funcs_after_fade_in = []
        self.funcs_before_fade_out = []
        self.funcs_after_fade_out = []
        self.setModal(False)

    def _set_fade_finished(self):
        """ """
        self.fade_running = False

    def _fade_setup(self):
        """ """
        self.fade_running = True
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, "opacity")
        self.anim.setEasingCurve(self.easing_curve)

    def _run_before_fade_in(self):
        """ """
        funcs = self.funcs_before_fade_in
        for func in funcs:
            func()

    def _run_after_fade_in(self):
        """ """
        funcs = self.funcs_after_fade_in
        for func in funcs:
            func()

    def _run_before_fade_out(self):
        """ """
        funcs = self.funcs_before_fade_out
        for func in funcs:
            func()

    def _run_after_fade_out(self):
        """ """
        funcs = self.funcs_after_fade_out
        for func in funcs:
            func()

    def set_funcs_before_fade_in(self, funcs):
        """ """
        self.funcs_before_fade_in = funcs

    def set_funcs_after_fade_in(self, funcs):
        """ """
        self.funcs_after_fade_in = funcs

    def set_funcs_before_fade_out(self, funcs):
        """ """
        self.funcs_before_fade_out = funcs

    def set_funcs_after_fade_out(self, funcs):
        """ """
        self.funcs_after_fade_out = funcs

    def fade_in(self, on_finished_connect):
        """ """
        self._run_before_fade_in()
        self._fade_setup()
        self.show()
        self.raise_()
        self.anim.setStartValue(self.opacity_min)
        self.anim.setEndValue(self.opacity_max)
        self.anim.setDuration(self.duration)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_fade_finished)
        self.anim.finished.connect(self._run_after_fade_in)
        self.anim.start()

    def fade_out(self, on_finished_connect):
        """ """
        self._run_before_fade_out()
        self._fade_setup()
        self.anim.setStartValue(self.opacity_max)
        self.anim.setEndValue(self.opacity_min)
        self.anim.setDuration(self.duration)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_fade_finished)
        self.anim.finished.connect(self._run_after_fade_out)
        self.anim.start()

    def is_fade_running(self):
        return self.fade_running


class FadingCanvas(FadingDialog):
    """The black semi transparent canvas that covers the application"""
    def __init__(self, parent, opacity_min, opacity_max, duration,
                 easing_curve, color):
        FadingDialog.__init__(self, parent, opacity_min, opacity_max,
                              duration, easing_curve)
        self.parent = parent
        self.opacity_min = opacity_min
        self.opacity_max = opacity_max
        self.duration = duration
        self.easing_curve = easing_curve
        self.color = color
        self.color_decoration = Qt.red
        self.stroke_decoration = 2
        self.region_mask = None
        self.region_subtract = None
        self.region_decoration = None

        self.widgets = None    # The widgets to uncover
        self.decoration = None    # The widgets to draw decoration
        self.interaction_on = False

        self.path_current = None
        self.path_subtract = None
        self.path_full = None
        self.path_decoration = None

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
        # FIX THIS!!!!  First add all widgets in one. and THEN substract
        if self.widgets is not None:
            for widget in self.widgets:
                temp_path = QPainterPath()
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
        # TODO:

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
            self.emit(SIGNAL("keyPressed"))

    def mousePressEvent(self, event):
        """Override Qt method"""
        tips = self.parent.tour.tips
        tips.raise_()
        tips.activateWindow()


class FadingTipDialog(FadingDialog):
    """ """
    def __init__(self, parent, opacity_min, opacity_max, duration,
                 easing_curve):
        FadingDialog.__init__(self, parent, opacity_min, opacity_max,
                              duration, easing_curve)
        self.holder = self.anim
        self.parent = parent
        self.opacity_min = opacity_min
        self.opacity_max = opacity_max
        self.duration = duration
        self.easing_curve = easing_curve

        self.color_top = QColor.fromRgb(230, 230, 230)
        self.color_back = QColor.fromRgb(255, 255, 255)
        self.offset_shadow = 6
        self.fixed_width = 300

        self.key_pressed = None

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(self.offset_shadow/2)
        effect.setOffset(self.offset_shadow/2, self.offset_shadow/2)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint)
        self.setModal(False)

        # Widgets
        self.button_next = QPushButton(">>")
        self.button_close = QPushButton("X")
        self.button_previous = QPushButton("<<")
        self.button_next = QPushButton(">>")
        self.button_run = QPushButton(_('Run code'))
        self.label_image = QLabel()

        self.label_title = QLabel()
        self.label_current = QLabel()
        self.label_content = QLabel()
        
        self.label_content.setMinimumWidth(self.fixed_width)
        self.label_content.setMaximumWidth(self.fixed_width)

        self.label_current.setAlignment(Qt.AlignCenter)

        self.label_content.setWordWrap(True)
        self.button_disable = None

        self.widgets = [self.label_content, self.label_title,
                        self.label_current,
                        self.button_close, self.button_next,
                        self.button_previous]

        self.stylesheet = """QPushButton {
                             background-color: rgbs(200,200,200,100%);
                             color: rgbs(0,0,0,100%);
                             border-style: outset;
                             border-width: 1px;
                             border-radius: 3px;
                             border-color: rgbs(100,100,100,100%);
                             padding: 2px;
                             }

                             QPushButton:hover {
                             background-color: rgbs(150, 150, 150, 100%);
                             }

                             QPushButton:disabled {
                             background-color: rgbs(230,230,230,100%);
                             color: rgbs(200,200,200,100%);
                             border-color: rgbs(200,200,200,100%);
                             }
                             """

        for widget in self.widgets:
            widget.setFocusPolicy(Qt.NoFocus)
            widget.setStyleSheet(self.stylesheet)

        spacer = QSpacerItem(self.offset_shadow, self.offset_shadow)
        spacer2 = QSpacerItem(15, 15)

        layout_top = QHBoxLayout()
        layout_top.addWidget(self.label_title)
        layout_top.addStretch()
        layout_top.addWidget(self.button_close)
        layout_top.addSpacerItem(spacer)

        layout_content = QHBoxLayout()
        layout_content.addWidget(self.label_content)
        layout_content.addWidget(self.label_image)
        layout_content.addSpacerItem(QSpacerItem(5, 5))
        
        layout_run = QHBoxLayout()
        layout_run.addStretch(1)
        layout_run.addWidget(self.button_run)
        layout_run.addStretch(1)
        layout_run.addSpacerItem(spacer)

        layout_navigation = QHBoxLayout()
        layout_navigation.addWidget(self.button_previous)
        layout_navigation.addStretch(1)
        layout_navigation.addWidget(self.label_current)
        layout_navigation.addStretch(1)
        layout_navigation.addWidget(self.button_next)
        layout_navigation.addSpacerItem(spacer)

        self.layout = QVBoxLayout()
        self.layout.addLayout(layout_top)
        self.layout.addStretch()
        self.layout.addSpacerItem(spacer2)
        self.layout.addLayout(layout_content)
        self.layout.addLayout(layout_run)
        self.layout.addStretch()
        self.layout.addSpacerItem(spacer2)
        self.layout.addLayout(layout_navigation)
        self.layout.addSpacerItem(spacer)

        self.setLayout(self.layout)

        self.set_funcs_before_fade_in([self._disable_widgets,
                                       self.activateWindow])

        self.set_funcs_after_fade_in([self._enable_widgets,
#                                      self.show, self.raise_, self.setFocus,
                                      self.activateWindow])

        self.set_funcs_before_fade_out([self._disable_widgets,
                                        self.activateWindow])
        self.setFocusPolicy(Qt.StrongFocus)

    def _disable_widgets(self):
        """ """
        for widget in self.widgets:
            widget.setDisabled(True)

    def _enable_widgets(self):
        """ """
        for widget in self.widgets:
            widget.setDisabled(False)

        if self.button_disable == 'previous':
            self.button_previous.setDisabled(True)
        elif self.button_disable == 'next':
            self.button_next.setDisabled(True)

    def set_data(self, title, content, current, image, run):
        """ """
        self.label_title.setText(title)
        self.label_current.setText(current)
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

        # To make sure that the widget height is calculated before drawing
        # the tip panel
        layout = self.layout
        layout.setSizeConstraint(3)
        layout.activate()
        
    def set_pos(self, x, y):
        """ """
        self.x = x
        self.y = y
        self.move(QPoint(x, y))

    def paintEvent(self, event):
        """ """
        self.build_paths()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillPath(self.round_rect_path, self.color_back)
        painter.fillPath(self.top_rect_path, self.color_top)
        painter.strokePath(self.round_rect_path, QPen(Qt.gray, 1))

        # TODO: Build the pointing arrow?

    def build_paths(self):
        """ """
        geo = self.geometry()
        radius = 30
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

    def keyReleaseEvent(self, event):
        """ """
        key = event.key()
        self.key_pressed = key

        keys = [Qt.Key_Right, Qt.Key_Left, Qt.Key_Down, Qt.Key_Up,
                Qt.Key_Escape, Qt.Key_PageUp, Qt.Key_PageDown]

        if key in keys:
            if not self.is_fade_running():
                self.emit(SIGNAL("keyPressed"))
    
    def mousePressEvent(self, event):
        """override Qt method"""
        # Raise the main application window on click
        self.parent.raise_()
        self.raise_()

    def reject(self):
        """Qt method to handle escape key event"""
        if not self.is_fade_running():
            key = Qt.Key_Escape
            self.key_pressed = key
            self.emit(SIGNAL("keyPressed"))


class AnimatedTour(QWidget):
    """ """

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.duration = 666
        self.opacity_min = 0.0
        self.opacity_middle = 0.7
        self.opacity_max = 1.0
        self.color = Qt.black
        self.easing_curve = QEasingCurve.Linear

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

        self.canvas = FadingCanvas(self.parent, self.opacity_min,
                                   self.opacity_middle, self.duration,
                                   self.easing_curve, self.color)
        self.tips = FadingTipDialog(self.parent, self.opacity_min,
                                    self.opacity_max, self.duration,
                                    self.easing_curve)

        self.connect(self.tips.button_next, SIGNAL('clicked()'),
                     self.next_step)
        self.connect(self.tips.button_previous, SIGNAL('clicked()'),
                     self.previous_step)
        self.connect(self.tips.button_close, SIGNAL('clicked()'),
                     self.close_tour)
        self.connect(self.tips.button_run, SIGNAL('clicked()'),
                     self.run_code)
        self.connect(self.tips.button_run, SIGNAL('clicked()'),
                     lambda: self.tips.button_run.setDisabled(True))


        # Main window move or resize
        self.connect(self.parent, SIGNAL('resized(QResizeEvent)'),
                     self._reset_size)
        self.connect(self.parent, SIGNAL('moved(QMoveEvent)'),
                     self._reset_position)

        # To capture the arrow keys that allow moving the tour
        self.connect(self.tips, SIGNAL("keyPressed"),
                     self._key_pressed)

    def _reset_size(self, event):
        """ """                
        size = event.size()
        self.canvas.setFixedSize(size)
        self.canvas.update_canvas()

        if self.is_tour_set:
            self._set_data()

    def _reset_position(self, event):
        """ """
        pos = event.pos()
        self.canvas.move(QPoint(pos.x(), pos.y()))
        
        if self.is_tour_set:
            self._set_data()

    def _close_canvas(self):
        """ """
        self.tips.hide()
        self.tips.setParent(None)
        self.canvas.fade_out(self.canvas.hide)

    def _move_step(self):
        """ """
        self._set_data()
        frame = self.frames[self.step_current]

        # Show the widget
        if 'widgets' in frame:
            widgets = self.dockwidgets
            widget = widgets[0]
            widget.show()

        frame = self.frames[self.step_current]

        # Very important!
        self.tips.fade_in(self.tips.activateWindow)

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
        """ """
        step, steps, frames = self.step_current, self.steps, self.frames
        current = '{0}/{1}'.format(step + 1, steps)
        frame = frames[step]

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
        else:
            self.canvas.set_interaction(False)

        if 'run' in frame:
            # Asume that the frist widget is the console
            run = frame['run']
            self.run = run            

        self.tips.set_data(title, content, current, image, run)
        self._check_buttons()
        self.canvas.update_widgets(dockwidgets)
        self.canvas.update_decoration(decoration)
        self.canvas.update_canvas()     
        
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
            pass
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

    def run_code(self):
        """ """
        codelines = self.run
        console = self.widgets[0]
        for codeline in codelines:
            console.execute_python_code(codeline)

    def set_tour(self, index, spy_window):
        """ """
        self.frames = get_tour(index)
        self.spy_window = spy_window
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

        # Reset step to begining
        self.step_current = 0

        # Adjust the canvas size to match the main window size
        self.canvas.setFixedSize(width, height)
        self.canvas.move(QPoint(x, y))
        self.canvas.fade_in(self._move_step)

    def close_tour(self):
        """ """
        self.tips.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.tips.show()

        message_box = QMessageBox()
        message_box.setText(_("Do you want to finish the tour?"))
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        answer = message_box.exec_()
        if answer == QMessageBox.Yes:
            self.tips.fade_out(self._close_canvas)
        else:
            self.tips.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint |
                                Qt.WindowStaysOnTopHint)
            self.tips.show()

    def next_step(self):
        """ """
        self.step_current += 1
        self.tips.fade_out(self._move_step)

    def previous_step(self):
        """ """
        self.step_current -= 1
        self.tips.fade_out(self._move_step)


class TestWindow(QMainWindow):
    """ """
    def __init__(self):
        QMainWindow.__init__(self)
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
        self.anim = QPropertyAnimation(effect, "opacity")
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
        index = 'test'
        self.tour.set_tour(index, self)
        self.tour.start_tour()

    def action2(self):
        """ """
        self.anim.start()

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.resizeEvent(self, event)
        self.emit(SIGNAL("resized(QResizeEvent)"), event)
        
    def moveEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.moveEvent(self, event)
        self.emit(SIGNAL("moved(QMoveEvent)"), event)


def test():
    """ """
    app = QApplication([])
    win = TestWindow()
    win.show()
    app.exec_()


if __name__ == '__main__':
    test()
