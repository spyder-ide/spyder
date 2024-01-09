:: This script launches Spyder after install
@echo off

set spy_rt=%PREFIX%\envs\spyder-runtime
set menu=%spy_rt%\Menu\spyder-menu.json
set mode=system
if exist "%PREFIX%\.nonadmin" set mode=user

:: Get shortcut path
for /F "tokens=*" %%i in (
    '%PREFIX%\python -c "from menuinst.api import _load; menu, menu_items = _load(r'%menu%', target_prefix=r'%spy_rt%', base_prefix=r'%PREFIX%', _mode='%mode%'); print(menu_items[0]._paths()[0])"'
) do (
    set shortcut=%%~fi
)

:: Launch Spyder
set tmpdir=%TMP%\spyder
set launch_script=%tmpdir%\launch_script.bat

if not exist "%tmpdir%" mkdir "%tmpdir%"
(
echo @echo off
echo :loop
echo tasklist /fi "ImageName eq Spyder-*" /fo csv 2^>NUL ^| findstr /r "Spyder-.*-Windows-x86_64.exe"^>NUL
echo if "%%errorlevel%%"=="0" ^(
echo     timeout /t 1 /nobreak ^> nul
echo     goto loop
echo ^) else ^(
echo     start "" /B "%shortcut%"
echo     exit
echo ^)
) > "%launch_script%"

C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -WindowStyle hidden -Command "& {Start-Process -FilePath %launch_script% -NoNewWindow}"
