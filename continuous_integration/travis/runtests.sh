#!/bin/bash -ex

source $HOME/miniconda/etc/profile.d/conda.sh
conda activate test

# Check manifest for missing files
check-manifest

python bootstrap.py -- --reset
python runtests.py
