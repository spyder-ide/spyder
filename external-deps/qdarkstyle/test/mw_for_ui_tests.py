#!python
# -*- coding: utf-8 -*-

"""This module provides a main window for UI tests.
"""

import logging
import sys
import argparse
import qdarkstyle

def get_main_window_app(qt_from='pyqt', no_dark=True):
    """Return main window application."""

    # set log for debug
    logging.basicConfig(level=logging.DEBUG)

    style = ''

    if qt_from == 'pyside':
        # using PySide wrapper
        from PySide.QtGui import QApplication, QMainWindow, QDockWidget
        from PySide.QtCore import QTimer, Qt, QSettings, QByteArray, QPoint, QSize
        # getting style
        style = qdarkstyle.load_stylesheet_pyside()

    elif qt_from == 'pyqt':
        # using PyQt4 wrapper
        from PyQt4.QtGui import QApplication, QMainWindow, QDockWidget
        from PyQt4.QtCore import QTimer, Qt, QSettings, QByteArray, QPoint, QSize
        # getting style
        style = qdarkstyle.load_stylesheet_pyqt()

    elif qt_from == 'pyqt5':
        # using PyQt5 wrapper
        from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget
        from PyQt5.QtCore import QTimer, Qt, QSettings, QByteArray, QPoint, QSize
        # getting style
        style = qdarkstyle.load_stylesheet_pyqt5()

    elif qt_from == 'qtpy':
        # using QtPy API
        from qtpy.QtWidgets import QApplication, QMainWindow, QDockWidget
        from qtpy.QtCore import QTimer, Qt, QSettings, QByteArray, QPoint, QSize
        # getting style
        style = qdarkstyle.load_stylesheet_from_environment()

    elif qt_from == 'pyqtgraph':
        # using PyQtGraph API
        from pyqtgraph.Qt import QtGui, QtCore
        # getting style
        style = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)

    if no_dark:
        style = ''

    # create the application
    app = QApplication(sys.argv)
    app.setOrganizationName('QDarkStyle')
    app.setApplicationName('QDarkStyle Test')
    # setup stylesheet
    app.setStyleSheet(style)
    # create main window
    window = QMainWindow()
    window.setWindowTitle("QDarkStyle v." + qdarkstyle.__version__ +
                          " - TEST - Using " + qt_from)
    # auto quit after 2s when testing on travis-ci
    if "--test" in sys.argv:
        QTimer.singleShot(2000, app.exit)
    # run
    window.showMaximized()
    app.exec_()

    return window

