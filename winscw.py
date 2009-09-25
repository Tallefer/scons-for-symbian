"""Environment for WINSCW compiler"""

__author__ = "Jussi Toivola"
__license__ = "MIT License"

from SCons.Environment import Environment
from arguments import * #IGNORE:W0611
import arguments as ARGS
import textwrap

DEFAULT_WINSCW_DEFINES = DEFAULT_SYMBIAN_DEFINES[:]
DEFAULT_WINSCW_DEFINES += [
                        "__CW32__",
                        "__WINS__",
                        "__WINSCW__"
                        ]
SYMBIAN_WINSCW_LIBPATHLIB = EPOCROOT + r"epoc32/release/winscw/udeb/"

#: UID.cpp for WINSCW simulator
TARGET_UID_CPP_TEMPLATE_DLL = r"""
// scons-generated uid source file
#include <e32cmn.h>
#pragma data_seg(".SYMBIAN")
__EMULATOR_IMAGE_HEADER2(0x10000079,0x00000000,0x00000000,EPriorityForeground,%(CAPABILITIES)su,0x00000000u,0x00000000,0,0x00010000,0)
#pragma data_seg()
"""
#: UID.cpp for WINSCW simulator
TARGET_UID_CPP_TEMPLATE_EXE = r"""
// scons-generated uid source file
#include <e32cmn.h>
#pragma data_seg(".SYMBIAN")
__EMULATOR_IMAGE_HEADER2(0x1000007a,0x100039ce,%(UID3)s,EPriorityForeground,%(CAPABILITIES)su,0x00000000u,%(SID)s,0x00000000,0x00010000,0)
#pragma data_seg()
"""


CAPABILITY_MAP = {
        "NONE" : 0,
        "TCB" : (1<<0),
        "COMMDD" :                 (1<<1),
        "POWERMGMT" :             (1<<2),
        "MULTIMEDIADD" :             (1<<3),
        "READDEVICEDATA" :         (1<<4),
        "WRITEDEVICEDATA" :         (1<<5),
        "DRM" :                     (1<<6),
        "TRUSTEDUI" :             (1<<7),
        "PROTSERV" :                 (1<<8),
        "DISKADMIN" :             (1<<9),
        "NETWORKCONTROL" :         (1<<10),
        "ALLFILES" :                 (1<<11),
        "SWEVENT" :                 (1<<12),
        "NETWORKSERVICES" :         (1<<13),
        "LOCALSERVICES" :         (1<<14),
        "READUSERDATA" :             (1<<15),
        "WRITEUSERDATA" :         (1<<16),
        "LOCATION" :                 (1<<17),
        "SURROUNDINGSDD" :         (1<<18),
        "USERENVIRONMENT" :         (1<<19),
}

def make_capability_hex(capabilities):
    result = 0
    for cap in capabilities:
        val = CAPABILITY_MAP[cap.upper()]
        result += val
    return "0x" + hex(result)[2:].zfill(8)

_WINSCW_ENV = None

def make_default_environment():
    global _WINSCW_ENV
    if _WINSCW_ENV is not None:
        return _WINSCW_ENV.Clone()

    platform_header = PLATFORM_HEADER#os.path.basename( PLATFORM_HEADER )
    #import pdb;pdb.set_trace()
    sysincludes = " "
    cc_flags = '-g -O0 -inline off -wchar_t off -align 4 -warnings on -w nohidevirtual,nounusedexpr -msgstyle gcc -enum int -str pool -exc ms -trigraphs on  -nostdinc'
    _WINSCW_ENV = Environment(
                    tools = ["mingw"], # Disable searching of tools

                    CC = r'mwccsym2',
                    CXX = r'mwccsym2',

                    ENV = os.environ, #os.environ['PATH'],
                    # Static library settings
                    AR = r'mwldsym2',
                    ARFLAGS = "-library -msgstyle gcc -stdlib -subsystem windows -noimplib -o",
                    RANLIBCOM = "",
                    LIBPREFIX = "",

                    CPPPATH = "",
                    CPPDEFINES = DEFAULT_WINSCW_DEFINES + CMD_LINE_DEFINES,
                    CCFLAGS = cc_flags + ' -cwd source -I- %s -include "%s"' % ( sysincludes, platform_header ),
                    INCPREFIX = "-i ",
                    CPPDEFPREFIX = "-d ",

                    # Linker settings
                    LINK = r'mwldsym2',
                    LINKFLAGS = "",
                    LIBS = "",
                    LIBLINKPREFIX = " "

        )

    return _WINSCW_ENV

def create_environment( target,
                        targettype,
                        includes,
                        sysincludes,
                        libraries,
                        user_libraries,
                        epocheapsize = None,
                        epocstacksize = None,
                        winscw_options = None,
                        win32_libraries = None,
                        win32_subsystem = None,
                        *args,
                        **kwargs
                        ):
    """Create WINSCW environment
    @param kwargs: ignored keyword arguments.
    @see: L{scons_symbian.SymbianProgram}
    """

    winscw_options = winscw_options   or WINSCW_OPTIMIZATION_FLAGS
    win32_subsystem = win32_subsystem or "windows"
    win32_libraries = win32_libraries or []

    defines = kwargs["defines"][:]
    for x in xrange( len( libraries ) ):
        lib = libraries[x]
        if "." not in lib:
            libraries[x] = lib + ".lib"

    OUTPUT_FOLDER = get_output_folder( COMPILER, RELEASE, target, targettype )

    LIBPATH = SYMBIAN_WINSCW_LIBPATHLIB
    USER_LIBPATH = ARGS.INSTALL_EPOC32_RELEASE
    # Link first against user_libraries so that they can override symbols
    LIBRARIES = (
        [ os.path.normpath( os.path.join(USER_LIBPATH, x) ).lower() for x in user_libraries ] +
        [ os.path.normpath( LIBPATH + x ).lower() for x in libraries ] +
        win32_libraries )
    defines.extend( DEFAULT_WINSCW_DEFINES )
    defines.extend( CMD_LINE_DEFINES )

    # TODO: Take lib out of DLL_TARGETTYPES
    if targettype != TARGETTYPE_LIB:
        if targettype in DLL_TARGETTYPES:
            defines.append( "__DLL__" )
            LIBRARIES.append( join(EPOC32_RELEASE, "edll.lib") )
        else:
            defines.append( "__EXE__" )
            LIBRARIES.append( join(EPOC32_RELEASE, "eexe.lib") )
    defines = [ '"%s"' % x for x in defines ]

    cc_flags = '-g -O0 -inline off -wchar_t off -align 4 -warnings on -w nohidevirtual,nounusedexpr -msgstyle gcc -enum int -str pool -exc ms -trigraphs on  -nostdinc'
    cc_flags = " ".join( [cc_flags, winscw_options ] )

     #%(EPOCROOT)sepoc32/RELEASE/WINSCW/UDEB/euser.lib %(EPOCROOT)sepoc32/release/WINSCW/UDEB/efsrv.lib
    LINKFLAGS = ""
    search_flag = ""
    if win32_libraries:
      # win32 libraries live in the linker's standard library folder, we don't
      # want to look for them, let the linker do that.
      search_flag = "-search"
    if targettype in DLL_TARGETTYPES:
        LINKFLAGS = " ".join( [
                    '-msgstyle gcc',
                    '-stdlib',
                    '-noentry -shared',
                    '-subsystem %s' % win32_subsystem,
                    '-g',
                    '-export dllexport',
                    '-m __E32Dll',
                    '-nocompactimportlib',
                    '-implib %(OUTPUT_FOLDER)s/%(TARGET)s._tmp_lib',
                    '-addcommand "out:%(TARGET)s._tmp_%(TARGETTYPE)s"',
                    '-warnings off',
                    search_flag,
                    ])

    elif targettype == TARGETTYPE_EXE:
        LINKFLAGS = " ".join( [
                    '-msgstyle gcc',
                    '-stdlib',
                    '-m "?_E32Bootstrap@@YGXXZ"',
                    '-subsystem %s' % win32_subsystem,
                    '-g',
                    '-noimplib',
                    search_flag,
                    ])

        # We don't want to set a stack size on winscw:
        #   - if the exe is run by starting it in the emulator (epoc.exe) the
        #     stack size is ignored
        #   - if the exe is started directly (e.g., from the command line) the
        #     stack is _not_ ignored, BUT winscw requires a much larger stack
        #     to work correctly (without KERN-EXEC 3s) than device so we don't
        #     want to use the device stack limit.

        if epocheapsize is not None:
            # TODO: Defined in both gcce.py and winscw.py. Relocate check to upper level
            assert type( epocheapsize ) == tuple, "epocheapsize must be 2-tuple( minsize, maxsize )"
            assert epocheapsize[0] >= 0x1000, "minimum heapsize must be at least 0x1000(4kb)"

            # Its defined as kilobytes here
            LINKFLAGS += """
                    -heapreserve=%d -heapcommit=%d
            """ % ( epocheapsize[0] / 1024, epocheapsize[1] / 1024 )

    LINKFLAGS = textwrap.dedent( LINKFLAGS )
    LINKFLAGS = " ".join( [ x.strip() for x in LINKFLAGS.split( "\n" ) ] )

    LINKFLAGS = LINKFLAGS % {"TARGET"     : target,
                             "TARGETTYPE" : targettype,
                             "EPOCROOT"   : EPOCROOT,
                             "COMPILER"   : COMPILER,
                             "OUTPUT_FOLDER": OUTPUT_FOLDER
                             }

    platform_header = os.path.basename( PLATFORM_HEADER )
    if len( sysincludes ) > 0:
        sysincludes = "-I" + " -I".join( sysincludes )
    else:
        sysincludes = " "

    global _WINSCW_ENV
    env = None
    if _WINSCW_ENV is None:
        #print "env"
        _WINSCW_ENV = Environment(
                    tools = ["mingw"], # Disable searching of tools

                    CC = r'mwccsym2',
                    CXX = r'mwccsym2',

                    ENV = os.environ, #os.environ['PATH'],
                    # Static library settings
                    AR = r'mwldsym2',
                    ARFLAGS = "-library -msgstyle gcc -stdlib -subsystem windows -noimplib -o",
                    RANLIBCOM = "",
                    LIBPREFIX = "",

                    CPPPATH = includes,
                    CPPDEFINES = defines,
                    CCFLAGS = cc_flags + ' -cwd source -I- %s -include "%s"' % ( sysincludes, platform_header ),
                    INCPREFIX = "-i ",
                    CPPDEFPREFIX = "-d ",

                    # Linker settings
                    LINK = r'mwldsym2',
                    LINKFLAGS = LINKFLAGS,
                    LIBS = LIBRARIES,
                    LIBLINKPREFIX = " ",
                    PROGSUFFIX = "." + targettype,

        )

        env = _WINSCW_ENV
    else:
        # A lot faster than creating the environment from scratch
        env = _WINSCW_ENV.Clone()

    env.Replace( ENV = os.environ,

                 # Static library settings
                 CPPPATH = includes,
                 CPPDEFINES = defines,
                 CCFLAGS = cc_flags + ' -cwd source -I- %s -include "%s"' % ( sysincludes, platform_header ),

                 # Linker settings
                 LINKFLAGS = LINKFLAGS,
                 LIBS = LIBRARIES,
                 PROGSUFFIX = "." + targettype,
    )

    return env
