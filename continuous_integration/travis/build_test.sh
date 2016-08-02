#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    # Print basic testing info
    conda info

    cd continuous_integration/conda-recipes
    conda build spyder
else
    # Print basic testing info
    pip --version

    # Moving to where our code is
    cd $FULL_SPYDER_CLONE

    # Checkout the right branch
    if [ $TRAVIS_PULL_REQUEST != "false" ] ; then
        git checkout travis_pr_$TRAVIS_PULL_REQUEST
    else
        git checkout master
    fi

    python setup.py bdist_wheel
fi
