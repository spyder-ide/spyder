# Python LSP Server

[![image](https://github.com/python-ls/python-ls/workflows/Linux%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Linux+tests%22) [![image](https://github.com/python-ls/python-ls/workflows/Mac%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Mac+tests%22) [![image](https://github.com/python-ls/python-ls/workflows/Windows%20tests/badge.svg)](https://github.com/python-ls/python-ls/actions?query=workflow%3A%22Windows+tests%22) [![image](https://img.shields.io/github/license/python-ls/python-ls.svg)](https://github.com/python-ls/python-ls/blob/master/LICENSE)

A Python 3.7+ implementation of the [Language Server Protocol](https://github.com/Microsoft/language-server-protocol).
(Note: versions <1.4 should still work with Python 3.6)

## Installation

The base language server requires [Jedi](https://github.com/davidhalter/jedi) to provide Completions, Definitions, Hover, References, Signature Help, and Symbols:

```
pip install python-lsp-server
```
This will expose the command `pylsp` on your PATH. Confirm that installation succeeded by running `pylsp --help`.

If the respective dependencies are found, the following optional providers will be enabled:
- [Rope](https://github.com/python-rope/rope) for Completions and renaming
- [Pyflakes](https://github.com/PyCQA/pyflakes) linter to detect various errors
- [McCabe](https://github.com/PyCQA/mccabe) linter for complexity checking
- [pycodestyle](https://github.com/PyCQA/pycodestyle) linter for style checking
- [pydocstyle](https://github.com/PyCQA/pydocstyle) linter for docstring style checking (disabled by default)
- [autopep8](https://github.com/hhatto/autopep8) for code formatting
- [YAPF](https://github.com/google/yapf) for code formatting (preferred over autopep8)
- [flake8](https://github.com/pycqa/flake8) for error checking (disabled by default)
- [pylint](https://github.com/PyCQA/pylint) for code linting (disabled by default)

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

### Windows and Linux installation

If you use Anaconda/Miniconda, you can install `python-lsp-server` using this conda command

```
conda install -c conda-forge python-lsp-server 
```

Python-lsp-server is available in the repos of every major Linux distribution, and it is usually called `python-lsp-server` or `python3-pylsp`.

For example, here is how to install it in Debian and Debian-based distributions (E.g. Ubuntu, Pop!_OS, Linux Mint)

```
sudo apt-get install python3-pylsp
```

or Fedora Linux

```
sudo dnf install python-lsp-server
```

or Arch Linux

```
sudo pacman -S python-lsp-server
````

Only on Alpine Linux the package is named differently. You can install it there by typing this command in your terminal:

```
apk add py3-lsp-server
```

### 3rd Party Plugins

Installing these plugins will add extra functionality to the language server:

- [pylsp-mypy](https://github.com/Richardk2n/pylsp-mypy): [MyPy](http://mypy-lang.org/) type checking for Python >=3.7.
- [pyls-isort](https://github.com/paradoxxxzero/pyls-isort): code formatting using [isort](https://github.com/PyCQA/isort) (automatic import sorting).
- [python-lsp-black](https://github.com/python-lsp/python-lsp-black): code formatting using [Black](https://github.com/psf/black).
- [pyls-memestra](https://github.com/QuantStack/pyls-memestra): detecting the use of deprecated APIs.
- [pylsp-rope](https://github.com/python-rope/pylsp-rope): Extended refactoring capabilities using [Rope](https://github.com/python-rope/rope).
- [python-lsp-ruff](https://github.com/python-lsp/python-lsp-ruff): Extensive and fast linting using [ruff](https://github.com/charliermarsh/ruff).

Please see the above repositories for examples on how to write plugins for the Python LSP Server.

[cookiecutter-pylsp-plugin](https://github.com/python-lsp/cookiecutter-pylsp-plugin) is a [cookiecutter](https://cookiecutter.readthedocs.io/) template for setting up a basic plugin project for python-lsp-server. It documents all the essentials you need to know to kick start your own plugin project.

Please file an issue if you require assistance writing a plugin.

## Configuration

Like all language servers, configuration can be passed from the client that talks to this server (i.e. your editor/IDE or other tool that has the same purpose). The details of how this is done depend on the editor or plugin that you are using to communicate with `python-lsp-server`. The configuration options available at that level are documented in [`CONFIGURATION.md`](https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md).

`python-lsp-server` depends on other tools, like flake8 and pycodestyle. These tools can be configured via settings passed from the client (as above), or alternatively from other configuration sources. The following sources are available:

- `pycodestyle`: discovered in `~/.config/pycodestyle`, `setup.cfg`, `tox.ini` and `pycodestyle.cfg`.
- `flake8`: discovered in `~/.config/flake8`, `.flake8`, `setup.cfg` and `tox.ini`

The default configuration sources are `pycodestyle` and `pyflakes`. If you would like to use `flake8`, you will need to:

1. Disable `pycodestyle`, `mccabe`, and `pyflakes`, by setting their corresponding `enabled` configurations, e.g. `pylsp.plugins.pycodestyle.enabled`, to `false`. This will prevent duplicate linting messages as flake8 includes these tools.
1. Set `pylsp.plugins.flake8.enabled` to `true`.
1. Change the `pylsp.configurationSources` setting (in the value passed in from your client) to `['flake8']` in order to use the flake8 configuration instead.

The configuration options available in these config files (`setup.cfg` etc) are documented in the relevant tools:

- [flake8 configuration](https://flake8.pycqa.org/en/latest/user/configuration.html)
- [pycodestyle configuration](https://pycodestyle.pycqa.org/en/latest/intro.html#configuration)

Overall configuration is computed first from user configuration (in home directory), overridden by configuration passed in by the language client, and then overridden by configuration discovered in the workspace.

As an example, to change the list of errors that pycodestyle will ignore, assuming you are using the `pycodestyle` configuration source (the default), you can:

1. Add the following to your ~/.config/pycodestyle:

   ```
   [pycodestyle]
   ignore = E226,E302,E41
   ```

2. Set the `pylsp.plugins.pycodestyle.ignore` config value from your editor
3. Same as 1, but add to `setup.cfg` file in the root of the project.


Python LSP Server can communicate over WebSockets when configured as follows:

```
pylsp --ws --port [port]
```

The following libraries are required for Web Sockets support:
- [websockets](https://websockets.readthedocs.io/en/stable/) for Python LSP Server Web sockets using websockets library. refer [Websockets installation](https://websockets.readthedocs.io/en/stable/intro/index.html#installation) for more details

You can install this dependency with command below:

```
pip install 'python-lsp-server[websockets]'
```

## LSP Server Features

* Auto Completion
* [Autoimport](docs/autoimport.md)
* Code Linting
* Code actions
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
