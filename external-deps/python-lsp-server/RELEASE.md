## Before the release:

1. Create pull request to update CHANGELOG.md with
    * `loghub python-lsp/python-lsp-server -m vX.X.X`
    * git add -A && git commit -m "Update changelog for X.X.X"

    This is necessary to run our tests before the release, so we can be sure
    everything is in order.
## To release a new version of python-lsp-server:

1. git fetch upstream && git checkout upstream/master
2. Close milestone on GitHub
3. git clean -xfdi
4. git tag -a vX.X.X -m "Release vX.X.X"
5. python -m pip install --upgrade pip
6. pip install --upgrade --upgrade-strategy eager build setuptools twine wheel
7. python -bb -X dev -W error -m build
8. twine check --strict dist/*
9. twine upload dist/*
10. git push upstream --tags
11. Create release on Github
