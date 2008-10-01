"""Main module"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"

import os
import sys
import textwrap
from os.path import join, basename

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
    
#: Handle to console for colorized output( and process launching )
_OUTPUT_COLORIZER = colorizer.OutputConsole(  )

# Set EPOCROOT as default target, so the stuff will actually be built.
Default( EPOCROOT )
    
# TODO: freeze # perl -S /epoc32/tools/efreeze.pl %(FROZEN)s %(LIB_DEFS)s
print "Building", COMPILER, RELEASE
print "Defines", CMD_LINE_DEFINES

# in template
# UID1 = 0x100039ce for exe
# UID1 = 0x00000000 for dll

def _create_environment( *args, **kwargs ):
    """Environment factory. Get correct environment for selected compiler."""
    env = None
    if COMPILER == COMPILER_GCCE:
        env = gcce.create_environment( *args, **kwargs )
    elif COMPILER == COMPILER_WINSCW:
        env = winscw.create_environment( *args, **kwargs )
    else:
        msg = "Error: Environment for '%s' is not implemented" % COMPILER
        raise NotImplementedError( msg )
    return env

def pkgname( sisname ):
    "Convert sisname to pkg filename"
    return ".".join( sisname.split(".")[:-1] + ["pkg"] )
    
def SymbianPackage( package, ensymbleargs = None, pkgargs = None, pkgfile=None, extra_files = None ):
    """
    Create Symbian Installer( sis ) file. Can use either Ensymble or pkg file.
    To enable creation, give command line arg: dosis=true
    
    @param package: Name of the package.
    @type package: str
    
    @param pkgargs: Arguments to PKG generation. Disabled if none, use empty dict for simple enable
    @type pkgargs: dict
    
    @param ensymbleargs: Arguments to Ensymble simplesis.
    @type ensymbleargs: dict 
    
    @param pkgfile: Path to pkg file.
    @type pkgfile: str
    @param extra_files: Copy files to package folder and install for simulator( to SIS with Ensymble only )
    """                     
    # Skip processing to speed up help message                    
    if HELP_ENABLED: return

    if ensymbleargs is not None and pkgfile is not None:
        raise ValueError( "Trying to use both Ensymble and PKG file. Which one do you really want?" )
    else:
        if ensymbleargs is None:
            ensymbleargs = {}
    
    if extra_files is not None:
        pkg = PKG_DATA.get( package, {} )
        
        for target, source in extra_files:
            pkg[source] = target
            
            Install( join( PACKAGE_FOLDER, package, target ), source )
            if COMPILER == COMPILER_WINSCW:
                Install( join( FOLDER_EMULATOR_C, target ),   source )
        
        PKG_DATA[package] = pkg
        
    def create_pkg_file( pkgargs ):
        
        if pkgargs is None:
            pkgargs = {}
            
        def cmd( env, target = None, source = None ):
            
            print "Creating pkg", target[0]
            
            pkgfile = str(target[0])
            f=open( pkgfile, 'w');
            version = pkgargs.get("version", ( "1","0","00000" ) )
            
            files = PKG_DATA[package]
            
            header = '#{"%(appname)s"},(%(uid)s),' % ( pkgargs )
            header += '%s,%s,%s' % tuple(version)
            header += ',TYPE=%s\n\n' % pkgargs.get( "type", "SISSYSTEM" )
            
            f.write( ";Localised package name\n")
            f.write( header )
            
            f.write( ";Localized vendor name\n")
            f.write( '%%{"%s"}\n\n' % pkgargs.get( "vendor", "VENDOR" ) )
            
            f.write( ';Unique Vendor name\n' )
            f.write( ':"%s"\n\n' % pkgargs.get( "vendor_id", "VENDOR" ) )
            
            ## TODO: Correct UID for UIQ    
            f.write( '[0x101F7961], 0, 0, 0, {"Series60ProductID"}\n\n' )
            keys = files.keys();keys.sort()
            for x in keys:
                t = files[x]
                t = t.split("\\")
                if t[0] == "any":
                    t[0] = "!:"
                else:
                    t[0] = t[0]+":"
                t = "\\".join( t ).replace("/","\\")
                x = x.replace("/", "\\")
                f.write( '%-50s - "%s"\n' % ( '"%s"' % x, t ) )
            
            f.close()
        
        Depends( package, pkgname( package ) )
        return Command( pkgname( package ), None, cmd, ENV = os.environ )
    
    if pkgargs is not None and COMPILER != COMPILER_WINSCW:    
        create_pkg_file( pkgargs )
    
    def create_install_file( installed ):
        "Utility for creating an installation package using Ensymble"
        from ensymble.cmd_simplesis import run as simplesis
        
        cmd = []
        
        def ensymble( env, target = None, source = None ):
            """ Wrap ensymble simplesis command. """
            try:
                print "Running simplesis:" + str(cmd)
                simplesis( "scons", cmd )
            except Exception, msg:
                return str(msg)
                                    
        if pkgfile is None and ENSYMBLE_AVAILABLE:
             
            for x in ensymbleargs:
                cmd += [ "%s=%s" % ( x, ensymbleargs[x] ) ]
                
            cmd += [ join( PACKAGE_FOLDER, package ), package ]
            
            return Command( package, installed, ensymble, ENV = os.environ )
        
        elif pkgfile is not None:
            cmd = "makesis %s %s" % ( pkgfile, package )
            return Command( package, installed + [pkgfile], cmd, ENV = os.environ )
            
 
    if DO_CREATE_SIS:
        return create_install_file( [] )

def SymbianHelp( *args  ):
    
    import cshlp
    
    helpresult = cshlp.CSHlp( *args )
    return helpresult
    

PKG_DATA = {}
def ToPackage( env, package_drive_map, package, target, source ):
    
    if package is None:
        return
        
    import re
    # WARNING: Copying to any/c/e is custom Ensymble feature.
    drive = ""
    
    pkg = PKG_DATA.get(package, {} )
    
    if package_drive_map is not None:
            
        # Goes to any by default
        drive = "any"    
        filename = os.path.basename( source )
        
        for d in package_drive_map:
            regexp = package_drive_map[d]       
            if type(regexp) == str: 
                regexp = re.compile( regexp )
                package_drive_map[d] = regexp
            
            if regexp.match( filename ):
                drive = d
                break
    
    # Add to pkg generator
    pkgsource      = join( PACKAGE_FOLDER, package, drive, target, basename( source ) )
    pkg[pkgsource] = join( drive, target, basename( source ) )
    env.Depends( pkgname(package), join( PACKAGE_FOLDER, package, pkg[pkgsource] )  )
    
    if drive == "":
        pkg[pkgsource] = join( "any", target, basename( source ) )
    PKG_DATA[package] = pkg
    
    # Do the copy
    cmd = env.Install( join( PACKAGE_FOLDER, package, drive, target ), source )                      
    return cmd
    
def SymbianProgram( target, targettype = None, 
                    sources = None, includes = None, 
                    libraries = None, uid2 = None, uid3 = None,
                    definput = None, capabilities = None,
                    icons = None, resources = None,
                    rssdefines = None, 
                    defines    = None,
                    help = None,
                    sysincludes = None,
                    # Sis stuff
                    package  = "",
                    package_drive_map = None,                 
                    extra_depends=[],                 
                    **kwargs ):
    """
    Main function for compiling Symbian software. Handles the whole process
    of source and resource compiling and SIS installer packaging. 
    
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
    
    @param definput:    Path to .def file containing frozen library entrypoints.
    @type definput: str
    
    @param icons:       List of icon files to compile
    @type icons: list
    
    @param resources:   List of paths to .rss files to compile. 
                        See rssdefines param for giving CPP macros.
    @type resources: list          
    
    @param libraries: Used libraries.
    @type libraries: list
    
    @param capabilities: Used capabilities. Default: FREE_CAPS
    @type capabilities: list
    
    @param defines: Preprocess definitions.
    @type defines: list
    
    @param rssdefines: Preprocessor definitions for resource compiler.
    @type rssdefines: list
    
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
    # Skip processing to speed up help message
    if HELP_ENABLED: return

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
    
    if includes is None:
        includes = []
    
    if defines is None:
        defines = []
    defines = defines[:]
    
    if sysincludes is None:
        sysincludes = []
        
    sysincludes.extend( SYSTEM_INCLUDES )
    
    if help:
    # Adds the .hrh file to include path
        includes.append( os.path.dirname( help ) )
    
    if libraries is None:
        libraries = []
        
    if CMD_LINE_LIBS is not None:
        libraries.extend( CMD_LINE_LIBS )
    
    if capabilities is None:
        capabilities = FREE_CAPS
    
    if uid2 is None:
        if targettype == TARGETTYPE_EXE:
            uid2 = "0x100039ce"
        else:
            uid2 = "0x0"
    
    if uid3 is None:
        uid3 = "0x0"
    
    # Add macros to ease changing application UID
    uiddefines = [
        "__UID3__=%s" % uid3
    ]
    defines.extend( uiddefines )
    
    if rssdefines is None:
        rssdefines = []
    rssdefines.append( r'LANGUAGE_SC' ) 
    rssdefines.extend( uiddefines )
    
    # Is this Symbian component enabled?
    component_name = ".".join( [ target, targettype] ).lower()
    
    if COMPONENTS is not None:
        if component_name not in COMPONENTS:
            print "Symbian component", component_name, "ignored"
            return None

    print "Getting dependencies for", ".".join( [target, targettype] )

    OUTPUT_FOLDER  = get_output_folder(COMPILER,RELEASE, target, targettype )
    
    # ???: SCons is able to compile sources with OUTPUT_FOLDER 
    #      but not able to detect if the files have changed without
    #      explicit dependency!! Without OUTPUT_FOLDER the resulting object
    #      files are stored in the same folder as sources causing cross compiling
    #      to fail.
    extra_depends.extend( sources )
    sources = [ join( OUTPUT_FOLDER, x) for x in sources ]
    
    # This is often needed
    FOLDER_TARGET_TUPLE = ( OUTPUT_FOLDER, target )    
    Mkdir( OUTPUT_FOLDER )
    
    # Just give type of the file
    TARGET_RESULTABLE   = "%s/%s" % FOLDER_TARGET_TUPLE + "%s"
    
    
    env = _create_environment( target, targettype,
                          includes,
                          sysincludes,
                          libraries,
                          uid2, uid3,
                          definput = definput,
                          capabilities = capabilities,
                          defines = defines,
                          **kwargs )
    
    # Don't duplicate to ease use of IDE(Carbide)
    env.BuildDir(OUTPUT_FOLDER, ".", duplicate=0 )
    
    if help:
        helpresult = SymbianHelp( env, help, uid3 )
        if COMPILER == COMPILER_WINSCW:
            env.Install( join( FOLDER_EMULATOR_C, "resource", "help" ), helpresult[0] )
        
        ToPackage( env, package_drive_map, package, 
                    join( "resource", "help" ), 
                    helpresult[0] )
        #
        extra_depends.extend( helpresult )

    #-------------------------------------------------------------- Create icons
    # Copy for emulator at the end using this list, just like binaries.
    #TODO: Create main interface SymbianIcon for generic icons
    def convert_icons():
        if icons is not None:

            #result_install = PACKAGE_FOLDER + "/resource/apps/"
            #Mkdir( result_install )
            
            sdk_data_resource = EPOCROOT + r"epoc32/DATA/Z/resource/apps/%s"
            sdk_resource = join( EPOCROOT + r"epoc32", "release", COMPILER,
                             RELEASE, "z",  "resource", "apps", "%s" )
            #package_resource = join( "resource", "apps")
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
                
                #package_target = join( package_resource, iconfilename )
                #copyres_cmds.append( Copy( package_target, tmp ) )
                #sdk_icons.append( package_target )
                
                ToPackage( env, package_drive_map, package, 
                    join( "resource", "apps"), 
                    tmp )
                    
                # Dependency
                #if package != "":  
                #    env.Depends( package, package_target )
                
            return env.Command( sdk_icons, icon_targets, copyres_cmds )

            #return icon_targets

        return None

    converted_icons = convert_icons()

    #---------------------------------------------------- Convert resource files
    #TODO: Create main interface SymbianResource for special resource compiling
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
        import rcomp

        if resources is not None:
            # Make the resources dependent on previous resource
            # Thus the resources must be listed in correct order.
            prev_resource = None
            
            for rss_path in resources:
                rss_notype = ".".join(os.path.basename(rss_path).split(".")[:-1]) # ignore rss
                converted_rsg = join( OUTPUT_FOLDER, "%s.rsg" % rss_notype )
                converted_rsc = join( OUTPUT_FOLDER, "%s.rsc" % rss_notype )
                converted_resources.append( converted_rsc )
                
                result_paths  = [ ]
                copyres_cmds = [ ]

                res_compile_command = rcomp.RComp( env, converted_rsc, converted_rsg,
                             rss_path,
                             "-m045,046,047",
                             sysincludes + includes,
                             [PLATFORM_HEADER],
                             rssdefines )
                             
                env.Depends(res_compile_command, converted_icons )

                includefolder = EPOC32_INCLUDE
                
                installfolder = []
                #if package != "": 
                    #installfolder.append( package )
                if rss_notype.endswith( "_reg" ):
                    installfolder.append( join( "private", "10003a3f","import","apps" ) )
                else:
                    installfolder.append( join( "resource", "apps" ) )
                installfolder = os.path.join( *installfolder )
                
                # Copy files for sis creation and for simulator
                def copy_file( source_path, target_path ):
                    copy_cmd = Copy( target_path, source_path )
                    #"copy %s %s" % ( source_path, target_path )
                    copyres_cmds.append( copy_cmd )
                    result_paths.append( target_path )

                rsc_filename = "%s.%s" % ( rss_notype, "rsc" )
                # Copy to sis creation folder                
                ToPackage( env, package_drive_map, package, 
                           installfolder, converted_rsc )

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
            env.Depends( build_prog, converted_resources )
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
               template = winscw.TARGET_UID_CPP_TEMPLATE_EXE % { "UID3": uid3 }
           else:
               template = winscw.TARGET_UID_CPP_TEMPLATE_DLL

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
                                join( EPOC32_RELEASE, libname ) )
        
        if targettype != TARGETTYPE_LIB:
            build_prog = env.Program( resultables, sources )
            # Depends on the used libraries. This has a nice effect since if,
            # this project depends on one of the other projects/components/dlls/libs
            # the depended project is automatically built first.
            
            env.Depends( build_prog, [ join( EPOC32_RELEASE, libname ) for libname in libraries] )
            env.Depends( build_prog, converted_icons )
            env.Depends( build_prog, converted_resources )
            env.Depends( build_prog, resource_headers )
        else:
            build_prog = env.StaticLibrary( TARGET_RESULTABLE % ".lib" , sources )
            output_libpath = ( TARGET_RESULTABLE % ".lib",
                                join( EPOC32_RELEASE, "%s.lib" % ( target ) ) )
        
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

            defbld = Builder( action = action,
                              ENV = os.environ )
            env.Append( BUILDERS = {'Def' : defbld} )
            env.Def( TARGET_RESULTABLE % ".def",
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
    
    for dep in extra_depends:
        env.Depends(sources, dep)
        env.Depends(build_prog, dep)
        #env.Depends(object_paths, dep)
        
    def copy_result_binary( ):
        """Copy the linked binary( exe, dll ) for emulator
        and to resultables folder.
        """
        installfolder = [ ]
        
        if targettype != TARGETTYPE_LIB:            
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
        
        if targettype != TARGETTYPE_LIB:
            ToPackage( env, package_drive_map, package, 
                    installfolder, 
                    copysource )
        else:  # Don't install libs to device.
            ToPackage( env, None, None, 
                    "lib", 
                    copysource )
                    
        return installed
    
    installed = copy_result_binary()
        
    if package != "" and targettype != TARGETTYPE_LIB:
        # package depends on the files anyway
        env.Depends( package, installed )
    
    return returned_command
