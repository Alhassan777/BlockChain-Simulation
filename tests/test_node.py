"""
Tests for the BlockchainNode class.

Note: Tests involving network operations are skipped by default.
Run with RUN_NETWORK_TESTS=1 to include them.
"""

import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.node import BlockchainNode
from src.block import Block
from src.transaction import Transaction
from src.metrics import reset_metrics

# Skip network tests by default
SKIP_NETWORK_TESTS = os.environ.get("RUN_NETWORK_TESTS", "0") != "1"
SKIP_REASON = "Network tests skipped by default. Set RUN_NETWORK_TESTS=1 to run."


class TestBlockchainNodeUnit(unittest.TestCase):
    """Unit tests for BlockchainNode that don't require network."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.genesis = Block.create_genesis_block()

    def test_node_creation(self):
        """Test basic node creation."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            block_reward=50.0,
            genesis_block=self.genesis,
        )

        self.assertEqual(node.node_id, "test_node")
        self.assertEqual(node.miner_address, "test_node")
        self.assertEqual(node.blockchain.difficulty, 2)
        self.assertEqual(node.consensus.block_reward, 50.0)
        self.assertFalse(node.is_mining)
        self.assertFalse(node.auto_mine)

    def test_node_creation_with_miner_address(self):
        """Test node creation with custom miner address."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            block_reward=50.0,
            miner_address="custom_miner",
            genesis_block=self.genesis,
        )

        self.assertEqual(node.node_id, "test_node")
        self.assertEqual(node.miner_address, "custom_miner")

    def test_node_has_genesis_block(self):
        """Test node starts with genesis block."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            genesis_block=self.genesis,
        )

        self.assertEqual(node.blockchain.get_chain_length(), 1)
        self.assertEqual(node.blockchain.chain[0].index, 0)

    def test_enable_auto_mining(self):
        """Test enabling auto-mining."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            genesis_block=self.genesis,
        )

        self.assertFalse(node.auto_mine)

        node.enable_auto_mining(min_transactions=5)

        self.assertTrue(node.auto_mine)
        self.assertEqual(node.min_transactions_to_mine, 5)

    def test_disable_auto_mining(self):
        """Test disabling auto-mining."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            genesis_block=self.genesis,
        )

        node.enable_auto_mining()
        self.assertTrue(node.auto_mine)

        node.disable_auto_mining()
        self.assertFalse(node.auto_mine)

    def test_get_status(self):
        """Test get_status returns expected fields."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            genesis_block=self.genesis,
        )

        status = node.get_status()

        self.assertIn("node_id", status)
        self.assertIn("chain_length", status)
        self.assertIn("chain_tip", status)
        self.assertIn("mempool_size", status)
        self.assertIn("balance", status)
        self.assertIn("is_mining", status)
        self.assertIn("peers", status)
        self.assertIn("peer_count", status)

        self.assertEqual(status["node_id"], "test_node")
        self.assertEqual(status["chain_length"], 1)
        self.assertEqual(status["mempool_size"], 0)
        self.assertFalse(status["is_mining"])
        self.assertEqual(status["peer_count"], 0)

    def test_mempool_initially_empty(self):
        """Test mempool is empty on creation."""
        node = BlockchainNode(
            node_id="test_node",
            host="127.0.0.1",
            port=9000,
            difficulty=2,
            genesis_block=self.genesis,
        )

        self.assertEqual(node.mempool.size(), 0)

    def test_shared_genesis_block(self):
        """Test that nodes can share the same genesis block."""
        node1 = BlockchainNode(
            node_id="node1",
            host="127.0.0.1",
            port=9001,
            difficulty=2,
            genesis_block=self.genesis,
        )

        node2 = BlockchainNode(
            node_id="node2",
            host="127.0.0.1",
            port=9002,
            difficulty=2,
            genesis_block=self.genesis,
        )

        # Both nodes should have the same genesis hash
        self.assertEqual(node1.blockchain.chain[0].hash, node2.blockchain.chain[0].hash)


@unittest.skipIf(SKIP_NETWORK_TESTS, SKIP_REASON)
class TestBlockchainNodeNetwork(unittest.TestCase):
    """Integration tests for BlockchainNode with networking."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.genesis = Block.create_genesis_block()

    def test_start_and_stop(self):
        """Test node can start and stop."""

        async def run_test():
            node = BlockchainNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9100,
                difficulty=2,
                genesis_block=self.genesis,
            )

            await node.start()
            self.assertIsNotNone(node.network.server)

            await node.stop()
            self.assertTrue(node.network.is_crashed)

        asyncio.run(run_test())

    def test_connect_to_peer(self):
        """Test connecting to a peer node."""

        async def run_test():
            node1 = BlockchainNode(
                node_id="node1",
                host="127.0.0.1",
                port=9200,
                difficulty=2,
                genesis_block=self.genesis,
            )
            node2 = BlockchainNode(
                node_id="node2",
                host="127.0.0.1",
                port=9201,
                difficulty=2,
                genesis_block=self.genesis,
            )

            try:
                await node1.start()
                await node2.start()

                success = await asyncio.wait_for(
                    node1.connect_to_peer("node2", "127.0.0.1", 9201), timeout=2.0
                )
                await asyncio.sleep(0.2)

                self.assertTrue(success)
                self.assertIn("node2", node1.network.get_peer_ids())
            finally:
                await node1.stop()
                await node2.stop()

        asyncio.run(run_test())

    def test_mine_block(self):
        """Test mining a block."""

        async def run_test():
            node = BlockchainNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9300,
                difficulty=1,  # Low difficulty for fast test
                genesis_block=self.genesis,
            )

            try:
                await node.start()

                # Mine a block
                block = await node.mine_next_block(max_iterations=10000)

                self.assertIsNotNone(block)
                self.assertEqual(block.index, 1)
                self.assertEqual(node.blockchain.get_chain_length(), 2)
                # Miner should have received block reward
                self.assertEqual(node.blockchain.get_balance("test_node"), 50.0)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_submit_transaction(self):
        """Test submitting a transaction."""

        async def run_test():
            node = BlockchainNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9400,
                difficulty=1,
                genesis_block=self.genesis,
            )

            try:
                await node.start()

                # First mine a block to get coins
                await node.mine_next_block(max_iterations=10000)

                # Create and submit transaction
                tx = Transaction(
                    sender="test_node",
                    receiver="bob",
                    amount=10.0,
                    fee=0.5,
                    nonce=0,
                )
                tx.sign("test_node")

                success = await node.submit_transaction(tx)

                self.assertTrue(success)
                self.assertEqual(node.mempool.size(), 1)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_reject_invalid_transaction(self):
        """Test that invalid transactions are rejected."""

        async def run_test():
            node = BlockchainNode(
                node_id="test_node",
                host="127.0.0.1",
                port=9500,
                difficulty=1,
                genesis_block=self.genesis,
            )

            try:
                await node.start()

                # Try to submit transaction without sufficient balance
                tx = Transaction(
                    sender="test_node",
                    receiver="bob",
                    amount=1000000.0,  # More than balance
                    fee=0.5,
                    nonce=0,
                )
                tx.sign("test_node")

                success = await node.submit_transaction(tx)

                self.assertFalse(success)
                self.assertEqual(node.mempool.size(), 0)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_transaction_propagation(self):
        """Test transaction propagates between connected nodes."""

        async def run_test():
            node1 = BlockchainNode(
                node_id="node1",
                host="127.0.0.1",
                port=9600,
                difficulty=1,
                genesis_block=self.genesis,
            )
            node2 = BlockchainNode(
                node_id="node2",
                host="127.0.0.1",
                port=9601,
                difficulty=1,
                genesis_block=self.genesis,
            )

            try:
                await node1.start()
                await node2.start()
                await node1.connect_to_peer("node2", "127.0.0.1", 9601)
                await asyncio.sleep(0.2)

                # Mine block on node1 to get coins
                await node1.mine_next_block(max_iterations=10000)
                await asyncio.sleep(0.2)

                # Submit transaction from node1
                tx = Transaction(
                    sender="node1",
                    receiver="bob",
                    amount=10.0,
                    fee=0.5,
                    nonce=0,
                )
                tx.sign("node1")
                await node1.submit_transaction(tx)
                await asyncio.sleep(0.3)

                # Transaction should propagate to node2
                self.assertEqual(node2.mempool.size(), 1)
            finally:
                await node1.stop()
                await node2.stop()

        asyncio.run(run_test())

    def test_block_propagation(self):
        """Test block propagates between connected nodes."""

        async def run_test():
            node1 = BlockchainNode(
                node_id="node1",
                host="127.0.0.1",
                port=9700,
                difficulty=1,
                genesis_block=self.genesis,
            )
            node2 = BlockchainNode(
                node_id="node2",
                host="127.0.0.1",
                port=9701,
                difficulty=1,
                genesis_block=self.genesis,
            )

            try:
                await node1.start()
                await node2.start()
                await node1.connect_to_peer("node2", "127.0.0.1", 9701)
                await asyncio.sleep(0.2)

                # Mine block on node1
                block = await node1.mine_next_block(max_iterations=10000)
                await asyncio.sleep(0.3)

                # Block should propagate to node2
                self.assertEqual(node2.blockchain.get_chain_length(), 2)
                self.assertEqual(node2.blockchain.get_latest_block().hash, block.hash)
            finally:
                await node1.stop()
                await node2.stop()

        asyncio.run(run_test())


if __name__ == "__main__":
    # Run with network tests enabled
    os.environ["RUN_NETWORK_TESTS"] = "1"
    unittest.main()
