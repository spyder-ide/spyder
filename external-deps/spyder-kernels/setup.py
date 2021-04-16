# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Jupyter Kernels for the Spyder consoles."""

# Standard library imports
import ast
import io
import os

# Third party imports
from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

with io.open('README.md', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()


def get_version(module='spyder_kernels'):
    """Get version."""
    with open(os.path.join(HERE, module, '_version.py'), 'r') as f:
        data = f.read()
    lines = data.split('\n')
    for line in lines:
        if line.startswith('VERSION_INFO'):
            version_tuple = ast.literal_eval(line.split('=')[-1].strip())
            version = '.'.join(map(str, version_tuple))
            break
    return version


REQUIREMENTS = [
    'cloudpickle',
    'decorator<5',  # Higher versions break the Cython magic
    'ipykernel<5; python_version<"3"',
    'ipykernel>=5.3.0; python_version>="3"',
    'ipython<6; python_version<"3"',
    'ipython>=7.6.0; python_version>="3"',
    'jupyter-client>=5.3.4',
    'pyzmq>=17',
    'wurlitzer>=1.0.3;platform_system!="Windows"',
]

TEST_REQUIREMENTS = [
    'codecov',
    'cython',
    'dask[distributed]',
    'flaky',
    'matplotlib',
    'mock',
    'numpy',
    'pandas',
    'pytest',
    'pytest-cov',
    'scipy',
    'xarray',
    'pillow',
]

setup(
    name='spyder-kernels',
    version=get_version(),
    keywords='spyder jupyter kernel ipython console',
    url='https://github.com/spyder-ide/spyder-kernels',
    download_url="https://www.spyder-ide.org/#fh5co-download",
    license='MIT',
    author='Spyder Development Team',
    author_email="spyderlib@googlegroups.com",
    description="Jupyter kernels for Spyder's console",
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['docs', '*tests']),
    install_requires=REQUIREMENTS,
    extras_require={'test': TEST_REQUIREMENTS},
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Jupyter',
        'Framework :: IPython',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Interpreters',
    ]
)
