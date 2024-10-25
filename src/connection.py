import requests

STATUS_OK = 200

class Connection:
    def __init__(self, connection_id: str, node_url: str):
        self.connection_id = connection_id
        self.node_url = node_url

        self.register_user()

    def register_user(self):
        """Register the user with the node by calling the /users endpoint."""
        url = f"{self.node_url}/connections"
        data = {
            'connection_id': self.connection_id,
            'node_url': self.node_url
        }
        response = requests.post(url, json=data)
        if response.status_code == STATUS_OK or response.status_code == 201:
            print(f"Connection {self.connection_id} registered with node {self.node_url}")
        else:
            print(f"Failed to register connection {self.connection_id}. Status: {response.status_code}, {response.text}")

    def send_message(self, target_connection_id, target_connection_node, message: str):
        get_connections = requests.get(f"{target_connection_node}/connections")
        connection_data = get_connections.json()

        recipient_node_url = connection_data.get(target_connection_id)

        if recipient_node_url:
            url = f"{recipient_node_url}/connection/{target_connection_id}/message"
            print(url)
            data = {'message': message}
            response = requests.post(url, json=data)
            if response.status_code != STATUS_OK:
                print(f"Failed to send message to {target_connection_id} at {recipient_node_url}")
                print(f"Response status code: {response.status_code}")
                print(f"Response text: {response.text}")
                raise Exception(f"FAIL({response.status_code}): {response.text}")
            print(f"Message sent successfully to {target_connection_id} on {recipient_node_url}.")
        else:
            print(f"Recipient {target_connection_id} not found in Nodes.")
            raise Exception(f"Recipient {target_connection_id} not found.")


    def get_messages(self):
        """Retrieve plaintext messages sent to this user from the node."""
        url = f"{self.node_url}/message/{self.connection_id}"
        response = requests.get(url)
        if response.status_code != STATUS_OK:
            raise Exception(f"FAIL({response.status_code}): {response.text}")
        return response.text