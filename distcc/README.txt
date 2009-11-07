HOWTO distcc with symbian-for-scons:

1. install cygwin (must be on same drive as compiler and 
   sources) in \cygwin folder.
   
1.1. Install admin/cygrunsrv to be able to run 
     distccd server as service
     
1.2. Install devel/distcc to be able to run distcc client and server
   
2. Install arm compiler wrapper needed for distcc

2.1. If you installed cygwin with dos crlf copy
     arm-none-symbianelf-g++.wrapper.cygwin_dos as arm-none-symbianelf-g++.wrapper
     to ?:\Program Files\CSL Arm Toolchain\bin     

2.2. If you installed cygwin with unix crlf copy
     arm-none-symbianelf-g++.wrapper.cygwin_unix as arm-none-symbianelf-g++.wrapper
     to ?:\Program Files\CSL Arm Toolchain\bin

Start arm-none-symbianelf-g++.wrapper from cygwin shell, if you get some message
that \r is wrong, you copied wrong wrapper. You should get message:
arm-none-symbianelf-g++.exe: warning: `-x c' after last input file has no effect
arm-none-symbianelf-g++.exe: no input files

3. Setup distccd server on win32/cygwin

3.1. Start distccd from command line to see if it works

distccd -N 19 -a 192.168.0.0/16 --verbose --no-detach --log-stderr
(change 192.168.0.0/16 with your local subnet)

3.2. Create script which will be run as service

From cygwin shell create file 
/usr/local/bin/startdistccd.sh with following content:

#!/usr/bin/sh
CROSS_CC_PATH="/cygdrive/c/Program Files/CSL Arm Toolchain/bin"
DISTCCD_EXEC=/usr/bin/distccd
DISTCCD_ARGS="--nice 19 -a 192.168.0.0/16 --no-detach --daemon"
export PATH="$CROSS_CC_PATH:$PATH"
exec $DISTCCD_EXEC $DISTCCD_ARGS

3.3. Allow execution of script

chmod 755 /usr/local/bin/startdistccd.sh

3.4 Install distcc as windows service

cygrunsrv.exe -I distcc --path /usr/local/bin/startdistccd.sh --shutdown

3.5. Start distcc service

net start distcc

before starting scons set DISTCC_HOSTS environment variable, e.g.:
set DISTCC_HOSTS="192.168.0.1 192.168.0.2 192.168.0.3"

Enjoy distributed symbian scons building :)

KNOWN PROBLEM 1 (and solution):
To avoid mifconv poping error when building for FP copy mifconv from FP1 to FP2.
Copy C:\Symbian\9.2\S60_3rd_FP1\Epoc32\tools\mifconv.exe 
C:\S60\devices\S60_3rd_FP2_SDK_v1.1\epoc32\tools

KNOWN PROBLEM 2 (and solution):
When building with distcc for FP2, you will get error that #include expect
filename in C:\S60\devices\S60_3rd_FP2_SDK_v1.1\epoc32\include\gcce\gcce.h
This is because gcce.h have:
  #if defined(__PRODUCT_INCLUDE__)
  #include __PRODUCT_INCLUDE__
  #endif
Preprocessor failes to include this file, to solve this issue, change gcce.h
to:
  #if defined(__PRODUCT_INCLUDE__)
  #define ___ST(b) #b
  #define __ST(b) ___ST(b)
  #include __ST(__PRODUCT_INCLUDE__)
  #endif