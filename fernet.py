# unicode utf8
from cryptography.fernet import Fernet

key = b'7mwDo5p3mft4qW3DJzhwKzC65vgYWgW45FhL_0DOg2E='

f = Fernet(key)

pw2byte = input("Passwort plain in byte übersetzen? [y/n] : ")
if pw2byte.lower() == 'y':
    pw = input('Passwort eingeben: ')
    token = f.encrypt(pw.encode())
    print('PW als byte: ' + token.decode())
else:
    pw2string = input("Bitte decodierten Byte-Wert des PW eingeben: ")
    token = f.decrypt(pw2string)
    print("PW als plain: " + token.decode())



