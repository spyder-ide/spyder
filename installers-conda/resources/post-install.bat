:: This script launches Spyder after install
@echo off

echo %PREFIX% | findstr /b "%USERPROFILE%" > nul && (
    set shortcut_root=%APPDATA%
) || (
    set shortcut_root=%ALLUSERSPROFILE%
)
set shortcut="%shortcut_root%\Microsoft\Windows\Start Menu\Programs\spyder\Spyder.lnk"

set tmpdir=%TMP%\spyder
set launch_script=%tmpdir%\launch_script.bat

mkdir %tmpdir% 2> nul
(
echo @echo off
echo :loop
echo tasklist /fi "ImageName eq Spyder-*" /fo csv 2^>NUL ^| findstr /r "Spyder-.*-Windows-x86_64.exe"^>NUL
echo if "%%errorlevel%%"=="0" ^(
echo     timeout /t 1 /nobreak ^> nul
echo     goto loop
echo ^) else ^(
echo     start "" /B %shortcut%
echo     exit
echo ^)
) > %launch_script%

start "" /MIN %launch_script%
