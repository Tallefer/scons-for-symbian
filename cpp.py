"""
Preprocessor utility
"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"

from os.path import abspath
import os
import sys

CPP = os.environ["EPOCROOT"] + os.path.join( "epoc32", "gcc", "bin", "cpp" )

if sys.platform == "linux2":
    CPP = "wine " + CPP + ".exe"

def Preprocess( env, target, source, includes, fileinc, defines ):
    """Utility for creating Command for preprocessor"""
    handle_path = abspath
    
    if sys.platform == "linux2":
        # Use relative on linux
        
        def h( x ):
            import relpath
            if not x.startswith( "/" ):
                return x
            
            p = relpath.relpath( os.getcwd(), x )
            #print p
            return p
            
        handle_path = h
    
    # This is strange... On windows it seems that include paths must be absolute and relative on linux
    cmd=[
            CPP,
            "-undef -C -I-",
            "-I",
            " -I ".join( [ handle_path(x) for x in includes ]  ),

            " -D" + " -D".join( defines ),
            handle_path(source),
            " -o %s" % handle_path(target),
            " -include",
            " -include ".join( [ handle_path(x) for x in fileinc ] )
        ]
    cmd = " ".join( cmd )
    
    return env.Command( target, source, cmd )



