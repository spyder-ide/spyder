#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    cd ~/
    conda install ~/miniconda/conda-bld/linux-64/spyder-*.tar.bz2
    spyder
fi
