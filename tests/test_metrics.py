"""
Tests for metrics collection system.
"""

import pytest
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metrics import MetricsCollector, get_metrics_collector, reset_metrics


class TestMetricsCollector:
    """Test cases for MetricsCollector class."""
    
    def setup_method(self):
        """Setup fresh metrics collector for each test."""
        self.metrics = MetricsCollector()
    
    def test_record_block_mined(self):
        """Test recording a mined block."""
        self.metrics.record_block_mined(
            block_hash="abc123",
            block_index=1,
            miner_id="node0",
            transaction_count=5,
            mining_duration=1.5
        )
        
        assert self.metrics.total_blocks_mined == 1
        assert "abc123" in self.metrics.blocks
        assert self.metrics.blocks["abc123"].miner_id == "node0"
        assert self.metrics.blocks["abc123"].mining_duration == 1.5
    
    def test_record_block_received(self):
        """Test recording block reception by nodes."""
        # First, mine a block
        self.metrics.record_block_mined(
            block_hash="abc123",
            block_index=1,
            miner_id="node0",
            transaction_count=5,
            mining_duration=1.5
        )
        
        # Record reception by other nodes
        self.metrics.record_block_received("abc123", "node1")
        self.metrics.record_block_received("abc123", "node2")
        
        assert len(self.metrics.blocks["abc123"].propagation_times) == 3
        assert "node1" in self.metrics.blocks["abc123"].propagation_times
        assert "node2" in self.metrics.blocks["abc123"].propagation_times
    
    def test_record_transaction(self):
        """Test recording transaction submission and reception."""
        self.metrics.record_transaction_submitted("tx123", "node0")
        
        assert self.metrics.total_transactions_processed == 1
        assert "tx123" in self.metrics.transactions
        
        # Record reception
        self.metrics.record_transaction_received("tx123", "node1")
        assert "node1" in self.metrics.transactions["tx123"].propagation_times
    
    def test_record_transaction_confirmed(self):
        """Test recording transaction confirmation."""
        self.metrics.record_transaction_submitted("tx123", "node0")
        time.sleep(0.1)
        self.metrics.record_transaction_confirmed("tx123", block_index=5)
        
        assert self.metrics.transactions["tx123"].confirmed_block_index == 5
        assert self.metrics.transactions["tx123"].confirmation_time is not None
    
    def test_orphan_tracking(self):
        """Test orphan block tracking."""
        self.metrics.record_block_mined(
            block_hash="orphan1",
            block_index=1,
            miner_id="node0",
            transaction_count=1,
            mining_duration=0.5
        )
        
        self.metrics.record_block_orphaned("orphan1")
        
        assert self.metrics.total_orphans == 1
        assert self.metrics.blocks["orphan1"].is_orphan
        assert "orphan1" in self.metrics.orphan_blocks
    
    def test_calculate_tps(self):
        """Test TPS calculation."""
        # Submit several transactions
        for i in range(10):
            self.metrics.record_transaction_submitted(f"tx{i}", "node0")
        
        time.sleep(1.1)  # Wait for at least 1 second
        
        tps = self.metrics.calculate_tps()
        assert tps > 0  # Should have some TPS
    
    def test_average_block_time(self):
        """Test average block time calculation."""
        # Mine several blocks with delays
        for i in range(3):
            self.metrics.record_block_mined(
                block_hash=f"block{i}",
                block_index=i,
                miner_id="node0",
                transaction_count=1,
                mining_duration=0.1
            )
            time.sleep(0.2)
        
        avg_time = self.metrics.get_average_block_time()
        assert avg_time > 0
    
    def test_propagation_delay(self):
        """Test propagation delay calculation."""
        self.metrics.record_block_mined(
            block_hash="block1",
            block_index=1,
            miner_id="node0",
            transaction_count=1,
            mining_duration=0.1
        )
        
        time.sleep(0.05)
        self.metrics.record_block_received("block1", "node1")
        
        time.sleep(0.05)
        self.metrics.record_block_received("block1", "node2")
        
        delay = self.metrics.get_block_propagation_delay("block1")
        
        assert delay is not None
        assert delay['min'] > 0
        assert delay['max'] >= delay['min']
        assert delay['nodes_reached'] == 3
    
    def test_orphan_rate(self):
        """Test orphan rate calculation."""
        # Mine 10 blocks, 2 orphaned
        for i in range(10):
            self.metrics.record_block_mined(
                block_hash=f"block{i}",
                block_index=i,
                miner_id="node0",
                transaction_count=1,
                mining_duration=0.1
            )
        
        self.metrics.record_block_orphaned("block3")
        self.metrics.record_block_orphaned("block7")
        
        orphan_rate = self.metrics.get_orphan_rate()
        assert orphan_rate == 20.0  # 2/10 = 20%
    
    def test_get_summary(self):
        """Test summary generation."""
        # Add some data
        self.metrics.record_block_mined(
            block_hash="block1",
            block_index=1,
            miner_id="node0",
            transaction_count=5,
            mining_duration=0.5
        )
        self.metrics.record_transaction_submitted("tx1", "node0")
        
        summary = self.metrics.get_summary()
        
        assert 'runtime_seconds' in summary
        assert 'total_blocks' in summary
        assert 'total_transactions' in summary
        assert 'current_tps' in summary
        assert 'orphan_rate_percent' in summary
        
        assert summary['total_blocks'] == 1
        assert summary['total_transactions'] == 1
    
    def test_recent_blocks_summary(self):
        """Test recent blocks summary."""
        for i in range(5):
            self.metrics.record_block_mined(
                block_hash=f"block{i}",
                block_index=i,
                miner_id=f"node{i % 3}",
                transaction_count=i + 1,
                mining_duration=0.1 * (i + 1)
            )
        
        recent = self.metrics.get_recent_blocks_summary(count=3)
        
        assert len(recent) == 3
        assert recent[0]['index'] == 4  # Most recent first
    
    def test_reset(self):
        """Test metrics reset."""
        self.metrics.record_block_mined(
            block_hash="block1",
            block_index=1,
            miner_id="node0",
            transaction_count=1,
            mining_duration=0.1
        )
        self.metrics.record_transaction_submitted("tx1", "node0")
        
        self.metrics.reset()
        
        assert self.metrics.total_blocks_mined == 0
        assert self.metrics.total_transactions_processed == 0
        assert len(self.metrics.blocks) == 0
        assert len(self.metrics.transactions) == 0
    
    def test_global_metrics_collector(self):
        """Test global metrics collector singleton."""
        reset_metrics()
        
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
        
        collector1.record_block_mined(
            block_hash="global_block",
            block_index=1,
            miner_id="node0",
            transaction_count=1,
            mining_duration=0.1
        )
        
        assert collector2.total_blocks_mined == 1


class TestMetricsThreadSafety:
    """Test thread safety of metrics collector."""
    
    def test_concurrent_recording(self):
        """Test concurrent block recording."""
        import threading
        
        metrics = MetricsCollector()
        errors = []
        
        def record_blocks(start_index):
            try:
                for i in range(100):
                    metrics.record_block_mined(
                        block_hash=f"block_{start_index}_{i}",
                        block_index=start_index * 100 + i,
                        miner_id=f"node{start_index}",
                        transaction_count=1,
                        mining_duration=0.01
                    )
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=record_blocks, args=(i,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert metrics.total_blocks_mined == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

