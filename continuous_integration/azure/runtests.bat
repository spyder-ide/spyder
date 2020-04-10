:: Activate conda env
conda activate test

:: Check manifest
check-manifest

:: Run tests several times
python runtests.py || python runtests.py || python runtests.py || python runtests.py || python runtests.py || exit 1

:: Run codecov if things were successful
codecov
