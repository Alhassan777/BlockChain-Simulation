"""
Tests for the Mempool (transaction pool) module.
"""

import unittest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mempool import Mempool
from src.transaction import Transaction


class TestMempool(unittest.TestCase):
    """Tests for the Mempool class."""

    def create_transaction(
        self, sender: str, receiver: str, amount: float, fee: float, nonce: int
    ) -> Transaction:
        """Helper to create a signed transaction."""
        tx = Transaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            fee=fee,
            nonce=nonce,
        )
        tx.sign(sender)
        return tx

    def test_mempool_creation(self):
        """Test mempool initialization."""
        mempool = Mempool(max_size=100, expiry_seconds=3600)

        self.assertEqual(mempool.size(), 0)
        self.assertEqual(mempool.max_size, 100)
        self.assertEqual(mempool.expiry_seconds, 3600)

    def test_add_transaction(self):
        """Test adding transactions to mempool."""
        mempool = Mempool()
        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)

        added = mempool.add_transaction(tx)

        self.assertTrue(added)
        self.assertEqual(mempool.size(), 1)
        self.assertTrue(mempool.has_transaction(tx.hash))

    def test_add_duplicate_rejected(self):
        """Test that duplicate transactions are rejected."""
        mempool = Mempool()
        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)

        mempool.add_transaction(tx)
        added_again = mempool.add_transaction(tx)

        self.assertFalse(added_again)
        self.assertEqual(mempool.size(), 1)

    def test_remove_transaction(self):
        """Test removing a transaction from mempool."""
        mempool = Mempool()
        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)

        mempool.add_transaction(tx)
        removed = mempool.remove_transaction(tx.hash)

        self.assertTrue(removed)
        self.assertEqual(mempool.size(), 0)
        self.assertFalse(mempool.has_transaction(tx.hash))

    def test_remove_nonexistent(self):
        """Test removing a transaction that doesn't exist."""
        mempool = Mempool()

        removed = mempool.remove_transaction("nonexistent_hash")

        self.assertFalse(removed)

    def test_get_transaction(self):
        """Test retrieving a transaction by hash."""
        mempool = Mempool()
        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)

        mempool.add_transaction(tx)
        retrieved = mempool.get_transaction(tx.hash)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hash, tx.hash)

    def test_get_all_transactions(self):
        """Test getting all transactions."""
        mempool = Mempool()

        for i in range(5):
            tx = self.create_transaction("alice", f"receiver{i}", 10.0, 0.5, i)
            mempool.add_transaction(tx)

        all_txs = mempool.get_all_transactions()

        self.assertEqual(len(all_txs), 5)

    def test_get_top_transactions_by_fee(self):
        """Test getting top transactions sorted by fee."""
        mempool = Mempool()

        # Add transactions with different fees
        tx1 = self.create_transaction("alice", "bob", 10.0, 0.1, 0)  # Low fee
        tx2 = self.create_transaction("alice", "charlie", 10.0, 1.0, 1)  # High fee
        tx3 = self.create_transaction("alice", "dave", 10.0, 0.5, 2)  # Medium fee

        mempool.add_transaction(tx1)
        mempool.add_transaction(tx2)
        mempool.add_transaction(tx3)

        top_txs = mempool.get_top_transactions(max_count=2, sort_by_fee=True)

        self.assertEqual(len(top_txs), 2)
        self.assertEqual(top_txs[0].fee, 1.0)  # Highest fee first
        self.assertEqual(top_txs[1].fee, 0.5)  # Second highest

    def test_max_size_limit(self):
        """Test that mempool respects max size limit."""
        mempool = Mempool(max_size=3)

        # Add transactions up to limit
        for i in range(3):
            tx = self.create_transaction("alice", f"receiver{i}", 10.0, 0.5, i)
            mempool.add_transaction(tx)

        self.assertEqual(mempool.size(), 3)

        # Add transaction with lower fee - should be rejected
        low_fee_tx = self.create_transaction("alice", "receiver99", 10.0, 0.1, 99)
        added = mempool.add_transaction(low_fee_tx)

        self.assertFalse(added)
        self.assertEqual(mempool.size(), 3)

    def test_max_size_replaces_low_fee(self):
        """Test that high-fee tx replaces low-fee tx when full."""
        mempool = Mempool(max_size=3)

        # Add low-fee transactions
        for i in range(3):
            tx = self.create_transaction("alice", f"receiver{i}", 10.0, 0.1, i)
            mempool.add_transaction(tx)

        # Add high-fee transaction
        high_fee_tx = self.create_transaction("alice", "receiver99", 10.0, 1.0, 99)
        added = mempool.add_transaction(high_fee_tx)

        self.assertTrue(added)
        self.assertEqual(mempool.size(), 3)
        self.assertTrue(mempool.has_transaction(high_fee_tx.hash))

    def test_remove_transactions_batch(self):
        """Test removing multiple transactions at once."""
        mempool = Mempool()

        hashes = []
        for i in range(5):
            tx = self.create_transaction("alice", f"receiver{i}", 10.0, 0.5, i)
            mempool.add_transaction(tx)
            hashes.append(tx.hash)

        # Remove first 3
        removed_count = mempool.remove_transactions(hashes[:3])

        self.assertEqual(removed_count, 3)
        self.assertEqual(mempool.size(), 2)

    def test_clear(self):
        """Test clearing the mempool."""
        mempool = Mempool()

        for i in range(5):
            tx = self.create_transaction("alice", f"receiver{i}", 10.0, 0.5, i)
            mempool.add_transaction(tx)

        mempool.clear()

        self.assertEqual(mempool.size(), 0)

    def test_expiry_cleanup(self):
        """Test that expired transactions are cleaned up."""
        mempool = Mempool(expiry_seconds=0.1)  # Very short expiry

        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)
        mempool.add_transaction(tx)

        self.assertEqual(mempool.size(), 1)

        # Wait for expiry
        time.sleep(0.2)

        # Cleanup should remove expired tx
        removed = mempool.cleanup_expired()

        self.assertEqual(removed, 1)
        self.assertEqual(mempool.size(), 0)

    def test_get_stats(self):
        """Test mempool statistics."""
        mempool = Mempool()

        for i in range(3):
            tx = self.create_transaction(
                "alice", f"receiver{i}", 10.0, 0.1 * (i + 1), i
            )
            mempool.add_transaction(tx)

        stats = mempool.get_stats()

        self.assertEqual(stats["size"], 3)
        self.assertAlmostEqual(stats["total_fees"], 0.6, places=2)  # 0.1 + 0.2 + 0.3
        self.assertAlmostEqual(stats["avg_fee"], 0.2, places=2)

    def test_empty_stats(self):
        """Test stats for empty mempool."""
        mempool = Mempool()

        stats = mempool.get_stats()

        self.assertEqual(stats["size"], 0)
        self.assertEqual(stats["total_fees"], 0.0)
        self.assertEqual(stats["avg_fee"], 0.0)

    def test_to_dict(self):
        """Test mempool serialization to dict."""
        mempool = Mempool(max_size=100)

        tx = self.create_transaction("alice", "bob", 10.0, 0.5, 0)
        mempool.add_transaction(tx)

        data = mempool.to_dict()

        self.assertEqual(data["size"], 1)
        self.assertEqual(data["max_size"], 100)
        self.assertEqual(len(data["transactions"]), 1)


class TestMempoolPrioritization(unittest.TestCase):
    """Tests for transaction prioritization in mempool."""

    def create_transaction(
        self, sender: str, receiver: str, amount: float, fee: float, nonce: int
    ) -> Transaction:
        """Helper to create a signed transaction."""
        tx = Transaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            fee=fee,
            nonce=nonce,
        )
        tx.sign(sender)
        return tx

    def test_fee_ordering(self):
        """Test that transactions are ordered by fee correctly."""
        mempool = Mempool()

        # Add in random order
        fees = [0.3, 0.1, 0.5, 0.2, 0.4]
        for i, fee in enumerate(fees):
            tx = self.create_transaction("alice", f"bob{i}", 10.0, fee, i)
            mempool.add_transaction(tx)

        top = mempool.get_top_transactions(max_count=5, sort_by_fee=True)

        # Should be sorted descending by fee
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i].fee, top[i + 1].fee)

    def test_fifo_when_no_sorting(self):
        """Test FIFO order when sorting is disabled."""
        mempool = Mempool()

        for i in range(5):
            tx = self.create_transaction("alice", f"bob{i}", 10.0, 0.5, i)
            mempool.add_transaction(tx)
            time.sleep(0.01)

        # Get without sorting
        txs = mempool.get_top_transactions(max_count=5, sort_by_fee=False)

        self.assertEqual(len(txs), 5)


if __name__ == "__main__":
    unittest.main()
