# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder, the Scientific PYthon Development EnviRonment
=====================================================

Developped and maintained by Pierre Raybaut

Copyright © 2009-2012 Pierre Raybaut
Licensed under the terms of the MIT License
(see spyderlib/__init__.py for details)
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import division

import sys
import re
import sre_constants
import os.path as osp
import time

from spyderlib.qt import is_pyqt46
from spyderlib.qt.QtGui import (QColor, QMenu, QApplication, QSplitter, QFont,
                                QTextEdit, QTextFormat, QPainter, QTextCursor,
                                QBrush, QTextDocument, QTextCharFormat,
                                QPixmap, QPrinter, QToolTip, QCursor, QLabel,
                                QInputDialog, QTextBlockUserData, QLineEdit,
                                QKeySequence, QWidget, QVBoxLayout,
                                QHBoxLayout, QDialog, QIntValidator,
                                QDialogButtonBox, QGridLayout, QMainWindow,
                                QAction, QPushButton, QGraphicsDropShadowEffect,
                                QPainterPath, QSpacerItem, QPen, QMessageBox,
                                QGraphicsOpacityEffect)
from spyderlib.qt.QtCore import (Qt, SIGNAL, QTimer, QRect, QRegExp, QSize,
                                 SLOT, Slot, QPointF, QPoint, QRectF,
                                 QTimeLine, QEvent, QPropertyAnimation,
                                 QEasingCurve)
from spyderlib.qt.compat import to_qvariant

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
from spyderlib.utils.sourcecode import ALL_LANGUAGES
from spyderlib.widgets.editortools import PythonCFM
from spyderlib.widgets.sourcecode.base import TextEditBaseWidget
from spyderlib.widgets.sourcecode import syntaxhighlighters as sh
from spyderlib.py3compat import to_text_string


# FIXME: WHERE TO PUT THIS?

def get_tour(index):
    """ """

    test = [{'title': "Welcome to Spyder introduction tour",
             'content': "<b>Spyder</b> is an interactive development environment \
                         based on bla",
             'image' : 'spyder.png'},

            {'title': "Welcome to Spyder introduction tour",
             'content': "Spyder is an interactive development environment \
                         based on bla",
             'widgets': ['button']},

            {'title': "Welcome to Spyder introduction tour",
             'content': "Spyder is an interactive development environment \
                         based on bla",
             'image' : 'spyder.png'},
            ]
    
    intro = [{'title': _("Welcome to Spyder introduction tour"),
              'content': _("<b>Spyder</b> is a powerful interactive development \
                          environment for the Python language. \n \
                          Use the arrow keys or the mouse to move into the tour."),
              'image' : 'spyder.png'},

             {'title': _("The toolbars"),
              'content': _("<b>Spyder</b> is a powerful interactive development \
                          environment for the Python language with advanced \
                          editing, interactive testing, debugging and \
                          introspection features"),
              'widgets': ['file_toolbar']},
                  
    
                   ['The run toolbar', 
                       '', 
                       ['self.run_toolbar'], None],
                   ['The debug toolbar', 
                       '', 
                       ['self.debug_toolbar'], None],
                   ['The main toolbar', 
                       '', 
                       ['self.main_toolbar'], None],
                   ['The editor', 
                       'Spyder has differnet bla bla bla', 
                       ['self.editor.dockwidget'], None],
                   ['The editor', 
                       'Spyder has differnet bla bla bla', 
                       ['self.outlineexplorer.dockwidget'], None],

                   ['The menu bar', 
                       'Spyder has differnet bla bla bla', 
                       ['self.menuBar()'], None],

                   ['The menu bar', 
                       'Spyder has differnet bla bla bla', 
                       ['self.statusBar()'], None],

                       
                   ['The toolbars!', 
                       'Spyder has differnet bla bla bla', 
                       ['self.variableexplorer.dockwidget'], None],
                   ['The toolbars MO!', 
                       'Spyder has differnet bla bla bla', 
                       ['self.extconsole.dockwidget'], None],
                   ['The whole window?!', 
                       'Spyder has differnet bla bla bla', 
                       ['self'], None],
                   ['Lets try something!', 
                       'Spyder has differnet bla bla bla', 
                       ['self.extconsole.dockwidget', 
                        'self.variableexplorer.dockwidget'], None]
                        
                      ]

    tours = {0: test,
             1: intro}

    return tours[index]

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
        self.anim_running = False
        self.funcs_before_fade_in = []
        self.funcs_after_fade_in = []        
        self.funcs_before_fade_out = []

    def _set_anim_finished(self):
        """ """
        self.anim_running = False
    
    def is_anim_running(self):
        return self.anim_running

    def __fade_setup(self):
        """ """
        self.anim_running = True
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, "opacity")
        self.anim.setEasingCurve(self.easing_curve)

    def fade_in(self, on_finished_connect):
        """ """
        self.__run_before_fade_in()
        self.__fade_setup()
        self.show()        
        self.anim.setStartValue(self.opacity_min)
        self.anim.setEndValue(self.opacity_max)
        self.anim.setDuration(self.duration)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_anim_finished)
        self.anim.finished.connect(self.__run_after_fade_in)
        self.anim.start()

    def fade_out(self, on_finished_connect):
        """ """
        self.__run_before_fade_out()
        self.__fade_setup()       
        self.anim.setStartValue(self.opacity_max)
        self.anim.setEndValue(self.opacity_min)
        self.anim.setDuration(self.duration)
        self.anim.finished.connect(on_finished_connect)
        self.anim.finished.connect(self._set_anim_finished)
        self.anim.start()
        
    def __run_before_fade_in(self):
        """ """
        funcs = self.funcs_before_fade_in
        for func in funcs:
            func()

    def __run_after_fade_in(self):
        """ """
        funcs = self.funcs_after_fade_in
        for func in funcs:
            func()            

    def __run_before_fade_out(self):
        """ """
        funcs = self.funcs_before_fade_out
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

        self.widgets = None    # The widgets to uncover

        self.path_current = None
        self.path_to_subtract = None
        self.path_full = None

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

    def _update_canvas(self):
        """ """
        w, h = self.parent.size().width(), self.parent.size().height()

        self.path_full = QPainterPath()
        self.path_to_subtract = QPainterPath()

        self.path_full.addRect(0, 0, w, h)

        # Add the path
        if self.widgets is not None:
            for widget in self.widgets:
                widget.raise_()
                widget.show()
                geo = widget.frameGeometry()
                width, height = geo.width(), geo.height()
                point = widget.mapTo(self.parent, QPoint(0, 0))
                x, y = point.x() , point.y()

                self.path_to_subtract.addRect(QRectF(x, y,width, height))

            self.path_current = self.path_full.subtracted(self.path_to_subtract)
        else:
            self.path_current = self.path_full

        # Add a decoration stroke around widget
        # TODO:

    def paintEvent(self, event):
        """ """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Decoration
        painter.fillPath(self.path_current, QBrush(self.color))
        #painter.strokePath(self.round_rect_path, QPen(Qt.gray, 1));

    def switch(self):
        """ """
#        self.repaint()
        self._update_canvas()
#        self.repaint()

    def update_widgets(self, widgets):
        """ """
        self.widgets = widgets

    def update_decoration_widgets(self, widgets):
        """ """
        self.widgets_decoration = widgets



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
        self.fixed_width = 360

        self.key_pressed = None

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(self.offset_shadow/2)
        effect.setOffset(self.offset_shadow/2, self.offset_shadow/2)
        self.setGraphicsEffect(effect)

        self.setAttribute(Qt.WA_TranslucentBackground)
#        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # Widgets
        self.button_close = QPushButton("X")
        self.button_previous = QPushButton("<<")
        self.button_next = QPushButton(">>")

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



        self.label_title = QLabel()
        self.label_current = QLabel()
        self.label_content = QLabel()

        self.label_current.setAlignment(Qt.AlignCenter)

        self.label_content.setWordWrap(True)
        self.label_image = QLabel()
        self.label_empty_previous = QLabel()
        self.label_empty_next = QLabel()
        self.button_disable = None

        self.widgets = [self.label_content, self.label_title, self.label_current,
                        self.button_close, self.button_next,
                        self.button_previous]
                        

        for widget in self.widgets:
            widget.setFocusPolicy(Qt.NoFocus)
            widget.setStyleSheet(self.stylesheet)

        spacer = QSpacerItem(self.offset_shadow, self.offset_shadow)
        spacer2 = QSpacerItem(20, 20)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label_title)
        top_layout.addStretch()
        top_layout.addWidget(self.button_close)
        top_layout.addSpacerItem(spacer)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self.label_content)
        content_layout.addWidget(self.label_image)
        content_layout.addSpacerItem(QSpacerItem(5,5))

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button_previous)
        button_layout.addStretch(1)
        button_layout.addWidget(self.label_current)
        button_layout.addStretch(1)
        button_layout.addWidget(self.button_next)
        button_layout.addSpacerItem(spacer)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addSpacerItem(spacer2)
        layout.addLayout(content_layout)
        layout.addSpacerItem(spacer2)
        layout.addLayout(button_layout)
        layout.addSpacerItem(spacer)

        self.setLayout(layout)
        self.setFixedWidth(self.fixed_width)
        
        self.set_funcs_before_fade_in([self._disable_widgets,
                                       self._set_window_flags])

        self.set_funcs_after_fade_in([self._enable_widgets,
                                      self._set_window_flags])
                                       
        self.set_funcs_before_fade_out([self._disable_widgets])
        self.setModal(True)

    def set_data(self, title, content, current, image=None):
        """ """
        self.label_title.setText(title)
        self.label_current.setText(current)
        self.label_content.setText(content)
        self.image = image
        
        if image is None:
            self.label_image.setFixedSize(0, 0)
        else:
            extension = image.split('.')[-1]
            self.image = QPixmap(get_image_path(image), extension)
            self.label_image.setFixedSize(self.image.size())

        # To make sure that the widget height is calculated before drawing
        # the tip panel
        self.show()
        self.hide()
        self.repaint()

    def set_pos(self, x, y):
        """ """
        self.x = x
        self.y = y
#        if x is not None and y is not None:
        self.move(QPoint(x, y))

    def paintEvent(self, event):
        """ """
        self.build_paths()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillPath(self.round_rect_path, self.color_back)
        painter.fillPath(self.top_rect_path, self.color_top)
        painter.strokePath(self.round_rect_path, QPen(Qt.gray, 1))
        
        if self.image is not None:
            x = self.fixed_width - self.offset_shadow - self.image.width()
            y = self.label_content.y()
            
            painter.drawPixmap(QPoint(x, y), self.image)
            self.label_image.setFixedSize(self.image.size())
        else:
            self.label_image.setFixedSize(0, 0)

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
        self.round_rect_path.arcTo(right-radius, top, radius, radius, 0.0, 90.0)
        self.round_rect_path.lineTo(left+radius, top)
        self.round_rect_path.arcTo(left, top, radius, radius, 90.0, 90.0)
        self.round_rect_path.lineTo(left, bottom-radius)
        self.round_rect_path.arcTo(left, bottom-radius, radius, radius, 180.0, 90.0)
        self.round_rect_path.lineTo(right-radius, bottom)
        self.round_rect_path.arcTo(right-radius, bottom-radius, radius, radius, 270.0, 90.0)
        self.round_rect_path.closeSubpath()

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

    def _set_window_flags(self):
        """ """
        # Needed to be able to click again on the fading tip wodget
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.raise_()

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

    def keyReleaseEvent(self, event):
        """ """
        key = event.key()
        self.key_pressed = key

        keys = [Qt.Key_Right, Qt.Key_Left, Qt.Key_Down, Qt.Key_Up,
                Qt.Key_Escape]

        if key in keys:
            if not self.is_anim_running():
                self.emit(SIGNAL("keyPressed"))

    def reject(self):
        """Qt method to handle escape key event"""
        key = Qt.Key_Escape
        self.key_pressed = key
        self.emit(SIGNAL("keyPressed"))


class AnimatedTour(QWidget):
    """ """

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.duration= 666
        self.opacity_min = 0.0
        self.opacity_middle = 0.7   
        self.opacity_max = 1.0
        self.color = Qt.black
        self.easing_curve = QEasingCurve.Linear

        self.current_step = 0
        self.step_current = 0
        self.steps = 0

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
        
        # FIXME: Not working now
        # To capture the arrow keys that allow moving the tour
        self.connect(self.tips, SIGNAL("keyPressed"),
                     self.key_pressed)

    def set_tour(self, index, spy_window):
        """ """
        self.spy_window = spy_window
        self.frames = get_tour(index)
        self.steps = len(self.frames)
        self._set_data()

    def _start_tips(self):
        """ """
        self.tips.fade_in(self.tips.show)
#        self.tips.raise_()

    def _close_canvas(self):
        """ """
        self.canvas.fade_out(self.canvas.close)
        # FIXME: some weird bug with the widget closing
        self.tips.raise_()           # Not sure why... but needed~
        self.tips.setParent(None)  # To delete the widget

    def _move_step(self):
        """ """
        self._set_data()
        frame = self.frames[self.step_current]

        # Show the widget
        if 'widgets' in  frame:
            widgets = self.widgets
            widget = widgets[0]
            widget.show()

        # Very important!
        self.tips.fade_in(self.canvas.lower)
        self.tips.raise_()

    def _set_data(self):
        """ """
        step, steps, frames = self.step_current, self.steps, self.frames
        current = '{0}/{1}'.format(step + 1, steps)
        frame = frames[step]

        title, content, widgets, image = '', '', None, None
        
        # Check if entry exists in dic and act accordingly
        if 'title' in frame:
            title = frame['title']
        if 'content' in frame:
            content = frame['content']
        if 'widgets' in frame:
            widgets = []
            widget_names = frames[step]['widgets']
            # Get the widgets based on their name
            for name in widget_names:
                widgets.append(getattr(self.spy_window, name))
            self.widgets = widgets

        if 'image' in frame:
            image = frames[step]['image']
        
        self.tips.set_data(title, content, current, image)
        self._check_buttons()
        self.canvas.update_widgets(widgets)
        self.canvas.switch()

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
        if widgets is not None:
            geo = widgets[0].geometry()
            x, y, width, height = geo.x(), geo.y(), geo.width(), geo.height()


            point = widgets[0].mapToGlobal(QPoint(0, 0))
            x_glob, y_glob = point.x(), point.y()

            # Check if is too tall and put to the side
            y_fac = height/self.height_main*100


            if y_fac > 60:  # FIXME:
                print('in the side!')
                if x < self.tips.width():
                    x = x_glob + width + delta
                    y = y_glob + height/2 - self.tips.height()/2 # Delta.. to define
                else:
                    x = x_glob - self.tips.width() - delta
                    y = y_glob + height/2 - self.tips.height()/2 # Delta.. to define
            else:
            # If toolbars... check for height
#            if height < self.tips.height():
                if y < self.tips.height():
                    x = x_glob + width/2 - self.tips.width()/2
                    y = y_glob + height + delta # Delta.. to define
                else:
                    x = x_glob + width/2 - self.tips.width()/2
                    y = y_glob - delta - self.tips.height()# Delta.. to define
#            else:
#                x = x + width/2 - self.tips.width()/2
#                y = y + height #se1lf.tips.height()/2
        else:
            pass
            # Center on parent
            x = self.x_main + self.width_main/2 - self.tips.width()/2
            y = self.y_main + self.height_main/2 - self.tips.height()/2
#            print('set data', geo)
#            print(self.tips.size())
#            print('set data', x, y)

        self.tips.set_pos(x, y)

    def _check_buttons(self):
        """ """
        step, steps = self.step_current, self.steps
        self.tips.button_disable = None
              
        if step == 0: 
            self.tips.button_disable = 'previous'

        if step == steps - 1:
            self.tips.button_disable = 'next'

    def start_tour(self):
        """ """
        geo = self.parent.geometry()
        x, y, width, height = geo.x(), geo.y(), geo.width(), geo.height()
        self.parent_x = x
        self.parent_y = y
        self.parent_w = width
        self.parent_h = height

        # Reset step to begining
        self.step_current = 0

        # Adjust the canvas size to match the main window size
        self.canvas.setMaximumSize(width, height)
        self.canvas.setMinimumSize(width, height)
        self.canvas.move(QPoint(x, y))

        self.canvas.fade_in(self._start_tips)
        self._set_data()

    def close_tour(self):
        """ """
        answer = QMessageBox.warning(self, _("All set to go?"),
                     _("Do you want to finish the tour?"),
                     QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            # Gracefully close everything
            self.tips.fade_out(self._close_canvas)

    def next_step(self):
        """ """
        self.step_current += 1
        self.tips.fade_out(self._move_step)

    def previous_step(self):
        """ """
        self.step_current -= 1
        self.tips.fade_out(self._move_step)

    def key_pressed(self):
        """ """
        key = self.tips.key_pressed

        if ((key == Qt.Key_Right or key == Qt.Key_Up) and
             self.step_current != self.steps - 1):
            self.next_step()
        elif ((key == Qt.Key_Left or key == Qt.Key_Down) and
              self.step_current != 0):
            self.previous_step()
        elif key == Qt.Key_Escape:
            print('close tour')
            self.close_tour()


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
        self.tour.set_tour(0, self)
        self.tour.start_tour()

    def action2(self):
        """ """
        self.anim.start()

def test():
    """ """
    app = QApplication([])
    win = TestWindow()
    win.show()
    app.exec_()


if __name__ == '__main__':
    test()
