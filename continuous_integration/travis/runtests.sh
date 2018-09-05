#!/bin/bash

source $HOME/miniconda/etc/profile.d/conda.sh
conda activate test

# python setup.py install
python bootstrap.py -- --reset

python runtests.py
