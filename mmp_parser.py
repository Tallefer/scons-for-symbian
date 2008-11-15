"""
Symbian project file(mmp) parser

This file is part of SCons for Symbian project.
"""
__author__ = "Jussi Toivola"
__license__ = "MIT License"

#TODO: Preprocess the mmp file
from os.path import join, abspath, dirname
from relpath import relpath
import os
import sys

from config.constants import *

KEYWORDS = ("target", "targettype", "library", "source", "systeminclude", "userinclude",
              "staticlibary", "epocallowdlldata", "macro", "capability", "epocstacksize",
              "resources", "uid"
            )

class MMPData(object):
    def __init__(self):
        self.EPOCSTACKSIZE = 0
        self.EPOCHEAPSIZE = 0
        self.SOURCE = []
        self.LIBRARY = []
        self.RESOURCE = []
        self.UID2 = ""
        self.UID3 = ""
        self.TARGETTYPE = ""
        self.SYSTEMINCLUDE = []
        self.USERINCLUDE = []
        self.EPOCALLOWDLLDATA = False
        self.CAPABILITY = []
        self.SOURCEPATH = ["."]
        self.MACRO = []
        self.RESOURCE = ""

TEMPLATE_RESOURCE = r"""
START RESOURCE    %(RESOURCE)s
HEADER
TARGETPATH resource\apps
END
"""

TEMPLATE_RESOURCE_REG = r"""
START RESOURCE    %(RESOURCE)s
#ifdef WINSCW
TARGETPATH       \private\10003a3f\apps
#else
TARGETPATH       \private\10003a3f\import\apps
#endif
END
"""
class MMPExporter(object):
    def __init__(self, targetpath):
        self.TargetPath = targetpath
        self.TargetDir = dirname(targetpath)
        self.MMPData = MMPData()
        self.MMPContents = ""
        
    def Export(self):
        attrs = [ x for x in dir(self.MMPData) if x.isupper() ]
        #import pdb;pdb.set_trace()
        result = []
        targettype = self.MMPData.TARGETTYPE
        if targettype in [ TARGETTYPE_PLUGIN, 
                           TARGETTYPE_DLL, 
                           TARGETTYPE_PYD ]:
            targettype = TARGETTYPE_DLL
            
        result.append("TARGET     %s.%s" % (self.MMPData.TARGET, self.MMPData.TARGETTYPE) )
        result.append("TARGETTYPE %s" % (targettype) )
        result.append("UID        %s %s" % ( self.MMPData.UID2, self.MMPData.UID3 ) )
        
        attrs.remove("TARGET")
        attrs.remove("TARGETTYPE")
        
        if self.MMPData.EPOCALLOWDLLDATA:
            result.append("EPOCALLOWDLLDATA")        
        attrs.remove("EPOCALLOWDLLDATA")
        
        if self.MMPData.EPOCHEAPSIZE == 0:
            attrs.remove("EPOCHEAPSIZE")
        if self.MMPData.EPOCSTACKSIZE == 0:
            attrs.remove("EPOCSTACKSIZE")
        
        attrs.remove("UID2")
        attrs.remove("UID3")
        
        attrs.remove("CAPABILITY")
        attrs.append("CAPABILITY")
        
        data = self.MMPData
        #import pdb;pdb.set_trace()
        #data.USERINCLUDE = ["."] + [ relpath(self.TargetDir, x ) for x in data.USERINCLUDE ]
        for x in xrange(len(data.USERINCLUDE) ):
            #print data.USERINCLUDE[x]
            #import pdb;pdb.set_trace()
            if not os.path.isabs( data.USERINCLUDE[x] ):
                try:
                    data.USERINCLUDE[x] = relpath(self.TargetDir, data.USERINCLUDE[x] )
                except TypeError:
                    data.USERINCLUDE[x] = "." 
                    pass # if same
                            
        #data.SYSTEMINCLUDE = [ relpath(self.TargetDir, x ) for x in data.SYSTEMINCLUDE ]
        
        order = [ "MACRO", "SYSTEMINCLUDE", "USERINCLUDE", "SOURCEPATH", "RESOURCE", "SOURCE", "LIBRARY"]
        for o in order:
            if o in attrs:
                attrs.remove(o)
        attrs = order + attrs
        
        for a in attrs:
            result.append("") # Separate sections with empty line
            
            data = getattr(self.MMPData, a)
            if type(data) == list:
                if a == "CAPABILITY":
                    #for item in data:
                    result.append( "%-11s %s" % ( "CAPABILITY", " ".join( self.MMPData.CAPABILITY ) ) )
                elif a == "SOURCE":
                    #import pdb;pdb.set_trace()
                    for s in data:
                        rpath = relpath(self.TargetDir, s )
                        result.append( "%-11s %s" % ( "SOURCE", rpath ) )
                elif a == "RESOURCE":
                    for s in data:
                        template = TEMPLATE_RESOURCE
                        if "_reg" in s.lower():
                            template = TEMPLATE_RESOURCE_REG
                        s = relpath(self.TargetDir, s )
                        res = template % {"RESOURCE" : s }
                        result.append( res )
                                                       
                else:    
                    for item in data:
                        result.append("%-11s %s" % (a, item))
            elif data:
                result.append("%-11s %s" % (a, data))
        
        result.append( "EXPORTUNFROZEN")
                                    
        self.MMPContents = "\n".join(result).replace("/", "\\")
        return self.MMPContents
    
    def Save(self):
        f = open( self.TargetPath, 'w')
        f.write( self.MMPContents )
        f.close()
    
class MMPParser:
    """Parse MMP to be built with SCons for Symbian"""
    def __init__(self, sourcefile):
        #: Path to the MMP file.
        self.Source = sourcefile
        
    def Parse(self):
        f = open(self.Source)
        lines = f.readlines()
        f.close()
        
        workingfolder = os.path.dirname(self.Source)
        sourcepath = workingfolder
        curdir = abspath(os.curdir)
        
        lines = [x for x in lines if len(x.strip()) > 0 ]        
        
        result = {}
        # initialize
        for x in KEYWORDS:
            result[x] = []
        result["epocallowdlldata"] = False # Not enabled with regular scripts either
        result["epocstacksize"].append(hex(8 * 1024))
        result["uid"] += [ None, None]
        for line in lines:                        
            parts = line.split()
            keyword = parts[0].lower()
            if keyword in KEYWORDS:
                items = result.get(keyword, [])                
                if len(parts) > 1:
                    if keyword == "source":
                        files = []
                        files = [ join(sourcepath, x) for x in parts[1:] ]
                        items += files
                    elif keyword == "library":
                        libs = [ x.lower().replace(".lib", "") for x in parts[1:] ]
                        items += libs
                    elif keyword in [ "systeminclude", "userinclude"]:
                        items += [ join(workingfolder, x) for x in parts[1:] ] 
                    else:
                        items += parts[1:]
                else:
                    if keyword == "epocallowdlldata":
                        result["epocallowdlldata"] = True
                    
                result[keyword] = items
                
            elif keyword == "sourcepath":
                sourcepath = join(sourcepath, parts[1])
                sourcepath = relpath(curdir, abspath(sourcepath))
                print "Curdir:", sourcepath
                
            elif keyword == "start":
                result["resources"] += [ join(sourcepath, parts[ - 1]) ]
                result["userinclude"] += [ sourcepath ]
        
        # Take targettype from file extension instead. TODO: special dlls.
        result["targettype"] = result["target"][0].split(".")[ - 1]
        result["target"] = ".".join(result["target"][0].split(".")[: - 1]) # Strip extension
        result["epocstacksize"] = int(result["epocstacksize"][0], 16)
        return result

if __name__ == "__main__":
    import pprint
    p = MMPParser(sys.argv[1])
    mmpdata = p.Parse()
    pprint.pprint(mmpdata)
    
    e = MMPExporter("test.mmp")
    for x in mmpdata:
        if x == "uid": continue
        setattr(e.MMPData, x.upper(), mmpdata[x])
    
    print e.Export()
    
