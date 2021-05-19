#!/usr/bin/env python

# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import ast
import os
from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def get_version(module='pylsp'):
    """Get version."""
    with open(os.path.join(HERE, module, '_version.py'), 'r') as f:
        data = f.read()
    lines = data.split('\n')
    for line in lines:
        if line.startswith('VERSION_INFO'):
            version_tuple = ast.literal_eval(line.split('=')[-1].strip())
            version = '.'.join(map(str, version_tuple))
            break
    return version


README = open('README.md', 'r').read()

install_requires = [
    'jedi>=0.17.2,<0.19.0',
    'python-lsp-jsonrpc>=1.0.0',
    'pluggy',
    'ujson>=3.0.0',
    'setuptools>=39.0.0'
]

setup(
    name='python-lsp-server',
    version=get_version(),
    description='Python Language Server for the Language Server Protocol',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/python-lsp/python-lsp-server',
    author='Python Language Server Contributors',
    packages=find_packages(exclude=['contrib', 'docs', 'test', 'test.*']),
    install_requires=install_requires,
    python_requires='>=3.6',
    extras_require={
        'all': [
            'autopep8',
            'flake8>=3.8.0',
            'mccabe>=0.6.0,<0.7.0',
            'pycodestyle>=2.7.0',
            'pydocstyle>=2.0.0',
            'pyflakes>=2.3.0,<2.4.0',
            'pylint>=2.5.0',
            'rope>=0.10.5',
            'yapf',
        ],
        'autopep8': ['autopep8'],
        'flake8': ['flake8>=3.8.0'],
        'mccabe': ['mccabe>=0.6.0,<0.7.0'],
        'pycodestyle': ['pycodestyle>=2.7.0'],
        'pydocstyle': ['pydocstyle>=2.0.0'],
        'pyflakes': ['pyflakes>=2.3.0,<2.4.0'],
        'pylint': ['pylint>=2.5.0'],
        'rope': ['rope>0.10.5'],
        'yapf': ['yapf'],
        'test': ['pylint>=2.5.0', 'pytest', 'pytest-cov', 'coverage', 'numpy',
                 'pandas', 'matplotlib', 'pyqt5', 'flaky'],
    },
    entry_points={
        'console_scripts': [
            'pylsp = pylsp.__main__:main',
        ],
        'pylsp': [
            'autopep8 = pylsp.plugins.autopep8_format',
            'folding = pylsp.plugins.folding',
            'flake8 = pylsp.plugins.flake8_lint',
            'jedi_completion = pylsp.plugins.jedi_completion',
            'jedi_definition = pylsp.plugins.definition',
            'jedi_hover = pylsp.plugins.hover',
            'jedi_highlight = pylsp.plugins.highlight',
            'jedi_references = pylsp.plugins.references',
            'jedi_rename = pylsp.plugins.jedi_rename',
            'jedi_signature_help = pylsp.plugins.signature',
            'jedi_symbols = pylsp.plugins.symbols',
            'mccabe = pylsp.plugins.mccabe_lint',
            'preload = pylsp.plugins.preload_imports',
            'pycodestyle = pylsp.plugins.pycodestyle_lint',
            'pydocstyle = pylsp.plugins.pydocstyle_lint',
            'pyflakes = pylsp.plugins.pyflakes_lint',
            'pylint = pylsp.plugins.pylint_lint',
            'rope_completion = pylsp.plugins.rope_completion',
            'rope_rename = pylsp.plugins.rope_rename',
            'yapf = pylsp.plugins.yapf_format'
        ]
    },
)
