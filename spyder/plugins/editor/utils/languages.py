# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language utilities
"""

ALL_LANGUAGES = {
    'Python': ('py', 'pyw', 'python', 'pyt', 'pyi'),
    'IPython': ('ipy', 'ipython'),
    'Cython': ('pyx', 'pxi', 'pxd'),
    'Enaml': ('enaml',),
    'Fortran77': ('f', 'for', 'f77'),
    'Fortran': ('f90', 'f95', 'f2k', 'f03', 'f08'),
    'Idl': ('pro',),
    'Diff': ('diff', 'patch', 'rej'),
    'GetText': ('po', 'pot'),
    'Nsis': ('nsi', 'nsh'),
    'Html': ('htm', 'html'),
    'Cpp': ('c', 'cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx'),
    'OpenCL': ('cl',),
    'Yaml': ('yaml', 'yml'),
    'Markdown': ('md', 'mdw'),
    # Every other language
    'None': ('', ),
}

CELL_LANGUAGES = {'Python': ('#%%', '# %%', '# <codecell>', '# In['),
                  'IPython': ('#%%', '# %%', '# <codecell>', '# In[')}
