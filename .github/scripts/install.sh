#!/bin/bash -ex

# Install gdb
if [ "$USE_GDB" = "true" ]; then
    micromamba install gdb -c conda-forge -q -y
fi

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then

    # Install dependencies per operating system
    if [ "$OS" = "win" ]; then
        micromamba install --file requirements/windows.yml
    elif [ "$OS" = "macos" ]; then
        micromamba install --file requirements/macos.yml
    else
        micromamba install --file requirements/linux.yml
    fi

    # Install test dependencies
    micromamba install --file requirements/tests.yml

    # To check our manifest and coverage
    micromamba install check-manifest -c conda-forge codecov -q -y

    # Install PyZMQ 24 to avoid hangs
    micromamba install -c conda-forge pyzmq=24
else
    # Update pip and setuptools
    python -m pip install -U pip setuptools wheel build

    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install QtAwesome from Github
    pip install git+https://github.com/spyder-ide/qtawesome.git

    # To check our manifest and coverage
    pip install -q check-manifest codecov

    # This allows the test suite to run more reliably on Linux
    if [ "$OS" = "linux" ]; then
        pip uninstall pyqt5 pyqt5-qt5 pyqt5-sip pyqtwebengine pyqtwebengine-qt5 -q -y
        pip install pyqt5==5.12.* pyqtwebengine==5.12.*
    fi

    # Install PyZMQ 24 to avoid hangs
    pip install pyzmq==24.0.1
fi

# Install subrepos from source
python -bb -X dev -W error install_dev_repos.py --not-editable --no-install spyder

# Install boilerplate plugin
pushd spyder/app/tests/spyder-boilerplate
pip install --no-deps -q -e .
popd

# Install Spyder to test it as if it was properly installed.
python -bb -X dev -W error -m build
python -bb -X dev -W error -m pip install --no-deps dist/spyder*.whl

# Adjust PATH on Windows so that we can use conda below. This needs to be done
# at this point or the pip slots fail.
if [ "$OS" = "win" ]; then
    PATH=/c/Miniconda/Scripts/:$PATH
fi

# Create environment for Jedi environment tests
conda create -n jedi-test-env -q -y python=3.9 flask
conda list -n jedi-test-env

# Create environment to test conda env activation before launching a kernel
conda create -n spytest-ž -q -y -c conda-forge python=3.9
conda run -n spytest-ž python -m pip install git+https://github.com/spyder-ide/spyder-kernels.git@master
conda list -n spytest-ž

# Install pyenv on Linux systems
if [ "$RUN_SLOW" = "false" ]; then
    if [ "$OS" = "linux" ]; then
        curl https://pyenv.run | bash
        $HOME/.pyenv/bin/pyenv install 3.8.1
    fi
fi
