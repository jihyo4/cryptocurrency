#!/usr/bin/env python3

import argparse
import base64
import json
import requests
import sys
import time

from Crypto.PublicKey import ECC
from Crypto.Hash import SHA256, RIPEMD160

from transaction import Transaction
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

def send_transaction(node, transaction, pub_key):
    try:
        response = requests.post(
            f"http://127.0.0.1:{node}/add_transaction",
            json=(transaction, pub_key)
        )
        if response.status_code == 201:
            print("Transaction sent successfully:", response.json())
        else:
            print("Error sending transaction:", response.text)
    except Exception as e:
        print("Error connecting to node:", e)

def create_signed_transaction(sender_name, password, recipient, amount, node):
    private_key = import_priv_key(f"{KEYS}{sender_name}_priv.pem", password)
    with open(f"{KEYS}{sender_name}_pub.pem", "rb") as file:
        data = file.read()
        pub_address = get_pub_address(ECC.import_key(data).export_key(format='raw'))
    tx = Transaction(pub_address, recipient, amount, time.time())
    tx.get_inputs(node)
    if not tx.sender_input:
        print('Not enough funds')
        return None
    tx.sign_transaction(private_key)
    return tx.to_json()

def get_user_balance(name):
    with open(f"{KEYS}{name}_pub.pem", "rb") as file:
        data = file.read()
        pub_address = get_pub_address(ECC.import_key(data).export_key(format='raw'))
    r = requests.post("http://127.0.0.1:3001/get_balance", json=pub_address)
    if r.status_code == 201:
        print(r.json()['balance'])
    else:
        print('Error.')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-id', '-c', help='Create a new identity.', action='store_true')
    parser.add_argument('--get-key', '-g', help='Get private key.', action='store_true')
    parser.add_argument('--add-transaction', '-t', help='Create a transaction.', action='store_true')
    parser.add_argument('--get-balance', '-b', help='Get balance.', action='store_true')
    parser.add_argument('--name', '-n', help='Name of the identity', type = str)
    parser.add_argument('--password', '-p', help='Password of the identity', type = str)
    parser.add_argument('--recipient', '-r', help='Recipient address', type = str)
    parser.add_argument('--node', '-nd', help='Node port', type = int)
    parser.add_argument('--amount', '-a', help='Amount to send', type = float)
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
    elif args.get_key:
        print(import_priv_key(f"{KEYS}{args.name}_priv.pem", args.password))
        return 0
    elif args.get_balance:
        get_user_balance(args.name)
        return 0
    elif args.add_transaction:
        if (not args.recipient) or (not args.node) or (not args.amount):
            print('Please provide the address of the recipient, port of the node and the amount to send.')
            return 1
        transaction = create_signed_transaction(
            args.name,
            args.password,
            args.recipient,
            args.amount,
            args.node
        )
        if not transaction:
            return 1
        with open(f"{KEYS}{args.name}_pub.pem", "rb") as file:
            data = file.read()
        pub_key = json.dumps({
            "key": base64.b64encode(data).decode("utf-8")
        })
        send_transaction(args.node, transaction, pub_key)
    if args.debug:
        with open(f"{KEYS}{args.name}_pub.pem", "rb") as file:
            data = file.read()
            print(ECC.import_key(data).export_key(format='raw'))
        return 0

if __name__ == '__main__':
    sys.exit(main())