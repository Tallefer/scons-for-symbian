"""Reads and stores globals including the command line arguments"""

import sys
import os
from os.path import join

from SCons.Script import ARGUMENTS, Options, EnumOption

# Constants -------------------------------------------------------------------
#: Symbian SDK folder
EPOCROOT = os.environ["EPOCROOT"]

COMPILER_WINSCW = "winscw"
COMPILER_GCCE   = "gcce"
RELEASE_UREL    = "urel"
RELEASE_UDEB    = "udeb"

TARGETTYPE_DLL    = "dll"
TARGETTYPE_EXE    = "exe"
TARGETTYPE_LIB    = "lib"
TARGETTYPE_PLUGIN = "plugin"
TARGETTYPE_PYD    = "pyd"
    
#: List of possible targettypes
TARGETTYPES       = [ TARGETTYPE_DLL,
                      TARGETTYPE_EXE,
                      TARGETTYPE_LIB,
                      TARGETTYPE_PLUGIN,
                      TARGETTYPE_PYD ]

#: Types, which are compiled not like exe.
DLL_TARGETTYPES = [ TARGETTYPE_DLL, TARGETTYPE_PYD, TARGETTYPE_LIB ]

#: Maps targettype to correct uid1
TARGETTYPE_UID_MAP = {
    TARGETTYPE_DLL : "0x10000079",
    TARGETTYPE_EXE : "0x1000007a",
    TARGETTYPE_LIB : "",
}


INCLUDES = [ join( EPOCROOT, 'epoc32', 'include' ),
             join( EPOCROOT, "epoc32", "include", "variant" )
             #r'D:/Symbian/CSL Arm Toolchain/bin/../lib/gcc/arm-none-symbianelf/3.4.3/include'
           ]
           
   
# End Constants ---------------------------------------------------------------

#: 
#: Remove drive name from EPOCROOT
#: Some Symbian tools requires this. TODO: Rewrite 'em and get rid of this thing!    
if ":" in EPOCROOT: 
    EPOCROOT = EPOCROOT.split(":",1)[-1]
    
print "EPOCROOT=%s" % EPOCROOT
if sys.platform == "win32":
    os.environ["EPOCROOT"] = EPOCROOT.replace("/", "\\")
else:
    os.environ["EPOCROOT"] = EPOCROOT

_p = os.environ["PATH"]
CSL_ARM_TOOLCHAIN_FOLDER_NAME = "CSL Arm Toolchain\\bin"
if sys.platform == "linux2":
    CSL_ARM_TOOLCHAIN_FOLDER_NAME = "csl-gcc/bin"
    
#: Path to arm toolchain. Detected automatically from path using 'CSL Arm Toolchain' on Windows or csl-gcc on Linux
PATH_ARM_TOOLCHAIN = [ _x for _x in _p.split( os.path.pathsep ) if CSL_ARM_TOOLCHAIN_FOLDER_NAME in _x ][0]

# Parse arguments -------------------------------------------------------------
opt = Options(None, ARGUMENTS)
opt.AddOptions(
         EnumOption(
          'compiler',
          'The compiler you want to use',
          'winscw',
          ['gcce','gcce'],
          {'winscw':'winscw'}))

#: Used compiler
COMPILER   = ARGUMENTS.get( "compiler", COMPILER_WINSCW ).lower()

#: Urel/Udeb
RELEASE    = ARGUMENTS.get( "release",  RELEASE_UDEB ).lower()

PACKAGE_FOLDER = join( "%s_%s" % ( COMPILER, RELEASE ), "packages" )

DO_CREATE_SIS = ( ARGUMENTS.get( "dosis",  "False" ).capitalize() == "True" )
ENSYMBLE_AVAILABLE = False
try:
    if COMPILER != COMPILER_WINSCW and DO_CREATE_SIS:
        import ensymble
        ENSYMBLE_AVAILABLE = True
except ImportError:
    print "Info: Automatic SIS creation requires Ensymble."

if COMPILER == COMPILER_WINSCW:
    DO_CREATE_SIS = False
    
if not DO_CREATE_SIS:
    print "Info: SIS creation disabled"

#: Built components. One SConstruct can define multiple SymbianPrograms.
#: This can be used from command-line to build only certain SymbianPrograms
COMPONENTS = ARGUMENTS.get( "components",  None )
if COMPONENTS is not None:
    COMPONENTS = COMPONENTS.lower().split(",")

def __get_defines():
    "Ensure correct syntax for defined strings"
    tmp = ARGUMENTS.get( "defines",  None )
    if tmp is None: return []
    tmp = tmp.split(",")

    defs = []
    for x in tmp:
        if "=" in x:
            name, value = x.split("=")
            if not value.isdigit():
                value = r'/"' + value + r'/"'

            x = "=".join( [name, value] )

        defs.append(x)
    return defs

#: Command-line define support
CMD_LINE_DEFINES = __get_defines()

#: Extra libraries( debug library etc. )
CMD_LINE_LIBS    = ARGUMENTS.get( "extra_libs", None )
if CMD_LINE_LIBS is not None: 
    CMD_LINE_LIBS = CMD_LINE_LIBS.split(",")
    
#: SDK Installation folder
SDKFOLDER     =  os.path.join( EPOCROOT, 
                               "epoc32", 
                               "release", 
                               COMPILER,
                               RELEASE
                )

#: Default Symbian definitions. TODO: Use UIQ macros on UIQ
DEFAULT_SYMBIAN_DEFINES = [ "__SYMBIAN32__",
                            "_UNICODE",
                            "__SERIES60_30__",
                            "__SERIES60_3X__",
                            "__SUPPORT_CPP_EXCEPTIONS__",
                             ]

if RELEASE == RELEASE_UREL:
    DEFAULT_SYMBIAN_DEFINES.append( "NDEBUG" )
else:
    DEFAULT_SYMBIAN_DEFINES.append( "_DEBUG" )

def get_output_folder(compiler, release, target, targettype ):
    return os.path.join( compiler + "_" + release, target + "_" + targettype )