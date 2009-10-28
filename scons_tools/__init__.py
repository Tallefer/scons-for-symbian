""" Package containing SCons Tools for Symbian """

from os.path import join, basename, dirname, abspath

THISDIR = abspath( dirname( __file__ ) )

def initialize():
    import SCons.Tool
    SCons.Tool.DefaultToolpath.append( join(THISDIR) )


