# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
# Copyright (C) 2010- Spyder Project Contributors
#
# Distributed under the terms of the Modified BSD License
# (BSD 3-clause; see NOTICE.txt in the Spyder root directory for details).
# -----------------------------------------------------------------------------

"""
Sphinx configuration file for the Help plugin rich text mode.

Originally based on a portion of sagenb/misc/sphinxify.py from the
`Sage Notebook project <https://github.com/sagemath/sagenb>`_,
part of the `SageMath <https://www.sagemath.org/>`_ system.
"""

# Third party imports
from sphinx import __version__ as sphinx_version

# Local imports
from spyder.config.manager import CONF


#==============================================================================
# General configuration
#==============================================================================

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.

# We need jsmath to get pretty plain-text latex in docstrings
math = CONF.get('help', 'math', '')

if sphinx_version < "1.1" or not math:
    extensions = ['sphinx.ext.jsmath']
else:
    extensions = ['sphinx.ext.mathjax']

# For scipy and matplotlib docstrings, which need this extension to
# be rendered correctly. See spyder-ide/spyder#1138.
extensions.append('sphinx.ext.autosummary')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# MathJax load path (doesn't have effect for sphinx 1.0-)
mathjax_path = 'MathJax/MathJax.js'

# JsMath load path (doesn't have effect for sphinx 1.1+)
jsmath_path = 'easy/load.js'

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'docstring'

# General information about the project.
project = u"Spyder Help plugin"
copyright = u'The Spyder Project Contributors'

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

# The reST default role (used for this markup: `text`) to use for all documents.
#
# TODO: This role has to be set on a per project basis, i.e. numpy, sympy,
# mpmath, etc, use different default_role's which give different rendered
# docstrings. Setting this to None until it's solved.
default_role = 'None'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

#==============================================================================
# Options for HTML output
#==============================================================================

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# A dictionary of values to pass into the template engine’s context for all
# pages
html_context = {}

# If true, Smart Quotes will be used to convert quotes and dashes to
# typographically correct entities.
# Spyder: Disabled to fix conflict with qtwebview and mathjax.
# See spyder-ide/spyder#5514.
if sphinx_version < "1.7":
    html_use_smartypants = False
else:
    smartquotes = False

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

