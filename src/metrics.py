"""
Metrics collection module for blockchain performance monitoring.
Tracks TPS, propagation delay, orphan rate, and other network statistics.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from threading import Lock
import statistics


@dataclass
class BlockMetric:
    """Metrics for a single block."""
    block_hash: str
    block_index: int
    miner_id: str
    creation_time: float
    propagation_times: Dict[str, float] = field(default_factory=dict)  # node_id -> time received
    transaction_count: int = 0
    mining_duration: float = 0.0
    is_orphan: bool = False


@dataclass 
class TransactionMetric:
    """Metrics for a single transaction."""
    tx_hash: str
    creation_time: float
    propagation_times: Dict[str, float] = field(default_factory=dict)  # node_id -> time received
    confirmation_time: Optional[float] = None  # When included in a block
    confirmed_block_index: Optional[int] = None


class MetricsCollector:
    """
    Collects and aggregates blockchain network metrics.
    
    Metrics tracked:
    - Transactions per second (TPS)
    - Block propagation delay
    - Transaction propagation delay
    - Orphan/stale block rate
    - Mining time
    - Confirmation latency
    - Network throughput
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of recent items to keep for rolling averages
        """
        self.window_size = window_size
        self.logger = logging.getLogger("Metrics")
        
        # Block metrics
        self.blocks: Dict[str, BlockMetric] = {}
        self.recent_blocks: deque = deque(maxlen=window_size)
        self.orphan_blocks: List[str] = []
        
        # Transaction metrics
        self.transactions: Dict[str, TransactionMetric] = {}
        self.recent_transactions: deque = deque(maxlen=window_size)
        
        # Time series data
        self.tps_history: deque = deque(maxlen=window_size)
        self.block_time_history: deque = deque(maxlen=window_size)
        
        # Counters
        self.total_blocks_mined = 0
        self.total_transactions_processed = 0
        self.total_orphans = 0
        
        # Timing
        self.start_time = time.time()
        self.last_block_time = time.time()
        self.last_tps_calculation = time.time()
        self.tx_count_since_last_tps = 0
        
        # Thread safety
        self._lock = Lock()
    
    # ==================== Recording Methods ====================
    
    def record_block_mined(
        self, 
        block_hash: str, 
        block_index: int, 
        miner_id: str,
        transaction_count: int,
        mining_duration: float = 0.0
    ) -> None:
        """Record a newly mined block."""
        with self._lock:
            current_time = time.time()
            
            metric = BlockMetric(
                block_hash=block_hash,
                block_index=block_index,
                miner_id=miner_id,
                creation_time=current_time,
                transaction_count=transaction_count,
                mining_duration=mining_duration
            )
            metric.propagation_times[miner_id] = current_time
            
            self.blocks[block_hash] = metric
            self.recent_blocks.append(block_hash)
            self.total_blocks_mined += 1
            
            # Calculate block time
            block_time = current_time - self.last_block_time
            self.block_time_history.append(block_time)
            self.last_block_time = current_time
            
            self.logger.debug(f"Recorded block {block_hash[:8]} from {miner_id}")
    
    def record_block_received(self, block_hash: str, node_id: str) -> None:
        """Record when a node receives a block."""
        with self._lock:
            if block_hash in self.blocks:
                self.blocks[block_hash].propagation_times[node_id] = time.time()
    
    def record_block_orphaned(self, block_hash: str) -> None:
        """Record a block as orphaned (not in main chain)."""
        with self._lock:
            if block_hash in self.blocks:
                self.blocks[block_hash].is_orphan = True
                self.orphan_blocks.append(block_hash)
                self.total_orphans += 1
    
    def record_transaction_submitted(self, tx_hash: str, node_id: str) -> None:
        """Record a newly submitted transaction."""
        with self._lock:
            current_time = time.time()
            
            metric = TransactionMetric(
                tx_hash=tx_hash,
                creation_time=current_time
            )
            metric.propagation_times[node_id] = current_time
            
            self.transactions[tx_hash] = metric
            self.recent_transactions.append(tx_hash)
            self.total_transactions_processed += 1
            self.tx_count_since_last_tps += 1
    
    def record_transaction_received(self, tx_hash: str, node_id: str) -> None:
        """Record when a node receives a transaction."""
        with self._lock:
            if tx_hash in self.transactions:
                self.transactions[tx_hash].propagation_times[node_id] = time.time()
    
    def record_transaction_confirmed(
        self, 
        tx_hash: str, 
        block_index: int,
        confirmation_time: Optional[float] = None
    ) -> None:
        """Record when a transaction is confirmed in a block."""
        with self._lock:
            if tx_hash in self.transactions:
                self.transactions[tx_hash].confirmation_time = confirmation_time or time.time()
                self.transactions[tx_hash].confirmed_block_index = block_index
    
    # ==================== Calculation Methods ====================
    
    def calculate_tps(self) -> float:
        """Calculate current transactions per second."""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_tps_calculation
            
            if elapsed < 1.0:
                # Return last known TPS if less than 1 second elapsed
                return self.tps_history[-1] if self.tps_history else 0.0
            
            tps = self.tx_count_since_last_tps / elapsed
            self.tps_history.append(tps)
            self.tx_count_since_last_tps = 0
            self.last_tps_calculation = current_time
            
            return tps
    
    def get_average_tps(self) -> float:
        """Get average TPS over the window."""
        with self._lock:
            if not self.tps_history:
                return 0.0
            return statistics.mean(self.tps_history)
    
    def get_block_propagation_delay(self, block_hash: str) -> Optional[Dict[str, float]]:
        """
        Get propagation delay for a specific block.
        
        Returns:
            Dict with 'min', 'max', 'mean', 'median' delays in seconds
        """
        with self._lock:
            if block_hash not in self.blocks:
                return None
            
            metric = self.blocks[block_hash]
            creation_time = metric.creation_time
            
            delays = [
                recv_time - creation_time 
                for recv_time in metric.propagation_times.values()
            ]
            
            if len(delays) < 2:
                return None
            
            return {
                'min': min(delays),
                'max': max(delays),
                'mean': statistics.mean(delays),
                'median': statistics.median(delays),
                'nodes_reached': len(delays)
            }
    
    def get_average_block_propagation_delay(self) -> float:
        """Get average block propagation delay across recent blocks."""
        with self._lock:
            all_delays = []
            
            for block_hash in self.recent_blocks:
                if block_hash in self.blocks:
                    metric = self.blocks[block_hash]
                    creation_time = metric.creation_time
                    
                    for recv_time in metric.propagation_times.values():
                        delay = recv_time - creation_time
                        if delay > 0:  # Exclude the miner's own record
                            all_delays.append(delay)
            
            if not all_delays:
                return 0.0
            
            return statistics.mean(all_delays)
    
    def get_orphan_rate(self) -> float:
        """Get orphan block rate as a percentage."""
        with self._lock:
            if self.total_blocks_mined == 0:
                return 0.0
            return (self.total_orphans / self.total_blocks_mined) * 100
    
    def get_average_block_time(self) -> float:
        """Get average time between blocks."""
        with self._lock:
            if not self.block_time_history:
                return 0.0
            return statistics.mean(self.block_time_history)
    
    def get_average_confirmation_latency(self) -> float:
        """Get average time from transaction submission to confirmation."""
        with self._lock:
            latencies = []
            
            for tx_hash in self.recent_transactions:
                if tx_hash in self.transactions:
                    metric = self.transactions[tx_hash]
                    if metric.confirmation_time:
                        latency = metric.confirmation_time - metric.creation_time
                        latencies.append(latency)
            
            if not latencies:
                return 0.0
            
            return statistics.mean(latencies)
    
    def get_average_mining_time(self) -> float:
        """Get average mining duration per block."""
        with self._lock:
            mining_times = []
            
            for block_hash in self.recent_blocks:
                if block_hash in self.blocks:
                    duration = self.blocks[block_hash].mining_duration
                    if duration > 0:
                        mining_times.append(duration)
            
            if not mining_times:
                return 0.0
            
            return statistics.mean(mining_times)
    
    # ==================== Summary Methods ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        runtime = time.time() - self.start_time
        
        return {
            'runtime_seconds': runtime,
            'total_blocks': self.total_blocks_mined,
            'total_transactions': self.total_transactions_processed,
            'total_orphans': self.total_orphans,
            'current_tps': self.calculate_tps(),
            'average_tps': self.get_average_tps(),
            'average_block_time': self.get_average_block_time(),
            'average_propagation_delay': self.get_average_block_propagation_delay(),
            'orphan_rate_percent': self.get_orphan_rate(),
            'average_confirmation_latency': self.get_average_confirmation_latency(),
            'average_mining_time': self.get_average_mining_time(),
            'blocks_per_minute': (self.total_blocks_mined / runtime) * 60 if runtime > 0 else 0
        }
    
    def get_recent_blocks_summary(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get summary of recent blocks."""
        with self._lock:
            summaries = []
            blocks_to_show = list(self.recent_blocks)[-count:]
            
            for block_hash in reversed(blocks_to_show):
                if block_hash in self.blocks:
                    metric = self.blocks[block_hash]
                    prop_delay = self.get_block_propagation_delay(block_hash)
                    
                    summaries.append({
                        'hash': block_hash[:16] + '...',
                        'index': metric.block_index,
                        'miner': metric.miner_id,
                        'tx_count': metric.transaction_count,
                        'mining_time': round(metric.mining_duration, 2),
                        'propagation_delay_mean': round(prop_delay['mean'], 3) if prop_delay else None,
                        'nodes_reached': prop_delay['nodes_reached'] if prop_delay else 1,
                        'is_orphan': metric.is_orphan
                    })
            
            return summaries
    
    def print_summary(self) -> None:
        """Print a formatted summary of metrics."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("BLOCKCHAIN METRICS SUMMARY")
        print("=" * 60)
        print(f"Runtime: {summary['runtime_seconds']:.1f} seconds")
        print(f"\n📦 Blocks:")
        print(f"  Total mined: {summary['total_blocks']}")
        print(f"  Blocks/minute: {summary['blocks_per_minute']:.2f}")
        print(f"  Average block time: {summary['average_block_time']:.2f}s")
        print(f"  Average mining time: {summary['average_mining_time']:.2f}s")
        print(f"\n📝 Transactions:")
        print(f"  Total processed: {summary['total_transactions']}")
        print(f"  Current TPS: {summary['current_tps']:.2f}")
        print(f"  Average TPS: {summary['average_tps']:.2f}")
        print(f"  Avg confirmation latency: {summary['average_confirmation_latency']:.2f}s")
        print(f"\n🌐 Network:")
        print(f"  Avg propagation delay: {summary['average_propagation_delay']*1000:.1f}ms")
        print(f"  Orphan blocks: {summary['total_orphans']}")
        print(f"  Orphan rate: {summary['orphan_rate_percent']:.2f}%")
        print("=" * 60)
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.blocks.clear()
            self.recent_blocks.clear()
            self.orphan_blocks.clear()
            self.transactions.clear()
            self.recent_transactions.clear()
            self.tps_history.clear()
            self.block_time_history.clear()
            self.total_blocks_mined = 0
            self.total_transactions_processed = 0
            self.total_orphans = 0
            self.start_time = time.time()
            self.last_block_time = time.time()
            self.last_tps_calculation = time.time()
            self.tx_count_since_last_tps = 0


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector."""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.reset()
    else:
        _metrics_collector = MetricsCollector()

