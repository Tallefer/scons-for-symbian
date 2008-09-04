"""
Environment for GCCE compiler

This file is part of SCons for Symbian project.

"""

__author__    = "Jussi Toivola"
__license__   = "MIT License"

import textwrap

import os
from os import path
from os.path import join

from arguments import *
#import spawn

from SCons.Builder     import Builder
from SCons.Environment import Environment

DEFAULT_GCCE_DEFINES = DEFAULT_SYMBIAN_DEFINES[:]
DEFAULT_GCCE_DEFINES += [
                        "__GCCE__",
                        "__EPOC32__",
                        "__MARM__",
                        "__EABI__",                        
                        "__MARM_ARMV5__",
                        ("__PRODUCT_INCLUDE__", '"%s"' % PLATFORM_HEADER )
                        ]

SYMBIAN_ARMV5_LIBPATH     = [ EPOCROOT ] + "epoc32 release armv5".split()
SYMBIAN_ARMV5_LIBPATHDSO  = join( *( SYMBIAN_ARMV5_LIBPATH + [ "lib" ] ) )   + path.sep
SYMBIAN_ARMV5_LIBPATHLIB  = join( *( SYMBIAN_ARMV5_LIBPATH + [ RELEASE ] ) ) + path.sep
 
SYMBIAN_ARMV5_BASE_LIBRARIES =  [ SYMBIAN_ARMV5_LIBPATHLIB + x + ".lib" for x in [ "usrt2_2" ] ]
SYMBIAN_ARMV5_BASE_LIBRARIES += [ SYMBIAN_ARMV5_LIBPATHDSO + x + ".dso" for x in [ "drtaeabi", "dfprvct2_2", "dfpaeabi", "scppnwdl" ,"drtrvct2_2" ] ]

# LIBARGS must be AFTER the libraries or we get "undefined reference to `__gxx_personality_v0'" when linking
WARNINGS =  "-Wall -Wno-ctor-dtor-privacy -Wno-unknown-pragmas -fexceptions " \
            "-march=armv5t -mapcs -pipe -nostdinc -msoft-float"

            
# These are enabled from FP1 onwards on regular scripts. Reduces size of the binaries.
GCCE_OPTIMIZATION_FLAGS = "-O2 -fno-unit-at-a-time"

def create_environment( target,
                        targettype,
                        includes,
                        libraries,
                        uid2,
                        uid3,
                        definput     = None,
                        capabilities = None,
                        defines      = None,
                        allowdlldata = True,
                        epocstacksize = None,
                        **kwargs ):
    """Create GCCE building environment
    @param allowdlldata: False to disable dll data support
    @type  allowdlldata: bool
    
    @param epocstacksize: Size of stack for executable.
    @type  epocstacksize: int
        
    @param kwargs: ignored keyword arguments.
    @see: L{scons_symbian.SymbianProgram}
    """

    if defines is None:
        defines = []
    
    if targettype in DLL_TARGETTYPES:
        defines.append( "__DLL__" )
    else:
        defines.append( "__EXE__" )
        
    defines.extend( DEFAULT_GCCE_DEFINES )
    defines.extend( CMD_LINE_DEFINES )
    

    LIBARGS   = [ "-lsupc++", "-lgcc" ]
    LIBPATH   = SYMBIAN_ARMV5_LIBPATHDSO
    
    # Add .dso if file extension does not exist
    for x in xrange( len( libraries ) ):
        lib = libraries[x]
        if "." not in lib:
            lib += ".dso"

        if ".dso" in lib.lower():
            libraries[x] = LIBPATH + lib
        else:
            libraries[x] = SYMBIAN_ARMV5_LIBPATHLIB + lib
            
    # GCCE uses .dso instead of .lib
    #LIBRARIES = [ LIBPATH + x.lower().replace(".lib", ".dso") for x in libraries ]#+ ".dso"
    if targettype == TARGETTYPE_EXE:
        libraries.append( SYMBIAN_ARMV5_LIBPATHDSO + "eikcore.dso" )
    else:
        # edllstub.lib must be just before euser.lib.. but they should not be first either.
        # Required for Tls::Dll
        # See: http://discussion.forum.nokia.com/forum/archive/index.php/t-59127.html
        for x in xrange(len(libraries)):
            lib = libraries[x]
            if lib.lower().endswith("euser.dso"):
                # Move to last
                libraries.remove( lib )
                libraries.append( SYMBIAN_ARMV5_LIBPATHLIB + "edllstub.lib" )
                libraries.append( lib )
                break
        
    libraries = libraries + SYMBIAN_ARMV5_BASE_LIBRARIES
    libraries += LIBARGS
   
    # Cleanup
    libraries = [ x.replace( "\\\\", "/") for x in libraries ]
    
    COMPILER_INCLUDE = os.path.abspath( join( EPOC32_INCLUDE, "gcce", "gcce.h" ) )

    # TODO: Cleanup following mess
    
    # Create linker flags
    LINKFLAGS     = r"""
                    --target1-abs --no-undefined -nostdlib
                    -shared -Ttext 0x8000 -Tdata 0x400000
                    --default-symver
                    -soname %(TARGET)s{%(UID2)s}[%(UID3)s].exe
                    """
    if targettype == TARGETTYPE_EXE:
        LINKFLAGS +="""
                    --entry _E32Startup  -u _E32Startup
                    """
    else:
        LINKFLAGS +="""
                    --entry _E32Dll  -u _E32Dll
                    """
    
    LINKFLAGS     +=r"""
                    %(EPOCROOT)sepoc32/release/armv5/urel/edll.lib
                    -Map %(EPOCROOT)sepoc32/release/gcce/urel/%(TARGET)s.%(TARGETTYPE)s.map
                    """

    if targettype == TARGETTYPE_EXE:
        LINKFLAGS = LINKFLAGS.replace( "edll.lib", "eexe.lib" )

    LINKFLAGS = textwrap.dedent( LINKFLAGS )
    LINKFLAGS = " ".join( [ x.strip() for x in LINKFLAGS.split("\n") ] )

    LINKFLAGS = LINKFLAGS % {"UID2"   : uid2,
                             "UID3"   : uid3,
                             "TARGET" : target,
                             "TARGETTYPE"   : targettype,
                             "EPOCROOT" : EPOCROOT }
    
    #--vid=0x00000000
    ELF2E32 =   r"""
                %(EPOCROOT)sepoc32/tools/elf2e32 --sid=%(UID3)s
                --uid1=%(UID1)s --uid2=%(UID2)s --uid3=%(UID3)s
                --capability=%(CAPABILITIES)s
                --fpu=softvfp --targettype=%(TARGETTYPE)s
                --output=$TARGET
                %(DEFCONFIG)s
                --elfinput="%(WORKING_DIR)s/$SOURCE"
                --linkas=%(TARGET)s{000a0000}.%(TARGETTYPE)s
                --libpath="%(EPOCROOT)sepoc32/release/armv5/lib"
                """
    if allowdlldata and targettype in DLL_TARGETTYPES:
        ELF2E32 += "--dlldata "
    
    if epocstacksize is not None and targettype == TARGETTYPE_EXE:
        ELF2E32 += "--stack=" + "0x" + hex( epocstacksize ).replace("0x","").zfill( 8 )
         
    ELF2E32 = textwrap.dedent( ELF2E32 )
    ELF2E32 = " ".join( [ x.strip() for x in ELF2E32.split("\n") ] )

    defconfig = ""
    # Based on targettype
    #uid1 = "0x1000007a" # Exe
    uid1 = ""
    elf_targettype = ""
    if targettype in DLL_TARGETTYPES:
        uid1 = TARGETTYPE_UID_MAP[TARGETTYPE_DLL]
        elf_targettype = TARGETTYPE_DLL
    else:
        uid1 = TARGETTYPE_UID_MAP[targettype]
        elf_targettype = TARGETTYPE_EXE

    if targettype in DLL_TARGETTYPES:

        defconfig = []
        if definput is not None:
            definput = os.path.abspath( definput )
            defconfig +=  ["--definput " + definput]
        defconfig += ["--defoutput " + target + "{000a0000}.def" ]
        defconfig += ["--unfrozen" ]
        defconfig += ["--dso " + os.environ["EPOCROOT"] + "epoc32/release/ARMV5/LIB/" + target + ".dso"]
        defconfig = " ".join( defconfig )
        
        uid1 = TARGETTYPE_UID_MAP[TARGETTYPE_DLL]#"0x10000079" # DLL
    
    env = Environment (
                    tools = ["mingw"], # Disable searching of tools
                    ENV = os.environ,
                    # Static library settings
                    AR  = r'arm-none-symbianelf-ar',
                    RANLIBCOM = "",
                    LIBPREFIX = "",
                    
                    # Compiler settings
                    CC  = r'arm-none-symbianelf-g++',
                    CFLAGS = WARNINGS +  " -x c -include " + COMPILER_INCLUDE,
                    
                    CXX = r'arm-none-symbianelf-g++',
                    CXXFLAGS = WARNINGS + " " + GCCE_OPTIMIZATION_FLAGS + " -x c++ -include " + COMPILER_INCLUDE,
                    CPPPATH = INCLUDES + includes,
                    CPPDEFINES = defines,
                    INCPREFIX = "-I ",
                    
                    # Linker settings
                    LINK    = r'"arm-none-symbianelf-ld"',
                    LIBPATH = [ PATH_ARM_TOOLCHAIN + x for x in [
                                r"/../lib/gcc/arm-none-symbianelf/3.4.3",
                                r"/../arm-none-symbianelf/lib"
                                ] 
                              ],
                    LINKFLAGS     = LINKFLAGS,
                    LIBS          = libraries,
                    LIBLINKPREFIX = " ",
                    PROGSUFFIX    = ".noelfexe"
                )
    
    # Add GCC binaries to path head, so we are sure to use them instead of some other (Cygwin, Carbide)
    # TODO: Windows specific
    env.PrependENVPath('PATH', 'C:\\Program Files\\CSL Arm Toolchain\\libexec\\gcc\\arm-none-symbianelf\\3.4.3')
    env.PrependENVPath('PATH', 'C:\\Program Files\\CSL Arm Toolchain\\arm-none-symbianelf\\bin')     
    
    
    
    # Add special builders------------------------------------------------------

    # Elf2e32 converter
    elf2e32_cmd = ELF2E32 % { "EPOCROOT"    : EPOCROOT,
                          "CAPABILITIES": "+".join( capabilities ),
                          "TARGET"      : target,
                          "release"     : RELEASE,
                          "WORKING_DIR" : os.path.abspath("."),
                          "TARGETTYPE"  : elf_targettype,
                          "UID1"        : uid1,
                          "UID2"        : uid2,
                          "UID3"        : uid3,
                          "DEFCONFIG"   : defconfig }
 
    elf2e32_builder = Builder( action     = elf2e32_cmd.replace("\\", "/"),
                       src_suffix = ".noelfexe",
                       suffix     = "." + targettype,
                       single_source = True,
                     )
    env.Append( BUILDERS = { "Elf" : elf2e32_builder } )
    
    #env["SPAWN"] = spawn.win32_spawn
    
    return env
