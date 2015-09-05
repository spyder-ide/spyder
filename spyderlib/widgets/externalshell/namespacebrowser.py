# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace browser widget"""

import os.path as osp
import socket

from spyderlib.qt.QtGui import (QWidget, QVBoxLayout, QHBoxLayout, QMenu,
                                QToolButton, QMessageBox, QApplication,
                                QCursor, QInputDialog)
from spyderlib.qt.QtCore import SIGNAL, Qt, Signal
from spyderlib.qt.compat import getopenfilenames, getsavefilename

# Local imports
from spyderlib.widgets.externalshell.monitor import (
            monitor_set_global, monitor_get_global, monitor_del_global,
            monitor_copy_global, monitor_save_globals, monitor_load_globals,
            communicate, REMOTE_SETTINGS)
from spyderlib.widgets.dicteditor import (RemoteDictEditorTableView,
                                          DictEditorTableView)
from spyderlib.widgets.dicteditorutils import globalsfilter
from spyderlib.utils import encoding
from spyderlib.utils.misc import fix_reference_name
from spyderlib.utils.programs import is_module_installed
from spyderlib.utils.qthelpers import (get_icon, create_toolbutton,
                                       add_actions, create_action)
from spyderlib.utils.iofuncs import iofunctions
from spyderlib.widgets.importwizard import ImportWizard
from spyderlib.baseconfig import _, get_supported_types
from spyderlib.py3compat import is_text_string, to_text_string, getcwd


SUPPORTED_TYPES = get_supported_types()


class NamespaceBrowser(QWidget):
    """Namespace browser (global variables explorer widget)"""
    sig_option_changed = Signal(str, object)
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.shellwidget = None
        self.is_internal_shell = None
        self.ipyclient = None
        self.is_ipykernel = None
        
        self.is_visible = True # Do not modify: light mode won't work!
        
        self.setup_in_progress = None
        
        # Remote dict editor settings
        self.check_all = None
        self.exclude_private = None
        self.exclude_uppercase = None
        self.exclude_capitalized = None
        self.exclude_unsupported = None
        self.excluded_names = None
        self.truncate = None
        self.minmax = None
        self.remote_editing = None
        self.autorefresh = None
        
        self.editor = None
        self.exclude_private_action = None
        self.exclude_uppercase_action = None
        self.exclude_capitalized_action = None
        self.exclude_unsupported_action = None
        
        self.filename = None
            
    def setup(self, check_all=None, exclude_private=None,
              exclude_uppercase=None, exclude_capitalized=None,
              exclude_unsupported=None, excluded_names=None,
              truncate=None, minmax=None, remote_editing=None,
              autorefresh=None):
        """Setup the namespace browser"""
        assert self.shellwidget is not None
        
        self.check_all = check_all
        self.exclude_private = exclude_private
        self.exclude_uppercase = exclude_uppercase
        self.exclude_capitalized = exclude_capitalized
        self.exclude_unsupported = exclude_unsupported
        self.excluded_names = excluded_names
        self.truncate = truncate
        self.minmax = minmax
        self.remote_editing = remote_editing
        self.autorefresh = autorefresh
        
        if self.editor is not None:
            self.editor.setup_menu(truncate, minmax)
            self.exclude_private_action.setChecked(exclude_private)
            self.exclude_uppercase_action.setChecked(exclude_uppercase)
            self.exclude_capitalized_action.setChecked(exclude_capitalized)
            self.exclude_unsupported_action.setChecked(exclude_unsupported)
            # Don't turn autorefresh on for IPython kernels
            # See Issue 1450
            if not self.is_ipykernel:
                self.auto_refresh_button.setChecked(autorefresh)
            self.refresh_table()
            return
        
        # Dict editor:
        if self.is_internal_shell:
            self.editor = DictEditorTableView(self, None, truncate=truncate,
                                              minmax=minmax)
        else:
            self.editor = RemoteDictEditorTableView(self, None,
                            truncate=truncate, minmax=minmax,
                            remote_editing=remote_editing,
                            get_value_func=self.get_value,
                            set_value_func=self.set_value,
                            new_value_func=self.set_value,
                            remove_values_func=self.remove_values,
                            copy_value_func=self.copy_value,
                            is_list_func=self.is_list,
                            get_len_func=self.get_len,
                            is_array_func=self.is_array,
                            is_image_func=self.is_image,
                            is_dict_func=self.is_dict,
                            is_data_frame_func=self.is_data_frame,
                            is_time_series_func=self.is_time_series,                       
                            get_array_shape_func=self.get_array_shape,
                            get_array_ndim_func=self.get_array_ndim,
                            oedit_func=self.oedit,
                            plot_func=self.plot, imshow_func=self.imshow,
                            show_image_func=self.show_image)
        self.editor.sig_option_changed.connect(self.sig_option_changed.emit)
        self.editor.sig_files_dropped.connect(self.import_data)
        
        
        # Setup layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        toolbar = self.setup_toolbar(exclude_private, exclude_uppercase,
                                     exclude_capitalized, exclude_unsupported,
                                     autorefresh)
        vlayout.setAlignment(Qt.AlignTop)
        for widget in toolbar:
            vlayout.addWidget(widget)
        hlayout.addWidget(self.editor)
        hlayout.addLayout(vlayout)
        self.setLayout(hlayout)
        hlayout.setContentsMargins(0, 0, 0, 0)

        self.sig_option_changed.connect(self.option_changed)
        
    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to namespace browser"""
        self.shellwidget = shellwidget
        from spyderlib.widgets import internalshell
        self.is_internal_shell = isinstance(self.shellwidget,
                                            internalshell.InternalShell)
        self.is_ipykernel = self.shellwidget.is_ipykernel
        if not self.is_internal_shell:
            shellwidget.set_namespacebrowser(self)
    
    def set_ipyclient(self, ipyclient):
        """Bind ipyclient instance to namespace browser"""
        self.ipyclient = ipyclient
        
    def setup_toolbar(self, exclude_private, exclude_uppercase,
                      exclude_capitalized, exclude_unsupported, autorefresh):
        """Setup toolbar"""
        self.setup_in_progress = True                          
                          
        toolbar = []

        refresh_button = create_toolbutton(self, text=_("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh_table)
        self.auto_refresh_button = create_toolbutton(self,
                                           text=_("Refresh periodically"),
                                           icon=get_icon('auto_reload.png'),
                                           toggled=self.toggle_auto_refresh)
        self.auto_refresh_button.setChecked(autorefresh)
        load_button = create_toolbutton(self, text=_("Import data"),
                                        icon=get_icon('fileimport.png'),
                                        triggered=self.import_data)
        self.save_button = create_toolbutton(self, text=_("Save data"),
                            icon=get_icon('filesave.png'),
                            triggered=lambda: self.save_data(self.filename))
        self.save_button.setEnabled(False)
        save_as_button = create_toolbutton(self,
                                           text=_("Save data as..."),
                                           icon=get_icon('filesaveas.png'),
                                           triggered=self.save_data)
        toolbar += [refresh_button, self.auto_refresh_button, load_button,
                    self.save_button, save_as_button]
        
        self.exclude_private_action = create_action(self,
                _("Exclude private references"),
                tip=_("Exclude references which name starts"
                            " with an underscore"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_private', state))
        self.exclude_private_action.setChecked(exclude_private)
        
        self.exclude_uppercase_action = create_action(self,
                _("Exclude all-uppercase references"),
                tip=_("Exclude references which name is uppercase"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_uppercase', state))
        self.exclude_uppercase_action.setChecked(exclude_uppercase)
        
        self.exclude_capitalized_action = create_action(self,
                _("Exclude capitalized references"),
                tip=_("Exclude references which name starts with an "
                      "uppercase character"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_capitalized', state))
        self.exclude_capitalized_action.setChecked(exclude_capitalized)
        
        self.exclude_unsupported_action = create_action(self,
                _("Exclude unsupported data types"),
                tip=_("Exclude references to unsupported data types"
                            " (i.e. which won't be handled/saved correctly)"),
                toggled=lambda state:
                self.sig_option_changed.emit('exclude_unsupported', state))
        self.exclude_unsupported_action.setChecked(exclude_unsupported)
        
        options_button = create_toolbutton(self, text=_("Options"),
                                           icon=get_icon('tooloptions.png'))
        toolbar.append(options_button)
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        editor = self.editor
        actions = [self.exclude_private_action, self.exclude_uppercase_action,
                   self.exclude_capitalized_action,
                   self.exclude_unsupported_action, None,
                   editor.truncate_action]
        if is_module_installed('numpy'):
            actions.append(editor.minmax_action)
        add_actions(menu, actions)
        options_button.setMenu(menu)
        
        self.setup_in_progress = False
        
        return toolbar

    def option_changed(self, option, value):
        """Option has changed"""
        setattr(self, to_text_string(option), value)
        if not self.is_internal_shell:
            settings = self.get_view_settings()
            communicate(self._get_sock(),
                        'set_remote_view_settings()', settings=[settings])

    def visibility_changed(self, enable):
        """Notify the widget whether its container (the namespace browser
        plugin is visible or not"""
        # This is slowing down Spyder a lot if too much data is present in
        # the Variable Explorer, and users give focus to it after being hidden.
        # This also happens when the Variable Explorer is visible and users
        # give focus to Spyder after using another application (like Chrome
        # or Firefox).
        # That's why we've decided to remove this feature
        # Fixes Issue 2593
        #
        # self.is_visible = enable
        # if enable:
        #     self.refresh_table()
        pass

    def toggle_auto_refresh(self, state):
        """Toggle auto refresh state"""
        self.autorefresh = state
        if not self.setup_in_progress and not self.is_internal_shell:
            communicate(self._get_sock(),
                        "set_monitor_auto_refresh(%r)" % state)
            
    def _get_sock(self):
        """Return socket connection"""
        return self.shellwidget.introspection_socket
    
    def get_internal_shell_filter(self, mode, check_all=None):
        """
        Return internal shell data types filter:
            * check_all: check all elements data types for sequences
              (dict, list, tuple)
            * mode (string): 'editable' or 'picklable'
        """
        assert mode in list(SUPPORTED_TYPES.keys())
        if check_all is None:
            check_all = self.check_all
        def wsfilter(input_dict, check_all=check_all,
                     filters=tuple(SUPPORTED_TYPES[mode])):
            """Keep only objects that can be pickled"""
            return globalsfilter(
                         input_dict, check_all=check_all, filters=filters,
                         exclude_private=self.exclude_private,
                         exclude_uppercase=self.exclude_uppercase,
                         exclude_capitalized=self.exclude_capitalized,
                         exclude_unsupported=self.exclude_unsupported,
                         excluded_names=self.excluded_names)
        return wsfilter

    def get_view_settings(self):
        """Return dict editor view settings"""
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = getattr(self, name)
        return settings
        
    def refresh_table(self):
        """Refresh variable table"""
        if self.is_visible and self.isVisible():
            if self.is_internal_shell:
                # Internal shell
                wsfilter = self.get_internal_shell_filter('editable')
                self.editor.set_filter(wsfilter)
                interpreter = self.shellwidget.interpreter
                if interpreter is not None:
                    self.editor.set_data(interpreter.namespace)
                    self.editor.adjust_columns()
            elif self.shellwidget.is_running():
    #            import time; print >>STDOUT, time.ctime(time.time()), "Refreshing namespace browser"
                sock = self._get_sock()
                if sock is None:
                    return
                try:
                    communicate(sock, "refresh()")
                except socket.error:
                    # Process was terminated before calling this method
                    pass                
                
    def process_remote_view(self, remote_view):
        """Process remote view"""
        if remote_view is not None:
            self.set_data(remote_view)
        
    #------ Remote Python process commands ------------------------------------
    def get_value(self, name):
        value = monitor_get_global(self._get_sock(), name)
        if value is None:
            if communicate(self._get_sock(), '%s is not None' % name):
                import pickle
                msg = to_text_string(_("Object <b>%s</b> is not picklable")
                                     % name)
                raise pickle.PicklingError(msg)
        return value
        
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
                           'isinstance(%s, (tuple, list))' % name)
        
    def is_dict(self, name):
        """Return True if variable is a dictionary"""
        return communicate(self._get_sock(), 'isinstance(%s, dict)' % name)
        
    def get_len(self, name):
        """Return sequence length"""
        return communicate(self._get_sock(), "len(%s)" % name)
        
    def is_array(self, name):
        """Return True if variable is a NumPy array"""
        return communicate(self._get_sock(), 'is_array("%s")' % name)
        
    def is_image(self, name):
        """Return True if variable is a PIL.Image image"""
        return communicate(self._get_sock(), 'is_image("%s")' % name)
    
    def is_data_frame(self, name):
        """Return True if variable is a data_frame"""
        return communicate(self._get_sock(),
             "isinstance(globals()['%s'], DataFrame)" % name)
    
    def is_time_series(self, name):
        """Return True if variable is a data_frame"""
        return communicate(self._get_sock(),
             "isinstance(globals()['%s'], TimeSeries)" % name)   
        
    def get_array_shape(self, name):
        """Return array's shape"""
        return communicate(self._get_sock(), "%s.shape" % name)
        
    def get_array_ndim(self, name):
        """Return array's ndim"""
        return communicate(self._get_sock(), "%s.ndim" % name)
        
    def plot(self, name, funcname):
        command = "import spyderlib.pyplot; "\
                  "__fig__ = spyderlib.pyplot.figure(); "\
                  "__items__ = getattr(spyderlib.pyplot, '%s')(%s); "\
                  "spyderlib.pyplot.show(); "\
                  "del __fig__, __items__;" % (funcname, name)
        if self.is_ipykernel:
            self.ipyclient.shellwidget.execute("%%varexp --%s %s" % (funcname,
                                                                   name))
        else:
            self.shellwidget.send_to_process(command)
        
    def imshow(self, name):
        command = "import spyderlib.pyplot; " \
                  "__fig__ = spyderlib.pyplot.figure(); " \
                  "__items__ = spyderlib.pyplot.imshow(%s); " \
                  "spyderlib.pyplot.show(); del __fig__, __items__;" % name
        if self.is_ipykernel:
            self.ipyclient.shellwidget.execute("%%varexp --imshow %s" % name)
        else:
            self.shellwidget.send_to_process(command)
        
    def show_image(self, name):
        command = "%s.show()" % name
        if self.is_ipykernel:
            self.ipyclient.shellwidget.execute(command)
        else:
            self.shellwidget.send_to_process(command)
        
    def oedit(self, name):
        command = "from spyderlib.widgets.objecteditor import oedit; " \
                  "oedit('%s', modal=False, namespace=locals());" % name
        self.shellwidget.send_to_process(command)
        
    #------ Set, load and save data -------------------------------------------
    def set_data(self, data):
        """Set data"""
        if data != self.editor.model.get_data():
            self.editor.set_data(data)
            self.editor.adjust_columns()
        
    def collapse(self):
        """Collapse"""
        self.emit(SIGNAL('collapse()'))
        
    def import_data(self, filenames=None):
        """Import data from text file"""
        title = _("Import data")
        if filenames is None:
            if self.filename is None:
                basedir = getcwd()
            else:
                basedir = osp.dirname(self.filename)
            filenames, _selfilter = getopenfilenames(self, title, basedir,
                                                     iofunctions.load_filters)
            if not filenames:
                return
        elif is_text_string(filenames):
            filenames = [filenames]

            
        for filename in filenames:
            
            self.filename = to_text_string(filename)
            ext = osp.splitext(self.filename)[1].lower()
            
            if ext not in iofunctions.load_funcs:
                buttons = QMessageBox.Yes | QMessageBox.Cancel
                answer = QMessageBox.question(self, title,
                            _("<b>Unsupported file extension '%s'</b><br><br>"
                              "Would you like to import it anyway "
                              "(by selecting a known file format)?"
                              ) % ext, buttons)
                if answer == QMessageBox.Cancel:
                    return
                formats = list(iofunctions.load_extensions.keys())
                item, ok = QInputDialog.getItem(self, title,
                                                _('Open file as:'),
                                                formats, 0, False)
                if ok:
                    ext = iofunctions.load_extensions[to_text_string(item)]
                else:
                    return

            load_func = iofunctions.load_funcs[ext]
                
            # 'import_wizard' (self.setup_io)
            if is_text_string(load_func):
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
                except Exception as error:
                    error_message = str(error)
            else:
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                QApplication.processEvents()
                if self.is_internal_shell:
                    namespace, error_message = load_func(self.filename)
                    interpreter = self.shellwidget.interpreter
                    for key in list(namespace.keys()):
                        new_key = fix_reference_name(key,
                                     blacklist=list(interpreter.namespace.keys()))
                        if new_key != key:
                            namespace[new_key] = namespace.pop(key)
                    if error_message is None:
                        interpreter.namespace.update(namespace)
                else:
                    error_message = monitor_load_globals(self._get_sock(),
                                                         self.filename, ext)
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
    
            if error_message is not None:
                QMessageBox.critical(self, title,
                                     _("<b>Unable to load '%s'</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (self.filename, error_message))
            self.refresh_table()
            
    
    def save_data(self, filename=None):
        """Save data"""
        if filename is None:
            filename = self.filename
            if filename is None:
                filename = getcwd()
            filename, _selfilter = getsavefilename(self, _("Save data"),
                                                   filename,
                                                   iofunctions.save_filters)
            if filename:
                self.filename = filename
            else:
                return False
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        if self.is_internal_shell:
            wsfilter = self.get_internal_shell_filter('picklable',
                                                      check_all=True)
            namespace = wsfilter(self.shellwidget.interpreter.namespace).copy()
            error_message = iofunctions.save(namespace, filename)
        else:
            settings = self.get_view_settings()
            error_message = monitor_save_globals(self._get_sock(),
                                                 settings, filename)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        if error_message is not None:
            QMessageBox.critical(self, _("Save data"),
                            _("<b>Unable to save current workspace</b>"
                              "<br><br>Error message:<br>%s") % error_message)
        self.save_button.setEnabled(self.filename is not None)
        
