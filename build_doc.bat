rmdir /S /Q spyderlib\doc
sphinx-build -b html doc_src spyderlib\doc
sphinx-build -b htmlhelp doc_src doctmp
pause