# Raw data #

These timings are acquired with Python's timeit module when compiling PyS60's core -module with dual core processor.

```
scons compiler=winscw release=udeb --debug=explain -j 1
1 loops, best of 1: 21.4 sec per loop

scons compiler=winscw release=udeb --debug=explain -j 2
1 loops, best of 1: 14.7 sec per loop

abld build winscw udeb
1 loops, best of 1: 34.2 sec per loop

```

So compiling with SCons using 2 parallel jobs grants you over 2x speed improvement. It is faster even without parallel jobs. The biggest difference comes from startup time of ABLD, when it is thinking what to build( or whatever it does ).