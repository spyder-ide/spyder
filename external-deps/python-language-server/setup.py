#!/usr/bin/env python
from setuptools import find_packages, setup
import versioneer

README = open('README.rst', 'r').read()


setup(
    name='python-language-server',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),

    description='Python Language Server for the Language Server Protocol',

    long_description=README,

    # The project's main homepage.
    url='https://github.com/palantir/python-language-server',

    author='Palantir Technologies, Inc.',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'test', 'test.*']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'configparser; python_version<"3.0"',
        'future>=0.14.0; python_version<"3"',
        'backports.functools_lru_cache; python_version<"3.2"',
        'jedi>=0.17.0,<0.18.0',
        'python-jsonrpc-server>=0.3.2',
        'pluggy',
        'ujson<=1.35; platform_system!="Windows"'
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[test]
    extras_require={
        'all': [
            'autopep8',
            'flake8>=3.8.0',
            'mccabe>=0.6.0,<0.7.0',
            'pycodestyle>=2.6.0,<2.7.0',
            'pydocstyle>=2.0.0',
            'pyflakes>=2.2.0,<2.3.0',
            'pylint',
            'rope>=0.10.5',
            'yapf',
        ],
        'autopep8': ['autopep8'],
        'flake8': ['flake8>=3.8.0'],
        'mccabe': ['mccabe>=0.6.0,<0.7.0'],
        'pycodestyle': ['pycodestyle>=2.6.0,<2.7.0'],
        'pydocstyle': ['pydocstyle>=2.0.0'],
        'pyflakes': ['pyflakes>=2.2.0,<2.3.0'],
        'pylint': ['pylint'],
        'rope': ['rope>0.10.5'],
        'yapf': ['yapf'],
        'test': ['versioneer', 'pylint', 'pytest', 'mock', 'pytest-cov',
                 'coverage', 'numpy', 'pandas', 'matplotlib',
                 'pyqt5;python_version>="3"'],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'pyls = pyls.__main__:main',
        ],
        'pyls': [
            'autopep8 = pyls.plugins.autopep8_format',
            'folding = pyls.plugins.folding',
            'flake8 = pyls.plugins.flake8_lint',
            'jedi_completion = pyls.plugins.jedi_completion',
            'jedi_definition = pyls.plugins.definition',
            'jedi_hover = pyls.plugins.hover',
            'jedi_highlight = pyls.plugins.highlight',
            'jedi_references = pyls.plugins.references',
            'jedi_rename = pyls.plugins.jedi_rename',
            'jedi_signature_help = pyls.plugins.signature',
            'jedi_symbols = pyls.plugins.symbols',
            'mccabe = pyls.plugins.mccabe_lint',
            'preload = pyls.plugins.preload_imports',
            'pycodestyle = pyls.plugins.pycodestyle_lint',
            'pydocstyle = pyls.plugins.pydocstyle_lint',
            'pyflakes = pyls.plugins.pyflakes_lint',
            'pylint = pyls.plugins.pylint_lint',
            'rope_completion = pyls.plugins.rope_completion',
            'rope_rename = pyls.plugins.rope_rename',
            'yapf = pyls.plugins.yapf_format'
        ]
    },
)
