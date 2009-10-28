"""Reads and stores globals including the command line arguments"""

__author__ = "Jussi Toivola"
__license__ = "MIT License"

from SCons.Script import ARGUMENTS, DefaultEnvironment, HelpFunction as Help
from SCons.Variables import Variables, EnumVariable
from config import * #IGNORE:W0611
from os.path import join, abspath
from echoutil import loginfo
import os
import sys

#: Are we running a build? This is to avoid messing up code analyzers
#: and Epydoc.
RUNNING_SCONS = ( "scons" in sys.argv[0] or "-c" == sys.argv[0] )

VARS = Variables( 'arguments.py' )
def GetArg( name, helpmsg, default, allowed_values = None, caseless = True ):
    """Utility for adding help information and retrieving argument"""

    if allowed_values is not None:
        VARS.Add( EnumVariable( name, helpmsg, default,
                    allowed_values = allowed_values,
                    ignorecase = 2 ) )
    else:
        VARS.Add( name, helpmsg, default )
    value = ARGUMENTS.get( name, default )
    if value is not None and caseless:
        value = value.lower()
    return value

#: Symbian SDK folder
EPOCROOT = os.environ.get( "EPOCROOT", EPOCROOT )
loginfo( "EPOCROOT=%s" % EPOCROOT )

#: Constant pointing to EPOCROOT/epoc32
EPOC32 = join( EPOCROOT, 'epoc32' )
#: Constant pointing to sdk's data folder
EPOC32_DATA = join( EPOC32, 'data' )
#: Constant pointing to system include folder
EPOC32_INCLUDE = join( EPOC32, 'include' )
#: Constant pointing to system tools folder
EPOC32_TOOLS = join( EPOC32, 'tools' )
#: Constant pointing to release folder
EPOC32_RELEASE = join( EPOC32, "release", COMPILER, RELEASE )

# TODO(mika.raento): The setting of the final output directories feels hacky
# here.
# I _do_ want them to be overridable from scripts, as I think it's more a
# project style question than something you change per build.
# Should we just make the 'constants' accessor functions instead? Or something
# else?

_set_install_epocroot = None

def SetInstallDirectory(dir):
  """
  SetInstallDirectory can be called to put the final output (binaries, resource
  files, .libs and headers) somewhere else than the SDK folder so that builds
  don't pollute the SDK. Apps can be started by pointing a virtual MMC to this
  directory (with _EPOC_DRIVE_E environment variable or epoc.ini setting).
  """

  global _set_install_epocroot
  if _set_install_epocroot and _set_install_epocroot != dir:
    msg = "You have conflicting settings for the installation directory" + "%s, %s" % (_set_install_epocroot, dir)
    raise msg
  _set_install_epocroot = dir


INSTALL_EPOCROOT = None
INSTALL_EPOC32 = None
INSTALL_EPOC32_DATA = None
INSTALL_EPOC32_INCLUDE = None
INSTALL_EPOC32_TOOLS = None
INSTALL_EPOC32_RELEASE = None
INSTALL_EMULATOR_C = None
SDKFOLDER = None
SYSTEM_INCLUDES = None

def ResolveInstallDirectories():
  """
  ResolveInstallDirectories sets the necessary constants for final output. It
  should be called before accessing any of the INSTALL_ variables but is split
  into a separate initialization so that that the root of the installation tree
  can be set in a SConscript.

  It will only do its thing once, returning True if it did.
  """

  global INSTALL_EPOCROOT, INSTALL_EPOC32, INSTALL_EPOC32_DATA
  global INSTALL_EPOC32_INCLUDE, INSTALL_EPOC32_TOOLS, INSTALL_EPOC32_RELEASE
  global INSTALL_EMULATOR_C, SDKFOLDER, SYSTEM_INCLUDES
  if not INSTALL_EPOCROOT is None:
    return False
  #: Final output directories, mimicking SDK structure
  INSTALL_EPOCROOT = _set_install_epocroot or EPOCROOT
  INSTALL_EPOCROOT = GetArg("install_epocroot", "Final output directory root, "
                            "if different from EPOCROOT", INSTALL_EPOCROOT)
  loginfo( "INSTALL_EPOCROOT=%s" % INSTALL_EPOCROOT )

  #: Constant pointing to INSTALL_EPOCROOT/epoc32
  INSTALL_EPOC32 = join( INSTALL_EPOCROOT, 'epoc32' )
  #: Constant pointing to sdk's data folder
  INSTALL_EPOC32_DATA = join( INSTALL_EPOC32, 'data' )
  #: Constant pointing to system include folder
  INSTALL_EPOC32_INCLUDE = join( INSTALL_EPOC32, 'include' )
  #: Constant pointing to system tools folder
  INSTALL_EPOC32_TOOLS = join( INSTALL_EPOC32, 'tools' )
  #: Constant pointing to release folder
  INSTALL_EPOC32_RELEASE = join( INSTALL_EPOC32, "release", COMPILER, RELEASE )
  #: Constant pointing to emulator c drive
  INSTALL_EMULATOR_C = join( EPOC32, "winscw", "c" )
  #: Default include folders
  SYSTEM_INCLUDES = [ EPOC32_INCLUDE,
                      join( EPOC32_INCLUDE, "variant" ),
                      INSTALL_EPOC32_INCLUDE,
                  ]
  #: SDK Installation folder
  SDKFOLDER = os.path.join( INSTALL_EPOCROOT,
                                 "epoc32",
                                 "release",
                                 COMPILER,
                                 RELEASE
                  )
  return True


if sys.platform == "win32":
    os.environ["EPOCROOT"] = EPOCROOT.replace( "/", "\\" )
else:
    os.environ["EPOCROOT"] = EPOCROOT

PYTHON_COMPILER = GetArg("pycompiler", "Enable Python source compilation into bytecode. Points to Python executable.", None )
PYTHON_DOZIP    = GetArg("pythondozip", "Zip all python sources into a single archive. Path to the file on device", None )

_p = os.environ["PATH"]
#CSL_ARM_TOOLCHAIN_FOLDER_NAME = "CSL Arm Toolchain\\bin"
#if sys.platform == "linux2":
#    CSL_ARM_TOOLCHAIN_FOLDER_NAME = "csl-gcc/bin"

#: Path to arm toolchain. Detected automatically from path using 'CSL Arm Toolchain' on Windows or csl-gcc on Linux
#PATH_ARM_TOOLCHAIN = [ _x for _x in _p.split( os.path.pathsep ) if CSL_ARM_TOOLCHAIN_FOLDER_NAME in _x ]


# Parse arguments -------------------------------------------------------------

#: Used compiler
COMPILER = GetArg( "compiler", "The compiler to use.", COMPILER, COMPILERS )

#: Release type
RELEASE = GetArg( "release", "Release type.", RELEASE, RELEASETYPES )

#: Compiler flags for GCCE
GCCE_OPTIMIZATION_FLAGS = GetArg( "gcce_options", "GCCE compiler options.",
                                    GCCE_OPTIMIZATION_FLAGS,
                                    caseless = False )
#: Compiler flags for GCCE
WINSCW_OPTIMIZATION_FLAGS = GetArg( "winscw_options", "WINSCW compiler options.",
                                    WINSCW_OPTIMIZATION_FLAGS,
                                    caseless = False )


MMP_EXPORT_ENABLED = GetArg( "mmpexport", "Enable MMP export(if configured).", "false", [ "true", "false"] )
MMP_EXPORT_ENABLED = MMP_EXPORT_ENABLED == "true"

DO_CREATE_SIS = GetArg( "dosis", "Create SIS package.", str( DO_CREATE_SIS ).lower(), [ "true", "false"] )
DO_CREATE_SIS = (DO_CREATE_SIS == "true" )

DO_DUPLICATE_SOURCES = GetArg( "duplicate", "Duplicate sources to build dir.", "false", [ "true", "false"] )
DO_DUPLICATE_SOURCES = (DO_DUPLICATE_SOURCES in ["true", 1])

ENSYMBLE_AVAILABLE = False
try:
    if COMPILER != COMPILER_WINSCW and DO_CREATE_SIS:
        __import__( "ensymble" )
        ENSYMBLE_AVAILABLE = True
except ImportError:
    loginfo( "Automatic SIS creation requires Ensymble." )

if COMPILER == COMPILER_WINSCW:
    DO_CREATE_SIS = False

if not DO_CREATE_SIS:
    loginfo( "SIS creation disabled" )

#: Constant for ui platform version
UI_VERSION = ( 3, 0 )
#: Symbian version of the SDK
SYMBIAN_VERSION = ( 9 , 1 )

#: SDK platform header( generated )
#: S60 3rd & mr = EPOC32_INCLUDE + variant + symbian_os_v9.1.hrh
PLATFORM_HEADER = join( EPOC32_INCLUDE, "variant" )

def _resolve_platform():
    """Find out current SDK version"""
    global PLATFORM_HEADER, UI_PLATFORM, UI_VERSION, SYMBIAN_VERSION

    if not RUNNING_SCONS:
        return

    if not os.path.exists( PLATFORM_HEADER ):
        raise RuntimeError( "'%s' does not exist. Invalid EPOCROOT?" % PLATFORM_HEADER )

    # These are the same on S60
    sdk_header = ""
    symbian_header = ""

    uiplatform = UI_PLATFORM_S60
    uiversion = UI_VERSION

    files = os.listdir( PLATFORM_HEADER )
    files.sort()

    for fname in files:

        if fname.lower().startswith( "symbian_os" ) \
        and "vintulo" not in fname.lower():
            symbian_header = join( PLATFORM_HEADER, fname )

        elif fname.lower().startswith( "uiq" ):
            # symbian_header found earlier
            assert symbian_header != ""

            sdk_header = join( PLATFORM_HEADER, fname )
            uiplatform = UI_PLATFORM_UIQ
            uiversion = sdk_header.split( "_" )[1].split( ".hrh" )[0].split( "." )
            uiversion = map( int, uiversion )
            break

    if symbian_header == "":
        raise RuntimeError( "Unknown platform. Invalid EPOCROOT?" )


    if uiplatform == UI_PLATFORM_S60:
        # Use manifest.xml to get version for all S60 SDKs
        f = open( join( EPOC32, "kit", "manifest.xml" ) )
        d = f.read()
        f.close()

        symbian_version = d.split('osInfo version="')[-1].split('"')[0]
        symbian_version = symbian_version.split(".")[:2]

        uiversion = d.split('sdkVersion>')[1].split('<')[0]
        uiversion = uiversion.split(".")[:2]

        sdk_header = symbian_header

    else: #UIQ
        symbian_version = symbian_header.split( "_v" )[1].split( "." )[:2]

    PLATFORM_HEADER = sdk_header
    UI_PLATFORM = uiplatform
    UI_VERSION = tuple( map( int, uiversion ) )
    SYMBIAN_VERSION = tuple( map( int, symbian_version ) )

_resolve_platform()

#: Location for the packages. Value generated in run-time.
PACKAGE_FOLDER = abspath( join( "build%d_%d" % SYMBIAN_VERSION, "%s_%s" % ( COMPILER, RELEASE ), "packages" ) )

loginfo( "Symbian OS version = %d.%d" % SYMBIAN_VERSION )
loginfo( "UI platform        = %s" % UI_PLATFORM, "%d.%d" % UI_VERSION )

#: Built components. One SConstruct can define multiple SymbianPrograms.
#: This can be used from command-line to build only certain SymbianPrograms
COMPONENTS = GetArg( "components", "Components to build. Separate with ','.", "all" )
COMPONENTS_EXCLUDE = False

def __processComponents():
    global COMPONENTS_EXCLUDE

    components = COMPONENTS.lower().split( "," )
    if "all" in components:

        if len( components ) == 1: # if all only
            return None

        COMPONENTS_EXCLUDE = True
        components.remove( "all" )

    return components

COMPONENTS = __processComponents()

def __get_defines():
    "Ensure correct syntax for defined strings"

    tmp = GetArg( "defines", "Extra preprocessor defines. For debugging, etc.", None, caseless=False )
    if tmp is None: return []
    tmp = tmp.split( "," )

    defs = []
    for x in tmp:
        if "=" in x:
            name, value = x.split( "=" )
            if not value.isdigit():
                value = r'/"' + value + r'/"'

            x = "=".join( [name, value] )

        defs.append( x )
    return defs

#: Command-line define support
CMD_LINE_DEFINES = __get_defines()

#: Extra libraries( debug library etc. )
CMD_LINE_LIBS = GetArg( "extra_libs", "Extra libraries. Debug libraries, etc.", None )
if CMD_LINE_LIBS is not None:
    CMD_LINE_LIBS = CMD_LINE_LIBS.split( "," )

#: Default Symbian definitions.
STANDARD_DEFINES = [ "__SYMBIAN32__",
                     "_UNICODE",
                   ]

if SYMBIAN_VERSION[0] > 8:
  STANDARD_DEFINES += [ "__SUPPORT_CPP_EXCEPTIONS__" ]

# Add S60 macros
EXTRA_DEFINES = []
if UI_PLATFORM == UI_PLATFORM_S60:
    STANDARD_DEFINES += [ "__SERIES60_%d%d__" % UI_VERSION ]
    STANDARD_DEFINES += [ "__SERIES60_%dX__" % UI_VERSION[0] ]

    # Special rules for 5th edition
    # __S60_3X__ and __SERIES60_3X__ are correct here
    # TODO: Should these be read from e32plat.pl directly?
    if UI_VERSION[0] == 5:
        STANDARD_DEFINES += ['__S60_50__','__S60_3X__','__SERIES60_3X__']

    # Not in regular build scripts
    EXTRA_DEFINES += [ "__SERIES60__" ]


#Add UIQ macros
elif UI_PLATFORM == UI_PLATFORM_UIQ:
    # WARNING! These are not defined in regular UIQ build scripts
    # if you use these defines in your code, it becomes incompatible with them
    # You'll need to add these in your MMP with MACRO
    EXTRA_DEFINES += [ "__UIQ_%d%d__" % UI_VERSION ]
    EXTRA_DEFINES += [ "__UIQ_%dX__" % UI_VERSION[0] ]
    EXTRA_DEFINES += [ "__UIQ__" ]

EXTRA_DEFINES += [ "__SYMBIAN_OS_VERSION__=%d%d" % SYMBIAN_VERSION ]
EXTRA_DEFINES += [ "__UI_VERSION__=%d%d" % UI_VERSION ]

DEFAULT_SYMBIAN_DEFINES = STANDARD_DEFINES + EXTRA_DEFINES

if RELEASE == RELEASE_UREL:
    DEFAULT_SYMBIAN_DEFINES.append( "NDEBUG" )
else:
    DEFAULT_SYMBIAN_DEFINES.append( "_DEBUG" )

def get_output_folder( compiler, release, target, targettype ):
    p = os.path.join( "build" + "%d_%d" % SYMBIAN_VERSION, compiler + "_" + release, target + "_" + targettype )
    return os.path.abspath( p )

# Generate help message
def __generate_help_message():

    separator = "=" * 79 + "\n"
    # SCons gets into some kind of infinite loop if this file is imported directly
    # as it is done with EpyDoc.

    ENV = DefaultEnvironment( variables = VARS )
    msg = "SCons for Symbian arguments:\n"
    msg += separator
    msg += VARS.GenerateHelpText( ENV ).replace( "\n    a", " | a" )
    Help( msg )

    Help( separator )

#: Flag to disable processing to shorten time to display help message
HELP_ENABLED = False
for _x in [ "-h", "-H", "--help"]:
    if _x in sys.argv:
        HELP_ENABLED = True
        __generate_help_message()
        break

PATH_ARM_TOOLCHAIN = None
def checkGCCE():
    global PATH_ARM_TOOLCHAIN
    paths = _p.split( os.path.pathsep )
    for p in paths:
        try:
            items = os.listdir( p )
        except WindowsError, msg: # TODO: WindowsError on windows... how about linux?
            print msg
            continue

        for i in items:
            if i.startswith( "arm-none-symbianelf" ):
                PATH_ARM_TOOLCHAIN = p
                return True
    return False

# Check if GCCE setup is correct
#if len( PATH_ARM_TOOLCHAIN ) > 0:
#    PATH_ARM_TOOLCHAIN = PATH_ARM_TOOLCHAIN[0]
if RUNNING_SCONS:
    if not checkGCCE():
        print "\nERROR"
        print "-" * 79
        print "Error: Unable to find 'arm-none-symbianelf' tools from path. GCCE building is not possible."
        raise SystemExit( - 1 )#IGNORE:W1010

# Check if WINSCW is found
def __winscw_in_path():
    if COMPILER == COMPILER_WINSCW:
        for x in os.environ["PATH"].split( ";" ):
            if os.path.exists( x ):
                if "mwccsym2.exe" in [ x.lower() for x in os.listdir( x ) ]:
                    return True
        return False
    return True

if not __winscw_in_path() and RUNNING_SCONS:

    print "\nERROR"
    print "-" * 79
    print "WINSCW compiler 'mwccsym2.exe' not found from PATH."
    print "Install Carbide and run configuration\\run_env_update.bat"
    if not HELP_ENABLED and RUNNING_SCONS:
        raise SystemExit( - 1 )#IGNORE:W1010

del _p
del _x
