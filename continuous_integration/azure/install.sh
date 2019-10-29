#!/bin/bash -ex

# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Avoid problems with invalid SSL certificates
    if [ "$PYTHON_VERSION" = "2.7" ]; then
        conda install -q -y python=2.7.16=h97142e2_0
    fi

    # Install nomkl to avoid installing Intel MKL libraries
    conda install -q -y nomkl

    # Install main dependencies
    conda install -q -y -c spyder-ide --file requirements/conda.txt

    # Install test ones
    conda install -q -y -c spyder-ide --file requirements/tests.txt

    # Github backend tests are failing with 1.1.1d
    conda install -q -y openssl=1.1.1c

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels

    # Install python-language-server from Github with no deps
    pip install -q --no-deps git+https://github.com/palantir/python-language-server
else
    # Github backend tests are failing with 1.1.1d
    conda install -q -y openssl=1.1.1c

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

    # Install python-language-server from Github
    pip install -q git+https://github.com/palantir/python-language-server
fi
