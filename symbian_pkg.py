"""PKG generation and sis creation from pkg files"""

import os
import codecs

from SCons.Script import Command, Depends

import arguments

DEFAULT_PKG_TEMPLATE = """


"""

def Makesis( pkgfile, package, installed = None, cert = None, key = None, passwd = "" ):
    """
    Call makesis command line utility to create a sis package.
    
    If cert is given, key must be given.
    @param installed: Installed files( to be parsed from pkg in the future )
    @param cert: Certificate used in signing
    @param key: Key used in signing
    @param passwd: Password used in signing
    
    """
    
    signcmd = None
    unsigned_package = package
    
    if installed is None:
        installed = []
    
    output_files = []
    output_files.append(package) # Always
        
    if cert is not None:
        if key is None:
            raise AttributeError("key must be given for certificate")
        
        signsis = " ".join( [ "signsis", package, package, cert, key, passwd] )
        unsigned_filename = "unsigned_" + unsigned_filename
        
        Command( package, unsigned_package, signsis, ENV = os.environ )
        output_files.append( unsigned_package )
    
    makesis = os.path.join( arguments.EPOC32_TOOLS, "makesis.exe" )
    makesis = ( "%s %s %s" % ( makesis, pkgfile, unsigned_package ) )
    Command( unsigned_package, installed + [pkgfile], 
             makesis, ENV = os.environ )
    
    return output_files
    
def GetPkgFilename( sisname ):
    "Convert sisname to pkg filename"
    return ".".join( sisname.split(".")[:-1] + ["pkg"] )
    
            
class PKGHandler:
    def __init__(self):
        self.pkg_files = {}
        self.pkg_args = {}
        self.pkg_sis = {}
        
    def Package(self, package):
        pkg = self.pkg_files.get( package, {} )
        self.pkg_files[package] = pkg        
        return pkg
    
    def PackageArgs(self, package ):
        args = self.pkg_args.get( package, 
                                  { "version" : ( "1","0","00000" ),
                                    "appname" : package,
                                    "uid"     : "0x0"
                                  } )
        
        self.pkg_args[package] = args  
        return args
    
    def GeneratePkg( self, target = None, source = None,  env = None ):
        
        
        pkgfilename = target[0].path
        package = self.pkg_sis[pkgfilename]
        #pkgfilename = GetPkgFilename( package )
        #Depends( package, pkgfilename )
        
        print "Creating pkg", pkgfilename
        f=codecs.open( pkgfilename, 'wb', encoding="utf-16le");
                
        files   = self.Package(package)
        pkgargs = self.PackageArgs(package)
        
        version = pkgargs["version"]
        
        header = '#{"%(appname)s"},(%(uid)s),' % ( pkgargs )
        header += '%s,%s,%s' % tuple(version)
        header += ',TYPE=%s\n\n' % pkgargs.get( "type", "SISSYSTEM" )
        
        f.write( ";Localised package name\n")
        f.write( header )
        
        f.write( ";Localized vendor name\n")
        f.write( '%%{"%s"}\n\n' % pkgargs.get( "vendor", "VENDOR" ) )
        
        f.write( ';Unique Vendor name\n' )
        f.write( ':"%s"\n\n' % pkgargs.get( "vendor_id", "VENDOR" ) )
        
        ## TODO: Correct UID for UIQ    
        f.write( '[0x101F7961], 0, 0, 0, {"Series60ProductID"}\n\n' )
        keys = files.keys();keys.sort()
        for x in keys:
            t = files[x]
            t = t.split("\\")
            if t[0] == "any":
                t[0] = "!:"
            else:
                t[0] = t[0]+":"
            t = "\\".join( t ).replace("/","\\")
            x = x.replace("/", "\\")
            f.write( '%-50s - "%s"\n' % ( '"%s"' % x, t ) )
        
        f.close()
        
