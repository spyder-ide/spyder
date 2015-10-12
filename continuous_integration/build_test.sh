#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    cd continuous_integration

    echo "----------- TESTING VERSIONS -----------"
    python --version
    pip --version
    conda --version
    echo "----------------------------------------"

    # Use --python only for 3.5 to avoid building for old Pythons
    # on the other versions
    if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ]; then
        conda build --python $TRAVIS_PYTHON_VERSION conda.recipe
    else
        conda build conda.recipe
    fi
fi
