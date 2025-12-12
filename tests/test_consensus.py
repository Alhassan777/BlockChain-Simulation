"""
Tests for consensus mechanisms (Proof-of-Work and Leader-based).
"""

import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.consensus import ProofOfWork, SimpleLeaderConsensus
from src.block import Block
from src.transaction import Transaction


class TestProofOfWork(unittest.TestCase):
    """Tests for Proof-of-Work consensus."""

    def test_mine_block_success(self):
        """Test successful block mining."""
        pow = ProofOfWork(node_id="node0", difficulty=2, block_reward=50.0)

        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            difficulty=2,
        )

        success = pow.mine_block(block, max_iterations=100000)

        self.assertTrue(success)
        self.assertTrue(block.is_valid_proof())
        self.assertTrue(block.hash.startswith("00"))

    def test_mine_block_respects_difficulty(self):
        """Test that mining respects difficulty setting."""
        # Higher difficulty = more leading zeros
        pow = ProofOfWork(node_id="node0", difficulty=3, block_reward=50.0)

        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            difficulty=3,
        )

        success = pow.mine_block(block, max_iterations=500000)

        if success:
            self.assertTrue(block.hash.startswith("000"))

    def test_create_block_with_coinbase(self):
        """Test block creation includes coinbase transaction."""
        pow = ProofOfWork(node_id="node0", difficulty=2, block_reward=50.0)

        # Create some regular transactions
        tx1 = Transaction(
            sender="alice",
            receiver="bob",
            amount=10.0,
            fee=0.5,
            nonce=0,
        )
        tx1.sign("alice")

        block = pow.create_block(
            index=1,
            transactions=[tx1],
            previous_hash="0" * 64,
            miner_address="miner_wallet",
        )

        # First transaction should be coinbase
        self.assertEqual(block.transactions[0].sender, "COINBASE")
        self.assertEqual(block.transactions[0].receiver, "miner_wallet")
        # Coinbase should include block reward + fees
        self.assertEqual(block.transactions[0].amount, 50.0 + 0.5)

    def test_max_iterations_stops_mining(self):
        """Test that mining stops after max iterations."""
        pow = ProofOfWork(node_id="node0", difficulty=10, block_reward=50.0)

        coinbase = Transaction.create_coinbase("miner", 50.0)
        block = Block(
            index=1,
            transactions=[coinbase],
            previous_hash="0" * 64,
            difficulty=10,  # Very high difficulty
        )

        # Should fail to find valid hash in 100 iterations
        success = pow.mine_block(block, max_iterations=100)

        self.assertFalse(success)

    def test_difficulty_adjustment_increase(self):
        """Test difficulty increases when blocks are mined too fast."""
        pow = ProofOfWork(
            node_id="node0",
            difficulty=2,
            target_block_time=10.0,
            adjustment_interval=3,
            enable_adjustment=True,
        )

        # Record very fast block times (much faster than target)
        for _ in range(5):
            pow.record_block_time(0.1)  # Very fast

        # Difficulty should have increased
        self.assertGreater(pow.difficulty, 2)

    def test_difficulty_adjustment_decrease(self):
        """Test difficulty decreases when blocks are mined too slow."""
        pow = ProofOfWork(
            node_id="node0",
            difficulty=4,
            target_block_time=1.0,
            adjustment_interval=3,
            enable_adjustment=True,
        )

        # Record very slow block times
        for _ in range(5):
            pow.record_block_time(100.0)  # Very slow

        # Difficulty should have decreased
        self.assertLess(pow.difficulty, 4)

    def test_difficulty_bounds(self):
        """Test difficulty stays within min/max bounds."""
        pow = ProofOfWork(
            node_id="node0",
            difficulty=1,
            target_block_time=10.0,
            adjustment_interval=3,
            enable_adjustment=True,
        )
        pow.min_difficulty = 1
        pow.max_difficulty = 8

        # Try to decrease below minimum
        for _ in range(10):
            pow.record_block_time(1000.0)

        self.assertGreaterEqual(pow.difficulty, pow.min_difficulty)

        # Reset and try to increase above maximum
        pow.difficulty = 8
        pow.recent_block_times.clear()
        for _ in range(10):
            pow.record_block_time(0.001)

        self.assertLessEqual(pow.difficulty, pow.max_difficulty)

    def test_get_difficulty_stats(self):
        """Test difficulty statistics retrieval."""
        pow = ProofOfWork(
            node_id="node0",
            difficulty=3,
            target_block_time=10.0,
            adjustment_interval=5,
            enable_adjustment=True,
        )

        pow.record_block_time(8.0)
        pow.record_block_time(12.0)

        stats = pow.get_difficulty_stats()

        self.assertEqual(stats["current_difficulty"], 3)
        self.assertEqual(stats["target_block_time"], 10.0)
        self.assertAlmostEqual(stats["average_block_time"], 10.0, places=1)
        self.assertTrue(stats["adjustment_enabled"])


class TestSimpleLeaderConsensus(unittest.TestCase):
    """Tests for simple leader-based consensus."""

    def test_leader_selection(self):
        """Test round-robin leader selection."""
        all_nodes = ["node0", "node1", "node2"]
        consensus = SimpleLeaderConsensus(
            node_id="node0",
            all_node_ids=all_nodes,
            block_reward=50.0,
        )

        # Round 0 -> node0
        self.assertEqual(consensus.get_leader(0), "node0")
        self.assertTrue(consensus.is_leader(0))

        # Round 1 -> node1
        self.assertEqual(consensus.get_leader(1), "node1")
        self.assertFalse(consensus.is_leader(1))

        # Round 2 -> node2
        self.assertEqual(consensus.get_leader(2), "node2")
        self.assertFalse(consensus.is_leader(2))

        # Round 3 -> back to node0
        self.assertEqual(consensus.get_leader(3), "node0")
        self.assertTrue(consensus.is_leader(3))

    def test_advance_round(self):
        """Test round advancement."""
        consensus = SimpleLeaderConsensus(
            node_id="node0",
            all_node_ids=["node0", "node1", "node2"],
            block_reward=50.0,
        )

        self.assertEqual(consensus.current_round, 0)

        consensus.advance_round()
        self.assertEqual(consensus.current_round, 1)

        consensus.advance_round()
        self.assertEqual(consensus.current_round, 2)

    def test_leader_creates_block(self):
        """Test leader can create a valid block."""
        consensus = SimpleLeaderConsensus(
            node_id="node0",
            all_node_ids=["node0", "node1"],
            block_reward=50.0,
        )

        tx = Transaction(
            sender="alice",
            receiver="bob",
            amount=10.0,
            fee=0.5,
            nonce=0,
        )
        tx.sign("alice")

        block = consensus.create_block(
            index=1,
            transactions=[tx],
            previous_hash="0" * 64,
            miner_address="leader_wallet",
        )

        # Block should be valid (mined with difficulty 1)
        self.assertTrue(block.is_valid_proof())
        self.assertEqual(block.transactions[0].sender, "COINBASE")
        self.assertEqual(block.transactions[0].amount, 50.0 + 0.5)  # reward + fees

    def test_deterministic_leader_order(self):
        """Test that leader order is deterministic regardless of node."""
        nodes = ["nodeC", "nodeA", "nodeB"]  # Unsorted order

        consensus1 = SimpleLeaderConsensus("nodeA", nodes.copy(), 50.0)
        consensus2 = SimpleLeaderConsensus("nodeB", nodes.copy(), 50.0)
        consensus3 = SimpleLeaderConsensus("nodeC", nodes.copy(), 50.0)

        # All should agree on leader for each round
        for round_num in range(10):
            leader1 = consensus1.get_leader(round_num)
            leader2 = consensus2.get_leader(round_num)
            leader3 = consensus3.get_leader(round_num)

            self.assertEqual(leader1, leader2)
            self.assertEqual(leader2, leader3)


class TestAsyncMining(unittest.TestCase):
    """Tests for async mining functionality."""

    def test_async_mining_success(self):
        """Test async mining completes successfully."""

        async def run_test():
            pow = ProofOfWork(node_id="node0", difficulty=2, block_reward=50.0)

            coinbase = Transaction.create_coinbase("miner", 50.0)
            block = Block(
                index=1,
                transactions=[coinbase],
                previous_hash="0" * 64,
                difficulty=2,
            )

            success = await pow.mine_block_async(block, max_iterations=100000)

            self.assertTrue(success)
            self.assertTrue(block.is_valid_proof())

        asyncio.run(run_test())

    def test_async_mining_stop_event(self):
        """Test async mining can be stopped via event."""

        async def run_test():
            pow = ProofOfWork(node_id="node0", difficulty=10, block_reward=50.0)
            stop_event = asyncio.Event()

            coinbase = Transaction.create_coinbase("miner", 50.0)
            block = Block(
                index=1,
                transactions=[coinbase],
                previous_hash="0" * 64,
                difficulty=10,  # High difficulty
            )

            # Set stop event after a short delay
            async def stop_after_delay():
                await asyncio.sleep(0.1)
                stop_event.set()

            asyncio.create_task(stop_after_delay())

            success = await pow.mine_block_async(
                block, max_iterations=10000000, stop_event=stop_event
            )

            self.assertFalse(success)  # Should have been stopped

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
