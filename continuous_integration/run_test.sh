#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing the app in Travis
export TEST_TRAVIS_APP=True

# Extra packages to install besides Spyder regular dependencies
# We install them here and not in travis_install.sh to see if
# Spyder is correctly pulling its deps (some of them are shared
# with mpl)
export EXTRA_PACKAGES="matplotlib pandas sympy pillow"

if [ "$USE_CONDA" = true ] ; then
    # Move to a tmp dir
    mkdir ~/tmp
    cd ~/tmp

    # Install and run the package
    conda install ~/miniconda/conda-bld/linux-64/spyder-*.tar.bz2

    # Install extra packages
    conda install -q $EXTRA_PACKAGES

    spyder
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi
