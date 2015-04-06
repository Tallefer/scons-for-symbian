This page contains information about SCons for Symbian command line parameters. For more up-to-date information type: scons -h. It also shows your own custom command line parameters.

### Parameters ###
components=my.dll,my.exe,...
> Consider only listed components

compiler=<winscw\gcce>
> Use winscw or gcce compiler.( Currently only one compiler supported at a time )

release=<udeb\urel>
> With or without debugging

defines=<list of definitions>
> These definitions are passed to compiler/preprocessor.

dosis=<true\false, default:false>
> When true, enables sis file creation. Disabled by default to not get in the way of lightning fast code-compile cycle.

### Example ###
scons compiler=winscw release=udeb components=my.dll --debug=explain

--debug=explain is SCons' own parameter.