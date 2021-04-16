#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A dark style sheet for QtWidgets application.
"""

# Standard library imports
from setuptools import find_packages, setup

# Local imports
from qdarkstyle import __doc__ as long_desc
from qdarkstyle import __version__

install_requires = ['qtpy>=1.9']

extras_require = {
    'develop': ['qtsass', 'watchdog'],
    'docs': ['sphinx', 'sphinx_rtd_theme'],
    'example': ['pyqt5', 'pyside2']
}

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Win32 (MS Windows)',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX :: Linux',
    'Operating System :: MacOS',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Topic :: Software Development :: Libraries :: Application Frameworks'
]

setup(
    name='QDarkStyle',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/ColinDuquesnoy/QDarkStyleSheet',
    license='MIT',
    author='Colin Duquesnoy',
    author_email='colin.duquesnoy@gmail.com',
    description='The most complete dark/light style sheet for C++/Python and Qt applications',
    long_description=long_desc,
    long_description_content_type='text/x-rst',
    include_package_data=True,  # add data file from MANIFEST.in #193
    classifiers=classifiers,
    zip_safe=False,  # don't use eggs
    entry_points={"console_scripts": ["qdarkstyle=qdarkstyle.__main__:main",
                                      "qdarkstyle.example=qdarkstyle.example.__main__:main",
                                      "qdarkstyle.utils=qdarkstyle.utils.__main__:main"]},
    extras_require=extras_require,
    install_requires=install_requires,
    project_urls={
        "Issues": "https://github.com/ColinDuquesnoy/QDarkStyleSheet/issues",
        "Docs": "https://qdarkstylesheet.readthedocs.io/en/stable",
    }
)
