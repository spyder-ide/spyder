setlocal enableextensions enabledelayedexpansion

@echo off

set SPYDERLIB=%APPVEYOR_BUILD_FOLDER%\spyderlib
set TEST_CI_WIDGETS=True

REM Spyderlib
for /r "%SPYDERLIB%" %%f in (*.py) do (
    set file=%%f

    if "%%f"=="%SPYDERLIB%\spyder.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\pyplot.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:app\=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:plugins\=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:qt=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\utils\qthelpers.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\formlayout.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:external\=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:utils\external\=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:utils\help=!"=="!file!" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\utils\bsdsocket.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\utils\introspection\__init__.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\utils\introspection\module_completion.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\systemshell.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\inputhooks.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\sitecustomize.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\start_ipython_kernel.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

REM Spyplugins
for /r "%APPVEYOR_BUILD_FOLDER%\spyplugins" %%f in (*.py) do (
    set file=%%f

    if not "!file:widgets\=!"=="!file!" (    
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

endlocal
