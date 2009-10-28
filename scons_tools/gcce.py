from glob import glob
import textwrap

import os
from os.path import abspath, join
import string

import SCons.Action
import SCons.Builder
import SCons.Defaults
import SCons.Tool
import SCons.Util

# This is what we search for to find mingw:
key_program = 'arm-none-symbianelf-gcc'

from scons_symbian import arguments as ARGS
DEFAULT_GCCE_DEFINES = ARGS.DEFAULT_SYMBIAN_DEFINES[:]
DEFAULT_GCCE_DEFINES += [
                        "__GCCE__",
                        "__EPOC32__",
                        "__MARM__",
                        "__EABI__",
                        "__MARM_ARMV5__",
                        ( "__PRODUCT_INCLUDE__", r'\"%s\"' % ARGS.PLATFORM_HEADER.replace("\\", "/") )
                        ]

#SYMBIAN_ARMV5_BASE_LIBRARIES = [ SYMBIAN_ARMV5_LIBPATHLIB + __x + ".lib" for __x in [ "usrt2_2" ] ]
SYMBIAN_BASE_LIBRARIES = [ "usrt2_2.lib", "drtaeabi", "dfprvct2_2", "dfpaeabi", "scppnwdl" , "drtrvct2_2", "eikcore.dso" ]
#SYMBIAN_ARMV5_BASE_LIBRARIES += [ SYMBIAN_ARMV5_LIBPATHDSO + __x + ".dso" for __x in DSO_LIBS ]

def find(env):
    # First search in the SCons path and then the OS path:
    return env.WhereIs(key_program) or SCons.Util.WhereIs(key_program)

def shlib_generator(target, source, env, for_signature):
    cmd = ['$SHLINK', '$SHLINKFLAGS', '-shared']

    no_import_lib = env.get('no_import_lib', 0)
    if no_import_lib: cmd.extend('-noimplib')

    dll = env.FindIxes(target, 'SHLIBPREFIX', 'SHLIBSUFFIX')
    if dll: cmd.extend(['-o', dll])

    implib = env.FindIxes(target, 'LIBPREFIX', 'LIBSUFFIX')
    if implib: cmd.extend(['-implib', implib.get_string(for_signature)])

    cmd.extend(['$SOURCES', '$_LIBDIRFLAGS', '$_LIBFLAGS'])

    return [cmd]


def shlib_emitter(target, source, env):
    dll = env.FindIxes(target, 'SHLIBPREFIX', 'SHLIBSUFFIX')
    no_import_lib = env.get('no_import_lib', 0)

    if not dll:
        raise SCons.Errors.UserError, "A shared library should have exactly one target with the suffix: %s" % env.subst("$SHLIBSUFFIX")

    if not no_import_lib and \
       not env.FindIxes(target, 'LIBPREFIX', 'LIBSUFFIX'):

        # Append an import library to the list of targets.
        target.append(env.ReplaceIxes(dll,
                                      'SHLIBPREFIX', 'SHLIBSUFFIX',
                                      'LIBPREFIX', 'LIBSUFFIX'))

    return target, source
                         

shlib_action = SCons.Action.Action(shlib_generator, generator=1)

res_action = SCons.Action.Action('$RCCOM', '$RCCOMSTR')

res_builder = SCons.Builder.Builder(action=res_action, suffix='.o',
                                    source_scanner=SCons.Tool.SourceFileScanner)

SCons.Tool.SourceFileScanner.add_scanner('.rss', SCons.Defaults.CScan)
SCons.Tool.SourceFileScanner.add_scanner('.rsc', SCons.Defaults.CScan)
SCons.Tool.SourceFileScanner.add_scanner('.rsg', SCons.Defaults.CScan)
SCons.Tool.SourceFileScanner.add_scanner('.rpp', SCons.Defaults.CScan)

def _abspath(path,env):
    """ Converts path into absolute path """
    p = abspath( path % env )
    #import pdb;pdb.set_trace()
    return p

def resolve_targettype( target ):
    if target.lower().endswith(".exe"):
        return "exe"
    return "dll"
    
def _elf2e32(target, env):
    
    #import pdb;pdb.set_trace()
    #elf2e32 = env.subst( "${EPOCROOT}epoc32/tools/elf2e32.exe" )
    targettype = resolve_targettype(target.path)
    env["_TARGETTYPE"] = targettype
    env["_TARGET"]     = target
    
    #print target
    elf2e32 = r""""${EPOCROOT}epoc32/tools/elf2e32.exe"
                --sid=$SID --uid1=$UID1 --uid2=$UID2 --uid3=$UID3
                --capability=${"+".join(CAPABILITIES)}
                --fpu=softvfp --targettype=${_TARGETTYPE}
                --output=$_TARGET
                ${_DEFCONFIG}
                --elfinput=${ELF_TARGET}
                --linkas=${_TARGET}{000a0000}.$_TARGETTYPE
                --libpath="$ELF2E32_LIBPATH"
                """
    
    elf2e32 = textwrap.dedent( elf2e32 )
    elf2e32 = " ".join( [ x.strip() for x in elf2e32.split( "\n" ) ] )
    elf2e32 = env.subst( elf2e32 )
    
    return elf2e32

def _getUID1(target):
    """ Resolve the UID1 based on target """
    if target is None: return ""
    
    targettype = resolve_targettype(target.path)
    
    uid = ""
    if targettype == ARGS.TARGETTYPE_EXE:
        uid = ARGS.TARGETTYPE_UID_MAP[targettype]
    else:
        uid = ARGS.TARGETTYPE_UID_MAP[ARGS.TARGETTYPE_DLL]
    
    return uid

def _getUID2(target):
    """ Resolve the UID2 based on target """
    if target is None: return ""
    
    targettype = resolve_targettype(target.path)
    
    uid = "0x0"
    if targettype == ARGS.TARGETTYPE_EXE:
        uid = "0x100039ce"
        
    return uid

PACKAGES = {}
def _package(target, env):
    if package != "":
        l = PACKAGES.get( package,{} )
        l.append( target )
        PACKAGES[package] = l

def package_generator(target, source, env, for_signature):
    print target[0].path
    def test():
        print "testing"
    return test

package_action = SCons.Action.Action(package_generator, generator=1)
CreatePackage = SCons.Builder.Builder(action=package_action)

def _CreatePackage( env, target, source ):
    package = env["PACKAGE"]
    if package == "": return ""
    
    env.Depends( target, env.Value( PACKAGES ) )
    
    print "Create pkg"
    print "Create sis"
    
def _ToPackage(env, target, source, targetpath=None):
    package = env["PACKAGE"]
    if package != "":
        l = PACKAGES.get( package, {} )
        l[source[0]] = targetpath
        PACKAGES[package] = l
        
    print "Added", target

def generate(env):
    gcce = find(env)
    if gcce:
        p = os.path.dirname(gcce)
        env.PrependENVPath('PATH', p )
        
     #import pdb;pdb.set_trace()
    SYMBIAN_FLAGS = "-Wall -Wno-unknown-pragmas -fexceptions -march=armv5t -mapcs -pipe -nostdinc -msoft-float"

    # Most of GCCE is the same as gcc and friends...
    gnu_tools = ['gcc', 'g++', 'gnulink', 'ar', 'gas', 'm4']
    for tool in gnu_tools:
        SCons.Tool.Tool(tool)(env)
    
    env['CC']   = 'arm-none-symbianelf-gcc'
    env['CXX']  = 'arm-none-symbianelf-g++'
    env['AS']   = 'arm-none-symbianelf-as'
    env["AR"]   = 'arm-none-symbianelf-ar'
    env["LINK"] = 'arm-none-symbianelf-ld'
    
    env["RELEASE"]  = "urel"
    env["EPOCROOT"] = os.environ.get( "EPOCROOT", "\\")
    
    # UID handling
    env["_getUID1"] = _getUID1
    env["_getUID2"] = _getUID2
    env["UID1"]     = "${_getUID1(_TARGET)}"
    env["UID2"]     = "${_getUID2(_TARGET)}"
    env["UID3"]     = "0"
    env["SID"]      =  "$UID3"
    
    # elf2e32 variables
    env["CAPABILITIES"]    = "NONE"
    env["ELF2E32_LIBPATH"] = join( "${EPOCROOT}epoc32","release","armv5","lib")
    env["ELF_TARGET"]      = "${_TARGET}.elf"
    
    # Packaging
    env["_package"]    = _package
    env["PACKAGE"]     = ""
    env["PACKAGE_UID"] = "0x0"
    env["PACKAGE_CERT"] = ""
    env["PACKAGE_KEY"]  = ""
    env["PACKAGE_PASS"] = ""
    
    env['BUILDERS']['CreatePackage'] = _CreatePackage
    env['BUILDERS']['ToPackage']     = _ToPackage
    
    # Compiling
    env["CFLAGS"]   = SYMBIAN_FLAGS + "-x c -include ${EPOCROOT}epoc32/include/gcce/gcce.h"
    
    env["_abspath"] = _abspath
    env["CXXFLAGS"] = SYMBIAN_FLAGS + " -Wno-ctor-dtor-privacy -x c++ -include ${_abspath('%(EPOCROOT)sepoc32/include/gcce/gcce.h', __env__)}"
    env["CPPPATH"]  = SCons.Util.CLVar("/epoc32/include")
    env["CPPDEFINES"] = DEFAULT_GCCE_DEFINES + ["__UID3__=${UID3}"]
    env["LINKFLAGS"]  = "--target1-abs --no-undefined -nostdlib" \
                        " -shared -Ttext 0x8000 -Tdata 0x400000" \
                        " --default-symver " \
                        " -soname ${TARGET}{${UID2}}[${UID3}].exe" \
                        " --entry _E32Startup -u _E32Startup" \
                        " ${EPOCROOT}epoc32/release/armv5/${RELEASE}/eexe.lib" \
                        " -Map ${EPOCROOT}epoc32/release/gcce/${RELEASE}/${TARGET}.map "
   
    # The prefix used to specify a library directory on the linker command line. 
    env["LIBDIRPREFIX"]  = "-L"
    env["LIBLINKPREFIX"] = ""
    env["LIBLINKSUFFIX"] = ""
    
    env["INCPREFIX"] = "-I "
    env['INCSUFFIX'] = ""
    env["RANLIBCOM"] = ""
    env["LIBSUFFIX"] = ".lib"
    
    env["SHLIBSUFFIX"]    = "-library "
    env["LDMODULESUFFIX"] = ".lib"
    env['SHLINK']         = '$LINK'
    env['SHLINKFLAGS'] = "--target1-abs --no-undefined -nostdlib" \
                        " -shared -Ttext 0x8000 -Tdata 0x400000" \
                        " --default-symver " \
                        " -soname ${TARGET}{${UID2}}[${UID3}].dll" \
                        " --entry _E32Dll -u _E32Dll" \
                        " ${EPOCROOT}epoc32/release/armv5/${RELEASE}/edll.lib" \
                        " -Map ${EPOCROOT}epoc32/release/gcce/${RELEASE}/${TARGET}.map "
    env['SHLINKCOM']   = shlib_action
    env['SHLIBEMITTER']= shlib_emitter
    
    env["LIBPATH"]  = SCons.Util.CLVar('')
    env["LIBPATH"]  += r"${EPOCROOT}" + join( "epoc32", "release", "armv5", "lib" )
    env["LIBPATH"]  += [ ARGS.PATH_ARM_TOOLCHAIN + x for x in [
                                "/../lib/gcc/arm-none-symbianelf/3.4.3",
                                "/../arm-none-symbianelf/lib",
                                ] ]
    env["LIBS"] = SCons.Util.CLVar('')
    
    def _findpath(env):
        # arm-none-symbianelf-ld does not respect the library search paths.
        # So we need to find them and generate absolute paths to the libraries.
        #import pdb;pdb.set_trace()
        LIBARGS  = [ "-lsupc++", "-lgcc" ]
        result   = []
        dircache = {}
        for library in SYMBIAN_BASE_LIBRARIES + env["LIBS"]:
            
            # GCCE uses .dso instead of .lib for dynamic libs. .lib indicates
            # static lib
    
            # Add .dso if file extension does not exist
            if "." not in library:
                library += ".dso"
            
            # If not found, use the default path 
            # it may be built by some other target.
            path = r"${EPOCROOT}epoc32/release/armv5/${RELEASE}/%s" % library
            
            for directory in env["LIBPATH"]:
                p = join( directory, library)
                p = env.subst( p )
                if os.path.exists( p):
                    path = p
                    break
            path = env.subst( path )
            result.append( path )
            
        result += LIBARGS
        result = " ".join( result )
        
        return result
    
    env["_findpath"] = _findpath
    env['_LIBFLAGS']  = '${_findpath(__env__)}'
    env['_elf2e32']  = _elf2e32
    env["LINKCOM"] = "$LINK -o ${TARGET}.elf $LINKFLAGS $SOURCES $_LIBDIRFLAGS $_LIBFLAGS\n${_elf2e32(TARGET, __env__)}\n${_package(TARGET, __env__)}"
    
    return

    # Some setting from the platform also have to be overridden:
    #env['OBJSUFFIX'] = '.o'
    #env['LIBPREFIX'] = 'lib'
    #env['LIBSUFFIX'] = '.a'

def exists(env):
    return find(env)
