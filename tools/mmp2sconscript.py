""" This a tool to convert an MMP file to a SCons's SConscript recipe """
import sys
import os

TEMPLATE_SCONSCRIPT = """
{{script}}
from pprint import pprint
from StringIO import StringIO

{{endscript}}

{{script}}
s=StringIO()
pprint( library, s )
library = s.getvalue()
s.close()
{{endscript}}

# This file is generated with mmp2sconscript
from scons_symbian import *

target     = "{{target}}"
targettype = "{{targettype}}"
libraries  = {{library}}
# Static libs
staticlibs = {{staticlibrary}}

{{script}}
if uid[1] is None: uid[1] = 0x0 
{{endscript}}
uid3 = {{uid[1]}}

{{script}}
s=StringIO()
pprint( source, s )
source = s.getvalue()
s.close()

s=StringIO()
pprint( userinclude, s )
includes = s.getvalue()
s.close()

s=StringIO()
pprint( systeminclude, s )
sysincludes = s.getvalue()
s.close()

{{endscript}}

sources = {{source}}

includes    = {{userinclude}}
sysincludes = {{systeminclude}}
defines     = {{macro}}

SymbianProgram( target, targettype,
    sources = sources,
    includes    = includes,
    sysincludes = sysincludes,
    libraries   = staticlibs+libraries,
    defines     = defines,
    epocstacksize = {{epocstacksize}},
    epocheapsize  = ({{",".join(epocheapsize)}}),
    uid3 = uid3,
)

"""

class MMP2SConscript(object):
    
    def __init__(self):
        pass
    
    def generate_sconscript(self, data):
        from scons_symbian import preppy
        
        m = preppy.getModule("sconscript", sourcetext=TEMPLATE_SCONSCRIPT)
        
        outputfile = None
        if self.sconscript:
            dirpath = os.path.dirname(os.path.abspath(self.sconscript))
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            
            outputfile = open( self.sconscript, 'wb')
            
        m.run( data, outputfile = outputfile )
        
    def convert_mmp( self, mmp, sconscript ):
        
        self.mmp = mmp
        self.sconscript = sconscript
        
        from scons_symbian.mmp_parser import MMPParser
        
        parser = MMPParser(mmp)    
        data = parser.Parse()
        print data
        scons_data = self.generate_sconscript(data)    
    
def start():
    
    from optparse import OptionParser
    
    parser = OptionParser()
    parser.add_option("-m", "", dest="mmp",
                  help="MMP to convert", metavar="FILE")
    parser.add_option("-s", "", dest="sconscript",
                  help="Target path for generated sconscript", metavar="FILE")

    (options, args) = parser.parse_args()
    
    c = MMP2SConscript()
    c.convert_mmp( options.mmp, options.sconscript )
    
if __name__ == "__main__":    
    start()
