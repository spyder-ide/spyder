To release a new version of Spyder you need to follow these steps:

* git pull or git fetch/merge

* Update CHANGELOG.md

* Update Announcements.txt

* Update version in:
  * __init__.py (set release version, remove 'dev0')
  * continuous_integration/conda-recipes/spyder/meta.yaml
  * continuous_integration/travis/run_test.sh
  * continuous_integration/appveyor/run_test.bat

* git add and git commit

* python setup.py sdist upload

* python2 setup.py bdist_wheel upload

* python3 setup.py bdist_wheel upload

* git tag -a vX.X.X -m 'comment'

* Update version in __init__.py (add 'dev0' and increment minor)

* git add and git commit

* git push

* git push --tags

* Publish release announcements to our list and the SciPy list

* Publish list of bugs and merged pull requests in the Github Releases page

* Create DMGs
