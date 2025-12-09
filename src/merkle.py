"""
Merkle Tree module for efficient transaction verification.
Implements a binary Merkle tree using SHA-256 hashing.
"""

import hashlib
from typing import List, Optional, Tuple
from src.transaction import Transaction


class MerkleTree:
    """
    Binary Merkle tree for transaction aggregation.
    
    Provides:
    - O(log n) proof of inclusion for any transaction
    - Single root hash representing all transactions
    - Efficient verification without downloading entire block
    """
    
    def __init__(self, transactions: List[Transaction]):
        """
        Build Merkle tree from list of transactions.
        
        Args:
            transactions: List of transactions to include in tree
        """
        self.transactions = transactions
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []
        self._root: Optional[str] = None
        
        if transactions:
            self._build_tree()
    
    def _hash(self, data: str) -> str:
        """Compute SHA-256 hash of data."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two nodes together."""
        return self._hash(left + right)
    
    def _build_tree(self) -> None:
        """Build the Merkle tree from transactions."""
        # Create leaf nodes from transaction hashes
        self.leaves = [tx.hash for tx in self.transactions]
        
        # If odd number of leaves, duplicate the last one
        if len(self.leaves) % 2 == 1:
            self.leaves.append(self.leaves[-1])
        
        # Build tree bottom-up
        self.tree = [self.leaves.copy()]
        current_level = self.leaves.copy()
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd, duplicate last node
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = self._hash_pair(left, right)
                next_level.append(parent)
            
            self.tree.append(next_level)
            current_level = next_level
        
        self._root = current_level[0] if current_level else self._hash("")
    
    @property
    def root(self) -> str:
        """Get the Merkle root hash."""
        if self._root is None:
            return self._hash("")  # Empty tree
        return self._root
    
    def get_proof(self, tx_index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for a transaction.
        
        Args:
            tx_index: Index of transaction in original list
        
        Returns:
            List of (hash, position) tuples where position is 'left' or 'right'
            indicating which side of the pair the sibling is on
        """
        if tx_index < 0 or tx_index >= len(self.transactions):
            return []
        
        proof = []
        index = tx_index
        
        # Handle case where we duplicated the last leaf
        if len(self.leaves) > len(self.transactions) and tx_index == len(self.transactions) - 1:
            # This transaction was duplicated
            pass
        
        for level in range(len(self.tree) - 1):
            level_size = len(self.tree[level])
            
            # Find sibling
            if index % 2 == 0:
                # We're on the left, sibling is on the right
                sibling_index = index + 1
                if sibling_index < level_size:
                    proof.append((self.tree[level][sibling_index], 'right'))
                else:
                    # No sibling (odd level), use self
                    proof.append((self.tree[level][index], 'right'))
            else:
                # We're on the right, sibling is on the left
                sibling_index = index - 1
                proof.append((self.tree[level][sibling_index], 'left'))
            
            # Move to parent index
            index = index // 2
        
        return proof
    
    def verify_proof(self, tx_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
        """
        Verify a Merkle proof.
        
        Args:
            tx_hash: Hash of the transaction to verify
            proof: Merkle proof from get_proof()
            root: Expected Merkle root
        
        Returns:
            True if proof is valid, False otherwise
        """
        current_hash = tx_hash
        
        for sibling_hash, position in proof:
            if position == 'left':
                current_hash = self._hash_pair(sibling_hash, current_hash)
            else:
                current_hash = self._hash_pair(current_hash, sibling_hash)
        
        return current_hash == root
    
    def verify_transaction(self, tx: Transaction) -> bool:
        """
        Verify that a transaction is in this tree.
        
        Args:
            tx: Transaction to verify
        
        Returns:
            True if transaction is in tree, False otherwise
        """
        try:
            tx_index = next(
                i for i, t in enumerate(self.transactions) 
                if t.hash == tx.hash
            )
            proof = self.get_proof(tx_index)
            return self.verify_proof(tx.hash, proof, self.root)
        except StopIteration:
            return False
    
    def get_tree_visualization(self) -> str:
        """Get a string visualization of the tree structure."""
        if not self.tree:
            return "Empty tree"
        
        lines = []
        for level_idx, level in enumerate(reversed(self.tree)):
            level_name = "Root" if level_idx == 0 else f"Level {len(self.tree) - level_idx - 1}"
            hashes = [h[:8] + "..." for h in level]
            lines.append(f"{level_name}: {' | '.join(hashes)}")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"MerkleTree(transactions={len(self.transactions)}, root={self.root[:16]}...)"


def compute_merkle_root(transactions: List[Transaction]) -> str:
    """
    Compute Merkle root for a list of transactions.
    
    Convenience function for quick root computation.
    
    Args:
        transactions: List of transactions
    
    Returns:
        Merkle root hash
    """
    tree = MerkleTree(transactions)
    return tree.root

