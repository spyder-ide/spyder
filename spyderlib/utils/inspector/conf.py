# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
# Copyright (C) 2012 The Spyder Team
# Distributed under the terms of the BSD License

"""Sphinx conf file for the object inspector rich text mode"""

# 3rd party imports
import sphinx

#==============================================================================
# General configuration
#==============================================================================

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.

# We need jsmath for 1.0- so that we can get plain text latex in docstrings
if sphinx.__version__ <= "1.0":
    extensions = ['sphinx.ext.autodoc', 'sphinx.ext.jsmath']
else:
    extensions = ['sphinx.ext.autodoc', 'sphinx.ext.mathjax']

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
project = u"Object Inspector"
copyright = u'2009--2012, The Spyder Development Team'

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

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

#==============================================================================
# Process docstring
#==============================================================================

def process_docstring_aliases(app, what, name, obj, options, docstringlines):
    """
    Change the docstrings for aliases to point to the original object.
    """
    basename = name.rpartition('.')[2]
    if hasattr(obj, '__name__') and obj.__name__ != basename:
        docstringlines[:] = ['See :obj:`%s`.' % name]

def process_directives(app, what, name, obj, options, docstringlines):
    """
    Remove 'nodetex' and other directives from the first line of any
    docstring where they appear.
    """
    if len(docstringlines) == 0:
        return
    first_line = docstringlines[0]
    directives = [ d.lower() for d in first_line.split(',') ]
    if 'nodetex' in directives:
        docstringlines.pop(0)

def process_docstring_cython(app, what, name, obj, options, docstringlines):
    """
    Remove Cython's filename and location embedding.
    """
    if len(docstringlines) <= 1:
        return

    first_line = docstringlines[0]
    if first_line.startswith('File:') and '(starting at' in first_line:
        #Remove the first two lines
        docstringlines.pop(0)
        docstringlines.pop(0)

def process_docstring_module_title(app, what, name, obj, options, docstringlines):
    """
    Removes the first line from the beginning of the module's docstring.  This
    corresponds to the title of the module's documentation page.
    """
    if what != "module":
        return

    #Remove any additional blank lines at the beginning
    title_removed = False
    while len(docstringlines) > 1 and not title_removed:
        if docstringlines[0].strip() != "":
            title_removed = True
        docstringlines.pop(0)

    #Remove any additional blank lines at the beginning
    while len(docstringlines) > 1:
        if docstringlines[0].strip() == "":
            docstringlines.pop(0)
        else:
            break

def setup(app):
    app.connect('autodoc-process-docstring', process_docstring_cython)
    app.connect('autodoc-process-docstring', process_directives)
    app.connect('autodoc-process-docstring', process_docstring_module_title)
    