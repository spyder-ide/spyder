# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Qt utilities"""

# Standard library imports
import os
import os.path as osp
import re
import sys
import logging

# Third party imports
from qtpy.compat import to_qvariant, from_qvariant
from qtpy.QtCore import (QEvent, QLibraryInfo, QLocale, QObject, Qt, QTimer,
                         QTranslator, Signal, Slot)
from qtpy.QtGui import QIcon, QKeyEvent, QKeySequence, QPixmap
from qtpy.QtWidgets import (QAction, QApplication, QHBoxLayout, QLabel,
                            QLineEdit, QMenu, QStyle, QToolBar, QToolButton,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import get_image_path, running_in_mac_app
from spyder.config.gui import get_shortcut
from spyder.utils import programs
from spyder.utils import icon_manager as ima
from spyder.utils.icon_manager import get_icon, get_std_icon
from spyder.py3compat import is_text_string, to_text_string

# Note: How to redirect a signal from widget *a* to widget *b* ?
# ----
# It has to be done manually:
#  * typing 'SIGNAL("clicked()")' works
#  * typing 'signalstr = "clicked()"; SIGNAL(signalstr)' won't work
# Here is an example of how to do it:
# (self.listwidget is widget *a* and self is widget *b*)
#    self.connect(self.listwidget, SIGNAL('option_changed'),
#                 lambda *args: self.emit(SIGNAL('option_changed'), *args))
logger = logging.getLogger(__name__)


def get_image_label(name, default="not_found.png"):
    """Return image inside a QLabel object"""
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label


class MacApplication(QApplication):
    """Subclass to be able to open external files with our Mac app"""
    sig_open_external_file = Signal(str)

    def __init__(self, *args):
        QApplication.__init__(self, *args)

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            fname = str(event.file())
            self.sig_open_external_file.emit(fname)
        return QApplication.event(self, event)


def qapplication(translate=True, test_time=3):
    """
    Return QApplication instance
    Creates it if it doesn't already exist

    test_time: Time to maintain open the application when testing. It's given
    in seconds
    """
    if running_in_mac_app():
        SpyderApplication = MacApplication
    else:
        SpyderApplication = QApplication

    app = SpyderApplication.instance()
    if app is None:
        # Set Application name for Gnome 3
        # https://groups.google.com/forum/#!topic/pyside/24qxvwfrRDs
        app = SpyderApplication(['Spyder'])

        # Set application name for KDE (See issue 2207)
        app.setApplicationName('Spyder')
    if translate:
        install_translator(app)

    test_ci = os.environ.get('TEST_CI_WIDGETS', None)
    if test_ci is not None:
        timer_shutdown = QTimer(app)
        timer_shutdown.timeout.connect(app.quit)
        timer_shutdown.start(test_time*1000)
    return app


def file_uri(fname):
    """Select the right file uri scheme according to the operating system"""
    if os.name == 'nt':
        # Local file
        if re.search(r'^[a-zA-Z]:', fname):
            return 'file:///' + fname
        # UNC based path
        else:
            return 'file://' + fname
    else:
        return 'file://' + fname


QT_TRANSLATOR = None
def install_translator(qapp):
    """Install Qt translator to the QApplication instance"""
    global QT_TRANSLATOR
    if QT_TRANSLATOR is None:
        qt_translator = QTranslator()
        if qt_translator.load("qt_"+QLocale.system().name(),
                      QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            QT_TRANSLATOR = qt_translator # Keep reference alive
    if QT_TRANSLATOR is not None:
        qapp.installTranslator(QT_TRANSLATOR)


def keybinding(attr):
    """Return keybinding"""
    ks = getattr(QKeySequence, attr)
    return from_qvariant(QKeySequence.keyBindings(ks)[0], str)


def _process_mime_path(path, extlist):
    if path.startswith(r"file://"):
        if os.name == 'nt':
            # On Windows platforms, a local path reads: file:///c:/...
            # and a UNC based path reads like: file://server/share
            if path.startswith(r"file:///"): # this is a local path
                path=path[8:]
            else: # this is a unc path
                path = path[5:]
        else:
            path = path[7:]
    path = path.replace('%5C' , os.sep)  # Transforming backslashes
    if osp.exists(path):
        if extlist is None or osp.splitext(path)[1] in extlist:
            return path


def mimedata2url(source, extlist=None):
    """
    Extract url list from MIME data
    extlist: for example ('.py', '.pyw')
    """
    pathlist = []
    if source.hasUrls():
        for url in source.urls():
            path = _process_mime_path(to_text_string(url.toString()), extlist)
            if path is not None:
                pathlist.append(path)
    elif source.hasText():
        for rawpath in to_text_string(source.text()).splitlines():
            path = _process_mime_path(rawpath, extlist)
            if path is not None:
                pathlist.append(path)
    if pathlist:
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


def create_toolbutton(parent, text=None, shortcut=None, icon=None, tip=None,
                      toggled=None, triggered=None,
                      autoraise=True, text_beside_icon=False):
    """Create a QToolButton"""
    button = QToolButton(parent)
    if text is not None:
        button.setText(text)
    if icon is not None:
        if is_text_string(icon):
            icon = get_icon(icon)
        button.setIcon(icon)
    if text is not None or tip is not None:
        button.setToolTip(text if tip is None else tip)
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(autoraise)
    if triggered is not None:
        button.clicked.connect(triggered)
    if toggled is not None:
        button.toggled.connect(toggled)
        button.setCheckable(True)
    if shortcut is not None:
        button.setShortcut(shortcut)
    return button


def action2button(action, autoraise=True, text_beside_icon=False, parent=None):
    """Create a QToolButton directly from a QAction object"""
    if parent is None:
        parent = action.parent()
    button = QToolButton(parent)
    button.setDefaultAction(action)
    button.setAutoRaise(autoraise)
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    return button


def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)


def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None, menurole=None,
                  context=Qt.WindowShortcut):
    """Create a QAction"""
    action = SpyderAction(text, parent)
    if triggered is not None:
        action.triggered.connect(triggered)
    if toggled is not None:
        action.toggled.connect(toggled)
        action.setCheckable(True)
    if icon is not None:
        if is_text_string(icon):
            icon = get_icon(icon)
        action.setIcon(icon)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if data is not None:
        action.setData(to_qvariant(data))
    if menurole is not None:
        action.setMenuRole(menurole)

    # Workround for Mac because setting context=Qt.WidgetShortcut
    # there doesn't have any effect
    if sys.platform == 'darwin':
        action._shown_shortcut = None
        if context == Qt.WidgetShortcut:
            if shortcut is not None:
                action._shown_shortcut = shortcut
            else:
                # This is going to be filled by
                # main.register_shortcut
                action._shown_shortcut = 'missing'
        else:
            if shortcut is not None:
                action.setShortcut(shortcut)
            action.setShortcutContext(context)
    else:
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.setShortcutContext(context)

    return action


def add_shortcut_to_tooltip(action, context, name):
    """Add the shortcut associated with a given action to its tooltip"""
    action.setToolTip(action.toolTip() + ' (%s)' %
                      get_shortcut(context=context, name=name))


def add_actions(target, actions, insert_before=None):
    """Add actions to a QMenu or a QToolBar."""
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
            if isinstance(action, SpyderAction):
                if isinstance(target, QMenu) or not isinstance(target, QToolBar):
                    try:
                        action = action.no_icon_action
                    except RuntimeError:
                        continue
            if insert_before is None:
                # This is needed in order to ignore adding an action whose
                # wrapped C/C++ object has been deleted. See issue 5074
                try:
                    target.addAction(action)
                except RuntimeError:
                    continue
            else:
                target.insertAction(insert_before, action)
        previous_action = action


def get_item_user_text(item):
    """Get QTreeWidgetItem user role string"""
    return from_qvariant(item.data(0, Qt.UserRole), to_text_string)


def set_item_user_text(item, text):
    """Set QTreeWidgetItem user role string"""
    item.setData(0, Qt.UserRole, to_qvariant(text))


def create_bookmark_action(parent, url, title, icon=None, shortcut=None):
    """Create bookmark action"""

    @Slot()
    def open_url():
        return programs.start_file(url)

    return create_action( parent, title, shortcut=shortcut, icon=icon,
                          triggered=open_url)


def create_module_bookmark_actions(parent, bookmarks):
    """
    Create bookmark actions depending on module installation:
    bookmarks = ((module_name, url, title), ...)
    """
    actions = []
    for key, url, title in bookmarks:
        # Create actions for scientific distros only if Spyder is installed
        # under them
        create_act = True
        if key == 'winpython':
            if not programs.is_module_installed(key):
                create_act = False
        if create_act:
            act = create_bookmark_action(parent, url, title)
            actions.append(act)
    return actions


def create_program_action(parent, text, name, icon=None, nt_name=None):
    """Create action to run a program"""
    if is_text_string(icon):
        icon = get_icon(icon)
    if os.name == 'nt' and nt_name is not None:
        name = nt_name
    path = programs.find_program(name)
    if path is not None:
        return create_action(parent, text, icon=icon,
                             triggered=lambda: programs.run_program(name))


def create_python_script_action(parent, text, icon, package, module, args=[]):
    """Create action to run a GUI based Python script"""
    if is_text_string(icon):
        icon = get_icon(icon)
    if programs.python_script_exists(package, module):
        return create_action(parent, text, icon=icon,
                             triggered=lambda:
                             programs.run_python_script(package, module, args))


class DialogManager(QObject):
    """
    Object that keep references to non-modal dialog boxes for another QObject,
    typically a QMainWindow or any kind of QWidget
    """
    def __init__(self):
        QObject.__init__(self)
        self.dialogs = {}

    def show(self, dialog):
        """Generic method to show a non-modal dialog and keep reference
        to the Qt C++ object"""
        for dlg in list(self.dialogs.values()):
            if to_text_string(dlg.windowTitle()) \
               == to_text_string(dialog.windowTitle()):
                dlg.show()
                dlg.raise_()
                break
        else:
            dialog.show()
            self.dialogs[id(dialog)] = dialog
            dialog.accepted.connect(
                              lambda eid=id(dialog): self.dialog_finished(eid))
            dialog.rejected.connect(
                              lambda eid=id(dialog): self.dialog_finished(eid))

    def dialog_finished(self, dialog_id):
        """Manage non-modal dialog boxes"""
        return self.dialogs.pop(dialog_id)

    def close_all(self):
        """Close all opened dialog boxes"""
        for dlg in list(self.dialogs.values()):
            dlg.reject()


def get_filetype_icon(fname):
    """Return file type icon"""
    ext = osp.splitext(fname)[1]
    if ext.startswith('.'):
        ext = ext[1:]
    return get_icon( "%s.png" % ext, ima.icon('FileIcon') )


class SpyderAction(QAction):
    """Spyder QAction class wrapper to handle cross platform patches."""

    def __init__(self, *args, **kwargs):
        """Spyder QAction class wrapper to handle cross platform patches."""
        super(SpyderAction, self).__init__(*args, **kwargs)
        self._action_no_icon = None

        if sys.platform == 'darwin':
            self._action_no_icon = QAction(*args, **kwargs)
            self._action_no_icon.setIcon(QIcon())
            self._action_no_icon.triggered.connect(self.triggered)
            self._action_no_icon.toggled.connect(self.toggled)
            self._action_no_icon.changed.connect(self.changed)
            self._action_no_icon.hovered.connect(self.hovered)
        else:
            self._action_no_icon = self

    def __getattribute__(self, name):
        """Intercept method calls and apply to both actions, except signals."""
        attr = super(SpyderAction, self).__getattribute__(name)

        if hasattr(attr, '__call__') and name not in ['triggered', 'toggled',
                                                      'changed', 'hovered']:
            def newfunc(*args, **kwargs):
                result = attr(*args, **kwargs)
                if name not in ['setIcon']:
                    action_no_icon = self.__dict__['_action_no_icon']
                    attr_no_icon = super(QAction,
                                         action_no_icon).__getattribute__(name)
                    attr_no_icon(*args, **kwargs)
                return result
            return newfunc
        else:
            return attr

    @property
    def no_icon_action(self):
        """Return the action without an Icon."""
        return self._action_no_icon


class ShowStdIcons(QWidget):
    """
    Dialog showing standard icons
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
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
    sys.exit(app.exec_())


def calc_tools_spacing(tools_layout):
    """
    Return a spacing (int) or None if we don't have the appropriate metrics
    to calculate the spacing.

    We're trying to adapt the spacing below the tools_layout spacing so that
    the main_widget has the same vertical position as the editor widgets
    (which have tabs above).

    The required spacing is

        spacing = tabbar_height - tools_height + offset

    where the tabbar_heights were empirically determined for a combination of
    operating systems and styles. Offsets were manually adjusted, so that the
    heights of main_widgets and editor widgets match. This is probably
    caused by a still not understood element of the layout and style metrics.
    """
    metrics = {  # (tabbar_height, offset)
        'nt.fusion': (32, 0),
        'nt.windowsvista': (21, 3),
        'nt.windowsxp': (24, 0),
        'nt.windows': (21, 3),
        'posix.breeze': (28, -1),
        'posix.oxygen': (38, -2),
        'posix.qtcurve': (27, 0),
        'posix.windows': (26, 0),
        'posix.fusion': (32, 0),
    }

    style_name = qapplication().style().property('name')
    key = '%s.%s' % (os.name, style_name)

    if key in metrics:
        tabbar_height, offset = metrics[key]
        tools_height = tools_layout.sizeHint().height()
        spacing = tabbar_height - tools_height + offset
        return max(spacing, 0)


def create_plugin_layout(tools_layout, main_widget=None):
    """
    Returns a layout for a set of controls above a main widget. This is a
    standard layout for many plugin panes (even though, it's currently
    more often applied not to the pane itself but with in the one widget
    contained in the pane.

    tools_layout: a layout containing the top toolbar
    main_widget: the main widget. Can be None, if you want to add this
        manually later on.
    """
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    spacing = calc_tools_spacing(tools_layout)
    if spacing is not None:
        layout.setSpacing(spacing)

    layout.addLayout(tools_layout)
    if main_widget is not None:
        layout.addWidget(main_widget)
    return layout


MENU_SEPARATOR = None


if __name__ == "__main__":
    show_std_icons()
