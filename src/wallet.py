#!/usr/bin/env python3

import argparse
import sys
from Crypto.PublicKey import ECC
from Crypto.Hash import SHA256, RIPEMD160

from validation import passwordValidation, nameValidation

KEYS = './keys/'

def import_priv_key(path, password):
    with open(path, "rt") as file:
        data = file.read()
        return ECC.import_key(data, password)
    
def get_pub_address(pub_key):
    sha256 = SHA256.new()
    sha256.update(pub_key)
    rip = RIPEMD160.new()
    rip.update(sha256.digest())
    hash = '00' + rip.hexdigest()
    sha256 = SHA256.new()
    sha256.update(hash.encode())
    sha = SHA256.new()
    sha.update(sha256.digest())
    return hash + sha.hexdigest()[:8]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-id', '-c', help='Create a new identity.', action='store_true')
    parser.add_argument('--get-key', '-g', help='Get private key.', action='store_true')
    parser.add_argument('--name', '-n', help='Name of the identity', type = str)
    parser.add_argument('--password', '-p', help='Password of the identity', type = str)
    parser.add_argument('--debug', '-d', help='Debug.', action='store_true')
    args = parser.parse_args()
    if (not args.name) or (not nameValidation(args.name)):
        print('Please input a correct name.')
        return 1
    if (not args.password) or (not passwordValidation(args.password)):
        print('Please input a correct password.')
        return 1
    if args.create_id:
        key = ECC.generate(curve='p256')
        priv_key = key.export_key(format='PEM', passphrase=args.password.encode(),protection='PBKDF2WithHMAC-SHA512AndAES256-CBC',prot_params={'iteration_count':131072})
        pub_key = key.public_key().export_key(format='PEM')       
        with open(f"{KEYS}{args.name}_priv.pem", "wt") as file:
            file.write(priv_key)
        with open(f"{KEYS}{args.name}_pub.pem", "wt") as file:
            file.write(pub_key)
        with open(f"{KEYS}{args.name}_pub_address.txt", "wt") as file:
            file.write(get_pub_address(key.public_key().export_key(format='raw')))
        print(f"Created identity {args.name}.")
        return 0
    if args.get_key:
        print(import_priv_key(f"{KEYS}{args.name}_priv.pem", args.password))
    if args.debug:
        with open(f"{KEYS}{args.name}_pub.pem", "rb") as file:
            data = file.read()
            print(get_pub_address(ECC.import_key(data).export_key(format='raw')))

if __name__ == '__main__':
    sys.exit(main())