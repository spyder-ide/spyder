#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    # Print basic testing info
    conda info

    cd continuous_integration/conda-recipes

    # Custom build of qtconsole for pyqt5
    if [ "$USE_QT_API" = "PyQt5" ]; then
        conda build --python $TRAVIS_PYTHON_VERSION qtconsole
    fi

    # There is no Miniconda for 3.5 right now
    if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ]; then
        conda build --python $TRAVIS_PYTHON_VERSION spyder
    else
        conda build spyder
    fi
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

    python setup.py bdist_wheel --universal
fi
