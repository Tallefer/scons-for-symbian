""" Constant definitions """


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
DLL_TARGETTYPES = [ TARGETTYPE_PLUGIN, TARGETTYPE_DLL, 
                    TARGETTYPE_PYD, TARGETTYPE_LIB ]

#: Maps targettype to correct uid1
TARGETTYPE_UID_MAP = {
    TARGETTYPE_DLL : "0x10000079",
    TARGETTYPE_EXE : "0x1000007a",
    TARGETTYPE_LIB : "",
}
  
#: Easy constant for self signed apps
CAPS_SELF_SIGNED = [
    "ReadUserData",    "WriteUserData", 
    "NetworkServices", "UserEnvironment", 
    "LocalServices"
]

#: Easy constant for caps granted for development certificate
CAPS_DEV_CERT = "NetworkServices LocalServices ReadUserData " \
            "WriteUserData Location UserEnvironment PowerMgmt " \
            "ProtServ SwEvent SurroundingsDD ReadDeviceData " \
            "WriteDeviceData TrustedUI".split()

#: For backward compatibility
FREE_CAPS = CAPS_DEV_CERT

#: Constant for S60 UI platform
UI_PLATFORM_S60 = "S60"
#: Constant for UIQ UI platform
UI_PLATFORM_UIQ = "UIQ"
#: List of possible UI platforms
UI_PLATFORMS    = [UI_PLATFORM_S60, UI_PLATFORM_UIQ]
#: Constant for current UI platform
#: One of UI_PLATFORMS
UI_PLATFORM = ""

# Extension added to sis files signed with signsis.
SIGNSIS_OUTPUT_EXTENSION = ".sisx"
            
#: Are we running a build? This is to avoid messing up code analyzers
#: and Epydoc.
import sys
RUNNING_SCONS = ( "scons" in sys.argv[0] or "-c" == sys.argv[0] )            
del sys