import os

def localfile(name):
    path = os.path.join(os.path.dirname(__file__), name)
    return path

