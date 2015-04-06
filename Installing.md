#### Install [SCons](http://www.scons.org/). ####
I used
> easy\_install scons

At least SCons 0.98.5 did not install properly so you most likely need to copy the SCons folder from:
> Python25\Lib\site-packages\scons-0.98.5-py2.5-win32.egg\scons-0.98.5
to
> Python25\Lib\site-packages\

After that you should have SCons folder under site-packages.
Also remember to check that you have Python25\Scripts folder in your PATH.

#### IMPORTANT: Install pywin32 for parallel compiling ####
SCons warns you about it: parallel (-j) builds may not work reliably with open Python files.
Install page:
> http://sourceforge.net/project/showfiles.php?group_id=78018&package_id=79063&release_id=616849

#### Get sources ####
  * Create 'scons\_symbian' folder to 'Python25\Lib\site-packages\'
  * Check out the project to the created folder
    * Follow the non-members' checkout instructions under [Source](http://code.google.com/p/scons-for-symbian/source/checkout) tab.

And you should be good to go.

#### Install Ensymble ( Optional ) ####

Even though PKG generation support is implemented, SIS files can also be created with [Ensymble](http://www.nbl.fi/~nbl928/ensymble.html). It can be a handy utility for various other tasks too. Get the source package, **DO NOT** get a pre-squeezed version.
  * Unpack the archive
  * Create 'ensymble' folder to 'Python25\Lib\site-packages\'
  * Put the ensymble files there
  * Add init.py file to allow importing ensymble.
  * Get the openssl stuff mentioned in the Ensymble readme and put 'em in your PATH.
Just to be sure. Start python interpreter and try to import ensymble.