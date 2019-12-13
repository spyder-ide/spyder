#!/bin/bash -ex

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then

    if [ "$OS" != "win" ]; then
        # Install nomkl to avoid installing Intel MKL libraries
        conda install nomkl -q -y
    fi

    # Install main dependencies
    conda install python=$PYTHON_VERSION --file requirements/conda.txt -q -y

    # Install test ones
    conda install python=$PYTHON_VERSION --file requirements/tests.txt -c spyder-ide -q -y

    # Remove spyder-kernels to be sure that we use its subrepo
    conda remove spyder-kernels --force -q -y

    # Install python-language-server from Github with no deps
    pip install --no-deps git+https://github.com/palantir/python-language-server -q
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

    # Remove spyder-kernels to be sure that we use its subrepo
    pip uninstall spyder-kernels -q -y

    # Install python-language-server from Github
    pip install git+https://github.com/palantir/python-language-server -q
fi

# To check our manifest
pip install check-manifest

# Create environment for Jedi environments tests
conda create -n jedi-test-env -q -y python=3.6 flask spyder-kernels
conda list -n jedi-test-env

# Create environment to test conda activation before launching a spyder kernel
conda create -n spytest-ž -q -y python=3.6 spyder-kernels
conda list -n spytest-ž

# Coverage
conda install -n test codecov
