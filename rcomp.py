"""RComp utility"""

__author__    = "Jussi Toivola"
__license__   = "MIT License"

import os
import sys
import cpp

from SCons.Script import Command

#: RComp command path
RCOMP = os.environ["EPOCROOT"] + os.path.join( "epoc32", "tools", "rcomp" )
if sys.platform == "linux2":
    RCOMP = "wine " + RCOMP + ".exe"
    
def RComp( env, rsc, rsg, rss, options, includes, fileinc, defines ):
    """Utility for creating Command for Symbian resource compiler"""
    # Preprocess the resource file first
    rpp = ".".join( os.path.basename( rss ).split(".")[:-1] + ["rpp"] )
    rpp = os.path.join( os.path.dirname( rsg ), rpp )
    
    cpp.Preprocess( env, rpp, rss, includes, fileinc, defines + ["_UNICODE" ] )
    
    cmd = RCOMP + ' -u %s -o"%s" -h"%s" -s"%s" -i"%s" ' % \
            ( options, rsc, rsg, rpp, rss )        
            
    return env.Command( [rsc,rsg], [rpp,rss], cmd )


