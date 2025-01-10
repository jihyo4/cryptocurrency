import hashlib
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from Crypto.PublicKey import ECC
import base64
from utils import broadcast_message

from transaction import Transaction, Input
from wallet import get_pub_address, KEYS

REWARD = 50.0
DIFFICULTY = 5  # Number of leading zeros required in the hash

class Miner:
    def __init__(self, blockchain, nodes, owner):
        self.transaction_pool = []
        self.blockchain = blockchain
        self.unspent_inputs = {}    
        self.mining_executor = ThreadPoolExecutor(max_workers=1)
        self.nodes = nodes
        self.mining = False
        self.address = None
        if owner: self.change_owner(owner)

        if not self.blockchain:
            # print("generating genesis here")
            genesis_block = self.create_genesis_block()
            self.blockchain.append(genesis_block)
        for block in self.blockchain:
            print(block)
            self.update_unspent_inputs(block)

    def update_unspent_inputs(self, block):
        """Remove used inputs and add new ones"""
        used_inputs = {}
        added_inputs = {}
        for transaction in block["transactions"]:
            tx = Transaction.from_json(transaction)
            for inp in tx.sender_input:
                if tx.sender == "Coinbase":
                    continue
                input = Input.from_json(inp)
                if input.address not in used_inputs.keys():
                    used_inputs[input.address] = []
                used_inputs[input.address].append(input.to_json())
            for out in tx.recipients:
                output = Input.from_json(out)
                if output.address not in added_inputs.keys():
                    added_inputs[output.address] = []
                added_inputs[output.address].append(output.to_json())

        for public_key, spent_inputs in used_inputs.items():
            if public_key in self.unspent_inputs:
                self.unspent_inputs[public_key] = [
                    input_obj for input_obj in self.unspent_inputs[public_key]
                    if input_obj not in spent_inputs
                ]
                if not self.unspent_inputs[public_key]:
                    del self.unspent_inputs[public_key]

        for public_key, new_inputs in added_inputs.items():
            if public_key in self.unspent_inputs:
                self.unspent_inputs[public_key].extend(new_inputs)
            else:
                self.unspent_inputs[public_key] = new_inputs
    
    def validate_inputs(self, tx):
        transaction = Transaction.from_json(tx)
        sender = transaction.sender
        required_amount = Input.from_json(transaction.recipients[0]).amount
        selected_inputs = []

        if sender not in self.unspent_inputs:
            return []

        total = 0
        for input_obj in self.unspent_inputs[sender]:
            selected_inputs.append(input_obj)
            total += Input.from_json(input_obj).amount
            if total >= required_amount:
                return [selected_inputs, Input(None, Input.from_json(input_obj).address, total - required_amount).to_json()]

        return []

    def get_balance(self, address):
        total = 0
        for input_obj in self.unspent_inputs[address]:
            total += Input.from_json(input_obj).amount
        return total
            
    def change_owner(self, owner):
        """Assign owner of the miner"""
        with open(f"{KEYS}{owner}_pub.pem", "rb") as file:
            data = file.read()
            self.address = get_pub_address(ECC.import_key(data).export_key(format='raw'))

    def create_genesis_block(self):
        """Creates genesis block"""
        coinbase_transaction = Transaction("Coinbase", self.address, REWARD)
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": [coinbase_transaction.to_json()],
            "previous_hash": "0" * 64,
            "nonce": 0,
        }
        genesis_block["hash"] = DIFFICULTY * '0' + "ab589a2161962fc11a616b271098b4fee6653dbed584d7ced30c76efe4c7bd61"[DIFFICULTY:]
        print("Genesis block created:", genesis_block)
        return genesis_block

    def add_transaction(self, transaction, pub_key):
        """Add a transaction to the pool."""
        tx = Transaction.from_json(transaction)
        key_dict = json.loads(pub_key)
        print(key_dict)
        pkey = ECC.import_key(base64.b64decode(key_dict["key"]))
        if tx.verify_signature(pkey):
            self.transaction_pool.append(tx.to_json())

    def create_block(self):
        """Create a block and mine it."""
        previous_hash = self.blockchain[-1]['hash'] if self.blockchain else '0' * 64
        coinbase_transaction = Transaction("Coinbase", self.address, REWARD)
        self.transaction_pool.insert(0, coinbase_transaction.to_json())
        block = {
            'index': len(self.blockchain),
            'timestamp': time.time(),
            'transactions': self.transaction_pool,
            'previous_hash': previous_hash,
            'nonce': 0
        }
        self.transaction_pool = []
        block['hash'] = self.mine_block(block)
        return block
    
    def start_mining(self):
        """Start mining in a background thread."""
        future = self.mining_executor.submit(self.create_block)
        future.add_done_callback(self.block_mined_callback)

    def block_mined_callback(self, future):
        """Handle the block once mining is complete."""
        new_block = future.result()
        #self.blockchain.append(new_block)
        print("New Block Mined:", new_block)
        data = {
            "index": new_block['index'],
            "timestamp": new_block['timestamp'],
            "transactions": new_block['transactions'],
            "previous_hash": new_block['previous_hash'],
            "nonce": new_block['nonce'],
            "hash": new_block['hash']
        }
        for node_url in self.nodes.values():
            try:
                requests.get(f"{node_url['url']}/get_blockchain")
            except Exception as e:
                print(f"Error synchronizing with node {node_url}: {e}")
        broadcast_message('add_block', data, self.nodes)
        #self.start_mining()

    def mine_block(self, block):
        """Perform proof-of-work to find a valid hash."""
        #time_start = time.time()
        while True:
            block_str = f"{block['index']}{block['timestamp']}{block['transactions']}{block['previous_hash']}{block['nonce']}"
            block_hash = hashlib.sha256(block_str.encode()).hexdigest()
            if block_hash.startswith('0' * DIFFICULTY):
                #print(time.time() - time_start)
                return block_hash
            block['nonce'] += 1

def serialise_transaction(sender, receiver, amount):
    """Serialise a transaction."""
    return json.dumps({
        'sender': sender,
        'receiver': receiver,
        'amount': amount
    })

def deserialise_transaction(transaction_json):
    """Deserialise a transaction."""
    return json.loads(transaction_json)
