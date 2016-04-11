conda info

cd %APPVEYOR_BUILD_FOLDER%
python setup.py sdist
if errorlevel 1 exit 1

cd %APPVEYOR_BUILD_FOLDER%\continuous_integration\conda-recipes
if %USE_QT_API%==PyQt5 (
    conda build -q qtconsole
    if errorlevel 1 exit 1
)

conda build -q spyder
if errorlevel 1 exit 1
