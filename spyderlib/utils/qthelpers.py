# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Qt utilities"""

import os.path as osp
import os, webbrowser

from PyQt4.QtGui import (QAction, QStyle, QWidget, QIcon, QApplication,
                         QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
                         QKeySequence, QToolButton, QKeyEvent, QMenu)
from PyQt4.QtCore import (SIGNAL, QVariant, QObject, Qt, QLocale, QTranslator,
                          QLibraryInfo)

# Local import
from spyderlib.config import get_icon, DATA_PATH
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

TRANSLATORS = []

def qapplication(translate=True):
    """
    Return QApplication instance
    Creates it if it doesn't already exist
    """
    if QApplication.startingUp():
        app = QApplication([])
        if translate:
            locale = QLocale.system().name()
            # Qt-specific translator
            qt_translator = QTranslator()
            TRANSLATORS.append(qt_translator) # Keep reference alive
            paths = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
            if qt_translator.load("qt_"+locale, paths):
                app.installTranslator(qt_translator)
            # Spyder-specific translator
            app_translator = QTranslator()
            TRANSLATORS.append(app_translator) # Keep reference alive
            if app_translator.load("spyder_"+locale, DATA_PATH):
                app.installTranslator(app_translator)
    else:
        app = QApplication.instance()
    return app

def translate(context, string):
    """Translation"""
    return QApplication.translate(context, string)

def keybinding(attr):
    """Return keybinding"""
    ks = getattr(QKeySequence, attr)
    return QKeySequence.keyBindings(ks)[0].toString()

def mimedata2url(source, extlist=None):
    """
    Extract url list from MIME data
    extlist: for example ('.py', '.pyw')
    """
    if source.hasUrls():
        pathlist = []
        for url in source.urls():
            path = unicode(url.toString())
            if path.startswith(r"file://"):
                if os.name == 'nt':
                    path = path[8:]
                else:
                    path = path[7:]
            if osp.exists(path):
                if extlist is None or osp.splitext(path)[1] in extlist:
                    pathlist.append(path)
        return pathlist

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
                      triggered=None, tip=None, toggled=None, shortcut=None,
                      autoraise=True, text_beside_icon=True):
    """Create a QToolButton"""
    button = QToolButton(parent)
    if text is not None:
        button.setText(text)
    if icon is not None:
        if isinstance(icon, (str, unicode)):
            icon = get_icon(icon)
        button.setIcon(icon)
    if text is not None or tip is not None:
        button.setToolTip(text if tip is None else tip)
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(autoraise)
    if triggered is not None:
        QObject.connect(button, SIGNAL('clicked()'), triggered)
    if toggled is not None:
        QObject.connect(button, SIGNAL("toggled(bool)"), toggled)
        button.setCheckable(True)
    if shortcut is not None:
        button.setShortcut(shortcut)
    return button

def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)

def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None,
                  context=Qt.WindowShortcut):
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
    #TODO: Hard-code all shortcuts and choose context=Qt.WidgetShortcut
    # (this will avoid calling shortcuts from another dockwidget
    #  since the context thing doesn't work quite well with these widgets)
    action.setShortcutContext(context)
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


def get_item_user_text(item):
    """Get QTreeWidgetItem user role string"""
    return unicode(item.data(0, Qt.UserRole).toString())

def set_item_user_text(item, text):
    """Set QTreeWidgetItem user role string"""
    item.setData(0, Qt.UserRole, QVariant(text))


def create_bookmark_action(parent, url, title, icon=None, shortcut=None):
    """Create bookmark action"""
    if icon is None:
        icon = get_icon('browser.png')
    if os.name == 'nt':
        callback = os.startfile
    else:
        callback = webbrowser.open
    return create_action( parent, title, shortcut=shortcut, icon=icon,
                          triggered=lambda u=url: callback(u) )

def create_module_bookmark_actions(parent, bookmarks):
    """
    Create bookmark actions depending on module installation:
    bookmarks = ((module_name, url, title), ...)
    """
    actions = []
    for key, url, title, icon in bookmarks:
        if programs.is_module_installed(key):
            act = create_bookmark_action(parent, url, title, get_icon(icon))
            actions.append(act)
    return actions
        
def create_program_action(parent, text, icon, name, nt_name=None):
    """Create action to run a program"""
    if os.name == 'nt':
        if nt_name is not None:
            name = nt_name
        name = programs.get_nt_program_name(name)
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
    app = qapplication()
    dialog = ShowStdIcons(None)
    dialog.show()
    import sys
    sys.exit(app.exec_())

if __name__ == "__main__":
    show_std_icons()