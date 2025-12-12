"""
Unit tests for Transaction module.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.transaction import Transaction


def test_transaction_creation():
    """Test basic transaction creation."""
    tx = Transaction(sender="alice", receiver="bob", amount=10.0, fee=0.5, nonce=0)

    assert tx.sender == "alice"
    assert tx.receiver == "bob"
    assert tx.amount == 10.0
    assert tx.fee == 0.5
    assert tx.nonce == 0


def test_transaction_hash():
    """Test transaction hash computation."""
    tx1 = Transaction("alice", "bob", 10.0, 0.5, 0)
    tx2 = Transaction("alice", "bob", 10.0, 0.5, 0)

    # Same data should produce same hash
    assert tx1.hash == tx2.hash

    # Different data should produce different hash
    tx3 = Transaction("alice", "bob", 11.0, 0.5, 0)
    assert tx1.hash != tx3.hash


def test_transaction_signature():
    """Test transaction signing and verification."""
    tx = Transaction("alice", "bob", 10.0, 0.5, 0)

    # Sign transaction
    tx.sign("alice_private_key")
    assert tx.signature is not None

    # Verify with correct key
    assert tx.verify_signature("alice_private_key") == True

    # Verify with wrong key
    assert tx.verify_signature("bob_private_key") == False


def test_transaction_validation():
    """Test transaction validation."""
    # Valid transaction
    tx = Transaction("alice", "bob", 10.0, 0.5, 0)
    tx.sign("alice")
    is_valid, error = tx.is_valid()
    assert is_valid == True

    # Invalid: negative amount
    tx_invalid = Transaction("alice", "bob", -10.0, 0.5, 0)
    is_valid, error = tx_invalid.is_valid(verify_sig=False)
    assert is_valid == False
    assert "negative" in error.lower() or "positive" in error.lower()

    # Invalid: negative fee
    tx_invalid = Transaction("alice", "bob", 10.0, -0.5, 0)
    is_valid, error = tx_invalid.is_valid(verify_sig=False)
    assert is_valid == False
    assert "fee" in error.lower()


def test_coinbase_transaction():
    """Test coinbase transaction creation."""
    coinbase = Transaction.create_coinbase("miner1", 50.0)

    assert coinbase.sender == "COINBASE"
    assert coinbase.receiver == "miner1"
    assert coinbase.amount == 50.0
    assert coinbase.signature == "COINBASE"


def test_transaction_serialization():
    """Test transaction to/from dict."""
    tx = Transaction("alice", "bob", 10.0, 0.5, 0)
    tx.sign("alice")

    # To dict
    tx_dict = tx.to_dict()
    assert tx_dict["sender"] == "alice"
    assert tx_dict["amount"] == 10.0

    # From dict
    tx_restored = Transaction.from_dict(tx_dict)
    assert tx_restored.sender == tx.sender
    assert tx_restored.amount == tx.amount
    assert tx_restored.hash == tx.hash


if __name__ == "__main__":
    test_transaction_creation()
    test_transaction_hash()
    test_transaction_signature()
    test_transaction_validation()
    test_coinbase_transaction()
    test_transaction_serialization()
    print("✓ All transaction tests passed!")
