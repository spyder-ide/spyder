# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Qt utilities"""

import os.path as osp
import os, webbrowser, imp

from PyQt4.QtGui import (QAction, QStyle, QWidget, QIcon, QApplication,
                         QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
                         QKeySequence, QToolButton, QKeyEvent, QMenu)
from PyQt4.QtCore import SIGNAL, QVariant, QObject, Qt

# Local import
from spyderlib.config import get_icon
from spyderlib.utils import programs

# Note: How to redirect a signal from widget *a* to widget *b* ?
# ----
# It has to be done manually:
#  * typing 'SIGNAL("clicked()")' works
#  * typing 'signalstr = "clicked()"; SIGNAL(signalstr)' won't work
# Here is an example of how to do it:
# (self.listwidget is widget *a* and self is widget *b*)
#    self.connect(self.listwidget, SIGNAL('option_changed'),
#                 lambda *args: self.emit(SIGNAL('option_changed'), *args))

def translate(context, string):
    """Translation"""
    return QApplication.translate(context, string)

def keybinding(attr):
    """Return keybinding"""
    ks = getattr(QKeySequence, attr)
    return QKeySequence.keyBindings(ks)[0].toString()

def mimedata2url(source):
    """Extract url list from MIME data"""
    if source.hasUrls():
        paths = [unicode(url.toString()) for url in source.urls()]
        return [path[8:] for path in paths if path.startswith(r"file://") \
                and (path.endswith(".py") or path.endswith(".pyw"))]

def keyevent2tuple(event):
    """Convert QKeyEvent instance into a tuple"""
    return (event.type(), event.key(), event.modifiers(), event.text(),
            event.isAutoRepeat(), event.count())
    
def tuple2keyevent(past_event):
    """Convert tuple into a QKeyEvent instance"""
    return QKeyEvent(*past_event)

def restore_keyevent(event):
    if isinstance(event, tuple):
        _, key, modifiers, text, _, _ = event
        event = tuple2keyevent(event)
    else:
        text = event.text()
        modifiers = event.modifiers()
        key = event.key()
    ctrl = modifiers & Qt.ControlModifier
    shift = modifiers & Qt.ShiftModifier
    return event, text, key, ctrl, shift

def create_toolbutton(parent, icon=None, text=None,
                      triggered=None, tip=None, toggled=None):
    """Create a QToolButton"""
    button = QToolButton(parent)
    if text is not None:
        button.setText(text)
    if icon is not None:
        button.setIcon(icon)
    if text is not None or tip is not None:
        button.setToolTip(text if tip is None else tip)
    button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(True)
    if triggered is not None:
        QObject.connect(button, SIGNAL('clicked()'), triggered)
    if toggled is not None:
        QObject.connect(button, SIGNAL("toggled(bool)"), toggled)
        button.setCheckable(True)
    return button

def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)

def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None,
                  window_context=True):
    """Create a QAction"""
    action = QAction(text, parent)
    if triggered is not None:
        parent.connect(action, SIGNAL("triggered()"), triggered)
    if toggled is not None:
        parent.connect(action, SIGNAL("toggled(bool)"), toggled)
        action.setCheckable(True)
    if icon is not None:
        if isinstance(icon, (str, unicode)):
            icon = get_icon(icon)
        action.setIcon( icon )
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if data is not None:
        action.setData(QVariant(data))
    if window_context:
        action.setShortcutContext(Qt.WindowShortcut)
    else:
        #TODO: Hard-code all shortcuts and choose window_context=False
        # (this will avoid calling shortcuts from another dockwidget
        #  since the context thing doesn't work quite well with these)
        action.setShortcutContext(Qt.WidgetShortcut)
    return action

def add_actions(target, actions, insert_before=None):
    """Add actions to a menu"""
    previous_action = None
    target_actions = list(target.actions())
    if target_actions:
        previous_action = target_actions[-1]
        if previous_action.isSeparator():
            previous_action = None
    for action in actions:
        if (action is None) and (previous_action is not None):
            if insert_before is None:
                target.addSeparator()
            else:
                target.insertSeparator(insert_before)
        elif isinstance(action, QMenu):
            if insert_before is None:
                target.addMenu(action)
            else:
                target.insertMenu(insert_before, action)
        elif isinstance(action, QAction):
            if insert_before is None:
                target.addAction(action)
            else:
                target.insertAction(insert_before, action)
        previous_action = action

def add_bookmark(parent, menu, url, title, icon=None, shortcut=None):
    """Add bookmark to a menu"""
    if icon is None:
        icon = get_icon('browser.png')
    if os.name == 'nt':
        callback = os.startfile
    else:
        callback = webbrowser.open
    act = create_action( parent, title, shortcut=shortcut, icon=icon,
                         triggered=lambda u=url: callback(u) )
    menu.addAction(act)

def add_module_dependent_bookmarks(parent, menu, bookmarks):
    """
    Add bookmarks to a menu depending on module installation:
    bookmarks = ((module_name, url, title), ...)
    """
    for key, url, title, icon in bookmarks:
        try:
            imp.find_module(key)
            add_bookmark(parent, menu, url, title, get_icon(icon))
        except ImportError:
            pass
        
def create_program_action(parent, text, icon, name, nt_name=None):
    """Create action to run a program"""
    if os.name == 'nt':
        if nt_name is None:
            name += ".exe"
        else:
            name = nt_name
    if isinstance(icon, basestring):
        icon = get_icon(icon)
    if programs.is_program_installed(name):
        return create_action(parent, text, icon=icon,
                             triggered=lambda: programs.run_program(name))
        
def create_python_gui_script_action(parent, text, icon, package, module):
    """Create action to run a GUI based Python script"""
    if isinstance(icon, basestring):
        icon = get_icon(icon)
    if programs.is_python_gui_script_installed(package, module):
        return create_action(parent, text, icon=icon,
                             triggered=lambda:
                             programs.run_python_gui_script(package, module))
        
def get_std_icon(name, size=None):
    """Get standard platform icon
    Call 'show_std_icons()' for details"""
    if not name.startswith('SP_'):
        name = 'SP_'+name
    icon = QWidget().style().standardIcon( getattr(QStyle, name) )
    if size is None:
        return icon
    else:
        return QIcon( icon.pixmap(size, size) )

def get_filetype_icon(fname):
    """Return file type icon"""
    ext = osp.splitext(fname)[1]
    if ext.startswith('.'):
        ext = ext[1:]
    return get_icon( "%s.png" % ext, get_std_icon('FileIcon') )


class ShowStdIcons(QWidget):
    """
    Dialog showing standard icons
    """
    def __init__(self, parent):
        super(ShowStdIcons, self).__init__(parent)
        layout = QHBoxLayout()
        row_nb = 14
        cindex = 0
        for child in dir(QStyle):
            if child.startswith('SP_'):
                if cindex == 0:
                    col_layout = QVBoxLayout()
                icon_layout = QHBoxLayout()
                icon = get_std_icon(child)
                label = QLabel()
                label.setPixmap(icon.pixmap(32, 32))
                icon_layout.addWidget( label )
                icon_layout.addWidget( QLineEdit(child.replace('SP_', '')) )
                col_layout.addLayout(icon_layout)
                cindex = (cindex+1) % row_nb
                if cindex == 0:
                    layout.addLayout(col_layout)                    
        self.setLayout(layout)
        self.setWindowTitle('Standard Platform Icons')
        self.setWindowIcon(get_std_icon('TitleBarMenuButton'))

def show_std_icons():
    """
    Show all standard Icons
    """
    import sys
    app = QApplication(sys.argv)
    dialog = ShowStdIcons(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    show_std_icons()