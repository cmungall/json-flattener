import os
from setuptools import setup, find_packages

NAME = 'json_flattener'
DESCRIPTION = 'Python library for denormalizing nested dicts or json objects to tables and back'
URL = 'https://github.com/cmungall/json-flattener'
AUTHOR = 'Chris Mungall'
EMAIL = 'cjmungall@lbl.gov'
REQUIRES_PYTHON = '>=3.7.0'
LICENSE = 'BSD'

VERSION = '0.1.9'
#version = pattern.search(text).group(1)

#with open("requirements.txt", "r") as FH:
#    REQUIREMENTS = FH.readlines()

EXTRAS = {}

setup(
    name=NAME,
    author=AUTHOR,
    author_email=EMAIL,
    version=VERSION,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    description=DESCRIPTION,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license=LICENSE,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    package_data={'json_flattener': ["config.yml"]},
    keywords='linkml data-science denormalization yaml json data-frames',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3'
    ],
    #install_requires=[r for r in REQUIREMENTS if not r.startswith("#")],
    install_requires=['click', 'pyyaml'],
    extras_require=EXTRAS,
    include_package_data=True,
    entry_points={
        'console_scripts': ['jfl=json_flattener.cli:main']
    },
    #setup_requires=['pbr'],
    #pbr=True,
)
