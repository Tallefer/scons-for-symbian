"""
Console output colorizer. pyreadline required( on windows )
"""
__author__    = "Jussi Toivola"
__license__   = "MIT License"

import os
import sys
import subprocess as sp

from SCons.Platform import win32

#: Pyreadline console
CONSOLE = None
try:
    # Only Windows supported for now.
    import platform
    if platform.system() == "Windows":
        import pyreadline
        CONSOLE = pyreadline.GetOutputFile()
except ImportError:
    #print "pyreadline not available."
    pass

#: Color constants. TODO: Get from user settings.
class Colors:
    WARNING = 14
    ERROR   = 12
    NORMAL  = 7
    COMMENT = 10

#: Get initial color of the console
if CONSOLE is not None:
    Colors.NORMAL = CONSOLE.attr


#: Lines containing these strings are drawn in Colors.ERROR color
KEYWORD_ERRORS = [ x.lower() for x in [ "error:", " error ", "failed", " undefined ", "does not match", "illegal",
               "was expected", "The process cannot access",
               "No such file or directory", "*** "
               "Cannot convert", "needed by", "explicit dependency" ] ]

#: Excluded errors
KEYWORD_ERRORS_EXCLUDE = [ "error." ]

#: Drawn with Colors.COMMENT
KEYWORD_COMMENT  = [ x.lower() for x in [ "scons:", "note:", "copy("] ]

#: Excluded comments
KEYWORD_COMMENT_EXCLUDE = []

#: Warning keywords. Drawn with Colors.WARNING
KEYWORD_WARNINGS = ["warning ", "warning:"]

#: Excluded warnings
KEYWORD_WARNINGS_EXCLUDE = ["-warning"]

#: Map colors to keywords.
KEYWORDMAP = [ ( KEYWORD_WARNINGS, KEYWORD_WARNINGS_EXCLUDE, Colors.WARNING ),
               ( KEYWORD_ERRORS,   KEYWORD_ERRORS_EXCLUDE,   Colors.ERROR ),
               ( KEYWORD_COMMENT,  KEYWORD_COMMENT_EXCLUDE,  Colors.COMMENT ) ]

class LineCounts:
    def __init__(self):
        self.reset()

    def reset(self):
        self.Errors   = 0
        self.Warnings = 0
        self.Others   = 0
LINECOUNTS = LineCounts()

#: Original sys.stdout
savedstdout = sys.stdout

def subsitute_env_vars(line, env):
    """ Substitutes environment variables in the command line.
    
    E.g. dir %EPOCROOT% -> dir T:\
    
    The command line does not seem to do this automatically when launched
    via subprocess.
    """
    for key,value in env.items():
        line = line.replace("%%%s%%" % key, value)
    return line
    
def write( line, color ):
    """Write line with color"""
    global CONSOLE
    
    if CONSOLE is not None:
        try:
            CONSOLE.write_color( line, color)
            CONSOLE.write_color( "", CONSOLE.attr)
        except TypeError:
            # Occurs at least when redirecting data to a file
            # So disable the color support
            CONSOLE = None
            savedstdout.write( line )
    else:
        savedstdout.write( line )
        
def comment(line):
    "Util for comments"
    write(line + "\n", Colors.COMMENT)
    
def error( line ):
    "Util for errors"
    write(line, Colors.ERROR)


class ConsoleBase(object):
    """Base class for colored console output"""

    def flush(self):
        self.savedstderr.flush()
        self.savedstdout.flush()

    def read(self):
        """Read both stdout and stderr and output the data with colors"""
        block  = None
        result = ""

        while block != "":
            block = self.savedstdout.readline()
            self.write(block)
            result += block

            block = self.savedstderr.readline()
            self.write(block)
            result += block

        return result

class OutputConsole(ConsoleBase):
    """Handles spawning external processes and colors the console output.
    """
    def __init__(self ):
        ConsoleBase.__init__(self)

        self.savedstdout = sys.stdout
        self.savedstderr = sys.stderr
        self.savedspawn  = os.spawnve
        
        sys.stdout       = self
        sys.stderr       = self
        
        win32.spawn = self.spawn

    def spawn( self, sh, escape, cmd, args, env):
        """
        Replaces SCons.Platform.spawn to colorize output of
        external processes
        """

        args = [ subsitute_env_vars( x.replace('"', '' ), env ) for x in args ]    
        
        # Long command support <= 32766
        startupinfo          = sp.STARTUPINFO()
        startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
        
        p = sp.Popen( args, bufsize = 1,
                      stdout = sp.PIPE, stderr=sp.STDOUT,
                      startupinfo = startupinfo,
                      shell = False, env = env)

        out, err = p.communicate( )
        self.write( out )
        result = p.wait()

        return result
        
    def write(self, text ):
        """Colorize each line based on the keywords"""
          
        lines = text.split("\n")
        
        for i in xrange(len(lines)):
            
            line = lines[i]
            lowcase = line.lower()

            detected = False
            for kws,excludes,color in KEYWORDMAP:
                # Check keywords and exclusion keywords
                if  len( [x for x in kws if x in lowcase] ) > 0 \
                and len( [x for x in excludes if x in lowcase] ) == 0:
                    write( line, color )
                    detected = True
                    break

            # Draw in normal color then
            if not detected:
                write( line, Colors.NORMAL)

            if i < ( len(lines) -1 ):
                write( "\n", Colors.NORMAL)


