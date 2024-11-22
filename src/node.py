#!/usr/bin/env python3

import argparse
import hashlib  
import json 
import sys
from time import time 

from flask import Flask, request, jsonify
import requests

from miner import Miner
from utils import broadcast_message

app = Flask(__name__)
block_chain = []
Nodes = {}
node_name = ''
messages = {}
miner = Miner(block_chain, Nodes)
@app.route('/')
def index() -> str:  
    return "The node is active.\n"

@app.get('/get_blockchain')
def getBlocks() -> str:  
    return jsonify(block_chain), 200

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """HTTP endpoint to add a transaction to the miner."""
    transaction = request.json

    # Sprawdź poprawność danych wejściowych
    if not transaction or "sender" not in transaction or "receiver" not in transaction or "amount" not in transaction:
        return jsonify({"error": "Invalid transaction format"}), 400

    miner.add_transaction(transaction)

    # Wymuś utworzenie bloku po dodaniu transakcji
    new_block = miner.create_block()
    block_chain.append(new_block)

    return jsonify({"message": "Transaction added and block created", "block": new_block}), 201

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
    r = requests.get(url + '/get_blockchain')
    blockchain = r.json()
    if not block_chain and blockchain:
        block_chain.extend(blockchain)  # Synchronizacja blockchainu
    elif not block_chain:
        block_chain.append(miner.create_genesis_block())
    
    r = requests.get(url + '/nodes')
    nodes = r.json()
    for name, info in nodes.items():
        if name != node_name:
            Nodes[name] = info
            requests.post(info['url'] + '/nodes', json=Nodes[node_name])


    
    
@app.route('/get_messages', methods=['GET'])
def get_all_messages():
    """Get all received messages."""
    return jsonify(messages), 200

@app.route('/broadcast_transaction', methods=['POST'])
def broadcast_transaction():
    transaction = request.json

    # Dodaj transakcję do lokalnej puli
    miner.add_transaction(transaction)

    # Wymuś utworzenie nowego bloku
    new_block = miner.create_block()
    block_chain.append(new_block)

    # Rozsyłaj nowy blok do innych węzłów
    broadcast_message('add_block', new_block, Nodes)

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

    # Synchronizacja blockchaina (opcjonalne)
    if len(block_chain) < block["index"]:
        print("Synchronizing blockchain...")
        synchronize_blockchain()

    # Walidacja bloku
    if validate_block(block):
        block_chain.append(block)
        print("Block added to chain.")

        # Rozgłoś do innych węzłów
        broadcast_message('add_block', block, Nodes)

        return jsonify({"message": "Block added"}), 200

    print("Block validation failed.")
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

    # Sprawdź poprawność poprzedniego hash'a, indeksu i hashu bloku
    return (
        block["previous_hash"] == last_block["hash"]
        and block["index"] == last_block["index"] + 1
        and block["hash"].startswith("0000")  # Sprawdzenie trudności (opcjonalne)
    )





def main(app: Flask, miner) -> int:
    global node_name
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='Initialise the first node.', action='store_true')
    parser.add_argument('--join', help='Create a new node. Please specify the port of the node it should be connected to')
    parser.add_argument('--port', help='Please specify the port number of the node', type=int)
    parser.add_argument('--miner', help='If used, the created node will also serve as a miner', action='store_true')
    args = parser.parse_args()

    node_name = str(args.port)

    Nodes[node_name] = {}
    Nodes[node_name]['name'] = node_name
    Nodes[node_name]['url'] = "http://127.0.0.1:"+node_name
    Nodes[node_name]['join'] = "init"

    if args.init and not block_chain:
        block_chain.append(miner.create_genesis_block())
        print("Starting node "+node_name+" on port "+node_name)
        if args.miner:
            miner.start_mining()
        app.run(host='127.0.0.1', port=node_name, threaded=True, use_reloader=False)
    elif args.join:
        print("Starting node "+node_name+" on port "+node_name)
        Nodes[node_name]['join'] = str(args.join)
        if args.miner:
            miner.start_mining()
        connect('http://127.0.0.1:'+str(args.join))
        app.run(host='127.0.0.1', port=node_name, threaded=True, use_reloader=False)
    else:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(app, miner))