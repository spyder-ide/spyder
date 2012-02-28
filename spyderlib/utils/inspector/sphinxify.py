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
from sphinx.application import Sphinx #@UnusedImport
from docutils.utils import SystemMessage as SystemMessage

# Local imports
from spyderlib.baseconfig import get_module_source_path

# Note: we do not use __file__ because it won't be working in the stand-alone
# version of Spyder (i.e. the py2exe or cx_Freeze build)
CSS_PATH = osp.join(get_module_source_path('spyderlib.utils.inspector'), 'css')


def is_sphinx_markup(docstring):
    """
    Returns whether a string that contains Sphinx-style ReST markup.

    INPUT:

    - ``docstring`` - string to test for markup

    OUTPUT:

    - boolean
    """
    # this could be made much more clever
    return ("`" in docstring or "::" in docstring)


def sphinxify(docstring, format='html'):
    r"""
    Runs Sphinx on a ``docstring``, and outputs the processed
    documentation.

    INPUT:

    - ``docstring`` -- string -- a ReST-formatted docstring

    - ``format`` -- string (optional, default 'html') -- either 'html' or
      'text'

    OUTPUT:

    - string -- Sphinx-processed documentation, in either HTML or
      plain text format, depending on the value of ``format``

    EXAMPLES::

        >>> from spyderlib.plugins.sphinxify import sphinxify
        >>> sphinxify('A test')
        '\n<div class="docstring">\n    \n  <p>A test</p>\n\n\n</div>'
        >>> sphinxify('**Testing**\n`monospace`')
        '\n<div class="docstring">\n    \n  <p><strong>Testing</strong>\n<span class="math">monospace</span></p>\n\n\n</div>'
        >>> sphinxify('`x=y`')
        '\n<div class="docstring">\n    \n  <p><span class="math">x=y</span></p>\n\n\n</div>'
        >>> sphinxify('`x=y`', format='text')
        'x=y\n'
        >>> sphinxify(':math:`x=y`', format='text')
        'x=y\n'
    """
    global Sphinx
    if not Sphinx:
        from sphinx.application import Sphinx

    srcdir = mkdtemp()
    base_name = os.path.join(srcdir, 'docstring')
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

    doctreedir = os.path.join(srcdir, 'doctrees')
    confoverrides = {'master_doc': 'docstring'}

    sphinx_app = Sphinx(srcdir, confdir, srcdir, doctreedir, format,
                        confoverrides, None, None, True)
    try:
        sphinx_app.build(None, [rst_name])
    except SystemMessage:
        output = '<div id=\"warning\"> \
        It\'s not possible to generate rich text help for this object. \
        Please see it in plain text. \
        </div>'
        return output

    if os.path.exists(output_name):
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
    r"""
    Generates a Sphinx configuration in ``directory``.

    INPUT:

    - ``directory`` - string, base directory to use

    EXAMPLES::

        >>> from spyderlib.plugins.sphinxify import generate_configuration
        >>> import tempfile, os
        >>> tmpdir = tempfile.mkdtemp()
        >>> generate_configuration(tmpdir)
        >>> open(os.path.join(tmpdir, 'conf.py')).read()
        '\n...extensions =...templates_path...source = False\n...'
    """
    
    conf = osp.join(get_module_source_path('spyderlib.utils.inspector'),
                    'conf.py')

    # Docstring layout page (in Jinja):
    layout = osp.join(get_module_source_path('spyderlib.utils.inspector'),
                           'templates', 'layout.html')
    
    os.makedirs(os.path.join(directory, 'templates'))
    os.makedirs(os.path.join(directory, 'static'))
    shutil.copy(conf, os.path.join(directory, 'conf.py'))
    shutil.copy(layout, os.path.join(directory, 'templates'))
    open(os.path.join(directory, '__init__.py'), 'w').write('')
    open(os.path.join(directory, 'static', 'empty'), 'w').write('')

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print sphinxify(sys.argv[1])
    else:
        print """Usage:
%s 'docstring'

docstring -- docstring to be processed
"""
