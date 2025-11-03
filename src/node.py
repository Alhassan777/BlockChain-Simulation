"""
Main blockchain node that integrates all components.
"""

import asyncio
import logging
from typing import List, Optional
from src.blockchain import Blockchain
from src.mempool import Mempool
from src.transaction import Transaction
from src.block import Block
from src.network import P2PNode, Message
from src.consensus import ProofOfWork


class BlockchainNode:
    """Complete blockchain node with networking, consensus, and state management."""
    
    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        difficulty: int = 2,
        block_reward: float = 50.0,
        miner_address: Optional[str] = None,
        genesis_block: Optional[Block] = None
    ):
        self.node_id = node_id
        self.miner_address = miner_address or node_id
        
        # Core components
        self.blockchain = Blockchain(difficulty=difficulty, genesis_block=genesis_block)
        self.mempool = Mempool()
        self.consensus = ProofOfWork(node_id, difficulty, block_reward)
        self.network = P2PNode(node_id, host, port, self._handle_network_message)
        
        # Mining state
        self.is_mining = False
        self.mining_task: Optional[asyncio.Task] = None
        self.stop_mining_event = asyncio.Event()  # Signal to stop mining
        self.auto_mine = False
        self.min_transactions_to_mine = 1
        
        # Setup logging
        self.logger = logging.getLogger(f"BlockchainNode-{node_id}")
    
    async def start(self) -> None:
        """Start the blockchain node."""
        await self.network.start()
        self.logger.info(f"Blockchain node {self.node_id} started")
    
    async def stop(self) -> None:
        """Stop the blockchain node."""
        self.is_mining = False
        if self.mining_task:
            self.mining_task.cancel()
        await self.network.stop()
        self.logger.info(f"Blockchain node {self.node_id} stopped")
    
    async def connect_to_peer(self, peer_id: str, host: str, port: int) -> bool:
        """Connect to a peer node."""
        success = await self.network.connect_to_peer(peer_id, host, port)
        if success:
            # Request peer's chain
            await self.network.send_to_peer(peer_id, 'GET_CHAIN', {})
        return success
    
    async def _handle_network_message(self, message: Message) -> None:
        """Handle incoming network messages."""
        try:
            if message.msg_type == 'NEW_TX':
                await self._handle_new_transaction(message)
            elif message.msg_type == 'NEW_BLOCK':
                await self._handle_new_block(message)
            elif message.msg_type == 'GET_CHAIN':
                await self._handle_get_chain(message)
            elif message.msg_type == 'CHAIN_RESPONSE':
                await self._handle_chain_response(message)
        except Exception as e:
            self.logger.error(f"Error handling message {message.msg_type}: {e}")
    
    async def _handle_new_transaction(self, message: Message) -> None:
        """Handle incoming transaction."""
        tx_data = message.data['transaction']
        tx = Transaction.from_dict(tx_data)
        
        # Check if already in mempool
        if self.mempool.has_transaction(tx.hash):
            return
        
        # Validate transaction
        can_apply, error = self.blockchain.can_apply_transaction(tx)
        if not can_apply:
            self.logger.warning(f"Rejected transaction {tx.hash[:8]}: {error}")
            return
        
        # Add to mempool
        self.mempool.add_transaction(tx)
        self.logger.info(f"Added transaction {tx.hash[:8]} to mempool")
        
        # Trigger mining if auto-mine is enabled
        if self.auto_mine and not self.is_mining:
            if self.mempool.size() >= self.min_transactions_to_mine:
                asyncio.create_task(self.mine_next_block())
    
    async def _handle_new_block(self, message: Message) -> None:
        """Handle incoming block."""
        block_data = message.data['block']
        block = Block.from_dict(block_data)
        
        self.logger.info(f"Received block #{block.index} from {message.sender_id}")
        
        # Try to add block
        added, error = self.blockchain.add_block(block)
        
        if added:
            self.logger.info(f"Added block #{block.index} to chain")
            
            # Remove included transactions from mempool
            tx_hashes = [tx.hash for tx in block.transactions]
            removed = self.mempool.remove_transactions(tx_hashes)
            self.logger.info(f"Removed {removed} transactions from mempool")
            
            # Stop current mining if any
            if self.is_mining:
                self.logger.info("Stopping current mining due to new block")
                self.stop_mining_event.set()  # Signal to stop
                if self.mining_task:
                    self.mining_task.cancel()
                    try:
                        await self.mining_task
                    except asyncio.CancelledError:
                        pass
                self.is_mining = False
        else:
            # Check if block is from a longer chain
            if block.index > self.blockchain.get_chain_length():
                self.logger.info(f"Block from longer chain detected, requesting full chain from {message.sender_id}")
                await self.network.send_to_peer(message.sender_id, 'GET_CHAIN', {})
            else:
                self.logger.warning(f"Rejected block #{block.index}: {error}")
    
    async def _handle_get_chain(self, message: Message) -> None:
        """Handle chain request."""
        chain_data = self.blockchain.to_dict()
        await self.network.send_to_peer(
            message.sender_id,
            'CHAIN_RESPONSE',
            {'chain': chain_data}
        )
    
    async def _handle_chain_response(self, message: Message) -> None:
        """Handle chain response."""
        chain_data = message.data['chain']
        new_blockchain = Blockchain.from_dict(chain_data)
        
        # Try to replace chain if longer
        replaced, error = self.blockchain.replace_chain(new_blockchain.chain)
        
        if replaced:
            self.logger.info(
                f"Replaced chain with longer chain from {message.sender_id} "
                f"(length {len(new_blockchain.chain)})"
            )
            
            # Rebuild mempool (remove transactions now in chain)
            chain_tx_hashes = set()
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    chain_tx_hashes.add(tx.hash)
            
            # Remove transactions that are now in the chain
            mempool_txs = self.mempool.get_all_transactions()
            for tx in mempool_txs:
                if tx.hash in chain_tx_hashes:
                    self.mempool.remove_transaction(tx.hash)
        else:
            self.logger.debug(f"Did not replace chain: {error}")
    
    async def submit_transaction(self, tx: Transaction) -> bool:
        """
        Submit a new transaction to the network.
        Returns True if accepted, False otherwise.
        """
        # Validate transaction
        can_apply, error = self.blockchain.can_apply_transaction(tx)
        if not can_apply:
            self.logger.warning(f"Transaction rejected: {error}")
            return False
        
        # Add to mempool
        self.mempool.add_transaction(tx)
        
        # Broadcast to network
        await self.network.broadcast('NEW_TX', {'transaction': tx.to_dict()})
        
        self.logger.info(f"Submitted transaction {tx.hash[:8]}")
        return True
    
    async def mine_next_block(self, max_iterations: Optional[int] = None) -> Optional[Block]:
        """
        Mine the next block with transactions from mempool.
        Returns the mined block if successful, None otherwise.
        """
        if self.is_mining:
            self.logger.warning("Already mining")
            return None
        
        self.is_mining = True
        self.stop_mining_event.clear()  # Reset stop signal
        
        try:
            # Get transactions from mempool
            transactions = self.mempool.get_top_transactions(max_count=100)
            
            # Note: Empty mempool is OK - we can mine blocks with only coinbase
            # This is how miners get initial coins
            
            # Create block
            latest_block = self.blockchain.get_latest_block()
            target_index = latest_block.index + 1
            
            block = self.consensus.create_block(
                index=target_index,
                transactions=transactions,
                previous_hash=latest_block.hash,
                miner_address=self.miner_address
            )
            
            self.logger.info(f"Mining block #{block.index} with {len(transactions)} transactions...")
            
            # Mine block with stop event
            success = await self.consensus.mine_block_async(
                block, 
                max_iterations,
                stop_event=self.stop_mining_event
            )
            
            # Check if we should still add this block (chain might have advanced)
            if success and self.blockchain.get_latest_block().index >= target_index:
                self.logger.info(f"Block #{target_index} already mined by another node, discarding our work")
                self.is_mining = False
                return None
            
            if success:
                # Add block to chain
                added, error = self.blockchain.add_block(block)
                
                if added:
                    self.logger.info(f"Successfully mined block #{block.index}")
                    
                    # Remove transactions from mempool
                    tx_hashes = [tx.hash for tx in block.transactions]
                    self.mempool.remove_transactions(tx_hashes)
                    
                    # Broadcast block
                    await self.network.broadcast('NEW_BLOCK', {'block': block.to_dict()})
                    
                    self.is_mining = False
                    return block
                else:
                    self.logger.error(f"Failed to add mined block: {error}")
            else:
                self.logger.info("Mining stopped or max iterations reached")
        
        except asyncio.CancelledError:
            self.logger.info("Mining cancelled")
        except Exception as e:
            self.logger.error(f"Error during mining: {e}")
        finally:
            self.is_mining = False
        
        return None
    
    def enable_auto_mining(self, min_transactions: int = 1) -> None:
        """Enable automatic mining when transactions arrive."""
        self.auto_mine = True
        self.min_transactions_to_mine = min_transactions
        self.logger.info(f"Auto-mining enabled (min {min_transactions} txs)")
    
    def disable_auto_mining(self) -> None:
        """Disable automatic mining."""
        self.auto_mine = False
        self.logger.info("Auto-mining disabled")
    
    def get_status(self) -> dict:
        """Get node status."""
        return {
            'node_id': self.node_id,
            'chain_length': self.blockchain.get_chain_length(),
            'chain_tip': self.blockchain.get_latest_block().hash,
            'mempool_size': self.mempool.size(),
            'balance': self.blockchain.get_balance(self.miner_address),
            'is_mining': self.is_mining,
            'peers': self.network.get_peer_ids(),
            'peer_count': self.network.get_peer_count()
        }

