import sys
import os
import time
import threading
import ikpdb

TEST_MULTI_THREADING = False
TEST_EXCEPTION_PROPAGATION = False
TEST_POSTMORTEM = True
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


if __name__=='__main__':
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
    
