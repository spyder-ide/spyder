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
    'ipykernel>=6.29.3,<7',
    'ipython>=8.12.2,<8.13; python_version=="3.8"',
    'ipython>=8.13.0,<9,!=8.17.1; python_version>"3.8"',
    'jupyter-client>=7.4.9,<9',
    'pyzmq>=24.0.0',
    'pyxdg>=0.26;platform_system=="Linux"',
    # We need at least this version of traitlets to fix an error when setting
    # the Matplotlib inline backend formats.
    # Fixes spyder-ide/spyder#24390
    'traitlets>=5.14.3',
    'wurlitzer>=1.0.3;platform_system!="Windows"',
]

TEST_REQUIREMENTS = [
    "cython",
    "dask[distributed]",
    "flaky",
    "matplotlib",
    "mock",
    "numpy",
    "pandas",
    "polars",
    "pyarrow",
    "pytest",
    "pytest-cov",
    "scipy",
    "xarray",
    "pillow",
    "django",
    "h5py",
    "pydicom",
    "anyio",
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
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Jupyter',
        'Framework :: IPython',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Interpreters',
    ]
)
