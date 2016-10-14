#include "Python.h"
#include "frameobject.h"
#include "pystate.h"

/**
 * This file is part of the IKPdb Debugger
 * Copyright (c) 2016 by cyril MORISSE, Audaxis
 * Licence: MIT. See LICENCE at repository root
 */

static long debuggerThreadIdent = 0;  // Track debugger thread ident

/*
 * Cached interned string objects used for calling the profile and
 * trace functions.  Initialized by trace_init().
 */
static PyObject *whatstrings[7] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL};
static int
trace_init(void)
{
    static char *whatnames[7] = {"call", "exception", "line", "return",
                                    "c_call", "c_exception", "c_return"};
    PyObject *name;
    int i;
    for (i = 0; i < 7; ++i) {
        if (whatstrings[i] == NULL) {
            name = PyString_InternFromString(whatnames[i]);
            if (name == NULL)
                return -1;
            whatstrings[i] = name;
        }
    }
    return 0;
}

static PyObject *
call_trampoline(PyThreadState *tstate, PyObject* callback,
                PyFrameObject *frame, int what, PyObject *arg)
{
    PyObject *args = PyTuple_New(3);
    PyObject *whatstr;
    PyObject *result;

    if (args == NULL)
        return NULL;
    Py_INCREF(frame);
    whatstr = whatstrings[what];
    Py_INCREF(whatstr);
    if (arg == NULL)
        arg = Py_None;
    Py_INCREF(arg);
    PyTuple_SET_ITEM(args, 0, (PyObject *)frame);
    PyTuple_SET_ITEM(args, 1, whatstr);
    PyTuple_SET_ITEM(args, 2, arg);

    /* call the Python-level function */
    PyFrame_FastToLocals(frame);
    result = PyEval_CallObject(callback, args);
    PyFrame_LocalsToFast(frame, 1);
    if (result == NULL)
        PyTraceBack_Here(frame);

    /* cleanup */
    Py_DECREF(args);
    return result;
}


static int
_tracer_trampoline(PyObject *self, PyFrameObject *frame, int what, PyObject *arg)
{
    PyThreadState *tstate = frame->f_tstate;
    PyObject *callback;
    PyObject *result;

    if (what == PyTrace_CALL)
        callback = self;
    else
        callback = frame->f_trace;
    if (callback == NULL)
        return 0;

    result = call_trampoline(tstate, callback, frame, what, arg);
    if (result == NULL) {
        PyEval_SetTrace(NULL, NULL);
        Py_CLEAR(frame->f_trace);
        return -1;
    }

    if (result != Py_None) {
        PyObject *temp = frame->f_trace;
        frame->f_trace = NULL;
        Py_XDECREF(temp);
        frame->f_trace = result;
    }
    else {
        Py_DECREF(result);
    }
    return 0;
}


void
IK_SetTrace(Py_tracefunc func, PyObject *arg)
{
    // Ensure _Py_TracingPossible is correctly set
    PyEval_SetTrace(func, arg);  
    
    // Now iterate over all threads to set tracing
    PyInterpreterState *interp = PyInterpreterState_Head();
    PyThreadState *loopThreadState = PyInterpreterState_ThreadHead(interp);
    while(loopThreadState) {
        if(loopThreadState->thread_id!=debuggerThreadIdent) {
            PyObject *temp = loopThreadState->c_traceobj;
            Py_XINCREF(arg);
            loopThreadState->c_tracefunc = NULL;
            loopThreadState->c_traceobj = NULL;
            /* Must make sure that profiling is not ignored if 'temp' is freed */
            loopThreadState->use_tracing = loopThreadState->c_profilefunc != NULL;
            Py_XDECREF(temp);
            loopThreadState->c_tracefunc = func;
            loopThreadState->c_traceobj = arg;
            /* Flag that tracing or profiling is turned on */
            loopThreadState->use_tracing = ((func != NULL) || (loopThreadState->c_profilefunc != NULL));
        } else {
            PyObject *temp = loopThreadState->c_traceobj;
            loopThreadState->c_tracefunc = NULL;
            loopThreadState->c_traceobj = NULL;
            /* Must make sure that profiling is not ignored if 'temp' is freed */
            loopThreadState->use_tracing = loopThreadState->c_profilefunc != NULL;
            Py_XDECREF(temp);

        };
        loopThreadState = PyThreadState_Next(loopThreadState);
    };
}


static PyObject *
_ik_set_trace_on(PyObject *self, PyObject *args)
{
    PyObject *traceObject = NULL;

    if (trace_init() == -1)
        return NULL;
    
    if (!PyArg_ParseTuple(args, "Ol", &traceObject, &debuggerThreadIdent)) {
        return NULL;
    }    

    IK_SetTrace(_tracer_trampoline, traceObject);

    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(_ik_set_trace_on_doc,
"_set_trace_on(tracer, thread_id)\n\
\n\
Activate tracing with tracer function, on all threads but the one specified.\n\
See the debugger chapter in the library manual.\n\
This function do not call threading.settrace(), user must do it."
);


static PyObject *
_ik_set_trace_off(PyObject *self)
{
    IK_SetTrace(NULL, NULL);
    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(_ik_set_trace_off_doc,
"_set_trace_off()\n\
\n\
Disable tracing on all threads.\n\
See the debugger chapter in the library manual.\n\
This function do not call threading.settrace(), user must do it."
);


static PyMethodDef InoukMethods[] = {
    {"_set_trace_on", _ik_set_trace_on, METH_VARARGS, _ik_set_trace_on_doc},
    {"_set_trace_off", (PyCFunction)_ik_set_trace_off, METH_NOARGS, _ik_set_trace_off_doc},
    {NULL,           NULL}           /* sentinel */
};


PyMODINIT_FUNC
initiksettrace(void)
{
    (void) Py_InitModule("iksettrace", InoukMethods);
}