import base64
import hashlib
import json
import requests
import time

from Crypto.Hash import SHA512
from Crypto.Signature import DSS



class Transaction:
    def __init__(self, sender, recipients, amount, transaction_id=None, signature=None, sender_input=[], timestamp=time.time()):
        """
        Initialize a transaction object.
        """
        self.transaction_id = transaction_id
        self.timestamp = timestamp
        self.sender = sender
        self.sender_input = []
        for input in sender_input:
            self.sender_input.append(input)
        if type(recipients) == str:
            self.recipients = [Input(recipients, amount).to_json()]
        else:
            self.recipients = recipients
        self.signature = signature
        if not self.transaction_id:
            self.compute_hash()

    def get_inputs(self):
        transaction = self.to_json()
        r = requests.post("http://127.0.0.1:3001/get_inputs", json=transaction)
        if r.status_code == 201:
            self.sender_input = r.json()["inputs"]
            self.recipients.append(r.json()["recipients"])
        else:
            self.sender_input = []

    def verify_signature(self, pub_key):
        deserialized_hash = SHA512.new()
        deserialized_hash.update(bytes.fromhex(self.transaction_id))
        verifier = DSS.new(pub_key, 'fips-186-3')
        try:
            verifier.verify(deserialized_hash, self.signature)
            return True
        except ValueError:
            return False

    def compute_hash(self):
        """
        Compute the hash of the transaction.
        """
        tx_data = f"{self.timestamp}{self.sender}:{self.sender_input}:{self.recipients}"
        self.transaction_id = SHA512.new(tx_data.encode()).hexdigest()

    def sign_transaction(self, private_key):
        """
        Sign the transaction with a private key.
        """
        self.compute_hash()
        signer = DSS.new(private_key, 'fips-186-3')
        deserialized_hash = SHA512.new()
        deserialized_hash.update(bytes.fromhex(self.transaction_id))
        self.signature = signer.sign(deserialized_hash)

    def to_json(self):
        """
        Serialize the transaction to a dictionary format.
        """
        return json.dumps({
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "sender_inputs": self.sender_input,
            "signature": base64.b64encode(self.signature).decode() if self.signature else None,
            "recipients": self.recipients,
        })

    @classmethod
    def from_json(cls, json_str):
        """
        Deserialize the JSON string to a Transaction object.
        """
        data = json.loads(json_str)
        return cls(
            transaction_id=data["transaction_id"],
            sender=data["sender"],
            sender_input=data["sender_inputs"],
            recipients=data["recipients"],
            signature=base64.b64decode(data["signature"]) if data["signature"] else None,
            amount=None,
            timestamp=data["timestamp"]
        )
    

class Input:
    def __init__(self, address, amount, id=hashlib.sha1().update(str(time.time()).encode("utf-8"))):
        """
        Input of a transaction.
        """
        self.id = id
        self.address = address
        self.amount = amount

    def to_json(self):
        """
        Serialize the input to json.
        """
        return json.dumps({
            "id": self.id,
            "address": self.address,
            "amount": self.amount,
        })
    
    @classmethod
    def from_json(cls, json_str):
        """
        Deserialize the JSON string to an Input object.
        """
        data = json.loads(json_str)
        return cls(
            id=data["id"],
            address=data["address"],
            amount=data["amount"],
        )
