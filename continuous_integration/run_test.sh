#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing the app on Travis
export TEST_TRAVIS_APP=True

if [ "$USE_CONDA" = true ] ; then
    # Move to a tmp dir
    mkdir ~/tmp
    cd ~/tmp

    # Install and run the package
    conda install ~/miniconda/conda-bld/linux-64/spyder-*.tar.bz2

    spyder
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi
