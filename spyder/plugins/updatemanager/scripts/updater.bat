@rem This script creates/updates the Updater environment and installs Spyder Updater
@echo on

set "conda_exe=%~1" & rem conda executable path
set "conda_cmd=%~2" & rem conda subcommand
set "env_path=%~3" & rem Environment path
set "spy_updater_lock=%~4" & rem Environment lock file
set "spy_updater_conda=%~5" & rem Updater conda package

set "tmpdir=%~ps4"

call :redirect > "%tmpdir%\updater_stdout.log" 2> "%tmpdir%\updater_stderr.log"

:exit
    exit /b %errorlevel%

:redirect
    @echo on
    %conda_exe% %conda_cmd% -q --yes --prefix %env_path% --file "%spy_updater_lock%" || goto :eof
    %conda_exe% install -q --yes --prefix %env_path% --no-deps --force-reinstall "%spy_updater_conda%"
    goto :eof
