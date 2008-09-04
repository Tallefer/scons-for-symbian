"""
SCons for Symbian
=================

SCons for Symbian is a build toolchain intended as a replacement for Perl and 
MMP files used on regular Symbian projects.

See examples folder for usage.

Main construction interfaces are L{SymbianProgram} and L{SymbianPackage}. Useful 
constants can be found from L{arguments} module.
"""

__author__    = "Jussi Toivola"
__license__   = "MIT License"

from scons_symbian import *