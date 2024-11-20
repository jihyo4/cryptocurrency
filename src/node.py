#!/usr/bin/env python3

import argparse
import hashlib  
import json 
import sys
from time import time 

from flask import Flask, request, jsonify
import requests

from miner import Miner

app = Flask(__name__)
block_chain = []
Nodes = {}
node_name = ''
messages = {}
Connections = {}
miner = Miner(block_chain)
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
    miner.add_transaction(transaction)
    return jsonify({"message": "Transaction added", "transaction": transaction}), 201

@app.post('/nodes')
def post_nodes():
    new_node = request.json
    name = new_node['name']
    if name not in Nodes:
        Nodes[name] = {}
        Nodes[name]['name'] = name
        Nodes[name]['url'] = new_node['url']
    return "\n", 201

@app.get('/nodes')
def get_nodes():
    return Nodes

def connect(url):
    r = requests.get(url+'/nodes')
    nodes = r.json()
    for name in nodes.keys():
        if name != node_name:
           Nodes[name] = {}
           Nodes[name]['name'] = name
           Nodes[name]['url'] = nodes[name]['url']
           requests.post(nodes[name]['url']+'/nodes', json=Nodes[node_name])


@app.post('/connections')
def post_connections():
    new_connection = request.json
    connection_id = new_connection['connection_id']
    node_url = new_connection['node_url']

    if connection_id not in Connections:
        Connections[connection_id] = node_url
        return f"Connection {connection_id} registered with node {node_url}", 201
    else:
        return f"Connection {connection_id} already exists.", 400

@app.get('/connections')
def get_connections():
    return Connections


@app.route('/connection/<connection_id>/message', methods=['POST'])
def send_message(connection_id):
    json = request.get_json()
    if json and 'message' in json:
        recipient_node_url = Connections.get(connection_id)
        if recipient_node_url:
            response = requests.post(f"{recipient_node_url}/message/{connection_id}", json={'message': json['message']})
            if response.status_code == 200:
                return "Message sent successfully.", 200
            else:
                return "Failed to send message.", 500
        else:
            return "Recipient not found.", 404
    else:
        return "Invalid message format.", 400


@app.route('/message/<connection_id>', methods=['POST'])
def receive_message(connection_id):
    json = request.get_json()
    if json and 'message' in json:
        messages[connection_id] = json['message']
        return f"Message for {connection_id} received.", 200
    else:
        return "Invalid message format.", 400
    

@app.get('/<connection_id>/message')
def get_message(connection_id):
    if connection_id in messages:
        return messages[connection_id]
    else:
        return "No messages for connection", 404


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

    if args.init:
        print("Starting node "+node_name+" on port "+node_name)
        if args.miner:
            miner.start_mining()
        app.run(host='127.0.0.1', port=node_name)
    elif args.join:
        print("Starting node "+node_name+" on port "+node_name)
        if args.miner:
            miner.start_mining()
        connect('http://127.0.0.1:'+str(args.join))
        app.run(host='127.0.0.1', port=node_name)
    else:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(app, miner))