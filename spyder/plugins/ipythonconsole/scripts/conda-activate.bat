:: This scripts helps activate a conda environment before running a spyder-kernel
@echo off

:: Create variables for arguments
set CODEPAGE=%1
set CONDA_ACTIVATE_SCRIPT=%2
set CONDA_ENV_PATH=%3
set CONDA_ENV_PYTHON=%4
set SPYDER_KERNEL_SPEC=%5

:: Set correct encoding
chcp %CODEPAGE%>nul

:: Activate kernel environment
call %CONDA_ACTIVATE_SCRIPT% %CONDA_ENV_PATH%

:: Start kernel
%CONDA_ENV_PYTHON% -m spyder_kernels.console -f %SPYDER_KERNEL_SPEC%
