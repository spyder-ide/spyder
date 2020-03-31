#!/bin/bash -l
# This script helps activate an internal environment before running a spyder-kernel

# Create variables for arguments
ENV_PYTHON=$1
SPYDER_KERNEL_SPEC=$2

# Start kernel
$ENV_PYTHON -m spyder_kernels.console -f $SPYDER_KERNEL_SPEC
