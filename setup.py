from setuptools import setup, find_packages

from src import __version__

setup(
    name='claude',
    version=__version__,
    url='https://github.com/AshwinPathi/claude',
    py_modules=find_packages(),

    install_requires=[
        'sseclient',
    ],
)
