#!/usr/bin/python3.5


from setuptools import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = open('README.md').read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

version = '0.3'

setup(
    name='census-wikidata-bot',
    version=version,
    install_requires=requirements,
    author='Sasan Bahadaran',
    author_email='sbahadaran@doc.gov',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/CommerceDataService/census-wikidata-bot',
    license='MIT',
    description='A bot to push official Census data to Wikidata and Wikipedia.',
    long_description=long_description,
    entry_points={
        'console_scripts': [
            'census-wikidata-bot = census-wikidata-bot:cli',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
