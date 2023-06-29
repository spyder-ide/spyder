:: This script launches Spyder after install
@echo off

echo %PREFIX% | findstr /b "%USERPROFILE%" > nul && (
    set shortcut_root=%APPDATA%
) || (
    set shortcut_root=%ALLUSERSPROFILE%
)
start "" /B "%shortcut_root%\Microsoft\Windows\Start Menu\Programs\spyder\Spyder.lnk"
