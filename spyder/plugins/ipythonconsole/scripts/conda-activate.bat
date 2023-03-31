:: This scripts helps activate a conda environment before running a spyder-kernel
@echo off

:: Create variables for arguments removing quotes
set CONDA_ACTIVATE_SCRIPT=%~1
set CONDA_ENV_PATH=%~2
set CONDA_ENV_PYTHON=%~3
set SPYDER_KERNEL_SPEC=%~4

:: Enforce encoding
chcp 65001>nul

:: Activate kernel environment
echo %CONDA_ACTIVATE_SCRIPT%| findstr /e micromamba.exe>Nul && goto micromamba || goto conda

:micromamba Activate using micromamba
for /f %%i in ('"%CONDA_ACTIVATE_SCRIPT%" shell activate %CONDA_ENV_PATH%') do set SCRIPT=%%i
call %SCRIPT%
goto start

:conda Activate using conda
call %CONDA_ACTIVATE_SCRIPT% %CONDA_ENV_PATH%
goto start

:start Start kernel
%CONDA_ENV_PYTHON% -m spyder_kernels.console -f %SPYDER_KERNEL_SPEC%
