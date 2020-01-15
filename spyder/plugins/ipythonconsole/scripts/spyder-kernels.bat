:: This scripts helps activate a conda environment before running a spyder-kernel
@echo off

set CODEPAGE=$1
set CONDA_ACTIVATE_SCRIPT=%2
set CONDA_ENV_PATH=%3
set CONDA_ENV_PYTHON=%4
set SPYDER_KERNEL_ARG=%5
set SPYDER_KERNEL_SPEC=%6

chcp %CODEPAGE%
call %CONDA_ACTIVATE_SCRIPT% %CONDA_ENV_PATH%
%CONDA_ENV_PYTHON% -m spyder_kernels.console.start %SPYDER_KERNEL_ARG% %SPYDER_KERNEL_SPEC%
