#!/usr/bin/env python

"""
Helper functions for relative paths.
Print relative path from /a/b/c/d to /a/b/c1/d1

Author: Cimarron Taylor
Date: July 6, 2003

"""
from os.path import abspath
__author__ = "Cimarron Taylor"
__date__   = "July 6, 2003"

import os

def pathsplit(path):
    """ This version, in contrast to the original version, permits trailing
    slashes in the pathname (in the event that it is a directory).
    It also uses no recursion """    
    return os.path.abspath( path ).replace("\\","/").split("/")

def commonpath(l1, l2, common=[]):                
    if len(l1) < 1: return (common, l1, l2)
    if len(l2) < 1: return (common, l1, l2)
    if l1[0] != l2[0]: return (common, l1, l2)
    return commonpath(l1[1:], l2[1:], common+[l1[0]])

def relpath(p1, p2):

        
    p1 = abspath(p1).replace("\\","/")
    p2 = abspath(p2).replace("\\","/")
    
    if len(p1) >= 2 and len(p2) >= 2:
        if p1[1] == ":" and p2[1] == ":": # On windows using drive
            if p1[0].lower() != p2[0].lower(): # Check drive
                return p2.replace("\\","/") # Return absolute path of the target
    
    p1, p2 = pathsplit(p1), pathsplit(p2)
    
    (common,l1,l2) = commonpath(p1, p2)
    p = []
    if len(l1) > 0:
        p = [ '..' ] * len(l1)
        
    p = p + l2
    return "/".join( p )

def test(p1,p2):
    print "from", p1, "to", p2, " -> ", relpath(p1, p2)

if __name__ == '__main__':
    test('/a/b/c/d', '/a/b/c1/d1')