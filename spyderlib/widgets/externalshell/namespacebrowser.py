# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace browser widget"""

import sys, os, os.path as osp

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
                monitor_get_globals_keys)
from spyderlib.widgets.dicteditor import RemoteDictEditorTableView
from spyderlib.utils import encoding
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
        
        self.shell = parent

        # Dict editor:
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        self.editor = RemoteDictEditorTableView(parent, None,
                                        truncate=truncate, inplace=inplace,
                                        minmax=minmax, collvalue=collvalue,
                                        get_value_func=self.get_value,
                                        set_value_func=self.set_value,
                                        new_value_func=self.set_value,
                                        remove_values_func=self.remove_values,
                                        copy_value_func=self.copy_value)
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
        
    def setup_toolbar(self, layout):
        toolbar = []

        refresh_button = create_toolbutton(self, text=self.tr("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh_table,
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
        toolbar += [refresh_button, load_button,
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
        
    def refresh_table(self):
        sock = self.shell.monitor_socket
        if sock is None:
            return
        settings = get_settings()
        self.set_data( monitor_get_remote_view(sock, settings) )
        
    def get_value(self, name):
        return monitor_get_global(self.shell.monitor_socket, name)
        
    def set_value(self, name, value):
        sock = self.shell.monitor_socket
        monitor_set_global(sock, name, value)
        self.refresh_table()
        
    def remove_values(self, names):
        sock = self.shell.monitor_socket
        for name in names:
            monitor_del_global(sock, name)
        self.refresh_table()
        
    def copy_value(self, orig_name, new_name):
        sock = self.shell.monitor_socket
        monitor_copy_global(sock, orig_name, new_name)
        self.refresh_table()
        
    def set_data(self, data):
        self.editor.set_data(data)
        self.editor.adjust_columns()
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
    def import_data(self):
        sock = self.shell.monitor_socket
        
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
                varname_base = self.tr("new")
                try:
                    varname_base = str(varname_base)
                except UnicodeEncodeError:
                    varname_base = unicode(varname_base)
                get_varname = lambda index: varname_base + ("%03d" % index)
                index = 0
                names = monitor_get_globals_keys(sock)
                while get_varname(index) in names:
                    index += 1
                editor = ImportWizard(self, text, title=self.filename,
                                      varname=get_varname(index))
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
        sock = self.shell.monitor_socket
        settings = get_settings()
        error_message = monitor_save_globals(sock, settings, filename)
        if error_message is not None:
            QMessageBox.critical(self, self.tr("Save data"),
                            self.tr("<b>Unable to save current workspace</b>"
                                    "<br><br>Error message:<br>%1") \
                            .arg(error_message))
        self.save_button.setEnabled(self.filename is not None)
        