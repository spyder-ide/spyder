#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    conda build conda.recipe
fi
