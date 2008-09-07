"""
Symbian project file(mmp) parser

This file is part of SCons for Symbian project.
"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"

#TODO: Preprocess the mmp file
import os
import sys
from os.path import join, dirname, abspath
from relpath import relpath

KEYWORDS =  ( "target", "targettype", "library", "source", "systeminclude", "userinclude", 
              "staticlibary", "epocallowdlldata", "macro", "capability", "epocstacksize",
              "resources", "uid"
            )
                                         
class MMPParser:
    """Parse MMP to be built with SCons for Symbian"""
    def __init__( self, sourcefile ):
        #: Path to the MMP file.
        self.Source = sourcefile
        
    def Parse( self ):
        f = open( self.Source )
        lines = f.readlines()
        f.close()
        
        workingfolder = os.path.dirname( self.Source )
        sourcepath    = workingfolder
        curdir        = abspath( os.curdir )
        
        lines = [x for x in lines if len( x.strip() ) > 0 ]        
        
        result = {}
        # initialize
        for x in KEYWORDS:
            result[x] = []
        result["epocallowdlldata"] = False # Not enabled with regular scripts either
        result["epocstacksize"].append( hex(8 * 1024 ) )
        result["uid"] += [ None, None]
        for line in lines:                        
            parts = line.split()
            keyword = parts[0].lower()
            if keyword in KEYWORDS:
                items = result.get( keyword, [] )                
                if len( parts ) > 1:
                    if keyword == "source":
                        files = []
                        files = [ join( sourcepath, x ) for x in parts[1:] ]
                        items += files
                    elif keyword == "library":
                        libs = [ x.replace(".lib", "") for x in parts[1:] ]
                        items += libs
                    elif keyword in [ "systeminclude", "userinclude"]:
                        items += [ join( workingfolder, x ) for x in parts[1:] ] 
                    else:
                        items += parts[1:]
                else:
                    if keyword == "epocallowdlldata":
                        result["epocallowdlldata"] = True
                    
                result[keyword] = items
                
            elif keyword == "sourcepath":
                sourcepath = join( sourcepath, parts[1] )
                sourcepath = relpath( curdir, abspath( sourcepath ) )
                print "Curdir:", sourcepath
                
            elif keyword == "start":
                result["resources"]   += [ join( sourcepath, parts[-1] ) ]
                result["userinclude"] += [ sourcepath ]
        
        # Take targettype from file extension instead. TODO: special dlls.
        result["targettype"]    = result["target"][0].split(".")[-1]
        result["target"]        = ".".join( result["target"][0].split(".")[:-1] ) # Strip extension
        result["epocstacksize"] = int( result["epocstacksize"][0], 16 )
        return result

if __name__ == "__main__":
    import pprint
    p = MMPParser( sys.argv[1] )
    
    pprint.pprint( p.Parse() )
