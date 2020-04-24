Python Language Server
======================

.. image:: https://circleci.com/gh/palantir/python-language-server.svg?style=shield
    :target: https://circleci.com/gh/palantir/python-language-server

.. image:: https://ci.appveyor.com/api/projects/status/mdacv6fnif7wonl0?svg=true
    :target: https://ci.appveyor.com/project/gatesn/python-language-server

.. image:: https://img.shields.io/github/license/palantir/python-language-server.svg
     :target: https://github.com/palantir/python-language-server/blob/master/LICENSE

A Python 2.7 and 3.5+ implementation of the `Language Server Protocol`_.

Installation
------------

The base language server requires Jedi_ to provide Completions, Definitions, Hover, References, Signature Help, and
Symbols:

``pip install python-language-server``

If the respective dependencies are found, the following optional providers will be enabled:

* Rope_ for Completions and renaming
* Pyflakes_ linter to detect various errors
* McCabe_ linter for complexity checking
* pycodestyle_ linter for style checking
* pydocstyle_ linter for docstring style checking (disabled by default)
* autopep8_ for code formatting
* YAPF_ for code formatting (preferred over autopep8)

Optional providers can be installed using the `extras` syntax. To install YAPF_ formatting for example:

``pip install 'python-language-server[yapf]'``

All optional providers can be installed using:

``pip install 'python-language-server[all]'``

If you get an error similar to ``'install_requires' must be a string or list of strings`` then please upgrade setuptools before trying again. 

``pip install -U setuptools``

3rd Party Plugins
~~~~~~~~~~~~~~~~~
Installing these plugins will add extra functionality to the language server:

* pyls-mypy_ Mypy type checking for Python 3
* pyls-isort_ Isort import sort code formatting
* pyls-black_ for code formatting using Black_

Please see the above repositories for examples on how to write plugins for the Python Language Server. Please file an
issue if you require assistance writing a plugin.

Configuration
-------------

Configuration is loaded from zero or more configuration sources. Currently implemented are:

* pycodestyle: discovered in ~/.config/pycodestyle, setup.cfg, tox.ini and pycodestyle.cfg.
* flake8: discovered in ~/.config/flake8, setup.cfg, tox.ini and flake8.cfg

The default configuration source is pycodestyle. Change the `pyls.configurationSources` setting to `['flake8']` in
order to respect flake8 configuration instead.

Overall configuration is computed first from user configuration (in home directory), overridden by configuration
passed in by the language client, and then overriden by configuration discovered in the workspace.

To enable pydocstyle for linting docstrings add the following setting in your LSP configuration:
```
"pyls.plugins.pydocstyle.enabled": true
```

Language Server Features
------------------------

Auto Completion:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/auto-complete.gif

Code Linting with pycodestyle and pyflakes:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/linting.gif

Signature Help:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/signature-help.gif

Go to definition:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/goto-definition.gif

Hover:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/hover.gif

Find References:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/references.gif

Document Symbols:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/document-symbols.gif

Document Formatting:

.. image:: https://raw.githubusercontent.com/palantir/python-language-server/develop/resources/document-format.gif

Development
-----------

To run the test suite:

``pip install .[test] && pytest``

Develop against VS Code
=======================

The Python language server can be developed against a local instance of Visual Studio Code.

Install `VSCode <https://code.visualstudio.com/download>`_

.. code-block:: bash

    # Setup a virtual env
    virtualenv env
    . env/bin/activate

    # Install pyls
    pip install .

    # Install the vscode-client extension
    cd vscode-client
    yarn install

    # Run VSCode which is configured to use pyls
    # See the bottom of vscode-client/src/extension.ts for info
    yarn run vscode -- $PWD/../

Then to debug, click View -> Output and in the dropdown will be pyls.
To refresh VSCode, press `Cmd + r`

License
-------

This project is made available under the MIT License.

.. _Language Server Protocol: https://github.com/Microsoft/language-server-protocol
.. _Jedi: https://github.com/davidhalter/jedi
.. _Rope: https://github.com/python-rope/rope
.. _Pyflakes: https://github.com/PyCQA/pyflakes
.. _McCabe: https://github.com/PyCQA/mccabe
.. _pycodestyle: https://github.com/PyCQA/pycodestyle
.. _pydocstyle: https://github.com/PyCQA/pydocstyle
.. _YAPF: https://github.com/google/yapf
.. _autopep8: https://github.com/hhatto/autopep8
.. _pyls-mypy: https://github.com/tomv564/pyls-mypy
.. _pyls-isort: https://github.com/paradoxxxzero/pyls-isort
.. _pyls-black: https://github.com/rupert/pyls-black
.. _Black: https://github.com/ambv/black
