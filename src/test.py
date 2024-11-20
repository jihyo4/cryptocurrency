#!/usr/bin/env python3
import time
import requests
from miner import Miner, serialise_transaction

if __name__ == "__main__":
    transaction = serialise_transaction("Alice", "Bob", 10)
    response = requests.post("http://127.0.0.1:3001/add_transaction", json=transaction)