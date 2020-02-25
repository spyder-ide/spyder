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

# Local imports
from spyder.config.base import DEV, get_conf_path, get_debug_level
from spyder.utils.qthelpers import file_uri

# For spyder-ide/spyder#7447.
try:
    from qtpy.QtQuick import QQuickWindow, QSGRendererInterface
except Exception:
    QQuickWindow = QSGRendererInterface = None


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

        if cli_options.debug_output == 'file':
            log_file = 'spyder-debug.log'
        else:
            log_file = None

        logging.basicConfig(level=log_level,
                            format=log_format,
                            filename=log_file,
                            filemode='w+')


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
