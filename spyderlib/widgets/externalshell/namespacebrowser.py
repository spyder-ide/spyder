# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace browser widget"""

import sys, os, os.path as osp, socket

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QWidget, QVBoxLayout, QHBoxLayout, QMenu, QToolButton,
                         QMessageBox)
from PyQt4.QtCore import SIGNAL, Qt

# Local imports
from spyderlib.widgets.externalshell.monitor import (monitor_get_remote_view,
                monitor_set_global, monitor_get_global, monitor_del_global,
                monitor_copy_global, monitor_save_globals, monitor_load_globals,
                monitor_is_array, communicate)
from spyderlib.widgets.dicteditor import RemoteDictEditorTableView
from spyderlib.utils import encoding, fix_reference_name
from spyderlib.utils.programs import is_module_installed
from spyderlib.utils.qthelpers import (create_toolbutton, add_actions,
                                       create_action)
from spyderlib.utils.iofuncs import iofunctions
from spyderlib.widgets.importwizard import ImportWizard
from spyderlib.config import get_icon
#TODO: remove the following line and make it work anyway
# In fact, this 'CONF' object has nothing to do in package spyderlib.widgets
# which should not contain anything directly related to Spyder's main app
# (including its preferences which are stored in CONF).
# So, one should be able to get rid of this object and set options through
# methods like 'set_options(kw1=..., kw2=..., ...)
from spyderlib.config import CONF


def get_settings():
    """
    Return namespace browser settings
    according to Spyder's configuration file
    """
    settings = {}
    for name in ('filters', 'itermax', 'exclude_private', 'exclude_upper',
                 'exclude_unsupported', 'excluded_names',
                 'truncate', 'minmax', 'collvalue'):
        settings[name] = CONF.get('external_shell', name)
    return settings


class NamespaceBrowser(QWidget):
    ID = 'external_shell'
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.shellwidget = None
        self.is_visible = True
        self.auto_refresh_enabled = True

        # Dict editor:
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        self.editor = RemoteDictEditorTableView(parent, None,
                truncate=truncate, inplace=inplace, minmax=minmax,
                collvalue=collvalue, get_value_func=self.get_value,
                set_value_func=self.set_value, new_value_func=self.set_value,
                remove_values_func=self.remove_values,
                copy_value_func=self.copy_value,
                is_list_func=self.is_list, get_len_func=self.get_len,
                is_array_func=self.is_array, is_dict_func=self.is_dict,
                get_array_shape_func=self.get_array_shape,
                get_array_ndim_func=self.get_array_ndim,
                oedit_func=self.oedit,
                plot_func=self.plot, imshow_func=self.imshow)
        self.connect(self.editor, SIGNAL('option_changed'), self.option_changed)
        
        # Setup layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        self.setup_toolbar(vlayout)
        hlayout.addWidget(self.editor)
        hlayout.addLayout(vlayout)
        self.setLayout(hlayout)
        hlayout.setContentsMargins(0, 0, 0, 0)

        self.connect(self, SIGNAL('option_changed'), self.option_changed)
        
        self.filename = None
        
        self.toggle_auto_refresh(self.auto_refresh_enabled)
        
    def set_shellwidget(self, shellwidget):
        self.shellwidget = shellwidget
        
    def setup_toolbar(self, layout):
        toolbar = []

        refresh_button = create_toolbutton(self, text=self.tr("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh_table,
                                           text_beside_icon=False)
        self.auto_refresh_button = create_toolbutton(self,
                                           text=self.tr("Refresh periodically"),
                                           icon=get_icon('auto_reload.png'),
                                           toggled=self.toggle_auto_refresh,
                                           text_beside_icon=False)
        load_button = create_toolbutton(self, text=self.tr("Import data"),
                                        icon=get_icon('fileimport.png'),
                                        triggered=self.import_data,
                                        text_beside_icon=False)
        self.save_button = create_toolbutton(self, text=self.tr("Save data"),
                                icon=get_icon('filesave.png'),
                                triggered=lambda: self.save_data(self.filename),
                                text_beside_icon=False)
        self.save_button.setEnabled(False)
        save_as_button = create_toolbutton(self,
                                           text=self.tr("Save data as..."),
                                           icon=get_icon('filesaveas.png'),
                                           triggered=self.save_data,
                                           text_beside_icon=False)
        toolbar += [refresh_button, self.auto_refresh_button, load_button,
                    self.save_button, save_as_button]
        
        exclude_private_action = create_action(self,
                self.tr("Exclude private references"),
                tip=self.tr("Exclude references which name starts"
                            " with an underscore"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_private', state))
        exclude_private_action.setChecked(CONF.get(self.ID, 'exclude_private'))
        
        exclude_upper_action = create_action(self,
                self.tr("Exclude capitalized references"),
                tip=self.tr("Exclude references which name starts with an "
                            "upper-case character"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_upper', state))
        exclude_upper_action.setChecked( CONF.get(self.ID, 'exclude_upper') )
        
        exclude_unsupported_action = create_action(self,
                self.tr("Exclude unsupported data types"),
                tip=self.tr("Exclude references to unsupported data types"
                            " (i.e. which won't be handled/saved correctly)"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_unsupported', state))
        exclude_unsupported_action.setChecked(CONF.get(self.ID,
                                              'exclude_unsupported'))
        
        options_button = create_toolbutton(self, text=self.tr("Options"),
                                           icon=get_icon('tooloptions.png'),
                                           text_beside_icon=False)
        toolbar.append(options_button)
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        editor = self.editor
        actions = [exclude_private_action, exclude_upper_action,
                   exclude_unsupported_action, None, editor.truncate_action,
                   editor.inplace_action, editor.collvalue_action]
        if is_module_installed('numpy'):
            actions.append(editor.minmax_action)
        add_actions(menu, actions)
        options_button.setMenu(menu)

        layout.setAlignment(Qt.AlignTop)
        for widget in toolbar:
            layout.addWidget(widget)

    def option_changed(self, option, value):
        CONF.set(self.ID, option, value)
        self.refresh_table()
        
    def visibility_changed(self, enable):
        """Notify the widget whether its container (the namespace browser 
        plugin is visible or not"""
        self.is_visible = enable
        
    def toggle_auto_refresh(self, state):
        self.auto_refresh_button.setChecked(state)
        self.auto_refresh_enabled = state
        
    def auto_refresh(self):
        if self.auto_refresh_enabled:
            self.refresh_table()
        
    def refresh_table(self):
        if self.is_visible and self.isVisible() \
           and self.shellwidget.is_running():
#            import time; print >>STDOUT, time.ctime(time.time()), "Refreshing namespace browser"
            sock = self.shellwidget.monitor_socket
            if sock is None:
                return
            settings = get_settings()
            try:
                self.set_data( monitor_get_remote_view(sock, settings) )
            except socket.error:
                # Process was terminated before calling this methods
                pass
        
    def get_value(self, name):
        return monitor_get_global(self.shellwidget.monitor_socket, name)
        
    def set_value(self, name, value):
        sock = self.shellwidget.monitor_socket
        monitor_set_global(sock, name, value)
        self.refresh_table()
        
    def remove_values(self, names):
        sock = self.shellwidget.monitor_socket
        for name in names:
            monitor_del_global(sock, name)
        self.refresh_table()
        
    def copy_value(self, orig_name, new_name):
        sock = self.shellwidget.monitor_socket
        monitor_copy_global(sock, orig_name, new_name)
        self.refresh_table()
        
    def is_list(self, name):
        """Return True if variable is a list or a tuple"""
        return communicate(self.shellwidget.monitor_socket,
                           "isinstance(globals()['%s'], (tuple, list))" % name,
                           pickle_try=True)
        
    def is_dict(self, name):
        """Return True if variable is a dictionary"""
        return communicate(self.shellwidget.monitor_socket,
                           "isinstance(globals()['%s'], dict)" % name,
                           pickle_try=True)
        
    def get_len(self, name):
        """Return sequence length"""
        return communicate(self.shellwidget.monitor_socket,
                           "len(globals()['%s'])" % name,
                           pickle_try=True)
        
    def is_array(self, name):
        """Return True if variable is a NumPy array"""
        return monitor_is_array(self.shellwidget.monitor_socket, name)
        
    def get_array_shape(self, name):
        """Return array's shape"""
        return communicate(self.shellwidget.monitor_socket,
                           "globals()['%s'].shape" % name,
                           pickle_try=True)
        
    def get_array_ndim(self, name):
        """Return array's ndim"""
        return communicate(self.shellwidget.monitor_socket,
                           "globals()['%s'].ndim" % name,
                           pickle_try=True)
        
    def plot(self, name):
        command = "import spyderlib.pyplot as plt; " \
                  "plt.figure(); plt.plot(%s); plt.show();" % name
        self.shellwidget.send_to_process(command)
        
    def imshow(self, name):
        command = "import spyderlib.pyplot as plt; " \
                  "plt.figure(); plt.imshow(%s); plt.show();" % name
        self.shellwidget.send_to_process(command)
        
    def oedit(self, name):
        command = "from spyderlib.widgets.objecteditor import oedit; " \
                  "oedit(%s);" % name
        self.shellwidget.send_to_process(command)
        
    def set_data(self, data):
        if data != self.editor.model.get_data():
            self.editor.set_data(data)
            self.editor.adjust_columns()
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
    def import_data(self):
        sock = self.shellwidget.monitor_socket
        
        title = self.tr("Import data")
        if self.filename is None:
            basedir = os.getcwdu()
        else:
            basedir = osp.dirname(self.filename)
        filename = iofunctions.get_open_filename(self, basedir, title)
        if filename:
            filename = unicode(filename)
        else:
            return
        self.filename = filename
        ext = osp.splitext(self.filename)[1].lower()
        
        if ext not in iofunctions.load_funcs:
            buttons = QMessageBox.Yes | QMessageBox.Cancel
            answer = QMessageBox.question(self, title,
                       self.tr("<b>Unsupported file type '%1'</b><br><br>"
                               "Would you like to import it as a text file?") \
                       .arg(ext), buttons)
            if answer == QMessageBox.Cancel:
                return
            else:
                load_func = 'import_wizard'
        else:
            load_func = iofunctions.load_funcs[ext]
            
        if isinstance(load_func, basestring): # 'import_wizard' (self.setup_io)
            # Import data with import wizard
            error_message = None
            try:
                text, _encoding = encoding.read(self.filename)
                base_name = osp.basename(self.filename)
                editor = ImportWizard(self, text, title=base_name,
                                      varname=fix_reference_name(base_name))
                if editor.exec_():
                    var_name, clip_data = editor.get_data()
                    monitor_set_global(sock, var_name, clip_data)
            except Exception, error:
                error_message = str(error)
        else:
            error_message = monitor_load_globals(sock, self.filename)

        if error_message is not None:
            QMessageBox.critical(self, title,
                                 self.tr("<b>Unable to load '%1'</b>"
                                         "<br><br>Error message:<br>%2") \
                                         .arg(self.filename).arg(error_message))
        self.refresh_table()
    
    def save_data(self, filename=None):
        """Save data"""
        if filename is None:
            filename = self.filename
            if filename is None:
                filename = os.getcwdu()
            filename = iofunctions.get_save_filename(self, filename,
                                                     self.tr("Save data"))
            if filename:
                filename = unicode(filename)
                self.filename = filename
            else:
                return False
        sock = self.shellwidget.monitor_socket
        settings = get_settings()
        error_message = monitor_save_globals(sock, settings, filename)
        if error_message is not None:
            QMessageBox.critical(self, self.tr("Save data"),
                            self.tr("<b>Unable to save current workspace</b>"
                                    "<br><br>Error message:<br>%1") \
                            .arg(error_message))
        self.save_button.setEnabled(self.filename is not None)
        