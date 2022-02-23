# Python LSP Server

[![image](https://github.com/python-ls/python-ls/workflows/Linux%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Linux+tests%22) [![image](https://github.com/python-ls/python-ls/workflows/Mac%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Mac+tests%22) [![image](https://github.com/python-ls/python-ls/workflows/Windows%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Windows+tests%22) [![image](https://img.shields.io/github/license/python-ls/python-ls.svg)](https://github.com/python-ls/python-ls/blob/master/LICENSE)

A Python 3.7+ implementation of the [Language Server Protocol](https://github.com/Microsoft/language-server-protocol).
(Note: versions <1.4 should still work with Python 3.6)

## Installation

The base language server requires [Jedi](https://github.com/davidhalter/jedi) to provide Completions, Definitions, Hover, References, Signature Help, and Symbols:

```
pip install python-lsp-server
```

If the respective dependencies are found, the following optional providers will be enabled:
- [Rope](https://github.com/python-rope/rope) for Completions and renaming
- [Pyflakes](https://github.com/PyCQA/pyflakes) linter to detect various errors
- [McCabe](https://github.com/PyCQA/mccabe) linter for complexity checking
- [pycodestyle](https://github.com/PyCQA/pycodestyle) linter for style checking
- [pydocstyle](https://github.com/PyCQA/pydocstyle) linter for docstring style checking (disabled by default)
- [autopep8](https://github.com/hhatto/autopep8) for code formatting
- [YAPF](https://github.com/google/yapf) for code formatting (preferred over autopep8)

Optional providers can be installed using the `extras` syntax. To install [YAPF](https://github.com/google/yapf) formatting for example:

```
pip install "python-lsp-server[yapf]"
```

All optional providers can be installed using:

```
pip install "python-lsp-server[all]"
```

If you get an error similar to `'install_requires' must be a string or list of strings` then please upgrade setuptools before trying again.

```
pip install -U setuptools
```

### 3rd Party Plugins

Installing these plugins will add extra functionality to the language server:

- [pyls-flake8](https://github.com/emanspeaks/pyls-flake8/): Error checking using [flake8](https://flake8.pycqa.org/en/latest/).
- [pylsp-mypy](https://github.com/Richardk2n/pylsp-mypy): [MyPy](http://mypy-lang.org/) type checking for Python >=3.7.
- [pyls-isort](https://github.com/paradoxxxzero/pyls-isort): code formatting using [isort](https://github.com/PyCQA/isort) (automatic import sorting).
- [python-lsp-black](https://github.com/python-lsp/python-lsp-black): code formatting using [Black](https://github.com/psf/black).
- [pyls-memestra](https://github.com/QuantStack/pyls-memestra): detecting the use of deprecated APIs.
- [pylsp-rope](https://github.com/python-rope/pylsp-rope): Extended refactoring capabilities using [Rope](https://github.com/python-rope/rope).

Please see the above repositories for examples on how to write plugins for the Python LSP Server.

[cookiecutter-pylsp-plugin](https://github.com/python-lsp/cookiecutter-pylsp-plugin) is a [cookiecutter](https://cookiecutter.readthedocs.io/) template for setting up a basic plugin project for python-lsp-server. It documents all the essentials you need to know to kick start your own plugin project.

Please file an issue if you require assistance writing a plugin.

## Configuration

Configuration is loaded from zero or more configuration sources.  Currently implemented are:

- pycodestyle: discovered in `~/.config/pycodestyle`, `setup.cfg`, `tox.ini` and `pycodestyle.cfg`.
- flake8: discovered in `~/.config/flake8`, `setup.cfg`, `tox.ini` and `flake8.cfg`

The default configuration source is pycodestyle. Change the `pylsp.configurationSources` setting to `['flake8']` in order to respect flake8 configuration instead.

Overall configuration is computed first from user configuration (in home directory), overridden by configuration passed in by the language client, and then overridden by configuration discovered in the workspace.

To enable pydocstyle for linting docstrings add the following setting in your LSP configuration:
`"pylsp.plugins.pydocstyle.enabled": true`

All configuration options are described in [`CONFIGURATION.md`](https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md).

## LSP Server Features

* Auto Completion
* Code Linting
* Signature Help
* Go to definition
* Hover
* Find References
* Document Symbols
* Document Formatting
* Code folding
* Multiple workspaces

## Development

To run the test suite:

```sh
pip install ".[test]" && pytest
```

After adding configuration options to `schema.json`, refresh the `CONFIGURATION.md` file with

```
python scripts/jsonschema2md.py pylsp/config/schema.json CONFIGURATION.md
```

## License

This project is made available under the MIT License.
