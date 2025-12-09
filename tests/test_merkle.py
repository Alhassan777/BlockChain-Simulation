"""
Tests for Merkle tree implementation.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.merkle import MerkleTree, compute_merkle_root
from src.transaction import Transaction


class TestMerkleTree:
    """Test cases for MerkleTree class."""
    
    def create_transactions(self, count: int) -> list:
        """Helper to create test transactions."""
        txs = []
        for i in range(count):
            tx = Transaction(
                sender=f"sender{i}",
                receiver=f"receiver{i}",
                amount=float(i + 1),
                fee=0.1,
                nonce=i
            )
            tx.sign(f"sender{i}")
            txs.append(tx)
        return txs
    
    def test_empty_tree(self):
        """Test Merkle tree with no transactions."""
        tree = MerkleTree([])
        assert tree.root is not None
        assert len(tree.root) == 64  # SHA-256 hex length
    
    def test_single_transaction(self):
        """Test Merkle tree with single transaction."""
        txs = self.create_transactions(1)
        tree = MerkleTree(txs)
        
        assert tree.root is not None
        # Single tx: root should be hash of (tx_hash + tx_hash)
        # since we duplicate for odd count
        assert len(tree.root) == 64
    
    def test_two_transactions(self):
        """Test Merkle tree with two transactions."""
        txs = self.create_transactions(2)
        tree = MerkleTree(txs)
        
        assert tree.root is not None
        assert len(tree.root) == 64
        assert len(tree.tree) == 2  # Leaves level + root level
    
    def test_four_transactions(self):
        """Test Merkle tree with four transactions (perfect binary tree)."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        assert tree.root is not None
        assert len(tree.tree) == 3  # 4 leaves, 2 internal, 1 root
        
    def test_odd_transaction_count(self):
        """Test Merkle tree with odd number of transactions."""
        txs = self.create_transactions(5)
        tree = MerkleTree(txs)
        
        assert tree.root is not None
        # Should handle odd count by duplicating last leaf
        assert len(tree.leaves) == 6  # 5 + 1 duplicate
    
    def test_proof_generation(self):
        """Test Merkle proof generation."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        # Get proof for first transaction
        proof = tree.get_proof(0)
        
        assert len(proof) > 0
        # For 4 txs, we need log2(4) = 2 proof elements
        assert len(proof) == 2
    
    def test_proof_verification(self):
        """Test Merkle proof verification."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        # Verify each transaction
        for i, tx in enumerate(txs):
            proof = tree.get_proof(i)
            is_valid = tree.verify_proof(tx.hash, proof, tree.root)
            assert is_valid, f"Proof verification failed for tx {i}"
    
    def test_invalid_proof(self):
        """Test that invalid proofs are rejected."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        # Get proof for tx 0
        proof = tree.get_proof(0)
        
        # Try to verify with wrong transaction hash
        fake_hash = "0" * 64
        is_valid = tree.verify_proof(fake_hash, proof, tree.root)
        assert not is_valid
    
    def test_wrong_root_rejected(self):
        """Test that proof fails with wrong root."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        proof = tree.get_proof(0)
        wrong_root = "f" * 64
        
        is_valid = tree.verify_proof(txs[0].hash, proof, wrong_root)
        assert not is_valid
    
    def test_verify_transaction(self):
        """Test direct transaction verification."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        # Verify transaction is in tree
        for tx in txs:
            assert tree.verify_transaction(tx)
        
        # Create transaction not in tree
        other_tx = Transaction(
            sender="other",
            receiver="other2",
            amount=100.0,
            fee=1.0,
            nonce=999
        )
        other_tx.sign("other")
        
        assert not tree.verify_transaction(other_tx)
    
    def test_root_consistency(self):
        """Test that same transactions always produce same root."""
        txs = self.create_transactions(4)
        
        tree1 = MerkleTree(txs)
        tree2 = MerkleTree(txs)
        
        assert tree1.root == tree2.root
    
    def test_root_changes_with_different_txs(self):
        """Test that different transactions produce different roots."""
        txs1 = self.create_transactions(4)
        txs2 = self.create_transactions(4)
        
        # Modify one transaction
        txs2[0] = Transaction(
            sender="modified",
            receiver="receiver0",
            amount=999.0,
            fee=0.1,
            nonce=0
        )
        txs2[0].sign("modified")
        
        tree1 = MerkleTree(txs1)
        tree2 = MerkleTree(txs2)
        
        assert tree1.root != tree2.root
    
    def test_compute_merkle_root_helper(self):
        """Test the compute_merkle_root helper function."""
        txs = self.create_transactions(4)
        
        tree = MerkleTree(txs)
        root = compute_merkle_root(txs)
        
        assert root == tree.root
    
    def test_large_tree(self):
        """Test Merkle tree with many transactions."""
        txs = self.create_transactions(100)
        tree = MerkleTree(txs)
        
        assert tree.root is not None
        
        # Verify random samples
        for i in [0, 25, 50, 75, 99]:
            proof = tree.get_proof(i)
            assert tree.verify_proof(txs[i].hash, proof, tree.root)
    
    def test_tree_visualization(self):
        """Test tree visualization output."""
        txs = self.create_transactions(4)
        tree = MerkleTree(txs)
        
        viz = tree.get_tree_visualization()
        
        assert "Root" in viz
        assert "..." in viz  # Truncated hashes


class TestBlockMerkleIntegration:
    """Test Merkle tree integration with Block class."""
    
    def test_block_has_merkle_root(self):
        """Test that blocks have Merkle root."""
        from src.block import Block
        
        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            difficulty=1
        )
        
        assert block.merkle_root is not None
        assert len(block.merkle_root) == 64
    
    def test_block_merkle_in_hash(self):
        """Test that Merkle root affects block hash."""
        from src.block import Block
        
        coinbase1 = Transaction.create_coinbase("miner1", 50.0)
        coinbase2 = Transaction.create_coinbase("miner2", 50.0)
        
        block1 = Block(
            index=1,
            transactions=[coinbase1],
            previous_hash="0" * 64,
            difficulty=1
        )
        
        block2 = Block(
            index=1,
            transactions=[coinbase2],
            previous_hash="0" * 64,
            difficulty=1
        )
        
        # Different transactions -> different Merkle roots -> different hashes
        assert block1.merkle_root != block2.merkle_root
        assert block1.hash != block2.hash
    
    def test_block_transaction_proof(self):
        """Test getting transaction proof from block."""
        from src.block import Block
        
        coinbase = Transaction.create_coinbase("miner", 50.0)
        tx1 = Transaction(
            sender="alice",
            receiver="bob",
            amount=10.0,
            fee=0.5,
            nonce=0
        )
        tx1.sign("alice")
        
        block = Block(
            index=1,
            transactions=[coinbase, tx1],
            previous_hash="0" * 64,
            difficulty=1
        )
        
        # Get and verify proof for tx1
        proof = block.get_transaction_proof(1)
        assert block.verify_transaction_proof(tx1, proof)
    
    def test_block_serialization_with_merkle(self):
        """Test that Merkle root is included in block serialization."""
        from src.block import Block
        
        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            difficulty=1
        )
        
        block_dict = block.to_dict()
        
        assert 'merkle_root' in block_dict
        assert block_dict['merkle_root'] == block.merkle_root
        
        # Recreate block from dict
        block2 = Block.from_dict(block_dict)
        assert block2.merkle_root == block.merkle_root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

