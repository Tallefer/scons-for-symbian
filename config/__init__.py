
import os
from os.path import join, dirname, exists

from defaults import *

__userconfig = join( dirname( __file__ ), os.environ["USERNAME"], "userconfig.py" )
if exists( __userconfig  ):
    import sys
    sys.path.append( dirname( __userconfig ) )
    from userconfig import *

