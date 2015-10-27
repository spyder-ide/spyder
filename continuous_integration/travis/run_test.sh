#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing the app in Travis
export TEST_CI_APP=True


# Extra packages to install besides Spyder regular dependencies
# We install them here and not in travis_install.sh to see if
# Spyder is correctly pulling its deps (some of them are shared
# with mpl)
export EXTRA_PACKAGES="pandas sympy pillow"


# Don't install mpl for PyQt5 because it pulls PyQt4
if [ "$USE_QT_API" = "PyQt4" ]; then
    EXTRA_PACKAGES+=" matplotlib"
fi


# Install our builds of Spyder
if [ "$USE_CONDA" = true ] ; then
    # Move to a tmp dir
    mkdir ~/tmp
    cd ~/tmp

    # Install and run the package
    conda install ~/miniconda/conda-bld/linux-64/spyder-*.tar.bz2

    # Install extra packages
    conda install -q $EXTRA_PACKAGES

    # Jedi 0.8 is not available in conda
    if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ]; then
        pip install jedi==0.8.1
    fi
else
    cd $FULL_SPYDER_CLONE
    pip install dist/spyder-*.whl
fi


# Testing that the app starts and runs
spyder
if [ $? -ne 0 ]; then
    exit 1
fi
