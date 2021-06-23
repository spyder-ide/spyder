To release a new version of python-lsp-server:
1. git fetch upstream && git checkout upstream/master
2. Close milestone on GitHub
3. git clean -xfdi
4. Update CHANGELOG.md with loghub
5. git add -A && git commit -m "Update Changelog"
6. Update release version in ``_version.py`` (set release version, remove 'dev0')
7. git add -A && git commit -m "Release vX.X.X"
8. python setup.py sdist
9. python setup.py bdist_wheel
10. twine check
11. twine upload
12. git tag -a vX.X.X -m "Release vX.X.X"
13. Update development version in ``_version.py`` (add 'dev0' and increment minor)
14. git add -A && git commit -m "Back to work"
15. git push upstream master
16. git push upstream --tags
