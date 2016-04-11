setlocal enableextensions enabledelayedexpansion

@echo off

set SPYDERLIB=%APPVEYOR_BUILD_FOLDER%\spyderlib
set TEST_CI_WIDGETS=True

:: Spyderlib
for /r "%SPYDERLIB%" %%f in (*.py) do (
    set file=%%f

    if "%%f"=="%SPYDERLIB%\pyplot.py" (
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
    ) else if "%%f"=="%SPYDERLIB%\widgets\sourcecode\codeeditor.py" (
        :: Testing file crashes on Python 2.7 without any reason
        if %PYTHON_VERSION%==2.7 (
            echo --- NOT testing %%f ---
            echo.
        ) else (
            echo --- Testing %%f ---
            python "%%f" || exit 1
            echo.
        )
    ) else if "%%f"=="%SPYDERLIB%\widgets\browser.py" (
        :: Not testing this file for now because m-labs builds doesn't have
        :: web widgets
        if %USE_QT_API%==PyQt5 (
            echo --- NOT testing %%f ---
            echo.
        ) else (
            echo --- Testing %%f ---
            python "%%f" || exit 1
            echo.
        )
    ) else if "%%f"=="%SPYDERLIB%\widgets\ipython.py" (
        :: Not testing this file for now because m-labs builds doesn't have
        :: web widgets
        if %USE_QT_API%==PyQt5 (
            echo --- NOT testing %%f ---
            echo.
        ) else (
            echo --- Testing %%f ---
            python "%%f" || exit 1
            echo.
        )
    ) else if "%%f"=="%SPYDERLIB%\widgets\pydocgui.py" (
        :: Not testing this file for now because m-labs builds doesn't have
        :: web widgets
        if %USE_QT_API%==PyQt5 (
            echo --- NOT testing %%f ---
            echo.
        ) else (
            echo --- Testing %%f ---
            python "%%f" || exit 1
            echo.
        )
    ) else (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

:: Spyplugins
for /r "%APPVEYOR_BUILD_FOLDER%\spyplugins" %%f in (*.py) do (
    set file=%%f

    if not "!file:widgets\=!"=="!file!" (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

endlocal
