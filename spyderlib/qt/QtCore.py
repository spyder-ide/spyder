# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os
import sys


if os.environ['QT_API'] == 'pyqt':
    if "PyQt4" in sys.modules:
        from PyQt4.Qt import QSize, QByteArray, QUrl, QThread
        from PyQt4.Qt import QAbstractTableModel, QModelIndex
        from PyQt4.Qt import QObject, Qt, QLocale, QTranslator
        from PyQt4.Qt import QProcess, QTimer, QTextCodec
        from PyQt4.Qt import QEventLoop, QEvent, QPoint, QRect
        from PyQt4.Qt import QRegExp, QFileInfo, QMimeData, QDir
        from PyQt4.Qt import QMutexLocker, QMutex, QCoreApplication, QDateTime
        from PyQt4.Qt import QBasicTimer
        from PyQt4.QtCore import QLibraryInfo
        from PyQt4.QtCore import pyqtSignal as Signal  
        from PyQt4.QtCore import pyqtSlot as Slot  
        from PyQt4.QtCore import pyqtProperty as Property  
        from PyQt4.QtCore import QT_VERSION_STR as __version__
        from PyQt4.QtCore import QProcessEnvironment
        try:
            # PyQt <v4.6 (API #1)
            from PyQt4.Qt import QString
        except ImportError:
            # PyQt >=v4.6
            QString = None  
    elif "PyQt5" in sys.modules:
        from PyQt5.QtCore import QSize, QByteArray, QUrl, QThread
        from PyQt5.QtCore import QAbstractTableModel, QModelIndex
        from PyQt5.QtCore import QObject, Qt, QLocale, QTranslator
        from PyQt5.QtCore import QProcess, QTimer, QTextCodec
        from PyQt5.QtCore import QEventLoop, QEvent, QPoint, QRect
        from PyQt5.QtCore import QRegExp, QFileInfo, QMimeData, QDir
        from PyQt5.QtCore import QMutexLocker, QMutex, QCoreApplication, QDateTime
        from PyQt5.QtCore import QBasicTimer, QLibraryInfo
        from PyQt5.QtCore import pyqtSignal as Signal
        from PyQt5.QtCore import pyqtSlot as Slot
        from PyQt5.QtCore import pyqtProperty as Property
        from PyQt5.QtCore import QT_VERSION_STR as __version__
        from PyQt5.QtCore import QProcessEnvironment



else:
    import PySide.QtCore
    __version__ = PySide.QtCore.__version__  
    from PySide.QtCore import *  
