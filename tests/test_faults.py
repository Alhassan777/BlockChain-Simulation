"""
Tests for fault injection module.

Note: These tests involve network operations and are skipped by default.
Run with RUN_NETWORK_TESTS=1 environment variable to include them.
"""

import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.faults import FaultInjector
from src.node import BlockchainNode
from src.block import Block

# Skip network tests by default (they can be slow/flaky)
SKIP_NETWORK_TESTS = os.environ.get("RUN_NETWORK_TESTS", "0") != "1"
SKIP_REASON = "Network tests skipped by default. Set RUN_NETWORK_TESTS=1 to run."


class TestFaultInjectorUnit(unittest.TestCase):
    """Unit tests for FaultInjector that don't require network."""

    def test_get_node_empty_list(self):
        """Test _get_node with empty node list."""
        injector = FaultInjector([])
        result = injector._get_node("nonexistent")
        self.assertIsNone(result)

    def test_set_drop_rate_nonexistent_node(self):
        """Test setting drop rate for nonexistent node."""
        injector = FaultInjector([])
        success = injector.set_message_drop_rate("nonexistent", 0.5)
        self.assertFalse(success)

    def test_set_delay_nonexistent_node(self):
        """Test setting delay for nonexistent node."""
        injector = FaultInjector([])
        success = injector.set_message_delay("nonexistent", 100)
        self.assertFalse(success)


@unittest.skipIf(SKIP_NETWORK_TESTS, SKIP_REASON)
class TestFaultInjector(unittest.TestCase):
    """Tests for the FaultInjector class with network."""

    def test_message_drop_rate(self):
        """Test setting message drop rate."""

        async def run_test():
            genesis = Block.create_genesis_block()
            node = BlockchainNode(
                node_id="node0",
                host="127.0.0.1",
                port=9990,
                difficulty=1,
                genesis_block=genesis,
            )
            try:
                await node.start()

                injector = FaultInjector([node])

                # Set drop rate
                success = injector.set_message_drop_rate("node0", 0.5)

                self.assertTrue(success)
                self.assertEqual(node.network.message_drop_prob, 0.5)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_message_delay(self):
        """Test setting message delay."""

        async def run_test():
            genesis = Block.create_genesis_block()
            node = BlockchainNode(
                node_id="node0",
                host="127.0.0.1",
                port=9991,
                difficulty=1,
                genesis_block=genesis,
            )
            try:
                await node.start()

                injector = FaultInjector([node])

                # Set delay
                success = injector.set_message_delay("node0", 100)

                self.assertTrue(success)
                self.assertEqual(node.network.message_delay_ms, 100)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_crash_node(self):
        """Test crashing a node."""

        async def run_test():
            genesis = Block.create_genesis_block()
            node = BlockchainNode(
                node_id="node0",
                host="127.0.0.1",
                port=9992,
                difficulty=1,
                genesis_block=genesis,
            )
            await node.start()

            self.assertFalse(node.network.is_crashed)

            injector = FaultInjector([node])
            success = await injector.crash_node("node0")

            self.assertTrue(success)
            self.assertTrue(node.network.is_crashed)

        asyncio.run(run_test())

    def test_restart_node(self):
        """Test restarting a crashed node."""

        async def run_test():
            genesis = Block.create_genesis_block()
            node = BlockchainNode(
                node_id="node0",
                host="127.0.0.1",
                port=9993,
                difficulty=1,
                genesis_block=genesis,
            )
            try:
                await node.start()

                injector = FaultInjector([node])

                # Crash and restart
                await injector.crash_node("node0")
                self.assertTrue(node.network.is_crashed)

                await injector.restart_node("node0")
                self.assertFalse(node.network.is_crashed)
            finally:
                await node.stop()

        asyncio.run(run_test())

    def test_invalid_transaction_injection(self):
        """Test injecting invalid transaction."""

        async def run_test():
            genesis = Block.create_genesis_block()
            node = BlockchainNode(
                node_id="node0",
                host="127.0.0.1",
                port=9994,
                difficulty=1,
                genesis_block=genesis,
            )
            try:
                await node.start()

                injector = FaultInjector([node])

                # Inject invalid transaction (insufficient balance)
                result = await injector.inject_invalid_transaction("node0")

                # Should be rejected (return False)
                self.assertFalse(result)
            finally:
                await node.stop()

        asyncio.run(run_test())


if __name__ == "__main__":
    # Run with network tests enabled
    os.environ["RUN_NETWORK_TESTS"] = "1"
    unittest.main()
