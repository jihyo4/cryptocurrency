import requests

def broadcast_message(endpoint, data, nodes, timeout=5):
    """Broadcast a message to all nodes."""
    for node_name, node_info in nodes.items():
        try:
            node_url = node_info['url']
            print(f"Broadcasting to {node_name} at {node_url}/{endpoint}")
            response = requests.post(f"{node_url}/{endpoint}", json=data, timeout=timeout)
            if response.status_code == 200:
                print(f"Successfully broadcasted to {node_name}")
            else:
                print(f"Failed to broadcast to {node_name}. Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error broadcasting to {node_name}: {e}")

