To release a new version of spyder-kernels on PyPI:

* Create an issue announcing the incoming release

* Close the respective milestone in GitHub

* git checkout master

* git fetch upstream && get merge upstream/master

* git clean -xfdi

* Update CHANGELOG.md with `loghub spyder-ide/spyder-kernels -zr "spyder-kernels vX.X.X"`

* Update `_version.py` (set release version, remove 'dev0')

* git add . && git commit -m 'Release X.X.X'

* python setup.py sdist

* python setup.py bdist_wheel

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update `_version.py` (add 'dev0' and increment minor)

* git add . && git commit -m 'Back to work'

* git checkout master

* git merge 1.x

* git push upstream master

* git push upstream 1.x

* git push upstream --tags
