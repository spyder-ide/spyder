#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    wget --no-check-certificate https://github.com/spyder-ide/spyder/pull/$TRAVIS_PULL_REQUEST.patch
    mv $TRAVIS_PULL_REQUEST.patch conda.recipe
    conda build conda.recipe
fi
