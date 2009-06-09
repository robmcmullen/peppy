#!/usr/bin/env python
###############################################################################
# Name: crypto.py                                                             #
# Purpose: Cryptography helper modules                                        #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""
 The code in this file uses a fairly simple octal transformation algorithm
 combined with a random salt for the encryption/decryption, and I threw in 
 a little code obfustication just for fun ;-).

 Encrypt:
   1) Get the password string to encrypt
   2) Generate a new random salt with os.urandom() or some other randomly 
      generated string for each password to encrypt
   3) Encrypt the password by calling Encrypt(password, salt)
   4) Save the salt in the users Profile (profiler.Profile_Set(KEY, VALUE)) in
      in some way that you can associate it with the repository or passwd when
      you need to fetch it later.
       - You can put any of pythons basic types in the profile
   5) Write out the encrypted password to your config file

 Decrypt:
   1) Get the encrypted password string
   2) Get the associated salt from the profile (profiler.Profile_Get(KEY, VALUE))
   3) Decrypt and get the orignal password by calling Decrypt(encrypted_passwd, salt)

 Finally:
   This message will self destruct in 5 seconds ...

"""

#-----------------------------------------------------------------------------#

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: crypto.py 659 2008-11-16 03:46:39Z CodyPrecord $"
__revision__ = "$Revision: 659 $"

#-----------------------------------------------------------------------------#
# Imports
import os
import zlib
import random
import base64

#-----------------------------------------------------------------------------#

def _Encode(text):
    g = lambda y: (y!='\\' and [y] or [str(8+(random.randint(0,100)%2))])[0]
    return ''.join([g(y) for y in ''.join(['\\%o'%ord(x) for x in text])])

def _Decode(text):
    exec 's="'+text.replace('8','\\').replace('9','\\')+'"'
    return s

def Encrypt(passwd, salt):
    return base64.b64encode(zlib.compress(str(long(_Encode(passwd))*long(_Encode(salt).replace('8','9'))),9))

def Decrypt(passwd, salt):
    return _Decode(str(long(zlib.decompress(base64.b64decode(passwd)))/long(str.replace(_Encode(salt),'8','9'))))

#-----------------------------------------------------------------------------#
# For testing

if __name__ == '__main__':
    TEST_FILE = "TEST_passwd.crypt"
    PASSWD = 'hello world'
    tmp_file = os.path.join(os.path.curdir, TEST_FILE)
    salt = os.urandom(6)
    print "PASSWORD STR: ", PASSWD
    es = Encrypt(PASSWD, salt)
    print "ENCRYPTED STR: ", es
    print "DECRYPTED STR: ", Decrypt(es, salt)
    print "\nNow doing a write test to %s" % tmp_file
    testwrite = open(tmp_file, "wb")
    testwrite.write(es)
    testwrite.close()
    print "Write finished, now reading back and decrypting..."
    testread = open(tmp_file, "rb")
    passwd = testread.read()
    testread.close()
    print "Decrypted from File: ", Decrypt(passwd, salt)

