"""
Consensus module implementing Proof-of-Work mining.
"""

import asyncio
import logging
import time
from typing import Optional, Callable
from src.block import Block
from src.transaction import Transaction


class ProofOfWork:
    """Implements simulated Proof-of-Work consensus."""

    def __init__(
        self,
        node_id: str,
        difficulty: int = 2,
        block_reward: float = 50.0,
        target_block_time: float = 10.0,  # Target time between blocks (seconds)
        adjustment_interval: int = 10,  # Adjust difficulty every N blocks
        enable_adjustment: bool = False,  # Whether to auto-adjust difficulty
    ):
        self.node_id = node_id
        self.difficulty = difficulty
        self.block_reward = block_reward
        self.is_mining = False
        self.logger = logging.getLogger(f"PoW-{node_id}")

        # Difficulty adjustment settings
        self.target_block_time = target_block_time
        self.adjustment_interval = adjustment_interval
        self.enable_adjustment = enable_adjustment
        self.min_difficulty = 1
        self.max_difficulty = 8

        # Track block times for adjustment
        self.recent_block_times: list[float] = []

    def mine_block(
        self,
        block: Block,
        max_iterations: Optional[int] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> bool:
        """
        Mine a block by finding a valid nonce.

        Args:
            block: Block to mine
            max_iterations: Maximum iterations before giving up
            stop_event: Event to signal mining should stop

        Returns:
            True if valid nonce found, False otherwise
        """
        iteration = 0
        start_time = time.time()

        while not block.is_valid_proof():
            # Check if we should stop
            if stop_event and stop_event.is_set():
                return False

            block.nonce += 1
            block._hash = None  # Force recomputation
            iteration += 1

            if max_iterations and iteration >= max_iterations:
                return False

            # Periodic logging
            if iteration % 10000 == 0:
                self.logger.debug(
                    f"Mining... iteration {iteration}, nonce={block.nonce}"
                )

        elapsed = time.time() - start_time
        self.logger.info(
            f"Block mined! Hash: {block.hash[:16]}..., "
            f"Nonce: {block.nonce}, Time: {elapsed:.2f}s, "
            f"Iterations: {iteration}"
        )

        return True

    async def mine_block_async(
        self,
        block: Block,
        max_iterations: Optional[int] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> bool:
        """
        Mine a block asynchronously (yields control periodically).

        Args:
            block: Block to mine
            max_iterations: Maximum iterations before giving up
            stop_event: Event to signal mining should stop

        Returns:
            True if valid nonce found, False otherwise
        """
        iteration = 0
        start_time = time.time()

        while not block.is_valid_proof():
            # Check if we should stop
            if stop_event and stop_event.is_set():
                self.logger.info(
                    f"Mining stopped by external signal after {iteration} iterations"
                )
                return False

            block.nonce += 1
            block._hash = None  # Force recomputation
            iteration += 1

            if max_iterations and iteration >= max_iterations:
                return False

            # Yield control every 1000 iterations
            if iteration % 1000 == 0:
                await asyncio.sleep(0)
                self.logger.debug(
                    f"Mining... iteration {iteration}, nonce={block.nonce}"
                )

        elapsed = time.time() - start_time
        self.logger.info(
            f"Block mined! Hash: {block.hash[:16]}..., "
            f"Nonce: {block.nonce}, Time: {elapsed:.2f}s, "
            f"Iterations: {iteration}"
        )

        return True

    def create_block(
        self,
        index: int,
        transactions: list[Transaction],
        previous_hash: str,
        miner_address: str,
    ) -> Block:
        """
        Create a new block with coinbase transaction.

        Args:
            index: Block index
            transactions: List of transactions (excluding coinbase)
            previous_hash: Hash of previous block
            miner_address: Address to receive mining reward

        Returns:
            New unmined block
        """
        # Calculate total fees
        total_fees = sum(tx.fee for tx in transactions)

        # Create coinbase transaction
        coinbase = Transaction.create_coinbase(
            miner=miner_address, reward=self.block_reward + total_fees
        )

        # Create block with coinbase as first transaction
        all_transactions = [coinbase] + transactions

        block = Block(
            index=index,
            transactions=all_transactions,
            previous_hash=previous_hash,
            difficulty=self.difficulty,
        )

        return block

    def record_block_time(self, block_time: float) -> None:
        """
        Record a block mining time for difficulty adjustment.

        Args:
            block_time: Time taken to mine the block (seconds)
        """
        self.recent_block_times.append(block_time)

        # Keep only recent blocks for adjustment calculation
        if len(self.recent_block_times) > self.adjustment_interval * 2:
            self.recent_block_times = self.recent_block_times[
                -self.adjustment_interval :
            ]

        # Adjust difficulty if enabled and enough data
        if (
            self.enable_adjustment
            and len(self.recent_block_times) >= self.adjustment_interval
        ):
            self.adjust_difficulty()

    def adjust_difficulty(self) -> int:
        """
        Adjust mining difficulty based on recent block times.

        Returns:
            New difficulty level
        """
        if len(self.recent_block_times) < self.adjustment_interval:
            return self.difficulty

        # Calculate average block time from recent blocks
        recent_times = self.recent_block_times[-self.adjustment_interval :]
        avg_block_time = sum(recent_times) / len(recent_times)

        old_difficulty = self.difficulty

        # Adjust difficulty based on how far we are from target
        ratio = avg_block_time / self.target_block_time

        if ratio < 0.5:
            # Blocks coming too fast, increase difficulty
            self.difficulty = min(self.difficulty + 1, self.max_difficulty)
        elif ratio > 2.0:
            # Blocks coming too slow, decrease difficulty
            self.difficulty = max(self.difficulty - 1, self.min_difficulty)

        if self.difficulty != old_difficulty:
            self.logger.info(
                f"Difficulty adjusted: {old_difficulty} -> {self.difficulty} "
                f"(avg block time: {avg_block_time:.2f}s, target: {self.target_block_time:.2f}s)"
            )

        return self.difficulty

    def get_difficulty_stats(self) -> dict:
        """Get current difficulty statistics."""
        avg_time = 0.0
        if self.recent_block_times:
            avg_time = sum(self.recent_block_times) / len(self.recent_block_times)

        return {
            "current_difficulty": self.difficulty,
            "target_block_time": self.target_block_time,
            "average_block_time": avg_time,
            "blocks_until_adjustment": max(
                0, self.adjustment_interval - len(self.recent_block_times)
            ),
            "adjustment_enabled": self.enable_adjustment,
        }


class SimpleLeaderConsensus:
    """
    Simple round-robin leader-based consensus (alternative to PoW).
    Each node takes turns being the leader who proposes blocks.
    """

    def __init__(
        self, node_id: str, all_node_ids: list[str], block_reward: float = 50.0
    ):
        self.node_id = node_id
        self.all_node_ids = sorted(all_node_ids)  # Deterministic ordering
        self.block_reward = block_reward
        self.current_round = 0
        self.logger = logging.getLogger(f"Leader-{node_id}")

    def is_leader(self, round_number: Optional[int] = None) -> bool:
        """Check if this node is the leader for given round."""
        if round_number is None:
            round_number = self.current_round

        leader_index = round_number % len(self.all_node_ids)
        leader_id = self.all_node_ids[leader_index]
        return leader_id == self.node_id

    def get_leader(self, round_number: Optional[int] = None) -> str:
        """Get the leader node ID for given round."""
        if round_number is None:
            round_number = self.current_round

        leader_index = round_number % len(self.all_node_ids)
        return self.all_node_ids[leader_index]

    def advance_round(self) -> None:
        """Move to next round."""
        self.current_round += 1

    def create_block(
        self,
        index: int,
        transactions: list[Transaction],
        previous_hash: str,
        miner_address: str,
    ) -> Block:
        """Create a new block (no mining needed)."""
        # Calculate total fees
        total_fees = sum(tx.fee for tx in transactions)

        # Create coinbase transaction
        coinbase = Transaction.create_coinbase(
            miner=miner_address, reward=self.block_reward + total_fees
        )

        # Create block with minimal difficulty
        all_transactions = [coinbase] + transactions

        block = Block(
            index=index,
            transactions=all_transactions,
            previous_hash=previous_hash,
            difficulty=1,  # Minimal difficulty for leader-based
        )

        # "Mine" the block (trivial with difficulty 1)
        block.mine()

        return block
