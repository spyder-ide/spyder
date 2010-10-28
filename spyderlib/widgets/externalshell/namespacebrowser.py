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
                         QMessageBox, QApplication, QCursor)
from PyQt4.QtCore import SIGNAL, Qt

# Local imports
from spyderlib.widgets.externalshell.monitor import (monitor_get_remote_view,
                monitor_set_global, monitor_get_global, monitor_del_global,
                monitor_copy_global, monitor_save_globals, monitor_load_globals,
                monitor_is_array, communicate, REMOTE_SETTINGS)
from spyderlib.widgets.dicteditor import (RemoteDictEditorTableView,
                                          DictEditorTableView, globalsfilter)
from spyderlib.utils import encoding, fix_reference_name
from spyderlib.utils.programs import is_module_installed
from spyderlib.utils.qthelpers import (create_toolbutton, add_actions,
                                       create_action)
from spyderlib.utils.iofuncs import iofunctions
from spyderlib.widgets.importwizard import ImportWizard
from spyderlib.config import get_icon, str2type


class NamespaceBrowser(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.shellwidget = None
        self.is_internal_shell = None
        self.is_visible = True
        
        # Remote dict editor settings
        self.filters = None
        self.itermax = None
        self.exclude_private = None
        self.exclude_upper = None
        self.exclude_unsupported = None
        self.excluded_names = None
        self.truncate = None
        self.minmax = None
        self.collvalue = None
        self.inplace = None
        self.autorefresh = None
        
        self.editor = None
        self.exclude_private_action = None
        self.exclude_upper_action = None
        self.exclude_unsupported_action = None
        
        self.filename = None
            
    def setup(self, filters=None, itermax=None, exclude_private=None,
              exclude_upper=None, exclude_unsupported=None, excluded_names=None,
              truncate=None, minmax=None, collvalue=None, inplace=None,
              autorefresh=None):
        assert self.shellwidget is not None
        
        self.filters = filters
        self.itermax = itermax
        self.exclude_private = exclude_private
        self.exclude_upper = exclude_upper
        self.exclude_unsupported = exclude_unsupported
        self.excluded_names = excluded_names
        self.truncate = truncate
        self.minmax = minmax
        self.collvalue = collvalue
        self.inplace = inplace
        self.autorefresh = autorefresh
        
        if self.editor is not None:
            self.editor.setup_menu(truncate, minmax, inplace, collvalue)
            self.exclude_private_action.setChecked(exclude_private)
            self.exclude_upper_action.setChecked(exclude_upper)
            self.exclude_unsupported_action.setChecked(exclude_unsupported)
            self.auto_refresh_button.setChecked(autorefresh)
            self.refresh_table()
            return
        
        # Dict editor:
        if self.is_internal_shell:
            self.editor = DictEditorTableView(self, None, truncate=truncate,
                                              inplace=inplace, minmax=minmax,
                                              collvalue=collvalue)
        else:
            self.editor = RemoteDictEditorTableView(self, None,
                            truncate=truncate, inplace=inplace, minmax=minmax,
                            collvalue=collvalue,
                            get_value_func=self.get_value,
                            set_value_func=self.set_value,
                            new_value_func=self.set_value,
                            remove_values_func=self.remove_values,
                            copy_value_func=self.copy_value,
                            is_list_func=self.is_list, get_len_func=self.get_len,
                            is_array_func=self.is_array, is_dict_func=self.is_dict,
                            get_array_shape_func=self.get_array_shape,
                            get_array_ndim_func=self.get_array_ndim,
                            oedit_func=self.oedit,
                            plot_func=self.plot, imshow_func=self.imshow)
        self.connect(self.editor, SIGNAL('option_changed'),
                     lambda option, value:
                     self.emit(SIGNAL('option_changed'), option, value))
        
        # Setup layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        toolbar = self.setup_toolbar(exclude_private, exclude_upper,
                                     exclude_unsupported, autorefresh)
        vlayout.setAlignment(Qt.AlignTop)
        for widget in toolbar:
            vlayout.addWidget(widget)
        hlayout.addWidget(self.editor)
        hlayout.addLayout(vlayout)
        self.setLayout(hlayout)
        hlayout.setContentsMargins(0, 0, 0, 0)

        self.connect(self, SIGNAL('option_changed'), self.option_changed)
        
    def set_shellwidget(self, shellwidget):
        self.shellwidget = shellwidget
        from spyderlib.widgets import internalshell
        self.is_internal_shell = isinstance(self.shellwidget,
                                            internalshell.InternalShell)
        
    def setup_toolbar(self, exclude_private, exclude_upper,
                      exclude_unsupported, autorefresh):
        toolbar = []

        refresh_button = create_toolbutton(self, text=self.tr("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh_table)
        self.auto_refresh_button = create_toolbutton(self,
                                           text=self.tr("Refresh periodically"),
                                           icon=get_icon('auto_reload.png'),
                                           toggled=self.toggle_auto_refresh)
        self.auto_refresh_button.setChecked(autorefresh)
        load_button = create_toolbutton(self, text=self.tr("Import data"),
                                        icon=get_icon('fileimport.png'),
                                        triggered=self.import_data)
        self.save_button = create_toolbutton(self, text=self.tr("Save data"),
                                icon=get_icon('filesave.png'),
                                triggered=lambda: self.save_data(self.filename))
        self.save_button.setEnabled(False)
        save_as_button = create_toolbutton(self,
                                           text=self.tr("Save data as..."),
                                           icon=get_icon('filesaveas.png'),
                                           triggered=self.save_data)
        toolbar += [refresh_button, self.auto_refresh_button, load_button,
                    self.save_button, save_as_button]
        
        self.exclude_private_action = create_action(self,
                self.tr("Exclude private references"),
                tip=self.tr("Exclude references which name starts"
                            " with an underscore"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_private', state))
        self.exclude_private_action.setChecked(exclude_private)
        
        self.exclude_upper_action = create_action(self,
                self.tr("Exclude capitalized references"),
                tip=self.tr("Exclude references which name starts with an "
                            "upper-case character"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_upper', state))
        self.exclude_upper_action.setChecked(exclude_upper)
        
        self.exclude_unsupported_action = create_action(self,
                self.tr("Exclude unsupported data types"),
                tip=self.tr("Exclude references to unsupported data types"
                            " (i.e. which won't be handled/saved correctly)"),
                toggled=lambda state:self.emit(SIGNAL('option_changed'),
                                               'exclude_unsupported', state))
        self.exclude_unsupported_action.setChecked(exclude_unsupported)
        
        options_button = create_toolbutton(self, text=self.tr("Options"),
                                           icon=get_icon('tooloptions.png'))
        toolbar.append(options_button)
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        editor = self.editor
        actions = [self.exclude_private_action, self.exclude_upper_action,
                   self.exclude_unsupported_action, None,
                   editor.truncate_action, editor.inplace_action,
                   editor.collvalue_action]
        if is_module_installed('numpy'):
            actions.append(editor.minmax_action)
        add_actions(menu, actions)
        options_button.setMenu(menu)
        
        return toolbar

    def option_changed(self, option, value):
        setattr(self, option, value)
        self.refresh_table()
        
    def visibility_changed(self, enable):
        """Notify the widget whether its container (the namespace browser 
        plugin is visible or not"""
        self.is_visible = enable
        
    def toggle_auto_refresh(self, state):
        self.autorefresh = state
        
    def auto_refresh(self):
        if self.autorefresh:
            self.refresh_table()
            
    def _get_sock(self):
        return self.shellwidget.introspection_socket
        
    def _get_settings(self):
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = getattr(self, name)
        return settings
    
    def get_internal_shell_filter(self, itermax=None):
        if itermax is None:
            itermax = self.itermax
        def wsfilter(input_dict, itermax=itermax,
                     filters=str2type(self.filters)):
            """Keep only objects that can be pickled"""
            return globalsfilter(
                         input_dict, itermax=itermax, filters=filters,
                         exclude_private=self.exclude_private,
                         exclude_upper=self.exclude_upper,
                         exclude_unsupported=self.exclude_unsupported,
                         excluded_names=self.excluded_names)
        return wsfilter
        
    def refresh_table(self):
        if self.is_visible and self.isVisible():
            if self.is_internal_shell:
                # Internal shell
                self.editor.set_filter(self.get_internal_shell_filter())
                interpreter = self.shellwidget.interpreter
                if interpreter is not None:
                    self.editor.set_data(interpreter.namespace)
                    self.editor.adjust_columns()
            elif self.shellwidget.is_running():
    #            import time; print >>STDOUT, time.ctime(time.time()), "Refreshing namespace browser"
                sock = self._get_sock()
                if sock is None:
                    return
                settings = self._get_settings()
                try:
                    data = monitor_get_remote_view(sock, settings)
                    if data is not None:
                        self.set_data(data)
                except socket.error:
                    # Process was terminated before calling this method
                    pass
        
    #------ Remote Python process commands -------------------------------------
    def get_value(self, name):
        return monitor_get_global(self._get_sock(), name)
        
    def set_value(self, name, value):
        monitor_set_global(self._get_sock(), name, value)
        self.refresh_table()
        
    def remove_values(self, names):
        for name in names:
            monitor_del_global(self._get_sock(), name)
        self.refresh_table()
        
    def copy_value(self, orig_name, new_name):
        monitor_copy_global(self._get_sock(), orig_name, new_name)
        self.refresh_table()
        
    def is_list(self, name):
        """Return True if variable is a list or a tuple"""
        return communicate(self._get_sock(),
                           "isinstance(globals()['%s'], (tuple, list))" % name)
        
    def is_dict(self, name):
        """Return True if variable is a dictionary"""
        return communicate(self._get_sock(),
                           "isinstance(globals()['%s'], dict)" % name)
        
    def get_len(self, name):
        """Return sequence length"""
        return communicate(self._get_sock(), "len(globals()['%s'])" % name)
        
    def is_array(self, name):
        """Return True if variable is a NumPy array"""
        return monitor_is_array(self._get_sock(), name)
        
    def get_array_shape(self, name):
        """Return array's shape"""
        return communicate(self._get_sock(), "globals()['%s'].shape" % name)
        
    def get_array_ndim(self, name):
        """Return array's ndim"""
        return communicate(self._get_sock(), "globals()['%s'].ndim" % name)
        
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
        
    #------ Set, load and save data --------------------------------------------
    def set_data(self, data):
        if data != self.editor.model.get_data():
            self.editor.set_data(data)
            self.editor.adjust_columns()
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
    def import_data(self, filenames=None):
        title = self.tr("Import data")
        if filenames is None:
            if self.filename is None:
                basedir = os.getcwdu()
            else:
                basedir = osp.dirname(self.filename)
            filenames = iofunctions.get_open_filenames(self, basedir, title)
            if not filenames:
                return
        elif isinstance(filenames, basestring):
            filenames = [filenames]

            
        for filename in filenames:
            
            self.filename = unicode(filename)
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
                
            # 'import_wizard' (self.setup_io)
            if isinstance(load_func, basestring):
                # Import data with import wizard
                error_message = None
                try:
                    text, _encoding = encoding.read(self.filename)
                    if self.is_internal_shell:
                        self.editor.import_from_string(text)
                    else:
                        base_name = osp.basename(self.filename)
                        editor = ImportWizard(self, text, title=base_name,
                                          varname=fix_reference_name(base_name))
                        if editor.exec_():
                            var_name, clip_data = editor.get_data()
                            monitor_set_global(self._get_sock(),
                                               var_name, clip_data)
                except Exception, error:
                    error_message = str(error)
            else:
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                QApplication.processEvents()
                if self.is_internal_shell:
                    namespace, error_message = load_func(self.filename)
                    interpreter = self.shellwidget.interpreter
                    for key in namespace.keys():
                        new_key = fix_reference_name(key,
                                         blacklist=interpreter.namespace.keys())
                        if new_key != key:
                            namespace[new_key] = namespace.pop(key)
                    if error_message is None:
                        interpreter.namespace.update(namespace)
                else:
                    error_message = monitor_load_globals(self._get_sock(),
                                                         self.filename)
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
    
            if error_message is not None:
                QMessageBox.critical(self, title,
                                     self.tr("<b>Unable to load '%1'</b>"
                                             "<br><br>Error message:<br>%2"
                                             ).arg(self.filename
                                                   ).arg(error_message))
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
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        if self.is_internal_shell:
            wsfilter = self.get_internal_shell_filter(itermax=-1)
            namespace = wsfilter(self.shellwidget.interpreter.namespace).copy()
            error_message = iofunctions.save(namespace, filename)
        else:
            settings = self._get_settings()
            error_message = monitor_save_globals(self._get_sock(),
                                                 settings, filename)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        if error_message is not None:
            QMessageBox.critical(self, self.tr("Save data"),
                            self.tr("<b>Unable to save current workspace</b>"
                                    "<br><br>Error message:<br>%1") \
                            .arg(error_message))
        self.save_button.setEnabled(self.filename is not None)
        