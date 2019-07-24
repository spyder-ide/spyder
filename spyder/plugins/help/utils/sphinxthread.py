# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""SphinxThread used in richtext help plugin."""

# Third party imports
from qtpy.QtCore import QThread, Signal

# Local Imports
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.plugins.help.utils.sphinxify import (CSS_PATH, generate_context,
                                                 sphinxify)


class SphinxThread(QThread):
    """
    A worker thread for handling rich text rendering.
    Parameters
    ----------
    doc : str or dict
        A string containing a raw rst text or a dict containing
        the doc string components to be rendered.
        See spyder.utils.dochelpers.getdoc for description.
    context : dict
        A dict containing the substitution variables for the
        layout template
    html_text_no_doc : unicode
        Text to be rendered if doc string cannot be extracted.
    math_option : bool
        Use LaTeX math rendering.
    """
    # Signals
    error_msg = Signal(str)
    html_ready = Signal(str)

    def __init__(self, html_text_no_doc='', css_path=CSS_PATH):
        super(SphinxThread, self).__init__()
        self.doc = None
        self.context = None
        self.html_text_no_doc = html_text_no_doc
        self.math_option = False
        self.css_path = css_path

    def render(self, doc, context=None, math_option=False, img_path='',
               css_path=CSS_PATH):
        """Start thread to render a given documentation"""
        # If the thread is already running wait for it to finish before
        # starting it again.
        if self.wait():
            self.doc = doc
            self.context = context
            self.math_option = math_option
            self.img_path = img_path
            self.css_path = css_path
            # This causes run() to be executed in separate thread
            self.start()

    def run(self):
        html_text = self.html_text_no_doc
        doc = self.doc
        if doc is not None:
            if type(doc) is dict and 'docstring' in doc.keys():
                try:
                    context = generate_context(name=doc['name'],
                                               argspec=doc['argspec'],
                                               note=doc['note'],
                                               math=self.math_option,
                                               img_path=self.img_path,
                                               css_path=self.css_path)
                    html_text = sphinxify(doc['docstring'], context)
                    if doc['docstring'] == '':
                        if any([doc['name'], doc['argspec'], doc['note']]):
                            msg = _("No further documentation available")
                            html_text += '<div class="hr"></div>'
                        else:
                            msg = _("No documentation available")
                        html_text += '<div id="doc-warning">%s</div>' % msg
                except Exception as error:
                    self.error_msg.emit(to_text_string(error))
                    return
            elif self.context is not None:
                try:
                    html_text = sphinxify(doc, self.context)
                except Exception as error:
                    self.error_msg.emit(to_text_string(error))
                    return
        self.html_ready.emit(html_text)
