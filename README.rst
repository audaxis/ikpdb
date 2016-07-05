=====
IKPdb
=====

IKPdb is a python (CPython 2.7) debugger built to work with online IDE (eg. cloud9)

IKPdb supports only CPython 2.7 (for now).

IKPDb have a decent feature set.
You can see it in action and test it using Cloud9 (http://c9.io) using the ikpdb Cloud 9 plugin.

--------------------
Content of this file
--------------------

- Licence
- Installation
- Usage
- 

License
=======

IKPdb is licensed under MIT License. See LICENCE.txt

Installation
============

From pypi
---------

Use pip or easy_install:

::

    $ pip install ikpdb 
    or
    $ easy_install ikpdb 

From source
-----------

Git clone from the official repository then install with:

::

    python setup.py install
    
Or

::
    $ pip install git+git://github.com/cmorisse/ikpdb.git@v0.1.0  # tag
    or
    $ pip install git+git://github.com/cmorisse/ikpdb.git@newbranch  # or branch

   

Usage
=====

IKPdb is a remote debugger whose only interface is a TCP Socket.
Once launched, it waits for a TCP connection on a TCP Port.
A remote debugger GUI can then connect to the debugger to send it command and get results.


Launch parameters
-----------------

Adress, port, script to debug, logging verbosity
TO DO complete


IKPdb protocol description
==========================

...

Next level title
----------------

bla
bla


Next level title
................

bla
bla




Package description
===================

This package contains only 1 file ikpdb.py which contains the whole debugger.



