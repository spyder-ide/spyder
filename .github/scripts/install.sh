#!/bin/bash -ex

if [ "$OS" = "macos" ]; then
    # Adjust PATH in macOS because conda is not at front of it
    PATH=/usr/local/miniconda/envs/test/bin:/usr/local/miniconda/condabin:$PATH
fi

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then

    if [ "$OS" != "win" ]; then
        # Install nomkl to avoid installing Intel MKL libraries
        conda install nomkl -q -y
    fi

    # Install main dependencies
    conda install python=$PYTHON_VERSION --file requirements/conda.txt -q -y -c spyder-ide/label/dev

    # Install test ones
    conda install python=$PYTHON_VERSION --file requirements/tests.txt -c spyder-ide -q -y

    # Install Pyzmq 19 because our tests are failing with version 20
    if [ "$OS" = "win" ]; then
        conda install pyzmq=19
    fi

    # Remove packages we have subrepos for.
    conda remove spyder-kernels --force -q -y
    conda remove python-lsp-server --force -q -y
    conda remove qdarkstyle --force -q -y
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

    # Install QtAwesome from Github
    pip install git+https://github.com/spyder-ide/qtawesome.git

    # Remove packages we have subrepos for
    pip uninstall spyder-kernels -q -y
    pip uninstall python-lsp-server -q -y
    pip uninstall qdarkstyle -q -y
fi

# Install subrepos in development mode
for dep in $(ls external-deps)
do
    pushd external-deps/$dep
    pip install --no-deps -q -e .
    popd
done

# Install Spyder to test it as if it was properly installed
pip uninstall spyder -q -y
python setup.py bdist_wheel
pip install --no-deps dist/spyder*.whl

# To check our manifest
pip install check-manifest

# Create environment for Jedi environments tests
conda create -n jedi-test-env -q -y python=3.6 flask spyder-kernels
conda list -n jedi-test-env

# Create environment to test conda activation before launching a spyder kernel
conda create -n spytest-ž -q -y python=3.6 spyder-kernels
conda list -n spytest-ž

# Install pyenv
if [ "$RUN_SLOW" = "false" ]; then
    if [ "$OS" != "win" ]; then
        curl https://pyenv.run | bash
        $HOME/.pyenv/bin/pyenv install 3.8.1
    fi
fi

# Coverage
pip install codecov
