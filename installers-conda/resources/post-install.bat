@rem  This script launches Spyder after install
@echo off
@setlocal ENABLEDELAYEDEXPANSION

call :redirect 2>&1 >> %PREFIX%\install.log

:redirect
@echo Environment Variables:
set

@rem ---- User site-packages
@rem  Prevent using user site-packages
@rem  See https://github.com/spyder-ide/spyder/issues/24773
set site=%PREFIX%\envs\spyder-runtime\Lib\site.py
set site_tmp=%PREFIX%\envs\spyder-runtime\Lib\_site.py
for /f "delims=" %%i in (%site%) do (
    set s=%%i
    echo !s! | findstr /b /c:"ENABLE_USER_SITE = None" && set s=!s:None=False!
    echo !s!>> %site_tmp%
)
move /y %site_tmp% %site%


if defined CI set no_launch_spyder=true
if "%INSTALLER_UNATTENDED%"=="1" set no_launch_spyder=true
if "%START_SPYDER%"=="False" set no_launch_spyder=true
if "%no_launch_spyder%"=="true" (
    @echo Do not launch Spyder
    exit /b %errorlevel%
) else (
    @echo Launching Spyder after install completed.
)

@rem ---- Get shortcut path
set mode=system
if exist "%PREFIX%\.nonadmin" set mode=user

for /F "tokens=*" %%i in (
    '%PREFIX%\python %PREFIX%\Scripts\menuinst_cli.py shortcut --mode=%mode%'
) do (
    set shortcut=%%~fi
)
@echo shortcut = %shortcut%

@rem ---- Launch Spyder
set tmpdir=%TMP%\spyder
set launch_script=%tmpdir%\launch_script.bat

if not exist "%tmpdir%" mkdir "%tmpdir%"
(
    echo @echo off
    echo :loop
    echo tasklist /fi "ImageName eq Spyder-*" /fo csv 2^>NUL ^| findstr /r "Spyder-.*Windows-x86_64.exe"^>NUL
    echo if "%%errorlevel%%"=="0" ^(
    echo     @rem  Installer is still running
    echo     timeout /t 1 /nobreak ^> nul
    echo     goto loop
    echo ^) else ^(
    echo     start "" /B "%shortcut%"
    echo     exit
    echo ^)
) > "%launch_script%"

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -WindowStyle hidden -Command "& {Start-Process -FilePath %launch_script% -NoNewWindow}"
