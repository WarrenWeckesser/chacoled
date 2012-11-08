#! /usr/bin/env python

import os

from setuptools import setup, find_packages


# Execute __init__.py and save the namespace in init_data.
# __init__.py defines __version__, which we'll use later in the
# call to setup().
init_data = {}
execfile(os.path.join('chacoled', '__init__.py'), init_data)

# FIXME: Add dependencies...

setup(
    name='chacoled',
    description='Chaco Colormap Editor',
    author='Warren Weckesser',
    author_email='warren.weckesser@gmail.com',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    version=init_data['__version__'],
    entry_points={
        'console_scripts': [
            'chacoled = chacoled.colormap_app:main',
        ]
    }
)
