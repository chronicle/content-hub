from __future__ import annotations
from .CBResponseManager import CBResponseManager
from .CBResponseManager6_3 import CBResponseManager6_3
from .CBResponseManager5_1 import CBResponseManager5_1


class CBResponseManagerLoader:
    @staticmethod
    def load_manager(version, *args, **kwargs):
        if version >= 6.3:
            return CBResponseManager6_3(*args, **kwargs)
        elif version == 5.1:
            return CBResponseManager5_1(*args, **kwargs)
        else:
            return CBResponseManager(*args, **kwargs)
