
---


# Regular Symbian project using .mmp file #
## ipc.mmp ##
```
targettype dll
TARGET	       _ipc.pyd
TARGETPATH     \sys\bin

CAPABILITY NetworkServices LocalServices ReadUserData WriteUserData Location UserEnvironment PowerMgmt ProtServ SwEvent SurroundingsDD ReadDeviceData WriteDeviceData TrustedUI

SYSTEMINCLUDE \epoc32\include
SYSTEMINCLUDE \epoc32\include\libc
SYSTEMINCLUDE \epoc32\include\python

USERINCLUDE   .

LIBRARY python222.lib
LIBRARY euser.lib

source  ipcmodule.cpp

NOSTRICTDEF
```

## bld.inf ##
```
PRJ_PLATFORMS

PRJ_MMPFILES
ipc.mmp
```

## Building ##
Generate project files
> bldmake bldfiles

Build for simulator:
> abld build winscw udeb

Build for device:
> abld build gcce urel



---

# SCons project #
With SCons you define a single file called 'SConstruct'. It is Python file even though it has no .py extension. You can define multiple SConstructs if you wish to create more complex projects.

## SConstruct ##
```
#!/usr/env/bin python
import os
import glob

from scons_symbian import *

COMMON_DEFINES = [ 
    #"__DEBUG_LOGGING__" 
]

def IPCPyd():
    "Build IPC module"
    # Use all .cpp files in the current directory.
    sources  = glob.glob( "*.cpp" )
    inc      = [ EPOCROOT + r"epoc32/include/libc",
                 EPOCROOT + r"epoc32/include/python",
                 r"."
               ]
    libs = ["python222", "euser"]
    return SymbianProgram( '_ipc', TARGETTYPE_PYD,
                            sources, inc, libs,
                            capabilities = FREE_CAPS,
                            defines      = COMMON_DEFINES )

IPCPyd()

```

## SConstruct & MMP import ##

It's not fun to redefine your project, if there is a complete MMP around.
```
#!/usr/env/bin python
from scons_symbian import *
SymbianProgram( "ipc.mmp" )
```

## Building ##
Build for simulator
> scons compiler=winscw

Build for device
> scons compiler=gcce release=urel

Use parallel building( if you have multiple cores )
> scons --jobs=2


---
