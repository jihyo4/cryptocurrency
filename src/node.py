#!/usr/bin/env python3

import argparse
import hashlib  
import json 
import sys
from time import time 

from flask import Flask, request

class Block():
    def __init__(self, ind: int, prev_hash: str, data: str) -> None:
        self._index = ind
        self._prev_hash = prev_hash
        self._timestamp = time()
        self._data = data
        self.block_hash = self.hash()

    def hash(self) -> str:
        return (hashlib.sha256((str(self._index) + self._prev_hash + str(self._timestamp) + self._data).encode())).hexdigest()
    
    def toJson(self) -> str:
        return json.dumps(self.__dict__, sort_keys = True)


class Block_chain():  
    def __init__(self) -> None:  
        self.chain = [Block(0, '816534932c2b7154836da6afc367695e6337db8a921823784c14378abed4f7d7', 'GenesisBlock').toJson()]  
        self.pendingTransactions = []
  
    def addBlock(self, block: str) -> None:  
        #validate
        self.chain.append(block)  


app = Flask(__name__)
block_chain = Block_chain()

@app.route('/')
def index() -> str:  
    return "The node is active.\n"

@app.get('/blocks')
def getBlocks() -> str:  
    return f"{block_chain.chain}\n"

def main(app: Flask) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='Initialise the first node.', action='store_true')
    parser.add_argument('--join', help='Create a new node. Please specify the port of the node it should be connected to')
    args = parser.parse_args()
    
    if args.init:
        app.run(host='127.0.0.1', port=3001)
    elif args.join:
        pass
    else:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(app))