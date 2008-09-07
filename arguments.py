"""Reads and stores globals including the command line arguments"""

__author__    = "Jussi Toivola"
__license__   = "MIT License"

import sys
import os
from os.path import join

from SCons.Script import ARGUMENTS, Options, DefaultEnvironment, EnumOption, Variables, EnumVariable, Help

VARS = Variables('arguments.py')
def GetArg( name, help, default, allowed_values = None ):
    """Utility for adding help information and retrieving argument"""
    
    if allowed_values is not None:
        VARS.Add( EnumVariable( name, help, default, 
                    allowed_values = allowed_values,
                    ignorecase=2 ) )
    else:
        VARS.Add( name, help, default )            
    value = ARGUMENTS.get( name, default )
    if value is not None:
        value = value.lower()
    return value
    
                
# Constants -------------------------------------------------------------------

#: Easy constant for free caps
FREE_CAPS = "NetworkServices LocalServices ReadUserData " \
            "WriteUserData Location UserEnvironment PowerMgmt " \
            "ProtServ SwEvent SurroundingsDD ReadDeviceData " \
            "WriteDeviceData TrustedUI".split()
            
#: Symbian SDK folder
EPOCROOT = os.environ["EPOCROOT"]

COMPILER_WINSCW = "winscw"
COMPILER_GCCE   = "gcce"
COMPILERS = [COMPILER_WINSCW, COMPILER_GCCE ]

RELEASE_UREL    = "urel"
RELEASE_UDEB    = "udeb"
RELEASETYPES    =  [ RELEASE_UDEB, RELEASE_UREL ]

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

#: Types, which are compiled like dll( outputs lib )
DLL_TARGETTYPES = [ TARGETTYPE_PLUGIN, TARGETTYPE_DLL, TARGETTYPE_PYD, TARGETTYPE_LIB ]

#: Maps targettype to correct uid1
TARGETTYPE_UID_MAP = {
    TARGETTYPE_DLL : "0x10000079",
    TARGETTYPE_EXE : "0x1000007a",
    TARGETTYPE_LIB : "",
}
  


# End Constants ---------------------------------------------------------------
   
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
PATH_ARM_TOOLCHAIN = [ _x for _x in _p.split( os.path.pathsep ) if CSL_ARM_TOOLCHAIN_FOLDER_NAME in _x ]
if len( PATH_ARM_TOOLCHAIN) > 0:
    PATH_ARM_TOOLCHAIN = PATH_ARM_TOOLCHAIN[0]
else:
    print "Warning: Unable to find '%s' from path. GCCE building will fail." % CSL_ARM_TOOLCHAIN_FOLDER_NAME
        
# Parse arguments -------------------------------------------------------------

COMPILER   = GetArg( "compiler", "The compiler to use.", COMPILER_WINSCW, COMPILERS )

RELEASE    = GetArg( "release", "Release type.", RELEASE_UDEB, RELEASETYPES )

#: Constant pointing to EPOCROOT/epoc32
EPOC32         = join( EPOCROOT, 'epoc32' )
#: Constant pointing to system include folder
EPOC32_INCLUDE = join( EPOC32, 'include' )
#: Constant pointing to system tools folder
EPOC32_TOOLS   = join( EPOC32, 'tools' )
#: Constant pointing to release folder
EPOC32_RELEASE = join( EPOC32, "release", COMPILER, RELEASE )    
#: Constant pointing to emulator c drive
FOLDER_EMULATOR_C = join( EPOC32, "winscw", "c" )

INCLUDES = [ EPOC32_INCLUDE,
             join( EPOC32_INCLUDE, "variant" )
           ]


#: Location for the packages. Value generated in run-time.
PACKAGE_FOLDER = join( "%s_%s" % ( COMPILER, RELEASE ), "packages" )


DO_CREATE_SIS = GetArg( "dosis", "Create SIS package.", "false", [ "true", "false"] ) 
DO_CREATE_SIS = DO_CREATE_SIS == "true" 

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


#: Constant for S60 UI platform
UI_PLATFORM_S60 = "S60"
#: Constant for UIQ UI platform
UI_PLATFORM_UIQ = "UIQ"
#: List of possible UI platforms
UI_PLATFORMS    = [UI_PLATFORM_S60, UI_PLATFORM_UIQ]
#: Constant for current UI platform
#: One of UI_PLATFORMS
UI_PLATFORM = ""

#: Constant for ui platform version
UI_VERSION  = (3,0)

#: SDK platform header( generated )
#: S60 3rd & mr = EPOC32_INCLUDE + variant + symbian_os_v9.1.hrh
PLATFORM_HEADER = join( EPOC32_INCLUDE, "variant" )


def _resolve_platform():    
    """Find out current SDK version"""
    if not os.path.exists( PLATFORM_HEADER ):
        raise RuntimeError( "'%s' does not exist. Invalid EPOCROOT?" % PLATFORM_HEADER )
        
    # These are the same on S60
    sdk_header     = ""
    symbian_header = ""
    
    uiplatform = UI_PLATFORM_S60
    uiversion  = UI_VERSION
     
    files = os.listdir( PLATFORM_HEADER )
    files.sort()
    
    for fname in files:
            
        if fname.lower().startswith( "symbian_os") \
        and "vintulo" not in fname.lower():
            symbian_header = join( PLATFORM_HEADER, fname )
        
        elif fname.lower().startswith( "uiq"):
            # symbian_header found earlier 
            assert symbian_header != ""
                       
            sdk_header = join( PLATFORM_HEADER, fname )
            uiplatform = UI_PLATFORM_UIQ
            uiversion  = sdk_header.split("_")[1].split(".hrh")[0].split(".")
            uiversion  = map( int, uiversion )
            break
            
    if symbian_header == "": 
        raise RuntimeError( "Unknown platform. Invalid EPOCROOT?")
    
    symbian_version = symbian_header.split("_v")[1].split(".")[:2]
    
    if uiplatform == UI_PLATFORM_S60:
        # 9.2 FP1, 9.3 FP2
        mapping    = { "91" : (3,0), "92" : ( 3,1 ), "93" : ( 3.2 ) }        
        uiversion  = mapping[ "".join( symbian_version ) ]
        sdk_header = symbian_header
        
    return sdk_header, uiplatform,  \
            tuple( uiversion ),     \
            tuple( map( int, symbian_version ) )
    
PLATFORM_HEADER, UI_PLATFORM, UI_VERSION, SYMBIAN_VERSION = _resolve_platform()
          
print "Info: Symbian OS version = %d.%d" % SYMBIAN_VERSION
print "Info: UI platform        = %s"    % UI_PLATFORM, "%d.%d" % UI_VERSION
        
#: Built components. One SConstruct can define multiple SymbianPrograms.
#: This can be used from command-line to build only certain SymbianPrograms
COMPONENTS = GetArg( "components", "Components to build. Separate with ','.", "all" )
COMPONENTS = ( None if COMPONENTS == "all" else COMPONENTS )  

if COMPONENTS is not None:
    COMPONENTS = COMPONENTS.lower().split(",")

def __get_defines():
    "Ensure correct syntax for defined strings"
    
    tmp = GetArg( "defines", "Extra preprocessor defines. For debugging, etc.", None )
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
CMD_LINE_LIBS    = GetArg( "extra_libs", "Extra libraries. Debug libraries, etc.", None )
if CMD_LINE_LIBS is not None: 
    CMD_LINE_LIBS = CMD_LINE_LIBS.split(",")
    
#: SDK Installation folder
SDKFOLDER     =  os.path.join( EPOCROOT, 
                               "epoc32", 
                               "release", 
                               COMPILER,
                               RELEASE
                )

#: Default Symbian definitions.
DEFAULT_SYMBIAN_DEFINES = [ "__SYMBIAN32__",
                            "_UNICODE",                            
                            "__SUPPORT_CPP_EXCEPTIONS__",
                          ]

# Add S60 macros                             
if UI_PLATFORM == UI_PLATFORM_S60:        
    DEFAULT_SYMBIAN_DEFINES += [ "__SERIES60_%d%d__" % UI_VERSION ]    
    DEFAULT_SYMBIAN_DEFINES += [ "__SERIES60_%dX__"  % UI_VERSION[0] ]
    # Not in regular build scripts
    DEFAULT_SYMBIAN_DEFINES += [ "__SERIES60__" ]                           
#Add UIQ macros    
elif UI_PLATFORM == UI_PLATFORM_UIQ:
    # WARNING! These are not defined in regular UIQ build scripts
    # if you use these defines in your code, it becomes incompatible with them
    # You'll need to add these in your MMP with MACRO    
    DEFAULT_SYMBIAN_DEFINES += [ "__UIQ_%d%d__" % UI_VERSION ]
    DEFAULT_SYMBIAN_DEFINES += [ "__UIQ_%dX__"  % UI_VERSION[0] ]
    DEFAULT_SYMBIAN_DEFINES += [ "__UIQ__" ]

DEFAULT_SYMBIAN_DEFINES += [ "__SYMBIAN_OS_VERSION__=%d%d" % SYMBIAN_VERSION ]
DEFAULT_SYMBIAN_DEFINES += [ "__UI_VERSION__=%d%d" % UI_VERSION ]
                                            
if RELEASE == RELEASE_UREL:
    DEFAULT_SYMBIAN_DEFINES.append( "NDEBUG" )
else:
    DEFAULT_SYMBIAN_DEFINES.append( "_DEBUG" )

def get_output_folder(compiler, release, target, targettype ):
    return os.path.join( compiler + "_" + release, target + "_" + targettype )

# Generate help message
def __generate_help_message():
    # SCons gets into somekind of infinite loop if this file is imported directly
    # as it is done with EpyDoc.        
    ENV = DefaultEnvironment(variables = VARS )
    msg = "SCons for Symbian arguments:"
    msg += "\n" + "=" *  len( msg )
    msg += VARS.GenerateHelpText(ENV).replace( "\n    a", " | a") 
    Help( msg )    
    
#: Flag to disable processing to shorten time to display help message
HELP_ENABLED = False    
for _x in [ "-h", "-H", "--help"]:
    if _x in sys.argv:
        HELP_ENABLED = True
        __generate_help_message()
        break    

#if VARS.UnknownVariables():
#   print "Unknown variables:", VARS.UnknownVariables().keys()
#   print "To avoid this message, add your own"
#   print "variables with arguments.py->GetArg or use Variables()"
#   raise SystemExit()
   
   
del _p
del _x
#del x
