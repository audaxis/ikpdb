import sys
import os
import time
import threading
import ikpdb
import logging
import datetime

TEST_MULTI_THREADING = False
TEST_EXCEPTION_PROPAGATION = False
TEST_POSTMORTEM = False
TEST_SYS_EXIT = 0
TEST_STEPPING = True

# Note that ikpdb.set_trace() will reset/mess breakpoints set using GUI
TEST_SET_TRACE = False  

TCB = TEST_CONDITIONAL_BREAKPOINT = True

class Worker(object):
    def __init__(self):
        self._running = True
    
    def terminate(self):
        self._running = False
        
    def run(self, n):
        work_count = n
        while self._running and n > 0:
            print "Worker: Doing iteration: %s" % (work_count - n)
            if n == 3:
                pass  # ikpdb.set_trace()
            n -= 1
            time.sleep(2)

ga = 5
gb ="hello"
g_dict = {"Genesis": 1, "Don't Look Back": 2, 'array': [1,3,{'coucou': 3.14}]}
a_tuple = (1,'e', 3.14, ['a', 'b'])

class BigBear:
    color = "white"
    def __init__(self, name='unknown'):
        self._name = name
        
    def grumble(self):
        print "Grrrrr"

def sub_function():
    return True

def the_function(p_nb_seconds):
    a_var = 18.3
    the_function_local_list = [1, 2, 3, ('others', 'me',)]
    a_beast = BigBear()
    print "ga=%s" % ga
    
    print "Hello World"
    print "This is the ligne with a breakpoint"
    for loop_idx in range(p_nb_seconds):
        print "hello @ %s seconds in MainThread" % loop_idx
        time.sleep(1)
        if loop_idx == 12:
            if TEST_SET_TRACE:
                ikpdb.set_trace()  # will break on next line
            pass # Need this for set_trace()
            a_var = 98.3
            sub_function()                


def sub_raiser():
    raise Exception("Take this")


def raiser():
    try:
        sub_raiser()
    except Exception as e:
        raise e

import logging


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
_logger.setup('g')


import timeit


if __name__=='__main__':

    start = timeit.default_timer()
    for i in range(1000):
        logging.warning("chaine debug")
    end = timeit.default_timer()
        
    
    start2 = timeit.default_timer()
    for i in range(1000):
        _logger.g_critical("chaine debug")
    end2 = timeit.default_timer()

    #_logger.x_debug("arg", 3, 4)
    _logger.x_error("chaine %s ", 3, 4)
    #_logger.x_erreor("chaine %s ", 3, 4)

    
    print "exec time 1 =%s" % (end-start) 
    print "exec time 2 =%s" % (end2-start2) 

    b = 0
    main_bear = BigBear("Cyril")
    print "Type of main_bear=%s" % type(main_bear)
    print "sys.argv=%s" % sys.argv
    
    if TEST_SYS_EXIT:
        sys.exit(TEST_SYS_EXIT)
    
    if TEST_EXCEPTION_PROPAGATION:
        raiser()
    
    if TEST_MULTI_THREADING:
        w = Worker()
        t = threading.Thread(target=w.run, args=(5,))
        t.start()

    duration = 2 if TEST_STEPPING else 15
    the_function(duration)

    if TEST_MULTI_THREADING:
        w.terminate()
        t.join()
    
    print "finished"
    
    if TEST_POSTMORTEM:
        print 5 / b
    
