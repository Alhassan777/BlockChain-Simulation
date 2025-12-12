"""
Tests for double-spend prevention and replay attack protection.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.blockchain import Blockchain
from src.block import Block
from src.transaction import Transaction


class TestDoubleSpendPrevention(unittest.TestCase):
    """Tests for double-spend attack prevention."""

    def setUp(self):
        """Set up test fixtures."""
        self.blockchain = Blockchain(difficulty=1)

        # Give alice some coins via mining
        coinbase = Transaction.create_coinbase("alice", 100.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash=self.blockchain.get_latest_block().hash,
            difficulty=1,
        )
        block.mine(max_iterations=10000)
        self.blockchain.add_block(block)

    def test_double_spend_same_nonce(self):
        """Test that spending same coins twice with same nonce is rejected."""
        # First transaction: alice -> bob (30 coins, leaving 70 - 0.5 = 69.5)
        tx1 = Transaction(
            sender="alice",
            receiver="bob",
            amount=30.0,
            fee=0.5,
            nonce=0,  # nonce 0
        )
        tx1.sign("alice")

        # Second transaction: alice -> charlie (same nonce - double spend attempt)
        # Using small amount to ensure nonce error is caught, not balance
        tx2 = Transaction(
            sender="alice",
            receiver="charlie",
            amount=10.0,
            fee=0.5,
            nonce=0,  # Same nonce as tx1!
        )
        tx2.sign("alice")

        # First transaction should be valid
        can_apply1, error1 = self.blockchain.can_apply_transaction(tx1)
        self.assertTrue(can_apply1, f"First tx should be valid: {error1}")

        # Add first transaction in a block
        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=2,
            transactions=[coinbase, tx1],
            previous_hash=self.blockchain.get_latest_block().hash,
            difficulty=1,
        )
        block.mine(max_iterations=10000)
        added, _ = self.blockchain.add_block(block)
        self.assertTrue(added)

        # Alice's nonce should now be 1
        self.assertEqual(self.blockchain.get_nonce("alice"), 1)

        # Second transaction with nonce 0 should be REJECTED (nonce error)
        can_apply2, error2 = self.blockchain.can_apply_transaction(tx2)
        self.assertFalse(can_apply2, "Double spend should be rejected")
        self.assertIn("nonce", error2.lower())

    def test_double_spend_insufficient_balance(self):
        """Test that spending more than balance is rejected."""
        # Alice has 100 coins, try to spend 150
        tx = Transaction(
            sender="alice",
            receiver="bob",
            amount=150.0,
            fee=0.5,
            nonce=0,
        )
        tx.sign("alice")

        can_apply, error = self.blockchain.can_apply_transaction(tx)
        self.assertFalse(can_apply)
        self.assertIn("balance", error.lower())

    def test_double_spend_after_partial_spend(self):
        """Test that double spend is caught after partial balance spent."""
        # Alice has 100 coins
        # First: spend 60 coins
        tx1 = Transaction(
            sender="alice",
            receiver="bob",
            amount=60.0,
            fee=0.5,
            nonce=0,
        )
        tx1.sign("alice")

        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=2,
            transactions=[coinbase, tx1],
            previous_hash=self.blockchain.get_latest_block().hash,
            difficulty=1,
        )
        block.mine(max_iterations=10000)
        self.blockchain.add_block(block)

        # Alice now has 100 - 60 - 0.5 = 39.5 coins
        alice_balance = self.blockchain.get_balance("alice")
        self.assertAlmostEqual(alice_balance, 39.5, places=2)

        # Try to spend 50 coins (more than remaining balance)
        tx2 = Transaction(
            sender="alice",
            receiver="charlie",
            amount=50.0,
            fee=0.5,
            nonce=1,
        )
        tx2.sign("alice")

        can_apply, error = self.blockchain.can_apply_transaction(tx2)
        self.assertFalse(can_apply)
        self.assertIn("balance", error.lower())

    def test_replay_attack_prevention(self):
        """Test that replaying old transactions is prevented via nonce."""
        # Create and process a valid transaction
        tx = Transaction(
            sender="alice",
            receiver="bob",
            amount=10.0,
            fee=0.5,
            nonce=0,
        )
        tx.sign("alice")

        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=2,
            transactions=[coinbase, tx],
            previous_hash=self.blockchain.get_latest_block().hash,
            difficulty=1,
        )
        block.mine(max_iterations=10000)
        self.blockchain.add_block(block)

        # Try to replay the same transaction (exact same tx)
        can_apply, error = self.blockchain.can_apply_transaction(tx)
        self.assertFalse(can_apply, "Replay attack should be prevented")
        self.assertIn("nonce", error.lower())

    def test_sequential_nonce_required(self):
        """Test that transactions must use sequential nonces."""
        # Try to use nonce 5 when expected nonce is 0
        tx = Transaction(
            sender="alice",
            receiver="bob",
            amount=10.0,
            fee=0.5,
            nonce=5,  # Wrong nonce!
        )
        tx.sign("alice")

        can_apply, error = self.blockchain.can_apply_transaction(tx)
        self.assertFalse(can_apply)
        self.assertIn("nonce", error.lower())
        self.assertIn("expected 0", error.lower())


class TestSelfTransfer(unittest.TestCase):
    """Tests for self-transfer prevention."""

    def test_self_transfer_rejected(self):
        """Test that sending to yourself is rejected."""
        tx = Transaction(
            sender="alice",
            receiver="alice",  # Same as sender!
            amount=10.0,
            fee=0.5,
            nonce=0,
        )
        tx.sign("alice")

        is_valid, error = tx.is_valid(verify_sig=False)
        self.assertFalse(is_valid)
        self.assertIn("different", error.lower())


if __name__ == "__main__":
    unittest.main()
