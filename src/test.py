#!/usr/bin/env python3
import requests
import subprocess
import time
from miner import Miner, serialise_transaction

def start_node(command):
    """
    Starts a node process with the given command.
    Returns the process object for later management.
    """
    return subprocess.Popen(command, shell=True)


def main():
    # Commands to run nodes
    commands = [
        "./node.py --init --port 3001 --miner angel",  # Miner node
        "./node.py --join 3001 --port 3002",    # Join node 3002 to miner
        "./node.py --join 3001 --port 3003",    # Join node 3003 to miner
        "./node.py --join 3002 --port 3004"     # Join node 3004 to node 3002
    ]

    # Start nodes
    processes = []
    for i, command in enumerate(commands):
        print(f"Starting node {i + 1}: {command}")
        processes.append(start_node(command))
        time.sleep(2)  # Delay to ensure each node initializes properly

    print("All nodes started successfully. Press Ctrl+C to terminate.")

    try:
        # Keep the script running to allow the nodes to operate
        i = 1
        while True:
            time.sleep(15)
            transaction = serialise_transaction("User 0", "Bob", i)
            response = requests.post("http://127.0.0.1:3001/add_transaction", json=transaction)
            i += 1
    except KeyboardInterrupt:
        print("\nShutting down nodes...")
        for process in processes:
            process.terminate()
        print("All nodes terminated.")


if __name__ == "__main__":
    main()