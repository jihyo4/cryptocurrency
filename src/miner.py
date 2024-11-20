import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor

class Miner:
    def __init__(self, blockchain):
        self.transaction_pool = []
        self.blockchain = blockchain
        self.difficulty = 5  # Number of leading zeros required in the hash
        self.mining_executor = ThreadPoolExecutor(max_workers=1)

    def add_transaction(self, transaction):
        """Add a transaction to the pool."""
        self.transaction_pool.append(transaction)

    def create_block(self):
        """Create a block and mine it."""
        previous_hash = self.blockchain[-1]['hash'] if self.blockchain else '0' * 64
        block = {
            'index': len(self.blockchain) + 1,
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
        self.blockchain.append(new_block)
        #print("New Block Mined:", new_block)
        self.start_mining()

    def mine_block(self, block):
        """Perform proof-of-work to find a valid hash."""
        #time_start = time.time()
        while True:
            block_str = f"{block['index']}{block['timestamp']}{block['transactions']}{block['previous_hash']}{block['nonce']}"
            block_hash = hashlib.sha256(block_str.encode()).hexdigest()
            if block_hash.startswith('0' * self.difficulty):
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