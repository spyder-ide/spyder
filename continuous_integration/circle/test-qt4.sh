#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"

source activate test

export PY_VERSIONS=($PY_VERSIONS)
export PY_VERSION=${PY_VERSIONS[$CIRCLE_NODE_INDEX]}

# We use container 3 to test with pip
if [ "$CIRCLE_NODE_INDEX" != "3" ]; then
    # Only run tests for PyQt4 in Python 2.7 and 3.5. There are
    # no packages available for other versions.
    if [ "$PY_VERSION" = "2.7" ] || [ "$PY_VERSION" = "3.5" ]; then
        conda install -q qt=4.* pyqt=4.*
        python runtests.py
    else
        exit 0
    fi
else
    exit 0
fi
