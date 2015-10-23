cd %APPVEYOR_BUILD_FOLDER%\\continuous_integration\\conda-recipes

conda build -q spyder
