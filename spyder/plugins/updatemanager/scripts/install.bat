:: This script updates or installs a new version of Spyder
@echo off

:: Create variables from arguments
:parse
IF "%~1"=="" GOTO endparse
IF "%~1"=="-p" set prefix=%2 & SHIFT
IF "%~1"=="-i" set install_exe=%2 & SHIFT
IF "%~1"=="-c" set conda=%2 & SHIFT
IF "%~1"=="-v" set spy_ver=%2 & SHIFT
SHIFT
GOTO parse
:endparse

:: Enforce encoding
chcp 65001>nul

IF not "%conda%"=="" IF not "%spy_ver%"=="" (
    call :update_subroutine
    call :launch_spyder
    goto exit
)

IF not "%install_exe%"=="" (
    call :install_subroutine
    goto exit
)

:exit
exit %ERRORLEVEL%

:install_subroutine
    echo Installing Spyder from: %install_exe%

    call :wait_for_spyder_quit

    :: Uninstall Spyder
    for %%I in ("%prefix%\..\..") do set "conda_root=%%~fI"

    echo Install will proceed after the current Spyder version is uninstalled.
    start %conda_root%\Uninstall-Spyder.exe

    :: Must wait for uninstaller to appear on tasklist
    :wait_for_uninstall_start
    tasklist /fi "ImageName eq Un_A.exe" /fo csv 2>NUL | find /i "Un_A.exe">NUL
    IF "%ERRORLEVEL%"=="1" (
        timeout /t 1 /nobreak > nul
        goto wait_for_uninstall_start
    )
    echo Uninstall in progress...

    :wait_for_uninstall
    timeout /t 1 /nobreak > nul
    tasklist /fi "ImageName eq Un_A.exe" /fo csv 2>NUL | find /i "Un_A.exe">NUL
    IF "%ERRORLEVEL%"=="0" goto wait_for_uninstall
    echo Uninstall complete.

    start %install_exe%
    goto :EOF

:update_subroutine
    echo =========================================================
    echo Updating Spyder
    echo ---------------
    echo
    echo IMPORTANT: Do not close this window until it has finished
    echo =========================================================
    echo

    call :wait_for_spyder_quit

    %conda% install -p %prefix% -c conda-forge --override-channels -y spyder=%spy_ver%
    set /P CONT=Press any key to exit...
    goto :EOF

:wait_for_spyder_quit
    echo Waiting for Spyder to quit...
    :loop
    tasklist /fi "ImageName eq spyder.exe" /fo csv 2>NUL | find /i "spyder.exe">NUL
    IF "%ERRORLEVEL%"=="0" (
        timeout /t 1 /nobreak > nul
        goto loop
    )
    echo Spyder is quit.
    goto :EOF

:launch_spyder
    echo %prefix% | findstr /b "%USERPROFILE%" > nul && (
        set shortcut_root=%APPDATA%
    ) || (
        set shortcut_root=%ALLUSERSPROFILE%
    )
    start "" /B "%shortcut_root%\Microsoft\Windows\Start Menu\Programs\spyder\Spyder.lnk"
    goto :EOF
