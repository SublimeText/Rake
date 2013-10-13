import sys
if sys.version[0] >= "3":
    from .python3 import *
else:
    from python2 import *
