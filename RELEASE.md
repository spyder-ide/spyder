To release a new version of Spyder you need to follow these steps:

* git pull or git fetch/merge

* Update CHANGELOG.md

* Update Announcements.txt

* Update version in `__init__.py` (set release version, remove 'dev0')

* git add and git commit

* python setup.py sdist upload

* python2 setup.py bdist_wheel upload

* python3 setup.py bdist_wheel upload

* git tag -a vX.X.X -m 'comment'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* git add and git commit

* git push upstream master

* git push upstream --tags

* Optional: Create conda packages
    - conda build conda.recipe
    - anaconda upload spyder-*.tar.bz2 -u spyder-ide

* Publish release announcements to our list and the SciPy list

* Publish list of bugs and merged pull requests to our Github Releases page

* Create DMGs, upload them to our Bitbucket Downloads page and link them
  in our Github Releases page.
