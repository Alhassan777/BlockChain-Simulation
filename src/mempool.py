"""
Mempool (Memory Pool) module for managing pending transactions.
"""

import time
from typing import List, Dict, Optional, Tuple
from src.transaction import Transaction


class Mempool:
    """Manages pending transactions waiting to be included in blocks."""

    def __init__(self, max_size: int = 1000, expiry_seconds: float = 3600.0):
        """
        Initialize mempool.

        Args:
            max_size: Maximum number of transactions to hold
            expiry_seconds: Time after which transactions expire (default: 1 hour)
        """
        self.transactions: Dict[str, Transaction] = {}  # tx_hash -> Transaction
        self.timestamps: Dict[str, float] = {}  # tx_hash -> timestamp added
        self.max_size = max_size
        self.expiry_seconds = expiry_seconds

    def add_transaction(self, tx: Transaction) -> bool:
        """
        Add a transaction to the mempool.
        Returns True if added, False if already exists or mempool full.
        """
        tx_hash = tx.hash
        if tx_hash in self.transactions:
            return False

        # Check if mempool is full
        if len(self.transactions) >= self.max_size:
            # Try to make room by removing expired transactions
            self.cleanup_expired()

            # If still full, reject low-fee transactions
            if len(self.transactions) >= self.max_size:
                # Only add if fee is higher than lowest fee in mempool
                lowest_fee_tx = min(self.transactions.values(), key=lambda t: t.fee)
                if tx.fee <= lowest_fee_tx.fee:
                    return False  # Reject low-fee transaction
                # Remove lowest fee transaction to make room
                self.remove_transaction(lowest_fee_tx.hash)

        self.transactions[tx_hash] = tx
        self.timestamps[tx_hash] = time.time()
        return True

    def remove_transaction(self, tx_hash: str) -> bool:
        """
        Remove a transaction from the mempool.
        Returns True if removed, False if not found.
        """
        if tx_hash in self.transactions:
            del self.transactions[tx_hash]
            if tx_hash in self.timestamps:
                del self.timestamps[tx_hash]
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Remove expired transactions from the mempool.
        Returns number of transactions removed.
        """
        current_time = time.time()
        expired_hashes = [
            tx_hash
            for tx_hash, timestamp in self.timestamps.items()
            if current_time - timestamp > self.expiry_seconds
        ]

        for tx_hash in expired_hashes:
            self.remove_transaction(tx_hash)

        return len(expired_hashes)

    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by hash."""
        return self.transactions.get(tx_hash)

    def has_transaction(self, tx_hash: str) -> bool:
        """Check if transaction exists in mempool."""
        return tx_hash in self.transactions

    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions in mempool."""
        return list(self.transactions.values())

    def get_top_transactions(
        self, max_count: int, sort_by_fee: bool = True
    ) -> List[Transaction]:
        """
        Get top transactions for inclusion in a block.

        Args:
            max_count: Maximum number of transactions to return
            sort_by_fee: If True, sort by fee (highest first)

        Returns:
            List of transactions
        """
        txs = list(self.transactions.values())

        if sort_by_fee:
            # Sort by fee per transaction (descending)
            txs.sort(key=lambda tx: tx.fee, reverse=True)

        return txs[:max_count]

    def clear(self) -> None:
        """Clear all transactions from mempool."""
        self.transactions.clear()
        self.timestamps.clear()

    def size(self) -> int:
        """Get number of transactions in mempool."""
        return len(self.transactions)

    def remove_transactions(self, tx_hashes: List[str]) -> int:
        """
        Remove multiple transactions from mempool.
        Returns number of transactions removed.
        """
        count = 0
        for tx_hash in tx_hashes:
            if self.remove_transaction(tx_hash):
                count += 1
        return count

    def to_dict(self) -> Dict:
        """Convert mempool to dictionary."""
        return {
            "transactions": [tx.to_dict() for tx in self.transactions.values()],
            "size": len(self.transactions),
            "max_size": self.max_size,
        }

    def get_stats(self) -> Dict:
        """Get mempool statistics."""
        if not self.transactions:
            return {
                "size": 0,
                "max_size": self.max_size,
                "total_fees": 0.0,
                "avg_fee": 0.0,
                "oldest_tx_age": 0.0,
            }

        current_time = time.time()
        fees = [tx.fee for tx in self.transactions.values()]
        ages = [current_time - ts for ts in self.timestamps.values()]

        return {
            "size": len(self.transactions),
            "max_size": self.max_size,
            "total_fees": sum(fees),
            "avg_fee": sum(fees) / len(fees) if fees else 0.0,
            "oldest_tx_age": max(ages) if ages else 0.0,
        }

    def __repr__(self) -> str:
        return f"Mempool(size={len(self.transactions)})"
