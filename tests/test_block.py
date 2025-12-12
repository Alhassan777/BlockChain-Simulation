"""
Unit tests for Block module.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.block import Block
from src.transaction import Transaction


def test_block_creation():
    """Test basic block creation."""
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(index=0, transactions=[tx], previous_hash="0" * 64, difficulty=1)

    assert block.index == 0
    assert len(block.transactions) == 1
    assert block.previous_hash == "0" * 64


def test_block_hash():
    """Test block hash computation."""
    tx = Transaction.create_coinbase("miner1", 50.0)
    # Use same timestamp to ensure deterministic hashing
    timestamp = 1000.0
    block1 = Block(0, [tx], "0" * 64, difficulty=1, nonce=0, timestamp=timestamp)
    block2 = Block(0, [tx], "0" * 64, difficulty=1, nonce=0, timestamp=timestamp)

    # Same data should produce same hash
    assert block1.hash == block2.hash

    # Different nonce should produce different hash
    block3 = Block(0, [tx], "0" * 64, difficulty=1, nonce=1, timestamp=timestamp)
    assert block1.hash != block3.hash


def test_block_mining():
    """Test Proof-of-Work mining."""
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(0, [tx], "0" * 64, difficulty=2)

    # Mine block
    success = block.mine(max_iterations=100000)
    assert success == True

    # Check proof is valid
    assert block.is_valid_proof() == True
    assert block.hash.startswith("00")


def test_block_validation():
    """Test block validation."""
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(0, [tx], "0" * 64, difficulty=2)
    block.mine(max_iterations=100000)

    # Valid block
    is_valid, error = block.is_valid()
    assert is_valid == True

    # Invalid: wrong proof
    bad_block = Block(0, [tx], "0" * 64, difficulty=2)
    bad_block.nonce = 999999  # Wrong nonce
    is_valid, error = bad_block.is_valid()
    assert is_valid == False


def test_genesis_block():
    """Test genesis block creation."""
    genesis = Block.create_genesis_block()

    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64
    assert genesis.is_valid_proof() == True


def test_block_serialization():
    """Test block to/from dict."""
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(0, [tx], "0" * 64, difficulty=1)
    block.mine(max_iterations=10000)

    # To dict
    block_dict = block.to_dict()
    assert block_dict["index"] == 0
    assert len(block_dict["transactions"]) == 1

    # From dict
    block_restored = Block.from_dict(block_dict)
    assert block_restored.index == block.index
    assert block_restored.hash == block.hash


if __name__ == "__main__":
    test_block_creation()
    test_block_hash()
    test_block_mining()
    test_block_validation()
    test_genesis_block()
    test_block_serialization()
    print("✓ All block tests passed!")
