=====
IKPdb
=====

IKPdb is a python (CPython 2.7) debugger built to work with online IDE (eg. cloud9)

IKPdb supports only CPython 2.7 (for now).

IKPDb have a decent feature set:

* Basic Multithreading Support
* Variable inspection and hot modifications
* Conditional breakoints
* And of course, Step over, Step in, Step out

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

Post mortem Integration with Odoo
=====================

IKPdb can be integrated with Odoo to automaticaly open the debugger on 
the line that raised an unhandled exception.

For that, you must:
* modify parts/odoo/openerp/tools/debugger.py like that:

::
    # -*- coding: utf-8 -*-
    # Copyright: 2014 - OpenERP S.A. <http://openerp.com>
    import types

    def post_mortem(config, info):
        if config['debug_mode'] and isinstance(info[2], types.TracebackType):
            try:
                import pudb as pdb
            except ImportError:
                try:
                    import ipdb as pdb
                except ImportError:
                    try:
                        import ikpdb as pdb
                    except ImportError:
                        import pdb
            pdb.post_mortem(info[2])
            
* launch odoo with the --debug command line parameter
    

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



