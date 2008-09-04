#!/usr/bin/env python

"""
Helper functions for relative paths.
Print relative path from /a/b/c/d to /a/b/c1/d1

Author: Cimarron Taylor
Date: July 6, 2003

"""
__author__ = "Cimarron Taylor"
__date__   = "July 6, 2003"

import os

def pathsplit(path):
    """ This version, in contrast to the original version, permits trailing
    slashes in the pathname (in the event that it is a directory).
    It also uses no recursion """
    return path.split(os.path.sep)

def commonpath(l1, l2, common=[]):
    if len(l1) < 1: return (common, l1, l2)
    if len(l2) < 1: return (common, l1, l2)
    if l1[0] != l2[0]: return (common, l1, l2)
    return commonpath(l1[1:], l2[1:], common+[l1[0]])

def relpath(p1, p2):
    (common,l1,l2) = commonpath(pathsplit(p1), pathsplit(p2))
    p = []
    if len(l1) > 0:
        p = [ '../' * len(l1) ]
    p = p + l2
    return os.path.join( *p )

def test(p1,p2):
    print "from", p1, "to", p2, " -> ", relpath(p1, p2)

if __name__ == '__main__':
    test('/a/b/c/d', '/a/b/c1/d1')