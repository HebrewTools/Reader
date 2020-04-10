from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='hebrew-reader',
    version='0.1',
    description='A tool to generate Biblical Hebrew readers',
    long_description=long_description,
    url='https://github.com/HebrewTools/Reader',
    author='Camil Staps',
    author_email='info@camilstaps.nl',
    license='MIT',
    install_requires=['text-fabric==7.*'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Religion',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Education',
        'Topic :: Religion',
        'Topic :: Utilities',
    ],
    keywords='hebrew bible biblical reader vocabulary',
    py_modules=['hebrewreader', 'hebrewreaderserver']
)
