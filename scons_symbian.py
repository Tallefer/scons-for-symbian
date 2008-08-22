"""
SCons for Symbian - SCons build toolchain support for Symbian.

See examples folder for usage.
"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"

import os
import sys
import textwrap
from os.path import join

from SCons.Environment import Environment
from SCons.Builder     import Builder
from SCons.Options     import Options, EnumOption
from SCons.Script      import Command, Copy, \
                              Execute, Depends, BuildDir, \
                              Install, Default, Mkdir, Clean

from arguments import *
import winscw
import gcce
import colorizer
#if colorizer.CONSOLE is not None:
OUTPUT_COLORIZER = colorizer.OutputConsole(  )
    
#: Easy constant for free caps
FREE_CAPS = "NetworkServices LocalServices ReadUserData " \
            "WriteUserData Location UserEnvironment PowerMgmt " \
            "ProtServ SwEvent SurroundingsDD ReadDeviceData " \
            "WriteDeviceData TrustedUI".split()

# Set EPOCROOT as default target, so the stuff will actually be built.
Default( EPOCROOT )
    
# TODO: freeze # perl -S /epoc32/tools/efreeze.pl %(FROZEN)s %(LIB_DEFS)s
print "Building", COMPILER, RELEASE
print "Defines", CMD_LINE_DEFINES

#: UID.cpp for WINSCW simulator
TARGET_UID_CPP_TEMPLATE_DLL = r"""
// scons-generated uid source file
#include <e32cmn.h>
#pragma data_seg(".SYMBIAN")
__EMULATOR_IMAGE_HEADER2(0x10000079,0x00000000,0x00000000,EPriorityForeground,0x000ff1b4u,0x00000000u,0x00000000,0,0x00010000,0)
#pragma data_seg()
"""
#: UID.cpp for WINSCW simulator
TARGET_UID_CPP_TEMPLATE_EXE = r"""
// scons-generated uid source file
#include <e32cmn.h>
#pragma data_seg(".SYMBIAN")
__EMULATOR_IMAGE_HEADER2(0x1000007a,0x100039ce,%(UID3)s,EPriorityForeground,0x000ff1b4u,0x00000000u,%(UID3)s,0x00000000,0x00010000,0)
#pragma data_seg()
"""

# in template
# UID1 = 0x100039ce for exe
# UID1 = 0x00000000 for dll

def create_environment( *args, **kwargs ):
    env = None
    if COMPILER == COMPILER_GCCE:
        env = gcce.create_environment( *args, **kwargs )
    elif COMPILER == COMPILER_WINSCW:
        env = winscw.create_environment( *args, **kwargs )
    else:
        msg = "Error: Environment for '%s' is not implemented" % COMPILER
        raise NotImplemented( msg )
    return env
 
def SymbianPackage( package, ensymbleargs = None, pkgfile=None ):
    """
    Create Symbian Installer( sis ) file. Can use either Ensymble or pkg file.
    @param package: Name of the package.
    @param ensymbleargs: Arguments to Ensymble simplesis.
    @param pkgfile: Path to pkg file.
    """                     

    if ensymbleargs is not None and pkgfile is not None:
        raise ValueError( "Trying to use both Ensymble and PKG file. Which one do you really want?" )
    else:
        if ensymbleargs is None:
            ensymbleargs = {}
        
    def create_install_file( installed ):
        "Utility for creating an installation package using Ensymble"
        from ensymble.cmd_simplesis import run as simplesis
        
        cmd = []
        
        if pkgfile is None and ENSYMBLE_AVAILABLE:
             
            for x in ensymbleargs:
                cmd += [ "%s=%s" % ( x, ensymbleargs[x] ) ]
            cmd += [ join( PACKAGE_FOLDER, package ), package ]
            
            def ensymble( env, target = None, source = None ):
                try:
                    simplesis( "scons", cmd )
                except Exception, msg:
                    return str(msg)
            
            return Command( package, installed, ensymble, ENV = os.environ )
        
        elif pkgfile is not None:
            cmd = "makesis %s %s" % ( pkgfile, package )
            return Command( package, installed + [pkgfile], cmd, ENV = os.environ )
            
 
    if DO_CREATE_SIS:
        return create_install_file( [] )
        
def SymbianProgram( target, targettype = None, 
                    sources = None, includes = None,
                    libraries = None, uid2 = None, uid3 = "0x0",
                    definput = None, capabilities = None,
                    icons = None, resources = None,
                    rssdefines = None, 
                    # Sis stuff
                    package  = "",                 
                    **kwargs ):
    """
    Compiles sources using selected compiler.
    Converts resource files.
    Converts icon files.
    @param target: Name of the module without file extension.
                   If the file ends with .mmp, the .mmp file is used for defining the module. 
    @param libraries: Used libraries.
    @param capabilities: Used capabilities. Default: FREE_CAPS
    @param rssdefines: Preprocessor definitions for resource compiler.
    @param package: Path to installer file. If given, an installer is created automatically.
    @param **kwargs: Keywords passed to C{create_environment()}
    @return: Last Command. For setting dependencies.
    """

    if target.lower().endswith( ".mmp" ):
        import mmp_parser
        p = mmp_parser.MMPParser( target )
        data = p.Parse()
        
        target       = data["target"]
        targettype   = data["targettype"]
        sources      = data["source"]        
        includes     = data["systeminclude"] + data["userinclude"]
        resources    = data["resources"]
        libraries    = data["library"]
        uid2         = data["uid"][0]
        uid3         = data["uid"][1]
        
        # Allow override in SConstruct
        if capabilities is None:
            capabilities = data["capability"]
        
        # Allow override in SConstruct
        if rssdefines is None:
            rssdefines = data["macro"][:]
        
        kwargs["defines"]       = data["macro"][:]
        kwargs["allowdlldata"]  = data["epocallowdlldata"]
        kwargs["epocstacksize"] = data["epocstacksize"]
   
    if libraries is None:
        libraries = []
        
    if CMD_LINE_LIBS is not None:
        libraries.extend( CMD_LINE_LIBS )
    
    if capabilities is None:
        capabilities = FREE_CAPS
        
    if rssdefines is None:
        rssdefines = []
    rssdefines.append( r'LANGUAGE_SC' ) 
    
    if uid2 is None:
        if targettype == TARGETTYPE_EXE:
            uid2 = "0x100039ce"
        else:
            uid2 = "0x0"
    
    
      
    # Is this Symbian component enabled?
    component_name = ".".join( [ target, targettype] ).lower()
    
    if COMPONENTS is not None:
        if component_name not in COMPONENTS:
            print "Symbian component", component_name, "ignored"
            return None

    print "Getting dependencies for", ".".join( [target, targettype] )

    OUTPUT_FOLDER  = get_output_folder(COMPILER,RELEASE, target, targettype )
    
    sources = [ OUTPUT_FOLDER + "/" + x for x in sources ]
    
    # This is often needed
    FOLDER_TARGET_TUPLE = ( OUTPUT_FOLDER, target )    
    Mkdir( OUTPUT_FOLDER )
    
    # Just give type of the file
    TARGET_RESULTABLE   = "%s/%s" % FOLDER_TARGET_TUPLE + "%s"

    env = create_environment( target, targettype,
                          includes,
                          libraries,
                          uid2, uid3,
                          definput = definput,
                          capabilities = capabilities,
                          **kwargs )
    env.BuildDir(OUTPUT_FOLDER, ".")
    
    
    
    #-------------------------------------------------------------- Create icons
    # Copy for emulator at the end using this list, just like binaries.
    def convert_icons():
        if icons is not None:

            #result_install = PACKAGE_FOLDER + "/resource/apps/"
            #Mkdir( result_install )
            
            sdk_data_resource = EPOCROOT + r"epoc32/DATA/Z/resource/apps/%s"
            sdk_resource = join( EPOCROOT + r"epoc32", "release", COMPILER,
                             RELEASE, "z",  "resource", "apps", "%s" )
            package_resource = join( PACKAGE_FOLDER, package, "resource", "apps")
            #if not os.path.exists(result_install): os.makedirs(result_install)
            #result_install += "%s"

            # Creates 32 bit icons
            convert_icons_cmd = ( EPOCROOT + r'epoc32/tools/mifconv "%s" /c32 "%s"' ).replace("\\", "/" )
            
            # TODO: Accept 2-tuple, first is the source, second: resulting name
            icon_target_path = join( OUTPUT_FOLDER, "%s_aif.mif" )
            icon_targets = [] # Icons at WINSCW/...
            sdk_icons    = [] # Icons at /epoc32
            copyres_cmds = [] # Commands to copy icons from WINSCW/ to /epoc32
            for x in icons:
                tmp = icon_target_path % ( target )
                icon_targets.append( tmp )
                # Execute convert
                env.Command( tmp, x, convert_icons_cmd % ( tmp, x ) )
                
                iconfilename = os.path.basename(tmp)
                
                sdk_target = sdk_resource % iconfilename
                copyres_cmds.append( Copy( sdk_target, tmp ) )
                sdk_icons.append( sdk_target )
                
                sdk_target = sdk_data_resource % iconfilename
                copyres_cmds.append( Copy( sdk_target, tmp ) )
                sdk_icons.append( sdk_target )
                
                package_target = join( package_resource, iconfilename )
                copyres_cmds.append( Copy( package_target, tmp ) )
                sdk_icons.append( package_target )
                
                # Dependency
                if package != "":  
                    env.Depends( package, package_target )
                
            return env.Command( sdk_icons, icon_targets, copyres_cmds )

            #return icon_targets

        return None

    converted_icons = convert_icons()

    #---------------------------------------------------- Convert resource files
    def convert_resources():
        """
        Compile resources and copy for sis creation and for simulator.
        .RSC
            -> /epoc32/DATA/Z/resource/apps/
            -> /epoc32/release/winscw/udeb/z/resource/apps/
        _reg.RSC
            -> epoc32/release/winscw/udeb/z/private/10003a3f/apps/
            -> epoc32/DATA/Z/private/10003a3f/apps/
        .RSG     -> epoc32/include/
        """
        converted_resources = []
        resource_headers = []

        if resources is not None:
            # Make the resources dependent on previous resource
            # Thus the resources must be listed in correct order.
            prev_resource = None
            
            for rss_path in resources:
                rss_notype = ".".join(os.path.basename(rss_path).split(".")[:-1]) # ignore rss
                converted_rsg = join( OUTPUT_FOLDER, "%s.rsg" % rss_notype )
                converted_rsc = join( OUTPUT_FOLDER, "%s.rsc" % rss_notype )
                platinc = EPOCROOT + join( "epoc32", "include", "variant", "symbian_os_v9.1.hrh" )
                import rcomp
                

                result_paths  = [ ]
                copyres_cmds = [ ]

                converted_resources.append( converted_rsc )

                # Compile resource files
                #res_compile_command = env.Command( [converted_rsc, converted_rsg], rss_path, cmd )
                import rcomp
                
                res_compile_command = rcomp.RComp( env, converted_rsc, converted_rsg,
                             rss_path,
                             "-m045,046,047",
                             includes + INCLUDES,
                             [platinc],
                             rssdefines )
                             
                env.Depends(res_compile_command, converted_icons)

                includefolder = EPOCROOT + join( "epoc32", "include" )
                
                installfolder = [ PACKAGE_FOLDER ]
                if package != "": 
                    installfolder.append( package )
                if rss_notype.endswith( "_reg" ):
                    installfolder.append( join( "private", "10003a3f","import","apps" ) )
                else:
                    installfolder.append( join( "resource", "apps" ) )
                installfolder = os.path.join( *installfolder )
                 
                if not os.path.exists(installfolder): 
                    os.makedirs(installfolder)

                # Copy files for sis creation and for simulator
                def copy_file( source_path, target_path ):
                    copy_cmd = Copy( target_path, source_path )
                    #"copy %s %s" % ( source_path, target_path )
                    copyres_cmds.append( copy_cmd )
                    result_paths.append( target_path )

                rsc_filename = "%s.%s" % ( rss_notype, "rsc" )
                installfolder += "/" + rsc_filename
                # Copy to sis creation folder
                copy_file( converted_rsc, installfolder )

                # Copy to /epoc32/include/
                includepath = join( includefolder, "%s.%s" % ( rss_notype, "rsg" ) )
                copy_file( converted_rsg, includepath )

                # Add created header to be added for build dependency
                resource_headers.append( includepath )

                # _reg files copied to /epoc32/DATA/Z/private/10003a3f/apps/ on simulator
                if COMPILER == COMPILER_WINSCW:
                    if "_reg" in rss_path.lower():
                        path_private_simulator = EPOCROOT + r"epoc32/DATA/Z/private/10003a3f/apps/%s" % rsc_filename
                        copy_file( converted_rsc, path_private_simulator )

                        path_private_simulator = EPOCROOT +  r"epoc32/release/winscw/udeb/z/private/10003a3f/apps/%s" % rsc_filename
                        copy_file( converted_rsc, path_private_simulator )

                    else: # Copy normal resources to resource/apps folder
                        path_resource_simulator = EPOCROOT + r"epoc32/DATA/Z/resource/apps/%s" % rsc_filename
                        copy_file( converted_rsc, path_resource_simulator )

                        path_resource_simulator = EPOCROOT + r"epoc32/release/winscw/udeb/z/resource/apps/%s" % rsc_filename
                        copy_file( converted_rsc, path_resource_simulator )

                header_rsg = env.Command( result_paths, converted_resources, copyres_cmds )

                # Depend on previous. TODO: Use SCons Preprocessor scanner.
                if prev_resource is not None:
                    #print converted_rsg, includepath
                    env.Depends( rss_path, prev_resource )
                prev_resource = includepath
                
        return converted_resources, resource_headers

    converted_resources, resource_headers = convert_resources()

    # To be copied to /epoc32/release/WINSCW/UDEB/
    output_libpath = None
    returned_command = None

    if COMPILER == COMPILER_GCCE:
        output_lib    = ( targettype in DLL_TARGETTYPES )
        temp_dll_path = TARGET_RESULTABLE % ("._tmp_" + targettype )
        resultables = [ temp_dll_path ]

        # GCCE uses .dso instead of .lib
        LIBPATH   = gcce.SYMBIAN_ARMV5_LIBPATHDSO
        
        if output_lib:
            libname = target + ".dso"
            output_libpath = ( EPOCROOT + r"epoc32/release/%s/%s/%s" % ( "armv5", "lib", libname ) )

        build_prog = None
        if targettype != TARGETTYPE_LIB:
            build_prog = env.Program( resultables, sources )

            # Depend on the libs
            for libname in libraries:
                env.Depends( build_prog, libname )
                
            env.Depends( build_prog, converted_icons )
            env.Depends( build_prog, resource_headers )

            # Mark the lib as a resultable also
            resultables = [ TARGET_RESULTABLE % ( "" ) ]
            if output_lib:
                resultables.append( output_libpath )

            # Create final binary and lib/dso
            env.Elf( resultables, temp_dll_path )

        else:
            build_prog = env.StaticLibrary( TARGET_RESULTABLE % ".lib" , sources )
            output_libpath = ( TARGET_RESULTABLE % ".lib",
                                EPOCROOT + r"epoc32/release/armv5/%s/%s.lib" % ( RELEASE, target ) )
        
        #return
    else:

        # Compile sources ------------------------------------------------------
        # Creates .lib
        targetfile = target + "." + targettype

        def build_uid_cpp(target, source, env):
           """Create .UID.CPP for simulator"""
           template = ""
           if targettype == TARGETTYPE_EXE:
               ## TODO: Set uid's
               template = TARGET_UID_CPP_TEMPLATE_EXE % { "UID3": uid3 }
           else:
               template = TARGET_UID_CPP_TEMPLATE_DLL

           f = open(uid_cpp_filename,'w');f.write( template );f.close()
           return None

        # Create <target>.UID.CPP from template---------------------------------
        uid_cpp_filename = TARGET_RESULTABLE % ".UID.cpp"

        bld = Builder(action = build_uid_cpp,
                      suffix = '.UID.cpp' )
        env.Append( BUILDERS = {'CreateUID' : bld})
        env.CreateUID(uid_cpp_filename, sources)

        # We need to include the UID.cpp also
        sources.append( uid_cpp_filename )

        # Compile the sources. Create object files( .o ) and temporary dll.
        output_lib    = ( targettype in DLL_TARGETTYPES )
        temp_dll_path = TARGET_RESULTABLE % ("._tmp_" + targettype )
        resultables = [ temp_dll_path ]

        if output_lib:
            # No libs from exes
            libname = target + ".lib"
            resultable_path = TARGET_RESULTABLE % "._tmp_lib"
            resultables.append(resultable_path )
            #resultables.append( TARGET_RESULTABLE % ".inf" )
            output_libpath = ( TARGET_RESULTABLE % ".lib",
                                EPOCROOT + r"epoc32/release/%s/%s/" % ( COMPILER, RELEASE ) + libname )
        
        if targettype != TARGETTYPE_LIB:
            build_prog = env.Program( resultables, sources )
            # Depends on the used libraries. This has a nice effect since if,
            # this project depends on one of the other projects/components/dlls/libs
            # the depended project is automatically built first.
            env.Depends( build_prog, [ r"/epoc32/release/%s/%s/%s" % ( COMPILER, RELEASE, libname ) for libname in libraries] )
            env.Depends( build_prog, converted_icons )
            env.Depends( build_prog, resource_headers )
        else:
            build_prog = env.StaticLibrary( TARGET_RESULTABLE % ".lib" , sources )
            output_libpath = ( TARGET_RESULTABLE % ".lib",
                                join( EPOCROOT + "epoc32", "release", COMPILER, RELEASE, "%s.lib" % ( target ) ) )
        
        if output_lib and targettype != TARGETTYPE_LIB:
            # Create .inf file

            if definput is not None:# and os.path.exists(definput):
                definput = '-Frzfile "%s" ' % definput
            else:
                definput = ""

            action = "\n".join( [
                # Creates <target>.lib
                'mwldsym2.exe -S -show only,names,unmangled,verbose -o "%s" "%s"' % ( TARGET_RESULTABLE % ".inf", TARGET_RESULTABLE % "._tmp_lib" ),
                # Creates def file
                r'perl -S %EPOCROOT%epoc32/tools/makedef.pl -absent __E32Dll ' + '-Inffile "%s" ' % ( TARGET_RESULTABLE % ".inf" )
                + definput
                + ' "%s"' % ( TARGET_RESULTABLE % '.def' ) ] )
            #print action
            #BuildDir('build', 'src', duplicate=0)
            defbld = Builder( action = action,
                              ENV = os.environ )
            env.Append( BUILDERS = {'Def' : defbld} )
            env.Def( #COMPILER+ "/" + target + ".inf",
                       #TARGET_RESULTABLE % ".inf",
                       TARGET_RESULTABLE % ".def",
                       TARGET_RESULTABLE % "._tmp_lib" )

        # NOTE: If build folder is changed this does not work anymore.
        # List compiled sources and add to dependency list
        object_paths = [ ".".join( x.split(".")[:-1] ) + ".o" for x in sources ]

        # Sources depend on the headers generated from .rss files.
        env.Depends( object_paths, resource_headers )

        # Get the lookup folders from source paths.
        object_folders = [ os.path.dirname( x ) for x in object_paths ]

        # Needed to generate the --search [source + ".cpp" -> ".o",...] param
        objects = [ os.path.basename( x ) for x in object_paths ]
        objects = " ".join( objects )

        libfolder = "%EPOCROOT%epoc32/release/winscw/udeb/"
        libs      = [ libfolder + x for x in libraries]

        if targettype in DLL_TARGETTYPES and targettype != TARGETTYPE_LIB:

            env.Command( TARGET_RESULTABLE % ("." + targettype ), [ temp_dll_path, TARGET_RESULTABLE % ".def" ],
            [
                " ".join( [
                            'mwldsym2 -msgstyle gcc',
                            '-stdlib %EPOCROOT%epoc32/release/winscw/udeb/edll.lib -noentry',
                            '-shared -subsystem windows',
                            '-g %s' % " ".join( libs ),
                            '-o "%s"' % temp_dll_path,
                            '-f "%s"' % ( TARGET_RESULTABLE % ".def" ),
                            '-implib "%s"' % ( TARGET_RESULTABLE % ".lib" ),
                            '-addcommand "out:%s.%s"' % ( target, targettype ),
                            '-warnings off',
                            '-l %s' % " -l ".join( set(object_folders) ),
                            '-search ' + objects,
                          ]
                        )
            ]
            )
        elif targettype == TARGETTYPE_EXE:
            env.Command( TARGET_RESULTABLE % ".exe", temp_dll_path,
                [
                " ".join( [ 'mwldsym2',
                            '-msgstyle gcc',
                            '-stdlib %EPOCROOT%epoc32/release/winscw/udeb/eexe.lib',
                            '-m "?_E32Bootstrap@@YGXXZ"',
                            '-subsystem windows',
                            '-g %s' % " ".join( libs ),
                            '-o "$TARGET"',
                            '-noimplib',
                            '-l %s' % " -l ".join( set( object_folders ) ),
                            '-search ' + objects,
                          ]
                        )
                ]
            )

    def copy_result_binary( ):
        """Copy the linked binary( exe, dll ) for emulator
        and to resultables folder.
        """
        installfolder = [ PACKAGE_FOLDER ]
        
        if targettype != TARGETTYPE_LIB:
            if package != "":  # Install the files for sis packaging.
                installfolder.append( package )
            installfolder += ["sys", "bin" ]
        else: # Don't install libs to device.
            installfolder += ["lib"]
            
        installfolder = join( *installfolder )
        Mkdir( installfolder )
        
        installpath = join( installfolder, "%s.%s" % ( target, targettype ) )
        
        # Combine with installfolder copying. TODO: Not needed anymore since EPOCROOT is default target.
        postcommands = []
        copysource = TARGET_RESULTABLE % ( "."+targettype)
        target_filename = target + "." + targettype
        sdkpath       = join( SDKFOLDER, target_filename )

        installed = []
        if COMPILER == COMPILER_WINSCW:
            # Copy to SDK to be used with simulator
            postcommands.append( Copy( sdkpath, copysource ) )
            installed.append( sdkpath )

        if output_libpath is not None and \
        ( COMPILER == COMPILER_WINSCW or targettype == TARGETTYPE_LIB ):
            s,t = output_libpath
            postcommands.append( Copy( t, s ) )
            installed.append( t )

        # Last to avoid copying to installpath if sdkfolder fails        
        postcommands.append( Copy( installpath, copysource ) )
        installed.append(installpath )
        returned_command = env.Command( installed , copysource, postcommands )
        
        return installed
    
    installed = copy_result_binary()
        
    if package != "" and targettype != TARGETTYPE_LIB:
        # package depends on the files anyway
        env.Depends( package, installed )
    
    return returned_command


    
