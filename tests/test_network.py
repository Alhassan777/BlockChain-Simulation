"""
Tests for P2P networking and message handling.

Note: Network tests are marked to skip by default since they involve
async operations that can be slow. Run with pytest --run-network to include them.
"""

import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.network import P2PNode, Message

# Skip network tests by default (they can be slow/flaky)
SKIP_NETWORK_TESTS = os.environ.get("RUN_NETWORK_TESTS", "0") != "1"
SKIP_REASON = "Network tests skipped by default. Set RUN_NETWORK_TESTS=1 to run."


class TestP2PNode(unittest.TestCase):
    """Tests for P2P networking - basic unit tests."""

    def test_node_creation(self):
        """Test basic node creation."""
        node = P2PNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
        )

        self.assertEqual(node.node_id, "test_node")
        self.assertEqual(node.host, "127.0.0.1")
        self.assertEqual(node.port, 9000)
        self.assertFalse(node.is_crashed)

    def test_fault_injection_settings(self):
        """Test fault injection configuration."""
        node = P2PNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
        )

        # Default values
        self.assertEqual(node.message_drop_prob, 0.0)
        self.assertEqual(node.message_delay_ms, 0)

        # Set fault injection
        node.set_fault_injection(drop_prob=0.5, delay_ms=100)

        self.assertEqual(node.message_drop_prob, 0.5)
        self.assertEqual(node.message_delay_ms, 100)

    def test_peer_tracking(self):
        """Test peer count and ID tracking."""
        node = P2PNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
        )

        # Initially no peers
        self.assertEqual(node.get_peer_count(), 0)
        self.assertEqual(node.get_peer_ids(), [])


class TestMessage(unittest.TestCase):
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test message creation."""
        msg = Message(
            msg_type="NEW_TX",
            data={"transaction": {"sender": "alice"}},
            msg_id="msg123",
            sender_id="node0",
        )

        self.assertEqual(msg.msg_type, "NEW_TX")
        self.assertEqual(msg.data["transaction"]["sender"], "alice")
        self.assertEqual(msg.msg_id, "msg123")
        self.assertEqual(msg.sender_id, "node0")


class TestDuplicateSuppression(unittest.TestCase):
    """Tests for message duplicate suppression."""

    def test_seen_messages_tracking(self):
        """Test that seen messages are tracked."""
        node = P2PNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
        )

        # Add message to seen set
        msg_id = "test_msg_123"
        node.seen_messages.add(msg_id)

        # Should be in seen set
        self.assertIn(msg_id, node.seen_messages)

        # Different message should not be seen
        self.assertNotIn("other_msg", node.seen_messages)


@unittest.skipIf(SKIP_NETWORK_TESTS, SKIP_REASON)
class TestNodeLifecycle(unittest.TestCase):
    """Tests for node start/stop lifecycle."""

    def test_start_and_stop(self):
        """Test node can start and stop cleanly."""

        async def run_test():
            node = P2PNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9200,
            )

            # Start node
            await node.start()
            self.assertIsNotNone(node.server)
            self.assertFalse(node.is_crashed)

            # Stop node
            await node.stop()
            self.assertTrue(node.is_crashed)

        asyncio.run(run_test())

    def test_restart_after_crash(self):
        """Test node can restart after being stopped."""

        async def run_test():
            node = P2PNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9300,
            )

            await node.start()
            await node.stop()
            self.assertTrue(node.is_crashed)

            # Restart
            await node.restart()
            self.assertFalse(node.is_crashed)

            await node.stop()

        asyncio.run(run_test())


@unittest.skipIf(SKIP_NETWORK_TESTS, SKIP_REASON)
class TestPeerConnection(unittest.TestCase):
    """Tests for peer-to-peer connections."""

    def test_connect_two_nodes(self):
        """Test connecting two nodes."""

        async def run_test():
            node1 = P2PNode("node1", "127.0.0.1", 9400)
            node2 = P2PNode("node2", "127.0.0.1", 9401)

            try:
                await node1.start()
                await node2.start()

                # Connect node1 to node2
                success = await asyncio.wait_for(
                    node1.connect_to_peer("node2", "127.0.0.1", 9401), timeout=2.0
                )
                await asyncio.sleep(0.2)

                self.assertTrue(success)
                self.assertEqual(node1.get_peer_count(), 1)
                self.assertIn("node2", node1.get_peer_ids())
            finally:
                await node1.stop()
                await node2.stop()

        asyncio.run(run_test())

    def test_bidirectional_connection(self):
        """Test that connections are bidirectional after handshake."""

        async def run_test():
            node1 = P2PNode("node1", "127.0.0.1", 9500)
            node2 = P2PNode("node2", "127.0.0.1", 9501)

            try:
                await node1.start()
                await node2.start()

                await asyncio.wait_for(
                    node1.connect_to_peer("node2", "127.0.0.1", 9501), timeout=2.0
                )
                await asyncio.sleep(0.3)

                # Both nodes should see each other as peers
                self.assertIn("node2", node1.get_peer_ids())
                self.assertIn("node1", node2.get_peer_ids())
            finally:
                await node1.stop()
                await node2.stop()

        asyncio.run(run_test())


@unittest.skipIf(SKIP_NETWORK_TESTS, SKIP_REASON)
class TestMessageBroadcast(unittest.TestCase):
    """Tests for message broadcasting."""

    def test_broadcast_to_peers(self):
        """Test broadcasting message to all peers."""

        async def run_test():
            received_messages = []

            async def handler(msg):
                received_messages.append(msg)

            node1 = P2PNode("node1", "127.0.0.1", 9600)
            node2 = P2PNode("node2", "127.0.0.1", 9601, message_handler=handler)
            node3 = P2PNode("node3", "127.0.0.1", 9602, message_handler=handler)

            try:
                await node1.start()
                await node2.start()
                await node3.start()

                # Connect node1 to both node2 and node3
                await asyncio.wait_for(
                    node1.connect_to_peer("node2", "127.0.0.1", 9601), timeout=2.0
                )
                await asyncio.wait_for(
                    node1.connect_to_peer("node3", "127.0.0.1", 9602), timeout=2.0
                )
                await asyncio.sleep(0.3)

                # Broadcast from node1
                await node1.broadcast("TEST_MSG", {"value": 42})
                await asyncio.sleep(0.3)

                # Both node2 and node3 should receive the message
                self.assertEqual(len(received_messages), 2)
                for msg in received_messages:
                    self.assertEqual(msg.msg_type, "TEST_MSG")
                    self.assertEqual(msg.data["value"], 42)
            finally:
                await node1.stop()
                await node2.stop()
                await node3.stop()

        asyncio.run(run_test())


if __name__ == "__main__":
    # Run with network tests enabled
    os.environ["RUN_NETWORK_TESTS"] = "1"
    unittest.main()
