"""
Blockchain module for maintaining the distributed ledger.
Handles chain management, fork resolution, and state transitions.
"""

from typing import List, Dict, Optional, Tuple
from src.block import Block
from src.transaction import Transaction
import copy


class Blockchain:
    """Manages the blockchain and account state."""
    
    def __init__(self, difficulty: int = 2, genesis_block: Optional[Block] = None):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.state: Dict[str, Dict] = {}  # address -> {balance, nonce}
        
        # Create or use provided genesis block
        if genesis_block:
            genesis = genesis_block
        else:
            genesis = Block.create_genesis_block()
        
        self.chain.append(genesis)
        self._apply_block_to_state(genesis)
    
    def _apply_block_to_state(self, block: Block) -> None:
        """Apply block transactions to state."""
        for tx in block.transactions:
            # Initialize accounts if needed
            if tx.sender not in self.state and tx.sender != "COINBASE":
                self.state[tx.sender] = {'balance': 0.0, 'nonce': 0}
            if tx.receiver not in self.state:
                self.state[tx.receiver] = {'balance': 0.0, 'nonce': 0}
            
            # Apply transaction
            if tx.sender == "COINBASE":
                # Coinbase transaction (mining reward)
                self.state[tx.receiver]['balance'] += tx.amount
            else:
                # Regular transaction
                self.state[tx.sender]['balance'] -= (tx.amount + tx.fee)
                self.state[tx.receiver]['balance'] += tx.amount
                self.state[tx.sender]['nonce'] = tx.nonce + 1
    
    def _revert_block_from_state(self, block: Block) -> None:
        """Revert block transactions from state."""
        for tx in reversed(block.transactions):
            if tx.sender == "COINBASE":
                self.state[tx.receiver]['balance'] -= tx.amount
            else:
                self.state[tx.sender]['balance'] += (tx.amount + tx.fee)
                self.state[tx.receiver]['balance'] -= tx.amount
                self.state[tx.sender]['nonce'] = tx.nonce
    
    def get_balance(self, address: str) -> float:
        """Get account balance."""
        if address not in self.state:
            return 0.0
        return self.state[address]['balance']
    
    def get_nonce(self, address: str) -> int:
        """Get account nonce."""
        if address not in self.state:
            return 0
        return self.state[address]['nonce']
    
    def can_apply_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        """
        Check if transaction can be applied to current state.
        Returns (can_apply, error_message).
        """
        # Validate transaction structure
        is_valid, error = tx.is_valid(verify_sig=True)
        if not is_valid:
            return False, error
        
        # Skip state checks for coinbase
        if tx.sender == "COINBASE":
            return True, ""
        
        # Check sender balance
        sender_balance = self.get_balance(tx.sender)
        total_cost = tx.amount + tx.fee
        if sender_balance < total_cost:
            return False, f"Insufficient balance: {sender_balance} < {total_cost}"
        
        # Check nonce
        expected_nonce = self.get_nonce(tx.sender)
        if tx.nonce != expected_nonce:
            return False, f"Invalid nonce: expected {expected_nonce}, got {tx.nonce}"
        
        return True, ""
    
    def add_block(self, block: Block) -> Tuple[bool, str]:
        """
        Add a new block to the chain.
        Returns (added, error_message).
        """
        # Validate block structure
        is_valid, error = block.is_valid(verify_transactions=True)
        if not is_valid:
            return False, error
        
        # Check index
        if block.index != len(self.chain):
            return False, f"Invalid index: expected {len(self.chain)}, got {block.index}"
        
        # Check previous hash
        if block.previous_hash != self.chain[-1].hash:
            return False, "Invalid previous_hash"
        
        # Validate transactions against current state
        for i, tx in enumerate(block.transactions):
            # Skip coinbase validation for state
            if i == 0 and tx.sender == "COINBASE":
                continue
            
            can_apply, error = self.can_apply_transaction(tx)
            if not can_apply:
                return False, f"Transaction {i} invalid: {error}"
        
        # Add block and update state
        self.chain.append(block)
        self._apply_block_to_state(block)
        
        return True, ""
    
    def replace_chain(self, new_chain: List[Block]) -> Tuple[bool, str]:
        """
        Replace current chain with a longer valid chain (fork resolution).
        Returns (replaced, error_message).
        """
        # Check if new chain is longer
        if len(new_chain) <= len(self.chain):
            return False, "New chain is not longer"
        
        # Validate new chain
        is_valid, error = self.validate_chain(new_chain)
        if not is_valid:
            return False, f"Invalid chain: {error}"
        
        # Replace chain and rebuild state
        self.chain = new_chain
        self.state = {}
        for block in self.chain:
            self._apply_block_to_state(block)
        
        return True, ""
    
    @staticmethod
    def validate_chain(chain: List[Block]) -> Tuple[bool, str]:
        """
        Validate an entire chain.
        Returns (is_valid, error_message).
        """
        if not chain:
            return False, "Chain is empty"
        
        # Validate genesis block
        if chain[0].index != 0:
            return False, "Invalid genesis block index"
        if chain[0].previous_hash != "0" * 64:
            return False, "Invalid genesis block previous_hash"
        
        # Validate each block and links
        for i in range(len(chain)):
            block = chain[i]
            
            # Validate block
            is_valid, error = block.is_valid(verify_transactions=True)
            if not is_valid:
                return False, f"Block {i} invalid: {error}"
            
            # Check index
            if block.index != i:
                return False, f"Block {i} has wrong index: {block.index}"
            
            # Check link to previous block
            if i > 0:
                if block.previous_hash != chain[i-1].hash:
                    return False, f"Block {i} has invalid previous_hash"
        
        return True, ""
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def get_chain_length(self) -> int:
        """Get the length of the chain."""
        return len(self.chain)
    
    def to_dict(self) -> Dict:
        """Convert blockchain to dictionary."""
        return {
            'difficulty': self.difficulty,
            'chain': [block.to_dict() for block in self.chain],
            'state': self.state
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Blockchain':
        """Create blockchain from dictionary."""
        blockchain = cls.__new__(cls)
        blockchain.difficulty = data['difficulty']
        blockchain.chain = [Block.from_dict(block_data) for block_data in data['chain']]
        blockchain.state = data['state']
        return blockchain
    
    def __repr__(self) -> str:
        return f"Blockchain(length={len(self.chain)}, tip={self.chain[-1].hash[:8]}...)"

