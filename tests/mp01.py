# coding: utf-8

#
# This file is part of the IKPdb Debugger
# Copyright (c) 2017 by Cyril MORISSE
# Licence: MIT. See LICENCE at repository root
#
import sys
import os
import time
import multiprocessing
import ikpdb


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


if __name__=='__main__':

    TEST_SUSPEND = True

    w = Worker()
    t = multiprocessing.Process(target=w.run, args=(5,))
    t.start()


    counter = 0
    if TEST_SUSPEND:
        print "Suspend test begin..."
        t0 = time.clock()
        while counter < 10000000:
            counter +=1
        t1 = time.clock()
        print "duration = %s" % (t1-t0)
        
        
    w.terminate()
    t.join()
    
    
    print "finished"