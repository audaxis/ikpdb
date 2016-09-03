.. _ikpdb_protocol:

IKPdb Protocol
==============

IKPdb communicates with debugging clients by exchanging JSON messages over a 
TCP socket. All exchanges between the debugger and clients are managed by the
:py:class:`ikpdb.IKPdbConnectionHandler` class.

Protocol overview
-----------------

Here is a typical message flow between IKPdb and a client.

+------------------------+------------+----------------------------+
| Client                 |            |               IKPdb        |
+========================+============+============================+
| connects                            |                            |
+------------------------+------------+----------------------------+
|                                     | sends "welcome" message    |
+------------------------+------------+----------------------------+
| sends "setBreakpoint"  |                                         |
| message                |                                         |
+------------------------+------------+----------------------------+
| sends "runScript"      |                                         |
| message                |                                         |
+------------------------+------------+----------------------------+
|                                     | sends "programBreak"       |
|                                     | message                    |
+------------------------+------------+----------------------------+
| sends "setVariable"    |                                         |
| message                |                                         |
+------------------------+------------+----------------------------+
| sends "resume"         |                                         |
| message                |                                         |
+------------------------+------------+----------------------------+
|                                     | sends "programEnd" message |
+------------------------+------------+----------------------------+

Protocol description
--------------------

As an overview, IKPdb waits for **"command"** messages from clients and reply 
with **"response"** messages. IKPdb also sends **"event"** messages to client when 
debugged program reach a breakpoint or raise an exception.

Packet description
__________________

IKpdb and remote client exchanges messages having this structure:
    
    ``"length={{integer length of json_dump_of_message_body hereafter}}{{MAGIC_CODE}}{{json_dump_of_message_body}}"``

Take a look at :class:`ikpdb.IKPdbConnectionHandler` for details.

Please note that json_dump_of_message will soon be encoded.

Format of "command" messages sent by clients to IKPdb
_____________________________________________________

Messages received by IKPdb follow this structure:

.. code-block:: python

    {
        "_id": an_integer, # Unique identifier of the command, used to link commands and replies
        "command": command_name_as_str,  # eg. "runScript"
        "args": { 
            # a dict containing command's specific parameters 
        }
    }


Format of "reply" messages sent by IKPdb
________________________________________

Replies sent by IKPdb follow this structure:

.. code-block:: python

    {
        "_id": an_integer,  # _id of the origin command
        "command": command_name_as_str,  # origin command eg. "runScript"
        "result": {
            # Updated status of debugged program when the reply is sent
            "executionStatus": "running" #  or "stopped" or "terminated",
            
        }
        "commandExecStatus": "ok" or "error",  # depends on command execution success
        "info_messages": a_list_of_str,
        "warning_messages": another_list_of_str,
        "error_messages": yet_another_list_of_str,
    }

Format of "event" messages sent by IKPdb
________________________________________

Event messages sent by IKPdb follow this structure:

.. code-block:: python

    {
        "_id": an_integer,  # _id of the origin command
        "command": "{{command_name}}",
        "result": {}
        "commandExecStatus": "ok"  # always "ok" for event
        "info_messages": a_list_of_str,
        "warning_messages": another_list_of_str,
        "error_messages": yet_another_list_of_str,
    	"frames": [
    	    # Complete stack dump, see below.
    	],
    	"exception": {
    	    "type": exception_name_as_str,
    	    "info": exception_message_as_str
    	}
    }

For detail about frames and exception, take a look at :func:`~ikpdb.IKPdb.dump_frames`.

Messages string
_______________

IKPdp sends 3 king of messages to clients:  *warning*, *info* and *error*. 
Usage of these messages is left to the client implementation. For example in Cloud9:

* *info_messages* are displayed using console.log()
* *warning_messages* are displayed using notification bubbles
* *error_messages* are displayed in a red banner at the top of the window (using cloud9 showError API)

Debugged program execution status
_________________________________

All messages related to debugged program execution modifications add an 
*executionStatus* key in the result dict.

Possible values for *executionStatus* are:

* "stopped" (break or exception)
* "running"
* "terminated" 

IKPdb command list summary
--------------------------

Here is the list (in no particular order) of commands supported by IKPdb.
For detailed parameters description, please look have a look at IKPdb code
especially :func:`~ikpdb.IKPdb.command_loop` and :py:func:`ikpdb.main`.

In next table *Way* is expressed from IKPdb point of view. "in" means received 
by IKPdb (and sent by client).

+-------------------------+-----+-------------------------------------+-------------------+
| Command                 | Way | Description                         | Update            |
|                         |     |                                     | executionStatus?  |
+=========================+=====+=====================================+===================+
| "changeBreakpointState" | in  | Ask IKPdb to modify an existing     |                   |
|                         |     | breakpoint                          |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "clearBreakpoint"       | in  | Ask IKPdb to delete a breakpoint.   |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "evaluate"              | in  | Evaluate an expression or statement | Yes               |
|                         |     | in the context of debugged program  |                   |
|                         |     | and return result.                  |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "getBreakpoints"        | in  | Ask IKPdb to return a list of all   |                   |
|                         |     | defined breakpoints                 |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "getProperties"         | in  | Ask IKPdb to the properties or      | Yes               |
|                         |     | members of a compound variable.     |                   |
|                         |     | This allows client to lay load huge |                   |
|                         |     | variables or dict                   |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "programBreak"          | out | Sent by IKPdb when debugged program | Yes: "stoped"     |
|                         |     | has reached a breakpoint or raised  |                   |
|                         |     | an exception.                       |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "programEnd"            | out | Sent when debugged program exited   | Yes: "Terminated" |
|                         |     | contains the exit code if any.      |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "resume"                | in  | Sent by the client to resume        | Yes: "Running"    |
|                         |     | execution of a paused debugged      |                   |
|                         |     | program.                            |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "runScript"             | in  | Start execution of debugged program.| Yes               |
+-------------------------+-----+-------------------------------------+-------------------+
| "setVariable"           | in  | Ask IKPdb to modify value of a stack| Yes               |
|                         |     | frame variable.                     |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "stepOver"              | in  |                                     | Yes: "Running"    |
+-------------------------+-----+-------------------------------------+-------------------+
| "setBreakpoints"        | in  | Ask IKPdb to set a breakpoint.      |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "stepInto"              | in  |                                     | Yes: "Running"    |
+-------------------------+-----+-------------------------------------+-------------------+
| "stepOut"               | in  |                                     | Yes: "Running"    |
+-------------------------+-----+-------------------------------------+-------------------+
| "suspend"               | in  | Sent by the client, if user         | Yes: "Running"    |
|                         |     | requests to pause debugged program. |                   |
+-------------------------+-----+-------------------------------------+-------------------+
| "welcome"               | out | A welcome message with IKPDb        |                   |
|                         |     | version sent at client connection.  |                   |
+-------------------------+-----+-------------------------------------+-------------------+

