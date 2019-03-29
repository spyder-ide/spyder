To release a new version of Spyder you need to follow these steps:

* Close the current milestone on Github

* git pull or git fetch/merge

* Update CHANGELOG.md

* Update Announcements.md

* git clean -xfdi

* Update version in `__init__.py` (set release version, remove 'dev0')

* git add and git commit with `Release X.X.X`

* python setup.py sdist

* activate py2env-with-latest-setuptools && python2 setup.py bdist_wheel

* activate py3env-with-latest-setuptools && python3 setup.py bdist_wheel

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* git add and git commit with `[ci skip]`

* git checkout master

* git merge 3.x

* git commit with `[ci skip]`

* git push upstream master

* git push upstream 3.x

* git push upstream --tags

* Publish release announcements to our list and the SciPy list

* Publish release in our Github Releases page
