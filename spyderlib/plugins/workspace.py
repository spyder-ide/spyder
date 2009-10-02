# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Workspace widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QFileDialog, QMessageBox, QFontDialog, QMenu
from PyQt4.QtCore import SIGNAL

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import (CONF, get_conf_path, str2type, get_icon,
                              get_font, set_font)
from spyderlib.qthelpers import create_action, add_actions, translate
from spyderlib.io import (save_dictionary, load_dictionary, load_array,
                          load_image, load_dicom, load_matlab, save_matlab)
from spyderlib.widgets.dicteditor import DictEditorTableView, globalsfilter
from spyderlib.plugins import PluginMixin


FILTERS = tuple(str2type(CONF.get('workspace', 'filters')))
ITERMAX = CONF.get('workspace', 'itermax')

def wsfilter(input_dict, itermax=ITERMAX, filters=FILTERS):
    """Keep only objects that can be pickled"""
    exclude_private = CONF.get('workspace', 'exclude_private')
    exclude_upper = CONF.get('workspace', 'exclude_upper')
    exclude_unsupported = CONF.get('workspace', 'exclude_unsupported')
    excluded_names = CONF.get('workspace', 'excluded_names')
    return globalsfilter(input_dict, itermax=itermax, filters=filters,
                         exclude_private=exclude_private,
                         exclude_upper=exclude_upper,
                         exclude_unsupported=exclude_unsupported,
                         excluded_names=excluded_names)


class Workspace(DictEditorTableView, PluginMixin):
    """
    Workspace widget (namespace explorer)
    """
    ID = 'workspace'
    TEMPFILE_PATH = get_conf_path('.temp.spydata')
        
    def __init__(self, parent):
        self.interpreter = None
        self.namespace = None
        self.filename = None
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        DictEditorTableView.__init__(self, parent, None, names=True,
                                     truncate=truncate, inplace=inplace,
                                     minmax=minmax, collvalue=collvalue)
        PluginMixin.__init__(self, parent)
        
        self.setup_io()
        self.load_temp_namespace()
        
        self.setFont(get_font(self.ID))

    def setup_io(self):
        """Setup I/O functions and filters"""
        iofuncs = (
                   ('.spydata', translate('Workspace', "Spyder data files"),
                                load_dictionary, save_dictionary),
                   ('.npy',     translate('Workspace', "NumPy arrays"),
                                load_array, None),
                   ('.mat',     translate('Workspace', "Matlab files"),
                                load_matlab, save_matlab),
                   ('.csv',     translate('Workspace', "CSV text files"),
                                'import_wizard', None),
                   ('.txt',     translate('Workspace', "Text files"),
                                'import_wizard', None),
                   ('.jpg',     translate('Workspace', "JPEG images"),
                                load_image, None),
                   ('.png',     translate('Workspace', "PNG images"),
                                load_image, None),
                   ('.gif',     translate('Workspace', "GIF images"),
                                load_image, None),
                   ('.tif',     translate('Workspace', "TIFF images"),
                                load_image, None),
                   ('.dcm',     translate('Workspace', "DICOM images"),
                                load_dicom, None),
                   )
        load_funcs = {}
        save_funcs = {}
        load_filters = []
        save_filters = []
        load_ext = []
        for ext, name, loadfunc, savefunc in iofuncs:
            filter_str = unicode(name + " (*%s)" % ext)
            if loadfunc is not None:
                load_filters.append(filter_str)
                load_funcs[ext] = loadfunc
                load_ext.append(ext)
            if savefunc is not None:
                save_filters.append(filter_str)
                save_funcs[ext] = savefunc
        load_filters.insert(0, unicode(self.tr("Supported files")+" (*"+\
                                       " *".join(load_ext)+")"))
        self.load_filters = "\n".join(load_filters)
        self.save_filters = "\n".join(save_filters)
        self.load_funcs = load_funcs
        self.save_funcs = save_funcs
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Workspace')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self
        
    def set_interpreter(self, interpreter):
        """Bind to interpreter"""
        self.interpreter = interpreter
        self.refresh()
        
    def get_namespace(self, itermax=ITERMAX):
        """Return filtered namespace"""
        return wsfilter(self.namespace, itermax=itermax)
    
    def __clear_namespace(self):
        """Clear namespace"""
        keys = self.get_namespace().keys()
        for key in keys:
            self.namespace.pop(key)
        self.refresh()
    
    def clear(self):
        """Ask to clear workspace"""
        answer = QMessageBox.question(self, self.tr("Clear workspace"),
                    self.tr("Do you want to clear all data from workspace?"),
                    QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.__clear_namespace()

    def refresh(self):
        """Refresh widget"""
        if CONF.get(self.ID, 'autorefresh'):
            self.refresh_editor()
        
    def refresh_editor(self):
        """Refresh DictEditor"""
        if self.interpreter is not None:
            self.namespace = self.interpreter.namespace
        self.set_filter( wsfilter )
        self.set_data( self.namespace )
        self.adjust_columns()
        
    def set_actions(self):
        """Setup actions"""
        import_action = create_action(self, self.tr("Import data..."), None,
            'ws_open.png', self.tr("Import data to workspace"),
            triggered=self.import_data)
        save_as_action = create_action(self, self.tr("Save workspace as..."),
            None, 'ws_save_as.png',  self.tr("Save workspace as..."),
            triggered = self.save_as)
        exclude_private_action = create_action(self,
            self.tr("Exclude private references"),
            tip=self.tr("Exclude references which name starts"
                        " with an underscore"),
            toggled=self.toggle_exclude_private)
        exclude_private_action.setChecked(CONF.get(self.ID, 'exclude_private'))
        exclude_upper_action = create_action(self,
            self.tr("Exclude capitalized references"),
            tip=self.tr("Exclude references which name starts with an "
                        "upper-case character"),
            toggled=self.toggle_exclude_upper)
        exclude_upper_action.setChecked( CONF.get(self.ID, 'exclude_upper') )
        exclude_unsupported_action = create_action(self,
            self.tr("Exclude unsupported data types"),
            tip=self.tr("Exclude references to unsupported data types"
                        " (i.e. which won't be handled/saved correctly)"),
            toggled=self.toggle_exclude_unsupported)
        exclude_unsupported_action.setChecked(CONF.get(self.ID,
                                              'exclude_unsupported'))

        refresh_action = create_action(self, self.tr("Refresh workspace"),
            None, 'ws_refresh.png', self.tr("Refresh workspace"),
            triggered = self.refresh_editor)
        
        autorefresh_action = create_action(self, self.tr("Auto refresh"),
                                           toggled=self.toggle_autorefresh)
        autorefresh_action.setChecked( CONF.get(self.ID, 'autorefresh') )
        
        autosave_action = create_action(self, self.tr("Auto save"),
            toggled=self.toggle_autosave,
            tip=self.tr("Automatically save workspace in a temporary file"
                        " when quitting"))
        autosave_action.setChecked( CONF.get(self.ID, 'autosave') )
        
        clear_action = create_action(self, self.tr("Clear workspace"),
                                 icon=get_icon('clear.png'),
                                 tip=self.tr("Clear all data from workspace"),
                                 triggered=self.clear)
        font_action1 = create_action(self, self.tr("Header Font..."),
                                     None, 'font.png',
                                     self.tr("Set font style"),
                                     triggered=self.change_font1)
        font_action2 = create_action(self, self.tr("Value Font..."),
                                     None, 'font.png',
                                     self.tr("Set font style"),
                                     triggered=self.change_font2)
        
        option_menu = QMenu(self.tr("Workspace settings"), self)
        option_menu.setIcon(get_icon('tooloptions.png'))
        add_actions(option_menu, (autosave_action, None,
                           self.truncate_action, self.inplace_action, None,
                           exclude_private_action, exclude_upper_action,
                           exclude_unsupported_action,
                           font_action1, font_action2))
        menu_actions = (import_action, save_as_action,
                        refresh_action, autorefresh_action, clear_action,
                        option_menu)
        toolbar_actions = (refresh_action, import_action, save_as_action)
        return (menu_actions, toolbar_actions)
        
    def change_font1(self):
        """Change font"""
        self.__change_font('dicteditor_header')
        
    def change_font2(self):
        """Change font"""
        self.__change_font('dicteditor')
    
    def __change_font(self, section):
        font, valid = QFontDialog.getFont(get_font(section), self,
                                          self.tr("Select a new font"))
        if valid:
            set_font(font, section)
    
    def toggle_autorefresh(self, checked):
        """Toggle autorefresh mode"""
        CONF.set(self.ID, 'autorefresh', checked)
        self.refresh()
        
    def toggle_autosave(self, checked):
        """Toggle autosave mode"""
        CONF.set(self.ID, 'autosave', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        if CONF.get(self.ID, 'autosave'):
            # Saving workspace
            self.__save(self.TEMPFILE_PATH)
        else:
            workspace = self.get_namespace(itermax=-1)
            if workspace is None:
                return True
            refnb = len(workspace)
            if refnb > 1:
                srefnb = str(refnb)
                s_or_not = 's'
                it_or_them = self.tr('them')
            else:
                srefnb = self.tr('one')
                s_or_not = ''
                it_or_them = self.tr('it')
            if refnb > 0:
                buttons = QMessageBox.Yes | QMessageBox.No
                if cancelable:
                    buttons = buttons | QMessageBox.Cancel
                answer = QMessageBox.question(self, self.get_widget_title(),
                   self.tr("Workspace is currently keeping reference "
                           "to %1 object%2.\n\nDo you want to save %3?") \
                   .arg(srefnb).arg(s_or_not).arg(it_or_them), buttons)
                if answer == QMessageBox.Yes:
                    # Saving workspace
                    self.__save(self.TEMPFILE_PATH)
                elif answer == QMessageBox.Cancel:
                    return False
                elif osp.isfile(self.TEMPFILE_PATH):
                    # Removing last saved workspace
                    os.remove(self.TEMPFILE_PATH)
        return True
    
    def load_temp_namespace(self):
        """Attempt to load last session namespace"""
        self.filename = unicode(self.TEMPFILE_PATH)
        if osp.isfile(self.filename):
            self.import_data(self.filename)
        else:
            self.namespace = None
            self.refresh()

    def import_data(self, filename=None):
        """
        Import data from workspace
        or other data type (not implemented yet)
        """
        title = self.tr("Import data")
        if filename is None:
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          title, basedir, self.load_filters)
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            if filename:
                filename = unicode(filename)
            else:
                return
        self.filename = unicode(filename)
        ext = osp.splitext(self.filename)[1]
        
        if ext not in self.load_funcs:
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
            load_func = self.load_funcs[ext]
            
        if isinstance(load_func, basestring): # 'import_wizard' (self.setup_io)
            # Import data with import wizard
            error_message = None
            try:
                from spyderlib import encoding
                text, _encoding = encoding.read(self.filename)
                self.import_from_string(text)
            except Exception, error:
                error_message = str(error)
        else:
            self.starting_long_process(self.tr("Loading data..."))
            namespace, error_message = load_func(self.filename)
            self.ending_long_process()           
            if error_message is None:
                if self.namespace is None:
                    self.namespace = namespace
                else:
                    self.interpreter.namespace.update(namespace)

        if error_message is not None:
            QMessageBox.critical(self, title,
                                 self.tr("<b>Unable to load '%1'</b>"
                                         "<br><br>Error message:<br>%2") \
                                         .arg(self.filename).arg(error_message))
        self.refresh()

    def save_as(self):
        """Save current workspace as"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save workspace"), self.filename,
                      self.save_filters)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            self.filename = unicode(filename)
            return self.__save(self.filename)
        else:
            return False
    
    def __save(self, filename):
        """Save workspace"""
        title = self.tr("Save workspace")
        
        ext = osp.splitext(filename)[1]
        if ext not in self.save_funcs:
            QMessageBox.critical(self, title,
                                 self.tr("<b>Unsupported file type '%1'</b>") \
                                         .arg(ext))
            return
        
        self.starting_long_process(self.tr("Saving workspace..."))
        namespace = self.get_namespace(itermax=-1).copy()
        error_message = self.save_funcs[ext](namespace, filename)
        self.ending_long_process()
        
        if error_message is not None:
            QMessageBox.critical(self, title,
                            self.tr("<b>Unable to save current workspace</b>"
                                    "<br><br>Error message:<br>%1") \
                            .arg(error_message))
            
        self.refresh()
        return True

    def toggle_exclude_private(self, checked):
        """Toggle exclude private references"""
        CONF.set(self.ID, 'exclude_private', checked)
        self.refresh()
        
    def toggle_exclude_upper(self, checked):
        """Toggle exclude upper-case references"""
        CONF.set(self.ID, 'exclude_upper', checked)
        self.refresh()

    def toggle_exclude_unsupported(self, checked):
        """Toggle exclude unsupported datatypes"""
        CONF.set(self.ID, 'exclude_unsupported', checked)
        self.refresh()

    #----Focus
    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        DictEditorTableView.focusInEvent(self, event)
        
    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        DictEditorTableView.focusOutEvent(self, event)
