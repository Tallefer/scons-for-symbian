"""
Main args.S4S module
"""
#pylint: disable-msg=E0611
from SCons.Builder import Builder
from SCons.Script import (Command, Copy, DefaultEnvironment, Install, Mkdir, Clean, Default)
import arguments as args
from arguments import sysout, get_output_folder, EPOCROOT
from os.path import join, basename, abspath
import zipfile
import py_compile
import re
import mmp_parser
import colorizer
import gcce
import os
import symbian_pkg
import winscw
import rcomp
import textwrap
#pylint: enable-msg=E0611

__author__ = "Jussi Toivola"
__license__ = "MIT License"

# TODO: freeze # perl -S /epoc32/tools/efreeze.pl %(FROZEN)s %(LIB_DEFS)s

#: Handle to console for colorized output( and process launching )
_OUTPUT_COLORIZER = colorizer.OutputConsole()

def FinalizeSymbianScons():
  if args.ResolveInstallDirectories():
    # Set args.EPOCROOT as default target, so the stuff will be built for emulator.
    Default( args.INSTALL_EPOCROOT )
    Default( "." )

sysout( "Building", args.COMPILER, args.RELEASE )
sysout( "Defines", args.CMD_LINE_DEFINES )

# in template
# args.UID1 = 0x100039ce for exe
# args.UID1 = 0x00000000 for dll

def _create_environment( *env_args, **kwargs ):
    """Environment factory. Get correct environment for selected compiler."""
    env = None

    if args.COMPILER == args.COMPILER_GCCE:
        env = gcce.create_environment( *env_args, **kwargs )
    elif args.COMPILER == args.COMPILER_WINSCW:
        env = winscw.create_environment( *env_args, **kwargs )
    else:
        msg = "Error: Environment for '%s' is not implemented" % args.COMPILER
        raise NotImplementedError( msg )
    return env


def SymbianPackage( package, ensymbleargs = None, pkgargs = None,
                    pkgfile = None, extra_files = None, source_package = None,
                    env=None, startonboot = None,
                    pkgtemplate = None ):
    """
    Create Symbian Installer( sis ) file. Can use either Ensymble or pkg file.
    To enable creation, give command line arg: dosis=true

    @param package: Name of the package.
    @type package: str

    @param pkgargs: Arguments to args.PKG generation. Disabled if none, use empty dict for simple enable.
                    To enable signing, give at least both cert and keys, which point to the
                    respective files. passwd key can be used for password.
                    If pkgfile is not given, package name is converted to pkg extension and used instead.
                    The signed sis file gets extension args.SIGNSIS_OUTPUT_EXTENSION defined in constants.py

    @type pkgargs: dict

    @param ensymbleargs: Arguments to Ensymble simplesis.
    @type ensymbleargs: dict

    @param source_package: Use data from another package for pkg generation.
                           Equals to 'package' if None.

    @param pkgfile: Path to pkg file.
    @type pkgfile: str

    @param startonboot: Name of the executable to be started on boot
    @type startonboot: str

    @param pkgtemplate: preppy template for generating pkg.
                        'pkgargs' contains the available variables in template.
    @type pkgtemplate: str

    @param extra_files: Copy files to package folder and install for simulator( to args.SIS with Ensymble only )
    """
    # Skip processing to speed up help message
    if args.HELP_ENABLED: return
    FinalizeSymbianScons()
    if not env:
        env = DefaultEnvironment()

    if ensymbleargs is not None and pkgargs is not None:
        raise ValueError( "Trying to use both Ensymble and args.PKG file. Which one do you really want?" )
    else:
        if ensymbleargs is None:
            ensymbleargs = {}

    if source_package is None:
        source_package = package

    if extra_files is not None:
        pkg = PKG_HANDLER.Package( package )

        for target, source in extra_files:
            pkg[source] = target

            ToPackage( DefaultEnvironment(), None, package, target, source, toemulator = False )

            if args.COMPILER == args.COMPILER_WINSCW:
                Install( join( args.FOLDER_EMULATOR_C, target ), source )

    def create_pkg_file( pkgargs ):

        if pkgargs is None:
            pkgargs = {}

        PKG_HANDLER.PackageArgs( package ).update( pkgargs )
        PKG_HANDLER.pkg_sis[pkgfile] = source_package
        PKG_HANDLER.pkg_template[pkgfile] = (pkgtemplate)

        Command( pkgfile, PKG_HANDLER.pkg_files[package].keys(),
                        PKG_HANDLER.GeneratePkg, ENV = os.environ )

        # Set deps
        files = PKG_HANDLER.Package( package )
        files_value = env.Value(files)
        env.Depends( pkgfile, files_value )

        pkgargs = PKG_HANDLER.PackageArgs( package )
        pkgargs_value = env.Value(pkgargs)
        env.Depends( pkgfile, pkgargs_value )

        if pkgtemplate is not None:
            if os.path.isfile(pkgtemplate):
                env.Depends( pkgfile, pkgtemplate )
            else:
                template_value = env.Value(pkgtemplate)
                env.Depends( pkgfile, template_value )
    # Create pkg file
    if args.COMPILER != args.COMPILER_WINSCW:
        if pkgargs is not None:
            if pkgfile is None:
                pkgfile = symbian_pkg.GetPkgFilename(package)
            create_pkg_file( pkgargs )

    def __create_boot_up_resource( target, source, env):
        """Create boot up resource file"""
        # Notice that the resource must args.ALWAYS be copied to args.C:
        template = r"""
        #include <startupitem.rh>

        args.RESOURCE STARTUP_ITEM_INFO startexe
        {
            executable_name = "c:\\sys\\bin\\%(APPNAME)s";
            recovery = args.EStartupItemExPolicyNone;
        }
        """

        content = template % { "APPNAME" : startonboot }

        content = textwrap.dedent(content)

        f = open( target[0].path, 'w' )
        f.write(content)
        f.close()


    def _makeBootUpResource( ):
        """Create resource file for starting executable on boot and compile it"""

        if not startonboot: return

        output_folder = get_output_folder( args.COMPILER, args.RELEASE, startonboot, "rss" )

        uid = PKG_HANDLER.PackageArgs(package)["uid"]

        uid = uid.replace("0x", "" )

        rssfilepath = join( output_folder, "[%s].rss" % uid )
        env.Command( rssfilepath, None, __create_boot_up_resource )

        rscfilepath = join( output_folder, "[%s].rsc" % uid )
        rsgfilepath = join( output_folder, "%s.rsg" % uid )

        rcomp.RComp( env, rscfilepath, rsgfilepath,
                             rssfilepath,
                             "-v -m045,046,047",
                             args.SYSTEM_INCLUDES,
                             [args.PLATFORM_HEADER],
                             [ 'LANGUAGE_SC'])

        ToPackage(env, { "C" : ".*[.](rsc)" }, package,
                  "private/101f875a/import/", rscfilepath, toemulator=False)

        if args.COMPILER == args.COMPILER_WINSCW:
            env.Install( join( args.INSTALL_EPOC32_DATA ), rscfilepath )

    #---------------------------------------------------- Create boot up args.API resource
    _makeBootUpResource()

    def create_install_file( installed ):
        """Utility for creating an installation package using Ensymble or args.PKG template"""
        from ensymble.cmd_simplesis import run as simplesis

        if pkgfile is None and args.ENSYMBLE_AVAILABLE:

            def ensymble( env, target = None, source = None ): #IGNORE:W0613
                """ Wrap ensymble simplesis command. """
                cmd = []
                for x in ensymbleargs:
                    cmd += [ "%s=%s" % ( x, ensymbleargs[x] ) ]

                cmd += [ join( args.PACKAGE_FOLDER, package ), package ]

                try:
                    print "Running simplesis:" + str( cmd )
                    simplesis( "scons", cmd )
                except Exception, msg:#IGNORE:W0703
                    import traceback
                    traceback.print_exc()
                    return str( msg )

            Command( package, installed, ensymble, ENV = os.environ )

        elif pkgfile is not None:
            result = symbian_pkg.Makesis( pkgfile,
                                          package,
                                          installed = PKG_HANDLER.pkg_files[package].keys() )

            cert = pkgargs.get("cert", None )
            key  = pkgargs.get("key", None)
            if cert and key:
                sisx = package.split(".")
                sisx = ".".join( sisx[:-1] ) + constants.SIGNSIS_OUTPUT_EXTENSION
                env.Depends( sisx, package )
                env.Depends( sisx, PKG_HANDLER.pkg_files[package].keys() + result )

                passwd = pkgargs.get( "passwd", "" )
                result.append( symbian_pkg.SignSis( sisx, package, pkgargs["cert"], pkgargs["key"], passwd ) )

    if args.DO_CREATE_SIS:
        return create_install_file( PKG_HANDLER.Package(package).keys() )

def SymbianHelp( source, uid, env = None ):
    """ Generate help files for Context Help
    @param source: Help project file .cshlp"
    @uid: args.UID of the application.

    @return: generated .hlp and .hrh files.
    @rtype: 2-tuple
    """
    import cshlp
    FinalizeSymbianScons()
    if env is None:
        env = DefaultEnvironment()

    helpresult = cshlp.CSHlp( DefaultEnvironment(), source, uid )
    return helpresult

def _is_python_file( filepath ):
    """ Check if file is a python file """
    lower = filepath.lower()
    for x in [ ".py", ".pyc", ".pyo" ]:
        if lower.endswith( x ):
            return True
    return False

def _zipfile(target,source,env):
    """ """
    zippath = target[0].abspath

    z = zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED)
    files = args.ZIP_FILES[zippath]["files"]
    print( "Install files into archive: %s" % (zippath) )
    for s,t in files:
        print s,t
        z.write( s, t )
    z.close()

ZIP_FILES = {}
def File2Zip(zipfilepath, source, arcpath, env = None ):
    """ Add a file into a zip archive """

    files = []
    FinalizeSymbianScons()
    if env is None:
        env = DefaultEnvironment()

    zipfilepath = abspath( zipfilepath )

    if zipfilepath not in args.ZIP_FILES:
        #import pdb;pdb.set_trace()
        # Create command
        args.ZIP_FILES[zipfilepath] = { "files" : files }
        env.Command( zipfilepath, "", _zipfile)
    else:
        files = args.ZIP_FILES[zipfilepath]["files"]

    env.Depends( zipfilepath, source )
    files.append( (source, arcpath) )

    return zipfilepath

def _py2pyc(target,source,env):
    """ Compile python sources to .pyc using selected python compiler """
    # Can strip docstrings and enable optimizations only through command line
    # But no matter since we could be on Py 2.6 but 2.5 is needed
    cmd = r"""%s -OO -c "import py_compile as p;""" % args.PYTHON_COMPILER

    files = zip(source,target )
    for py, pyc in files:
        cmd += "p.compile(r'%s',cfile=r'%s', dfile='%s');" % ( py, pyc, basename(pyc.abspath) )

    os.system( cmd )
    return 0

def Python2ByteCode( source, target = ".pyc", env = None ):
    """ Utility to compile Python source into a byte code """

    FinalizeSymbianScons()
    if target in [".pyc", ".pyo"]:
        target = source.replace(".py", target)

    if env is None:
        env = DefaultEnvironment()

    cmd = env.Command( [target], [source], _py2pyc)

    return target

#: Holds the file source->target paths for each package
#: This information is be used to generate the pkg file.
PKG_HANDLER = symbian_pkg.PKGHandler()

def ToPackage( env = None,     package_drive_map = None,
               package = None, target = None,
               source = None,  toemulator = True,
               dopycompile = ".pyc", pylibzip = None ):
    """Insert file into package.
    @param env: Environment. DefaultEnvironment() used if None.

    @param package_drive_map: Regular expression drive mapping. You can also
                              tell the path directly on 'target', but do not
                              use this then.
    @rtype package_drive_map: dict

    @param package: Package(.sis) to be used. Nothing done, if None.
    @param target: Folder on device
    @param source: Source path of the file
    @param toemulator: Flag to determine if the file is installed for args.SDK's emulator.
    @param dopycompile: Compile .py sources into .pyc or .pyo
                        Can be a full path.
                        Set to None to disable byte-code compilation.
                        arguments.PYTHON_COMPILER must be set to enable.
                        This can be used to compile only certain files.
    @param pylibzip: If defined and source is a Python file( .py, .pyc, .pyo ), it is archived into
                     the given file. The zip file is added automatically to pkg.
                     The target path must be in subdirectory of the pylibzip.
                     The file gets the remaining path inside the zip.
                     For example:
                         target   = c:\libs\testing\test.py
                         pylibzip = c:\libs\testing.zip

                         The zip is created to the location given in pylibzip.
                         The target is stored in the zip with path: testing\test.py
    """
    for attr in ["target", "source"]:
        notnone = locals()[attr]
        if notnone is None:
            raise AttributeError( "Error: '%s' is None." % attr )

    FinalizeSymbianScons()
    if env is None:
        env = DefaultEnvironment()

    # Just skip this then
    if package is None:
        return

    # Convert python source into a byte code
    if dopycompile and args.PYTHON_COMPILER and source.endswith(".py"):
        source = Python2ByteCode( source, target = dopycompile )

    # args.WARNING: Copying to any/c/e is custom Ensymble feature of PyS60 args.CE
    drive = ""

    # Gets reference.
    pkg = PKG_HANDLER.Package( package )

    if package_drive_map is not None:

        # Goes to any by default
        drive = "any"
        filename = os.path.basename( source )

        for d in package_drive_map:
            regexp = package_drive_map[d]
            if type( regexp ) == str:
                regexp = re.compile( regexp )
                package_drive_map[d] = regexp

            if regexp.match( filename ):
                drive = d
                break

    pkgsource = join( args.PACKAGE_FOLDER, package, drive, target, basename( source ) )
    # Handle Python library zipping
    if pylibzip is not None and _is_python_file(source):
        fullzippath = abspath( join( args.PACKAGE_FOLDER, package, drive, pylibzip ) )
        zipfolder   = dirname( fullzippath )
        arcpath = abspath( pkgsource )
        arcpath = arcpath.replace( zipfolder, "" )

        pkgsource = File2Zip(fullzippath, source, arcpath )

        # Add to pkg generator
        pkgsource = fullzippath

        if drive == "":
            pkg[pkgsource] = join( "any", pylibzip )
        else:
            pkg[pkgsource] = join( drive, pylibzip )

        if toemulator and args.COMPILER == args.COMPILER_WINSCW:
            env.Install( join( args.FOLDER_EMULATOR_C, dirname(pylibzip) ), pkgsource )

        return fullzippath

    else:
        # Add to pkg generator
        pkg[pkgsource] = join( drive, target, basename( source ) )

        env.Depends( symbian_pkg.GetPkgFilename( package ), join( args.PACKAGE_FOLDER, package, pkg[pkgsource] ) )

        package_target = join( args.PACKAGE_FOLDER, package, drive, target )
        cmd = env.Install( package_target, source )
        Clean( cmd,join( args.PACKAGE_FOLDER, package) )

        if drive == "":
            pkg[pkgsource] = join( "any", target, basename( source ) )

        if toemulator and args.COMPILER == args.COMPILER_WINSCW:
            env.Install( join( args.FOLDER_EMULATOR_C, target ), source )

    return target

def SymbianProgram( target, targettype = None, #IGNORE:W0621
                    sources = None, includes = None,
                    libraries = None, user_libraries = None,
                    uid2 = None, uid3 = None,
                    sid = None,
                    definput = None, capabilities = None,
                    icons = None, resources = None,
                    rssdefines = None,
                    defines = None,
                    help = None,
                    sysincludes = None,
                    mmpexport = None,
                    elf2e32_args = None,
                    win32_libraries = None,
                    win32_subsystem = None,
                    # Sis stuff
                    package = "",
                    package_drive_map = None,
                    extra_depends = None,
                    **kwargs):
    """
    Main function for compiling Symbian applications and libraries.
    Handles the whole process of source and resource compiling
    and args.SIS installer packaging.

    @param target: Name of the module without file extension.
                    If the name ends with .mmp, the .mmp file is used for
                    defining the module.
    @type target: str

    @param targettype: Type of the program. One of args.L{arguments.TARGETTYPES}.
    @type targettype: str

    @param sources:     List of paths to sources to compiler
    @type sources: list

    @param includes:    List of folders to be used for finding user headers.
    @type includes: list

    @param sysincludes:  List of folders to be used for finding system headers.
    @type sysincludes: list

    @param sid: Secure id. Defaults to uid3.
    @type sid: str/hex

    @param mmpexport: Path to the generated args.MMP
    @type mmpexport: str

    @param definput:    Path to .def file containing frozen library entrypoints.
    @type definput: str

    @param icons:       List of icon files to compile
    @type icons: list

    @param resources:   List of paths to .rss files to compile.
                        See rssdefines param for giving args.CPP macros.
    @type resources: list

    @param libraries: Used libraries.
    @type libraries: list

    @param capabilities: Used capabilities. Default: args.FREE_CAPS
    @type capabilities: list

    @param defines: Preprocess definitions.
    @type defines: list

    @param rssdefines: Preprocessor definitions for resource compiler.
    @type rssdefines: list

    @param elf2e32_args: Extra arguments to elf2e32 Symbian Post Linker
    @param elf2e32_args: str

    @param win32_libraries: Win32 libraries to link against (default None)
    @param win32_libraries: list of str

    @param win32_subsystem: Subsystem for the resulting binary (default windows)
    @param win32_subsystem: str, either "windows" or "console"

    @param package:       Path to installer file. If given, an installer is automatically created.
                          The files are copied to args.L{arguments.PACKAGE_FOLDER} and
                          Ensymble is used to create an installer package with simplesis command.

    @type package: str

    @param package_drive_map: For custom Ensymble with drive destination support.
                              Map files to drives by using regular expressions.
                              For example, to map .mif and .rsc files to args.C drive:
                                package_drive_map = { "C" : ".*[.](mif|rsc)" }
                              The files goes to 'any' folder by default.

                              Disabled if None. Normal Ensymble behavior used.

    @type  package_drive_map: dict

    @param extra_depends: External files which must be built prior the app
    @type extra_depends: list

    @param kwargs: Additional keywords passed to selected compiler environment
                   factory: args.L{gcce.create_environment}, args.L{winscw.create_environment}

    @return: Last Command. For setting dependencies.

    """

    # Transforms arguments into keywords
    FinalizeSymbianScons()
    kwargs.update( locals() )

    handler = SymbianProgramHandler( **kwargs )
    return handler.Process()

class SymbianProgramHandler(object):
    """Internal class for handling the SymbianProgram function call"""
    def __init__(self, **kwargs):

        FinalizeSymbianScons()
        #: Compiler environment
        self._env = None
        self.target = None
        self.extra_depends = None
        self.sysincludes = None
        self.origsources = [] # Sources not altered for BuildDir
        self.origlibraries = []
        # Store the keywords as instance attributes
        for arg in kwargs:
            setattr( self, arg, kwargs[arg] )

        #: Folder for compiler releasables.
        self.output_folder = ""


    def _isComponentEnabled(self):
        """Is the component enabled."""
        component_name = ".".join( [ self.target, self.targettype] ).lower()

        if args.COMPONENTS is not None:
            inlist = ( component_name in args.COMPONENTS )
            if inlist and not args.COMPONENTS_EXCLUDE:
                pass
            elif not inlist and args.COMPONENTS_EXCLUDE:
                pass
            else:
                print "Ignored Symbian component %s(%s)" % ( component_name, self.uid3 )
                return False

        print "Getting dependencies for %s(%s)" % ( component_name, self.uid3 )

        return True

    def _doConvertIcons( self, env, target, source):

        # Creates 32 bit icons
        convert_icons_cmd = ( args.EPOCROOT + r'epoc32/tools/mifconv "%s" /c32 "%s"' ).replace( "\\", "/" )

        if os.name == 'nt':
            source_icon = source[0].abspath
            target_icon = target[0].abspath


            # Copy the file to current drive. This fixes also issues with some(old)
            # versions of mifconv not accepting drive letter in paths
            if not os.path.exists( "/tmp"):
                os.mkdir("/tmp")

            import tempfile
            fileid, mifpath = tempfile.mkstemp( suffix=".mif", dir="/tmp" )
            if ":" in mifpath:
                mifpath = mifpath.split(":")[-1]
            cmd = convert_icons_cmd % ( mifpath, abspath(source_icon) )

            # TODO: Use colorizer
            print( cmd )
            err = os.system( cmd )

            import shutil
            print( "scons: Copying temporary '%s' to '%s'" % (mifpath, target_icon ) )
            shutil.copyfile( mifpath, target_icon )

            # Close so we can remove it
            os.close(fileid)
            os.remove(mifpath)
        else:
            from relpath import relpath
            source_icon = relpath(os.getcwd(), source[0].tpath)
            target_icon = target[0].tpath

            cmd = convert_icons_cmd % ( target_icon, source_icon )
            #import pdb;pdb.set_trace()
            # TODO: Use colorizer
            print( cmd )
            err = os.system( cmd )

        return err

    def _handleIcons(self):
        """Sets self.converted_icons"""
        #TODO: Create main interface SymbianIcon for generic icons

        # Copy for emulator at the end using this list, just like binaries.
        self.converted_icons = []

        if self.icons is None:
            return

        sdk_data_resource = args.EPOCROOT + r"epoc32/DATA/Z/resource/apps/%s"
        sdk_resource = join( args.EPOCROOT + r"epoc32", "release", args.COMPILER,
                         args.RELEASE, "z", "resource", "apps", "%s" )

        icon_target_path = join( self.output_folder, "%s_aif.mif" )
        icon_targets = [] # Icons at args.WINSCW/...
        sdk_icons = [] # Icons at /epoc32
        copyres_cmds = [] # Commands to copy icons from args.WINSCW/ to /epoc32

        for x in self.icons:

            # Accepts 2-tuple, first is the source, second: resulting name
            tmp = ""
            icon_name = x
            source_icon = x

            if type( x ) == tuple:
                icon_name = x[1]
                source_icon = x[0]
            else:
                # Strip the extension from the file name
                icon_name = ".".join(icon_name.split(".")[:-1])
            tmp = icon_target_path % ( icon_name )
            icon_targets.append( tmp )

            icon_name = abspath( icon_name )
            source_icon = abspath( source_icon )

            # Execute convert
            if os.name == "posix":
                # Linux's mifconv fails with absolute paths without
                source_icon = "/"+source_icon

            self._env.Command( tmp, source_icon, self._doConvertIcons)

            iconfilename = os.path.basename( tmp )
            # TODO: Use Install instead. Copy does not seem to work if there are changes.
            sdk_target = sdk_resource % iconfilename
            copyres_cmds.append( Copy( sdk_target, tmp ) )
            sdk_icons.append( sdk_target )

            sdk_target = sdk_data_resource % iconfilename
            copyres_cmds.append( Copy( sdk_target, tmp ) )
            sdk_icons.append( sdk_target )

            ToPackage( self._env, self.package_drive_map, self.package,
                join( "resource", "apps" ),
                tmp, toemulator = False )

        self._env.Command( sdk_icons, icon_targets, copyres_cmds )
        self.converted_icons = sdk_icons

    def _copyResultBinary(self):
        """Copy the linked binary( exe, dll ) for emulator
        and to resultables folder.
        """

        env = self._env
        installfolder = [ ]

        if self.targettype != args.TARGETTYPE_LIB:
            installfolder += ["sys", "bin" ]
        else: # Don't install libs to device.
            installfolder += ["lib"]

        installfolder = join( *installfolder )
        #Mkdir( installfolder )

        #installpath = join( installfolder, "%s.%s" % ( self.target, self.targettype ) )

        # Combine with installfolder copying.
        #TODO: Not needed anymore since args.EPOCROOT is default target.
        postcommands = []
        copysource = self._result_template % ( "." + self.targettype )
        target_filename = self.target + "." + self.targettype
        sdkpath = join( args.SDKFOLDER, target_filename )

        installed = []
        if args.COMPILER == args.COMPILER_WINSCW:
            # Copy to args.SDK to be used with simulator
            postcommands.append( Copy( sdkpath, copysource ) )
            installed.append( sdkpath )

        if self.output_libpath is not None:
            if (  args.COMPILER == args.COMPILER_WINSCW and
                  self.targettype != args.TARGETTYPE_LIB) or \
                args.COMPILER == args.COMPILER_GCCE and self.targettype == args.TARGETTYPE_LIB :

                s, t = self.output_libpath
                postcommands.append( Copy( t, s ) )
                installed.append( t )

        if len(installed) > 0:
            env.Command( installed, #IGNORE:W0612
                         copysource,
                         postcommands )

        if self.targettype != args.TARGETTYPE_LIB:
            ToPackage( env, self.package_drive_map, self.package,
                    installfolder,
                    copysource, toemulator = False )
        else:  # Don't install libs to device.
            ToPackage( env, None, None,
                    "lib",
                    copysource, toemulator = False )

        return installed

    #TODO: Create main interface SymbianResource for special resource compiling
    def _convertResources( self ):
        """
        Compile resources and copy for sis creation and for simulator.
        Sets self.resource_headers, self.converted_resources.
        .RSC
            -> /epoc32/DATA/Z/resource/apps/
            -> /epoc32/release/winscw/udeb/z/resource/apps/
        _reg.RSC
            -> epoc32/release/winscw/udeb/z/private/10003a3f/apps/
            -> epoc32/DATA/Z/private/10003a3f/apps/
        .RSG     -> epoc32/include/
        """

        self.converted_resources = []
        self.resource_headers    = []

        if self.resources is not None:
            # Make the resources dependent on previous resource
            # Thus the resources must be listed in correct order.
            prev_resource = None

            for rss_path in self.resources:
                if type(rss_path) != str:
                    #Assuming File type then
                    rss_path = rss_path.abspath
                    #import pdb;pdb.set_trace()

                rss_notype = ".".join( os.path.basename( rss_path ).split( "." )[: - 1] ) # ignore rss
                converted_rsg = join( self.output_folder, "%s.rsg" % rss_notype )
                converted_rsc = join( self.output_folder, "%s.rsc" % rss_notype )
                self.converted_resources.append( converted_rsc )

                result_paths = [ ]
                copyres_cmds = [ ]

                res_compile_command = rcomp.RComp( self._env, converted_rsc, converted_rsg,
                             rss_path,
                             "-m045,046,047",
                             self.sysincludes + self.includes,
                             [args.PLATFORM_HEADER],
                             self.rssdefines )

                self._env.Depends( res_compile_command, self.converted_icons )

                installfolder = []
                if rss_notype.endswith( "_reg" ):
                    installfolder.append( join( "private", "10003a3f", "import", "apps" ) )
                else:
                    installfolder.append( join( "resource", "apps" ) )
                installfolder = os.path.join( *installfolder )

                rsc_filename = "%s.%s" % ( rss_notype, "rsc" )
                # Copy to sis creation folder
                ToPackage( self._env, self.package_drive_map, self.package,
                           installfolder, converted_rsc, toemulator = False )

                includefolder = args.INSTALL_EPOC32_INCLUDE

                # Copy to /epoc32/include/
                self._env.Install( includefolder, converted_rsg )#IGNORE:E1101
                includepath = join( includefolder, "%s.%s" % ( rss_notype, "rsg" ) )

                # Add created header to be added for build dependency
                self.resource_headers.append( includepath )

                # _reg files copied to /epoc32/DATA/Z/private/10003a3f/apps/ on simulator
                if args.COMPILER == args.COMPILER_WINSCW:
                    if "_reg" in rss_path.lower():
                        self._env.Install( join( args.INSTALL_EPOC32_DATA, "Z", "private","10003a3f","apps"), converted_rsc )
                        self._env.Install( join( args.INSTALL_EPOC32_RELEASE, "Z", "private","10003a3f","apps"), converted_rsc )
                        self._env.Install( join( args.INSTALL_EPOC32_DATA, "Z",
                                                "private","10003a3f","import", "apps"), converted_rsc )
                        self._env.Install( join( args.INSTALL_EPOC32_RELEASE,
                                                "Z", "private","10003a3f", "import", "apps"), converted_rsc )

                    else: # Copy normal resources to resource/apps folder
                        self._env.Install( join( args.INSTALL_EPOC32_DATA, "Z", "resource","apps"), converted_rsc )
                        self._env.Install( join( args.INSTALL_EPOC32_RELEASE, "Z", "resource", "apps"), converted_rsc )

                # Depend on previous. TODO: Use args.SCons Preprocessor scanner.
                if prev_resource is not None:
                    self._env.Depends( rss_path, prev_resource )
                prev_resource = includepath

    def _handleGCCEBuild(self):
        env = self._env
        output_lib   = ( self.targettype in args.DLL_TARGETTYPES )
        elf_dll_path = self._result_template % ( "._elf_" + self.targettype )
        resultables  = [ elf_dll_path  ]

        if output_lib:
            libname = self.target + ".dso"
            self.output_libpath = ( args.INSTALL_EPOCROOT + r"epoc32/release/%s/%s/%s" % ( "armv5", "lib", libname ) )

        build_prog = None
        if self.targettype != args.TARGETTYPE_LIB:
            build_prog = self._env.Program( resultables, self.sources )#IGNORE:E1101

            # Depend on the libs
            for libname in self.libraries:
                env.Depends( build_prog, libname )

            # Mark the lib as a resultable also
            resultables = [ self._result_template % ( "" ) ]
            if output_lib:
                resultables.append( self.output_libpath )

            # Create final binary and lib/dso
            env.Elf( resultables, elf_dll_path )#IGNORE:E1101

            env.Install( args.INSTALL_EPOCROOT + r"epoc32/release/gcce/%s" % ( args.RELEASE ),
                         ".".join( [resultables[0], self.targettype] ) )
        else:
            build_prog = env.StaticLibrary( self._result_template % ".lib" , self.sources )#IGNORE:E1101
            self.output_libpath = ( self._result_template % ".lib",
                                    args.INSTALL_EPOCROOT + r"epoc32/release/armv5/%s/%s.lib" % ( args.RELEASE, self.target ) )

        return build_prog

    # TODO: Move to winscw.py
    def _createUIDCPP( self, target, source, env ):#IGNORE:W0613
        """Create .UID.CPP for simulator"""
        template = ""
        capabilities = winscw.make_capability_hex( self.capabilities )
        if self.targettype == args.TARGETTYPE_EXE:
            template = winscw.TARGET_UID_CPP_TEMPLATE_EXE % { "UID3": self.uid3,
                                                              "SID" : self.sid,
                                                              "CAPABILITIES": capabilities }
        else:
            template = winscw.TARGET_UID_CPP_TEMPLATE_DLL % { "CAPABILITIES": capabilities }

        f = open( target[0].path, 'w' );f.write( template );f.close()

        return None

    def _handleWINSCWBuild(self):
        # Compile sources ------------------------------------------------------
        env = self._env

        if self.targettype != args.TARGETTYPE_LIB:
            # Create <target>.UID.CPP from template---------------------------------
            uid_cpp_filename = self._result_template % ".UID.cpp"
            #self._createUIDCPP( [env.File( uid_cpp_filename)], None, env )

            # TODO: Move to winscw.py
            bld = Builder( action = self._createUIDCPP,
                          suffix = '.UID.cpp',
                          caps = self.capabilities )
            env.Append( BUILDERS = {'CreateUID' : bld} )
            env.CreateUID( uid_cpp_filename, self.sources )#IGNORE:E1101

            # uid.cpp depends on the value of the capabilities
            #import args.SCons.Node.Python
            caps_value = env.Value(self.capabilities)
            env.Depends( uid_cpp_filename, caps_value )

            # We need to include the args.UID.cpp also
            self.sources.append( uid_cpp_filename )

        # Compile the sources. Create object files( .o ) and temporary dll.
        output_lib = ( self.targettype in args.DLL_TARGETTYPES )
        temp_dll_path = self._result_template % ( "._tmp_" + self.targettype )
        resultables = [ temp_dll_path ]

        if output_lib:
            # No libs from exes
            libname = self.target + ".lib"
            resultable_path = self._result_template % "._tmp_lib"
            resultables.append( resultable_path )
            #resultables.append( self._result_template % ".inf" )
            self.output_libpath = ( self._result_template % ".lib",
                                join( args.INSTALL_EPOC32_RELEASE, libname ) )

        if self.targettype != args.TARGETTYPE_LIB:
            build_prog = env.Program( resultables, self.sources )#IGNORE:E1101
            # Depends on the used libraries. This has a nice effect since if,
            # this project depends on one of the other projects/components/dlls/libs
            # the depended project is automatically built first.
            env.Depends( build_prog, [ join( args.EPOC32_RELEASE, libname ) for libname in self.libraries] )
            env.Depends( build_prog, [ join( args.INSTALL_EPOC32_RELEASE,
                                            libname ) for libname in self.user_libraries] )

        else:
            build_prog = env.StaticLibrary( self._result_template % ".lib" , self.sources )#IGNORE:E1101
            self.output_libpath = ( self._result_template % ".lib",
                                join( args.INSTALL_EPOC32_RELEASE, "%s.lib" % ( self.target ) ) )

        if output_lib and self.targettype != args.TARGETTYPE_LIB:
            # Create .inf file
            definput = self.definput
            if definput is not None:# and os.path.exists(definput):
                definput = '-Frzfile "%s" ' % definput
            else:
                definput = ""

            tmplib  = self._result_template % "._tmp_lib"
            inffile = '-Inffile "%s" ' % ( self._result_template % ".inf" )
            defout  = ( self._result_template % '.def' )
            # Creates def file
            makedef = r'perl -S %%EPOCROOT%%epoc32/tools/makedef.pl -absent __E32Dll %s %s "%s"' % \
                    ( inffile, definput, defout )

            action = "\n".join( [
                # Creates <target>.lib
                'mwldsym2.exe -S -show only,names,unmangled,verbose -o "%s" "%s"' % ( self._result_template % ".inf", self._result_template % "._tmp_lib" ),
                makedef
                 ] )

            defbld = Builder( action = action,
                              ENV = os.environ )
            env.Append( BUILDERS = {'Def' : defbld} )
            env.Def( defout, tmplib )

        # args.NOTE: If build folder is changed this does not work anymore.
        # List compiled sources and add to dependency list
        object_paths = [ ".".join( x.split( "." )[: - 1] ) + ".o" for x in self.sources ] #IGNORE:W0631

        # Sources depend on the headers generated from .rss files.
        env.Depends( object_paths, self.resource_headers )

        # Get the lookup folders from source paths.
        object_folders = [ os.path.dirname( x ) for x in object_paths ]

        # Needed to generate the --search [source + ".cpp" -> ".o",...] param
        objects = [ os.path.basename( x ) for x in object_paths ]
        objects = " ".join( objects )

        libfolder = "%EPOCROOT%epoc32/release/winscw/udeb/"
        libs = [ libfolder + x for x in self.libraries] + [
            join(args.INSTALL_EPOC32_RELEASE, x) for x in self.user_libraries ]
        win32_libs = self.win32_libraries or []
        win32_subsystem = self.win32_subsystem or "windows"

        if self.targettype in args.DLL_TARGETTYPES and self.targettype != args.TARGETTYPE_LIB:

            env.Command( self._result_template % ( "." + self.targettype ), [ temp_dll_path, self._result_template % ".def" ],
            [
                " ".join( [
                            'mwldsym2 -msgstyle gcc',
                            '-stdlib %EPOCROOT%epoc32/release/winscw/udeb/edll.lib -noentry',
                            '-shared -subsystem ' % win32_subsystem,
                            '-g %s' % " ".join( libs ),
                            ' %s' % " ".join( win32_libs ),
                            '-o "%s"' % temp_dll_path,
                            '-f "%s"' % ( self._result_template % ".def" ),
                            '-implib "%s"' % ( self._result_template % ".lib" ),
                            '-addcommand "out:%s.%s"' % ( self.target, self.targettype ),
                            '-warnings off',
                            '-l %s' % " -l ".join( set( object_folders ) ),
                            '-search ' + objects,
                          ]
                        )
            ]
            )
        elif self.targettype == args.TARGETTYPE_EXE:
            env.Command( self._result_template % ".exe", temp_dll_path,
                [
                " ".join( [ 'mwldsym2',
                            '-msgstyle gcc',
                            '-stdlib %EPOCROOT%epoc32/release/winscw/udeb/eexe.lib',
                            '-m "?_E32Bootstrap@@YGXXZ"',
                            '-subsystem %s' % win32_subsystem,
                            '-g %s' % " ".join( libs ),
                            ' %s' % " ".join( win32_libs ),
                            '-o "$TARGET"',
                            '-noimplib',
                            '-l %s' % " -l ".join( set( object_folders ) ),
                            '-search ' + objects,
                          ]
                        )
                ]
            )
            self.output_libpath = ( self._result_template % ".exe", join( args.INSTALL_EPOC32_RELEASE, "z", "sys", "bin", "%s.exe" % ( self.target ) ) )

        return build_prog

    def _handleHelp(self):
        if not self.help:
            return

        helpresult = SymbianHelp( self.help, self.uid3, env = self._env )
        #if args.COMPILER == args.COMPILER_WINSCW:
            #self._env.Install( join( args.FOLDER_EMULATOR_C, "resource", "help" ), helpresult[0] )#IGNORE:E1101

        ToPackage( self._env, self.package_drive_map, self.package,
                    join( "resource", "help" ),
                    helpresult[0] )
        #
        self.extra_depends.extend( helpresult )

    def _importMMP(self):
        import mmp_parser

        p = mmp_parser.MMPParser( self.target )
        data = p.Parse()

        #pylint: disable-msg=W0201
        self.target = data["target"]
        self.targettype = data["targettype"]
        self.sources = data["source"]
        self.includes = data["systeminclude"] + data["userinclude"]
        self.resources = data["resources"]
        self.libraries = data["library"]
        self.uid2 = data["uid"][0]
        self.uid3 = data["uid"][1]

        # Allow override in args.SConstruct
        if self.capabilities is None:
            self.capabilities = data["capability"]

        # Allow override in args.SConstruct
        if self.rssdefines is None:
            self.rssdefines = data["macro"][:]

        self.defines       = data["macro"][:]
        self.allowdlldata  = data["epocallowdlldata"]
        self.epocstacksize = data["epocstacksize"]
        #pylint: enable-msg=W0201

    def Process(self):

        # Skip processing to speed up help message
        if args.HELP_ENABLED: return

        if self.target.lower().endswith( ".mmp" ):
            self._importMMP()

        # After mmp import
        self.output_folder = get_output_folder( args.COMPILER, args.RELEASE, self.target, self.targettype )

        if self.includes is None:
            self.includes = []

        if self.defines is None:
            self.defines = []

        self.defines = self.defines[:] # Copy

        if self.extra_depends is None:
            self.extra_depends = []

        if self.sysincludes is None:
            self.sysincludes = []

        self.sysincludes.extend( args.SYSTEM_INCLUDES )

        if self.help:
        # Adds the .hrh file to include path
            self.includes.append( os.path.dirname( self.help ) )

        if self.libraries is None:
            self.libraries = []
        if self.user_libraries is None:
            self.user_libraries = []
        # Copied to avoid modifying the user's list
        self.libraries      = self.libraries[:]
        self.user_libraries = self.user_libraries[:]
        self.origlibraries  = self.libraries[:]

        if args.CMD_LINE_LIBS is not None:
            self.libraries.extend( args.CMD_LINE_LIBS )

        if self.capabilities is None:
            self.capabilities = args.CAPS_SELF_SIGNED

        # Handle args.UIDs
        if self.uid2 is None:
            if self.targettype == args.TARGETTYPE_EXE:
                self.uid2 = "0x100039ce"
            else:
                self.uid2 = "0x0"

        if self.uid3 is None:
            self.uid3 = "0x0"
        elif type(self.uid3) != str:
            self.uid3 = hex(self.uid3)[:-1]

        if not self.sid:
            self.sid = self.uid3
        elif type(self.sid) != str:
            self.sid = hex(self.sid)[:-1]

        # Add macros to ease changing application args.UID
        self.uiddefines = [
            "__UID3__=%s" % self.uid3
        ]

        self.defines.extend( self.uiddefines )

        if self.rssdefines is None:
            self.rssdefines = []
        self.rssdefines.append( r'LANGUAGE_SC' )
        self.rssdefines.extend( self.uiddefines )

        # Check if this Symbian component is enabled
        if not self._isComponentEnabled():
            return None

        # ???: args.SCons is able to compile sources with self.output_folder
        #      but not able to detect if the files have changed without
        #      explicit dependency!! Without self.output_folder the resulting object
        #      files are stored in the same folder as sources causing cross compiling
        #      to fail.
        # Seems to work again without. What is going on here? Updated scons 1.1?
        #self.extra_depends.extend( self.sources )

        # Convert File typed objects to str
        # TODO: It would be better if we convert str to File instead
        for x in xrange(len(self.sources)):
            if type(self.sources[x]) != str:
                self.sources[x] = self.sources[x].path
        #self.sources = [ x.path for x in self.sources ]
        self.origsources = self.sources[:]

        tmp = []
        updirs = []
        for x in self.sources:
            updirs.append( x.count("..") )
            x = x.replace("..", "_up_")
            x = join( self.output_folder, x )
            tmp.append(x)

        #self.sources = [ join( self.output_folder, x ) for x in self.sources ]
        self.sources = tmp

        # This is often needed
        args.FOLDER_TARGET_TUPLE = ( self.output_folder, self.target )
        Mkdir( self.output_folder )

        # Target resultable template. Just give extension of the file
        self._result_template = "%s/%s" % args.FOLDER_TARGET_TUPLE + "%s"
        self._result_template = os.path.abspath( self._result_template )

        # Copy the modified keywords from self ignoring private
        kwargs = {}
        for x in dir(self):
            if x.startswith("_"):
                continue
            kwargs[x] = getattr( self, x )

        kwargs["defoutput"] = self._result_template % ( "{000a0000}.def" )
        self._env = _create_environment( **kwargs )

        # File duplication can be disabled with args.SCons's -n parameter to ease use of args.IDE(Carbide)
        # It seems that args.SCons is not always able to detect changes if duplication is disabled.
        self._env.VariantDir( self.output_folder, ".", duplicate = args.DO_DUPLICATE_SOURCES )

        # Define build dir for top folders.
        updirs = list(set(updirs))
        # Zero not valid in updirs
        if 0 in updirs: updirs.remove( 0 )
        for count in updirs:
            out_updir = "/" + "/".join( ["_up_"] * count )
            src_updir = "/".join( [".."] * count )
            #print self.output_folder + out_updir, src_updir
            self._env.VariantDir( self.output_folder + out_updir, src_updir, duplicate = args.DO_DUPLICATE_SOURCES )


        #------------------------------------------------------- Generate help files
        self._handleHelp()

        #-------------------------------------------------------------- Create icons
        self._handleIcons()

        #---------------------------------------------------- Convert resource files
        self._convertResources()

        # To be copied to /epoc32/release/WINSCW/UDEB/
        self.output_libpath = None

        build_prog = None
        #---------------------------------------------------------- Build using args.GCCE
        if args.COMPILER == args.COMPILER_GCCE:
            build_prog = self._handleGCCEBuild()
        #-------------------------------------------------------- Build using args.WINSCW
        else:
            build_prog = self._handleWINSCWBuild()


        self._env.Depends( build_prog, self.converted_icons )
        self._env.Depends( build_prog, self.converted_resources )
        self._env.Depends( build_prog, self.resource_headers )

        for dep in self.extra_depends:
            #self._env.Depends( self.sources, dep )
            self._env.Depends( build_prog, dep )

        #-------------------------------------------------------------- Copy results
        installed = self._copyResultBinary()

        #---------------------------------------------------------------- Export args.MMP
        if self.mmpexport is not None and args.MMP_EXPORT_ENABLED:
            exporter = mmp_parser.MMPExporter( self.mmpexport )
            data = exporter.MMPData

            data.TARGET = self.target
            #import pdb;pdb.set_trace()
            data.TARGETTYPE = self.targettype
            #import pdb;pdb.set_trace()
            defines = self.defines[:] + args.EXTRA_DEFINES
            #for d in args.STANDARD_DEFINES:
            #    if d in defines:
            #        defines.remove(d)
            if hasattr( self, "epocstacksize" ):
                data.EPOCSTACKSIZE = self.epocstacksize
            if hasattr( self, "epocheapsize" ):
                data.EPOCHEAPSIZE  = self.epocheapsize

            if self.resources:
                data.RESOURCE = self.resources[:]

            data.MACRO   = defines
            data.SOURCE  = self.origsources[:]
            data.LIBRARY = [ x + ".lib" for x in self.origlibraries ]
            data.UID2    = self.uid2.replace("L","")
            data.UID3    = self.uid3.replace("L","")
            data.CAPABILITY = self.capabilities[:]
            data.USERINCLUDE.extend( self.includes )
            data.SYSTEMINCLUDE = self.sysincludes[:]
            #import pdb;pdb.set_trace()
            exporter.Export()
            exporter.Save()

            print( "Info: args.MMP exported '%s'" % self.mmpexport )

        if self.package is not None and self.package != "" and self.targettype != args.TARGETTYPE_LIB:
            # package depends on the files anyway
            self._env.Depends( self.package, installed )

        # Extra cleaning
        # It is easy to leave stuff with old names lying around
        # and those are never cleaned otherwise
        Clean( build_prog, self.output_folder )

        return build_prog