sphinx-build -b html doc doctmp
cd doctmp
zip ..\doc.zip -r *.*
cd ..
rmdir /S /Q doctmp