A hackable CPython remote debugger designed for integration with the latest generation of Javascript editor / IDE (eg. Cloud9, Atom, VS Code)
=============================================================================================================================================


Features
--------

* Debugging of multithreaded programs
* Conditional breakpoints
* Variables hot modifications
* "Turbo mode"
* easy integration in frameworks

Installation
------------

.. code-block:: bash

   $ pip install ikpdb

Installation from sources
_________________________

Git clone from the official repository then install with one of these:

.. code-block:: bash

   $ pip install git+git://github.com/audaxis/ikpdb.git@1.0.x  # 1.0.x is the branch name


.. _getting-started:

Getting started
---------------

Cloud9 is our debugger client reference implementation so head 
to `Cloud9 <https://c9.io/>`_, create an account there then refer to the Getting
Started section of `IKPdb documentation <https://ikpdb.readthedocs.io/>`_.

Documentation
-------------

https://ikpdb.readthedocs.io/


Requirements
------------

CPython 2.7.

A C compiler (eg. python-dev Debian package, xcode tools on macOS).

License
-------

``IKPdb`` is licensed under the MIT License.
See the License paragraph in the documentation.

Source code
------------

Source code is available on github:

https://github.com/audaxis/ikpdb


Issues
------

Issues are managed using Github's Issues Tracker.

