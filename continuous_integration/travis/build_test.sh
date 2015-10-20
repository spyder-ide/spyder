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

    python setup.py bdist_wheel --universal
fi
