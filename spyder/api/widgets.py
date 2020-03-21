# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.widgets
==================
Here, 'spyder widgets' are Qt main windows that should be used to encapsulate
the main interface of Spyder dockable plugins.
"""

# Standard library imports
from collections import OrderedDict
import sys
import textwrap
import uuid

# Third party imports
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QAction, QHBoxLayout, QMainWindow, QSizePolicy,
                            QToolBar, QToolButton, QWidget)
import qdarkstyle

# Local imports
from spyder.api.mixins import SpyderMenu, SpyderToolBarMixin, SpyderWidgetMixin
from spyder.api.translations import get_translation
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_waitspinner,
                                    set_menu_icons)
from spyder.widgets.dock import SpyderDockWidget
from spyder.widgets.tabs import Tabs


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class PluginMainWidgetActions:
    ClosePane = 'close_pane'
    DockPane = 'dock_pane'
    UndockPane = 'undock_pane'


class PluginMainWidgetMenus:
    Context = 'context_menu'
    Options = 'options_menu'


class PluginMainWidgetWidgets:
    CornerWidget = 'corner_widget'
    MainToolbar = 'main_toolbar_widget'
    OptionsToolButton = 'options_button_widget'
    Spinner = 'spinner_widget'


class OptionsMenuSections:
    Top = 'top_section'
    Bottom = 'bottom_section'


class ToolBarLocations:
    Top = 'top_location'
    Bottom = 'bottom_location'


# --- Spyder Widgets
# ----------------------------------------------------------------------------
class SpyderWindowWidget(QMainWindow):
    """
    MainWindow subclass that contains a Spyder Plugin.
    """

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

        # Setting interface theme
        if is_dark_interface():
            self.setStyleSheet(qdarkstyle.load_stylesheet())

    def closeEvent(self, event):
        """
        Override Qt method.
        """
        # TODO:
        # self.plugin.set_ancestor(self.plugin.main)
        # self.plugin.switch_to_plugin()
        super().closeEvent(event)


class MainCornerWidget(QWidget):
    """
    Corner widget to hold options menu, spinner and additional options.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._widgets = {}
        self.setObjectName(PluginMainWidgetWidgets.CornerWidget)

        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        # FIXME: Decide on a number
        spacing = 2
        self._layout.setSpacing(2)

        # left, top, right, bottom
        self._layout.setContentsMargins(spacing, 0, spacing, spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def add_widget(self, name, widget):
        """
        Add a widget to the left of the last widget added to the corner.
        """
        if name in self._widgets:
            raise Exception('Wigdet with name "{}" already added. '
                            'Current names are: {}'.format(
                                name, list(self._widgets.keys())))

        self._widgets[name] = widget
        self._layout.insertWidget(0, widget)

    def get_widget(self, name):
        """
        Return a widget by name.
        """
        if name in self._widgets:
            return self._widgets[name]


class MainWidgetMenu(SpyderMenu):
    """
    This menu fixes the bottom section of the options menu.
    """

    def _render(self):
        """
        Create the menu prior to showing it. This takes into account sections
        and location of menus. It also hides consecutive separators if found.
        """
        if self._dirty:
            self.clear()
            bottom = OptionsMenuSections.Bottom
            actions = []
            for section in self._sections:
                for (sec, action) in self._actions:
                    if sec == section and sec != bottom:
                        actions.append(action)

                actions.append(None)

            # Add bottom actions
            for (sec, action) in self._actions:
                if sec == bottom:
                    actions.append(action)

            # TODO: Remove any consecutive Nones
            add_actions(self, actions)

            self._ordered_actions = actions
            self._dirty = False


class ApplicationMenu(SpyderMenu):
    """
    Spyder Main Window application Menus.

    This class provides application menus with some predefined functionality
    and section definition.
    """


class ApplicationToolBar(QToolBar):
    """
    Spyder Main application ToolBar.

    This class provides application toolbars with some predefined
    functionality and section definition.
    """


class MainWidgetToolbar(QToolBar):
    """
    Spyder Widget toolbar class.

    A toolbar used in Spyder Widgets to add internal toolbars
    to their interface.
    """

    def __init__(self, parent=None, areas=Qt.TopToolBarArea,
                 corner_widget=None):
        super().__init__(parent)
        self._section_items = OrderedDict()
        self._set_corner_widget(corner_widget)
        self._icon_size = QSize(16, 16)

        # Setup
        self.setObjectName("main_widget_toolbar_{}".format(
            str(uuid.uuid4())[:8]))
        # self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setFloatable(False)
        self.setMovable(False)
        self.setAllowedAreas(areas)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setIconSize(self._icon_size)
        self._setup_style()

    def set_icon_size(self, icon_size):
        self._icon_size = icon_size
        self.setIconSize(icon_size)

    def addWidget(self, widget):
        """
        Override Qt method.

        Take into account the existence of a corner widget when adding a new
        widget in this toolbar.
        """
        if self._corner_widget is not None:
            super().insertWidget(self._corner_separator_action, widget)
        else:
            super().addWidget(widget)

    def addAction(self, action):
        """
        Override Qt method.

        Take into account the existence of a corner widget when adding a new
        action in this toolbar.
        """
        pass

    def add_item(self, action_or_widget, section=None, before=None):
        if section is not None:
            action_or_widget._section = section

        if section is None and before is not None:
            action_or_widget._section = before._section
            section = before._section

        if section is not None and section not in self._section_items:
            self._section_items[section] = [action_or_widget]
        else:
            self._section_items[section].append(action_or_widget)

    def _render(self):
        """
        Create the toolbar taking into account the sections and locations.

        This method is called once on widget setup.
        """
        sec_items = []
        for sec, items in self._section_items.items():
            for item in items:
                sec_items.append([sec, item])

            sep = QAction(self)
            sep.setSeparator(True)
            sec_items.append((None, sep))

        if sec_items:
            sec_items.pop()

        for (sec, item) in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
                insert_method = super().insertAction
            else:
                add_method = super().addWidget
                insert_method = super().insertWidget

            if self._corner_widget is not None:
                insert_method(self._corner_separator, item)
            else:
                add_method(item)

            if isinstance(item, QAction):
                text_beside_icon = getattr(item, 'text_beside_icon', False)
                if text_beside_icon:
                    widget = self.widgetForAction(item)
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget = self.widgetForAction(item)
                    widget.setCheckable(True)

    def create_toolbar_stretcher(self):
        """
        Create a stretcher widget to be used in a Qt toolbar.
        """
        stretcher = QWidget()
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return stretcher

    def _set_corner_widget(self, corner_widget):
        """
        Add the given corner widget to this toolbar.

        A stretcher widget is added before the corner widget so that
        its position is forced to the right side of the toolbar when the
        toolbar is resized.
        """
        self._corner_widget = corner_widget
        if corner_widget is not None:
            stretcher = self.create_toolbar_stretcher()
            self._corner_separator = super().addWidget(stretcher)
            super().addWidget(self._corner_widget)
        else:
            self._corner_separator = None

    def _setup_style(self):
        """
        Set the style of this toolbar with a stylesheet.
        """
        if is_dark_interface():
            stylesheet = r"""
                QToolBar QToolButton:!hover:!pressed {
                    border-color: transparent;
                }
                QToolBar {
                    border: 0px;
                    background: rgb(25, 35, 45);
                }
                QToolButton {
                    background-color: transparent;
                }
                QToolButton:checked {
                    background-color: rgb(49, 64, 75);
                }
            """
        else:
            stylesheet = r"QToolBar {border: 0px;}"

        self.setStyleSheet(textwrap.dedent(stylesheet))


class PluginWidget(QWidget, SpyderWidgetMixin, SpyderToolBarMixin):
    """
    Spyder widget class.

    This class handles non dockable widget.

    Notes
    -----
    All Spyder non dockable plugins define a plugin widget that must subclass
    this.
    """
    DEFAULT_OPTIONS = {}

    # Signals
    sig_option_changed = Signal(str, object)
    sig_redirect_stdio_requested = Signal(bool)
    sig_refresh_requested = Signal()  # FIXME:

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(parent=parent)
        self._options = options

        # Attributes
        # --------------------------------------------------------------------
        self._name = name
        self._plugin = plugin
        self._parent = parent

    # --- API: methods to define or override
    # ------------------------------------------------------------------------
    def get_title(self):
        """
        Return the title that will be displayed on dockwidget or window title.
        """
        raise NotImplementedError('PluginWidget must define `get_title`!')

    def setup(self, options=DEFAULT_OPTIONS):
        """
        Create widget actions, add to menu and other setup requirements.
        """
        raise NotImplementedError('PluginWidget must define `setup`!')


class PluginMainWidget(QMainWindow, SpyderWidgetMixin, SpyderToolBarMixin):
    """
    Spyder widget class.

    This class handles both a dockwidget pane and a floating window widget
    (undocked pane).

    Notes
    -----
    All Spyder dockable plugins define a main widget that must subclass this.

    A Spyder widget is a Qt main window that consists of a single widget and a
    set of toolbars that are stacked above or below that widget.

    The toolbars are not moveable nor floatable and must occupy the entire
    horizontal space available for the plugin, i.e. that toolbars must be
    stacked vertically and cannot be placed horizontally next to each other.
    """
    DEFAULT_OPTIONS = {}

    # Signals
    sig_option_changed = Signal(str, object)
    sig_redirect_stdio_requested = Signal(bool)
    sig_refresh_requested = Signal()  # FIXME:
    sig_toggle_view_changed = Signal(bool)
    sig_update_ancestor_requested = Signal()  # FIXME:

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(parent=parent)

        # Attributes
        # --------------------------------------------------------------------
        self._options = options
        self._is_tab = False
        self._name = name
        self._plugin = plugin
        self._parent = parent
        self._default_margins = None
        self.is_maximized = None
        self.is_visible = None
        # We create our toggle action instead of using the one that comes with
        # dockwidget because it was not possible to raise and focus the plugin
        self.toggle_view_action = None
        self._widgets = {}
        self._toolbars = {}

        # Widgets
        # --------------------------------------------------------------------
        self.windowwidget = None
        self.dockwidget = None
        self._central_widget = QWidget(self)
        self._icon = QIcon()
        self._spinner = create_waitspinner(size=16, parent=self)
        self._corner_widget = MainCornerWidget(parent=self)

    # --- Private Methods ---------------------------------------------
    # -----------------------------------------------------------------
    @staticmethod
    def _find_children(obj, all_children):
        """
        Find all children of `obj` that use SpyderWidgetMixin recursively.

        `all_children` is a list on which to append the results.
        """
        children = obj.findChildren(SpyderWidgetMixin)
        all_children.extend(children)

        if obj not in all_children:
            all_children.append(obj)

        for child in children:
            children = child.findChildren(SpyderWidgetMixin)
            all_children.extend(children)

        return all_children

    def _setup(self, options=DEFAULT_OPTIONS):
        """
        Setup default actions, create options menu, and connect signals.
        """
        # Tabs
        children = self.findChildren(Tabs)
        if children:
            for child in children:
                self._is_tab = True
                child.setCornerWidget(self._corner_widget)
                break

        if self._is_tab:
            corner_widget = None
        else:
            corner_widget = self._corner_widget

        self._main_toolbar = MainWidgetToolbar(corner_widget=corner_widget)

        if self._is_tab:
            # This disables the toolbar on all tabbed plugins
            self.get_main_toolbar().setVisible(not self._is_tab)

        self._options_menu = self.create_menu(
            PluginMainWidgetMenus.Options,
            text='',
        )
        self._options_button = self.create_toolbutton(
            PluginMainWidgetWidgets.OptionsToolButton,
            text=_('Options'),
            icon=self.create_icon('tooloptions'),
        )

        self.add_corner_widget(
            PluginMainWidgetWidgets.OptionsToolButton,
            self._options_button,
        )
        self.add_corner_widget(
            PluginMainWidgetWidgets.Spinner,
            self._spinner,
        )

        # TODO: Check if the central widget added is a QTabWidget or similar
        # and hide the main toolbar, in which case only a corner widget is
        # used
        self._toolbars['main'] = self._main_toolbar

        # Setup the a dictionary in which pointers to additional toolbars
        # added to the plugin interface are going to be saved.
        self._aux_toolbars = {Qt.TopToolBarArea: [], Qt.BottomToolBarArea: []}

        # Widget setup
        # --------------------------------------------------------------------
        self._options_button.setPopupMode(QToolButton.InstantPopup)
        self.setWindowFlags(Qt.Widget)
        self.addToolBar(self._main_toolbar)
        self.addToolBarBreak(Qt.TopToolBarArea)

        # Create default widget actions
        self.dock_action = self.create_action(
            name=PluginMainWidgetActions.DockPane,
            text=_("Dock"),
            tip=_("Dock the pane"),
            icon=self.create_icon('dock'),
            triggered=self.close_window,
        )
        self.undock_action = self.create_action(
            name=PluginMainWidgetActions.UndockPane,
            text=_("Undock"),
            tip=_("Undock the pane"),
            icon=self.create_icon('undock'),
            triggered=self.create_window,
        )
        self.close_action = self.create_action(
            name=PluginMainWidgetActions.ClosePane,
            text=_("Close"),
            tip=_("Close the pane"),
            icon=self.create_icon('close_pane'),
            triggered=self.close_dock,
        )
        # We use this instead of the QDockWidget.toggleViewAction
        self.toggle_view_action = self.create_action(
            name='switch to ' + self._name,
            text=self.get_title(),
            toggled=lambda checked: self.toggle_view(checked),
            context=Qt.WidgetShortcut,
            shortcut_context='_',
        )
        self.toggle_view_action.setChecked(True)

        # TODO: Should provide the right section?
        bottom_section = OptionsMenuSections.Bottom
        self.add_item_to_menu(
            self.undock_action,
            self._options_menu,
            section=bottom_section,
        )
        self.add_item_to_menu(
            self.close_action,
            self._options_menu,
            section=bottom_section,
        )
        self.add_item_to_menu(
            self.dock_action,
            self._options_menu,
            section=bottom_section,
        )

        self._options_button.setMenu(self._options_menu,)
        self._options_menu.aboutToShow.connect(self._update_actions)

        # Hide icons in Mac plugin menus
        if sys.platform == 'darwin':
            self._options_menu.aboutToHide.connect(
                lambda menu=self._options_menu: set_menu_icons(menu, False))

        # Update title
        # TODO:
        # self.sig_update_plugin_title.connect(self._update_plugin_title)
        self.setWindowTitle(self.get_title())
        self._update_style()

    def _update_style(self):
        """
        Update style of the widget.
        """
        qss = r"""
            QToolButton::menu-indicator {
                image: none;
            }
            QToolButton {
                margin: 0px;
            }
            """
        self._options_button.setStyleSheet(textwrap.dedent(qss))

    def _update_actions(self):
        """
        Refresh Options menu.
        """
        show_dock_actions = self.windowwidget is None
        self.undock_action.setVisible(show_dock_actions)
        self.close_action.setVisible(show_dock_actions)
        self.dock_action.setVisible(not show_dock_actions)

        if sys.platform == 'darwin':
            set_menu_icons(self.get_menu(PluginMainWidgetMenus.Options), True)

        self.update_actions()
        self._update_style()

    @Slot(bool)
    def _on_top_level_change(self, top_level):
        """
        Actions to perform when a plugin is undocked to be moved.
        """
        self.undock_action.setDisabled(top_level)

    # --- Public Qt overriden methods
    # ------------------------------------------------------------------------
    def setLayout(self, layout):
        """
        Set the layout of the SpyderWidget.

        Notes
        -----
        Convenience to use this widget as a normal QWidget.
        """
        self._central_widget.setLayout(layout)
        self.setCentralWidget(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def layout(self):
        """
        Return the layout of the SpyderWidget.
        """
        return self._central_widget.layout()

    # --- Public methods to use
    # ------------------------------------------------------------------------
    def get_plugin(self):
        """
        Return the parent plugin.
        """
        return self._plugin

    def get_action(self, name):
        """
        Return action by name.
        """
        actions = self.get_actions(filter_actions=False)

        if name in actions:
            return actions[name]
        else:
            raise Exception('{} not found in {}'.format(
                name, list(actions.keys())))

    # FIXME: Cache!
    def get_actions(self, filter_actions=True):
        """
        Return all actions defined by the Spyder plugin widget and child
        widgets implementing SpyderWidgetMixin.

        Notes
        -----
        1. Actions should be created once. Creating new actions on menu popup
           is *highly* discouraged.
        2. To create an action the user must user this method on this Mixin.
        3. The PluginMainWidget will collect any actions defined in subwidgets
           (if defined) and expose them in the get_actions method at the plugin
           level.
        4. Any action created this way is now exposed as a possible shortcut
           automatically without manual shortcut registration.
           If an option is found in the config then it is assigned otherwise
           is left with an empty shortcut.
        5. There is no need to override this method.
        """
        all_children = self._find_children(self, [self])
        actions = OrderedDict()
        for child in all_children:
            get_actions_method = getattr(child, 'get_actions', None)
            _actions = getattr(child, '_actions', None)

            if get_actions_method and _actions:
                for key, action in child._actions.items():
                    # These are actions that we want to skip from exposing to
                    # make things simpler, but avoid creating specific
                    # variables for this
                    if filter_actions:
                        actions_blacklist = [
                            self.dock_action,
                            self.undock_action,
                            self.close_action,
                            'switch to ' + self._name,
                        ]
                        if key not in actions_blacklist:
                            if key in actions:
                                raise Exception('{} or a child widget has '
                                                'already defined an '
                                                'action "{}"!'.format(self,
                                                                      key))
                            else:
                                actions[key] = action
                    else:
                        if key in actions:
                            raise Exception('{} or a child widget has '
                                            'already defined an '
                                            'action "{}"!'.format(self, key))
                        else:
                            actions[key] = action

        return actions

    def add_corner_widget(self, name, widget, before=None):
        """
        Add widget to corner, that is to the left of the last added widget.

        Parameters
        ----------
        name: str
            Unique name of the widget.
        widget: QWidget
            Any QWidget to add in the corner widget.
        before: QWidget
            Insert the widget before this widget.

        Notes
        -----
        By default widgets are added to the left of the last corner widget.

        SpyderWidget provides an options menu button and a spinner so any
        additional widgets will be placed to the left of the spinner,
        if visible.
        """
        if self._corner_widget is not None:
            self._corner_widget.add_widget(name, widget)

    def get_corner_widget(self, name):
        """
        Return the a widget inside the corner widget by name.

        Parameters
        ----------
        name: str
            Unique name of the widget.
        """
        return self._corner_widget.get_widget(name)

    def start_spinner(self):
        """
        Start default status spinner.
        """
        self._spinner.setVisible(True)
        self._spinner.start()

    def stop_spinner(self):
        """
        Stop default status spinner.
        """
        self._spinner.stop()
        self._spinner.setVisible(False)

    def create_toolbar(self, name, location='top'):
        """
        Create and add an auxiliary toolbar at the top or at the bottom
        of the plugin.

        Parameters
        ----------
        location: str
            A string whose value is used to determine where to add the
            toolbar in the plugin interface. The toolbar can be added either
            at the 'top' or at the 'bottom' of the plugin.

        Returns
        -------
        SpyderPluginToolbar
            The auxiliary toolbar that was created and added to the plugin
            interface.
        """
        if name in self._toolbars:
            raise Exception('!')

        if location not in ['top', 'bottom']:
            raise Exception('Invalid location "{}"!'.format(location))

        toolbar = MainWidgetToolbar(parent=self)
        self._toolbars[name] = toolbar
        self._add_auxiliary_toolbar(toolbar, location)

        return toolbar

    def create_menu(self, name, text=''):
        """
        Override SpyderMenuMixin method to use a different menu class.
        """
        menus = getattr(self, '_menus', None)
        if menus is None:
            self._menus = OrderedDict()

        if name in self._menus:
            raise Exception('Menu name "{}" already in use!'.format(name))

        menu = MainWidgetMenu(name, title=text, parent=self)
        self._menus[name] = menu
        return menu

    def _add_auxiliary_toolbar(self, toolbar, location):
        """
        Add the given toolbar at the top or at the bottom of the plugin.
        Parameters
        ----------
        toolbar: QToolBar
            The SpyderPluginToolbar that needs to be added to the plugin
            interface.
        location: str
            A string whose value is used to determine where to add the given
            toolbar in the plugin interface. The toolbar can be added either
            at the 'top' or at the 'bottom' of the plugin.
        """
        if location == 'top':
            area = Qt.TopToolBarArea
        elif location == 'bottom':
            area = Qt.BottomToolBarArea
        else:
            raise Exception('Invalid location "{}"!'.format(location))

        if self._aux_toolbars[area]:
            self.addToolBarBreak(area)

        toolbar.setAllowedAreas(area)
        self.addToolBar(toolbar)
        self._aux_toolbars[area].append(toolbar)

    def get_toolbar(self, name):
        """
        Return the main toolbar of the plugin.

        Returns
        -------
        QToolBar
            The main toolbar of the plugin that contains the options button.
        """
        if name not in self._toolbars:
            raise Exception('TODO:')

        return self._toolbars[name]

    def get_options_menu(self):
        """
        Return the main options menu of the widget.
        """
        return self._options_menu

    def get_main_toolbar(self):
        """
        Return the main toolbar of the plugin.

        Returns
        -------
        QToolBar
            The main toolbar of the widget that contains the options button.
        """
        return self._main_toolbar

    def set_icon_size(self, icon_size):
        """
        Set the icon size of the plugin's toolbars.

        Parameters
        ----------
        iconsize: int
            An integer corresponding to the size in pixels to which the icons
            of the plugin's toolbars need to be set.
        """
        self._icon_size = icon_size
        self._main_toolbar.set_icon_size(QSize(icon_size, icon_size))

    def show_status_message(self, message, timeout):
        """
        Show a status message in the Spyder widget.
        """
        status_bar = self.statusBar()
        if status_bar.isVisible():
            status_bar.showMessage(message, timeout)

    def get_focus_widget(self):
        """
        Get the widget to give focus to.

        Returns
        -------
        QWidget
            QWidget to give focus to.

        Notes
        -----
        This is applied when plugin's dockwidget is raised on top-level.
        """
        return self

    def update_margins(self, margin=None):
        """
        Update widget margins.
        """
        layout = self._central_widget.layout()
        if self._default_margins is None:
            self._default_margins = layout.getContentsMargins()

        if margin is not None:
            layout.setContentsMargins(margin, margin + 3, margin, margin)
        else:
            layout.setContentsMargins(*self._default_margins)

    def update_title(self):
        """
        Update title of dockwidget or plugin window.
        """
        if self.dockwidget is not None:
            widget = self.dockwidget
        elif self.windowwidget is not None:
            widget = self.undocked_window
        else:
            return

        widget.setWindowTitle(self.get_title())

    def set_name(self, name):
        """
        Set widget name (plugin.NAME).
        """
        self._name = name

    def get_name(self):
        """
        Return widget name (plugin.NAME).
        """
        return self._name

    def set_icon(self, icon):
        """
        Set widget icon.
        """
        self._icon = icon

    def get_icon(self):
        """
        Return widget icon.
        """
        return self._icon

    # --- SpyderDockwidget handling ------------------------------------------
    # ------------------------------------------------------------------------
    @Slot()
    def create_window(self):
        """
        Create a QMainWindow instance containing this SpyderWidget.
        """
        # Wigdets
        self.windowwidget = window = SpyderWindowWidget(self)

        # Wigdet setup
        window.setWindowIcon(self.get_icon())
        window.setCentralWidget(self)
        window.setWindowTitle(self.get_title())
        window.resize(self.size())

        if self.dockwidget:
            self.dockwidget.setFloating(False)
            self.dockwidget.setVisible(False)

        self.set_ancestor(window)
        self._update_actions()
        window.show()

        # Signals
        # TODO:
        # self.sig_refresh_requested.emit()

    @Slot()
    def close_window(self):
        """
        Close QMainWindow instance that contains this SpyderWidget.
        """
        if self.windowwidget is not None:
            # Fixes spyder-ide/spyder#10704
            self.__unsafe_window = self.windowwidget
            self.__unsafe_window.deleteLater()
            self.windowwidget.close()
            self.windowwidget = None

            # These actions can appear disabled when 'Dock' action is pressed
            self.undock_action.setDisabled(False)
            self.close_action.setDisabled(False)

        if self.dockwidget is not None:
            # TODO: need a signal!
            # self.set_ancestor(self.main)
            self.dockwidget.setWidget(self)
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
            self._update_actions()
            # self.sig_switch_to_plugin_requested.emit()

    def change_visibility(self, enable, force_focus=None):
        """
        Dock widget visibility has changed.
        """
        if self.dockwidget is None:
            return

        is_visible = not self.is_visible

        # TODO: handle maximized!

        if enable:
            # Avoid double trigger of visibility change
            self.dockwidget.blockSignals(True)
            self.dockwidget.raise_()
            self.dockwidget.blockSignals(False)

        raise_and_focus = getattr(self, 'RAISE_AND_FOCUS', None)

        if force_focus is None:
            if raise_and_focus or not is_visible:
                focus_widget = self.get_focus_widget()
                if focus_widget:
                    focus_widget.setFocus()
        elif force_focus is True:
            focus_widget = self.get_focus_widget()
            if focus_widget:
                focus_widget.setFocus()
        elif force_focus is False:
            pass

        self.is_visible = enable

        # TODO: Handle this option
        # if getattr(self, 'DISABLE_ACTIONS_WHEN_HIDDEN', None):
        #     toggle_actions(self.get_actions(), visible)
        #     toggle_actions(self._plugin_actions, visible)

        # self.is_visible = enable and visible

    def toggle_view(self, checked):
        """
        Toggle dockwidget's visibility when its entry is selected in
        the menu `View > Panes`.

        Parameters
        ----------
        checked: bool
            Is the entry in `View > Panes` checked or not?

        Notes
        -----
        If you need to attach some functionality when this changes, use
        sig_toggle_view_changed. For an example, please see
        `spyder/plugins/ipythonconsole/plugin.py`
        """
        if not self.dockwidget:
            return

        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            self.is_visible = True
        else:
            self.dockwidget.hide()
            self.is_visible = False

        # Update toggle view status, if needed, without emitting signals.
        if self.toggle_view_action.isChecked() != checked:
            self.blockSignals(True)
            self.toggle_view_action.setChecked(checked)
            self.blockSignals(False)

        self.sig_toggle_view_changed.emit(checked)

    def create_dockwidget(self, mainwindow):
        """
        Add to parent QMainWindow as a dock widget.
        """
        # Creating dock widget
        title = self.get_title()
        self.dockwidget = dock = SpyderDockWidget(title, mainwindow)

        # Setup
        dock.setObjectName(self.__class__.__name__ + '_dw')
        dock.setWidget(self)

        # Signals
        dock.visibilityChanged.connect(self.change_visibility)
        dock.topLevelChanged.connect(self._on_top_level_change)

        # TODO: Change name of signal and connect? when is this used?
        # dock.sig_plugin_closed.connect(self.close_dock)

        return (dock, dock.LOCATION)

    @Slot()
    def close_dock(self):
        """
        Close the dockwidget.
        """
        self.toggle_view(False)

    # --- API: methods to define or override
    # ------------------------------------------------------------------------
    def get_title(self):
        """
        Return the title that will be displayed on dockwidget or window title.
        """
        raise NotImplementedError('PluginMainWidget must define `get_title`!')

    def set_ancestor(self, ancestor):
        """
        Needed to update the ancestor/parent of child widgets when undocking.
        """
        pass

    def setup(self, options):
        """
        Create widget actions, add to menu and other setup requirements.
        """
        raise NotImplementedError('A PluginMainWigdet must define a setup '
                                  'method!')

    def update_actions(self):
        """
        Update the state of exposed actions.

        Exposed actions are actions created by the self.create_action method.
        """
        raise NotImplementedError

    def on_option_update(self, option, value):
        """
        This method is called when the an option is set with the `set_option`
        or `set_options` method from the OptionMixin.
        """
        raise NotImplementedError


def run_test():
    # Third party imports
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication, QTableWidget

    # Local imports
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    main = QMainWindow()
    widget = PluginMainWidget('test', main)
    options = PluginMainWidget.DEFAULT_OPTIONS
    widget.get_title = lambda x=None: 'Test title'
    widget._setup(options)
    layout = QHBoxLayout()
    layout.addWidget(QTableWidget())
    widget.setLayout(layout)
    widget.start_spinner()
    dock, location = widget.create_dockwidget(main)
    main.addDockWidget(location, dock)
    main.setStyleSheet(qdarkstyle.load_stylesheet())
    main.show()
    app.exec_()


if __name__ == '__main__':
    run_test()
