"""
Symbian context help generation support

This file is part of SCons for Symbian project.
"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"


import os
import sys
from os.path import join, dirname, abspath, basename
from relpath import relpath
from arguments import COMPILER

def replace_tag( data, tag, value ):
    
    i = data.index( tag )
    i = data.index( ">", i ) + 1
    e = data.index( "<", i )
    
    return data[:i] + value + data[e:]
    
def CSHlp( env, source, uid ):
    "@param source: Help project file .cshlp"
    
    # TODO: Read used files from the project file and add dependencies.
    
    f = open( source ); data = f.read(); f.close()
    
    new_source   = join( dirname( source ) , "_" + basename( source ) )
    source_noext = ".".join( source.split(".")[:-1] )
    # Adding underscore before .hlp, because on GCCE, colon forces space on preprocessor concatenation
    # and it seems to be impossible to generate the header filename if token starts with colon.( See LogMan project )
    result       = "%s_%s_.hlp" % ( source_noext, uid )
    result_hrh   = result + ".hrh"
    
    data = replace_tag( data, "helpfileUID", uid )
    data = replace_tag( data, "destination", basename( result ) )
    
    f = open( new_source, 'w' ); f.write( data.encode( "utf-8") ); f.close()
    
    cmd = "cshlpcmp %s" % ( new_source )
    
    env.Command( [ result, result_hrh ], source, cmd )
    
    return [ result, result_hrh ]
        
        
if __name__ == "__main__":
    
    p = MMPParser( sys.argv[1] )
    
