To release a new version of qtconsole you need to follow these steps:

* git pull or git fetch/merge

* Close the current milestone on Github

* Update docs/source/changelog.rst with a PR.

* git clean -xfdi

* Update version in `_version.py` (set release version, remove 'dev0')

* git add and git commit with `Release X.X.X`

* python setup.py sdist

* activate pyenv-with-latest-setuptools && python setup.py bdist_wheel

* twine check dist/*

* twine upload dist/*

* git tag -a X.X.X -m 'Release X.X.X'

* Update version in `_version.py` (add 'dev0' and increment minor)

* git add and git commit with `Back to work`

* git push upstream master

* git push upstream --tags
