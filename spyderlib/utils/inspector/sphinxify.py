# -*- coding: utf-8 -*

"""
Process docstrings with Sphinx

AUTHORS:
- Tim Joseph Dumol (2009-09-29): initial version
- The Spyder Development Team: Several changes to make it work with Spyder

Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
Copyright (C) 2013 The Spyder Development Team
Distributed under the terms of the BSD License

Taken from the Sage project (www.sagemath.org).
See here for the original version:
www.sagemath.org/doc/reference/sagenb/misc/sphinxify.html
"""

# Stdlib imports
import codecs
import os
import os.path as osp
import shutil
import sys
from tempfile import mkdtemp

# 3rd party imports
from docutils.utils import SystemMessage as SystemMessage
from jinja2 import Environment, FileSystemLoader
import sphinx
from sphinx.application import Sphinx

# Local imports
from spyderlib.baseconfig import (_, get_module_data_path,
                                  get_module_source_path)
from spyderlib.utils import encoding


#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

# Note: we do not use __file__ because it won't be working in the stand-alone
# version of Spyder (i.e. the py2exe or cx_Freeze build)
CONFDIR_PATH = get_module_source_path('spyderlib.utils.inspector')
CSS_PATH = osp.join(CONFDIR_PATH, 'static', 'css')
JS_PATH = osp.join(CONFDIR_PATH, 'js')

# To let Debian packagers redefine the MathJax and JQuery locations so they can
# use their own packages for them. See Issue 1230, comment #7.
MATHJAX_PATH = get_module_data_path('spyderlib',
                                    relpath=osp.join('utils', 'inspector',
                                                     JS_PATH, 'mathjax'),
                                    attr_name='MATHJAXPATH')

JQUERY_PATH = get_module_data_path('spyderlib',
                                   relpath=osp.join('utils', 'inspector',
                                                    JS_PATH),
                                   attr_name='JQUERYPATH')

#-----------------------------------------------------------------------------
# Utility functions
#-----------------------------------------------------------------------------

def is_sphinx_markup(docstring):
    """Returns whether a string contains Sphinx-style ReST markup."""
    # this could be made much more clever
    return ("`" in docstring or "::" in docstring)


def warning(message):
    """Print a warning message on the rich text view"""
    env = Environment()
    env.loader = FileSystemLoader(osp.join(CONFDIR_PATH, 'templates'))
    warning = env.get_template("warning.html")
    return warning.render(css_path=CSS_PATH, text=message)


def usage(title, message, tutorial_message, tutorial):
    """Print a usage message on the rich text view"""
    env = Environment()
    env.loader = FileSystemLoader(osp.join(CONFDIR_PATH, 'templates'))
    usage = env.get_template("usage.html")
    return usage.render(css_path=CSS_PATH, title=title, intro_message=message,
                        tutorial_message=tutorial_message, tutorial=tutorial)


def generate_context(name='', argspec='', note='', math=False, collapse=False,
                     img_path=''):
    """
    Generate the html_context dictionary for our Sphinx conf file.
    
    This is a set of variables to be passed to the Jinja template engine and
    that are used to control how the webpage is rendered in connection with
    Sphinx

    Parameters
    ----------
    name : str
        Object's name.
    note : str
        A note describing what type has the function or method being
        introspected
    argspec : str
        Argspec of the the function or method being introspected
    math : bool
        Turn on/off Latex rendering on the OI. If False, Latex will be shown in
        plain text.
    collapse : bool
        Collapse sections
    
    Returns
    -------
    A dict of strings to be used by Jinja to generate the webpage
    """
    
    context = \
    {
      # Arg dependent variables
      'math_on': 'true' if math else '',
      'name': name,
      'argspec': argspec,
      'note': note,
      'collapse': collapse,
      'img_path': img_path,
      
      # Static variables
      'css_path': CSS_PATH,
      'js_path': JS_PATH,
      'jquery_path': JQUERY_PATH,
      'mathjax_path': MATHJAX_PATH,
      'right_sphinx_version': '' if sphinx.__version__ < "1.1" else 'true',
      'platform': sys.platform
    }
    
    return context


def sphinxify(docstring, context, buildername='html'):
    """
    Runs Sphinx on a docstring and outputs the processed documentation.

    Parameters
    ----------
    docstring : str
        a ReST-formatted docstring

    context : dict
        Variables to be passed to the layout template to control how its
        rendered (through the Sphinx variable *html_context*).

    buildername:  str
        It can be either `html` or `text`.

    Returns
    -------
    An Sphinx-processed string, in either HTML or plain text format, depending
    on the value of `buildername`
    """

    srcdir = mkdtemp()
    srcdir = encoding.to_unicode_from_fs(srcdir)

    base_name = osp.join(srcdir, 'docstring')
    rst_name = base_name + '.rst'

    if buildername == 'html':
        suffix = '.html'
    else:
        suffix = '.txt'
    output_name = base_name + suffix

    # This is needed so users can type \\ on latex eqnarray envs inside raw
    # docstrings
    if context['right_sphinx_version'] and context['math_on']:
        docstring = docstring.replace('\\\\', '\\\\\\\\')
    
    # Add a class to several characters on the argspec. This way we can
    # highlight them using css, in a similar way to what IPython does.
    argspec = context['argspec']
    for char in ['=', ',', '(', ')', '*', '**']:
        argspec = argspec.replace(char,
                         '<span class="argspec-highlight">' + char + '</span>')
    context['argspec'] = argspec

    doc_file = codecs.open(rst_name, 'w', encoding='utf-8')
    doc_file.write(docstring)
    doc_file.close()
    
    temp_confdir = False
    if temp_confdir:
        # TODO: This may be inefficient. Find a faster way to do it.
        confdir = mkdtemp()
        confdir = encoding.to_unicode_from_fs(confdir)
        generate_configuration(confdir)
    else:
        confdir = osp.join(get_module_source_path('spyderlib.utils.inspector'))

    confoverrides = {'html_context': context}

    doctreedir = osp.join(srcdir, 'doctrees')

    sphinx_app = Sphinx(srcdir, confdir, srcdir, doctreedir, buildername,
                        confoverrides, status=None, warning=None,
                        freshenv=True, warningiserror=False, tags=None)
    try:
        sphinx_app.build(None, [rst_name])
    except SystemMessage:
        output = _("It was not possible to generate rich text help for this "
                    "object.</br>"
                    "Please see it in plain text.")
        return warning(output)

    # TODO: Investigate if this is necessary/important for us
    if osp.exists(output_name):
        output = codecs.open(output_name, 'r', encoding='utf-8').read()
        output = output.replace('<pre>', '<pre class="literal-block">')
    else:
        output = _("It was not possible to generate rich text help for this "
                    "object.</br>"
                    "Please see it in plain text.")
        return warning(output)

    if temp_confdir:
        shutil.rmtree(confdir, ignore_errors=True)
    shutil.rmtree(srcdir, ignore_errors=True)

    return output


def generate_configuration(directory):
    """
    Generates a Sphinx configuration in `directory`.

    Parameters
    ----------
    directory : str
        Base directory to use
    """
    
    # conf.py file for Sphinx
    conf = osp.join(get_module_source_path('spyderlib.utils.inspector'),
                    'conf.py')

    # Docstring layout page (in Jinja):
    layout = osp.join(osp.join(CONFDIR_PATH, 'templates'), 'layout.html')
    
    os.makedirs(osp.join(directory, 'templates'))
    os.makedirs(osp.join(directory, 'static'))
    shutil.copy(conf, directory)
    shutil.copy(layout, osp.join(directory, 'templates'))
    open(osp.join(directory, '__init__.py'), 'w').write('')
    open(osp.join(directory, 'static', 'empty'), 'w').write('')
