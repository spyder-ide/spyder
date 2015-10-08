#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    # Downloading PR patch
    wget --no-check-certificate https://github.com/spyder-ide/spyder/pull/$TRAVIS_PULL_REQUEST.diff
    mv $TRAVIS_PULL_REQUEST.diff continuous_integration/conda.recipe

    # Making a level 0 patch so it can be applied by conda-build
    cd continuous_integration/conda.recipe
    sed -i s/'--- a\/'/'--- '/g $TRAVIS_PULL_REQUEST.diff
    sed -i s/'+++ b\/'/'+++ '/g $TRAVIS_PULL_REQUEST.diff
    cd ..

    # Building the recipe
    conda build conda.recipe
fi
