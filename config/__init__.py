
import os
import sys
from os.path import join, dirname, exists

from defaults import * #IGNORE:W14 W4

__username = "USERNAME" #IGNORE:W006
if sys.platform == "linux2":
    __username = "USER" #IGNORE:W6

__userconfig = join( dirname( __file__ ), os.environ[__username], "userconfig.py" ) #IGNORE:W6
if exists( __userconfig  ):
    sys.path.append( dirname( __userconfig ) )
    from userconfig import * #IGNORE:W14

