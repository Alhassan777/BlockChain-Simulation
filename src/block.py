"""
Block module for blockchain system.
Handles block structure, hashing, and validation.
Includes Merkle tree for efficient transaction verification.
"""

import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from src.transaction import Transaction
from src.merkle import MerkleTree, compute_merkle_root


class Block:
    """Represents a block in the blockchain."""

    def __init__(
        self,
        index: int,
        transactions: List[Transaction],
        previous_hash: str,
        timestamp: Optional[float] = None,
        nonce: int = 0,
        difficulty: int = 2,
        block_hash: Optional[str] = None,
        merkle_root: Optional[str] = None,
    ):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.difficulty = difficulty
        self._hash = block_hash
        self._merkle_root = merkle_root
        self._merkle_tree: Optional[MerkleTree] = None

    @property
    def merkle_root(self) -> str:
        """Get Merkle root of transactions (lazy computation)."""
        if self._merkle_root is None:
            self._merkle_root = compute_merkle_root(self.transactions)
        return self._merkle_root

    @property
    def merkle_tree(self) -> MerkleTree:
        """Get full Merkle tree for transaction proofs."""
        if self._merkle_tree is None:
            self._merkle_tree = MerkleTree(self.transactions)
        return self._merkle_tree

    def get_transaction_proof(self, tx_index: int) -> List[tuple]:
        """
        Get Merkle proof for a transaction.

        Args:
            tx_index: Index of transaction in block

        Returns:
            Merkle proof as list of (hash, position) tuples
        """
        return self.merkle_tree.get_proof(tx_index)

    def verify_transaction_proof(self, tx: Transaction, proof: List[tuple]) -> bool:
        """
        Verify a transaction is in this block using Merkle proof.

        Args:
            tx: Transaction to verify
            proof: Merkle proof from get_transaction_proof()

        Returns:
            True if transaction is verified, False otherwise
        """
        return self.merkle_tree.verify_proof(tx.hash, proof, self.merkle_root)

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of block header (includes Merkle root)."""
        block_data = {
            "index": self.index,
            "merkle_root": self.merkle_root,  # Use Merkle root instead of full tx list
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    @property
    def hash(self) -> str:
        """Get block hash (lazy computation)."""
        if self._hash is None:
            self._hash = self.compute_hash()
        return self._hash

    def is_valid_proof(self) -> bool:
        """Check if block hash meets difficulty requirement."""
        return self.hash.startswith("0" * self.difficulty)

    def mine(self, max_iterations: Optional[int] = None) -> bool:
        """
        Mine block by finding valid nonce.
        Returns True if valid nonce found, False if max_iterations reached.
        """
        iteration = 0
        while not self.is_valid_proof():
            self.nonce += 1
            self._hash = None  # Force recomputation
            iteration += 1

            if max_iterations and iteration >= max_iterations:
                return False

        return True

    def get_total_fees(self) -> float:
        """Calculate total transaction fees in block."""
        return sum(tx.fee for tx in self.transactions if tx.sender != "COINBASE")

    def is_valid(self, verify_transactions: bool = True) -> tuple[bool, str]:
        """
        Validate block.
        Returns (is_valid, error_message).
        """
        # Check proof of work
        if not self.is_valid_proof():
            return False, f"Invalid proof of work (difficulty={self.difficulty})"

        # Check transactions if required
        if verify_transactions:
            # Must have at least one transaction (coinbase)
            if not self.transactions:
                return False, "Block must contain at least one transaction"

            # First transaction should be coinbase
            if self.transactions[0].sender != "COINBASE":
                return False, "First transaction must be coinbase"

            # Verify Merkle root matches transactions
            computed_root = compute_merkle_root(self.transactions)
            if self._merkle_root is not None and self._merkle_root != computed_root:
                return (
                    False,
                    f"Merkle root mismatch: expected {computed_root[:16]}..., got {self._merkle_root[:16]}...",
                )

            # Validate all transactions
            for i, tx in enumerate(self.transactions):
                # Skip signature verification for coinbase
                verify_sig = tx.sender != "COINBASE"
                is_valid, error = tx.is_valid(verify_sig=verify_sig)
                if not is_valid:
                    return False, f"Invalid transaction {i}: {error}"

        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "hash": self.hash,
            "merkle_root": self.merkle_root,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        """Create block from dictionary."""
        transactions = [
            Transaction.from_dict(tx_data) for tx_data in data["transactions"]
        ]
        return cls(
            index=data["index"],
            transactions=transactions,
            previous_hash=data["previous_hash"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            difficulty=data["difficulty"],
            block_hash=data.get("hash"),
            merkle_root=data.get("merkle_root"),
        )

    @classmethod
    def create_genesis_block(cls) -> "Block":
        """Create the first block in the blockchain."""
        coinbase = Transaction.create_coinbase("GENESIS", 0)
        genesis = cls(
            index=0, transactions=[coinbase], previous_hash="0" * 64, difficulty=2
        )
        genesis.mine()
        return genesis

    def __repr__(self) -> str:
        return f"Block(#{self.index}, {len(self.transactions)} txs, hash={self.hash[:8]}...)"
