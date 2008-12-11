"""RComp utility"""

__author__ = "Jussi Toivola"
__license__ = "MIT License"

import cpp
import os
import sys

#: RComp command path
RCOMP = os.environ["EPOCROOT"] + os.path.join( "epoc32", "tools", "rcomp" )
if sys.platform == "linux2":
    RCOMP = "wine " + RCOMP + ".exe"

def RComp( env, rsc, rsg, rss, options, includes, fileinc, defines ):
    """Utility for creating Command for Symbian resource compiler"""
    # Preprocess the resource file first
    rpp = ".".join( os.path.basename( rss ).split( "." )[: - 1] + ["rpp"] )
    rpp = os.path.abspath(os.path.join( os.path.dirname( rsg ), rpp ))
    
    import relpath    
    cpp.Preprocess( env, rpp, rss, includes, fileinc, defines + ["_UNICODE" ] )
    rss = relpath.relpath( os.path.abspath( "." ), os.path.abspath( rss ) )
    # FIXME: For some strange reason, using the rcomp when creating bootup resource fails
    #        if using the 'normal' way( colorizer.py must mess it up somehow )
    def build(target, source, env):
        
        cmd = RCOMP + ' -u %s -o\"%s\" -h\"%s\" -s\"%s\" -i\"%s\" ' % \
                ( options, rsc, rsg, rpp, rss )
        os.system(cmd)        
    
    return env.Command( [rsc, rsg], [rpp, rss], build )


