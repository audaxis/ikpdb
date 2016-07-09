#! /usr/bin/env python
# coding: utf8
import socket
import sys
import os
import bdb
import atexit
import signal
import json
import logging
import traceback
import types
import inspect
import threading
import types, ctypes

IKPDB_AUTO_SET_TRACE = True
DEBUGGER_ADDRESS = 'localhost'
DEBUGGER_PORT = 15470

ikpdb = None

# Configure logging
_logger = logging.getLogger("IKPdb")
_logger.setLevel(logging.DEBUG)

_ch_logger = logging.getLogger("IKPdb-Conn")
_ch_logger.setLevel(logging.INFO)

_bp_logger = logging.getLogger("IKPdb-Break")
_bp_logger.setLevel(logging.DEBUG)

_exp_logger = logging.getLogger("IKPdb-Expr")
_exp_logger.setLevel(logging.DEBUG)

_exec_logger = logging.getLogger("IKPdb-Exec")
_exec_logger.setLevel(logging.DEBUG)

# to prevent console handler to be added at each import
# See: http://stackoverflow.com/questions/6729268/python-logging-messages-appearing-twice
if False and not _logger.handlers:
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(name)s] %(asctime)s - %(levelname)s - %(message)s")  # create formatter
    console_handler.setFormatter(formatter)  # add formatter to ch
    _logger.addHandler(console_handler)
    _ch_logger.addHandler(console_handler)
    _bp_logger.addHandler(console_handler)
    _exp_logger.addHandler(console_handler)
    _exec_logger.addHandler(console_handler)
##
# Message Handler
#
class IKPdbConnectionError(Exception):
    pass


class IKPdbConnectionHandler():
    """ Manages a connection with a remote client. 
    IKpdb and remote client communicate with messages having this structure:
    length={{length - as integer - of json_message_body below}}{{MAGIC_CODE}}{{message_body_as_json_dump}}
    
    Where {{...}} must be replaced by real content.
    """
    MAGIC_CODE = "LLADpcdtbdpac"
    MESSAGE_TEMPLATE = "length=%s"+MAGIC_CODE+"%s"
    
    SOCKET_BUFFER_SIZE = 4096  # Maximum size of a packet received from client
    MSG_WAITALL = 0x100  # From Linux sys/socket.h
    
    
    def __init__(self, connection):
        self._connection = connection
        self._connection_lock = threading.Lock()
        self._received_data = ''

    def encode(self, obj):
        json_obj = json.dumps(obj)
        return self.MESSAGE_TEMPLATE % (len(json_obj), json_obj,)

    def decode(self, message):
        json_obj = message.split(self.MAGIC_CODE)[1]
        obj = json.loads(json_obj)
        return obj
        
    def log_sent(self, msg):
        _ch_logger.debug("Sent %s bytes >>>%s<<<", len(msg), msg)
        
    def log_received(self, msg):
        _ch_logger.debug("Received %s bytes >>>%s<<<", len(msg), msg)
    
    def send(self, command, _id=None, result={}, command_exec_status="ok", frames=[], messages=[], warnings=[]):
        """Build a message from passed dict object and send it to debugger"""
        with self._connection_lock:
            msg = self.encode({
                '_id': _id,
                'command': command,
                'result': result,
                'commandExecStatus': command_exec_status,
                'frames': frames,
                'messages': messages,
                'warnings': warnings
            })
            if self._connection:
                send_bytes_count = self._connection.sendall(msg)
                self.log_sent(msg)
                return send_bytes_count
            raise IKPdbConnectionError("Connection lost!")

    def reply(self, obj, result, command_exec_status='ok', messages=[], warnings=[]):
        """Build a response from a previsoulsy received command msg, send it
           and return number of sent bytes."""
        with self._connection_lock:
            # TODO: add a parameter to remove args from messags ?
            if True:
                del obj['args']
            obj['result'] = result
            obj['commandExecStatus'] = command_exec_status,
            obj['messages'] = messages
            obj['warnings'] = warnings
            msg = self.encode(obj)
            send_bytes_count = self._connection.sendall(msg)
            self.log_sent(msg)
            return send_bytes_count

    def receive(self):
        """Waits for a message from the debugger and returns it as a dict"""
        with self._connection_lock:
            # TODO: Manages message bigger than SOCKET_BUFFER_SIZE
            # TODO: ensure we always have a command before leaving receive()
            
            while True:
                _ch_logger.debug("Enter socket.recv(%s) with self._received_data = %s)", 
                                 self.SOCKET_BUFFER_SIZE, 
                                 self._received_data)
                data = self._connection.recv(self.SOCKET_BUFFER_SIZE)
                _ch_logger.debug("Socket.recv(%s) => %s", self.SOCKET_BUFFER_SIZE, data)
                self._received_data += data
                    
                # have we received a MAGIC_CODE
                try:
                    magic_code_idx = self._received_data.index(self.MAGIC_CODE)
                except ValueError:
                    continue
                
                # Have we received a length=
                try:
                    length_idx = self._received_data.index('length=')
                except ValueError:
                    continue
                
                # extract length content from received data
                json_length = int(self._received_data[length_idx + 7:magic_code_idx])
                message_length = magic_code_idx + len(self.MAGIC_CODE) + json_length
                if message_length <= len(self._received_data):
                    full_message = self._received_data[:message_length]
                    self._received_data = self._received_data[message_length:]
                    if len(self._received_data) > 0:
                        self.SOCKET_BUFFER_SIZE = 0
                    else:
                        self.SOCKET_BUFFER_SIZE = 4096
                    break
                else:
                    self.SOCKET_BUFFER_SIZE = message_length - len(self._received_data)

            self.log_received(full_message)
            obj = self.decode(full_message)
            return obj
        

##
# Debugger


class IKPdbException(Exception):
    pass

def IKPdbRepr(t):
    """returns a type reprsentation suitable for debugger gui
    :param t: a thing
    """
    if hasattr(t, '__class__'):
        return t.__class__.__name__
    t_type = type(t)
    return str(t_type).split(' ')[1][1:-2]
        
    
class IKPdb(bdb.Bdb):
    
    def __init__(self, skip=None, launch_working_directory=None):
        bdb.Bdb.__init__(self, skip=skip)
        self.mainpyfile = ''
        self._wait_for_mainpyfile = 0
        self._active_breakpoint_lock = threading.Lock()
        self.curframe = None
        self.stopframe = None
        self.botframe = None
        self._CWD = launch_working_directory or os.getcwd()

    def lookup_module(self, filename):
        """Helper function for break/clear parsing -- may be overridden.
        lookup_module() translates (possibly incomplete) file or module name
        into an absolute file name.
        """
        _logger.debug("lookup_module(%s) with os.getcwd()=>%s", filename, os.getcwd())
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
            
        # Can we find file relatively to launch script
        f = os.path.join(sys.path[0], filename)  
        if  os.path.exists(f) and self.canonic(f) == self.mainpyfile:
            return f
            
        # Can we find the file relatively to launch CWD (useful with buildout)
        f = os.path.join(self._CWD, filename)  
        if  os.path.exists(f):
            return f

        # Try as an absolute path after adding .py extension 
        root, ext = os.path.splitext(filename)
        if ext == '':
            filename = filename + '.py'
        if os.path.isabs(filename):
            return filename
        
        # Cand we find the file in system path
        for dirname in sys.path:
            while os.path.islink(dirname):
                dirname = os.readlink(dirname)
            fullname = os.path.join(dirname, filename)
            if os.path.exists(fullname):
                return fullname
        return None

    def forget(self):
        """resets debugging state variables."""
        self.lineno = None
        self.stack = []
        self.curindex = 0  # current stack index
        self.curframe = None

    def setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]
        # The f_locals dictionary is updated from the actual frame
        # locals whenever the .f_locals accessor is called, so we
        # cache it here to ensure that modifications are not overwritten.
        self.curframe_locals = self.curframe.f_locals

    def remove_setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]
        # The f_locals dictionary is updated from the actual frame
        # locals whenever the .f_locals accessor is called, so we
        # cache it here to ensure that modifications are not overwritten.
        self.curframe_locals = self.curframe.f_locals

    def object_properties_count(self, o):
        """ returns the number of user browsable properties of an object. """
        if type(o) in (types.DictType, types.ListType, types.TupleType,):
            return len(o)
        else:
            count = len([o for o in dir(o) 
                            if not o.startswith('__') and not hasattr(o, '__call__')])
            return count

    def extract_object_properties(self, o):
        """ extracts all properties from an object (eg. f_locals, f_globals, 
            user dict, instance ...) and returns them as an array of variables
        """
        
        var_list = []
        if type(o) == types.DictType:
            a_var_name = None
            a_var_value = None
            for a_var_name in o:
                a_var_value = o[a_var_name]
                var_list.append({
                    'id': id(a_var_value),
                    'name': a_var_name,
                    'type': IKPdbRepr(a_var_value),
                    'value': repr(a_var_value),
                    'children_count': self.object_properties_count(a_var_value)
                })
                
        elif type(o) in (types.ListType, types.TupleType,):
            a_var_name = None
            a_var_value = None
            for a_var_name, a_var_value in enumerate(o):
                var_list.append({
                    'id': id(a_var_value),
                    'name': a_var_name,
                    'type': IKPdbRepr(a_var_value),
                    'value': repr(a_var_value),
                    'children_count': self.object_properties_count(a_var_value)
                })

        else:
            a_var_name = None
            a_var_value = None
            for a_var_name in [member for member in dir(o) if not member.startswith('__')]:
                a_var_value = getattr(o, a_var_name)
                if not hasattr(a_var_value, '__call__'):
                    var_list.append({
                        'id': id(a_var_value),
                        'name': a_var_name,
                        'type': IKPdbRepr(a_var_value),
                        'value': repr(a_var_value),
                        'children_count': self.object_properties_count(a_var_value)
                    })
        return var_list    
            

    def dump_frames(self, frame):
        """Dumps frames chain in a representation suitable for serialization 
           and remote (debugger) client usage.
        """
        current_tread = threading.currentThread()
        frames = []
        frame_browser = frame
        
        # Browse the frame chain as far as we can
        while hasattr(frame_browser, 'f_back') and frame_browser.f_back != self.botframe:
            _logger.debug("Frame analysis:")
            _logger.debug("    frame = %s", frame_browser)
            _logger.debug("    frame.f_code = %s", frame_browser.f_code)
            _logger.debug("    frame.f_back = %s", frame_browser.f_back)
            _logger.debug("    self.botframe = %s", self.botframe)
            _logger.debug("    frame.f_lineno = %s", frame_browser.f_lineno)  # Warning 0 based
            _logger.debug("    frame.f_code.co_filename = %s", frame_browser.f_code.co_filename)
            _logger.debug("    frame.f_locals = %s", ",".join([l_key for l_key in frame_browser.f_locals]))
            _logger.debug("    frame.g_globals = %s", ",".join([g_key for g_key in frame_browser.f_globals if g_key not in frame_browser.f_locals]))

            # Update local variables (User can use watch expressions for globals)
            locals_vars_list = self.extract_object_properties(frame_browser.f_locals)

            frame_name = "%s(), thread='%s'" % (frame_browser.f_code.co_name, current_tread.name,)
            remote_frame = {
                'id': id(frame_browser),
                'name': frame_name,
                'line_number': frame_browser.f_lineno,  # Warning 0 based
                'file_path': frame_browser.f_code.co_filename, 
                'thread': id(current_tread),
                'f_locals': locals_vars_list
            }
            frames.append(remote_frame)
            frame_browser = frame_browser.f_back
        return frames        


    def evaluate(self, frame_id, expression, global_context=False, disable_break=False):
        """ evaluate given expression in the givent frame 
            or globally and return a tuple of value and type as str"""
        if disable_break:
            _exp_logger.warning("Unsupported value (True) for disable_break ignored in evaluate()")
        
        if frame_id and not global_context:
            eval_frame = ctypes.cast(frame_id, ctypes.py_object).value
            global_vars = eval_frame.f_globals
            local_vars = eval_frame.f_locals
        else:
            global_vars = None
            local_vars = None
        try:
            result = eval(expression, 
                          global_vars,
                          local_vars)
            result_type = IKPdbRepr(result)
            result_value = repr(result)
            # TODO: support statement execution
            #try: ...
            #except SyntaxError:
            #    exec expression in global_vars, local_vars
            #    ... extract result from stdout    
        except:
            t, result = sys.exc_info()[:2]
            if isinstance(t, str):
                result_type = t
            else: 
                result_type = t.__name__
            result_value = None
            result_type = "%s: %s" % (result_type, result,)
        _exp_logger.debug("evaluate(%s) => value = %s:%s | %s", expression, result_value, result_type, result)
        return result_value, result_type

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        _logger.debug("entering user_call() with:\n"
                      "  => _wait_for_mainpyfile=%s\n"
                      "  => threadName=%s\n"
                      "  => frame=%s\n"
                      "  => frame.f_code.co_filename=%s\n"
                      "  => frame.f_lineno=%s\n"
                      "  => self.mainpyfile=%s\n"
                      "  => self.break_here()=%s\n"
                      "  => self.stop_here()=%s\n",
                      self._wait_for_mainpyfile,
                      threading.currentThread().name,
                      frame,
                      frame.f_code.co_filename,
                      frame.f_lineno,
                      self.mainpyfile,
                      self.break_here(frame),
                      self.stop_here(frame))

        if self._wait_for_mainpyfile:
            return  # processing is done in user_line()
        
        if self.stop_here(frame):
            return  # processing is done in user_line()
        # TODO: What can we do with this function in the context of gui debugging

    def stop_here(self, frame):
        """ Called by dispatch function to check wether debugger must stop at
            this frame.
        """
        # (CT) stopframe may now also be None, see dispatch_call.
        # (CT) the former test for None is therefore removed from here.
        if self.skip and self.is_skipped_module(frame.f_globals.get('__name__')):
            return False
        if frame is self.stopframe:
            if self.stoplineno == -1:
                return False
            return frame.f_lineno >= self.stoplineno
            
        if not self.stopframe:
            return True
        return False


    def user_line(self, frame, post_mortem=True):
        """This function is called when debugger has decided that we must
        stop or break at this frame."""
        
        _logger.debug("Entering user_line() with:\n"
                      "  => _wait_for_mainpyfile=%s\n"
                      "  => threadName=%s\n"
                      "  => frame=%s\n"
                      "  => frame.f_code.co_filename=%s\n"
                      "  => frame.f_lineno=%s\n"
                      "  => self.mainpyfile=%s\n"
                      "  => self.break_here()=%s\n"
                      "  => self.stop_here()=%s\n\n",
                      self._wait_for_mainpyfile,
                      threading.currentThread().name,
                      frame,
                      frame.f_code.co_filename,
                      frame.f_lineno,
                      self.mainpyfile,
                      self.break_here(frame),
                      self.stop_here(frame))
                      
        # By default, Bdb will trace each call until user use the 'continue' command
        # This behaviour allow user to take control over debugging at the 
        # beginning of the session.
        # In IKPdb this behaviour is not needed as user can use the GUI to 
        # set breakpoints before launch.
        # So we simulate the continue command at the first debugger stop
        # which is just before before executing the string 
        # containing the exec statement defined in ::run()
        if (self._wait_for_mainpyfile and frame.f_code.co_filename=='<string>'
            and frame.f_lineno==1):
            self._wait_for_mainpyfile = 0
            self.set_continue()  
            return

        # acquire breakpoint Lock before sending break command to Cloud9
        self._active_breakpoint_lock.acquire()
        frames = self.dump_frames(frame)
        remote_client.send('programBreak', frames=frames)
        self.setup(frame, None)  # Reconfigure frame, stack and locals
        self.command_loop(post_mortem=post_mortem)
        

    def get_breakpoint_number(self, filename, line):
        """lookup breakpoint by filename and line number and returns number 
            its' number"""
        cfile = self.lookup_module(filename)
        for bp in bdb.Breakpoint.bpbynumber:
            if bp and bp.file == cfile and bp.line == line:
                return bp.number
        return 0

    def change_breakpoint_state(self, bp_number, enabled, condition=None):
        """ enable or disable a breakpoint identified by it's 
            breakpoint number.
            :returns: None or an error message (string)
        """
        if not (0 <= bp_number < len(bdb.Breakpoint.bpbynumber)):
            return "Found no breakpoint numbered %s" % bp_number
        bp = bdb.Breakpoint.bpbynumber[bp_number]
        _bp_logger.debug("bp #%s = %s", bp_number, bp)
        if bp:
            if enabled:
                bp.enable()
            else:
                bp.disable()
            # manage conditional breakpoints
            if condition:
                bp.cond = condition
            
        return None

    def run(self, cmd, globals=None, locals=None):
        """ overloaded to debug multithreaded programm"""
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        threading.settrace(self.trace_dispatch)  # <== here it is
        sys.settrace(self.trace_dispatch)
        if not isinstance(cmd, types.CodeType):
            cmd = cmd+'\n'
        try:
            exec cmd in globals, locals
        except bdb.BdbQuit:
            pass
        finally:
            self.quitting = 1
            sys.settrace(None)

    def _runscript(self, filename):
        # The script has to run in __main__ namespace (or imports from
        # __main__ will break).
        # So we clear up the __main__ and set several special variables
        # (this gets rid of pdb's globals and cleans old variables on start).
        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update({"__name__"    : "__main__",
                                  "__file__"    : filename,
                                  "__builtins__": __builtins__,
                                 })

        # When bdb sets tracing, a number of call and line events happens
        # BEFORE debugger even reaches user's code (and the exact sequence of
        # events depends on python version). So we take special measures to
        # avoid stopping before we reach the main script (see user_line and
        # user_call for details).
        self._wait_for_mainpyfile = 1
        self.mainpyfile = self.canonic(filename)
        self._user_requested_quit = 0
        statement = 'execfile(%r)' % filename
        self.run(statement)

    def command_loop(self, post_mortem=False):
        """ return 1 to exit command_loop and resume execution 
        """
        while True:
            obj = remote_client.receive()
            command = obj["command"]  # TODO: ensure we always have a command if receive returns
            args = obj['args']
        
            if command == 'getBreakpoints':
                _bp_logger.debug("getBreakpoints(%s)", args)
                breakpoint_list = self.get_all_breaks()
                # TODO: Derive it from object list
                result = []  
                # TODO: Warning IKPDb line numbers are 1 based vs c9 0 based
                remote_client.reply(obj, result)
                
            elif command == "setBreakpoint":
                # TODO: manage conditionnals
                # set_break(filename, lineno, temporary=0, cond=None, funcname=None)
                # Set a new breakpoint. If the lineno line doesn't exist for the
                # filename passed as argument, return an error message. €
                # The filename should be in canonical form, as described in the 
                # canonic() method.
                file_name = args['file_name']
                line_number = args['line_number']
                condition = args.get('condition', '')
                enabled = args.get('enabled', '')
                _bp_logger.debug("setBreakpoint(file_name=%s, line_number=%s,"
                                 " condition=%s, enabled=%s) with CWD=%s",
                                 file_name,
                                 line_number,
                                 condition,
                                 enabled,
                                 os.getcwd())

                r = self.set_break(file_name, 
                                   line_number, 
                                   cond=condition)
                messages = []
                if r:
                    _logger.error("setBreakpoint error: %s", r)
                    messages = [r]
                    result = {}
                    command_exec_status = 'error'
                else:
                    bp_number = self.get_breakpoint_number(args['file_name'], args['line_number'])
                    assert bp_number, "Internal error: uncaught setBreakpoint failure"
                    result = {'breakpoint_number': bp_number}
                    command_exec_status = 'ok'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    messages=messages)
            
            elif command == "changeBreakpointState":
                # Allows to:
                #  - activate or deactivate breakpoint 
                #  - set or remove condition
                # set_break(filename, lineno, temporary=0, cond=None, funcname=None)
                bp_number = args.get('breakpoint_number', None)
                enabled = args.get('enabled', False)
                condition = args.get('condition', '')
                
                _bp_logger.debug("changeBreakpointState(%s)", args)
                if bp_number:
                    r = self.change_breakpoint_state(bp_number, 
                                                     enabled, condition=condition)
                    result = {}
                    messages = []
                    if r:
                        msg = "changeBreakpointState error: \"%s\"" % r
                        _logger.error(msg)
                        messages = [msg]
                        command_exec_status = 'error'
                    else:
                        command_exec_status = 'ok'
                else:
                    result = {}
                    msg = "changeBreakpointState error: breakpointNumber parameter is required."
                    _logger.error(msg)
                    messages = [msg]
                    command_exec_status = 'error'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    messages=messages)
                
            
            elif command == "clearBreakpoint":
                # set_break(filename, lineno, temporary=0, cond=None, funcname=None)
                # Set a new breakpoint. If the lineno line doesn't exist for the
                # filename passed as argument, return an error message. €
                # The filename should be in canonical form, as described in the 
                # canonic() method.
                _bp_logger.debug("clearBreakpoint(%s)", args)
                r = self.clear_break(args['file_name'], args['line_number'])
                result = {}
                messages = []
                if r:
                    _logger.error("clearBreakpoint error: %s", r)
                    messages = [r]
                    command_exec_status = 'error'
                else:
                    command_exec_status = 'ok'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    messages=messages)
            
            elif command == "getProperties":
                messages = []
                po_value = ctypes.cast(args['id'], ctypes.py_object).value
                result={'properties': self.extract_object_properties(po_value) or []}
                command_exec_status = 'ok'
                _exp_logger.debug("getProperties(%s) => %s", args, result)
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    messages=messages)

            elif command == "setVariable":
                _exp_logger.debug("setVariable(%s)", args)
                messages = []
                result = {}
                sv_frame = ctypes.cast(args['frame'], ctypes.py_object).value
                try:
                    if args['name'] in sv_frame.f_locals:
                        sv_frame.f_locals[args['name']] = eval(str(args['value']))
                    else:
                        sv_frame.f_globals[args['name']] = eval(str(args['value']))
                    command_exec_status = 'ok'
                except:
                    command_exec_status = 'error'
                    msg = "setVariable error: failed to let %s to var with id: %s" % (args['id'], args['value'],)
                    messages = [msg]
                    _logger.error(msg)
                command_exec_status = 'ok'
                remote_client.reply(obj, 
                                    result, 
                                    command_exec_status=command_exec_status,
                                    messages=messages)

            elif command == 'runScript':
                _exec_logger.debug("runScript(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self._runscript(self.mainpyfile)
                return 1 
                
            elif command == 'resume':
                _exec_logger.debug("resume(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_continue()
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepOver':  # <=> Pdb n(ext)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_next(self.curframe)
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepInto':  # <=> Pdb s(tep)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_step()
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepOut':  # <=> Pdb r(eturn)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_return(self.curframe)
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'evaluate':  # <=> Pdb p command
                _exp_logger.debug("evaluate(%s)", args)
                value, result_type = self.evaluate(args['frame'], args['expression'], args['global'], disable_break=args['disableBreak'])
                if value:
                    remote_client.reply(obj,
                                        {'value': value, 'type': result_type})  # result
                else:
                    remote_client.reply(obj,
                                        {},
                                        command_exec_status="error",
                                        messages=[result_type])

            else:
                _logger.critical("Unsupported command '%s'.", command)
                return

        
def set_trace():
    """ breaks on the line that invoked this function. 
    """
    global ikpdb
    if not ikpdb:
        raise Exception("IKPdb must be launched before calling ikpd.set_trace().")
    ikpdb.set_trace(sys._getframe().f_back)

def post_mortem(trace_back):
    """ given a trace back, post_mortem() will break on it. This is useful for 
        integration with system that manages Exceptions to allow them to 
        set up a developer mode where Unhandled exceptions a returned to 
        the developer.
    """
    global ikpdb
    if not ikpdb:
        raise Exception("IKPdb must be launched before calling ikpd.post_mortem().")
    pm_traceback = trace_back
    while pm_traceback.tb_next:
        pm_traceback = pm_traceback.tb_next      
    ikpdb.setup(None, pm_traceback)
    ikpdb.user_line(pm_traceback.tb_frame)
    ikpdb.forget()
    _logger.info("Post mortem debugger finished.")





##
# Signal Handler to properly close socket connection
#
SIGNALS_DICT = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                if v.startswith('SIG') and not v.startswith('SIG_'))

def close_connection():
    try:
        if client_connection:
            _logger.debug("Closing open connection...")
            # Cf. https://docs.python.org/2/howto/sockets.html#disconnecting
            client_connection.shutdown(socket.SHUT_RDWR)
            client_connection.close()
            _logger.debug("Connection closed...")
    except NameError:
        pass
    
# On SIGINT, SIGTERM shutdown socket and close connection
# (SIGKILL cannot be caught)
def signal_handler(signal, frame):
    print "%s received" % SIGNALS_DICT[signal]
    close_connection()
    # Cf. http://tldp.org/LDP/abs/html/exitcodes.html
    sys.exit(128+signal)
    

##
# main
#
def main():
    _logger.debug("main() with sys.argv=%s, CWD='%s'", sys.argv, os.getcwd())
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print "usage: ikpdb.py scriptfile [arg] ..."
        sys.exit(2)

    mainpyfile =  sys.argv[1]     # Get script filename
    if not os.path.exists(mainpyfile):
        print 'Error:', mainpyfile, 'does not exist'
        sys.exit(1)

    # sets up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    del sys.argv[0]         # Hide "ikpdb.py" from argument list

    # Replace ikpdb's dir with script's dir in front of module search path.
    sys.path[0] = os.path.dirname(mainpyfile)

    # Note on saving/restoring sys.argv: it's a good idea when sys.argv was
    # modified by the script being debugged. It's a bad idea when it was
    # changed by the user from the command line.
    
    # Initialize IKPdb listen socket
    debug_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # http://stackoverflow.com/questions/4465959/python-errno-98-address-already-in-use?lq=1
    debug_socket.bind((DEBUGGER_ADDRESS,DEBUGGER_PORT,))

    _logger.info('Listening on %s:%s', DEBUGGER_ADDRESS, DEBUGGER_PORT)
    debug_socket.listen(1)  # 1 connection max
    
    # Wait for a connection
    global client_connection
    client_connection, client_address = debug_socket.accept()
    _logger.debug("Connected with %s:%s", client_address[0], client_address[1])  
    # TODO: Redirect sdtout and stderr to a cloud9 windows ??

    # setup remote client connection
    global remote_client
    remote_client = IKPdbConnectionHandler(client_connection)  
    
    global ikpdb
    ikpdb = IKPdb()

    # Send welcome message
    # TODO: Add a command line parameter to disable ( --welcome-message=0 or 1 )
    if True:  
        remote_client.send("start", messages=["Welcome", "IKPdb", "version=0.1"])

    # Launch debugging
    try:
        ikpdb.mainpyfile = mainpyfile
        ikpdb.command_loop()
        remote_client.send('programEnd', 
                           result={'exit_code': None, 
                                   'executionStatus': 'terminated'}, 
                           command_exec_status="ok")
        _logger.info("Program terminated with no returned value.")  # TODO: send this to the debuger gui
        sys.exit(0)

    except SystemExit:
        # In most cases SystemExit does not warrant a post-mortem session.
        exit_code = sys.exc_info()[1].code
        _logger.info("Program exited with exit code: %s.", exit_code)

        # Connection may have been closed
        try:
            remote_client.send('programEnd', 
                               result={'exit_code': exit_code, 
                                       'executionStatus': 'terminated'}, 
                               command_exec_status="ok")
        except:
            pass
        close_connection()
        sys.exit(exit_code)
        
    except SyntaxError:
        # Python detected a syntax error while running or launching program 
        # to debug.
        traceback.print_exc()
        close_connection()
        sys.exit(1)  # 1 = General error
        
    except:
        traceback.print_exc()
        _logger.info("Uncaught exception. Entering post mortem debugging")
        pm_traceback = sys.exc_info()[2]
        while pm_traceback.tb_next:
            pm_traceback = pm_traceback.tb_next      
        ikpdb.setup(None, pm_traceback)
        ikpdb.user_line(pm_traceback.tb_frame)
        ikpdb.forget()
        try:
            remote_client.send('programEnd', 
                               result={'exit_code': None, 
                                       'executionStatus': 'terminated'}, 
                               command_exec_status="ok")
        except:
            pass
        
        _logger.info("Post mortem debugger finished.")
        close_connection()
        sys.exit(1)


# When invoked as main program, invoke the debugger on a script
if __name__ == '__main__':
    import ikpdb
    ikpdb.main()
