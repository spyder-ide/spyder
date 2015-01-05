# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os
import sys

if os.environ['QT_API'] == 'pyqt':
    if "PyQt4" in sys.modules:
        from PyQt4.QtWebKit import QWebPage, QWebView, QWebSettings
    elif "PyQt5" in sys.modules:
        from PyQt5.QtWebKitWidgets import QWebPage, QWebView
        from PyQt5.QtWebKit import QWebSettings

else:
    from PySide.QtWebKit import *  # analysis:ignore