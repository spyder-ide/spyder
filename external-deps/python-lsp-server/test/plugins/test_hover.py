# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os

from pylsp import uris
from pylsp.plugins.hover import pylsp_hover
from pylsp.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """

def main():
    \"\"\"hello world\"\"\"
    pass
"""

NUMPY_DOC = """

import numpy as np
np.sin

"""


def test_numpy_hover(workspace):
    # Over the blank line
    no_hov_position = {'line': 1, 'character': 0}
    # Over 'numpy' in import numpy as np
    numpy_hov_position_1 = {'line': 2, 'character': 8}
    # Over 'np' in import numpy as np
    numpy_hov_position_2 = {'line': 2, 'character': 17}
    # Over 'np' in np.sin
    numpy_hov_position_3 = {'line': 3, 'character': 1}
    # Over 'sin' in np.sin
    numpy_sin_hov_position = {'line': 3, 'character': 4}

    doc = Document(DOC_URI, workspace, NUMPY_DOC)

    contents = ''
    assert contents in pylsp_hover(doc, no_hov_position)['contents']

    contents = 'NumPy\n=====\n\nProvides\n'
    assert contents in pylsp_hover(doc, numpy_hov_position_1)['contents'][0]

    contents = 'NumPy\n=====\n\nProvides\n'
    assert contents in pylsp_hover(doc, numpy_hov_position_2)['contents'][0]

    contents = 'NumPy\n=====\n\nProvides\n'
    assert contents in pylsp_hover(doc, numpy_hov_position_3)['contents'][0]

    # https://github.com/davidhalter/jedi/issues/1746
    # pylint: disable=import-outside-toplevel
    import numpy as np

    if np.lib.NumpyVersion(np.__version__) < '1.20.0':
        contents = 'Trigonometric sine, element-wise.\n\n'
        assert contents in pylsp_hover(
            doc, numpy_sin_hov_position)['contents'][0]


def test_hover(workspace):
    # Over 'main' in def main():
    hov_position = {'line': 2, 'character': 6}
    # Over the blank second line
    no_hov_position = {'line': 1, 'character': 0}

    doc = Document(DOC_URI, workspace, DOC)

    contents = [{'language': 'python', 'value': 'main()'}, 'hello world']

    assert {
        'contents': contents
    } == pylsp_hover(doc, hov_position)

    assert {'contents': ''} == pylsp_hover(doc, no_hov_position)


def test_document_path_hover(workspace_other_root_path, tmpdir):
    # Create a dummy module out of the workspace's root_path and try to get
    # a definition on it in another file placed next to it.
    module_content = '''
def foo():
    """A docstring for foo."""
    pass
'''

    p = tmpdir.join("mymodule.py")
    p.write(module_content)

    # Content of doc to test definition
    doc_content = """from mymodule import foo
foo"""
    doc_path = str(tmpdir) + os.path.sep + 'myfile.py'
    doc_uri = uris.from_fs_path(doc_path)
    doc = Document(doc_uri, workspace_other_root_path, doc_content)

    cursor_pos = {'line': 1, 'character': 3}
    contents = pylsp_hover(doc, cursor_pos)['contents']

    assert contents[1] == 'A docstring for foo.'
