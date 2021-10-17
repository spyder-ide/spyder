#!/bin/bash -ex

# Adjust PATH in macOS
if [ "$OS" = "macos" ]; then
    PATH=/Users/runner/miniconda3/envs/test/bin:/Users/runner/miniconda3/condabin:$PATH
fi

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then

    # Install main dependencies
    mamba install python=$PYTHON_VERSION --file requirements/conda.txt -c conda-forge -q -y

    # Install test ones
    mamba install python=$PYTHON_VERSION --file requirements/tests.txt -c conda-forge -q -y

    # Install Pyzmq 19 because our tests are failing with version 20
    if [ "$OS" = "win" ]; then
        mamba install pyzmq=19
    fi

    # To check our manifest and coverage
    mamba install check-manifest codecov -c conda-forge -q -y

    # Remove packages we have subrepos for.
    conda remove spyder-kernels --force -q -y
    conda remove python-lsp-server --force -q -y
    conda remove qdarkstyle --force -q -y

    # Note: Remove this when PyLSP 1.3.0 is released
    mamba install 'pylint >=2.10' -c conda-forge -q -y
else
    # Update pip and setuptools
    pip install -U pip setuptools

    # Note: Remove this when PyLSP 1.3.0 is released
    pip install pylint==2.9.6

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

    # To check our manifest and coverage
    pip install -q check-manifest codecov

    # Remove packages we have subrepos for
    pip uninstall spyder-kernels -q -y
    pip uninstall python-lsp-server -q -y
    pip uninstall qdarkstyle -q -y

    # Remove Spyder to properly install it below
    pip uninstall spyder -q -y

    # Note: Remove this when PyLSP 1.3.0 is released
    pip install -U pylint
fi

# Install subrepos in development mode
for dep in $(ls external-deps)
do
    pushd external-deps/$dep
    pip install --no-deps -q -e .
    popd
done

# Install boilerplate plugin
pushd spyder/app/tests/spyder-boilerplate
pip install --no-deps -q -e .
popd

# Install Spyder to test it as if it was properly installed.
# Note: `python setup.py egg_info` doesn't work here but it
# does locally.
python setup.py -q bdist_wheel
pip install --no-deps -q dist/spyder*.whl

# Create environment for Jedi environments tests
mamba create -n jedi-test-env -q -y python=3.6 flask spyder-kernels
mamba list -n jedi-test-env

# Create environment to test conda activation before launching a spyder kernel
mamba create -n spytest-ž -q -y python=3.6 spyder-kernels
mamba list -n spytest-ž

# Install pyenv in Posix systems
if [ "$RUN_SLOW" = "false" ]; then
    if [ "$OS" != "win" ]; then
        curl https://pyenv.run | bash
        $HOME/.pyenv/bin/pyenv install 3.8.1
    fi
fi
