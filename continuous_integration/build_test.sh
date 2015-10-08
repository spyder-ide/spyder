#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    # Downloading PR patch
    wget --no-check-certificate https://github.com/spyder-ide/spyder/pull/$TRAVIS_PULL_REQUEST.patch
    mv $TRAVIS_PULL_REQUEST.patch conda.recipe

    # Making a level 0 patch so it can be applied by conda-build
    cd conda.recipe
    sed -i s/'--- a\/'/'--- '/g $TRAVIS_PULL_REQUEST.patch
    sed -i s/'+++ b\/'/'+++ '/g $TRAVIS_PULL_REQUEST.patch
    cd ..

    # Building the recipe
    conda build conda.recipe
fi
