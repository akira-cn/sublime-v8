## To build your own PyV8 ?

If the PyV8 lib not work at your sublime text 2 version, you may build your own PyV8 lib from source.

http://code.google.com/p/pyv8/wiki/HowToBuild

After the lib was built, copy the binary file to replace the old file on the sub-directory (win32, osx or linux). 

If you've to update the python console version on osx just setup a new python version with MacPort then execute the command :

    sudo ln -s /the/new/python /System/Library/Frameworks/Python.framwork/Versions/2.6/python