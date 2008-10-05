"""Default configuration. 
These variables + the variables in constants are modifiable in 
user configuration.
"""

import os

from constants import * #IGNORE:W14

#: Default EPOCROOT. Assuming most people subst sdk folder to a drive.
#: Unfortunately I can't make such assumptions on Linux where it is set to "".   
EPOCROOT = os.path.sep

#: Default release
RELEASE = RELEASE_UDEB

#: Default compiler
COMPILER = COMPILER_WINSCW

DO_CREATE_SIS = False

# These are enabled from FP1 onwards on regular scripts. 
# Positioning module stops working on PyS60 ==> removed.
# -O2 -fno-unit-at-a-time"
GCCE_OPTIMIZATION_FLAGS = ""


if os.name == "posix":    
    EPOCROOT = ""
    COMPILER = COMPILER_GCCE