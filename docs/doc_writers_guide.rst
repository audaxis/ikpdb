Documentation Writer's Guide
----------------------------

The documentation is written using the `Sphinx Documentation Generator <http://www.sphinx-doc.org/>`_.

Refer to this site for information about the syntax and possibilities of Sphinx.


IKPdb's Installation
--------------------

The documentation is stored in the debugger repository, so you must install 
IKPdb's source code.

We suggests you follow the instructions in the § 
:ref:`install-ikpdb-source-code` of the :doc:`developers_guide`.

Once it's done, you can edit the files in the *doc* directory. 

Sphinx's Installation
--------------------

The instructions below are valid in a Cloud9 workspace.

.. code-block:: bash

   $ cd ~/workspace/ikpdb/docs
   $ sudo pip install Sphinx


Rebuild the documentation
-------------------------

In a Cloud9 Terminal,

.. code-block:: bash

   $ cd ~/workspace/ikpdb/docs
   $ make html

You must rebuild the documentation each time you make a modification, 
if you want to preview the result.
   
Review your changes
-------------------

To review your changes, you will use Python's embedded web server with the 
Cloud9 Preview system.

First rebuild the documentation as explained above.

Then open a Cloud9 Terminal,

.. code-block:: bash

   $ cd ~/workspace/ikpdb/docs/_build/html
   $ python -m SimpleHTTPServer $C9_PORT 
   Serving HTTP on 0.0.0.0 port 8080 ...

Now you can open the Preview windows using the **Preview / Preview Running Application** entry of the top menu.

Note that: if you do a *make clean*, you must relaunch SimpleHTTPServer on the 
newly created *_build* directory (as the previous one has been moved to 
the *"trash"*).

Commit your changes
-------------------

Just commit your modifications (with a clear commit message) then send us 
a *Pull Request*.

