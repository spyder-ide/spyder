@rem  This script launches Spyder after install
@echo off

if "%CI%"=="1" set no_launch_spyder=true
if "%INSTALLER_UNATTENDED%"=="1" set no_launch_spyder=true
if defined no_launch_spyder (
    @echo Installing in CI or silent mode, do not launch Spyder
    exit /b %errorlevel%
)

set mode=system
if exist "%PREFIX%\.nonadmin" set mode=user

@rem  Get shortcut path
for /F "tokens=*" %%i in (
    '%PREFIX%\python %PREFIX%\Scripts\menuinst_cli.py shortcut --mode=%mode%'
) do (
    set shortcut=%%~fi
)

@rem  Launch Spyder
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
