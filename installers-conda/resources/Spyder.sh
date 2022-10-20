#!/bin/bash
# Get user environment variables
eval "$($SHELL -l -c "declare -x")"

# Activate the conda environment
source $ROOT_PREFIX/bin/activate $PREFIX

# Find root conda and mamba
export PATH=$ROOT_PREFIX/condabin:$PATH

# Launch Spyder
$(dirname "$0")/python $CONDA_PREFIX/bin/spyder "$@"
