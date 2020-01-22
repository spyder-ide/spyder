:: This scripts helps activate a conda environment before running a spyder-kernel
@echo off

:: Create variables for arguments
set CONDA_ACTIVATE_SCRIPT=%1
set CONDA_ENV_PATH=%2
set CONDA_ENV_PYTHON=%3
set SPYDER_KERNEL_SPEC=%4

:: Enforce encoding
chcp 65001>nul

:: Activate kernel environment
call %CONDA_ACTIVATE_SCRIPT% %CONDA_ENV_PATH%

:: Start kernel
%CONDA_ENV_PYTHON% -m spyder_kernels.console -f %SPYDER_KERNEL_SPEC%
