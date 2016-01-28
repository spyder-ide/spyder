# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

if os.environ['QT_API'] == 'pyqt5':
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView      # analysis:ignore
    from PyQt5.QtWebKit import QWebSettings                   # analysis:ignore
elif os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtWebKit import (QWebPage, QWebView,           # analysis:ignore
                                QWebSettings)
else:
    from PySide.QtWebKit import *                             # analysis:ignore
