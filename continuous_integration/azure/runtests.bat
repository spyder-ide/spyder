:: Activate conda env
conda activate test

:: Check manifest
check-manifest
if errorlevel 1 exit 1

:: Run tests several times
python runtests.py || python runtests.py || python runtests.py || python runtests.py || python runtests.py || exit 1

:: Run codecov if things were successful
codecov
if errorlevel 1 exit 1
