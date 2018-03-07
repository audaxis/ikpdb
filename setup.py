# coding: utf-8

#
# This file is part of the IKPdb Debugger
# Copyright (c) 2016, 2017 by Cyril MORISSE, Audaxis
# Licence: MIT. See LICENCE at repository root
#

from setuptools import setup, find_packages, Extension

name = 'ikpdb'
version = '1.2.2'


long_description = (
    open('README.rst').read()
)

iksettrace_module = Extension('iksettrace', sources=['iksettrace.c'])

setup(
    name = name,
    version = version,
    #packages = find_packages('src'),
    py_modules = ['ikpdb'],
    #package_dir={'': 'src'},
    license='MIT',
    author='Cyril MORISSE, Audaxis',
    author_email='cmorisse@boxes3.net',
    description="A hackable CPython remote debugger designed for the Web and online IDE integration.",
    long_description = long_description,
    keywords = "debugger debug remote tcp",
    include_package_data=True,
    url = 'https://github.com/audaxis/ikpdb',
    
    # files will be hosted on index
    #download_url = 'https://github.com/cmorisse/ikpdb/archive/1.0.x.zip', 
    
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
