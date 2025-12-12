"""
Tests for orphan block tracking functionality.
"""

import unittest
from src.block import Block
from src.blockchain import Blockchain
from src.transaction import Transaction
from src.metrics import MetricsCollector, reset_metrics, get_metrics_collector


class TestOrphanTracking(unittest.TestCase):
    """Tests for orphan block detection and tracking."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.metrics = get_metrics_collector()

    def tearDown(self):
        """Clean up after tests."""
        reset_metrics()

    def create_chain_with_blocks(
        self, num_blocks: int, difficulty: int = 1
    ) -> Blockchain:
        """Helper to create a blockchain with specified number of blocks."""
        blockchain = Blockchain(difficulty=difficulty)

        for i in range(num_blocks):
            coinbase = Transaction.create_coinbase(f"miner{i}", 50.0)
            block = Block(
                index=blockchain.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain.get_latest_block().hash,
                difficulty=difficulty,
            )
            block.mine(max_iterations=100000)
            blockchain.add_block(block)

        return blockchain

    def test_no_orphans_in_normal_chain(self):
        """Test that no orphans are recorded in a linear chain."""
        blockchain = self.create_chain_with_blocks(5)

        self.assertEqual(blockchain.get_chain_length(), 6)  # Genesis + 5
        self.assertEqual(self.metrics.total_orphans, 0)

    def test_orphan_recorded_on_chain_replacement(self):
        """Test that orphans are recorded when chain is replaced."""
        # Create two blockchains with same genesis
        genesis = Block.create_genesis_block()
        blockchain1 = Blockchain(difficulty=1, genesis_block=genesis)
        blockchain2 = Blockchain(difficulty=1, genesis_block=genesis)

        # Add 2 blocks to blockchain1
        for i in range(2):
            coinbase = Transaction.create_coinbase(f"miner_a{i}", 50.0)
            block = Block(
                index=blockchain1.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain1.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=100000)
            blockchain1.add_block(block)
            self.metrics.record_block_mined(block.hash, block.index, "miner_a", 1, 0.01)

        # Add 1 block to blockchain2 (different block at same height)
        coinbase = Transaction.create_coinbase("miner_b0", 50.0)
        block_b = Block(
            index=blockchain2.get_chain_length(),
            transactions=[coinbase],
            previous_hash=blockchain2.get_latest_block().hash,
            difficulty=1,
        )
        block_b.mine(max_iterations=100000)
        blockchain2.add_block(block_b)
        self.metrics.record_block_mined(block_b.hash, block_b.index, "miner_b", 1, 0.01)

        # blockchain1 has 3 blocks (genesis + 2)
        # blockchain2 has 2 blocks (genesis + 1)
        self.assertEqual(blockchain1.get_chain_length(), 3)
        self.assertEqual(blockchain2.get_chain_length(), 2)

        # Replace blockchain2's chain with blockchain1's longer chain
        replaced, _ = blockchain2.replace_chain(blockchain1.chain)

        self.assertTrue(replaced)
        self.assertEqual(blockchain2.get_chain_length(), 3)

        # The block from blockchain2 (block_b) should be orphaned
        self.assertEqual(self.metrics.total_orphans, 1)

    def test_multiple_orphans_recorded(self):
        """Test that multiple orphans are recorded when chain diverges significantly."""
        genesis = Block.create_genesis_block()
        blockchain1 = Blockchain(difficulty=1, genesis_block=genesis)
        blockchain2 = Blockchain(difficulty=1, genesis_block=genesis)

        # Add 3 blocks to blockchain1 (longer chain)
        for i in range(3):
            coinbase = Transaction.create_coinbase(f"miner_a{i}", 50.0)
            block = Block(
                index=blockchain1.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain1.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=100000)
            blockchain1.add_block(block)

        # Add 2 blocks to blockchain2 (shorter chain, will be orphaned)
        for i in range(2):
            coinbase = Transaction.create_coinbase(f"miner_b{i}", 50.0)
            block = Block(
                index=blockchain2.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain2.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=100000)
            blockchain2.add_block(block)
            self.metrics.record_block_mined(block.hash, block.index, "miner_b", 1, 0.01)

        # Replace blockchain2's chain with blockchain1's longer chain
        replaced, _ = blockchain2.replace_chain(blockchain1.chain)

        self.assertTrue(replaced)
        # Both blocks from blockchain2 should be orphaned
        self.assertEqual(self.metrics.total_orphans, 2)

    def test_orphan_rate_calculation(self):
        """Test orphan rate is calculated correctly."""
        genesis = Block.create_genesis_block()
        blockchain1 = Blockchain(difficulty=1, genesis_block=genesis)
        blockchain2 = Blockchain(difficulty=1, genesis_block=genesis)

        # Record 10 blocks mined
        for i in range(10):
            coinbase = Transaction.create_coinbase(f"miner{i}", 50.0)
            block = Block(
                index=blockchain1.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain1.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=100000)
            blockchain1.add_block(block)
            self.metrics.record_block_mined(
                block.hash, block.index, f"miner{i}", 1, 0.01
            )

        # Add 1 block to blockchain2 that will be orphaned
        coinbase = Transaction.create_coinbase("orphan_miner", 50.0)
        orphan_block = Block(
            index=1, transactions=[coinbase], previous_hash=genesis.hash, difficulty=1
        )
        orphan_block.mine(max_iterations=100000)
        blockchain2.add_block(orphan_block)
        self.metrics.record_block_mined(
            orphan_block.hash, orphan_block.index, "orphan_miner", 1, 0.01
        )

        # Replace chain - orphan block will be marked
        blockchain2.replace_chain(blockchain1.chain)

        # Calculate orphan rate: 1 orphan out of 11 total blocks = ~9.09%
        orphan_rate = self.metrics.get_orphan_rate()
        self.assertEqual(self.metrics.total_orphans, 1)
        self.assertAlmostEqual(orphan_rate, (1 / 11) * 100, places=2)

    def test_no_replacement_if_chain_not_longer(self):
        """Test that chain is not replaced if new chain is not longer."""
        blockchain = self.create_chain_with_blocks(5)

        # Try to replace with shorter chain
        short_chain = blockchain.chain[:3]
        replaced, error = blockchain.replace_chain(short_chain)

        self.assertFalse(replaced)
        self.assertEqual(error, "New chain is not longer")
        self.assertEqual(self.metrics.total_orphans, 0)

    def test_genesis_never_orphaned(self):
        """Test that genesis block is never marked as orphaned."""
        genesis = Block.create_genesis_block()
        blockchain1 = Blockchain(difficulty=1, genesis_block=genesis)
        blockchain2 = Blockchain(difficulty=1, genesis_block=genesis)

        # Add blocks to make blockchain1 longer
        for i in range(3):
            coinbase = Transaction.create_coinbase(f"miner{i}", 50.0)
            block = Block(
                index=blockchain1.get_chain_length(),
                transactions=[coinbase],
                previous_hash=blockchain1.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=100000)
            blockchain1.add_block(block)

        # Replace blockchain2 with blockchain1
        blockchain2.replace_chain(blockchain1.chain)

        # Genesis should not be orphaned (only index > 0 blocks)
        for block_hash in self.metrics.orphan_blocks:
            block = self.metrics.blocks.get(block_hash)
            if block:
                self.assertNotEqual(block.block_index, 0)


if __name__ == "__main__":
    unittest.main()

