sphinx-build -b htmlhelp doc doctmp
"C:\Program Files\HTML Help Workshop\hhc.exe" doctmp\Spyderdoc.hhp
copy doctmp\Spyderdoc.chm .
rmdir /S /Q doctmp