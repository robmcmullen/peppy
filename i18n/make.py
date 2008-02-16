import glob, po2dict, shutil

for poFile in glob.glob('*.po'):
    print poFile
    pyFile = po2dict.make(poFile)
    shutil.move(pyFile, '../peppy/i18n/%s'%pyFile)
