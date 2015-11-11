cd %APPVEYOR_BUILD_FOLDER%
python setup.py sdist
if errorlevel 1 exit 1

cd %APPVEYOR_BUILD_FOLDER%\continuous_integration\conda-recipes
conda build -q spyder
if errorlevel 1 exit 1
