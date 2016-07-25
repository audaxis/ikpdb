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
import argparse
import datetime
import cStringIO

# For now ikpdb is a singleton
ikpdb = None 

##
# logging
# IKPdb has it's own logging system distinct from python logging to
# avoid collision when debugging programs that reconfigure logging
# system wide.
#
# logging is organized in domains (which corresponds to loggers)
# identified by one letter.
# IKPdb logs on these domains:
# letter: domain
# - n,N: Network 
# - b,B: Breakpoints 
# - e,E: Expression evaluation
# - x,X: Execution 
# - f,F: Frame 
# - g,G: Global debugger
#
# Logging support the same notion of level as python logging.
# Logging is invoked using this syntax:
# _logger.{{domain}}_{{level}}(*args)
# eg: _logger.x_debug("error in %s", the_error)
#
class ANSIColors:
    MAGENTA = '\033[95m'    
    BLUE = '\033[94m'       # debug
    GREEN = '\033[92m'      # info
    YELLOW = '\033[93m'     # warning
    RED = '\033[91m'        # error
    BOLD = '\033[1m'        # critical
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

class IKPdbLoggerError(Exception):
    pass
    
class MetaIKPdbLogger(type):
    def __getattr__(cls, name):
        domain, level_name = name.split('_')
        level = IKPdbLogger.LEVELS.get(level_name, None)
        if domain not in IKPdbLogger.DOMAINS or not level:
            raise IKPdbLoggerError("'%s' is not valid logging domain and level combination !" % name)
            
        def wrapper(*args, **kwargs):
            return cls._log(domain, level, *args, **kwargs)
        return wrapper

class IKPdbLogger():
    __metaclass__ = MetaIKPdbLogger
    
    enabled = False
    TEMPLATES = [
        "\033[1m[IKPdb-%s]\033[0m %s - \033[94mNOLOG\033[0m - %s",    # nolog    0
        "\033[1m[IKPdb-%s]\033[0m %s - \033[94mDEBUG\033[0m - %s",    # debug    1
        "\033[1m[IKPdb-%s]\033[0m %s - \033[92mINFO\033[0m - %s",     # info     2
        "\033[1m[IKPdb-%s]\033[0m %s - \033[93mWARNING\033[0m - %s",  # warning  3
        "\033[1m[IKPdb-%s]\033[0m %s - \033[91mERROR\033[0m - %s",    # error    4
        "\033[1m[IKPdb-%s]\033[0m %s - \033[91mCRITICAL\033[0m - %s", # critical 5
    ]

    # Levels
    CRITICAL = 50
    ERROR = 40
    WARNING= 30
    INFO = 20
    DEBUG = 10
    NOLOG= 0

    # Levels by name
    LEVELS = {
        "critical": 50,
        "error": 40,
        "warning": 30,
        "info": 20, 
        "debug": 10,
        "nolog": 0,
    }

    # Domains and domain's level
    DOMAINS = {
        "n": 20,
        "b": 20,
        "e": 20,
        "x": 20,
        "f": 20,
        "p": 20,
        "g": 20
    }

    @classmethod
    def setup(cls, ikpdb_log_arg):
        """activates DEBUG logging level based on the --ikpdb-log command
           line argument.
           IKPDB_LOG is a string composed of a serie of letters which
           switch debug logging level on components of the debugger.
           Here are the letters and the component they activate DEBUG logging 
           level on:
            - n,N: Network 
            - b,B: Breakpoints 
            - e,E: Expression evaluation
            - x,X: Execution 
            - f,F: Frame 
            - p,P: Path and python path manipulation
            - g,G: Global debugger
           by default logging is disabled for all components. A value in 
           --ikpdb-log arg activates INFO level logging on all domains. 
        """
        if not ikpdb_log_arg:
            return
        IKPdbLogger.enabled = True
        logging_configuration_string = ikpdb_log_arg.lower()
        for letter in logging_configuration_string:
            if letter in IKPdbLogger.DOMAINS:
                IKPdbLogger.DOMAINS[letter] = 10

    @classmethod
    def _log(cls, domain, level, message, *args):
        ts = datetime.datetime.now().strftime('%H:%M:%S,%f')
        if level >= IKPdbLogger.DOMAINS[domain]:
            try:
                string = message % args
            except:
                string = message+"".join(map(lambda e: str(e), args))
            print >>sys.stderr, IKPdbLogger.TEMPLATES[level/10] % (domain, ts, string,) 

_logger = IKPdbLogger


##
# Network connection
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
        _logger.n_debug("Sent %s bytes >>>%s<<<", len(msg), msg)
        
    def log_received(self, msg):
        _logger.n_debug("Received %s bytes >>>%s<<<", len(msg), msg)
    
    def send(self, command, _id=None, result={}, command_exec_status="ok", 
             frames=[], error_messages=[], warning_messages=[], info_messages=[],
             exception=None):
        """Build a message from passed dict object and send it to debugger"""
        with self._connection_lock:
            msg = self.encode({
                '_id': _id,
                'command': command,
                'result': result,
                'commandExecStatus': command_exec_status,
                'frames': frames,
                'info_messages': info_messages,
                'warning_messages': warning_messages,
                'error_messages': error_messages,
                'exception': exception
            })
            if self._connection:
                send_bytes_count = self._connection.sendall(msg)
                self.log_sent(msg)
                return send_bytes_count
            raise IKPdbConnectionError("Connection lost!")

    def reply(self, obj, result, command_exec_status='ok', info_messages=[], 
              warning_messages=[], error_messages=[]):
        """Build a response from a previsoulsy received command msg, send it
           and return number of sent bytes."""
        with self._connection_lock:
            # TODO: add a parameter to remove args from messags ?
            if True:
                del obj['args']
            obj['result'] = result
            obj['commandExecStatus'] = command_exec_status
            obj['info_messages'] = info_messages
            obj['warning_messages'] = warning_messages
            obj['error_messages'] = error_messages
            msg = self.encode(obj)
            send_bytes_count = self._connection.sendall(msg)
            self.log_sent(msg)
            return send_bytes_count

    def receive(self):
        """Waits for a message from the debugger and returns it as a dict"""
        with self._connection_lock:
            while True:
                _logger.n_debug("Enter socket.recv(%s) with self._received_data = %s)", 
                                self.SOCKET_BUFFER_SIZE, 
                                self._received_data)
                data = self._connection.recv(self.SOCKET_BUFFER_SIZE)
                _logger.n_debug("Socket.recv(%s) => %s", self.SOCKET_BUFFER_SIZE, data)
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
#


class IKPdbException(Exception):
    pass


def IKPdbRepr(t):
    """returns a type representation suitable for debugger GUI
    :param t: anyThing
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
        self._active_thread_lock = threading.Lock()
        self.curframe = None
        self.stopframe = None
        self.botframe = None
        self._CWD = launch_working_directory or os.getcwd()
        
        # If True, debugger breaks on first line to allow user to setup 
        # some breakpoints.
        self.initial_setup_break = False  
        
        # if defined, force debugger to stop only in a specific thread
        self.stop_thread_ident = None  

    def canonic(self, filename):
        """ returns canonical version of a file name.
        A canonical file name is an absolute, lowercase normalized path 
        to a given file.
        """
        if filename == "<" + filename[1:-1] + ">":
            return filename
        canonic = self.fncache.get(filename)
        if not canonic:
            canonic = os.path.abspath(filename)
            canonic = os.path.normcase(canonic)
            self.fncache[filename] = canonic
        return canonic

    def lookup_module(self, filename):
        """Helper function for break/clear parsing -- may be overridden.
        lookup_module() translates (possibly incomplete) file or module name
        into an absolute file name.
        """
        _logger.p_debug("lookup_module(%s) with os.getcwd()=>%s", filename, os.getcwd())
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
            
        # Can we find file relatively to launch script
        f = os.path.join(sys.path[0], filename)  
        if os.path.exists(f) and self.canonic(f) == self.mainpyfile:
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
        o_type = type(o)
        if type(o) in (types.DictType, types.ListType, types.TupleType,):
            return len(o)
        elif type(o) in (types.NoneType, types.BooleanType, types.FloatType, 
                         types.UnicodeType, types.FloatType, types.IntType, 
                         types.StringType, types.LongType, types.ModuleType, 
                         types.MethodType, types.FunctionType,):
            return 0
        else:
            # Following lines are used to debug variables members browsing
            # and counting
            # if False and str(o_type) == "<class 'socket._socketobject'>":
            #     print "@378"
            #     print dir(o)
            #     print "hasattr(o, '__dict__')=%s" % hasattr(o,'__dict__')
            #     count = 0
            #     if hasattr(o, '__dict__'):
            #         for m_name, m_value in o.__dict__.iteritems():
            #             if m_name.startswith('__'):
            #                 print "    %s=>False" % (m_name,)
            #                 continue
            #             if type(m_value) in (types.ModuleType, types.MethodType, types.FunctionType,):
            #                 print "    %s=>False" % (m_name,)
            #                 continue
            #             print "    %s=>True" % (m_name,)
            #             count +=1
            #     print "    %s => %s = %s" % (o, count, dir(o),)
            # else:
            if hasattr(o, '__dict__'):
                count = len([m_name for m_name, m_value in o.__dict__.iteritems()
                              if not m_name.startswith('__') 
                                and not type(m_value) in (types.ModuleType, 
                                                          types.MethodType, 
                                                          types.FunctionType,) ])
            else:
                count = 0
            return count

    def extract_object_properties(self, o):
        """Extracts all properties from an object (eg. f_locals, f_globals, 
        user dict, instance ...) and returns them as an array of variables
        """
        _logger.e_debug("extract_object_properties(%s)", o)
        var_list = []
        if type(o) == types.DictType:
            a_var_name = None
            a_var_value = None
            for a_var_name in o:
                a_var_value = o[a_var_name]
                a_var_info = {
                    'id': id(a_var_value),
                    'name': a_var_name,
                    'type': IKPdbRepr(a_var_value),
                    'value': repr(a_var_value),
                    'children_count': self.object_properties_count(a_var_value)
                }
                var_list.append(a_var_info)
                
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
            if hasattr(o, '__dict__'):
                for a_var_name, a_var_value in o.__dict__.iteritems():
                    if (not a_var_name.startswith('__') 
                        and not type(a_var_value) in (types.ModuleType, 
                                                      types.MethodType, 
                                                      types.FunctionType,)):
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
        _logger.f_debug("dump_frames(), frame analysis:")
        spacer = ""
        while hasattr(frame_browser, 'f_back') and frame_browser.f_back != self.botframe:
            spacer += "="
            _logger.f_debug("%s>frame = %s, frame.f_code = %s, frame.f_back = %s, "
                            "self.botframe = %s",
                            spacer,
                            hex(id(frame_browser)),
                            frame_browser.f_code,
                            hex(id(frame_browser.f_back)),
                            hex(id(self.botframe)))
                                
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
        """ evaluate 'expression' in the context of the frame identified by
        'frame_id' or globally.
        Breakpoints are disabled depending on 'disable_break' value.
        Retursn a tuple of value and type both as str.
        """
        if disable_break:
            breakpoints_backup = self.backup_breakpoints_state()
            self.disable_all_breakpoints()

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
        except SyntaxError:
            try:
                # From: http://stackoverflow.com/questions/3906232/python-get-the-print-output-in-an-exec-statement
                sys_stdout = sys.stdout
                eval_stdout = cStringIO.StringIO()
                sys.stdout = eval_stdout
                exec(expression, global_vars, local_vars)
                sys.stdout = sys_stdout
                result_value = "<plaintext>%s" % eval_stdout.getvalue()
                result_type = "str"
                result = result_value
            except Exception as e:
                t, result = sys.exc_info()[:2]
                if isinstance(t, str):
                    result_type = t
                else: 
                    result_type = str(t.__name__)
                result_value = "%s: %s" % (result_type, result,)
        except:
            t, result = sys.exc_info()[:2]
            if isinstance(t, str):
                result_type = t
            else: 
                result_type = t.__name__
            result_value = "%s: %s" % (result_type, result,)

        if disable_break:
            self.restore_breakpoints_state(breakpoints_backup)

        _logger.e_debug("evaluate(%s) => value = %s:%s | %s", expression, result_value, result_type, result)
        return result_value, result_type

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        
        _logger.f_debug("user_call() with _wait_for_mainpyfile=%s," 
                        "threadName=%s, frame=%s, frame.f_code=%s, self.mainpyfile=%s,"
                        "self.break_here()=%s, self.stop_here()=%s\n",
                        self._wait_for_mainpyfile,
                        threading.currentThread().name,
                        hex(id(frame)),
                        frame.f_code,
                        self.mainpyfile,
                        self.break_here(frame),
                        self.stop_here(frame))
        
        if self._wait_for_mainpyfile:
            return  # processing is done in user_line()
        
        if self.stop_here(frame):
            return  # processing is done in user_line()
        # TODO: What can we do with this function in the context of gui debugging


    def _set_stopinfo(self, stopframe, returnframe, stoplineno=0, thread_ident=None):
        """Defines where/where debugger must stop next.
        This method is overloaded to supprot multi-threading debugging.
        """
        self.stopframe = stopframe
        self.returnframe = returnframe
        self.quitting = False
        # stoplineno >= 0 means: stop at line >= the stoplineno
        # stoplineno -1 means: don't stop at all
        self.stoplineno = stoplineno
        self.stop_thread_ident = thread_ident  # if defined, stop only in this thread


    def set_next(self, frame):  # aka Step Over
        """Stop on the next line in or below the given frame. 
           Often aka 'Step Over'
        """
        self._set_stopinfo(frame,
                           None,
                           thread_ident=None)  # now Stop in every thread

    def set_step(self):
        """Stop after one line of code. Often aka 'Step Into'.
        This method is overloaded to support multi-threading: original 'set_step()'
        causes the debugger to stop on next executed line whatever threads it
        belongs to.
        In this version, we specify that the debugger must stop only in 
        the current thread by letting self.thread_ident.
        self.thread_ident will be reset at 'run', 'resume', 'step over', 'step out', 'step into'
        """
        # Issue #13183: pdb skips frames after hitting a breakpoint and running
        # step commands.
        # Restore the trace function in the caller (that may not have been set
        # for performance reasons) when returning from the current frame.
        if self.frame_returning:
            caller_frame = self.frame_returning.f_back
            if caller_frame and not caller_frame.f_trace:
                caller_frame.f_trace = self.trace_dispatch
        self._set_stopinfo(None, None, thread_ident=threading.currentThread().ident)


    def set_return(self, frame):
        """Stop when returning from the given frame. Often aka Step Out"""
        self._set_stopinfo(frame.f_back, 
                           frame,
                           thread_ident=None)

    def set_continue(self):
        """ Resume: don't stop except at breakpoints or when finished
        """
        self._set_stopinfo(self.botframe, 
                           None, 
                           -1, 
                           thread_ident=None)  # now break in every threads
        if not self.breaks:
            # no breakpoints; run without debugger overhead 
            # TODO: Remove trace function in any threads
            sys.settrace(None)
            frame = sys._getframe().f_back
            while frame and frame is not self.botframe:
                del frame.f_trace
                frame = frame.f_back

    def set_break(self, filename, lineno, temporary=0, cond = None,
                  funcname=None, enabled=True):
        """ Create a beakpoint. 
        This method is overloaded to allow straight creation of disabled 
        breakpoints
        """
        filename = self.canonic(filename)
        import linecache # Import as late as possible
        line = linecache.getline(filename, lineno)
        if not line:
            return 'Line %s:%d does not exist' % (filename,
                                   lineno)
        if not filename in self.breaks:
            self.breaks[filename] = []
        list = self.breaks[filename]
        if not lineno in list:
            list.append(lineno)
        bp = bdb.Breakpoint(filename, lineno, temporary, cond, funcname)
        bp.enabled = enabled


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
            # set_step() leads us here. Let's check we are on the good thread
            if self.stop_thread_ident:
                if self.stop_thread_ident == threading.currentThread().ident:
                    #_logger.b_debug("stop_here() step_into in stop_thread => True")
                    # self.stop_thread_ident will be reset by resume, step out, step over
                    return True
                else:
                    #_logger.b_debug("stop_here() step_into NOT in stop_thread => False")
                    return False
            #_logger.b_debug("stop_here() step_into with NO stop_thread => True")
            return True
        return False


    def user_line(self, frame, post_mortem=False):
        """This function is called when debugger has decided that we must
        stop or break at this frame."""
        
        _logger.f_debug("user_line() with_wait_for_mainpyfile=%s," 
                        "threadName=%s, frame=%s, frame.f_code=%s, self.mainpyfile=%s,"
                        "self.break_here()=%s, self.stop_here()=%s\n",
                         self._wait_for_mainpyfile,
                         threading.currentThread().name,
                         hex(id(frame)),
                         frame.f_code,
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
        if (self._wait_for_mainpyfile 
                and frame.f_code.co_filename=='<string>'
                and frame.f_lineno==1):
            self._wait_for_mainpyfile = 0
            if not self.breaks:
                self.set_step()  # We want to give user an opportunity to set breakpoints  
                self.initial_setup_break = True  # fsend message to user 
            else:
                self.set_continue()  
            return

        # acquire breakpoint Lock before sending break command to Cloud9
        self._active_breakpoint_lock.acquire()
        frames = self.dump_frames(frame)
        exception=None
        warning_messages = []

        if post_mortem:
            exception = {
                'type': IKPdbRepr(post_mortem[1]),
                'info': post_mortem[1].message
            }

        if self.initial_setup_break:
            warning_messages = ["No breakpoints are defined ! IKPdb stopped so "
                                "that you can setup some breakpoints then "
                                "'Resume' execution."]
            self.initial_setup_break = False

        remote_client.send('programBreak', 
                           frames=frames,
                           result={'executionStatus': 'stopped'},
                           warning_messages=warning_messages,
                           exception=exception)
        self.setup(frame, None)  # Reconfigure frame, stack and locals
        self.command_loop(post_mortem=post_mortem)
        
    #####
    # breakpoints related methods
    # In a future must be moved to a new Breakpoint class
    #
    def get_breakpoints_list(self):
        """Returns a list of all breakpoints with their complete state.
        Each breakpoint is described by a dict.
        Warning: IKPDb line numbers are 1 based ; any line number conversion
        must be done by clients (eg. inouk.ikpdb for Cloud9)
        """
        breakpoints_list = []
        for breakpoint in bdb.Breakpoint.bpbynumber:
            if breakpoint:  # breakpoint #0 exists and is always None
                bp_dict = {
                    'breakpoint_number': breakpoint.number,
                    'file_name': breakpoint.file,
                    'line_number': breakpoint.line,
                    'condition': breakpoint.cond,
                    'enabled': breakpoint.enabled,
                }
                all_breakpoints_state.append(bp_dict)
        return breakpoints_list
        
    def get_breakpoint_number(self, filename, line):
        """lookup breakpoint by filename and line number and returns 
        its' number.
        """
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
        if not bp:
            return "Found no breakpoint numbered %s" % bp_number
        _logger.b_debug("    change_breakpoint_state(bp_number=%s, enabled=%s, condition=%s) found %s", 
                        bp_number,
                        enabled,
                        repr(condition),
                        bp)
        if bp:
            bp.enabled = enabled
            # update condition for conditional breakpoints
            bp.cond = condition
        return None

    def backup_breakpoints_state(self):
        """Returns the state of all breakpoints"""
        all_breakpoints_state = []
        for breakpoint in bdb.Breakpoint.bpbynumber:
            if breakpoint:  # breakpoint #0 exists and is always None
                all_breakpoints_state.append((breakpoint.number, 
                                              breakpoint.enabled, 
                                              breakpoint.cond,))
        return all_breakpoints_state

    def restore_breakpoints_state(self, breakpoints_state_list):
        """Restore the state of breakpoints given a list.
        breakpoints_state_list is a list of tuple. Each tuple is of form:
        (breakpoint_number, enabled,)
        """
        for breakpoint_state in breakpoints_state_list:
            self.change_breakpoint_state(breakpoint_state[0],
                                         breakpoint_state[1],
                                         breakpoint_state[2])
        return

    def disable_all_breakpoints(self):
        """Disable all breakpointss"""
        for breakpoint in bdb.Breakpoint.bpbynumber:
            if breakpoint:  # breakpoint #0 exists and is always None
                breakpoint.enabled = False
        return


    def run(self, cmd, globals=None, locals=None):
        """ overloaded to debug multithreaded programs"""
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
                breakpoints_list = self.get_breakpoints_list()
                remote_client.reply(obj, breakpoints_list)
                _logger.b_debug("getBreakpoints(%s) => %s", args, breakpoints_list)
                
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
                enabled = args.get('enabled', True)
                _logger.b_debug("setBreakpoint(file_name=%s, line_number=%s,"
                                " condition=%s, enabled=%s) with CWD=%s",
                                file_name,
                                line_number,
                                condition,
                                enabled,
                                os.getcwd())
                c_file_name = self.lookup_module(file_name)
                r = self.set_break(c_file_name, 
                                   line_number, 
                                   cond=condition,
                                   enabled=enabled)
                error_messages = []
                if r:
                    _logger.g_error("setBreakpoint error: %s", r)
                    error_messages = [r]
                    result = {}
                    command_exec_status = 'error'
                else:
                    # get_breakpoint_number invoke lookup_module() so we don't need to do it
                    # TODO: remove this comment when all breakpoint methods will
                    # do the same
                    bp_number = self.get_breakpoint_number(args['file_name'], args['line_number'])
                    assert bp_number, "Internal error: uncaught setBreakpoint failure"
                    result = {'breakpoint_number': bp_number}
                    command_exec_status = 'ok'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    error_messages=error_messages)
            
            elif command == "changeBreakpointState":
                # Allows to:
                #  - activate or deactivate breakpoint 
                #  - set or remove condition
                _logger.b_debug("changeBreakpointState(%s)", args)
                bp_number = args.get('breakpoint_number', None)
                if bp_number:
                    r = self.change_breakpoint_state(bp_number,
                                                     args.get('enabled', False), 
                                                     condition=args.get('condition', ''))
                    result = {}
                    error_messages = []
                    if r:
                        msg = "changeBreakpointState() error: \"%s\"" % r
                        _logger.g_error("    "+msg)
                        error_messages = [msg]
                        command_exec_status = 'error'
                    else:
                        command_exec_status = 'ok'
                else:
                    result = {}
                    msg = "changeBreakpointState() error: missing required breakpointNumber parameter."
                    _logger.g_error("    "+msg)
                    error_messages = [msg]
                    command_exec_status = 'error'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    error_messages=error_messages)
                _logger.b_debug("    command_exec_status => %s", command_exec_status)

            elif command == "clearBreakpoint":
                # set_break(filename, lineno, temporary=0, cond=None, funcname=None)
                # Set a new breakpoint. If the lineno line doesn't exist for the
                # filename passed as argument, return an error message. €
                # The filename should be in canonical form, as described in the 
                # canonic() method.
                c_file_name = self.lookup_module(args['file_name'])
                r = self.clear_break(c_file_name, args['line_number'])
                result = {}
                error_messages = []
                if r:
                    _logger.g_error("clearBreakpoint error: %s", r)
                    error_messages = [r]
                    command_exec_status = 'error'
                else:
                    command_exec_status = 'ok'
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    error_messages=error_messages)
                _logger.b_debug("clearBreakpoint(%s)", args)
            
            elif command == "getProperties":
                _logger.e_debug("getProperties(%s)", args)
                error_messages = []
                if args.get('id', False):
                    po_value = ctypes.cast(args['id'], ctypes.py_object).value
                    result={'properties': self.extract_object_properties(po_value) or []}
                    command_exec_status = 'ok'
                else:
                    result={'properties': self.extract_object_properties(None) or []}
                    command_exec_status = 'ok'
                    
                _logger.e_debug("    => %s", result)
                remote_client.reply(obj, result, 
                                    command_exec_status=command_exec_status,
                                    error_messages=error_messages)

            elif command == "setVariable":
                _logger.e_debug("setVariable(%s)", args)
                error_messages = []
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
                    error_messages = [msg]
                    _logger.e_error(msg)
                command_exec_status = 'ok'
                remote_client.reply(obj, 
                                    result, 
                                    command_exec_status=command_exec_status,
                                    error_messages=error_messages)

            elif command == 'runScript':
                _logger.x_debug("runScript(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self._runscript(self.mainpyfile)
                return 1 
                
            elif command == 'resume':
                _logger.x_debug("resume(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_continue()
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepOver':  # <=> Pdb n(ext)
                _logger.x_debug("stepOver(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_next(self.curframe)
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepInto':  # <=> Pdb s(tep)
                _logger.x_debug("stepInto(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_step()
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'stepOut':  # <=> Pdb r(eturn)
                _logger.x_debug("stepOut(%s)", args)
                remote_client.reply(obj, {'executionStatus': 'running'})
                self.set_return(self.curframe)
                self._active_breakpoint_lock.release()
                return 1

            elif command == 'evaluate':
                _logger.e_debug("evaluate(%s)", args)
                value, result_type = self.evaluate(args['frame'], args['expression'], args['global'], disable_break=args['disableBreak'])
                remote_client.reply(obj, {'value': value, 'type': result_type})  # result

            else:
                _logger.g_critical("Unsupported command '%s'.", command)
                return

            if True:
                _logger.b_debug("Current breakpoint list:")
                if not bdb.Breakpoint.bplist:
                    _logger.b_debug("    <empty>") 
                                        
                for bl in bdb.Breakpoint.bplist:
                    for bp in bdb.Breakpoint.bplist[bl]:
                        _logger.b_debug("    %s => %s => number=%s, enabled=%s, condition=%s", 
                                        bl, bp,
                                        bp.number,
                                        bp.enabled,
                                        repr(bp.cond))

        
def set_trace():
    """ breaks on the line that invoked this function. 
    """
    global ikpdb
    if not ikpdb:
        raise Exception("IKPdb must be launched before calling ikpd.set_trace().")
    ikpdb.set_trace(sys._getframe().f_back)

def post_mortem(trace_back, exc_info=None):
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
    if exc_info:
        ikpdb.user_line(pm_traceback.tb_frame, post_mortem=exc_info)
    else:
        ikpdb.user_line(pm_traceback.tb_frame)
        
    ikpdb.forget()
    _logger.g_info("Post mortem debugger finished.")

##
# Signal Handler to properly close socket connection
#
SIGNALS_DICT = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                if v.startswith('SIG') and not v.startswith('SIG_'))

def close_connection():
    try:
        if client_connection:
            _logger.g_debug("Closing open connection...")
            # Cf. https://docs.python.org/2/howto/sockets.html#disconnecting
            client_connection.shutdown(socket.SHUT_RDWR)
            client_connection.close()
            _logger.g_debug("Connection closed...")
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

    parser = argparse.ArgumentParser(description="IKPdb %s - Inouk Python Debugger for CPython 2.7",
                                     epilog="(c) 2016 Cyril MORISSE")
    parser.add_argument("-ik_a","--ikpdb-address", 
                        default='127.0.0.1',
                        dest="IKPDB_ADDRESS",
                        help="Network address on which debugger runs.")
    parser.add_argument("-ik_p","--ikpdb-port",
                        type=int, 
                        default=15470,
                        dest="IKPDB_PORT",
                        help="Network port on which debugger runs.")
    parser.add_argument("-ik_l", "--ikpdb-log",
                        dest="IKPDB_LOG",
                        default='',
                        help="Logger command string.")
    parser.add_argument("-ik_w", "--ikpdb-welcome",
                        dest="IKPDB_SEND_WELCOME_MESSAGE",
                        default=True,
                        help="Send a Welcome 'start' message at client connection.")
    parser.add_argument("script_command_args",
                        metavar="scriptfile [args]",
                        help="Debugged script followed by all his args.",
                        nargs=argparse.REMAINDER)
    cmd_line_args = parser.parse_args()
    
    _logger.setup(cmd_line_args.IKPDB_LOG)

    # We modify sys.argv to reflect command line of
    # debugged script with all IKPdb args removed
    sys.argv = cmd_line_args.script_command_args

    _logger.g_debug("Interpreter: '%s'", sys.executable)
    _logger.g_debug("Args: %s", cmd_line_args)
    _logger.g_info("Starts debugging: '%s'", " ".join(sys.argv))
    _logger.g_info("With CWD: '%s'", os.getcwd())
    
    if not sys.argv[0:]:
        print "Error: scriptfile argument is required"
        sys.exit(2)

    # By using argparse.REMAINDER, sys.argv reflects command line of
    # debugged script with all IKPdb args removed
    mainpyfile =  sys.argv[0]     # Get script filename
    _logger.g_debug("mainpyfile = '%s'", mainpyfile)
    if not os.path.exists(mainpyfile):
        print 'Error:', mainpyfile, 'does not exist'
        sys.exit(1)

    # sets up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # no longer required
    # del sys.argv[0]         # Hide "ikpdb.py" from argument list

    # Replace ikpdb's dir with script's dir in front of module search path.
    sys.path[0] = os.path.dirname(mainpyfile)

    # Note on saving/restoring sys.argv: it's a good idea when sys.argv was
    # modified by the script being debugged. It's a bad idea when it was
    # changed by the user from the command line.
    
    # Initialize IKPdb listen socket
    debug_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # http://stackoverflow.com/questions/4465959/python-errno-98-address-already-in-use?lq=1
    debug_socket.bind((cmd_line_args.IKPDB_ADDRESS, cmd_line_args.IKPDB_PORT,))

    _logger.g_info('IKPdb listening on %s:%s', cmd_line_args.IKPDB_ADDRESS, cmd_line_args.IKPDB_PORT)
    debug_socket.listen(1)  # 1 connection max
    
    # Wait for a connection
    global client_connection
    client_connection, client_address = debug_socket.accept()
    _logger.g_info("Connected with %s:%s", client_address[0], client_address[1])  
    # TODO: Redirect sdtout and stderr to a cloud9 windows ??

    # setup remote client connection
    global remote_client
    remote_client = IKPdbConnectionHandler(client_connection)  
    
    global ikpdb
    ikpdb = IKPdb()

    if cmd_line_args.IKPDB_SEND_WELCOME_MESSAGE:  
        remote_client.send("start", info_messages=["Welcome to", "IKPdb", "0.1"])

    # Launch debugging
    try:
        ikpdb.mainpyfile = mainpyfile
        ikpdb.command_loop()
        remote_client.send('programEnd', 
                           result={'exit_code': None, 
                                   'executionStatus': 'terminated'}, 
                           command_exec_status="ok")
        _logger.g_info("Program terminated with no returned value.")  # TODO: send this to the debuger gui
        sys.exit(0)

    except SystemExit:
        # In most cases SystemExit does not warrant a post-mortem session.
        exit_code = sys.exc_info()[1].code
        _logger.g_info("Program exited with exit code: %s.", exit_code)

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
        _logger.g_info("Uncaught exception. Entering post mortem debugging")
        pm_traceback = sys.exc_info()[2]
        while pm_traceback.tb_next:
            pm_traceback = pm_traceback.tb_next      
        ikpdb.setup(None, pm_traceback)
        ikpdb.user_line(pm_traceback.tb_frame, post_mortem=sys.exc_info())
        ikpdb.forget()
        try:
            remote_client.send('programEnd', 
                               result={'exit_code': None, 
                                       'executionStatus': 'terminated'}, 
                               command_exec_status="ok")
        except:
            pass
        
        _logger.g_info("Post mortem debugger finished.")
        close_connection()
        sys.exit(1)


# When invoked as main program, invoke the debugger on a script
if __name__ == '__main__':
    import ikpdb
    ikpdb.main()
