#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing the app in Travis
export TEST_CI_APP=True


# Extra packages to install besides Spyder regular dependencies
# We install them here and not in travis_install.sh to see if
# Spyder is correctly pulling its deps (some of them are shared
# with mpl)
export EXTRA_PACKAGES="nomkl pandas sympy pillow scipy"

# Install our builds of Spyder
if [ "$USE_CONDA" = true ] ; then
    # Move to a tmp dir
    mkdir ~/tmp
    cd ~/tmp

    # Install and run the package
    conda install --use-local spyder-dev

    # Install extra packages
    conda install -q $EXTRA_PACKAGES
else
    cd $FULL_SPYDER_CLONE
    export WHEEL=`ls dist/spyder-*.whl`
    pip install $WHEEL[test]
fi


# Testing that the app starts and runs
if [[ "$USE_CONDA" = false && "$TRAVIS_PYTHON_VERSION" != "2.7" ]] ; then
    spyder3
else
    spyder
fi
if [ $? -ne 0 ]; then
    exit 1
fi
