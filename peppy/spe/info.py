import os,sys 

PLATFORM                    = sys.platform
WIN                         = PLATFORM.startswith('win')
DARWIN                      = PLATFORM.startswith('darwin')
LINUX                       = not (WIN or DARWIN)

if WIN:
    windowsVer = sys.getwindowsversion()
    if (windowsVer[3] == 1 ):
        WIN98   = True
    else:
        WIN98   = False
else:
    WIN98       = False
    
PYTHON_EXEC                 = sys.executable
if WIN:
    if PYTHON_EXEC.endswith('w.exe'):
        PYTHON_EXEC = PYTHON_EXEC[:-5] + '.exe'
    try:
        import win32api
        PYTHON_EXEC         = win32api.GetShortPathName(PYTHON_EXEC)
        PYTHON_COM          = True
    except ImportError:
        PYTHON_EXEC         = (r'%s'%PYTHON_EXEC).replace('Program Files','progra~1')
        PYTHON_COM          = False
    if ' ' in PYTHON_EXEC:
        PYTHON_EXEC         = '"%s"'%PYTHON_EXEC
elif DARWIN:
    PYTHON_EXEC.replace('ython','ythonw')
    PYTHON_COM              = False
else:
    PYTHON_COM              = False

PATH                        = os.path.dirname(__file__)
_PATH                       = os.path.dirname(PATH)
