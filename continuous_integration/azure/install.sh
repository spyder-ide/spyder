#!/bin/bash -ex

# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Install main dependencies
    conda install -q -y -c spyder-ide --file requirements/conda.txt

    # Install test ones
    conda install -q -y -c spyder-ide --file requirements/tests.txt

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels

    # macOS tests are failing with Qt 5.9.7
    if [ $(uname) == Darwin ]; then
        conda install -q -y qt=5.9.6
    fi
else
    # Update pip and setuptools
    pip install -U pip setuptools

    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Remove pytest-xvfb because it causes hangs
    pip uninstall -q -y pytest-xvfb

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git

    # Install spyder-kernels from Github
    pip install -q git+https://github.com/spyder-ide/spyder-kernels
fi
