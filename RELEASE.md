To release a new version of Spyder you need to follow these steps:

* git pull or git fetch/merge

* git clean -xfdi

* Update CHANGELOG.md

* Update Announcements.md

* Update version in `__init__.py` (set release version, remove 'dev0')

* git add and git commit with `Release X.X.X`

* python setup.py sdist upload

* python setup.py bdist_wheel --plat-name manylinux1_x86_64 upload

* python setup.py bdist_wheel --plat-name manylinux1_i686 upload

* python setup.py bdist_wheel upload

* git tag -a vX.X.X -m 'Release X.X.X'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* git add and git commit with `[ci skip]`

* git checkout master

* git merge 3.x

* git commit with `[ci skip]`

* git push upstream master

* git push upstream 3.x

* git push upstream --tags

* Optional: Create conda packages
    - conda build conda.recipe
    - anaconda upload spyder-*.tar.bz2 -u spyder-ide

* Publish release announcements to our list and the SciPy list

* Publish list of bugs and merged pull requests to our Github Releases page

* Create DMGs, upload them to our Bitbucket Downloads page and link them
  in our Github Releases page.
