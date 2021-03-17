# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Utility functions for the Spyder application."""

# Standard library imports
import glob
import logging
import os
import os.path as osp
import re
import sys

# Third-party imports
import psutil
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

# Local imports
from spyder.config.base import (DEV, get_conf_path, get_debug_level,
                                running_under_pytest)
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.qthelpers import file_uri
from spyder.utils.external.dafsa.dafsa import DAFSA

# For spyder-ide/spyder#7447.
try:
    from qtpy.QtQuick import QQuickWindow, QSGRendererInterface
except Exception:
    QQuickWindow = QSGRendererInterface = None


root_logger = logging.getLogger()
FILTER_NAMES = os.environ.get('SPYDER_FILTER_LOG', "").split(',')
FILTER_NAMES = [f.strip() for f in FILTER_NAMES]


class Spy:
    """
    This is used to inject a 'spy' object in the internal console
    namespace to inspect Spyder internals.

    Attributes:
        app       Reference to main QApplication object
        window    Reference to spyder.MainWindow widget
    """
    def __init__(self, app, window):
        self.app = app
        self.window = window

    def __dir__(self):
        return (list(self.__dict__.keys()) +
                [x for x in dir(self.__class__) if x[0] != '_'])


def get_python_doc_path():
    """
    Return Python documentation path
    (Windows: return the PythonXX.chm path if available)
    """
    if os.name == 'nt':
        doc_path = osp.join(sys.prefix, "Doc")
        if not osp.isdir(doc_path):
            return
        python_chm = [path for path in os.listdir(doc_path)
                      if re.match(r"(?i)Python[0-9]{3,6}.chm", path)]
        if python_chm:
            return file_uri(osp.join(doc_path, python_chm[0]))
    else:
        vinf = sys.version_info
        doc_path = '/usr/share/doc/python%d.%d/html' % (vinf[0], vinf[1])
    python_doc = osp.join(doc_path, "index.html")
    if osp.isfile(python_doc):
        return file_uri(python_doc)


def set_opengl_implementation(option):
    """
    Set the OpenGL implementation used by Spyder.

    See spyder-ide/spyder#7447 for the details.
    """
    if option == 'software':
        QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
        if QQuickWindow is not None:
            QQuickWindow.setSceneGraphBackend(QSGRendererInterface.Software)
    elif option == 'desktop':
        QCoreApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
        if QQuickWindow is not None:
            QQuickWindow.setSceneGraphBackend(QSGRendererInterface.OpenGL)
    elif option == 'gles':
        QCoreApplication.setAttribute(Qt.AA_UseOpenGLES)
        if QQuickWindow is not None:
            QQuickWindow.setSceneGraphBackend(QSGRendererInterface.OpenGL)


def setup_logging(cli_options):
    """Setup logging with cli options defined by the user."""
    if cli_options.debug_info or get_debug_level() > 0:
        levels = {2: logging.INFO, 3: logging.DEBUG}
        log_level = levels[get_debug_level()]
        log_format = '%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s'

        console_filters = cli_options.filter_log.split(',')
        console_filters = [x.strip() for x in console_filters]
        console_filters = console_filters + FILTER_NAMES
        console_filters = [x for x in console_filters if x != '']

        handlers = [logging.StreamHandler()]
        if cli_options.debug_output == 'file':
            log_file = 'spyder-debug.log'
            handlers.append(
                logging.FileHandler(filename=log_file, mode='w+')
            )
        else:
            log_file = None

        match_func = lambda x: True
        if console_filters != [''] and len(console_filters) > 0:
            dafsa = DAFSA(console_filters)
            match_func = lambda x: (dafsa.lookup(x, stop_on_prefix=True)
                                    is not None)

        formatter = logging.Formatter(log_format)

        class ModuleFilter(logging.Filter):
            """Filter messages based on module name prefix."""

            def filter(self, record):
                return match_func(record.name)

        filter = ModuleFilter()
        root_logger.setLevel(log_level)
        for handler in handlers:
            handler.addFilter(filter)
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
            root_logger.addHandler(handler)


def delete_lsp_log_files():
    """Delete previous dead Spyder instances LSP log files."""
    regex = re.compile(r'.*_.*_(\d+)[.]log')
    files = glob.glob(osp.join(get_conf_path('lsp_logs'), '*.log'))
    for f in files:
        match = regex.match(f)
        if match is not None:
            pid = int(match.group(1))
            if not psutil.pid_exists(pid):
                os.remove(f)


def qt_message_handler(msg_type, msg_log_context, msg_string):
    """
    Qt warning messages are intercepted by this handler.

    On some operating systems, warning messages might be displayed
    even if the actual message does not apply. This filter adds a
    blacklist for messages that are being printed for no apparent
    reason. Anything else will get printed in the internal console.

    In DEV mode, all messages are printed.
    """
    BLACKLIST = [
        'QMainWidget::resizeDocks: all sizes need to be larger than 0',
    ]
    if DEV or msg_string not in BLACKLIST:
        print(msg_string)  # spyder: test-skip


def create_splash_screen():
    """Create splash screen."""
    if not running_under_pytest():
        splash = QSplashScreen(QPixmap(get_image_path('splash')))
        splash_font = splash.font()
        splash_font.setPixelSize(10)
        splash.setFont(splash_font)
    else:
        splash = None

    return splash
