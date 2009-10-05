""" Utility functions for printing out stuff """

import sys
import os
from config import RUNNING_SCONS

def sysout(*args):
    global RUNNING_SCONS
    if not RUNNING_SCONS: return
    
    for a in args:
        sys.stdout.write( str(a) )
        sys.stdout.write( " " )
    sys.stdout.write( os.linesep )

def loginfo(*args):
    sysout( "Info:", *args)