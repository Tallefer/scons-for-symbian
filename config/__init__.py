
import os
import sys
from os.path import join, dirname, exists

from defaults import *
__username = "USERNAME"
if sys.platform == "linux2":
    __username = "USER"

__userconfig = join( dirname( __file__ ), os.environ[__username], "userconfig.py" )
if exists( __userconfig  ):
    import sys
    sys.path.append( dirname( __userconfig ) )
    from userconfig import *

