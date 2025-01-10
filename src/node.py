#!/usr/bin/env python3

import argparse
import hashlib  
import json
import sys

from flask import Flask, request, jsonify
import requests

from miner import Miner, deserialise_transaction, DIFFICULTY
from utils import broadcast_message

app = Flask(__name__)
block_chain = []
Nodes = {}
node_name = ''
messages = {}
miner = None
orphan_blocks = []
@app.route('/')
def index() -> str:  
    return "The node is active.\n"

@app.get('/get_blockchain')
def getBlocks() -> str:  
    return jsonify(block_chain), 200

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    global miner
    """HTTP endpoint to add a transaction to the miner."""
    transaction, pub_key = request.json
    if not transaction or "sender" not in transaction or "recipients" not in transaction:
        return jsonify({"error": transaction}), 400
        # return jsonify({"error": "Invalid transaction format"}), 400

    miner.add_transaction(transaction, pub_key)

    return jsonify({"message": "Transaction added.", "transaction": transaction}), 201

@app.route('/get_inputs', methods=['POST'])
def get_inputs():
    global miner
    transaction = request.json

    if not transaction or "sender" not in transaction or "recipients" not in transaction:
        # return jsonify({"error": transaction}), 400
        return jsonify({"error": "Invalid transaction format"}), 400

    input_list = miner.validate_inputs(transaction)
    
    return jsonify({"message": "Returned inputs.", "inputs": input_list[0], "recipients": input_list[1]}), 201

@app.route('/get_balance', methods=['POST'])
def get_balance():
    global miner
    address = request.json

    balance = miner.get_balance(address)
    
    return jsonify({"message": "Returned balance.", "balance": balance}), 201

@app.post('/nodes')
def post_nodes():
    new_node = request.json
    name = new_node['name']
    # print(new_node[name]['join'])
    if name not in Nodes:
        Nodes[name] = {}
        Nodes[name]['name'] = name
        Nodes[name]['url'] = new_node['url']
        Nodes[name]['join'] = new_node['join']
    return "\n", 201

@app.get('/nodes')
def get_nodes():
    return Nodes

def connect(url):
    try:
        r = requests.get(f"{url}/get_blockchain")
        if r.status_code == 200:
            remote_blockchain = r.json()
            if remote_blockchain:
                print(f"Received blockchain from node {url}. Length: {len(remote_blockchain)}")
                if len(remote_blockchain) > len(block_chain):
                    if validate_chain(remote_blockchain):
                        if validate_chain(block_chain):
                            idx = find_common_index(block_chain, remote_blockchain)
                            if idx == len(block_chain)-1: 
                                block_chain.clear()
                                block_chain.extend(remote_blockchain)
                            if idx is not None:
                                orphan_blocks.extend(block_chain[idx:])
                                block_chain.clear()
                                block_chain.extend(remote_blockchain)
                        else:
                            print(f"You are trying to synchronize an invalid blockchain")
                        print(f"Blockchain synchronized with longer chain from node {url}.")
                    else:
                        print(f"Received blockchain from {url} is invalid. Ignoring.")
                else:
                    print(f"Current blockchain is longer or equal. No synchronization needed.")
            else:
                print(f"Node {url} has no blockchain. Skipping sync.")

        r = requests.get(f"{url}/nodes")
        if r.status_code == 200:
            nodes = r.json()
            for name, info in nodes.items():
                if name != node_name:
                    Nodes[name] = info
                    requests.post(info['url'] + '/nodes', json=Nodes[node_name])

        if len(block_chain) >= len(remote_blockchain):
            print("Broadcasting longer blockchain to the network.")
            data = {"blockchain": block_chain}
            broadcast_message("sync_blockchain", data, Nodes)

    except requests.exceptions.RequestException as e:
        print(f"Error synchronizing with {url}: {e}")

@app.route('/get_unspent_inputs', methods=['GET'])
def get_unspent_inputs():
    """Get all unspent inputs."""
    return jsonify(miner.unspent_inputs), 200  
    
@app.route('/get_messages', methods=['GET'])
def get_all_messages():
    """Get all received messages."""
    return jsonify(messages), 200

# Transakcja nie musi być broadcastowana, potencjalnie do wywalenia
@app.route('/broadcast_transaction', methods=['POST'])
def broadcast_transaction():
    global miner
    transaction = request.json

    miner.add_transaction(transaction)

    # new_block = miner.create_block()
    # block_chain.append(new_block)

    # broadcast_message('add_block', new_block, Nodes)

    return jsonify({"message": "Transaction broadcasted and block created"}), 200


@app.route('/broadcast_block', methods=['POST'])
def broadcast_block():
    block = request.json
    broadcast_message('add_block', block, Nodes)  
    return jsonify({"message": "Block broadcasted"}), 200

@app.route('/add_block', methods=['POST'])
def add_block():
    block = request.json
    print(f"Received block: {block}")
    if block["previous_hash"] == block_chain[-1]["hash"]:
        if validate_block(block):
            block_chain.append(block)
            print("Block validated. Adding to chain.")
            synchronize_blockchain()
            process_orphan_blocks()
            if miner.mining:
                miner.start_mining()
            return jsonify({"message": "Block added"}), 200
        else:
            return jsonify({"error": "Invalid block"}), 400
    
    print("Block does not match current chain. Storing as orphan.")
    orphan_blocks.append(block)
    return jsonify({"message": "Orphan block stored"}), 202


@app.route('/get_orphan_blocks', methods=['GET'])
def get_orphan_blocks():
    return jsonify(orphan_blocks), 200

@app.route('/sync_blockchain', methods=['POST'])
def sync_blockchain():
    data = request.json
    remote_blockchain = data.get("blockchain", [])

    if len(remote_blockchain) >= len(block_chain):
        print(f"Received a blockchain from another node. Length: {len(remote_blockchain)}")
        if validate_chain(remote_blockchain):
            idx = find_common_index(block_chain, remote_blockchain)
            if len(remote_blockchain) == len(block_chain) and idx == len(block_chain)-1:
                block_chain.clear()
                block_chain.extend(remote_blockchain)
            elif idx == len(block_chain)-1 and len(remote_blockchain) > len(block_chain): 
                block_chain.clear()
                block_chain.extend(remote_blockchain)
            elif idx < len(block_chain)-1 and len(remote_blockchain) > len(block_chain):
                orphan_blocks.extend(block_chain[max(idx,1):])
                block_chain.clear()
                block_chain.extend(remote_blockchain)
            elif idx < len(block_chain)-1 and len(remote_blockchain) == len(block_chain):
                orphan_blocks.extend(remote_blockchain[max(idx,1):])
            print("Blockchain synchronized with the received chain.")
        else:
            print("Received blockchain is invalid. Ignoring.")
    else:
        print("Received blockchain is shorter or equal. No synchronization needed.")
    return jsonify({"message": "Blockchain synchronization complete."}), 200




def synchronize_blockchain():
    """Synchronizes blockchain with other nodes"""
    global block_chain, orphan_blocks
    longest_chain = block_chain
    for node_name, node_info in Nodes.items():
        try:
            response = requests.get(f"{node_info['url']}/get_blockchain")
            if response.status_code == 200:
                remote_blockchain = response.json()
                if not has_common_block(block_chain, remote_blockchain):
                    print(f"No common block with {node_name}. Chain rejected.")
                    continue

                if len(remote_blockchain) > len(longest_chain) and validate_chain(remote_blockchain):
                    print(f"Synchronizing with {node_name}. Found a longer chain.")
                    orphan_blocks.extend(find_orphan_blocks(block_chain, remote_blockchain))
                    longest_chain = remote_blockchain
        except requests.exceptions.RequestException as e:
            print(f"Error synchronizing with {node_name}: {e}")

    if longest_chain != block_chain:
        print("Replacing current chain with the longest chain.")
        block_chain = longest_chain
        print(f"Updated chain. Orphan blocks: {len(orphan_blocks)}")


def has_common_block(local_chain, external_chain):
    """Check whether the genesis is the same"""
    if not local_chain or not external_chain:
        return False

    local_genesis = local_chain[0]
    external_genesis = external_chain[0]

    return (
        local_genesis["index"] == external_genesis["index"]
        and local_genesis["hash"] == external_genesis["hash"]
        and local_genesis["transactions"] == external_genesis["transactions"]
        and local_genesis["previous_hash"] == external_genesis["previous_hash"]
    )


def find_common_index(local_chain, remote_chain):
    common_index = None
    for i in range(min(len(local_chain), len(remote_chain))):
        if local_chain[i]["hash"] == remote_chain[i]["hash"]:
            common_index = i
        else:
            break
    return common_index





def validate_block(block):
    """Waliduje otrzymany blok."""
    if not block_chain:
        # Genesis block
        return block["previous_hash"] == "0" * 64

    last_block = block_chain[-1]
    return (
        block["previous_hash"] == last_block["hash"]
        and block["index"] == last_block["index"] + 1
        and block["hash"].startswith(DIFFICULTY * "0")
        and deserialise_transaction(block["transactions"][0])["sender"] == "Coinbase"
    )

def validate_chain(chain):
    """Validates the whole chain."""
    if not chain:
        return False

    genesis_block = chain[0]
    if genesis_block["previous_hash"] != "0" * 64:
        print("Invalid genesis block: Incorrect previous hash.")
        return False

    
    genesis_block_hash = DIFFICULTY * '0' + "ab589a2161962fc11a616b271098b4fee6653dbed584d7ced30c76efe4c7bd61"[DIFFICULTY:]
    if genesis_block_hash != genesis_block["hash"] or not genesis_block_hash.startswith("0" * DIFFICULTY):
        print("Invalid genesis block: Hash does not match or difficulty not met.")
        return False

    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i - 1]

        if current_block["previous_hash"] != previous_block["hash"]:
            print(f"Invalid block at index {i}: Previous hash does not match.")
            return False

        block_str = f"{current_block['index']}{current_block['timestamp']}{current_block['transactions']}{current_block['previous_hash']}{current_block['nonce']}"
        block_hash = hashlib.sha256(block_str.encode()).hexdigest()
        if block_hash != current_block["hash"] or not block_hash.startswith("0" * DIFFICULTY):
            print(f"Invalid block at index {i}: Hash does not match or difficulty not met.")
            return False

    return True


def process_orphan_blocks():
    """Tries to add orphan blocks to blockchain."""
    global orphan_blocks
    new_orphan_blocks = []
    for block in orphan_blocks:
        if block["previous_hash"] == block_chain[-1]["hash"]:
            if validate_block(block):
                block_chain.append(block)
                print("Orphan block added to blockchain.")
            else:
                print("Invalid orphan block.")
                new_orphan_blocks.append(block)
        else:
            new_orphan_blocks.append(block)
    orphan_blocks = new_orphan_blocks

def find_orphan_blocks(old_chain, new_chain):
    """Returns orphaned blocks."""
    new_chain_hashes = {block["hash"] for block in new_chain} 
    orphaned_blocks = [
        block for block in old_chain if block["hash"] not in new_chain_hashes
    ]
    return orphaned_blocks




def main(app: Flask) -> int:
    global node_name
    global miner
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='Initialise the first node.', action='store_true')
    parser.add_argument('--join', help='Create a new node. Please specify the port of the node it should be connected to')
    parser.add_argument('--port', help='Please specify the port number of the node', type=int)
    parser.add_argument('--miner', help='If used, the created node will also serve as a miner and the user with the given name will be the owner of the miner')
    parser.add_argument('--malicious', help='Simulate a malicious fork.', type=str)
    parser.add_argument('--predefined-blocks', help='Path to a file containing predefined blocks.', type=str)

    args = parser.parse_args()

    node_name = str(args.port)

    Nodes[node_name] = {}
    Nodes[node_name]['name'] = node_name
    Nodes[node_name]['url'] = "http://127.0.0.1:"+node_name
    Nodes[node_name]['join'] = "init"

    if args.predefined_blocks:
        try:
            with open(args.predefined_blocks, 'r') as file:
                predefined_blocks = json.load(file)
                if not block_chain:
                    block_chain.extend(predefined_blocks)
                    print(f"Predefined blockchain loaded with {len(predefined_blocks)} blocks from {args.predefined_blocks}.")
                else:
                    print(f'Blockchain: {block_chain}')
                    print("Cannot load predefined blocks: Blockchain already initialized.")
        except FileNotFoundError:
            print(f"Error: File {args.predefined_blocks} not found.")
        except json.JSONDecodeError as e:
            print(f"Error loading predefined blocks: {e}")
    
    if args.malicious:
        try:
            with open(args.malicious, 'r') as file:
                predefined_blocks = json.load(file)
                if not block_chain:
                    block_chain.extend(predefined_blocks)
                    print(f"Predefined blockchain loaded with {len(predefined_blocks)} blocks from {args.malicious}.")
                else:
                    print(f'Blockchain: {block_chain}')
                    print("Cannot load predefined blocks: Blockchain already initialized.")
        except FileNotFoundError:
            print(f"Error: File {args.malicious} not found.")
        except json.JSONDecodeError as e:
            print(f"Error loading predefined blocks: {e}")

    if args.init:   
        miner = Miner(block_chain, Nodes, args.miner) 
        if not block_chain:
            block_chain.append(miner.create_genesis_block())
            print(f"Node {node_name} initialized with Genesis Block.")
        if args.miner:
            miner.mining = True
            miner.start_mining()
        app.run(host='127.0.0.1', port=node_name, threaded=True, use_reloader=False)
        return 0 

    elif args.join:
        Nodes[node_name]['join'] = str(args.join)
        print(f"Node {node_name} joining node {args.join}.")
        connect(f"http://127.0.0.1:{args.join}")
        miner = Miner(block_chain, Nodes, args.miner)
        if args.miner:
            miner.mining = True
            miner.start_mining()
        app.run(host='127.0.0.1', port=node_name, threaded=True, use_reloader=False)
        return 0  
    else:
        print("No valid arguments provided. Exiting.")
        return 1

if __name__ == '__main__':
    sys.exit(main(app))