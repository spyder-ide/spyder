#!/bin/bash

source $HOME/miniconda/etc/profile.d/conda.sh
conda activate test

python bootstrap.py -- --reset
python runtests.py
