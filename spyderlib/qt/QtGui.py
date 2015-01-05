# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os
import sys

if os.environ['QT_API'] == 'pyqt':
    if "PyQt4" in sys.modules:
        from PyQt4.QtGui import QApplication, QMainWindow, QWidget, QLabel
        from PyQt4.QtGui import QDockWidget, QShortcut, QCursor, QDialog, QListWidget
        from PyQt4.QtGui import QListWidgetItem, QVBoxLayout, QStackedWidget, QListView
        from PyQt4.QtGui import QHBoxLayout, QDialogButtonBox, QCheckBox, QMessageBox
        from PyQt4.QtGui import QLabel, QLineEdit, QSpinBox, QPushButton
        from PyQt4.QtGui import QFontComboBox, QGroupBox, QComboBox, QColor, QGridLayout
        from PyQt4.QtGui import QTabWidget, QRadioButton, QButtonGroup, QSplitter
        from PyQt4.QtGui import QStyleFactory, QScrollArea, QAction, QPrinter
        from PyQt4.QtGui import QPrintDialog, QToolBar, QActionGroup
        from PyQt4.QtGui import QInputDialog, QMenu, QAbstractPrintDialog, QKeySequence
        from PyQt4.QtGui import QPrintPreviewDialog, QFontDialog, QSizePolicy, QToolButton
        from PyQt4.QtGui import QFormLayout, QStackedWidget, QFrame, QItemDelegate
        from PyQt4.QtGui import QTableView, QStackedWidget, QDesktopServices, QStyle
        from PyQt4.QtGui import QIcon, QKeyEvent, QPixmap, QFont
        from PyQt4.QtGui import QCursor, QTextCursor, QTextEdit, QTextCharFormat
        from PyQt4.QtGui import QToolTip, QPlainTextEdit, QPalette, QTextOption
        from PyQt4.QtGui import QMouseEvent, QTextFormat, QClipboard, QPainter
        from PyQt4.QtGui import QBrush, QTextDocument, QTextBlockUserData, QIntValidator
        from PyQt4.QtGui import QSyntaxHighlighter, QDoubleValidator, QAbstractItemDelegate, QProgressBar
        from PyQt4.QtGui import QColorDialog, QCompleter, QDateEdit, QDateTimeEdit
        from PyQt4.QtGui import QTreeWidgetItem, QFileSystemModel, QDrag, QSortFilterProxyModel
        from PyQt4.QtGui import QSpacerItem, QFileIconProvider, QHeaderView, QAbstractItemView
        from PyQt4.QtGui import QTabBar, QFontDatabase, QSplashScreen
        from PyQt4.QtGui import QFileDialog, QTreeWidget, QTreeView
        from PyQt4.QtGui import QStylePainter, QStyleOptionFrame,QPaintEvent
    elif "PyQt5" in sys.modules:
        from PyQt5.QtGui import QCursor
        from PyQt5.QtGui import QColor
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtGui import QIcon, QKeyEvent, QPixmap, QFont
        from PyQt5.QtGui import QCursor, QTextCursor
        from PyQt5.QtGui import QTextCharFormat
        from PyQt5.QtGui import QPalette, QTextOption
        from PyQt5.QtGui import QMouseEvent, QTextFormat, QClipboard, QPainter
        from PyQt5.QtGui import QBrush, QTextDocument, QTextBlockUserData, QIntValidator
        from PyQt5.QtGui import QSyntaxHighlighter, QDoubleValidator
        from PyQt5.QtGui import QDrag 
        from PyQt5.QtGui import QFontDatabase, QPaintEvent
        from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel
        from PyQt5.QtWidgets import QDockWidget, QShortcut
        from PyQt5.QtWidgets import QDialog, QListWidget
        from PyQt5.QtWidgets import QListWidgetItem, QVBoxLayout, QStackedWidget, QListView
        from PyQt5.QtWidgets import QHBoxLayout, QDialogButtonBox, QCheckBox, QMessageBox
        from PyQt5.QtWidgets import QLabel, QLineEdit, QSpinBox, QPushButton
        from PyQt5.QtWidgets import QFontComboBox, QGroupBox, QComboBox
        from PyQt5.QtWidgets import QGridLayout
        from PyQt5.QtWidgets import QTabWidget, QRadioButton, QButtonGroup, QSplitter
        from PyQt5.QtWidgets import QStyleFactory, QScrollArea, QAction
        from PyQt5.QtWidgets import QToolBar, QActionGroup
        from PyQt5.QtWidgets import QInputDialog, QMenu
        from PyQt5.QtWidgets import QFontDialog, QSizePolicy, QToolButton
        from PyQt5.QtWidgets import QFormLayout, QStackedWidget, QFrame, QItemDelegate
        from PyQt5.QtWidgets import QTableView, QStackedWidget
        from PyQt5.QtWidgets import QStyle
        from PyQt5.QtWidgets import QTextEdit
        from PyQt5.QtWidgets import QToolTip, QPlainTextEdit
        from PyQt5.QtWidgets import QProgressBar, QAbstractItemDelegate
        from PyQt5.QtWidgets import QColorDialog, QCompleter, QDateEdit, QDateTimeEdit
        from PyQt5.QtWidgets import QTreeWidgetItem, QFileSystemModel
        from PyQt5.QtWidgets import QSpacerItem, QFileIconProvider, QHeaderView, QAbstractItemView
        from PyQt5.QtWidgets import QTabBar, QSplashScreen
        from PyQt5.QtWidgets import QFileDialog, QTreeWidget, QTreeView
        from PyQt5.QtWidgets import QStylePainter, QStyleOptionFrame
        from PyQt5.QtCore import QSortFilterProxyModel
        from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QAbstractPrintDialog
        from PyQt5.QtPrintSupport import QPrintPreviewDialog

else:
    from PySide.QtGui import *  # analysis:ignore
