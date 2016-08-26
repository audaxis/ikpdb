.. IKPdb documentation master file, created by
   sphinx-quickstart on Tue Aug 23 04:27:18 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _IKPdbGitHub: https://github.com/cmorisse/ikpdb
.. _IKPdbCloud9PluginGitHub: https://github.com/cmorisse/c9.ide.run.debug.ikpdb
.. _Cloud9GitHub: https://github.com/c9/core


Welcome to IKPdb's documentation!
=================================

A hackable CPython remote debugger designed for the Web.

Features:
---------

IKPdb supports:

* Debugging of multithreaded programs
* Conditional breakpoints
* Variables hot modifications

IKPdb has no integrated GUI ; it's only interface is a tcp protocol.

IKPdb client GUI reference implementation is `Cloud9 Online IDE <https://c9.io/?redirect=0>`_

IKPdb TCP protocol - based on JSON - is designed for easy integration with latest generation of 
Javascript editor / IDE (eg. Visual Studio Code, Cloud9, Atom).

Please note that IKPdb supports only CPython 2.7, CPython 3 support is the next 
step.

Installation
------------

.. code-block:: bash

   $ pip install ikpdb

Installation from sources
_________________________

Git clone from the official repository then install with one of these:

.. code-block:: bash

   # If you want a specific version
   $ pip install git+git://github.com/cmorisse/ikpdb.git@1.0.1  # 1.0.1 is a tag

   # If you want latest version from a branch
   $ pip install git+git://github.com/cmorisse/ikpdb.git@1.0.x  # 1.0.x is the branch name

Getting started
---------------

If you work with Cloud9, check these instructions: :doc:`IKPdb User Guide for Cloud9 <cloud9_user_guide>`.

Else, IKPdb is a debug server you launch with:

.. code-block:: bash

   $ python -m ikpdb to_debug.py
   [IKPdb-g] 05:04:40,690467 - INFO - IKPdb 1.0.0-alpha - Inouk Python Debugger for CPython 2.7
   [IKPdb-g] 05:04:40,690937 - INFO - IKPdb listening on 127.0.0.1:15470
   
This command starts debugging of to_debug.py. IKPdb is listening for commands 
on localhst port 15470 (15470 is default port).

IKPdb has a --help command that shows all available options.

.. code-block:: bash

   $ python -m ikpdb --help

At that point you need an IKPdp client. You can either take a look at the 
`Cloud9 Online IDE <https://c9.io/?redirect=0>`_ which is the reference client 
or start hacking your own client.

For that you can use this starting material:

* :doc:`protocol`
* `IKPdb Cloud9 client source code <https://github.com/cmorisse/c9.ide.run.debug.ikpdb>`_
* `IKPdb source code <https://github.com/cmorisse/ikpdb>`_

Integration
-----------

You can get a huge productivity boost by integrating IKPdb with your software 
of the framework you use.

Once integrated, the debugger will automaticaly open an gives you all information
requires to debug each time an exception occurs.

Read the :doc:`integration_guide` here.

Source code
-----------

IKPdb is composed of these projects hosted on github:

* `IKPdb debugger <https://github.com/cmorisse/ikpdb>`_
* `IKPdb Cloud9 reference client <https://github.com/cmorisse/c9.ide.run.debug.ikpdb>`_

Issues / Suggestions
--------------------

Please feel free to file an issue on the project's Github bug tracker if you:

* have found a bug
* have some idea about improvements or optimizations
* have some needs to build a new debugging client !

Dependencies
------------

IKPdb has no external dependencies and we wish this to remain like that.



Documentation contents:
-----------------------

.. toctree::
   :maxdepth: 2
   
   cloud9_user_guide
   integration_guide
   api
   protocol
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

