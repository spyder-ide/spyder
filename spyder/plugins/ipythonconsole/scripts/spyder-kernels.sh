#!/usr/bin/env bash

# This scripts helps activate a conda environment before running a spyder-kernel
CONDA_ACTIVATE_SCRIPT=$1
CONDA_ENV_PATH=$2
CONDA_ENV_PYTHON=$3
SPYDER_KERNEL_ARG=$4
SPYDER_KERNEL_SPEC=$5

source $CONDA_ACTIVATE_SCRIPT $CONDA_ENV_PATH
$CONDA_ENV_PYTHON -m spyder_kernels.console.start $SPYDER_KERNEL_ARG $SPYDER_KERNEL_SPEC
