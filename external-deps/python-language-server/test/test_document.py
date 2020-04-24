# Copyright 2017 Palantir Technologies, Inc.
from test.fixtures import DOC_URI, DOC
from pyls.workspace import Document


def test_document_props(doc):
    assert doc.uri == DOC_URI
    assert doc.source == DOC


def test_document_lines(doc):
    assert len(doc.lines) == 4
    assert doc.lines[0] == 'import sys\n'


def test_document_source_unicode():
    document_mem = Document(DOC_URI, u'my source')
    document_disk = Document(DOC_URI)
    assert isinstance(document_mem.source, type(document_disk.source))


def test_offset_at_position(doc):
    assert doc.offset_at_position({'line': 0, 'character': 8}) == 8
    assert doc.offset_at_position({'line': 1, 'character': 5}) == 16
    assert doc.offset_at_position({'line': 2, 'character': 0}) == 12
    assert doc.offset_at_position({'line': 2, 'character': 4}) == 16
    assert doc.offset_at_position({'line': 4, 'character': 0}) == 51


def test_word_at_position(doc):
    """ Return the position under the cursor (or last in line if past the end) """
    # import sys
    assert doc.word_at_position({'line': 0, 'character': 8}) == 'sys'
    # Past end of import sys
    assert doc.word_at_position({'line': 0, 'character': 1000}) == 'sys'
    # Empty line
    assert doc.word_at_position({'line': 1, 'character': 5}) == ''
    # def main():
    assert doc.word_at_position({'line': 2, 'character': 0}) == 'def'
    # Past end of file
    assert doc.word_at_position({'line': 4, 'character': 0}) == ''


def test_document_empty_edit():
    doc = Document('file:///uri', u'')
    doc.apply_change({
        'range': {
            'start': {'line': 0, 'character': 0},
            'end': {'line': 0, 'character': 0}
        },
        'text': u'f'
    })
    assert doc.source == u'f'


def test_document_line_edit():
    doc = Document('file:///uri', u'itshelloworld')
    doc.apply_change({
        'text': u'goodbye',
        'range': {
            'start': {'line': 0, 'character': 3},
            'end': {'line': 0, 'character': 8}
        }
    })
    assert doc.source == u'itsgoodbyeworld'


def test_document_multiline_edit():
    old = [
        "def hello(a, b):\n",
        "    print a\n",
        "    print b\n"
    ]
    doc = Document('file:///uri', u''.join(old))
    doc.apply_change({'text': u'print a, b', 'range': {
        'start': {'line': 1, 'character': 4},
        'end': {'line': 2, 'character': 11}
    }})
    assert doc.lines == [
        "def hello(a, b):\n",
        "    print a, b\n"
    ]


def test_document_end_of_file_edit():
    old = [
        "print 'a'\n",
        "print 'b'\n"
    ]
    doc = Document('file:///uri', u''.join(old))
    doc.apply_change({'text': u'o', 'range': {
        'start': {'line': 2, 'character': 0},
        'end': {'line': 2, 'character': 0}
    }})
    assert doc.lines == [
        "print 'a'\n",
        "print 'b'\n",
        "o",
    ]
