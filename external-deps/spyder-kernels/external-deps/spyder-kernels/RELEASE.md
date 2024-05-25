To release a new version of spyder-kernels on PyPI:

* Close the respective milestone on Github

* git checkout 2.x

* git fetch upstream && get merge upstream/2.x

* git clean -xfdi

* Update CHANGELOG.md with `loghub spyder-ide/spyder-kernels -m vX.X.X`

* Update `_version.py` (set release version, remove 'dev0')

* git add . && git commit -m 'Release X.X.X'

* python setup.py sdist

* python setup.py bdist_wheel

* twine check dist/*

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update `_version.py` (add 'dev0' and increment minor)

* git add . && git commit -m 'Back to work'

* git checkout master

* git merge 2.x

* git push upstream master

* git push upstream 2.x

* git push upstream --tags
