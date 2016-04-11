"""
'spyplugins' makes uses of namespace packages to keep different plugins
organized in the sitepackages directory and in the user directory.

Spyder plugins can be of 'io' type or 'ui' type. Each type also makes use
of namespace packages.

For more information on namespace packages visit:
- https://www.python.org/dev/peps/pep-0382/
- https://www.python.org/dev/peps/pep-0420/
"""
__import__('pkg_resources').declare_namespace(__name__)
