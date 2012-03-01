# -*- coding: utf-8 -*
#!/usr/bin/env python
r"""
Process docstrings with Sphinx

Processes docstrings with Sphinx. Can also be used as a commandline script:

``python sphinxify.py <text>``

AUTHORS:
- Tim Joseph Dumol (2009-09-29): initial version
- The Spyder Team: Several changes to make it work with Spyder

Copyright (C) 2009 Tim Dumol <tim@timdumol.com>
Copyright (C) 2012 The Spyder Development Team
Distributed under the terms of the BSD License

Taken from the Sage project (www.sagemath.org).
See here for the original version:
www.sagemath.org/doc/reference/sagenb/misc/sphinxify.html
"""

# Stdlib imports
import codecs
import os
import os.path as osp
import re
import shutil
from tempfile import mkdtemp

# 3rd party imports
from jinja2 import Environment, FileSystemLoader
from sphinx.application import Sphinx #@UnusedImport
from docutils.utils import SystemMessage as SystemMessage

# Local imports
from spyderlib.baseconfig import get_module_source_path, _

# Note: we do not use __file__ because it won't be working in the stand-alone
# version of Spyder (i.e. the py2exe or cx_Freeze build)
CSS_PATH = osp.join(get_module_source_path('spyderlib.utils.inspector'), 'css')
TEMPLATES_PATH = osp.join(get_module_source_path('spyderlib.utils.inspector'),
                          'templates')


def is_sphinx_markup(docstring):
    """Returns whether a string contains Sphinx-style ReST markup."""
    
    # this could be made much more clever
    return ("`" in docstring or "::" in docstring)

def warning(message):
    env = Environment(loader=FileSystemLoader(TEMPLATES_PATH))
    warning = env.get_template("warning.html")
    return warning.render(css_path=CSS_PATH, text=message)

def sphinxify(docstring, format='html'):
    """
    Runs Sphinx on a docstring and outputs the processed documentation.

    Parameters
    ==========

    docstring : str
        a ReST-formatted docstring

    format:  str
        It can be either `html` or `text`.

    Returns
    =======

    An Sphinx-processed string, in either HTML or plain text format, depending
    on the value of `format`
    """
    global Sphinx
    if not Sphinx:
        from sphinx.application import Sphinx

    srcdir = mkdtemp()
    base_name = osp.join(srcdir, 'docstring')
    rst_name = base_name + '.rst'

    if format == 'html':
        suffix = '.html'
    else:
        suffix = '.txt'
    output_name = base_name + suffix

    # This is needed for jsMath to work.
    docstring = docstring.replace('\\\\', '\\')

    filed = codecs.open(rst_name, 'w', encoding='utf-8')
    filed.write(docstring)
    filed.close()

    # Sphinx constructor: Sphinx(srcdir, confdir, outdir, doctreedir,
    # buildername, confoverrides, status, warning, freshenv).
    
    # This may be inefficient.
    # TODO: Find a faster way to do it.
    temp_confdir = True
    confdir = mkdtemp()
    generate_configuration(confdir)

    doctreedir = osp.join(srcdir, 'doctrees')
    confoverrides = {'master_doc': 'docstring'}

    sphinx_app = Sphinx(srcdir, confdir, srcdir, doctreedir, format,
                        confoverrides, None, None, True)
    try:
        sphinx_app.build(None, [rst_name])
    except SystemMessage:
        output = _("It was not possible to generate rich text help for this "
                    "object.</br>"
                    "Please see it in plain text.")
        return warning(output)

    if osp.exists(output_name):
        output = codecs.open(output_name, 'r', encoding='utf-8').read()
        output = output.replace('<pre>', '<pre class="literal-block">')

        # Translate URLs for media from something like
        #    "../../media/...path.../blah.png"
        # or
        #    "/media/...path.../blah.png"
        # to
        #    "/doc/static/reference/media/...path.../blah.png"
        output = re.sub("""src=['"](/?\.\.)*/?media/([^"']*)['"]""",
                          'src="/doc/static/reference/media/\\2"',
                          output)
    else:
        print "BUG -- Sphinx error"
        if format == 'html':
            output = '<pre class="introspection">%s</pre>' % docstring
        else:
            output = docstring

    if temp_confdir:
        shutil.rmtree(confdir, ignore_errors=True)
    shutil.rmtree(srcdir, ignore_errors=True)

    return output


def generate_configuration(directory):
    """
    Generates a Sphinx configuration in `directory`.

    Parameters
    ==========

    directory : str
        Base directory to use
    """
    
    # conf.py file for Sphinx
    conf = osp.join(get_module_source_path('spyderlib.utils.inspector'),
                    'conf.py')

    # Docstring layout page (in Jinja):
    layout = osp.join(TEMPLATES_PATH, 'layout.html')
    
    os.makedirs(osp.join(directory, 'templates'))
    os.makedirs(osp.join(directory, 'static'))
    shutil.copy(conf, directory)
    shutil.copy(layout, osp.join(directory, 'templates'))
    open(osp.join(directory, '__init__.py'), 'w').write('')
    open(osp.join(directory, 'static', 'empty'), 'w').write('')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print sphinxify(sys.argv[1])
    else:
        print """Usage:
%s 'docstring'

docstring -- docstring to be processed
"""
