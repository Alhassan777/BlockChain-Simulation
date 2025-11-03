"""
Fault injection module for testing network resilience.
"""

import asyncio
import logging
from typing import List
from src.node import BlockchainNode


class FaultInjector:
    """Manages fault injection for testing."""
    
    def __init__(self, nodes: List[BlockchainNode]):
        self.nodes = nodes
        self.logger = logging.getLogger("FaultInjector")
    
    def set_message_drop_rate(self, node_id: str, drop_prob: float) -> bool:
        """
        Set message drop probability for a node.
        
        Args:
            node_id: Node to affect
            drop_prob: Probability of dropping a message (0.0 to 1.0)
        
        Returns:
            True if successful, False if node not found
        """
        node = self._get_node(node_id)
        if not node:
            return False
        
        node.network.set_fault_injection(drop_prob=drop_prob)
        self.logger.info(f"Set message drop rate to {drop_prob*100}% for {node_id}")
        return True
    
    def set_message_delay(self, node_id: str, delay_ms: int) -> bool:
        """
        Set message delay for a node.
        
        Args:
            node_id: Node to affect
            delay_ms: Delay in milliseconds
        
        Returns:
            True if successful, False if node not found
        """
        node = self._get_node(node_id)
        if not node:
            return False
        
        node.network.set_fault_injection(delay_ms=delay_ms)
        self.logger.info(f"Set message delay to {delay_ms}ms for {node_id}")
        return True
    
    async def crash_node(self, node_id: str) -> bool:
        """
        Crash a node (stop all operations).
        
        Args:
            node_id: Node to crash
        
        Returns:
            True if successful, False if node not found
        """
        node = self._get_node(node_id)
        if not node:
            return False
        
        await node.stop()
        self.logger.info(f"Crashed node {node_id}")
        return True
    
    async def restart_node(self, node_id: str) -> bool:
        """
        Restart a crashed node.
        
        Args:
            node_id: Node to restart
        
        Returns:
            True if successful, False if node not found
        """
        node = self._get_node(node_id)
        if not node:
            return False
        
        await node.start()
        
        # Reconnect to peers
        for other_node in self.nodes:
            if other_node.node_id != node_id:
                await node.connect_to_peer(
                    other_node.node_id,
                    other_node.network.host,
                    other_node.network.port
                )
        
        self.logger.info(f"Restarted node {node_id}")
        return True
    
    async def partition_network(self, group1_ids: List[str], group2_ids: List[str]) -> bool:
        """
        Create a network partition by disconnecting two groups.
        
        Args:
            group1_ids: Node IDs in first group
            group2_ids: Node IDs in second group
        
        Returns:
            True if successful
        """
        # Disconnect all connections between groups
        for node_id_1 in group1_ids:
            node1 = self._get_node(node_id_1)
            if not node1:
                continue
            

            for node_id_2 in group2_ids:
                # Remove peer from node1 (if exists)
                if node_id_2 in node1.network.peers:
                    writer = node1.network.peers[node_id_2]
                    writer.close()
                    await writer.wait_closed()
                    # Check again as closing might have triggered cleanup
                    if node_id_2 in node1.network.peers:
                        del node1.network.peers[node_id_2]
                if node_id_2 in node1.network.peer_info:
                    del node1.network.peer_info[node_id_2]
        
        # Do the reverse
        for node_id_2 in group2_ids:
            node2 = self._get_node(node_id_2)
            if not node2:
                continue
            
            for node_id_1 in group1_ids:
                if node_id_1 in node2.network.peers:
                    writer = node2.network.peers[node_id_1]
                    writer.close()
                    await writer.wait_closed()
                    # Check again as closing might have triggered cleanup
                    if node_id_1 in node2.network.peers:
                        del node2.network.peers[node_id_1]
                if node_id_1 in node2.network.peer_info:
                    del node2.network.peer_info[node_id_1]
        
        self.logger.info(f"Partitioned network: {group1_ids} | {group2_ids}")
        return True
    
    async def heal_partition(self) -> bool:
        """
        Heal a network partition by reconnecting all nodes.
        
        Returns:
            True if successful
        """
        for i, node1 in enumerate(self.nodes):
            for node2 in self.nodes[i+1:]:
                # Check if not already connected
                if node2.node_id not in node1.network.peers:
                    await node1.connect_to_peer(
                        node2.node_id,
                        node2.network.host,
                        node2.network.port
                    )
                    await asyncio.sleep(0.1)  # Small delay
        
        self.logger.info("Healed network partition")
        return True
    
    def _get_node(self, node_id: str) -> BlockchainNode:
        """Get node by ID."""
        return next((n for n in self.nodes if n.node_id == node_id), None)
    
    async def inject_invalid_transaction(self, node_id: str) -> bool:
        """
        Inject an invalid transaction (insufficient balance).
        
        Args:
            node_id: Node to inject transaction to
        
        Returns:
            True if injected, False if rejected
        """
        from src.transaction import Transaction
        
        node = self._get_node(node_id)
        if not node:
            return False
        
        # Create transaction with amount > sender's balance
        tx = Transaction(
            sender=node_id,
            receiver="victim",
            amount=99999999,  # Huge amount
            fee=0,
            nonce=0
        )
        tx.sign(node_id)  # Toy signature
        
        # Try to submit (should be rejected)
        result = await node.submit_transaction(tx)
        
        self.logger.info(f"Injected invalid transaction to {node_id} (accepted={result})")
        return result

