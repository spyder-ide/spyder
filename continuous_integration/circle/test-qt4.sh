#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"

source activate test

# Only run tests for PyQt4 in Python 2.7 and 3.5
export PY_VERSIONS=($PY_VERSIONS)
export PY_VERSION=${PY_VERSIONS[$CIRCLE_NODE_INDEX]}

if [ "$PY_VERSION" = "2.7" ] || [ "$PY_VERSION" = "3.5" ]; then
    conda install -q qt=4.* pyqt=4.*
    python runtests.py
else
    exit 0
fi
