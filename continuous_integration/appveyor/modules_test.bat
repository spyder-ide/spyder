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
        :: This is failing randomly
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\utils\introspection\plugin_client.py" (
        :: We have to investigate this failure!
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\editor.py" (
        :: This is making AppVeyor to time out!
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\systemshell.py" (
        :: This is failing randomly
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\inputhooks.py" (
        :: It can't be tested outside of a Python console
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\sitecustomize.py" (
        :: It can't be tested outside of a Python console
        echo --- NOT testing %%f ---
        echo.
    ) else if "%%f"=="%SPYDERLIB%\widgets\externalshell\start_ipython_kernel.py" (
        :: It can't be tested outside of a Qtconsole
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
