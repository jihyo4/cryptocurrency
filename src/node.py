#!/usr/bin/env python3

import argparse
import hashlib  
import json 
import sys
from time import time 

from flask import Flask, request, jsonify
import requests

from miner import Miner, deserialise_transaction
from utils import broadcast_message

app = Flask(__name__)
block_chain = []
Nodes = {}
node_name = ''
messages = {}
miner = None
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
    transaction = request.json

    if not transaction or "sender" not in transaction or "receiver" not in transaction or "amount" not in transaction:
        return jsonify({"error": "Invalid transaction format"}), 400

    miner.add_transaction(transaction)

    return jsonify({"message": "Transaction added.", "transaction": transaction}), 201

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
            blockchain = r.json()
            if blockchain:  
                block_chain.clear()
                block_chain.extend(blockchain)
                print(f"Blockchain synchronized with node {url}.")
            else:
                print(f"Node {url} has no blockchain. Skipping sync.")

        r = requests.get(f"{url}/nodes")
        nodes = r.json()
        for name, info in nodes.items():
            if name != node_name:
                Nodes[name] = info
                requests.post(info['url'] + '/nodes', json=Nodes[node_name])

    except requests.exceptions.RequestException as e:
        print(f"Error synchronizing with {url}: {e}")




    
    
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

    if len(block_chain) < block["index"]:
        print("Synchronizing blockchain...")
        synchronize_blockchain()

    if validate_block(block):
        print("Block validated. Adding to chain.")
        block_chain.append(block)
        if miner.mining:
            miner.start_mining()
        return jsonify({"message": "Block added"}), 200

    print("Block validation failed. Ignoring block.")
    return jsonify({"error": "Invalid block"}), 400





def synchronize_blockchain():
    """Synchronizuje blockchain z innymi węzłami."""
    for node_name, node_info in Nodes.items():
        try:
            response = requests.get(f"{node_info['url']}/get_blockchain")
            if response.status_code == 200:
                remote_blockchain = response.json()
                if len(remote_blockchain) > len(block_chain):
                    print(f"Blockchain synchronized with {node_name}.")
                    block_chain.clear()
                    block_chain.extend(remote_blockchain)
        except requests.exceptions.RequestException as e:
            print(f"Error synchronizing with {node_name}: {e}")




def validate_block(block):
    """Waliduje otrzymany blok."""
    if not block_chain:
        # Genesis block
        return block["previous_hash"] == "0" * 64

    last_block = block_chain[-1]
    return (
        block["previous_hash"] == last_block["hash"]
        and block["index"] == last_block["index"] + 1
        and block["hash"].startswith(miner.difficulty * "0")
        and deserialise_transaction(block["transactions"][0])["sender"] == "Coinbase"
    )







def main(app: Flask) -> int:
    global node_name
    global miner
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='Initialise the first node.', action='store_true')
    parser.add_argument('--join', help='Create a new node. Please specify the port of the node it should be connected to')
    parser.add_argument('--port', help='Please specify the port number of the node', type=int)
    parser.add_argument('--miner', help='If used, the created node will also serve as a miner and the user with the given name will be the owner of the miner')
    args = parser.parse_args()

    node_name = str(args.port)

    Nodes[node_name] = {}
    Nodes[node_name]['name'] = node_name
    Nodes[node_name]['url'] = "http://127.0.0.1:"+node_name
    Nodes[node_name]['join'] = "init"

    miner = Miner(block_chain, Nodes, args.miner)

    if args.init:    
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