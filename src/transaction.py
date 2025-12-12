"""
Transaction module for blockchain system.
Handles transaction creation, validation, and signing.
"""

import hashlib
import hmac
import json
from typing import Optional, Dict, Any


class Transaction:
    """Represents a transaction in the blockchain."""

    def __init__(
        self,
        sender: str,
        receiver: str,
        amount: float,
        fee: float = 0.0,
        nonce: int = 0,
        signature: Optional[str] = None,
        tx_hash: Optional[str] = None,
    ):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.nonce = nonce
        self.signature = signature
        self._hash = tx_hash

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of transaction data."""
        tx_data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "fee": self.fee,
            "nonce": self.nonce,
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    @property
    def hash(self) -> str:
        """Get transaction hash (lazy computation)."""
        if self._hash is None:
            self._hash = self.compute_hash()
        return self._hash

    def sign(self, private_key: str) -> None:
        """Sign transaction using HMAC (toy signature)."""
        tx_hash = self.compute_hash()
        self.signature = hmac.new(
            private_key.encode(), tx_hash.encode(), hashlib.sha256
        ).hexdigest()

    def verify_signature(self, public_key: str) -> bool:
        """Verify transaction signature using HMAC."""
        if self.signature is None:
            return False

        tx_hash = self.compute_hash()
        expected_signature = hmac.new(
            public_key.encode(), tx_hash.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(self.signature, expected_signature)

    def is_valid(self, verify_sig: bool = True) -> tuple[bool, str]:
        """
        Validate transaction.
        Returns (is_valid, error_message).
        """
        # Check amount is positive (allow 0 for genesis coinbase)
        if self.amount < 0:
            return False, "Amount cannot be negative"
        if self.amount == 0 and self.sender != "COINBASE":
            return False, "Amount must be positive for non-coinbase transactions"

        # Check fee is non-negative
        if self.fee < 0:
            return False, "Fee cannot be negative"

        # Check sender and receiver are different
        if self.sender == self.receiver:
            return False, "Sender and receiver must be different"

        # Check signature if required
        if verify_sig and self.sender != "COINBASE":
            if not self.signature:
                return False, "Transaction must be signed"
            if not self.verify_signature(self.sender):
                return False, "Invalid signature"

        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "fee": self.fee,
            "nonce": self.nonce,
            "signature": self.signature,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Create transaction from dictionary."""
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            amount=data["amount"],
            fee=data.get("fee", 0.0),
            nonce=data.get("nonce", 0),
            signature=data.get("signature"),
            tx_hash=data.get("hash"),
        )

    @classmethod
    def create_coinbase(cls, miner: str, reward: float) -> "Transaction":
        """Create a coinbase transaction (block reward)."""
        return cls(
            sender="COINBASE",
            receiver=miner,
            amount=reward,
            fee=0.0,
            nonce=0,
            signature="COINBASE",
        )

    def __repr__(self) -> str:
        return f"Transaction({self.sender[:8]}→{self.receiver[:8]}, {self.amount}, fee={self.fee})"
