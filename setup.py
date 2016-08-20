from setuptools import setup, find_packages, Extension

name = 'ikpdb'
version = '1.0.0-alpha'


long_description = (
    '\nDetailed Documentation\n'
      '######################\n'
    + '\n' +
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '############\n'
    + '\n' +
    open('CONTRIBUTORS.txt').read()
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
    url='https://github.com/cmorisse/ikpdb',
    license='MIT',
    author='Cyril MORISSE',
    author_email='cmorisse@boxes3.net',
    description="A hackable debugger built for network remote debugging and web/online IDE integration.",
    long_description = long_description,
    keywords = "debugger debug remote tcp",
    include_package_data=True,
    #install_requires=['setuptools',],
    classifiers=[
        #'Framework :: Buildout',
        'Development Status :: 4 - Alpha',
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
