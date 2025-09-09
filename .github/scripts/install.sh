#!/bin/bash -ex

# Auxiliary functions
install_spyder_kernels() {
    echo "Installing subrepo version of spyder-kernels in "$1"..."

    pushd external-deps/spyder-kernels

    if [ "$OS" = "win" ]; then
        # `conda run` fails on Windows without a clear reason
        /c/Users/runneradmin/miniconda3/envs/"$1"/python -m pip install -q .
    else
        conda run -n "$1" python -m pip install -q .
    fi

    popd
}

# Install gdb
if [ "$USE_GDB" = "true" ]; then
    micromamba install gdb -c conda-forge -q -y
fi

# Install dependencies
if [ "$USE_CONDA" = "true" ]; then
    if [ -n "$SPYDER_QT_BINDING" ]; then
        # conda has no PyQt6 package
        echo "Cannot use Qt 6 with Conda" 1>&2
        exit 1
    fi

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

    # To check our manifest
    micromamba install check-manifest -q -y

    # Remove pylsp before installing its subrepo below
    micromamba remove --force python-lsp-server python-lsp-server-base -y

    if [ "$OS" = "linux" ]; then
        # Pin Jedi to 0.19.1 because test_update_outline fails frequently with
        # 0.19.2, although it passes locally
        micromamba install jedi=0.19.1
    elif [ "$OS" = "win" ]; then
        # Build 8 of this version makes tests fail in odd ways.
        micromamba install bzip2=1.0.8=h2466b09_7
    fi

else
    # Update pip and setuptools
    python -m pip install -U pip setuptools wheel build

    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install QtAwesome from Github
    pip install git+https://github.com/spyder-ide/qtawesome.git

    # To check our manifest
    pip install -q check-manifest

    # Pin Jedi to 0.19.1 because test_update_outline fails frequently with
    # 0.19.2, although it passes locally
    if [ "$OS" = "linux" ]; then
        pip install jedi==0.19.1
    fi
fi

# Install subrepos from source
python -bb -X dev install_dev_repos.py --not-editable --no-install spyder spyder-remote-services

# Install Spyder to test it as if it was properly installed.
python -bb -X dev -m build
python -bb -X dev -m pip install --no-deps dist/spyder*.whl

if [ "$SPYDER_TEST_REMOTE_CLIENT" = "true" ]; then
    pip install pytest-docker
else

    # Install boilerplate plugin
    pushd spyder/app/tests/spyder-boilerplate
    pip install --no-deps .
    popd

    # Create environment for Jedi environment tests
    conda create -n jedi-test-env -q -y python=3.9 flask
    install_spyder_kernels jedi-test-env
    conda list -n jedi-test-env

    # Create environment to test conda env activation before launching a kernel
    conda create -n spytest-ž -q -y -c conda-forge python=3.9
    install_spyder_kernels spytest-ž
    conda list -n spytest-ž

    # Install pyenv on Linux systems
    if [ "$RUN_SLOW" = "false" ]; then
        if [ "$OS" = "linux" ]; then
            curl https://pyenv.run | bash
            $HOME/.pyenv/bin/pyenv install 3.10.6
        fi
    fi
fi
