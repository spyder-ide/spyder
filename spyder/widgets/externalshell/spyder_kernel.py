# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder kernel for Jupyter
"""

# Third-party imports
from ipykernel.ipkernel import IPythonKernel

# Local imports
from spyder.widgets.variableexplorer.utils import make_remote_view


class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter"""

    def __init__(self, *args, **kwargs):
        super(SpyderKernel, self).__init__(*args, **kwargs)
        self.pdb_frame = None
        self.pdb_locals = {}
        self.remote_view_settings = {}

    def update_remote_view(self):
        """Return namespace view

        This is going to be rendered by the NamespaceBrowser
        widget
        """
        settings = self.remote_view_settings
        if settings:
            ns = self.get_current_namespace()
            more_excluded_names = ['In', 'Out']
            remote_view = make_remote_view(ns, settings, more_excluded_names)
            return remote_view

    def get_current_namespace(self, with_magics=False):
        """
        Return current namespace

        This is globals() if not debugging, or a dictionary containing
        both locals() and globals() for current frame when debugging
        """
        ns = {}
        glbs = self.mglobals()

        if self.pdb_frame is None:
            ns.update(glbs)
        else:
            ns.update(glbs)
            ns.update(self.pdb_locals)

        # Add magics to ns so we can show help about them on the Help
        # plugin
        if with_magics:
            line_magics = self.shell.magics_manager.magics['line']
            cell_magics = self.shell.magics_manager.magics['cell']
            ns.update(line_magics)
            ns.update(cell_magics)

        return ns

    def mglobals(self):
        """Return current globals -- handles Pdb frames"""
        if self.pdb_frame is not None:
            return self.pdb_frame.f_globals
        else:
            return self.shell.user_ns
