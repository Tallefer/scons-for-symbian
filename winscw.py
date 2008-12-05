"""Environment for WINSCW compiler"""

__author__ = "Jussi Toivola"
__license__ = "MIT License"

from SCons.Environment import Environment
from arguments import * #IGNORE:W0611
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
                        
def create_environment( target,
                        targettype,
                        includes,
                        sysincludes,
                        libraries,
                        epocheapsize = None,
                        epocstacksize = None,
                        *args,
                        **kwargs  
                        ):
    """Create WINSCW environment
    @param kwargs: ignored keyword arguments.
    @see: L{scons_symbian.SymbianProgram}
    """
    
    defines = kwargs["defines"][:]
    for x in xrange( len( libraries ) ):
        lib = libraries[x]
        if "." not in lib:
            libraries[x] = lib + ".lib"
            
    OUTPUT_FOLDER = get_output_folder( COMPILER, RELEASE, target, targettype )

    LIBPATH = SYMBIAN_WINSCW_LIBPATHLIB
    LIBRARIES = [ os.path.normpath( LIBPATH + x ).lower() for x in libraries ]    
    
    defines.extend( DEFAULT_WINSCW_DEFINES )
    defines.extend( CMD_LINE_DEFINES )

    if targettype in DLL_TARGETTYPES:
        defines.append( "__DLL__" )
    else:
        defines.append( "__EXE__" )
    defines = [ '"%s"' % x for x in defines ]

    WINSCW_CC_FLAGS = '-g -O0 -inline off -wchar_t off -align 4 -warnings on -w nohidevirtual,nounusedexpr -msgstyle gcc -enum int -str pool -exc ms -trigraphs on  -nostdinc'
     #%(EPOCROOT)sepoc32/RELEASE/WINSCW/UDEB/euser.lib %(EPOCROOT)sepoc32/release/WINSCW/UDEB/efsrv.lib
    LINKFLAGS = ""
    if targettype in DLL_TARGETTYPES:
        LINKFLAGS = """
                    -msgstyle gcc
                    -stdlib "%(EPOCROOT)sepoc32/release/winscw/udeb/edll.lib"
                    -noentry -shared
                    -subsystem windows                    
                    -g
                    -export dllexport
                    -m __E32Dll
                    -nocompactimportlib
                    -implib %(OUTPUT_FOLDER)s/%(TARGET)s._tmp_lib
                    -addcommand "out:%(TARGET)s._tmp_%(TARGETTYPE)s"
                    -warnings off
                     """

    elif targettype == TARGETTYPE_EXE:
        LINKFLAGS = """
                    -msgstyle gcc
                    -stdlib "%(EPOCROOT)sepoc32/release/winscw/udeb/eexe.lib"
                    -m "?_E32Bootstrap@@YGXXZ"
                    -subsystem windows -g
                    -noimplib
                     """
        
        if epocstacksize is None:
            # This is default for device builds so we'll use it here as well
            epocstacksize = 80
        else:
            # Defined in bytes for device but in kilobytes for winscw
            epocstacksize /= 1024
        
        LINKFLAGS += """
            -stackreserve %d
        """ % epocstacksize
        
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
                             "OUTPUT_FOLDER": OUTPUT_FOLDER }

    platform_header = os.path.basename( PLATFORM_HEADER )
    if len( sysincludes ) > 0:
        sysincludes = "-I" + " -I".join( sysincludes )
    else:
        sysincludes = " "
        
    env = Environment( 
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
                    CCFLAGS = WINSCW_CC_FLAGS + ' -cwd source -I- %s -include "%s"' % ( sysincludes, platform_header ),
                    INCPREFIX = "-i ",
                    CPPDEFPREFIX = "-d ",
                    
                    # Linker settings
                    LINK = r'mwldsym2',
                    LINKFLAGS = LINKFLAGS,
                    LIBS = LIBRARIES,
                    LIBLINKPREFIX = " ",
                    PROGSUFFIX = "." + targettype,

                )
    return env
