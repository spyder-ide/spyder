# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Patching matplotlib's FigureManager"""

from __future__ import print_function

import sys

# Local imports
from spyderlib.py3compat import to_text_string


def is_available():
    """Is Matplotlib installed version supported by this patch?"""
    import matplotlib
    mpl_ver = matplotlib.__version__.split('.')
    if int(mpl_ver[0]) < 1 or int(mpl_ver[0]) == 1 and int(mpl_ver[1]) == 0:
        # Matplotlib <=v1.0 is installed
        return True


def apply():
    """Monkey patching matplotlib Qt4 backend figures"""
    if not is_available():
        return

    # Warning: do not move these import statements outside this function,
    # otherwise, PyQt would be imported as soon as this module would be.
    from spyderlib.qt import is_pyqt46
    from spyderlib.qt.QtGui import QIcon, QCursor, QInputDialog, QMainWindow
    from spyderlib.qt.QtCore import Qt, SIGNAL, QObject
    
    # Avoid using matplotlib's formlayout version which is not compatible 
    # with PyQt4 API #2 and PySide (at least up to Matplotlib v1.0.1)
    from spyderlib.widgets import formlayout
    sys.modules['matplotlib.backends.qt4_editor.formlayout'] = formlayout
    import matplotlib.backends.qt4_editor
    matplotlib.backends.qt4_editor.formlayout = formlayout
    
    from matplotlib.backends import backend_qt4
    
    # Class added to matplotlib to fix a bug with PyQt4 v4.6+
    class FigureWindow(QMainWindow):
        def __init__(self):
            super(FigureWindow, self).__init__()
            
        def closeEvent(self, event):
            super(FigureWindow, self).closeEvent(event)
            if is_pyqt46:
                self.emit(SIGNAL('destroyed()'))
    # ****************************************************************
    # *  FigureManagerQT
    # ****************************************************************
    class FigureManagerQT(backend_qt4.FigureManagerQT):
        """
        Patching matplotlib...
        """
        def __init__(self, canvas, num):
            import matplotlib
            
            if backend_qt4.DEBUG:
                print('FigureManagerQT.%s' % backend_qt4.fn_name())
            backend_qt4.FigureManagerBase.__init__(self, canvas, num)
            self.canvas = canvas
            
            self.window = FigureWindow()
            self.window.setWindowTitle("Figure %d" % num)
            self.window.setAttribute(Qt.WA_DeleteOnClose)

            import os.path as osp
            image = osp.join(matplotlib.rcParams['datapath'],
                             'images', 'matplotlib.png' )
            self.window.setWindowIcon(QIcon(image))
    
            # Give the keyboard focus to the figure instead of the manager
            self.canvas.setFocusPolicy(Qt.ClickFocus)
            self.canvas.setFocus()
    
            QObject.connect(self.window, SIGNAL('destroyed()'),
                            lambda: self._widgetclosed())
            self.window._destroying = False
    
            self.toolbar = self._get_toolbar(self.canvas, self.window)
            self.window.addToolBar(self.toolbar)
            QObject.connect(self.toolbar, SIGNAL("message"),
                    self.window.statusBar().showMessage)
    
            self.window.setCentralWidget(self.canvas)
    
            if matplotlib.is_interactive():
                self.window.show()
    
            # attach a show method to the figure for pylab ease of use
            self.canvas.figure.show = lambda *args: self.window.show()
    
            def notify_axes_change(fig):
                # This will be called whenever the current axes is changed
                if self.toolbar != None: self.toolbar.update()
            self.canvas.figure.add_axobserver(notify_axes_change)
    # ****************************************************************
    backend_qt4.FigureManagerQT = FigureManagerQT
    
    # ****************************************************************
    # *  NavigationToolbar2QT
    # ****************************************************************
    try:
        # This will work with the next matplotlib release:
        edit_parameters = backend_qt4.NavigationToolbar2QT.edit_parameters
        # -> Figure options button has already been added by matplotlib
    except AttributeError:
        edit_parameters = None
        # -> Figure options button does not exist yet
        
    from spyderlib.widgets.figureoptions import figure_edit
    class NavigationToolbar2QT(backend_qt4.NavigationToolbar2QT):
        def _init_toolbar(self):
            super(NavigationToolbar2QT, self)._init_toolbar()
            if edit_parameters is None:
                from spyderlib.utils.qthelpers import get_icon
                a = self.addAction(get_icon("options.svg"),
                                   'Customize', self.edit_parameters)
                a.setToolTip('Edit curves line and axes parameters')
        def edit_parameters(self):
            allaxes = self.canvas.figure.get_axes()
            if len(allaxes) == 1:
                axes = allaxes[0]
            elif len(allaxes) > 1:
                titles = []
                for axes in allaxes:
                    title = axes.get_title()
                    ylabel = axes.get_ylabel()
                    if title:
                        text = title
                        if ylabel:
                            text += ": "+ylabel
                        text += " (%s)"
                    elif ylabel:
                        text = ylabel+" (%s)"
                    else:
                        text = "%s"
                    titles.append(text % repr(axes))
                item, ok = QInputDialog.getItem(self, 'Customize',
                                                'Select axes:', titles,
                                                0, False)
                if ok:
                    axes = allaxes[titles.index(to_text_string(item))]
                else:
                    return
            else:
                return
            figure_edit(axes, self)
        def save_figure(self):
            super(NavigationToolbar2QT, self).save_figure()
        def set_cursor(self, cursor):
            if backend_qt4.DEBUG: print('Set cursor', cursor)
            self.parent().setCursor(QCursor(backend_qt4.cursord[cursor]))
    # ****************************************************************
    backend_qt4.NavigationToolbar2QT = NavigationToolbar2QT
