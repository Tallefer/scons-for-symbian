"""

    Workaround Windows command line length limitations.
    
    http://www.scons.org/wiki/LongCmdLinesOnWin32 

"""
import subprocess
import string

import win32file
import win32event
import win32process
import win32security

def subsitute_env_vars(line, env):
    """ Substitutes environment variables in the command line.
    
    E.g. dir %EPOCROOT% -> dir T:\
    
    The command line does not seem to do this automatically when launched
    via subprocess.
    """
    for key,value in env.items():
        line = line.replace("%%%s%%" % key, value)
    return line


def win32_spawn(sh, escape, cmd, args, spawnenv):
    """ Extended command line spawner for Windows.
    
    Workaround Windows command line limitation up to 32k characters.
    """
    for var in spawnenv:
        spawnenv[var] = spawnenv[var].encode('ascii', 'replace')

    # If we have path names containing spaces escaped with quotes
    # we need to have a sepcial quote unstripping for them here
    newargs = []
    for a in args:
        if len(a) >= 2:
            if a[0] == '"' and a[-1] == '"':
                a = a[1:-1]
        newargs.append(a)
            

    sAttrs = win32security.SECURITY_ATTRIBUTES()
    StartupInfo = win32process.STARTUPINFO()
    newargs = string.join(map(escape, newargs[1:]), ' ')
    cmdline = cmd + " " + newargs
    cmdline = subsitute_env_vars(cmdline, spawnenv)
    # check for any special operating system commands
    
    if cmd == 'del':
        for arg in args[1:]:
            win32file.DeleteFile(arg)
        exit_code = 0
    else:
        # otherwise execute the command.
        hProcess, hThread, dwPid, dwTid = win32process.CreateProcess(None, cmdline, None, None, 1, 0, spawnenv, None, StartupInfo)
        win32event.WaitForSingleObject(hProcess, win32event.INFINITE)
        exit_code = win32process.GetExitCodeProcess(hProcess)
        win32file.CloseHandle(hProcess);
        win32file.CloseHandle(hThread);
    return exit_code

# TODO: Not reliable
class SubprocessSpawn:
    """ A custom spawner to workaround windows command line length limit. 
    
    Up to 32 000 characters.
    """ 
    
            
    def __call__(self, sh, escape, cmd, args, env):
        newargs = string.join(args[1:], ' ')
        cmdline = cmd + " " + newargs
        cmdline = self.subsitute_env_vars(cmdline, env)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, startupinfo=startupinfo, shell = False, env = env)
        data, err = proc.communicate()
        rv = proc.wait()
        if rv:
            # The process exited with error status
            # Display the error to the console.
            print "====="
            print data, err
            print "====="
        return rv

