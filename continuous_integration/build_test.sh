#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    # Building the recipe
    cd continuous_integration
    conda build conda.recipe
fi
