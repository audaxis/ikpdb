API
===

Here is the complete documentation for the ikpdb module.

IKPdb *"public"* API consists of 2 functions described in the 
:ref:`integration-api` paragraph of the :doc:`integration_guide`

IKPdb *"private"* API consists of:

* 4 classes:
    * :class:`ikpdb.IKPdbLogger` (logging system)
    * :class:`ikpdb.IKBreakpoint` (breakpoints manager)
    * :class:`ikpdb.IKPdbConnectionHandler` (protocol implementation)
    * :class:`ikpdb.IKPdb`: The debugger by itself
* 1 exception:
    * :class:`ikpdb.IKPdbQuit`
* 1 helper:
    * :func:`ikpdb.IKPdbRepr` returns a *repr* suitable for clients

and of course a :func:`ikpdb.main`

Classes
-------

.. autoclass:: ikpdb.IKPdbLogger
    :members:
.. autoclass:: ikpdb.IKBreakpoint
    :members:
.. autoclass:: ikpdb.IKPdbConnectionHandler
    :members:
.. autoclass:: ikpdb.IKPdb
    :members:

Exceptions
----------

.. autoexception:: ikpdb.IKPdbQuit

Helpers
-------

.. autofunction:: ikpdb.IKPdbRepr

Main
----

.. autofunction:: ikpdb.main

