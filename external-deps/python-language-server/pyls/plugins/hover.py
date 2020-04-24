# Copyright 2017 Palantir Technologies, Inc.
from distutils.version import LooseVersion
import logging

from pyls import hookimpl, _utils

log = logging.getLogger(__name__)


@hookimpl
def pyls_hover(document, position):
    definitions = document.jedi_script(position).goto_definitions()
    word = document.word_at_position(position)

    if LooseVersion(_utils.JEDI_VERSION) >= LooseVersion('0.15.0'):
        # Find first exact matching definition
        definition = next((x for x in definitions if x.name == word), None)

        # Ensure a definition is used if only one is available
        # even if the word doesn't match. An example of this case is 'np'
        # where 'numpy' doesn't match with 'np'. Same for NumPy ufuncs
        if len(definitions) == 1:
            definition = definitions[0]

        if not definition:
            return {'contents': ''}

        # raw docstring returns only doc, without signature
        doc = _utils.format_docstring(definition.docstring(raw=True))

        # Find first exact matching signature
        signature = next((x.to_string() for x in definition.get_signatures() if x.name == word), '')

        contents = []
        if signature:
            contents.append({
                'language': 'python',
                'value': signature,
            })
        if doc:
            contents.append(doc)
        if not contents:
            return {'contents': ''}
        return {'contents': contents}
    else:
        # Find an exact match for a completion
        for d in definitions:
            if d.name == word:
                return {'contents': _utils.format_docstring(d.docstring()) or ''}

        return {'contents': ''}
