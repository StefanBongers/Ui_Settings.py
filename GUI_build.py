import os
from qtpy import uic
#
if __name__ == '__main__':
    print("Compiling all files under %s" % os.path.abspath("."))
    uic.compileUiDir("Beringungsoberflaeche", recurse=True)
    #if input("Fortfahren? [y]/n ") != "n":
    exit()
