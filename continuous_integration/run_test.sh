#!/usr/bin/env bash

set -ex

if [ "$USE_CONDA" = true ] ; then
    mkdir ~/tmp
    cd ~/tmp
    conda install ~/miniconda/conda-bld/linux-64/spyder-*.tar.bz2
    spyder
fi
