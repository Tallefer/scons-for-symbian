"""
API Documentation updater.
Install Epydoc: easy_install epydoc

"""
import sys
import os

if __name__ == "__main__":
    path = os.path.abspath( os.path.dirname( sys.executable ) + "\Scripts\epydoc.py" )
    
    args = '. --html -o html -v --no-sourcecode --no-private -n "SCons for Symbian API"  --exclude="update_api_doc*|setup.*|spawn.*"'
    
    cmd = "python %s %s" % ( path ,args )
    os.system( cmd )