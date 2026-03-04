from __future__ import annotations
import requests

class CustomManager(object):
    def __init__(self):
        requests.get("www.google.com")
        
    def method_a(self):
        pass