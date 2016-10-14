# coding: utf-8

#
# This file is part of the IKPdb Debugger
# Copyright (c) 2016 by Cyril MORISSE, Audaxis
# Licence: MIT. See LICENCE at repository root
#

from setuptools import setup, find_packages, Extension

name = 'ikpdb'
version = '1.0.0-beta'


long_description = (
    '\nDetailed Documentation\n'
      '######################\n'
    + '\n' +
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '############\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    'Change history\n'
    '##############\n'
    + '\n' +
    open('CHANGES.txt').read()
    + '\n'
)

iksettrace_module = Extension('iksettrace', sources=['iksettrace.c'])

setup(
    name = name,
    version = version,
    #packages = find_packages('src'),
    py_modules = ['ikpdb'],
    #package_dir={'': 'src'},
    url='https://github.com/audaxis/ikpdb',
    license='MIT',
    author='Cyril MORISSE, Audaxis',
    author_email='cmorisse@boxes3.net',
    description="A hackable CPython remote debugger designed for the Web and online IDE integration.",
    long_description = long_description,
    keywords = "debugger debug remote tcp",
    include_package_data=True,
    #install_requires=['setuptools',],
    classifiers=[
        #'Framework :: Buildout',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Debuggers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Natural Language :: English',
     ],
     ext_modules=[iksettrace_module]
#    ,entry_points={
#        'console_scripts': [
#            'ikpdb=ikpdb:main',
#        ],
#    },     

)
