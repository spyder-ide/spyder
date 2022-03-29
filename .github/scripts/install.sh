#!/bin/bash -ex

# Adjust PATH in macOS
if [ "$OS" = "macos" ]; then
    PATH=/Users/runner/miniconda3/envs/test/bin:/Users/runner/miniconda3/condabin:$PATH
fi

# Install gdb
if [ "$USE_GDB" = "true" ]; then
    mamba install gdb -c conda-forge -q -y
fi

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then

    # Install main dependencies
    mamba install python=$PYTHON_VERSION --file requirements/conda.txt -c conda-forge -q -y

    # Install test ones
    mamba install python=$PYTHON_VERSION --file requirements/tests.txt -c conda-forge -q -y

    # To check our manifest and coverage
    mamba install check-manifest codecov -c conda-forge -q -y

    # Remove packages we have subrepos for.
    for dep in $(ls external-deps)
    do
        echo "Removing $dep package"

        if [ "$dep" = "qtconsole" ]; then
            conda remove qtconsole-base qtconsole --force -q -y
        else
            conda remove $dep --force -q -y
        fi
    done
else
    # Update pip and setuptools
    pip install -U pip setuptools

    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install QtAwesome from Github
    pip install git+https://github.com/spyder-ide/qtawesome.git

    # To check our manifest and coverage
    pip install -q check-manifest codecov

    # Remove packages we have subrepos for
    for dep in $(ls external-deps)
    do
        echo "Removing $dep package"
        pip uninstall $dep -q -y
    done

    # Remove Spyder to properly install it below
    pip uninstall spyder -q -y
fi

# Install subrepos in development mode
for dep in $(ls external-deps)
do
    echo "Installing $dep subrepo"

    # This is necessary to pass our minimal required version of PyLSP to setuptools-scm
    if [ "$dep" = "python-lsp-server" ]; then
        SETUPTOOLS_SCM_PRETEND_VERSION=`python pylsp_utils.py` pip install --no-deps -q -e external-deps/$dep
    else
        pip install --no-deps -q -e external-deps/$dep
    fi
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
    if [ "$OS" = "linux" ]; then
        curl https://pyenv.run | bash
        $HOME/.pyenv/bin/pyenv install 3.8.1
    fi
fi
