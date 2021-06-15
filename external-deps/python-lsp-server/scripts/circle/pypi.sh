#!/bin/bash -e

if [ -z "$CI" ]; then
    echo "Will only continue on CI"
    exit
fi

# build package and upload to private pypi index
rm -f ~/.pypirc
echo "[distutils]" >> ~/.pypirc
echo "index-servers = pypi-private" >> ~/.pypirc
echo "[pypi-private]" >> ~/.pypirc
echo "repository=https://$PYPI_HOST" >> ~/.pypirc
echo "username=$PYPI_USERNAME" >> ~/.pypirc
echo "password=$PYPI_PASSWORD" >> ~/.pypirc

python setup.py bdist_wheel sdist upload -r pypi-private
