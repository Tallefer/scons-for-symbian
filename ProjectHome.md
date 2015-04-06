# Introduction #
SCons for Symbian is a build toolchain intended as a replacement for Perl and MMP files used on regular Symbian projects. Tested on SCons 1.1.0

### Check Wiki for: ###
  * [BenchMark](BenchMark.md) for speed comparison between SCons and MMP building.
  * [Parameters](http://code.google.com/p/scons-for-symbian/wiki/Parameters) for information about possible command line arguments.
  * [Installing](http://code.google.com/p/scons-for-symbian/wiki/Installing) for installation instructions
  * [ExampleProject](ExampleProject.md) for... example project.

## What is SCons? ##
From SCons FAQ:
> SCons is a software construction tool--that is, a superior
> alternative to the classic "Make" build tool that we all
> know and love.

With SCons, MMP files are replaced with Python scripts. No more limiting '#ifdef THIS' preprocessor stuff. Now you have the power of Python to create your project. But you don't have to recreate your project from scratch: MMP import is supported.

Have you noticed that resources are not always updated when they should. Well, I have. No worries here anymore. No need for 'abld reallyclean' all the time. SCons produces more reliable builds by using a checksum to check if files have changed instead of only looking at the time of change.

SCons also supports parallel compiling out-of-the-box speeding up compiling process over 2x and it's faster even without parallel compiling. See the BenchMark. And do you hate listing all those .cpp files you need to build? Use Python's glob module instead. See SCons [homepage](http://www.scons.org/) for more info.

## Other projects using SCons for Symbian ##
  * [pygame for S60](http://code.google.com/p/pygame-symbian-s60)
  * [LogMan](http://code.google.com/p/logman-for-symbian/)
  * [PyS60 Community Edition](https://code.launchpad.net/pys60community)

## Supported features ##
The most important features required to build a working application.
  * Support for S60 3rd ( MR, FP1, FP2) and S60 5th edition SDKs
    * GCCE & WINSCW compiling
    * Icons
    * Resources
  * Automatic SIS creation
    * [Ensymble](http://code.google.com/p/ensymble/) by default
    * PKG files
      * Automatic PKG generation and signing
      * Templates powered by [preppy](http://www.reportlab.org/preppy.html).
  * Colorized output ( uses [pyreadline](http://ipython.scipy.org/moin/PyReadline/Intro) )
    * Errors, warnings and comments shown in different colors based on keywords.
  * Linux support
    * Requires [GnuPoc](http://www.martin.st/symbian/) and Wine
  * PyS60 support
    * Create byte-compiled and zipped python library for your application.
  * User configuration file
    * Make your own defaults
  * Additional default preprocessor definitions
    * `__SYMBIAN_OS_VERSION__` = 91,...
    * `__UI_VERSION__` = 30,...
    * `__UID3__` = <application/module uid3>
      * Changing development UID made easier
    * `__UIQ__`, `__UIQ_??__`, `__UIQ_?X__`
      * Defines for UIQ similar to S60
  * MMP export
    * For those who don't see the light.


## Untested/incomplete features ##
  * UIQ3
    * I don't own or know anybody with UIQ3 device so it is hard to test.
    * HelloWorld compiles without errors.
  * MMP import
    * Stick with your old MMP, but let SCons do the dirty work.
  * Context Help file compilation
  * setup.py for easy install

## Missing or planned features ##
At least these features are missing. There are propably a lot more that I am not even aware of.
  * Rewrite used Perl scripts in Python
    * ~~RComp launcher~~
    * cshlpcmp
      * Crashes perl
  * ccache & distcc?
    * Are these possible?
  * Try to get rid of the inability to use drive letter in EPOCROOT
  * ARMV5/RVCT compiling
  * EKA1
    * ARMI,THUMB,WINS compiling
