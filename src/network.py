"""
P2P Network module for node communication.
Implements asyncio-based TCP networking with gossip protocol.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a network message."""
    msg_type: str
    data: Dict[str, Any]
    msg_id: str
    sender_id: str


class P2PNode:
    """Peer-to-peer network node with gossip protocol."""
    
    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        message_handler: Optional[Callable] = None
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.message_handler = message_handler
        
        # Networking
        self.peers: Dict[str, asyncio.StreamWriter] = {}  # peer_id -> writer
        self.peer_info: Dict[str, tuple] = {}  # peer_id -> (host, port)
        self.seen_messages: Set[str] = set()  # For duplicate suppression
        self.server: Optional[asyncio.Server] = None
        
        # Fault injection
        self.message_drop_prob = 0.0
        self.message_delay_ms = 0
        self.is_crashed = False
        
        # Setup logging
        self.logger = logging.getLogger(f"Node-{node_id}")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def start(self) -> None:
        """Start the node's TCP server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        self.logger.info(f"Node {self.node_id} listening on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the node and close all connections."""
        self.is_crashed = True
        
        # Close all peer connections (copy to list to avoid dict size change during iteration)
        for writer in list(self.peers.values()):
            writer.close()
            await writer.wait_closed()
        
        # Clear peer dictionaries
        self.peers.clear()
        self.peer_info.clear()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.logger.info(f"Node {self.node_id} stopped")
    
    async def restart(self) -> None:
        """Restart the node after a crash."""
        self.is_crashed = False
        self.seen_messages.clear()
        await self.start()
        self.logger.info(f"Node {self.node_id} restarted")
    
    async def connect_to_peer(self, peer_id: str, host: str, port: int) -> bool:
        """
        Connect to a peer node.
        Returns True if connection successful, False otherwise.
        """
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            # Send handshake
            handshake = {
                'type': 'HANDSHAKE',
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port
            }
            writer.write(json.dumps(handshake).encode() + b'\n')
            await writer.drain()
            
            # Store peer info
            self.peers[peer_id] = writer
            self.peer_info[peer_id] = (host, port)
            
            self.logger.info(f"Connected to peer {peer_id} at {host}:{port}")
            
            # Start listening to this peer
            asyncio.create_task(self._listen_to_peer(peer_id, reader))
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to connect to {peer_id}: {e}")
            return False
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming connection from a peer."""
        try:
            # Read handshake
            data = await reader.readline()
            handshake = json.loads(data.decode())
            
            if handshake['type'] == 'HANDSHAKE':
                peer_id = handshake['node_id']
                peer_host = handshake['host']
                peer_port = handshake['port']
                
                # Store peer info
                self.peers[peer_id] = writer
                self.peer_info[peer_id] = (peer_host, peer_port)
                
                self.logger.info(f"Accepted connection from peer {peer_id}")
                
                # Start listening to this peer
                asyncio.create_task(self._listen_to_peer(peer_id, reader))
        
        except Exception as e:
            self.logger.error(f"Error handling client connection: {e}")
            writer.close()
            await writer.wait_closed()
    
    async def _listen_to_peer(self, peer_id: str, reader: asyncio.StreamReader) -> None:
        """Listen for messages from a peer."""
        try:
            while not self.is_crashed:
                data = await reader.readline()
                if not data:
                    break
                
                message_json = data.decode().strip()
                if not message_json:
                    continue
                
                message_data = json.loads(message_json)
                
                # Skip handshakes
                if message_data.get('type') == 'HANDSHAKE':
                    continue
                
                # Process message
                await self._handle_message(message_data, peer_id)
        
        except Exception as e:
            self.logger.error(f"Error listening to peer {peer_id}: {e}")
        
        finally:
            # Clean up disconnected peer
            if peer_id in self.peers:
                del self.peers[peer_id]
                del self.peer_info[peer_id]
                self.logger.info(f"Peer {peer_id} disconnected")
    
    async def _handle_message(self, message_data: Dict, sender_id: str) -> None:
        """Handle incoming message."""
        if self.is_crashed:
            return
        
        msg_id = message_data.get('msg_id', '')
        
        # Duplicate suppression
        if msg_id in self.seen_messages:
            return
        
        self.seen_messages.add(msg_id)
        
        # Apply fault injection (message drop)
        if self.message_drop_prob > 0:
            import random
            if random.random() < self.message_drop_prob:
                self.logger.debug(f"Dropped message {msg_id}")
                return
        
        # Apply delay
        if self.message_delay_ms > 0:
            await asyncio.sleep(self.message_delay_ms / 1000.0)
        
        # Create message object
        message = Message(
            msg_type=message_data['type'],
            data=message_data['data'],
            msg_id=msg_id,
            sender_id=message_data['sender_id']
        )
        
        # Call message handler
        if self.message_handler:
            await self.message_handler(message)
        
        # Gossip to other peers (except sender)
        await self._gossip_message(message_data, exclude_peer=sender_id)
    
    async def broadcast(self, msg_type: str, data: Dict[str, Any]) -> None:
        """Broadcast a message to all peers."""
        if self.is_crashed:
            return
        
        import uuid
        msg_id = str(uuid.uuid4())
        
        message = {
            'type': msg_type,
            'data': data,
            'msg_id': msg_id,
            'sender_id': self.node_id
        }
        
        # Mark as seen to avoid processing our own message
        self.seen_messages.add(msg_id)
        
        # Send to all peers
        await self._gossip_message(message)
    
    async def _gossip_message(self, message: Dict, exclude_peer: Optional[str] = None) -> None:
        """Gossip message to all peers except excluded one."""
        message_bytes = json.dumps(message).encode() + b'\n'
        
        for peer_id, writer in list(self.peers.items()):
            if peer_id == exclude_peer:
                continue
            
            try:
                writer.write(message_bytes)
                await writer.drain()
            except Exception as e:
                self.logger.error(f"Failed to send message to {peer_id}: {e}")
    
    async def send_to_peer(self, peer_id: str, msg_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to a specific peer.
        Returns True if sent successfully, False otherwise.
        """
        if peer_id not in self.peers:
            return False
        
        import uuid
        msg_id = str(uuid.uuid4())
        
        message = {
            'type': msg_type,
            'data': data,
            'msg_id': msg_id,
            'sender_id': self.node_id
        }
        
        try:
            writer = self.peers[peer_id]
            writer.write(json.dumps(message).encode() + b'\n')
            await writer.drain()
            return True
        except Exception as e:
            self.logger.error(f"Failed to send to {peer_id}: {e}")
            return False
    
    def get_peer_count(self) -> int:
        """Get number of connected peers."""
        return len(self.peers)
    
    def get_peer_ids(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.peers.keys())
    
    def set_fault_injection(
        self,
        drop_prob: float = 0.0,
        delay_ms: int = 0
    ) -> None:
        """Configure fault injection parameters."""
        self.message_drop_prob = drop_prob
        self.message_delay_ms = delay_ms

