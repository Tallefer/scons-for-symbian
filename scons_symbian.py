"""
Main S4S module
"""
#pylint: disable-msg=E0611
from SCons.Builder import Builder
from SCons.Script import (Command, Copy, DefaultEnvironment, Install, Mkdir, Clean, Default)
from SCons.Node.FS import File

# This will speed up startup.
# See http://osdir.com/ml/programming.tools.scons.user/2006-05/msg00112.html
# Tested with LogMan.
# Before: 10 loops, best of 1: 2.68 sec per loop
# After : 10 loops, best of 1: 2 sec per loop
from SCons.Defaults import *
SCons.Defaults.DefaultEnvironment(tools = [])

import arguments as ARGS
# TODO(mika.raento): previously scons_symbian imported all names from
# arguments.py, including all the names that it imported from config.
# Importing the names imports the values of the variables as the import runs.
# The variables modified later (INSTALL_*) would have the initial values.
# Existing scripts may rely on the old behaviour, so we manually import the
# names that were avaiable previously.
# config has defaults for certain variables, import that first so that any
# reuse of those names in arguments.py correctly overrides.
# This should be replaced by having the 'constants' in arguments.py be mutable
# proxy objects to strings.
from config import *
from echoutil import loginfo
from arguments import get_output_folder, RUNNING_SCONS, VARS, EPOCROOT, EPOC32, EPOC32_DATA, EPOC32_INCLUDE, EPOC32_TOOLS, EPOC32_RELEASE, PYTHON_COMPILER, PYTHON_DOZIP, COMPILER, RELEASE, GCCE_OPTIMIZATION_FLAGS, WINSCW_OPTIMIZATION_FLAGS, MMP_EXPORT_ENABLED, DO_CREATE_SIS, DO_DUPLICATE_SOURCES, ENSYMBLE_AVAILABLE, UI_VERSION, SYMBIAN_VERSION, PLATFORM_HEADER, PACKAGE_FOLDER, COMPONENTS, COMPONENTS_EXCLUDE, CMD_LINE_DEFINES, CMD_LINE_LIBS, STANDARD_DEFINES, EXTRA_DEFINES, DEFAULT_SYMBIAN_DEFINES, HELP_ENABLED, PATH_ARM_TOOLCHAIN
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

def publicapi(func, *args,**kwargs):
    """ Decorator for public APIs to initialize system """
    def dummy(*args,**kwargs): pass

    def api(*args,**kwargs):
        _finalize_symbian_scons()
        return func(*args,**kwargs)

    if ARGS.HELP_ENABLED: return dummy;

    return api

def _finalize_symbian_scons():
  if ARGS.ResolveInstallDirectories():
    # Set ARGS.INSTALL_EPOCROOT as default target, so the stuff will be
    # built for emulator.
    Default( ARGS.INSTALL_EPOCROOT )
    Default( "." )

loginfo( "Building", ARGS.COMPILER, ARGS.RELEASE )
loginfo( "Defines =", ARGS.CMD_LINE_DEFINES )

# in template
# UID1 = 0x100039ce for exe
# UID1 = 0x00000000 for dll

def _create_environment( *env_args, **kwargs ):
    """Environment factory. Get correct environment for selected compiler."""
    env = None
    if ARGS.COMPILER == ARGS.COMPILER_GCCE:
        env = gcce.create_environment( *env_args, **kwargs )
    elif ARGS.COMPILER == ARGS.COMPILER_WINSCW:
        env = winscw.create_environment( *env_args, **kwargs )
    else:
        msg = "Error: Environment for '%s' is not implemented" % ARGS.COMPILER
        raise NotImplementedError( msg )

    # These sped up LogMan build startup ~0.2s
    #env.SetOption('max_drift', 4)
    #env.SetOption('implicit_cache', 1)
    #env.SetOption('diskcheck', None)

    return env

def SetInstallDirectory(dir):
  """
  SetInstallDirectory can be called to put the final output (binaries, resource
  files, .libs and headers) somewhere else than the SDK folder so that builds
  don't pollute the SDK. Apps can be started by pointing a virtual MMC to this
  directory (with _EPOC_DRIVE_E environment variable or epoc.ini setting).
  """
  ARGS.SetInstallDirectory(dir)

@publicapi
def SymbianPackage( package, ensymbleargs = None, pkgargs = None,
                    pkgfile = None, extra_files = None, source_package = None,
                    env=None, startonboot = None,
                    pkgtemplate = None ):
    """
    Create Symbian Installer( sis ) file. Can use either Ensymble or pkg file.
    To enable creation, give command line arg: dosis=true

    @param package: Name of the package.
    @type package: str

    @param pkgargs: Arguments to PKG generation. Disabled if none, use empty dict for simple enable.
                    To enable signing, give at least both cert and keys, which point to the
                    respective files. passwd key can be used for password.
                    If pkgfile is not given, package name is converted to pkg extension and used instead.
                    The signed sis file gets extension SIGNSIS_OUTPUT_EXTENSION defined in constants.py

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

    @param extra_files: Copy files to package folder and install for simulator( to SIS with Ensymble only )
    """
    # Skip processing to speed up help message
    if not env:
        env = DefaultEnvironment()

    if ensymbleargs is not None and pkgargs is not None:
        raise ValueError( "Trying to use both Ensymble and ARGS.PKG file. Which one do you really want?" )
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

            if ARGS.COMPILER == ARGS.COMPILER_WINSCW:
                Install( join( ARGS.INSTALL_EMULATOR_C, target ), source )

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
    if ARGS.COMPILER != ARGS.COMPILER_WINSCW:
        if pkgargs is not None:
            if pkgfile is None:
                pkgfile = symbian_pkg.GetPkgFilename(package)
            create_pkg_file( pkgargs )

    def __create_boot_up_resource( target, source, env):
        """Create boot up resource file"""
        # Notice that the resource must ALWAYS be copied to C:
        template = r"""
        #include <startupitem.rh>

        RESOURCE STARTUP_ITEM_INFO startexe
        {
            executable_name = "c:\\sys\\bin\\%(APPNAME)s";
            recovery = EStartupItemExPolicyNone;
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

        output_folder = get_output_folder( ARGS.COMPILER, ARGS.RELEASE, startonboot, "rss" )

        uid = PKG_HANDLER.PackageArgs(package)["uid"]

        uid = uid.replace("0x", "" )

        rssfilepath = join( output_folder, "[%s].rss" % uid )
        env.Command( rssfilepath, None, __create_boot_up_resource )

        rscfilepath = join( output_folder, "[%s].rsc" % uid )
        rsgfilepath = join( output_folder, "%s.rsg" % uid )

        rcomp.RComp( env, rscfilepath, rsgfilepath,
                             rssfilepath,
                             "-v -m045,046,047",
                             ARGS.SYSTEM_INCLUDES,
                             [ARGS.PLATFORM_HEADER],
                             [ 'LANGUAGE_SC'])

        ToPackage(env, { "C" : ".*[.](rsc)" }, package,
                  "private/101f875a/import/", rscfilepath, toemulator=False)

        if ARGS.COMPILER == ARGS.COMPILER_WINSCW:
            env.Install( join( ARGS.INSTALL_EPOC32_DATA ), rscfilepath )

    #---------------------------------------------------- Create boot up API resource
    _makeBootUpResource()

    def create_install_file( installed ):
        """Utility for creating an installation package using Ensymble or PKG template"""
        from ensymble.cmd_simplesis import run as simplesis

        if pkgfile is None and ARGS.ENSYMBLE_AVAILABLE:

            def ensymble( env, target = None, source = None ): #IGNORE:W0613
                """ Wrap ensymble simplesis command. """
                cmd = []
                for x in ensymbleargs:
                    cmd += [ "%s=%s" % ( x, ensymbleargs[x] ) ]

                cmd += [ join( ARGS.PACKAGE_FOLDER, package ), package ]

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

    if ARGS.DO_CREATE_SIS:
        return create_install_file( PKG_HANDLER.Package(package).keys() )

@publicapi
def SymbianHelp( source, uid, env = None ):
    """ Generate help files for Context Help
    @param source: Help project file .cshlp"
    @uid: UID of the application.

    @return: generated .hlp and .hrh files.
    @rtype: 2-tuple
    """
    import cshlp
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
    files = ZIP_FILES[zippath]["files"]
    print( "Install files into archive: %s" % (zippath) )
    for s,t in files:
        print s,t
        z.write( s, t )
    z.close()

ZIP_FILES = {}
@publicapi
def File2Zip(zipfilepath, source, arcpath, env = None ):
    """ Add a file into a zip archive """
    global ZIP_FILES

    files = []
    if env is None:
        env = DefaultEnvironment()

    zipfilepath = abspath( zipfilepath )

    if zipfilepath not in ZIP_FILES:
        #import pdb;pdb.set_trace()
        # Create command
        ZIP_FILES[zipfilepath] = { "files" : files }
        env.Command( zipfilepath, "", _zipfile)
    else:
        files = ZIP_FILES[zipfilepath]["files"]

    env.Depends( zipfilepath, source )
    files.append( (source, arcpath) )

    return zipfilepath

def _py2pyc(target,source,env):
    """ Compile python sources to .pyc using selected python compiler """
    # Can strip docstrings and enable optimizations only through command line
    # But no matter since we could be on Py 2.6 but 2.5 is needed
    cmd = r"""%s -OO -c "import py_compile as p;""" % ARGS.PYTHON_COMPILER

    files = zip(source,target )
    for py, pyc in files:
        cmd += "p.compile(r'%s',cfile=r'%s', dfile='%s');" % ( py, pyc, basename(pyc.abspath) )

    os.system( cmd )
    return 0

@publicapi
def Python2ByteCode( source, target = ".pyc", env = None ):
    """ Utility to compile Python source into a byte code """


    if target in [".pyc", ".pyo"]:
        target = source.replace(".py", target)

    if env is None:
        env = DefaultEnvironment()

    cmd = env.Command( [target], [source], _py2pyc)

    return target

#: Holds the file source->target paths for each package
#: This information is be used to generate the pkg file.
PKG_HANDLER = symbian_pkg.PKGHandler()

@publicapi
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
    @param toemulator: Flag to determine if the file is installed for SDK's emulator.
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

    if env is None:
        env = DefaultEnvironment()

    # Just skip this then
    if package is None:
        return

    # Convert python source into a byte code
    if dopycompile and ARGS.PYTHON_COMPILER and source.endswith(".py"):
        source = Python2ByteCode( source, target = dopycompile )

    # WARNING: Copying to any/c/e is custom Ensymble feature of PyS60 CE
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

    pkgsource = join( ARGS.PACKAGE_FOLDER, package, drive, target, basename( source ) )
    # Handle Python library zipping
    if pylibzip is not None and _is_python_file(source):
        fullzippath = abspath( join( ARGS.PACKAGE_FOLDER, package, drive, pylibzip ) )
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

        if toemulator and ARGS.COMPILER == ARGS.COMPILER_WINSCW:
            env.Install( join( ARGS.INSTALL_EMULATOR_C, dirname(pylibzip) ), pkgsource )

        return fullzippath

    else:
        # Add to pkg generator
        pkg[pkgsource] = join( drive, target, basename( source ) )

        env.Depends( symbian_pkg.GetPkgFilename( package ), join( ARGS.PACKAGE_FOLDER, package, pkg[pkgsource] ) )

        package_target = join( ARGS.PACKAGE_FOLDER, package, drive, target )
        cmd = env.Install( package_target, source )
        Clean( cmd,join( ARGS.PACKAGE_FOLDER, package) )

        if drive == "":
            pkg[pkgsource] = join( "any", target, basename( source ) )

        if toemulator and ARGS.COMPILER == ARGS.COMPILER_WINSCW:
            env.Install( join( ARGS.INSTALL_EMULATOR_C, target ), source )

    return target

def SymbianTargetPath(target, targettype = ""):
    """ Return the result path for symbian target"""

    p = get_output_folder( ARGS.COMPILER, ARGS.RELEASE, target, targettype )
    if targettype == "":
        p = p[:-1]
    return os.path.abspath(p)

def SymbianIconCommand(env, target, source):
    """SCons command for running the mifconv icon conversion tool."""
    
    # Creates 32 bit icons
    if 'custom_mifconv' in env:
      convert_icons_cmd = (env['custom_mifconv'] + r' "%s"').replace( "\\", "/" )
    else:
      convert_icons_cmd = ( ARGS.EPOCROOT + r'epoc32/tools/mifconv "%s"' ).replace( "\\", "/" )

    if os.name == 'nt':
        source_icons   = source
        target_miffile = target[0].abspath
        if ":" in target_miffile:
          target_miffile = target_miffile.split(":")[-1]
    else:
        # TODO: Use source[0].rel_path ?
        from relpath import relpath
        source_icons = []
        for icon in source:
          source_icons.append(relpath(os.getcwd(), icon.tpath))
        target_miffile = target[0].tpath

    cmd = convert_icons_cmd % ( target_miffile )
    if len(target) > 1:
      mbg_filename = target[1].abspath
      cmd += r' /h"' + mbg_filename + r'"'

    # This is needed if you have mifconv on different
    # drive then sources    
    if SYMBIAN_VERSION[0] == 9 and SYMBIAN_VERSION[1] == 3:
      cmd += r' /S' + ARGS.EPOCROOT + r'epoc32/tools'
      
    for icon in source_icons:
      cmd += r' /c32,1 "' + icon.abspath + r'"'

        # TODO: Use colorizer
    print cmd
    return os.system( cmd )

@publicapi
def SymbianIconBuilder(target, source, env = None, custom_mifconv = None ):
    """ Runs Command with SymbianIconCommand handler """
    if not env: env = DefaultEnvironment()
    env['custom_mifconv'] = custom_mifconv

    return env.Command( target, source, SymbianIconCommand )

@publicapi
def SymbianIcon(icons, env = None, mif_filename = None, mbg_filename = None, package = None, package_drive_map = None, custom_mifconv = None ):
    """
    Converts a single icon or list of iccons and installs it to default or specified location

    Example:
    >>> SymbianIcon( "myicon.svg", package = "myapp")
    => Creates myicon_aif.mif
    >>> SymbianIcon( ("myicon.svg", "renamed"), package = "myapp" )
    => Creates renamed_aif.mif
    
    @param icons: Path to single icon, or list of paths to multiple icons.
	@param mif_filename: Target mif file (without extension).
	                     If path not specified default path will be used.
	                     If parameter not specified, mif filename will be generated from first icon.
	@param mbg_filename  Target header file to be created.
	                     If path not specified default path will be used.
	                     If parameter not specified, mif filename will be generated from first icon.
    @param package: Name of the package.
    
    @return: Dict containing:
        {
            "result"    : <path of the result under build dir>,
            "installed" : tuple( <locations where the icon was installed to>)
        }
    @rtype: dict
    """
    if not env: env = DefaultEnvironment()

    target_miffile = mif_filename;

    source_icons = icons
    if type(icons) == str:
      source_icons = [ icons ]


    # Set target path
    if mif_filename is None:
      template    = join( SymbianTargetPath("icons"), "%s_aif.mif" )
      target_miffile = template % ( target_icons[0] )
    else:
      if mif_filename.find('/') != -1:
        target_miffile = abspath(mif_filename) + ".mif"
      else:
        template    = join( SymbianTargetPath("icons"), "%s.mif" )
        target_miffile = template % ( mif_filename )

    # Convert
    resultables = [ target_miffile ]

    target_mbg = None
    if mbg_filename is not None:
      template    = join( SymbianTargetPath("icons"), "%s.mbg" )
      target_mbg  = template % ( mbg_filename )
      resultables.append(target_mbg)

    env.SideEffect("dont_build_more_mifs_at_same_time.txt", resultables)
    
    SymbianIconBuilder(resultables, source_icons, env = env, custom_mifconv = custom_mifconv)

    # Install to default locations
    sdk_data = join(ARGS.INSTALL_EPOC32_DATA, "Z", "resource","apps/")
    sdk_rel  = join(ARGS.INSTALL_EPOC32_RELEASE, "z", "resource", "apps" )

    env.Install( sdk_rel,  target_miffile )
    env.Install( sdk_data, target_miffile )

    if target_mbg is not None:
      sdk_inc  = ARGS.INSTALL_EPOC32_INCLUDE
      env.Install( sdk_inc, target_mbg )
      # return copied name as result
      target_mbg = os.path.basename(target_mbg)
      target_mbg = os.path.join(ARGS.INSTALL_EPOC32_INCLUDE, target_mbg).replace("\\", "/")

    if package:
        ToPackage( env  = env,
                target  = join( "resource", "apps" ),
                source  = source_icons,
                package = package,
                package_drive_map = package_drive_map,
                toemulator = False )

    return { "result" : target_miffile, "header" : target_mbg, "installed" : (sdk_data, sdk_rel) }

@publicapi
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
                    win32_headers = False,
                    # Sis stuff
                    package = "",
                    package_drive_map = None,
                    extra_depends = None,
                    **kwargs):
    """
    Main function for compiling Symbian applications and libraries.
    Handles the whole process of source and resource compiling
    and SIS installer packaging.

    @param target: Name of the module without file extension.
                    If the name ends with .mmp, the .mmp file is used for
                    defining the module.
    @type target: str

    @param targettype: Type of the program. One of L{arguments.TARGETTYPES}.
    @type targettype: str

    @param sources:     List of paths to sources to compiler
    @type sources: list

    @param includes:    List of folders to be used for finding user headers.
    @type includes: list

    @param sysincludes:  List of folders to be used for finding system headers.
    @type sysincludes: list

    @param sid: Secure id. Defaults to uid3.
    @type sid: str/hex

    @param mmpexport: Path to the generated MMP
    @type mmpexport: str

    @param definput:    Path to .def file containing frozen library entrypoints.
    @type definput: str

    @param icons:       List of icon files to compile
    @type icons: list

    @param resources:   List of paths to .rss files to compile.
                        See rssdefines param for giving CPP macros.
    @type resources: list

    @param libraries: Used libraries. Searched for in the SDK.
    @type libraries: list

    @param user_libraries: Used libraries from the developer's build.
                           Searched for under the directory given to
                           SetInstallDirectory.

    @param capabilities: Used capabilities. Default: FREE_CAPS
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

    @param win32_headers: Whether to add win32 include paths (default False)

    @param package:       Path to installer file. If given, an installer is automatically created.
                          The files are copied to L{arguments.PACKAGE_FOLDER} and
                          Ensymble is used to create an installer package with simplesis command.

    @type package: str

    @param package_drive_map: For custom Ensymble with drive destination support.
                              Map files to drives by using regular expressions.
                              For example, to map .mif and .rsc files to C drive:
                                package_drive_map = { "C" : ".*[.](mif|rsc)" }
                              The files goes to 'any' folder by default.

                              Disabled if None. Normal Ensymble behavior used.

    @type  package_drive_map: dict

    @param extra_depends: External files which must be built prior the app
    @type extra_depends: list

    @param kwargs: Additional keywords passed to selected compiler environment
                   factory: L{gcce.create_environment}, L{winscw.create_environment}

    @return: Last Command. For setting dependencies.

    """

    # Transforms arguments into keywords
    kwargs.update( locals() )

    handler = SymbianProgramHandler( **kwargs )
    return handler.Process()

class SymbianProgramHandler(object):
    """Internal class for handling the SymbianProgram function call"""
    def __init__(self, **kwargs):

        _finalize_symbian_scons()
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

        if ARGS.COMPONENTS is not None:
            inlist = ( component_name in ARGS.COMPONENTS )
            if inlist and not ARGS.COMPONENTS_EXCLUDE:
                pass
            elif not inlist and ARGS.COMPONENTS_EXCLUDE:
                pass
            else:
                print "Ignored Symbian component %s(%s)" % ( component_name, self.uid3 )
                return False

        print "Getting dependencies for %s(%s)" % ( component_name, self.uid3 )

        return True

    def _handleIcons(self):
        """Sets self.converted_icons"""

        # Copy for emulator at the end using this list, just like binaries.
        self.converted_icons = []

        if self.icons is None:
            return

        for icon in self.icons:
            paths = SymbianIcon( icon, package = self.package, env = self._env )
            self.converted_icons.append( paths["result"] )

        return True

    def _copyResultBinary(self):
        """Copy the linked binary( exe, dll ) for emulator
        and to resultables folder.
        """

        env = self._env
        installfolder = [ ]

        if self.targettype != ARGS.TARGETTYPE_LIB:
            installfolder += ["sys", "bin" ]
        else: # Don't install libs to device.
            installfolder += ["lib"]

        installfolder = join( *installfolder )
        #Mkdir( installfolder )

        #installpath = join( installfolder, "%s.%s" % ( self.target, self.targettype ) )

        # Combine with installfolder copying.
        #TODO: Not needed anymore since ARGS.INSTALL_EPOCROOT is default target.
        postcommands = []
        copysource = self._result_template % ( "." + self.targettype )
        target_filename = self.target + "." + self.targettype
        sdkpath = join( ARGS.SDKFOLDER, target_filename )

        installed = []
        if ARGS.COMPILER == ARGS.COMPILER_WINSCW:
            # Copy to SDK to be used with simulator
            postcommands.append( Copy( sdkpath, copysource ) )
            installed.append( sdkpath )

        if self.output_libpath is not None:
            if (  ARGS.COMPILER == ARGS.COMPILER_WINSCW and
                  self.targettype != ARGS.TARGETTYPE_LIB) or \
                ARGS.COMPILER == ARGS.COMPILER_GCCE and self.targettype == ARGS.TARGETTYPE_LIB :

                s, t = self.output_libpath
                postcommands.append( Copy( t, s ) )
                installed.append( t )

        if len(installed) > 0:
            env.Command( installed, #IGNORE:W0612
                         copysource,
                         postcommands )

        if self.targettype != ARGS.TARGETTYPE_LIB:
            ToPackage( env, self.package_drive_map, self.package,
                    installfolder,
                    copysource, toemulator = False )
        else:  # Don't install libs to device.
            ToPackage( env, None, None,
                    "lib",
                    copysource, toemulator = False )

        return installed

    #TODO: Create main interface SymbianResource for special resource compiling
    def _convertResources( self, extra_depends = None):
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
                             [ARGS.PLATFORM_HEADER],
                             self.rssdefines,
                             extra_depends )

                self._env.Depends( res_compile_command, self.converted_icons )

                installfolder = []
                if rss_notype.endswith( "_reg" ):
                    installfolder.append( join( "private", "10003a3f", "import", "apps" ) )
                else:
                    if ARGS.SYMBIAN_VERSION[0] > 8:
                      installfolder.append( join( "resource", "apps" ) )
                    else:
                      installfolder.append( join( "system", "apps", self.target ) )
                installfolder = os.path.join( *installfolder )

                rsc_filename = "%s.%s" % ( rss_notype, "rsc" )
                # Copy to sis creation folder
                ToPackage( self._env, self.package_drive_map, self.package,
                           installfolder, converted_rsc, toemulator = False )

                includefolder = ARGS.INSTALL_EPOC32_INCLUDE

                # Copy to /epoc32/include/
                self._env.Install( includefolder, converted_rsg )#IGNORE:E1101
                includepath = join( includefolder, "%s.%s" % ( rss_notype, "rsg" ) )

                # Add created header to be added for build dependency
                self.resource_headers.append( includepath )

                # _reg files copied to /epoc32/DATA/Z/private/10003a3f/apps/ on simulator
                if ARGS.COMPILER == ARGS.COMPILER_WINSCW:
                    if "_reg" in rss_path.lower():
                        self._env.Install( join( ARGS.INSTALL_EPOC32_DATA, "Z", "private","10003a3f","apps"), converted_rsc )
                        self._env.Install( join( ARGS.INSTALL_EPOC32_RELEASE, "Z", "private","10003a3f","apps"), converted_rsc )
                        self._env.Install( join( ARGS.INSTALL_EPOC32_DATA, "Z",
                                                "private","10003a3f","import", "apps"), converted_rsc )
                        self._env.Install( join( ARGS.INSTALL_EPOC32_RELEASE,
                                                "Z", "private","10003a3f", "import", "apps"), converted_rsc )

                    else: # Copy normal resources to resource/apps folder
                        self._env.Install( join( ARGS.INSTALL_EPOC32_DATA, "Z", "resource","apps"), converted_rsc )
                        self._env.Install( join( ARGS.INSTALL_EPOC32_RELEASE, "Z", "resource", "apps"), converted_rsc )
                        self._env.Install( join( ARGS.INSTALL_EPOC32_RELEASE,
                                                "Z", "system", "apps",
                                                self.target), converted_rsc )

                # Depend on previous. TODO: Use SCons Preprocessor scanner.
                if prev_resource is not None:
                    self._env.Depends( rss_path, prev_resource )
                prev_resource = includepath

    def _handleGCCEBuild(self):
        env = self._env
        output_lib   = ( self.targettype in ARGS.DLL_TARGETTYPES )
        elf_dll_path = self._result_template % ( "._elf_" + self.targettype )
        resultables  = [ elf_dll_path  ]

        if output_lib:
            libname = self.target + ".dso"
            self.output_libpath = ( join(ARGS.INSTALL_EPOCROOT,
                                   r"epoc32/release/%s/%s/%s" % ( "armv5", "lib", libname ) ) )

        build_prog = None
        if self.targettype != ARGS.TARGETTYPE_LIB:
            build_prog = self._env.Program( resultables, self.sources )#IGNORE:E1101

            # Depend on the libs
            #import pdb;pdb.set_trace()
            for libname in self.libraries:
                env.Depends( build_prog, libname )

            for libname in self.user_libraries:
                env.Depends( build_prog, libname )

            # Mark the lib as a resultable also
            resultables = [ self._result_template % ( "" ) ]
            if output_lib:
                resultables.append( self.output_libpath )

            # Create final binary and lib/dso
            env.Elf( resultables, elf_dll_path )#IGNORE:E1101

            env.Install( join(ARGS.INSTALL_EPOCROOT + r"epoc32/release/gcce/%s" % ( ARGS.RELEASE )),
                         ".".join( [resultables[0], self.targettype] ) )
        else:
            build_prog = env.StaticLibrary( self._result_template % ".lib" , self.sources )#IGNORE:E1101
            self.output_libpath = ( self._result_template % ".lib",
                                    join(ARGS.INSTALL_EPOCROOT,
                                         r"epoc32/release/armv5/%s/%s.lib" % (
                                           ARGS.RELEASE, self.target ) ) )

        return build_prog

    # TODO: Move to winscw.py
    def _createUIDCPP( self, target, source, env ):#IGNORE:W0613
        """Create .UID.CPP for simulator"""
        template = ""
        capabilities = winscw.make_capability_hex( self.capabilities )
        if self.targettype == ARGS.TARGETTYPE_EXE:
            template = winscw.TARGET_UID_CPP_TEMPLATE_EXE % { "UID2": self.uid2,
                                                              "UID3": self.uid3,
                                                              "SID" : self.sid,
                                                              "CAPABILITIES": capabilities }
        else:
          template = winscw.TARGET_UID_CPP_TEMPLATE_DLL % { "UID2": self.uid2,
                                                            "UID3": self.uid3,
                                                            "CAPABILITIES": capabilities }

        f = open( target[0].path, 'w' );f.write( template );f.close()

        return None

    def _handleWINSCWBuild(self):
        """
        DLL:
        A temporary library(.lib) is created in order to generate .inf file, which in turn
        is used to generate exports .def file with makedef.pl perl script.
        The .def file is used to generate the final dll.
        """
        # Compile sources ------------------------------------------------------
        env = self._env

        if self.targettype != ARGS.TARGETTYPE_LIB:
            # Create <target>.UID.CPP from template---------------------------------
            uid_cpp_filename = self._result_template % ".UID.cpp"
            #self._createUIDCPP( [env.File( uid_cpp_filename)], None, env )

            # TODO: Move to winscw.py
            bld = Builder( action = self._createUIDCPP,
                          suffix = '.UID.cpp',
                          caps = self.capabilities )
            env.Append( BUILDERS = {'CreateUID' : bld} )

            # uid.cpp depends on the value of the capabilities
            caps_value = env.Value(self.capabilities)
            env.CreateUID( uid_cpp_filename, [
              caps_value,
              env.Value(self.uid2),
              env.Value(self.uid3) ] )#IGNORE:E1101

            # We need to include the UID.cpp also
            self.sources.append( self._env.File(uid_cpp_filename ) )

        # Compile the sources. Create object files( .o ) and temporary dll.
        output_lib = ( self.targettype in ARGS.DLL_TARGETTYPES )
        temp_dll_path = self._result_template % ( "._tmp_" + self.targettype )
        resultables = [ temp_dll_path ]

        # TODO(jtoivola/mika.raento): We should pass the libraries needed to
        # the env.Program() call instead of stuffing them in the environment
        # LIBRARIES variable so that the dependencies get set right without
        # having to call env.Depends() explicitly.
        if output_lib:
            # No libs from exes
            libname = self.target + ".lib"
            resultable_path = self._result_template % "._tmp_lib"
            resultables.append( resultable_path )
            #resultables.append( self._result_template % ".inf" )
            self.output_libpath = ( self._result_template % ".lib",
                                join( ARGS.INSTALL_EPOC32_RELEASE, libname ) )
        if self.targettype == ARGS.TARGETTYPE_EXE:
            build_prog = env.Program( self._result_template % ".exe", self.sources )
            env.Depends( build_prog, [ join( ARGS.EPOC32_RELEASE, libname ) for libname in self.libraries] )
            env.Depends( build_prog, [ join( ARGS.INSTALL_EPOC32_RELEASE,
                                            libname ) for libname in self.user_libraries] )
            if ARGS.EPOCROOT != ARGS.INSTALL_EPOCROOT:
              env.Install( join(ARGS.INSTALL_EPOC32_RELEASE, "z", "sys", "bin"),
                           build_prog[0] )
            return build_prog

        elif self.targettype != ARGS.TARGETTYPE_LIB:
            build_prog = env.Program( resultables, self.sources )#IGNORE:E1101
            # Depends on the used libraries. This has a nice effect since if,
            # this project depends on one of the other projects/components/dlls/libs
            # the depended project is automatically built first.
            env.Depends( build_prog, [ join( ARGS.EPOC32_RELEASE, libname ) for libname in self.libraries] )
            env.Depends( build_prog, [ join( ARGS.INSTALL_EPOC32_RELEASE,
                                            libname ) for libname in self.user_libraries] )

        else:
            build_prog = env.StaticLibrary( self._result_template % ".lib" , self.sources )#IGNORE:E1101
            self.output_libpath = ( self._result_template % ".lib",
                                join( ARGS.INSTALL_EPOC32_RELEASE, "%s.lib" % ( self.target ) ) )

        if output_lib and self.targettype != ARGS.TARGETTYPE_LIB:
            # Create .inf file from the .lib
            definput = self.definput
            if definput is not None:# and os.path.exists(definput):
                definput = '-Frzfile "%s" ' % definput
            else:
                definput = ""

            tmplib  = self._result_template % "._tmp_lib"
            inffile = '-Inffile "%s" ' % ( self._result_template % ".inf" )
            defout  = ( self._result_template % '.def' )
            # Creates def file
            absent_e32dll = "-absent __E32Dll"
            if ARGS.SYMBIAN_VERSION[0] < 9:
              absent_e32dll = ''
            makedef = r'perl -S %%EPOCROOT%%epoc32/tools/makedef.pl %s %s %s "%s"' % \
                    ( absent_e32dll, inffile, definput, defout )

            action = "\n".join( [
                # Creates <target>.lib
                'mwldsym2.exe -S -show only,names,unmangled,verbose -o "%s" "%s"' % ( self._result_template % ".inf", self._result_template % "._tmp_lib" ),
                makedef
                 ] )

            defbld = Builder( action = action,
                              ENV = os.environ )
            env.Append( BUILDERS = {'Def' : defbld} )
            env.Def( defout, tmplib )

        # NOTE: If build folder is changed this does not work anymore.
        # List compiled sources and add to dependency list
        object_paths = [ ".".join( x.path.split( "." )[: - 1] ) + ".o" for x in self.sources ] #IGNORE:W0631

        # Sources depend on the headers generated from .rss files.
        env.Depends( object_paths, self.resource_headers )

        # Get the lookup folders from source paths.
        object_folders = [ os.path.dirname( x ) for x in object_paths ]

        # Needed to generate the --search [source + ".cpp" -> ".o",...] param
        objects = [ os.path.basename( x ) for x in object_paths ]
        objects = " ".join( objects )

        libfolder = "%EPOCROOT%epoc32/release/winscw/udeb/"
        libs = [ libfolder + x for x in self.libraries] + [
            join(ARGS.INSTALL_EPOC32_RELEASE, x) for x in self.user_libraries ]
        win32_libs = self.win32_libraries or []
        win32_subsystem = self.win32_subsystem or "windows"

        if self.targettype in ARGS.DLL_TARGETTYPES and self.targettype != ARGS.TARGETTYPE_LIB:
            final_output = self._result_template % ( "." + self.targettype )
            implib = '-implib "%s"' % ( self._result_template % ".lib" )
            noentry = '-noentry'
            if self.targettype == ARGS.TARGETTYPE_APP:
                env.Install( join(ARGS.INSTALL_EPOC32_RELEASE, "z", "system",
                                  "apps", self.target),
                             final_output )
                implib = ''
                noentry = ''

            env.Command( final_output, [ temp_dll_path, self._result_template % ".def" ],
            [
                " ".join( [
                            'mwldsym2 -msgstyle gcc',
                            '-stdlib %EPOCROOT%epoc32/release/winscw/udeb/edll.lib',
                            noentry,
                            '-shared -subsystem %s' % win32_subsystem,
                            '-g %s' % " ".join( libs ),
                            ' %s' % " ".join( win32_libs ),
                            '-o "%s"' % temp_dll_path,
                            '-f "%s"' % ( self._result_template % ".def" ),
                            implib,
                            '-addcommand "out:%s.%s"' % ( self.target, self.targettype ),
                            '-warnings off',
                            '-l %s' % " -l ".join( set( object_folders ) ),
                            '-search ' + objects,
                          ]
                        )
            ]
            )
        return build_prog

    def _handleHelp(self):
        if not self.help:
            return

        helpresult = SymbianHelp( self.help, self.uid3, env = self._env )
        #if ARGS.COMPILER == ARGS.COMPILER_WINSCW:
            #self._env.Install( join( ARGS.INSTALL_EMULATOR_C, "resource", "help" ), helpresult[0] )#IGNORE:E1101

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

        # Allow override in SConstruct
        if self.capabilities is None:
            self.capabilities = data["capability"]

        # Allow override in SConstruct
        if self.rssdefines is None:
            self.rssdefines = data["macro"][:]

        self.defines       = data["macro"][:]
        self.allowdlldata  = data["epocallowdlldata"]
        self.epocstacksize = data["epocstacksize"]
        #pylint: enable-msg=W0201

    def Process(self):

        if self.target.lower().endswith( ".mmp" ):
            self._importMMP()

        # After mmp import
        self.output_folder = SymbianTargetPath( self.target, self.targettype )

        if self.includes is None:
            self.includes = []

        if self.defines is None:
            self.defines = []

        self.defines = self.defines[:] # Copy

        if self.extra_depends is None:
            self.extra_depends = []

        if self.sysincludes is None:
            self.sysincludes = []

        self.sysincludes.extend( ARGS.SYSTEM_INCLUDES )

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

        if ARGS.CMD_LINE_LIBS is not None:
            self.libraries.extend( ARGS.CMD_LINE_LIBS )

        if self.capabilities is None:
            self.capabilities = ARGS.CAPS_SELF_SIGNED

        # Handle UIDs
        if self.uid2 is None:
            if self.targettype == ARGS.TARGETTYPE_EXE:
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

        # Add macros to ease changing application UID
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

        # ???: SCons is able to compile sources with self.output_folder
        #      but not able to detect if the files have changed without
        #      explicit dependency!! Without self.output_folder the resulting object
        #      files are stored in the same folder as sources causing cross compiling
        #      to fail.
        # Seems to work again without. What is going on here? Updated scons 1.1?
        #self.extra_depends.extend( self.sources )

        # This is often needed
        ARGS.FOLDER_TARGET_TUPLE = ( self.output_folder, self.target )
        Mkdir( self.output_folder )

        # Target resultable template. Just give extension of the file
        self._result_template = "%s/%s" % ARGS.FOLDER_TARGET_TUPLE + "%s"
        self._result_template = os.path.abspath( self._result_template )

        # Copy the modified keywords from self ignoring private
        kwargs = {}
        for x in dir(self):
            if x.startswith("_"):
                continue
            kwargs[x] = getattr( self, x )

        kwargs["defoutput"] = self._result_template % ( "{000a0000}.def" )
        self._env = _create_environment( **kwargs )

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
            tmp.append(self._env.File(x))

        #self.sources = [ join( self.output_folder, x ) for x in self.sources ]
        self.sources = tmp

        # File duplication can be disabled with SCons's -n parameter to ease use of IDE(Carbide)
        # It seems that SCons is not always able to detect changes if duplication is disabled.
        self._env.VariantDir( self.output_folder, ".", duplicate = ARGS.DO_DUPLICATE_SOURCES )

        # Define build dir for top folders.
        updirs = list(set(updirs))
        # Zero not valid in updirs
        if 0 in updirs: updirs.remove( 0 )
        for count in updirs:
            out_updir = "/" + "/".join( ["_up_"] * count )
            src_updir = "/".join( [".."] * count )
            #print self.output_folder + out_updir, src_updir
            self._env.VariantDir( self.output_folder + out_updir, src_updir, duplicate = ARGS.DO_DUPLICATE_SOURCES )


        #------------------------------------------------------- Generate help files
        self._handleHelp()

        #-------------------------------------------------------------- Create icons
        self._handleIcons()

        #---------------------------------------------------- Convert resource files
        self._convertResources(extra_depends = self.extra_depends)

        # To be copied to /epoc32/release/WINSCW/UDEB/
        self.output_libpath = None

        build_prog = None
        #---------------------------------------------------------- Build using GCCE
        if ARGS.COMPILER == ARGS.COMPILER_GCCE:
            build_prog = self._handleGCCEBuild()
        #-------------------------------------------------------- Build using WINSCW
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

        #---------------------------------------------------------------- Export MMP
        if self.mmpexport is not None and ARGS.MMP_EXPORT_ENABLED:
            exporter = mmp_parser.MMPExporter( self.mmpexport )
            data = exporter.MMPData

            data.TARGET = self.target
            #import pdb;pdb.set_trace()
            data.TARGETTYPE = self.targettype
            #import pdb;pdb.set_trace()
            defines = self.defines[:] + ARGS.EXTRA_DEFINES
            #for d in ARGS.STANDARD_DEFINES:
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

            print( "Info: ARGS.MMP exported '%s'" % self.mmpexport )

        if self.package is not None and self.package != "" and self.targettype != ARGS.TARGETTYPE_LIB:
            # package depends on the files anyway
            self._env.Depends( self.package, installed )

        # Extra cleaning
        # It is easy to leave stuff with old names lying around
        # and those are never cleaned otherwise
        Clean( build_prog, self.output_folder )

        return build_prog

del publicapi
del File