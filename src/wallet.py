#!/usr/bin/env python3

import argparse
import hashlib  
import json
import sqlite3
import sys
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA512

DATABASE = "./sqlite3.db"

def generateKeyPair(password):
    keys = RSA.generate(3072)
    return keys.exportKey(passphrase=password, pkcs=8, protection='PBKDF2WithHMAC-SHA512AndAES256-CBC', prot_params={'iteration_count':21000}), keys.publickey().exportKey()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='Initialise the database.', action='store_true')
    parser.add_argument('--create-id', '-c', help='Create a new identity.', action='store_true')
    parser.add_argument('--name', '-n', help='Name of the identity', type = str)
    parser.add_argument('--password', '-p', help='Password of the identity', type = str)
    parser.add_argument('--debug', '-d', help='Prints everything in the database', action='store_true')
    args = parser.parse_args()
    if args.init:
        print("Database initiated.")
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        sql.execute("DROP TABLE IF EXISTS keys;")
        sql.execute("CREATE TABLE keys (name VARCHAR(32) PRIMARY KEY, priv_key BLOB, pub_key BLOB);")
        sql.execute("INSERT INTO keys (name, priv_key, pub_key) VALUES ('bro', 'a', 'b');")
        db.commit()
        return 0
    if args.create_id:
        print(f"Created identity {args.name}.")
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        cmd = f"INSERT INTO keys (name, priv_key, pub_key) VALUES (?, ?, ?);"
        keys = generateKeyPair(args.password)
        sql.execute(cmd, (args.name, keys[0], keys[1]))
        db.commit()
        return 0
    if args.debug:
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        cmd = f"SELECT name, priv_key, pub_key FROM keys"
        sql.execute(cmd)
        print(sql.fetchall())

if __name__ == '__main__':
    sys.exit(main())