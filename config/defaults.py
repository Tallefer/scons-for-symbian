
from scons_symbian.config.constants import *

#: Default EPOCROOT. Assuming most people subst sdk folder to a drive.
EPOCROOT = "\\"

#: Default release
RELEASE = RELEASE_UDEB

#: Default compiler
COMPILER = COMPILER_WINSCW

DO_CREATE_SIS = False


# These are enabled from FP1 onwards on regular scripts. 
# Positioning module stops working on PyS60 ==> removed.
# -O2 -fno-unit-at-a-time"
GCCE_OPTIMIZATION_FLAGS = ""

