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

    python setup.py bdist_wheel --universal
fi
