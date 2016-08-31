A hackable CPython remote debugger designed for integration with the latest generation of Javascript editor / IDE (eg. Cloud9, Atom, VS Code)
=============================================================================================================================================


Features
--------

* Debugging of multithreaded programs
* Conditional breakpoints
* Variables hot modifications
* :ref:`turbo-mode`
* easy integration in frameworks

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

Cloud9 is our debugger reference implementation so first try with `Cloud9 <https://c9.io/>`_.

So head to `Cloud9 <https://c9.io/>`_ and create an account then:

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

.. image:: docs/index_pic1__py_snippet.png

4. Click on the Run button at the Top menu right-hand side.

.. image:: docs/index_pic2__run_button.png

The debugger is now open on the breakpoint you defined at step 3.

.. image:: docs/index_pic3__debugger_opened.png

Now you can:

* Play with the debugger
* Read the `Cloud9 debugging documentation <https://docs.c9.io/docs/debugging-your-code>`_ to discover all Cloud9 features related to debugging.
* Read `IKPdb documentation <https://ikpdb.readthedocs.io/>`_ to get information about IKPdb and Python debugging.

Documentation
-------------

https://ikpdb.readthedocs.io/


Requirements
------------

CPython 2.7


License
-------

``IKPdb`` is licensed under a FreeBSD License.
See :doc:`IKPdb licence<LICENCE>`

Source code
------------

Source code is available on github:

https://github.com/cmorisse/ikpdb