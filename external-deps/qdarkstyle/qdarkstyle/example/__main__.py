#!python
# -*- coding: utf-8 -*-

"""Example of qdarkstyle use for Python and Qt applications.

This module a main window with every item that could be created with
Qt Design (common ones) in the basic states (enabled/disabled), and
(checked/unchecked) for those who has this attribute.

Requirements:

    - Python 3
    - QtPy
    - PyQt5 or PyQt4 or PySide2 or PySide
    - PyQtGraph or Qt.Py (if choosen)

To run this example using PyQt5, simple do

.. code-block:: python

    python example.py

or

.. code-block:: python

    python example.py  --qt_from=pyqt5

Other options for qt_from are: pyqt5, pyside2, pyqt, pyside, qtpy, pyqtgraph, and qt.py.
Also, you can run the example without any theme (none), to check for problems.

.. code-block:: python

    python example.py  --qt_from=pyqt5 --palette=none

Note:
    qdarkstyle does not have to be installed to run the example.

"""

# Standard library imports

import argparse
import logging
import os
import sys
import platform
import time

# Make the example runnable without the need to install and include ui
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../..'))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../ui'))

# Must be in this place, after setting path, to not need to install
import qdarkstyle  # noqa: E402
from qdarkstyle.dark.palette import DarkPalette  # noqa: E402
from qdarkstyle.light.palette import LightPalette  # noqa: E402

# Set log for debug
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

here = os.path.abspath(os.path.dirname(__file__))

# Constants
SCREENSHOTS_PATH = qdarkstyle.IMAGES_PATH


def main():
    """Execute QDarkStyle example."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--palette', default='dark', type=str,
                        choices=['dark', 'light', 'none'],
                        help="Palette to display. Using 'none' there is no style sheet applied, OS like.")
    parser.add_argument('--qt_from', default='qtpy', type=str,
                        choices=['pyqt5', 'pyqt', 'pyside2', 'pyside', 'qtpy', 'pyqtgraph', 'qt.py'],
                        help="Choose which binding and/or abstraction is to be used to run the example. Default is 'qtpy'")
    parser.add_argument('--test', action='store_true',
                        help="Auto close window after 2s.")
    parser.add_argument('--screenshots', action='store_true',
                        help="Generate screenshots on images folder.")
    parser.add_argument('--offscreen', action='store_true',
                        help="Do not try to show the screen (running on server).")
    parser.add_argument('--reset', action='store_true',
                        help="Reset GUI settings (position, size) then opens.")

    # Parsing arguments from command line
    args = parser.parse_args()

    # To avoid problems when testing without screen
    if args.test or args.offscreen:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    # Set QT_API variable before importing QtPy
    if args.qt_from in ['pyqt', 'pyqt5', 'pyside', 'pyside2']:
        os.environ['QT_API'] = args.qt_from
    elif args.qt_from == 'pyqtgraph':
        os.environ['QT_API'] = os.environ['PYQTGRAPH_QT_LIB']
    elif args.qt_from in ['qt.py', 'qt']:
        try:
            import Qt
        except ImportError:
            print('Could not import Qt (Qt.Py)')
        else:
            os.environ['QT_API'] = Qt.__binding__

    # QtPy imports
    from qtpy import API_NAME, QT_VERSION, PYQT_VERSION, PYSIDE_VERSION, uic
    from qtpy import __version__ as QTPY_VERSION
    from qtpy import QtCore, QtGui, QtWidgets

    # Set API_VERSION variable
    API_VERSION = ''

    if PYQT_VERSION:
        API_VERSION = PYQT_VERSION
    elif PYSIDE_VERSION:
        API_VERSION = PYSIDE_VERSION
    else:
        API_VERSION = 'Not found'

    # create the application
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('QDarkStyle')
    app.setApplicationName('QDarkStyle Example')

    style = ''

    if args.palette == 'dark':
        style = qdarkstyle.load_stylesheet(palette=DarkPalette)
    elif args.palette == 'light':
        style = qdarkstyle.load_stylesheet(palette=LightPalette)

    app.setStyleSheet(style)

    # create main window
    window = QtWidgets.QMainWindow()
    window.setObjectName('mainwindow')
    uic.loadUi(os.path.join(here, 'ui/mw_menus.ui'), window)

    title = ("QDarkStyle Example - ("
             + f"QDarkStyle=v{qdarkstyle.__version__}, "
             + f"QtPy=v{QTPY_VERSION}, "
             + f"{API_NAME}=v{API_VERSION}, "
             + f"Qt=v{QT_VERSION}, "
             + f"Python=v{platform.python_version()}, "
             # Operating system info are maybe too much,
             # but different OS add info in different places
             + f"System={platform.system()}, "
             + f"Release={platform.release()}, "
             + f"Version={platform.version()}, "
             + f"Platform={platform.platform()}"
             + ")")

    _logger.info(title)
    window.setWindowTitle(title)

    # Create docks for buttons
    dw_buttons = QtWidgets.QDockWidget()
    dw_buttons.setObjectName('buttons')
    uic.loadUi(os.path.join(here, 'ui/dw_buttons.ui'), dw_buttons)
    window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dw_buttons)

    # Set state indeterminate (value=1)
    dw_buttons.checkBoxTristate.stateChanged.connect(dw_buttons.checkBoxTristateDis.setCheckState)
    dw_buttons.checkBoxTristate.setCheckState(1)

    # Add actions on popup toolbuttons
    menu = QtWidgets.QMenu()

    for action in ['Action A', 'Action B', 'Action C']:
        menu.addAction(action)

    # Add menu in special tool buttons
    dw_buttons.toolButtonDelayedPopup.setMenu(menu)
    dw_buttons.toolButtonInstantPopup.setMenu(menu)
    dw_buttons.toolButtonMenuButtonPopup.setMenu(menu)

    # Add menu in toolbar #251
    action_menu = QtWidgets.QAction(u'Menu action', window.toolBarMenus)
    action_menu.setMenu(menu)
    window.toolBarMenus.addAction(action_menu)

    # Add color to tab title text #212
    window.tabWidget.tabBar().setTabTextColor(3, QtGui.QColor('red'))

    # Connect dialogs to buttons
    window.toolButtonColorDialog.clicked.connect(lambda: QtWidgets.QColorDialog().exec())
    window.toolButtonFileDialog.clicked.connect(lambda: QtWidgets.QFileDialog().exec())
    window.toolButtonFileDialogStatic.clicked.connect(lambda: QtWidgets.QFileDialog.getOpenFileNames())
    window.toolButtonFontDialog.clicked.connect(lambda: QtWidgets.QFontDialog().exec())
    window.toolButtonInputDialog.clicked.connect(lambda: QtWidgets.QInputDialog().exec())
    window.toolButtonMessageBox.clicked.connect(lambda: QtWidgets.QMessageBox().exec())
    window.toolButtonMessageBoxStatic.clicked.connect(lambda: QtWidgets.QMessageBox.critical(window, "Critical title", "Critical message"))
    window.toolButtonProgressDialog.clicked.connect(lambda: QtWidgets.QProgressDialog().exec())

    # Create docks for buttons
    dw_displays = QtWidgets.QDockWidget()
    dw_displays.setObjectName('displays')
    uic.loadUi(os.path.join(here, 'ui/dw_displays.ui'), dw_displays)
    window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dw_displays)

    # Create docks for inputs - no fields
    dw_inputs_no_fields = QtWidgets.QDockWidget()
    dw_inputs_no_fields.setObjectName('inputs_no_fields')
    uic.loadUi(os.path.join(here, 'ui/dw_inputs_no_fields.ui'), dw_inputs_no_fields)
    window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dw_inputs_no_fields)

    # Create docks for inputs - fields
    dw_inputs_fields = QtWidgets.QDockWidget()
    dw_inputs_fields.setObjectName('inputs_fields')
    uic.loadUi(os.path.join(here, 'ui/dw_inputs_fields.ui'), dw_inputs_fields)
    window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dw_inputs_fields)

    # Create docks for widgets
    dw_widgets = QtWidgets.QDockWidget()
    dw_widgets.setObjectName('widgets')
    uic.loadUi(os.path.join(here, 'ui/dw_widgets.ui'), dw_widgets)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw_widgets)

    # Create docks for views
    dw_views = QtWidgets.QDockWidget()
    dw_views.setObjectName('views')
    uic.loadUi(os.path.join(here, 'ui/dw_views.ui'), dw_views)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw_views)

    # Create docks for containers - no tabs
    dw_containers_no_tabs = QtWidgets.QDockWidget()
    dw_containers_no_tabs.setObjectName('containers_no_tabs')
    uic.loadUi(os.path.join(here, 'ui/dw_containers_no_tabs.ui'), dw_containers_no_tabs)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw_containers_no_tabs)

    # Create docks for containters - tabs
    dw_containers_tabs = QtWidgets.QDockWidget()
    dw_containers_tabs.setObjectName('containers_tabs')
    uic.loadUi(os.path.join(here, 'ui/dw_containers_tabs.ui'), dw_containers_tabs)
    window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw_containers_tabs)

    # Tabify right docks
    window.tabifyDockWidget(dw_buttons, dw_displays)
    window.tabifyDockWidget(dw_displays, dw_inputs_fields)
    window.tabifyDockWidget(dw_inputs_fields, dw_inputs_no_fields)

    # Tabify left docks
    window.tabifyDockWidget(dw_containers_no_tabs, dw_containers_tabs)
    window.tabifyDockWidget(dw_containers_tabs, dw_widgets)
    window.tabifyDockWidget(dw_widgets, dw_views)

    # Issues #9120, #9121 on Spyder
    qstatusbar = QtWidgets.QStatusBar()
    qstatusbar.addWidget(QtWidgets.QLabel('Issue Spyder #9120, #9121 - background not matching.'))
    qstatusbar.addWidget(QtWidgets.QPushButton('OK'))

    # Add info also in status bar for screenshots get it
    qstatusbar.addWidget(QtWidgets.QLabel('INFO: ' + title))
    window.setStatusBar(qstatusbar)

    # Todo: add report info and other info in HELP graphical

    # Auto quit after 2s when in test mode
    if args.test:
        QtCore.QTimer.singleShot(2000, app.exit)

    # Save screenshots for different displays and quit
    if args.screenshots:
        window.showFullScreen()
        create_screenshots(app, window, args)
    # Do not read settings when taking screenshots - like reset
    else:
        _read_settings(window, args.reset, QtCore.QSettings)
        window.showMaximized()

    app.exec_()
    _write_settings(window, QtCore.QSettings)


def _write_settings(window, QSettingsClass):
    """Get window settings and write it into a file."""
    settings = QSettingsClass('QDarkStyle', 'QDarkStyle Example')
    settings.setValue('pos', window.pos())
    settings.setValue('size', window.size())
    settings.setValue('state', window.saveState())


def _read_settings(window, reset, QSettingsClass):
    """Read and set window settings from a file."""
    settings = QSettingsClass('QDarkStyle', 'QDarkStyle Example')

    try:
        pos = settings.value('pos', window.pos())
        size = settings.value('size', window.size())
        state = settings.value('state', window.saveState())
    except Exception:
        pos = settings.value('pos', window.pos(), type='QPoint')
        size = settings.value('size', window.size(), type='QSize')
        state = settings.value('state', window.saveState(), type='QByteArray')

    if not reset:
        window.restoreState(state)
        window.resize(size)
        window.move(pos)


def create_screenshots(app, window, args):
    """Save screenshots for different application views and quit."""

    theme = args.palette

    print('\nCreating {} screenshots'.format(theme))

    docks = window.findChildren(QtWidgets.QDockWidget)
    tabs = window.findChildren(QtWidgets.QTabWidget)

    widget_data = {
        'containers_no_tabs_buttons.png': [
            'Containers - No Tabs',
            'Buttons',
        ],
        'containers_tabs_displays.png': [
            'Containers - Tabs',
            'Displays',
        ],
        'widgets_inputs_fields.png': [
            'Widgets',
            'Inputs - Fields',
        ],
        'views_inputs_no_fields.png': [
            'Views',
            'Inputs - No Fields',
        ]
    }

    # Central widget tabs of with examples, reset positions
    tab = [tab for tab in tabs if tab.count() >= 12][0]
    tab.setCurrentIndex(0)

    QtCore.QCoreApplication.processEvents()

    for fname_suffix, dw_titles in widget_data.items():
        png_path = os.path.join(SCREENSHOTS_PATH, theme, fname_suffix)
        print('\t' + png_path)

        for dw in docks:
            if dw.windowTitle() in dw_titles:
                print('Evidencing : ', dw.windowTitle())
                dw.raise_()
                dw.show()
                QtCore.QCoreApplication.processEvents()

        # Attention: any change in update, processEvent and sleep calls
        # make those screenshots not working, specially the first one.
        # It seems that processEvents are not working properly

        window.update()
        window.showFullScreen()
        QtCore.QCoreApplication.processEvents()

        time.sleep(0.5)
        QtCore.QCoreApplication.processEvents()

        screen = QtGui.QGuiApplication.primaryScreen()
        QtCore.QCoreApplication.processEvents()
        pixmap = screen.grabWindow(window.winId())

        # Yeah, this is duplicated to avoid screenshot problems
        screen = QtGui.QGuiApplication.primaryScreen()
        QtCore.QCoreApplication.processEvents()
        pixmap = screen.grabWindow(window.winId())

        img = pixmap.toImage()
        img.save(png_path)

        QtCore.QCoreApplication.processEvents()

    QtCore.QCoreApplication.processEvents()
    window.close()
    print('\n')
    app.exit(sys.exit())


if __name__ == "__main__":
    sys.exit(main())
