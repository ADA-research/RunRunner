'''Setup for runrunner.'''
from setuptools import setup, find_packages

setup(
    name='runrunner',
    version='0.0.3',
    packages=find_packages(include=['runrunner']),
    install_requires=[
        'pydantic <2.0a',
    ]
)
