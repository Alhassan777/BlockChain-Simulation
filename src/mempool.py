"""
Mempool (Memory Pool) module for managing pending transactions.
"""

from typing import List, Dict, Optional
from src.transaction import Transaction


class Mempool:
    """Manages pending transactions waiting to be included in blocks."""
    
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}  # tx_hash -> Transaction
    
    def add_transaction(self, tx: Transaction) -> bool:
        """
        Add a transaction to the mempool.
        Returns True if added, False if already exists.
        """
        tx_hash = tx.hash
        if tx_hash in self.transactions:
            return False
        
        self.transactions[tx_hash] = tx
        return True
    
    def remove_transaction(self, tx_hash: str) -> bool:
        """
        Remove a transaction from the mempool.
        Returns True if removed, False if not found.
        """
        if tx_hash in self.transactions:
            del self.transactions[tx_hash]
            return True
        return False
    
    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by hash."""
        return self.transactions.get(tx_hash)
    
    def has_transaction(self, tx_hash: str) -> bool:
        """Check if transaction exists in mempool."""
        return tx_hash in self.transactions
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions in mempool."""
        return list(self.transactions.values())
    
    def get_top_transactions(self, max_count: int, sort_by_fee: bool = True) -> List[Transaction]:
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
            'transactions': [tx.to_dict() for tx in self.transactions.values()]
        }
    
    def __repr__(self) -> str:
        return f"Mempool(size={len(self.transactions)})"

