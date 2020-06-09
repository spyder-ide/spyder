:: This scripts helps activate a conda environment before running a spyder-kernel
@echo off

:: Create variables for arguments
set ENV_PYTHON=%1
set SPYDER_KERNEL_SPEC=%2

:: Enforce encoding
chcp 65001>nul

:: Start kernel
%ENV_PYTHON% -m spyder_kernels.console -f %SPYDER_KERNEL_SPEC%
