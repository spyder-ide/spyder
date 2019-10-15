#!/bin/bash -ex

# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Install main dependencies
    conda install -q -y -c conda-forge/label/beta -c conda-forge --file requirements/conda.txt

    # Install test ones
    conda install -q -y -c conda-forge --file requirements/tests.txt

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
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
