"""
Tests for the Dashboard module.

Uses Flask's test client for HTTP endpoint testing.
"""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dashboard import Dashboard
from src.metrics import MetricsCollector, reset_metrics
from src.block import Block
from src.blockchain import Blockchain
from src.mempool import Mempool
from src.transaction import Transaction


class MockNode:
    """Mock BlockchainNode for testing dashboard without network."""

    def __init__(self, node_id: str, chain_length: int = 1, balance: float = 0.0):
        self.node_id = node_id
        self.miner_address = node_id

        # Create real blockchain with genesis
        genesis = Block.create_genesis_block()
        self.blockchain = Blockchain(difficulty=1, genesis_block=genesis)

        # Add blocks to reach desired chain length
        for i in range(chain_length - 1):
            coinbase = Transaction.create_coinbase(node_id, 50.0)
            block = Block(
                index=self.blockchain.get_chain_length(),
                transactions=[coinbase],
                previous_hash=self.blockchain.get_latest_block().hash,
                difficulty=1,
            )
            block.mine(max_iterations=10000)
            self.blockchain.add_block(block)

        self.mempool = Mempool()

        # Mock network
        self.network = MockNetwork()

    def get_status(self):
        return {
            "node_id": self.node_id,
            "chain_length": self.blockchain.get_chain_length(),
            "chain_tip": self.blockchain.get_latest_block().hash,
            "mempool_size": self.mempool.size(),
            "balance": self.blockchain.get_balance(self.miner_address),
            "is_mining": False,
            "peers": self.network.get_peer_ids(),
            "peer_count": self.network.get_peer_count(),
        }


class MockNetwork:
    """Mock network for testing."""

    def __init__(self):
        self.peers = {}

    def get_peer_ids(self):
        return list(self.peers.keys())

    def get_peer_count(self):
        return len(self.peers)


class TestDashboard(unittest.TestCase):
    """Tests for Dashboard class."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.metrics = MetricsCollector()

        # Create mock nodes
        self.nodes = [
            MockNode("node0", chain_length=3, balance=100.0),
            MockNode("node1", chain_length=3, balance=50.0),
        ]

        # Create dashboard with mock nodes
        self.dashboard = Dashboard(
            nodes=self.nodes, port=5999, metrics_collector=self.metrics
        )

        # Get Flask test client
        self.client = self.dashboard.app.test_client()

    def test_index_returns_html(self):
        """Test that index route returns HTML."""
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data)
        self.assertIn(b"Blockchain Network Dashboard", response.data)

    def test_api_status_returns_json(self):
        """Test /api/status returns JSON array of node statuses."""
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        data = json.loads(response.data)

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        # Check first node
        node0 = data[0]
        self.assertEqual(node0["node_id"], "node0")
        self.assertIn("chain_length", node0)
        self.assertIn("chain_tip", node0)
        self.assertIn("mempool_size", node0)
        self.assertIn("balance", node0)
        self.assertIn("is_mining", node0)

    def test_api_metrics_returns_json(self):
        """Test /api/metrics returns metrics summary."""
        # Add some metrics data
        self.metrics.record_block_mined(
            block_hash="abc123",
            block_index=1,
            miner_id="node0",
            transaction_count=5,
            mining_duration=0.5,
        )
        self.metrics.record_transaction_submitted("tx123", "node0")

        response = self.client.get("/api/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        data = json.loads(response.data)

        self.assertIn("summary", data)
        self.assertIn("recent_blocks", data)

        summary = data["summary"]
        self.assertIn("total_blocks", summary)
        self.assertIn("total_transactions", summary)
        self.assertEqual(summary["total_blocks"], 1)
        self.assertEqual(summary["total_transactions"], 1)

    def test_api_chain_returns_node_chain(self):
        """Test /api/chain/<node_id> returns chain data."""
        response = self.client.get("/api/chain/node0")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        data = json.loads(response.data)

        self.assertEqual(data["node_id"], "node0")
        self.assertIn("chain", data)
        self.assertIn("state", data)
        self.assertIsInstance(data["chain"], list)
        self.assertEqual(len(data["chain"]), 3)  # 3 blocks

    def test_api_chain_not_found(self):
        """Test /api/chain/<node_id> returns 404 for unknown node."""
        response = self.client.get("/api/chain/unknown_node")

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_api_network_returns_topology(self):
        """Test /api/network returns network topology."""
        response = self.client.get("/api/network")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        data = json.loads(response.data)

        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIsInstance(data["nodes"], list)
        self.assertIsInstance(data["edges"], list)
        self.assertEqual(len(data["nodes"]), 2)


class TestDashboardWithMetrics(unittest.TestCase):
    """Tests for Dashboard metrics integration."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.metrics = MetricsCollector()
        self.nodes = [MockNode("node0")]
        self.dashboard = Dashboard(
            nodes=self.nodes, port=5998, metrics_collector=self.metrics
        )
        self.client = self.dashboard.app.test_client()

    def test_metrics_shows_block_info(self):
        """Test metrics endpoint shows block information."""
        # Record multiple blocks
        for i in range(3):
            self.metrics.record_block_mined(
                block_hash=f"block{i}",
                block_index=i + 1,
                miner_id="node0",
                transaction_count=i + 1,
                mining_duration=0.1 * (i + 1),
            )

        response = self.client.get("/api/metrics")
        data = json.loads(response.data)

        self.assertEqual(data["summary"]["total_blocks"], 3)
        self.assertIsInstance(data["recent_blocks"], list)

    def test_metrics_shows_orphan_info(self):
        """Test metrics endpoint shows orphan information."""
        self.metrics.record_block_mined(
            block_hash="orphan1",
            block_index=1,
            miner_id="node0",
            transaction_count=1,
            mining_duration=0.1,
        )
        self.metrics.record_block_orphaned("orphan1")

        response = self.client.get("/api/metrics")
        data = json.loads(response.data)

        self.assertEqual(data["summary"]["total_orphans"], 1)


class TestDashboardHTML(unittest.TestCase):
    """Tests for Dashboard HTML content."""

    def setUp(self):
        """Set up test fixtures."""
        reset_metrics()
        self.nodes = [MockNode("node0")]
        self.dashboard = Dashboard(nodes=self.nodes, port=5997)
        self.client = self.dashboard.app.test_client()

    def test_html_contains_expected_sections(self):
        """Test HTML contains all expected sections."""
        response = self.client.get("/")
        html = response.data.decode("utf-8")

        # Check for main sections
        self.assertIn("Network Metrics", html)
        self.assertIn("Network Nodes", html)
        self.assertIn("Recent Blocks", html)

    def test_html_contains_api_endpoints(self):
        """Test HTML references correct API endpoints."""
        response = self.client.get("/")
        html = response.data.decode("utf-8")

        self.assertIn("/api/status", html)
        self.assertIn("/api/metrics", html)


if __name__ == "__main__":
    unittest.main()
