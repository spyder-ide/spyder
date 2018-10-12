setlocal enableextensions enabledelayedexpansion

@echo off

set SPYDER=%APPVEYOR_BUILD_FOLDER%\spyder
set TEST_CI_WIDGETS=True

:: These tests are failing intermittently in Python 2.
:: Disabling them for now.
if %PYTHON_VERSION%==2.7 (
    exit 0
)

:: Spyder
for /r "%SPYDER%" %%f in (*.py) do (
    set file=%%f

    if "%%f"=="%SPYDER%\pyplot.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:app\=!"=="!file!" (
        :: Most files in this dir can't be ran alone
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:plugins\=!"=="!file!" (
        :: Plugins can't be ran independently
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:tests\=!"=="!file!" (
        :: We don't want py.test's to be run here
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:test\=!"=="!file!" (
        :: We don't want py.test's to be run here
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:site\=!"=="!file!" (
        :: We can't test our site files
        echo --- NOT testing %%f ---
        echo.
    ) else if not "!file:ipython\=!"=="!file!" (
        :: We can't test these files outside of our IPython console
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDER%\utils\qthelpers.py" (
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
    ) else if "%%f"=="%SPYDER%\utils\bsdsocket.py" (
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%spyder%\utils\inputhooks.py" (
        :: It can't be tested outside of a Python console
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDER%\utils\introspection\fallback_plugin.py" (
        :: We have to investigate this failure!
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDER%\widgets\editor.py" (
        :: This is making AppVeyor to time out!
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%spyder%\widgets\externalshell\systemshell.py" (
        :: This is failing randomly
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%spyder%\widgets\ipythonconsole\__init__.py" (
        :: This is failing randomly
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDER%\widgets\sourcecode\codeeditor.py" (
        :: Testing file crashes on Python 2.7 without any reason
        if %PYTHON_VERSION%==2.7 (
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

:: Third-party plugins
for /r "%APPVEYOR_BUILD_FOLDER%\spyder_breakpoints" %%f in (*.py) do (
    set file=%%f
    if not "!file:widgets\=!"=="!file!" (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

for /r "%APPVEYOR_BUILD_FOLDER%\spyder_profiler" %%f in (*.py) do (
    set file=%%f
    if not "!file:widgets\=!"=="!file!" (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

for /r "%APPVEYOR_BUILD_FOLDER%\spyder_pylint" %%f in (*.py) do (
    set file=%%f
    if not "!file:widgets\=!"=="!file!" (
        echo --- Testing %%f ---
        python "%%f" || exit 1
        echo.
    )
)

endlocal
