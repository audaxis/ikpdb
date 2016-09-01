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

Features
--------

IKPdb supports:

* Debugging of multithreaded programs
* Conditional breakpoints
* Variables hot modifications
* :ref:`turbo-mode`

IKPdb has no integrated GUI ; it's only interface is a TCP protocol.

**IKPdb client GUI reference implementation is** `Cloud9 Online IDE <https://c9.io/?redirect=0>`_

IKPdb TCP protocol - based on JSON - is designed for easy integration with latest
generation of Javascript editor / IDE (eg. Visual Studio Code, Cloud9, Atom).

Please note that IKPdb supports only CPython 2.7, CPython 3 support is the next 
step.

.. _installation:

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

.. _getting-started:

Getting started
---------------

.. _getting-started-with-cloud9:

Getting started with Cloud9
___________________________

1. Create a Workspace using the Python template
2. Create a new file with a few statements and save it as "debug_me.py".

You can copy / paste this snippet.

.. code-block:: python

   #coding: utf-8
   print "I want to try Python debugging with IKPdb in Cloud9."
   print "I step over onto this line."

3. Set a breakpoint on the first line by clicking in the left margin until a 
red circle appears.

**Ignore the red check button on line 1 ; as it is relevant only for Django development.**

.. image:: index_pic1__py_snippet.png

4. Click on the Run button at the Top menu right-hand side.

.. image:: index_pic2__run_button.png

The debugger is now open on the breakpoint you defined at step 3.

.. image:: index_pic3__debugger_opened.png

Now you can:

* Play with the debugger
* Read the `Cloud9 debugging documentation <https://docs.c9.io/docs/debugging-your-code>`_ to discover all Cloud9 features related to debugging.
* Read :doc:`IKPdb User Guide for Cloud9 <cloud9_user_guide>` to get information about IKPdb and Python debugging.

.. _getting-started-without-cloud9:

Getting started without Cloud9
______________________________

IKPdb is a debug server you launch with:

.. code-block:: bash

   $ python -m ikpdb to_debug.py
   [IKPdb-g] 05:04:40,690467 - INFO - IKPdb 1.0.0-alpha - Inouk Python Debugger for CPython 2.7
   [IKPdb-g] 05:04:40,690937 - INFO - IKPdb listening on 127.0.0.1:15470
   
This command starts debugging of to_debug.py. IKPdb is listening for commands 
on localhost port 15470 (15470 is default port).

IKPdb has a --help command that shows all available options.

.. code-block:: bash

   $ python -m ikpdb --help

At that point you need an IKPdp client. For now, the only available client is the `Cloud9 Online IDE <https://c9.io/?redirect=0>`_.

But you can start hacking your own client. For that you can use this starting material:

* :doc:`protocol`
* `IKPdb Cloud9 client source code <https://github.com/cmorisse/c9.ide.run.debug.ikpdb>`_
* `IKPdb source code <https://github.com/cmorisse/ikpdb>`_


.. _source-files-mapping:

Source files mapping
--------------------

IKPdb exchanges file names with his debugger clients. When it sends a file name, IKPdb 
always uses full path. But some debuggers client sends relative paths 
(when setting breakpoints for example). In that case, IKPdb tries to resolve the
file's full path using it's *"working directory"* as a base folder. If it fails, 
IKPdb sends a "FileMappingError:".

IKPdb's working directory can be defined:

* Implicitly ; working directory is set to the debugged program's current directory.
* Explictly ; using the **--ikpdb-working-directory** command line parameter

To ask IKPdb to display it's working directory add a **--ikpdb-log=G** command 
line parameter in the runner.

Integration
-----------

You can get a huge productivity boost by integrating IKPdb with your software 
of the framework you use. Once integrated, the debugger will automaticaly opens
an gives you all information required to debug each time an exception occurs.

.. image:: index_pic4__demo_exception.png

Read the :doc:`integration_guide` here.

Source code
-----------

IKPdb is composed of these projects hosted on github:

* `IKPdb debugger <https://github.com/cmorisse/ikpdb>`_
* `IKPdb Cloud9 reference client <https://github.com/cmorisse/c9.ide.run.debug.ikpdb>`_

Developer's Guide
-----------------

The :doc:`developers_guide` describes how to modify the debugger or the 
IKPdb's client Cloud9 plugin.

Issues / Suggestions
--------------------

Please feel free to file an issue on the project's Github bug tracker if you:

* have found a bug
* have some idea about improvements or optimizations
* have some needs to build a new debugging client !

Dependencies
------------

IKPdb has no external dependencies (and we wish this to remain like that).

Other documentation content
---------------------------

.. toctree::
   :maxdepth: 2
   
   cloud9_user_guide
   integration_guide
   developers_guide
   protocol
   api
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

