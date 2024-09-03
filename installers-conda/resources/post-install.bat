rem This script launches Spyder after install
@echo off

set mode=system
if exist "%PREFIX%\.nonadmin" set mode=user

rem Get shortcut path
for /F "tokens=*" %%i in (
    '%PREFIX%\python %PREFIX%\Scripts\menuinst_cli.py shortcut --mode=%mode%'
) do (
    set shortcut=%%~fi
)

rem Launch Spyder
set tmpdir=%TMP%\spyder
set launch_script=%tmpdir%\launch_script.bat

if not exist "%tmpdir%" mkdir "%tmpdir%"
(
echo @echo off
echo :loop
echo tasklist /fi "ImageName eq Spyder-*" /fo csv 2^>NUL ^| findstr /r "Spyder-.*Windows-x86_64.exe"^>NUL
echo if "%%errorlevel%%"=="0" ^(
echo     timeout /t 1 /nobreak ^> nul
echo     goto loop
echo ^) else ^(
echo     start "" /B "%shortcut%"
echo     exit
echo ^)
) > "%launch_script%"

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -WindowStyle hidden -Command "& {Start-Process -FilePath %launch_script% -NoNewWindow}"
