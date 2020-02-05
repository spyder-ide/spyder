#!/bin/bash

# Install Miniconda
if [ $(uname) == Linux ]; then
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
else
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O miniconda.sh
fi
bash miniconda.sh -b -p $HOME/miniconda
source $HOME/miniconda/etc/profile.d/conda.sh

# Make new conda environment with required Python version
conda create -y -n test python=$PYTHON_VERSION
conda activate test

# Install dependencies
conda install -y -q --file requirements/posix.txt

# Install test dependencies
conda install -y -q nomkl
conda install -y -q --file requirements/tests.txt

# Install codecov
pip install -q codecov
