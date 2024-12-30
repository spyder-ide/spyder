To release a new version of spyder-kernels on PyPI:

* Close the respective milestone on Github

* git checkout 3.x

* git fetch upstream && get merge upstream/3.x

* Update CHANGELOG.md with `loghub spyder-ide/spyder-kernels -m vX.X.X`

* git clean -xfdi

* Update `_version.py` (set release version, remove 'dev0')

* git add . && git commit -m 'Release X.X.X'

* python setup.py sdist

* python setup.py bdist_wheel

* twine check --strict dist/*

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update `_version.py` (add 'dev0' and increment patch)

* git add . && git commit -m 'Back to work'

* git push upstream 3.x

* git push upstream --tags
