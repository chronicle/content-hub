from __future__ import annotations
import sys
import os
import site

# Ensure soar_sdk directory is in sys.path for SiemplifyUtils imports
site_packages = site.getsitepackages()
for sp in site_packages:
    soar_sdk_dir = os.path.join(sp, "soar_sdk")
    if os.path.exists(soar_sdk_dir) and soar_sdk_dir not in sys.path:
        sys.path.insert(0, soar_sdk_dir)
