#!/usr/bin/env bash
# This script helps activate a conda environment before running a spyder-kernel

# Create variables for arguments
CONDA_ACTIVATE_SCRIPT=$1
CONDA_ENV_PATH=$2
CONDA_ENV_PYTHON=$3
SPYDER_KERNEL_SPEC=$4

# Activate kernel environment
if [[ "$CONDA_ACTIVATE_SCRIPT" = *"micromamba" ]]; then
    eval "$($CONDA_ACTIVATE_SCRIPT shell activate -p $CONDA_ENV_PATH)"
else
    source $CONDA_ACTIVATE_SCRIPT $CONDA_ENV_PATH
fi

# Start kernel
$CONDA_ENV_PYTHON -m spyder_kernels.console -f $SPYDER_KERNEL_SPEC
