"""
Environment for GCCE compiler

This file is part of SCons for Symbian project.

"""

__author__ = "Jussi Toivola"
__license__ = "MIT License"

from SCons.Builder import Builder
from SCons.Environment import Environment
from arguments import * #IGNORE:W0611
import arguments as ARGS
from os import path
from os.path import join
import os
import textwrap

USE_DISTCC = False
if "DISTCC_HOSTS" in os.environ:
  if os.environ["DISTCC_HOSTS"] != "":
    USE_DISTCC= True

DEFAULT_GCCE_DEFINES = DEFAULT_SYMBIAN_DEFINES[:]
DEFAULT_GCCE_DEFINES += [
                        "__GCCE__",
                        "__EPOC32__",
                        "__MARM__",
                        "__EABI__",
                        "__MARM_ARMV5__",
                        ( "__PRODUCT_INCLUDE__", r'%s' % PLATFORM_HEADER.replace("\\", "/") )
                          if USE_DISTCC else
                        ( "__PRODUCT_INCLUDE__", r'\"%s\"' % PLATFORM_HEADER.replace("\\", "/") )
                        ]

SYMBIAN_ARMV5_LIBPATH = [ EPOCROOT ] + "epoc32 release armv5".split()
SYMBIAN_ARMV5_LIBPATHDSO = join( *( SYMBIAN_ARMV5_LIBPATH + [ "lib" ] ) ) + path.sep
SYMBIAN_ARMV5_LIBPATHLIB = join( *( SYMBIAN_ARMV5_LIBPATH + [ RELEASE ] ) ) + path.sep

SYMBIAN_ARMV5_BASE_LIBRARIES = [ SYMBIAN_ARMV5_LIBPATHLIB + __x + ".lib" for __x in [ "usrt2_2" ] ]
DSO_LIBS = [ "drtaeabi", "dfprvct2_2", "dfpaeabi", "scppnwdl" , "drtrvct2_2" ]
SYMBIAN_ARMV5_BASE_LIBRARIES += [ SYMBIAN_ARMV5_LIBPATHDSO + __x + ".dso" for __x in DSO_LIBS ]

# LIBARGS must be AFTER the libraries or we get "undefined reference to `__gxx_personality_v0'" when linking
WARNINGS_C = "-Wall -Wno-unknown-pragmas -fexceptions " \
            "-march=armv5t -mapcs -pipe -nostdinc -msoft-float"
WARNINGS_CXX = WARNINGS_C + " -Wno-ctor-dtor-privacy"


#: Environment cache
_GCCE_ENV = None

def create_environment( target,
                        targettype,
                        includes,
                        sysincludes,
                        libraries,
                        user_libraries,
                        uid2,
                        uid3,
                        sid = None,
                        definput = None,
                        defoutput = None,
                        capabilities = None,
                        defines = None,
                        allowdlldata = True,
                        epocstacksize = None,
                        epocheapsize = None,
                        gcce_options = None,
                        elf2e32_args = None,
                        **kwargs ):
    """Create GCCE building environment

    @param allowdlldata: False to disable dll data support
    @type  allowdlldata: bool

    @param epocstacksize: Size of stack for executable.
    @type  epocstacksize: int

    @param epocheapsize: Minimum and maximum heap size
    @type epocheapsize: 2-tuple( int, int )
    @param kwargs: ignored keyword arguments.
    @see: L{scons_symbian.SymbianProgram}
    """


    defines = defines[:]

    if gcce_options is None:
        gcce_options = GCCE_OPTIMIZATION_FLAGS

    if targettype != TARGETTYPE_LIB:
        if targettype in DLL_TARGETTYPES:
            defines.append( "__DLL__" )
        else:
            defines.append( "__EXE__" )

    defines.extend( DEFAULT_GCCE_DEFINES )
    defines.extend( CMD_LINE_DEFINES )

    LIBARGS = [ "-lsupc++", "-lgcc" ]
    LIBPATH = SYMBIAN_ARMV5_LIBPATHDSO

    for x in xrange( len( libraries ) ):
        lib = libraries[x]
        # GCCE uses .dso instead of .lib for dynamic libs. .lib indicates
        # static lib

        # Add .dso if file extension does not exist
        if "." not in lib:
            lib += ".dso"

        if ".dso" in lib.lower():
            libraries[x] = LIBPATH + lib
        elif not lib.endswith(".o"): # Allows prebuilt object files
            libraries[x] = SYMBIAN_ARMV5_LIBPATHLIB + lib

    if targettype == TARGETTYPE_EXE:
        libraries.append( SYMBIAN_ARMV5_LIBPATHDSO + "eikcore.dso" )
    else:
        # edllstub.lib must be just before euser.lib.. but they should not be first either.
        # Required for Tls::Dll
        # See: http://discussion.forum.nokia.com/forum/archive/index.php/t-59127.html
        for x in xrange( len( libraries ) ):
            lib = libraries[x]
            if lib.lower().endswith( "euser.dso" ):
                # Move to last
                libraries.remove( lib )
                libraries.append( SYMBIAN_ARMV5_LIBPATHLIB + "edllstub.lib" )
                libraries.append( lib )
                break

    USER_LIBPATH = join(ARGS.INSTALL_EPOC32, "release", "armv5", RELEASE)
    USER_DSOPATH = join(ARGS.INSTALL_EPOC32, "release", "armv5", "lib")
    for x in xrange( len( user_libraries ) ):
        lib = user_libraries[x]
        if "." not in lib:
            lib += ".dso"

        if ".dso" in lib.lower():
            user_libraries[x] = join(USER_DSOPATH, lib)
        elif not lib.endswith(".o"): # Allows prebuilt object files
            user_libraries[x] = join(USER_LIBPATH, lib)

    # Link to user_libraries first so that they can override symbols
    libraries = [ os.path.normpath( x ).lower() for x in user_libraries ] + libraries
    libraries = libraries + SYMBIAN_ARMV5_BASE_LIBRARIES
    libraries += LIBARGS

    # Cleanup
    libraries = [ x.replace( "\\\\", "/" ) for x in libraries ]

    COMPILER_INCLUDE = os.path.abspath( join( EPOC32_INCLUDE, "gcce", "gcce.h" ) )

    # TODO: Cleanup following mess

    # Create linker flags
    LINKFLAGS = r"""
                    --target1-abs --no-undefined -nostdlib
                    -shared -Ttext 0x8000 -Tdata 0x400000
                    --default-symver
                    """
    if targettype == TARGETTYPE_EXE:
        LINKFLAGS += """
                    -soname %(TARGET)s{%(UID2)s}[%(UID3)s].exe
                    --entry _E32Startup -u _E32Startup
                    %(EPOCROOT)sepoc32/release/armv5/urel/eexe.lib
                    """
    else:
        LINKFLAGS += """
                    -soname %(TARGET)s{%(UID2)s}[%(UID3)s].dll
                    --entry _E32Dll -u _E32Dll
                    %(EPOCROOT)sepoc32/release/armv5/urel/edll.lib
                    """

    LINKFLAGS += r"""
                  -Map %(INSTALL_EPOCROOT)s/epoc32/release/gcce/%(RELEASE)s/%(TARGET)s.%(TARGETTYPE)s.map
                  """

    LINKFLAGS = textwrap.dedent( LINKFLAGS )
    LINKFLAGS = " ".join( [ x.strip() for x in LINKFLAGS.split( "\n" ) ] )

    LINKFLAGS = LINKFLAGS % {"UID2"   : uid2,
                             "UID3"   : uid3,
                             "TARGET" : target,
                             "TARGETTYPE"   : targettype,
                             "EPOCROOT" : ARGS.EPOCROOT,
                             "INSTALL_EPOCROOT" : ARGS.INSTALL_EPOCROOT,
                             "RELEASE" : ARGS.RELEASE }

    #--vid=0x00000000
    ELF2E32 = r"""
                %(EPOCROOT)sepoc32/tools/elf2e32 --sid=%(SID)s
                --uid1=%(UID1)s --uid2=%(UID2)s --uid3=%(UID3)s
                --capability=%(CAPABILITIES)s
                --fpu=softvfp --targettype=%(TARGETTYPE)s
                --output=$TARGET
                %(DEFCONFIG)s
                --elfinput="%(WORKING_DIR)s$SOURCE"
                --linkas=%(TARGET)s{000a0000}.%(TARGETTYPE)s
                --libpath="%(EPOCROOT)sepoc32/release/armv5/lib"
                """
    if allowdlldata and targettype in DLL_TARGETTYPES:
        ELF2E32 += "--dlldata "

    if epocstacksize is not None and targettype == TARGETTYPE_EXE:
        ELF2E32 += "--stack=" + "0x" + hex( epocstacksize ).replace( "0x", "" ).zfill( 8 )
    # TODO: Defined in both gcce.py and winscw.py. Relocate check to upper level
    if epocheapsize is not None and targettype == TARGETTYPE_EXE:
        assert type( epocheapsize ) == tuple, "epocheapsize must be 2-tuple( minsize, maxsize )"
        assert epocheapsize[0] >= 0x1000, "minimum heapsize must be at least 0x1000(4kb)"
        min = hex( epocheapsize[0] ).replace("0x", "").zfill(8)
        max = hex( epocheapsize[1] ).replace("0x", "").zfill(8)
        ELF2E32 += " --heap=0x%s,0x%s " % ( min, max )

    ELF2E32 = textwrap.dedent( ELF2E32 )
    ELF2E32 = " ".join( [ x.strip() for x in ELF2E32.split( "\n" ) ] )
    if elf2e32_args is not None:
        ELF2E32 += " " + elf2e32_args

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
            defconfig += ["--definput " + definput]
        defconfig += ["--defoutput " + defoutput ]
        defconfig += ["--unfrozen" ]
        defconfig += ["--dso " + ARGS.INSTALL_EPOCROOT + "epoc32/release/ARMV5/LIB/" + target + ".dso"]
        defconfig = " ".join( defconfig )

        uid1 = TARGETTYPE_UID_MAP[TARGETTYPE_DLL]#"0x10000079" # DLL


    global _GCCE_ENV
    if _GCCE_ENV is None:
        _GCCE_ENV = Environment (
                    tools = ["mingw"], # Disable searching of tools
                    ENV = os.environ,
                    # Static library settings
                    AR = r'arm-none-symbianelf-ar',
                    RANLIBCOM = "",
                    LIBPREFIX = "",

                    # Compiler settings

                    CC = (r'\cygwin\bin\distcc.exe arm-none-symbianelf-g++.wrapper')
                           if USE_DISTCC else
                         (r'arm-none-symbianelf-g++'),

                    CFLAGS = (WARNINGS_C + " " + gcce_options + " -include " + COMPILER_INCLUDE)
                             if USE_DISTCC else
                             (WARNINGS_C + " " + gcce_options + " -x c -include " + COMPILER_INCLUDE),

                    CXX = (r'\cygwin\bin\distcc.exe arm-none-symbianelf-g++.wrapper')
                            if USE_DISTCC else                    
                          (r'arm-none-symbianelf-g++'),

                    CXXFLAGS = (WARNINGS_CXX + " " + gcce_options + " -include %s " % ( COMPILER_INCLUDE ))
                                 if USE_DISTCC else
                               (WARNINGS_CXX + " " + gcce_options + " -x c++ -include %s " % ( COMPILER_INCLUDE )),

                    # isystem does not work so just adding the system include paths before normal includes.
                    CPPPATH = sysincludes + includes,
                    CPPDEFINES = defines,
                    INCPREFIX = "-I ",

                    # Linker settings
                    LINK = r'"arm-none-symbianelf-ld"',
                    LIBPATH = [ PATH_ARM_TOOLCHAIN + x for x in [
                                r"/../lib/gcc/arm-none-symbianelf/3.4.3",
                                r"/../arm-none-symbianelf/lib"
                                ]
                              ],
                    LINKFLAGS = LINKFLAGS,
                    LIBS = libraries,
                    LIBLINKPREFIX = " ",
                    PROGSUFFIX = ".noelfexe"
                )
        env = _GCCE_ENV
    else:
        # A lot faster than creating the environment from scratch
        env = _GCCE_ENV.Clone()

    env.Replace(
        ENV = os.environ,

        CFLAGS = (WARNINGS_C + " " + gcce_options + " -include " + COMPILER_INCLUDE)
                   if USE_DISTCC else
                 (WARNINGS_C + " " + gcce_options + " -x c -include " + COMPILER_INCLUDE),

        CXXFLAGS = (WARNINGS_CXX + " " + gcce_options + " -include %s " % ( COMPILER_INCLUDE ))
                     if USE_DISTCC else
                   (WARNINGS_CXX + " " + gcce_options + " -x c++ -include %s " % ( COMPILER_INCLUDE )),

        # isystem does not work so just adding the system include paths before normal includes.
        CPPPATH = sysincludes + includes,
        CPPDEFINES = defines,

        # Linker settings
        LINKFLAGS = LINKFLAGS,
        LIBS = libraries,
    )


    # Add GCC binaries to path head, so we are sure to use them instead of some other (Cygwin, Carbide)
    # TODO: Windows specific
    # Commented out... these really don't belong here.
    # What if somebody uses different path or another GCCE compiler version?... like I do.
    #env.PrependENVPath( 'PATH', 'C:\\Program Files\\CSL Arm Toolchain\\libexec\\gcc\\arm-none-symbianelf\\3.4.3' )
    #env.PrependENVPath( 'PATH', 'C:\\Program Files\\CSL Arm Toolchain\\arm-none-symbianelf\\bin' )

    # Add special builders------------------------------------------------------

    # Elf2e32 converter
    capabilities_string = "+".join( capabilities )
    if len(capabilities_string) == 0:
      capabilities_string = "NONE"
    elf2e32_cmd = ELF2E32 % { "EPOCROOT"    : EPOCROOT,
                          "CAPABILITIES": capabilities_string,
                          "TARGET"      : target,
                          "release"     : RELEASE,
                          "WORKING_DIR" : "",#os.path.abspath( "." ),
                          "TARGETTYPE"  : elf_targettype,
                          "UID1"        : uid1,
                          "UID2"        : uid2,
                          "UID3"        : uid3,
                          "SID"         : sid,
                          "DEFCONFIG"   : defconfig }

    elf2e32_builder = Builder( action = elf2e32_cmd.replace( "\\", "/" ),
                       src_suffix = ".noelfexe",
                       suffix = "." + targettype,
                       single_source = True,
                     )
    env.Append( BUILDERS = { "Elf" : elf2e32_builder } )

    #env["SPAWN"] = spawn.win32_spawn

    return env
