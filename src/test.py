#!/usr/bin/env python3
import subprocess
import time

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

    cmd = [
        "./wallet.py",
        "-t",
        "--name", "angel",
        "-p", "Pass12..",
        "--recipient", "00c96bf380732a3218aba9cd5076c7cdd8d39c8fdc98768802",
        "-nd", "3001",
        "-a", "30"
    ]

    def run_wallet_transaction(cmd):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("Command Output:")
            print(result.stdout)
        
        except subprocess.CalledProcessError as e:
            print("Error:")
            print(e.stderr)
    
    # Start nodes
    processes = []
    for i, command in enumerate(commands):
        print(f"Starting node {i + 1}: {command}")
        processes.append(start_node(command))
        time.sleep(2)

    print("All nodes started successfully. Press Ctrl+C to terminate.")

    try:
        while True:
            time.sleep(10)
            run_wallet_transaction(cmd)
    except KeyboardInterrupt:
        print("\nShutting down nodes...")
        for process in processes:
            process.terminate()
        print("All nodes terminated.")


if __name__ == "__main__":
    main()