import sys
import os

int_dir = os.path.dirname(os.path.abspath(__file__))
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)

import soar_sdk
sdk_dir = os.path.dirname(soar_sdk.__file__)
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

try:
    import core
    print("CORE PATH:", core.__file__)
except Exception as e:
    print("CORE IMPORT ERROR:", e)
