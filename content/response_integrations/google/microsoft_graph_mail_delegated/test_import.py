import sys
import os
int_dir = os.path.dirname(__file__)
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)

import soar_sdk
sdk_dir = os.path.dirname(soar_sdk.__file__)
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

print(sys.path)

try:
    from core.MicrosoftGraphMailDelegatedManager import ApiManager
    print("Import success")
except Exception as e:
    import traceback
    traceback.print_exc()
