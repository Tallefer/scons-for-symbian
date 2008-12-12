"""PKG generation and sis creation from pkg files"""

from SCons.Script import DefaultEnvironment
import arguments
import os
import sys
from relpath import relpath

MAKESIS_EXECUTABLE = "makesis"
    
DEFAULT_PKG_TEMPLATE = """
"""

#: Use absolute path on windows but relative on linux
#: Todo: Invent more generic place and better name for this!
handle_path = os.path.abspath
    
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
    
def Makesis( pkgfile, package, installed = None, cert = None, key = None, passwd = "", env = None ):
    """
    Call makesis command line utility to create a sis package.
    
    If cert is given, key must be given.
    @param installed: Installed files( to be parsed from pkg in the future )
    @param cert: Certificate used in signing
    @param key: Key used in signing
    @param passwd: Password used in signing
    
    """
    if env is None: env = DefaultEnvironment()
    
    unsigned_package = package
    
    if installed is None:
        installed = []
    
    output_files = []
    output_files.append( package ) # Always
         
    makesis = os.path.join( arguments.EPOC32_TOOLS, MAKESIS_EXECUTABLE )
    makesis = ( "%s %s %s" % ( makesis, pkgfile, unsigned_package ) )
    env.Command( unsigned_package, installed + [pkgfile],
             makesis, ENV = os.environ )
    
    return output_files


def SignSis(target, source, cert, key, passwd = "", env = None):
    """ Call signsis command line utility to create a sis package.
    
    """
    if env is None: env = DefaultEnvironment()
    
    signsis = os.path.join( arguments.EPOC32_TOOLS, "signsis.exe" )
    signsis = ( "%s %s %s %s %s %s" % ( signsis, handle_path(source), handle_path(target), handle_path(cert), handle_path(key) ,passwd ) )
    env.Command( target, source, signsis, ENV = os.environ )
    
    return [target]
    
def GetPkgFilename( sisname ):
    "Convert sisname to pkg filename"
    return ".".join( sisname.split( "." )[: - 1] + ["pkg"] )
    
            
class PKGHandler:
    def __init__( self ):
        self.pkg_files = {}
        self.pkg_args = {}
        self.pkg_sis = {}
        
    def Package( self, package ):
        pkg = self.pkg_files.get( package, {} )
        self.pkg_files[package] = pkg        
        return pkg
    
    def PackageArgs( self, package ):
        args = self.pkg_args.get( package,
                                  { "version" : ( "1", "0", "00000" ),
                                    "appname" : package,
                                    "uid"     : "0x0"
                                  } )
        
        self.pkg_args[package] = args  
        return args
     
    def GeneratePkg( self, target = None, source = None, env = None ):
        """ SCons Command to generate PKG file
        @param target: Contains the pkg filename
        """
        
        pkgfilename = target[0].path
        package = self.pkg_sis[pkgfilename]
        #pkgfilename = GetPkgFilename( package )
        #Depends( package, pkgfilename )
        
        print "Creating pkg", pkgfilename
        #f=codecs.open( pkgfilename, 'wb', encoding="utf-16le");
        f = open( pkgfilename, 'w' )
                
        files = self.Package( package )
        pkgargs = self.PackageArgs( package )
        
        if type( pkgargs["uid"] ) != str:
            pkgargs["uid"] = hex( pkgargs["uid"] ).replace("L","")
        
        version = pkgargs["version"]
        
        header = '#{"%(appname)s"},(%(uid)s),' % ( pkgargs )
        header += '%s,%s,%s' % tuple( version )
        #header += ',TYPE=%s\n\n' % pkgargs.get( "type", "" )
        header += "\n"
        
        f.write( ";Localised package name\n" )
        f.write( header )
        
        f.write( ";Localized vendor name\n" )
        f.write( '%%{"%s"}\n\n' % pkgargs.get( "vendor", "VENDOR" ) )
        
        f.write( ';Unique Vendor name\n' )
        f.write( ':"%s"\n\n' % pkgargs.get( "vendor_id", "VENDOR" ) )
        
        ## TODO: Correct UID for UIQ    
        f.write( '[0x101F7961], 0, 0, 0, {"Series60ProductID"}\n\n' )
        keys = files.keys();keys.sort()
        for x in keys:
            t = files[x]
            # Do split in platform independent way
            t = t.replace("\\","/").split( "/" )
            if t[0] == "any":
                t[0] = "!:"
            else:
                t[0] = t[0] + ":"
            # Convert the slashes for pkg
            t = "\\".join( t ).replace( "/", "\\" )            
            
            #import pdb;pdb.set_trace()
            x = relpath( os.getcwd(), x )
            x = x.replace( "/", "\\" )
            
            f.write( '%-50s - "%s"\n' % ( '"%s"' % x, t ) )
        
        f.close()
        
