'''Setup for RunRunner.'''
from setuptools import setup, find_packages

setup(
    name='RunRunner',
    version='0.1.1',
    url='https://github.com/thijssnelleman/RunRunner',
    author='Thijs Snelleman',
    author_email='fkt_sparkle@aim.rwth-aachen.de',
    description='RunRunner is a wrapper library for creating and managing subprocesses and their status, mainly focussed on using Slurm but (in absence) can also work with local jobs.',
    long_description=open("README.MD", 'r').read(),
    long_description_content_type="text/markdown",
    packages=find_packages(include=['runrunner']),
    install_requires=[
        'pydantic <2.0a',
    ]
)
