"""
Unit tests for Blockchain module.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.blockchain import Blockchain
from src.block import Block
from src.transaction import Transaction


def test_blockchain_creation():
    """Test blockchain initialization."""
    blockchain = Blockchain(difficulty=2)
    
    # Should have genesis block
    assert blockchain.get_chain_length() == 1
    assert blockchain.chain[0].index == 0


def test_add_block():
    """Test adding blocks to chain."""
    blockchain = Blockchain(difficulty=1)
    
    # Create and add block
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(
        index=1,
        transactions=[tx],
        previous_hash=blockchain.get_latest_block().hash,
        difficulty=1
    )
    block.mine(max_iterations=10000)
    
    added, error = blockchain.add_block(block)
    assert added == True
    assert blockchain.get_chain_length() == 2


def test_balance_tracking():
    """Test account balance tracking."""
    blockchain = Blockchain(difficulty=1)
    
    # Genesis gives 0 to GENESIS
    genesis_balance = blockchain.get_balance("GENESIS")
    assert genesis_balance == 0
    
    # Add block with coinbase
    tx = Transaction.create_coinbase("miner1", 50.0)
    block = Block(1, [tx], blockchain.get_latest_block().hash, difficulty=1)
    block.mine(max_iterations=10000)
    blockchain.add_block(block)
    
    # Check balance
    assert blockchain.get_balance("miner1") == 50.0


def test_transaction_validation():
    """Test transaction validation against state."""
    blockchain = Blockchain(difficulty=1)
    
    # Give miner1 some coins
    tx_coinbase = Transaction.create_coinbase("miner1", 50.0)
    block1 = Block(1, [tx_coinbase], blockchain.get_latest_block().hash, difficulty=1)
    block1.mine(max_iterations=10000)
    blockchain.add_block(block1)
    
    # Valid transaction
    tx_valid = Transaction("miner1", "alice", 10.0, 0.5, 0)
    tx_valid.sign("miner1")
    can_apply, error = blockchain.can_apply_transaction(tx_valid)
    assert can_apply == True
    
    # Invalid: insufficient balance
    tx_invalid = Transaction("miner1", "alice", 100.0, 0.5, 0)
    tx_invalid.sign("miner1")
    can_apply, error = blockchain.can_apply_transaction(tx_invalid)
    assert can_apply == False
    assert "balance" in error.lower()


def test_nonce_tracking():
    """Test nonce tracking."""
    blockchain = Blockchain(difficulty=1)
    
    # Initial nonce should be 0
    assert blockchain.get_nonce("alice") == 0
    
    # Give alice coins and make transaction
    tx_coinbase = Transaction.create_coinbase("alice", 50.0)
    block1 = Block(1, [tx_coinbase], blockchain.get_latest_block().hash, difficulty=1)
    block1.mine(max_iterations=10000)
    blockchain.add_block(block1)
    
    tx = Transaction("alice", "bob", 10.0, 0.5, 0)
    tx.sign("alice")
    tx_coinbase2 = Transaction.create_coinbase("miner", 50.0)
    block2 = Block(2, [tx_coinbase2, tx], blockchain.get_latest_block().hash, difficulty=1)
    block2.mine(max_iterations=10000)
    blockchain.add_block(block2)
    
    # Nonce should be incremented
    assert blockchain.get_nonce("alice") == 1


def test_fork_resolution():
    """Test longest-chain rule."""
    # Create blockchain with shared genesis
    genesis = Block.create_genesis_block()
    blockchain = Blockchain(difficulty=1, genesis_block=genesis)
    
    # Create longer chain using the same genesis
    longer_chain = [genesis]  # Start with same genesis
    
    for i in range(1, 5):
        tx = Transaction.create_coinbase(f"miner{i}", 50.0)
        block = Block(i, [tx], longer_chain[-1].hash, difficulty=1)
        block.mine(max_iterations=10000)
        longer_chain.append(block)
    
    # Replace chain
    replaced, error = blockchain.replace_chain(longer_chain)
    assert replaced == True
    assert blockchain.get_chain_length() == 5


def test_chain_validation():
    """Test full chain validation."""
    # Create blockchain with proper genesis
    genesis = Block.create_genesis_block()
    blockchain = Blockchain(difficulty=1, genesis_block=genesis)
    
    # Add valid blocks
    for i in range(1, 3):
        tx = Transaction.create_coinbase(f"miner{i}", 50.0)
        block = Block(i, [tx], blockchain.get_latest_block().hash, difficulty=1)
        block.mine(max_iterations=10000)
        blockchain.add_block(block)
    
    # Validate
    is_valid, error = Blockchain.validate_chain(blockchain.chain)
    assert is_valid == True


if __name__ == "__main__":
    test_blockchain_creation()
    test_add_block()
    test_balance_tracking()
    test_transaction_validation()
    test_nonce_tracking()
    test_fork_resolution()
    test_chain_validation()
    print("✓ All blockchain tests passed!")

