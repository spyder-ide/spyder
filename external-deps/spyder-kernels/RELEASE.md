# Instructions to release a new Spyder-kernels version

## Before starting the release

* Create a PR against `master` to update the Changelog with the following command:

    `loghub spyder-ide/spyder-kernels -m vX.X.X`

## To release a new version on PyPI

* Close the respective milestone on Github

* git checkout 3.x

* git fetch upstream && get merge upstream/3.x

* git clean -xfdi

* Update `_version.py` (set release version, remove 'dev0')

* git add . && git commit -m 'Release X.X.X'

* python -m pip install --upgrade pip

* pip install --upgrade --upgrade-strategy eager build setuptools twine wheel

* python -bb -X dev -W error -m build

* twine check --strict dist/*

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update `_version.py` (add 'dev0' and increment patch)

* git add . && git commit -m 'Back to work'

* git push upstream 3.x

* git push upstream --tags
