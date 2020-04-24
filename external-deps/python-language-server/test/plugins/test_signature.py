# Copyright 2017 Palantir Technologies, Inc.
import pytest
from pyls import uris
from pyls.plugins import signature
from pyls.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def main(param1, param2):
    \"\"\" Main docstring

    Args:
        param1 (str): Docs for param1
    \"\"\"
    raise Exception()

main(
"""

MULTI_LINE_DOC = """import sys

def main(param1=None,
            param2=None,
            param3=None,
            param4=None,
            param5=None,
            param6=None,
            param7=None,
            param8=None):
    \"\"\" Main docstring

    Args:
        param1 (str): Docs for param1
    \"\"\"
    raise Exception()

main(
"""


def test_no_signature():
    # Over blank line
    sig_position = {'line': 9, 'character': 0}
    doc = Document(DOC_URI, DOC)

    sigs = signature.pyls_signature_help(doc, sig_position)['signatures']
    assert not sigs


def test_signature():
    # Over '( ' in main(
    sig_position = {'line': 10, 'character': 5}
    doc = Document(DOC_URI, DOC)

    sig_info = signature.pyls_signature_help(doc, sig_position)

    sigs = sig_info['signatures']
    assert len(sigs) == 1
    assert sigs[0]['label'] == 'main(param1, param2)'
    assert sigs[0]['parameters'][0]['label'] == 'param1'
    assert sigs[0]['parameters'][0]['documentation'] == 'Docs for param1'

    assert sig_info['activeParameter'] == 0


def test_multi_line_signature():
    # Over '( ' in main(
    sig_position = {'line': 17, 'character': 5}
    doc = Document(DOC_URI, MULTI_LINE_DOC)

    sig_info = signature.pyls_signature_help(doc, sig_position)

    sigs = sig_info['signatures']
    assert len(sigs) == 1
    assert sigs[0]['label'] == (
        'main(param1=None, param2=None, param3=None, param4=None, '
        'param5=None, param6=None, param7=None, param8=None)'
    )
    assert sigs[0]['parameters'][0]['label'] == 'param1'
    assert sigs[0]['parameters'][0]['documentation'] == 'Docs for param1'

    assert sig_info['activeParameter'] == 0


@pytest.mark.parametrize('regex,doc', [
    (signature.SPHINX, "    :param test: parameter docstring"),
    (signature.EPYDOC, "    @param test: parameter docstring"),
    (signature.GOOGLE, "    test (str): parameter docstring")
])
def test_docstring_params(regex, doc):
    m = regex.match(doc)
    assert m.group('param') == "test"
    assert m.group('doc') == "parameter docstring"
