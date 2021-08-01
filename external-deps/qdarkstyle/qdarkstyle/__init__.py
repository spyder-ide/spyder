#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The most complete dark/light style sheet for Qt applications (Qt4, Qt5,
PySide, PySide2, PyQt4, PyQt5, QtPy, PyQtGraph, Qt.Py) for Python 2/3 and C++.

Python 2, as well as Qt4 (PyQt4 and PySide), will not be supported anymore.
They still there as it is, but no back-compatibility, fixes, nor features
will be implemented.

We still preparing the portability to Qt6 since we need changes in
`QtPy <https://github.com/spyder-ide/qtpy>`__ dependency project.

Check the `documentation <https://qdarkstylesheet.readthedocs.io/en/stable>`__
to see how to set the desirable theme palette.

This module provides a function to load the stylesheets transparently
with the right resources file.

First, start importing our module

.. code-block:: python

    import qdarkstyle

Then you can get stylesheet provided by QDarkStyle for various Qt wrappers
as shown below

.. code-block:: python

    # PySide
    dark_stylesheet = qdarkstyle.load_stylesheet_pyside()
    # PySide 2
    dark_stylesheet = qdarkstyle.load_stylesheet_pyside2()
    # PyQt4
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt()
    # PyQt5
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()

Alternatively, from environment variables provided by QtPy, PyQtGraph, Qt.Py

.. code-block:: python

    # QtPy
    dark_stylesheet = qdarkstyle.load_stylesheet()
    # PyQtGraph
    dark_stylesheet = qdarkstyle.load_stylesheet(qt_api=os.environ('PYQTGRAPH_QT_LIB'))
    # Qt.Py
    dark_stylesheet = qdarkstyle.load_stylesheet(qt_api=Qt.__binding__)

Finally, set your QApplication with it

.. code-block:: python

    app.setStyleSheet(dark_stylesheet)

Enjoy!

"""

# Standard library imports
import logging
import os
import platform
import sys
import warnings

# Local imports
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
from qdarkstyle.palette import Palette

__version__ = "3.0.2"

_logger = logging.getLogger(__name__)

# Folder's path
REPO_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

EXAMPLE_PATH = os.path.join(REPO_PATH, 'example')
IMAGES_PATH = os.path.join(REPO_PATH, 'docs/images')
PACKAGE_PATH = os.path.join(REPO_PATH, 'qdarkstyle')

QSS_PATH = os.path.join(PACKAGE_PATH, 'qss')
RC_PATH = os.path.join(PACKAGE_PATH, 'rc')
SVG_PATH = os.path.join(PACKAGE_PATH, 'svg')

# File names
QSS_FILE = 'style.qss'
QRC_FILE = QSS_FILE.replace('.qss', '.qrc')

MAIN_SCSS_FILE = 'main.scss'
STYLES_SCSS_FILE = '_styles.scss'
VARIABLES_SCSS_FILE = '_variables.scss'

# File paths
QSS_FILEPATH = os.path.join(PACKAGE_PATH, QSS_FILE)
QRC_FILEPATH = os.path.join(PACKAGE_PATH, QRC_FILE)

MAIN_SCSS_FILEPATH = os.path.join(QSS_PATH, MAIN_SCSS_FILE)
STYLES_SCSS_FILEPATH = os.path.join(QSS_PATH, STYLES_SCSS_FILE)
VARIABLES_SCSS_FILEPATH = os.path.join(QSS_PATH, VARIABLES_SCSS_FILE)

# Todo: check if we are deprecate all those functions or keep them
DEPRECATION_MSG = '''This function will be deprecated in v3.0.
Please, set the wanted binding by using QtPy environment variable QT_API,
then use load_stylesheet() or use load_stylesheet()
passing the argument qt_api='wanted_binding'.'''


def _apply_os_patches(palette):
    """
    Apply OS-only specific stylesheet pacthes.

    Returns:
        str: stylesheet string (css).
    """
    os_fix = ""

    if platform.system().lower() == 'darwin':
        # See issue #12, #267
        os_fix = '''
        QDockWidget::title
        {{
            background-color: {color};
            text-align: center;
            height: 12px;
        }}
        QTabBar::close-button {{
            padding: 2px;
        }}
        '''.format(color=palette.COLOR_BACKGROUND_4)

    # Only open the QSS file if any patch is needed
    if os_fix:
        _logger.info("Found OS patches to be applied.")

    return os_fix


def _apply_binding_patches():
    """
    Apply binding-only specific stylesheet patches for the same OS.

    Returns:
        str: stylesheet string (css).
    """
    binding_fix = ""

    if binding_fix:
        _logger.info("Found binding patches to be applied.")

    return binding_fix


def _apply_version_patches(qt_version):
    """
    Apply version-only specific stylesheet patches for the same binding.

    Args:
        qt_version (str): Qt string version.

    Returns:
        str: stylesheet string (css).
    """
    version_fix = ""

    major, minor, patch = qt_version.split('.')
    major, minor, patch = int(major), int(minor), int(patch)

    if major == 5 and minor >= 14:
        # See issue #214
        version_fix = '''
        QMenu::item {
            padding: 4px 24px 4px 6px;
        }
        '''

    if version_fix:
        _logger.info("Found version patches to be applied.")

    return version_fix


def _apply_application_patches(QCoreApplication, QPalette, QColor, palette):
    """
    Apply application level fixes on the QPalette.

    The import names args must be passed here because the import is done
    inside the load_stylesheet() function, as QtPy is only imported in
    that moment for setting reasons.
    """
    # See issue #139
    color = palette.COLOR_ACCENT_3
    qcolor = QColor(color)

    # Todo: check if it is qcoreapplication indeed
    app = QCoreApplication.instance()

    _logger.info("Found application patches to be applied.")

    if app:
        app_palette = app.palette()
        app_palette.setColor(QPalette.Normal, QPalette.Link, qcolor)
        app.setPalette(app_palette)
    else:
        _logger.warn("No QCoreApplication instance found. "
                     "Application patches not applied. "
                     "You have to call load_stylesheet function after "
                     "instantiation of QApplication to take effect. ")


def _load_stylesheet(qt_api='', palette=None):
    """
    Load the stylesheet based on QtPy abstraction layer environment variable.

    If the argument is not passed, it uses the current QT_API environment
    variable to make the imports of Qt bindings. If passed, it sets this
    variable then make the imports.

    Args:
        qt_api (str): qt binding name to set QT_API environment variable.
                      Default is ''. Possible values are pyside, pyside2
                      pyqt4, pyqt5. Not case sensitive.
        palette (Palette): Palette class that inherits from Palette.

    Note:
        - Note that the variable QT_API is read when first imported. So,
          pay attention to the import order.
        - If you are using another abstraction layer, i.e PyQtGraph to do
          imports on Qt things you must set both to use the same Qt
          binding (PyQt, PySide).
        - OS, binding and binding version number, and application specific
          patches are applied in this order.

    Returns:
        str: stylesheet string (css).
    """

    if qt_api:
        os.environ['QT_API'] = qt_api

    # Import is made after setting QT_API
    from qtpy.QtCore import QCoreApplication, QFile, QTextStream
    from qtpy.QtGui import QColor, QPalette
    from qtpy import QT_VERSION

    # Then we import resources - binary qrc content
    if palette is None:
        from qdarkstyle.dark import style_rc
        palette = DarkPalette
    elif palette.ID == 'dark':
        from qdarkstyle.dark import style_rc
        palette = DarkPalette
    elif palette.ID == 'light':
        from qdarkstyle.light import style_rc
        palette = LightPalette
    else:
        print("Not recognized ID for palette! Exiting!")
        sys.exit(1)

    # Thus, by importing the binary we can access the resources
    package_dir = os.path.basename(PACKAGE_PATH)
    qss_rc_path = ":" + os.path.join(package_dir, palette.ID, QSS_FILE)

    _logger.debug("Reading QSS file in: %s" % qss_rc_path)

    # It gets the qss file from compiled style_rc that was imported,
    # not from the file QSS as we are using resources
    qss_file = QFile(qss_rc_path)

    if qss_file.exists():
        qss_file.open(QFile.ReadOnly | QFile.Text)
        text_stream = QTextStream(qss_file)
        stylesheet = text_stream.readAll()
        _logger.info("QSS file sucessfuly loaded.")
    else:
        stylesheet = ""
        # Todo: check this raise type and add to docs
        raise FileNotFoundError("Unable to find QSS file '{}' "
                                "in resources.".format(qss_rc_path))

    _logger.debug("Checking patches for being applied.")

    # Todo: check execution order for these functions
    # 1. Apply OS specific patches
    stylesheet += _apply_os_patches(palette)

    # 2. Apply binding specific patches
    stylesheet += _apply_binding_patches()

    # 3. Apply binding version specific patches
    stylesheet += _apply_version_patches(QT_VERSION)

    # 4. Apply palette fix. See issue #139
    _apply_application_patches(QCoreApplication, QPalette, QColor, palette)

    return stylesheet


def load_stylesheet(*args, **kwargs):
    """
    Load the stylesheet. Takes care of importing the rc module.

    Args:
        pyside (bool): True to load the PySide (or PySide2) rc file,
                       False to load the PyQt4 (or PyQt5) rc file.
                       Default is False.
        or

        qt_api (str): Qt binding name to set QT_API environment variable.
                      Default is '', i.e PyQt5 the default QtPy binding.
                      Possible values are pyside, pyside2 pyqt4, pyqt5.
                      Not case sensitive.

        or

        palette (Palette): Class (not instance) that inherits from Palette.

    Raises:
        TypeError: If arguments do not match: type, keyword name nor quantity.

    Returns:
        str: the stylesheet string.
    """

    stylesheet = ""
    arg = None

    try:
        arg = args[0]
    except IndexError:
        # It is already none
        pass

    # Get palette
    palette = kwargs.get('palette', None)

    # Number of arguments are wrong
    if (kwargs and args) or len(args) > 2 or len(kwargs) > 2:
        raise TypeError("load_stylesheet() takes zero, one or two arguments: "
                        "(new) string type qt_api='pyqt5' or "
                        "(old) boolean type pyside='False' or "
                        "(new) palette type palette=Palette.")

    # No arguments
    if not kwargs and not args:
        stylesheet = _load_stylesheet(qt_api='pyqt5')

    # Old API arguments
    elif 'pyside' in kwargs or isinstance(arg, bool):
        pyside = kwargs.get('pyside', arg)

        if pyside:
            stylesheet = _load_stylesheet(qt_api='pyside2', palette=palette)
            if not stylesheet:
                stylesheet = _load_stylesheet(qt_api='pyside', palette=palette)

        else:
            stylesheet = _load_stylesheet(qt_api='pyqt5', palette=palette)
            if not stylesheet:
                stylesheet = _load_stylesheet(qt_api='pyqt4', palette=palette)

        # Deprecation warning only for old API
        warnings.warn(DEPRECATION_MSG, DeprecationWarning)

    # New API arguments
    elif 'qt_api' in kwargs or isinstance(arg, str):
        qt_api = kwargs.get('qt_api', arg)
        stylesheet = _load_stylesheet(qt_api=qt_api, palette=palette)

    # Palette arg
    elif 'palette' in kwargs or issubclass(arg, Palette):
        palette_arg = kwargs.get('palette', arg)
        stylesheet = _load_stylesheet(palette=palette_arg)

    # Wrong API arguments name or type
    else:
        raise TypeError("load_stylesheet() takes only zero, one or two arguments: "
                        "(new) string type qt_api='pyqt5' or "
                        "(new) palette type palette=Palette or "
                        "(old) boolean type pyside='False'.")

    return stylesheet


def load_stylesheet_pyside():
    """
    Load the stylesheet for use in a PySide application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyside')


def load_stylesheet_pyside2():
    """
    Load the stylesheet for use in a PySide2 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyside2')


def load_stylesheet_pyqt():
    """
    Load the stylesheet for use in a PyQt4 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyqt4')


def load_stylesheet_pyqt5():
    """
    Load the stylesheet for use in a PyQt5 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyqt5')


# Deprecation Warning --------------------------------------------------------


def load_stylesheet_from_environment(is_pyqtgraph=False):
    """
    Load the stylesheet from QT_API (or PYQTGRAPH_QT_LIB) environment variable.

    Args:
        is_pyqtgraph (bool): True if it is to be set using PYQTGRAPH_QT_LIB.

    Raises:
        KeyError: if PYQTGRAPH_QT_LIB does not exist.

    Returns:
        str: the stylesheet string.
    """
    warnings.warn(DEPRECATION_MSG, DeprecationWarning)

    if is_pyqtgraph:
        stylesheet = _load_stylesheet(qt_api=os.environ.get('PYQTGRAPH_QT_LIB', None))
    else:
        stylesheet = _load_stylesheet()

    return stylesheet


# Deprecated ----------------------------------------------------------------
