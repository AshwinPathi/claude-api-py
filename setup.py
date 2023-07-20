from setuptools import setup, find_packages

from claude import __version__

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='rev_claude_api',
    packages=['claude'],
    version=__version__,
    license='MIT',
    url='https://github.com/AshwinPathi/claude',
    description='Unofficial Anthropic Claude API for Python3.',
    keywords=['llm', 'claude', 'api', 'gpt'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    py_modules=find_packages(),
    install_requires=[
        'sseclient-py',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
