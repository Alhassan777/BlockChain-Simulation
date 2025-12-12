"""
Web dashboard for visualizing blockchain network state.
Includes real-time metrics visualization.
"""

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from typing import List, Dict, Optional
import logging
from src.metrics import get_metrics_collector, MetricsCollector


class Dashboard:
    """Flask-based web dashboard for blockchain visualization."""

    def __init__(
        self,
        nodes: List,
        port: int = 5000,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        self.nodes = nodes  # List of BlockchainNode instances
        self.app = Flask(__name__)
        CORS(self.app)
        self.port = port
        self.metrics = metrics_collector or get_metrics_collector()

        # Disable Flask logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            return render_template_string(HTML_TEMPLATE)

        @self.app.route("/api/status")
        def get_status():
            """Get status of all nodes."""
            status = []
            for node in self.nodes:
                node_status = node.get_status()
                node_status["mempool_transactions"] = [
                    tx.to_dict() for tx in node.mempool.get_all_transactions()[:10]
                ]
                status.append(node_status)
            return jsonify(status)

        @self.app.route("/api/metrics")
        def get_metrics():
            """Get network performance metrics."""
            summary = self.metrics.get_summary()
            recent_blocks = self.metrics.get_recent_blocks_summary(count=10)

            return jsonify({"summary": summary, "recent_blocks": recent_blocks})

        @self.app.route("/api/chain/<node_id>")
        def get_chain(node_id):
            """Get full blockchain for a specific node."""
            node = next((n for n in self.nodes if n.node_id == node_id), None)
            if not node:
                return jsonify({"error": "Node not found"}), 404

            chain_data = []
            for block in node.blockchain.chain:
                block_dict = block.to_dict()
                # Limit transactions to prevent huge response
                if len(block_dict["transactions"]) > 20:
                    block_dict["transactions"] = block_dict["transactions"][:20]
                    block_dict["transactions_truncated"] = True
                chain_data.append(block_dict)

            return jsonify(
                {
                    "node_id": node_id,
                    "chain": chain_data,
                    "state": node.blockchain.state,
                }
            )

        @self.app.route("/api/network")
        def get_network():
            """Get network topology."""
            topology = {"nodes": [], "edges": []}

            for node in self.nodes:
                topology["nodes"].append(
                    {
                        "id": node.node_id,
                        "label": node.node_id,
                        "chain_length": node.blockchain.get_chain_length(),
                        "mempool_size": node.mempool.size(),
                    }
                )

                for peer_id in node.network.get_peer_ids():
                    # Add edge (avoid duplicates by sorting IDs)
                    edge_id = "-".join(sorted([node.node_id, peer_id]))
                    if edge_id not in [e["id"] for e in topology["edges"]]:
                        topology["edges"].append(
                            {"id": edge_id, "from": node.node_id, "to": peer_id}
                        )

            return jsonify(topology)

    def run(self):
        """Run the dashboard server."""
        import sys

        print(f"\n{'='*60}")
        print(f"Dashboard running at http://localhost:{self.port}")
        print(f"{'='*60}\n")
        sys.stdout.flush()

        # Suppress Flask startup message
        import logging

        cli_log = logging.getLogger("werkzeug")
        cli_log.setLevel(logging.ERROR)

        try:
            # Use 127.0.0.1 instead of 0.0.0.0 to avoid macOS firewall issues
            self.app.run(
                host="127.0.0.1",
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True,
            )
        except Exception as e:
            print(f"Dashboard error: {e}")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Blockchain Network Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #f39c12;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        h2 {
            color: #f39c12;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #0f3460;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Metrics Section */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            border: 2px solid #0f3460;
            transition: transform 0.2s, border-color 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #3498db;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        .metric-value.highlight {
            color: #f39c12;
        }
        .metric-value.success {
            color: #27ae60;
        }
        .metric-value.warning {
            color: #e74c3c;
        }
        .metric-label {
            color: #95a5a6;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .metric-unit {
            color: #7f8c8d;
            font-size: 0.8em;
        }
        
        /* Nodes Grid */
        .nodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .node-card {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border: 2px solid #0f3460;
        }
        .node-card.mining {
            border-color: #f39c12;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { border-color: #f39c12; }
            50% { border-color: #e74c3c; }
        }
        .node-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #0f3460;
        }
        .node-id {
            font-size: 1.3em;
            font-weight: bold;
            color: #3498db;
        }
        .status-badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .status-mining { background: #f39c12; color: #000; }
        .status-idle { background: #27ae60; color: #fff; }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
        }
        .info-label {
            color: #95a5a6;
            font-weight: 600;
        }
        .info-value {
            color: #ecf0f1;
            font-weight: bold;
        }
        .hash {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #3498db;
        }
        .mempool-section {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 2px solid #0f3460;
        }
        .section-title {
            color: #f39c12;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .tx-list {
            max-height: 150px;
            overflow-y: auto;
            font-size: 0.85em;
        }
        .tx-item {
            background: #0f3460;
            padding: 8px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #3498db;
        }
        .peers-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        .peer-badge {
            background: #0f3460;
            padding: 6px 12px;
            border-radius: 20px;
            color: #3498db;
            font-weight: bold;
            font-size: 0.85em;
            border: 1px solid #3498db;
        }
        
        /* Recent Blocks Table */
        .blocks-table {
            width: 100%;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }
        .blocks-table th {
            background: #0f3460;
            color: #f39c12;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        .blocks-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #0f3460;
        }
        .blocks-table tr:hover {
            background: rgba(52, 152, 219, 0.1);
        }
        .blocks-table .hash-cell {
            font-family: 'Courier New', monospace;
            color: #3498db;
        }
        .orphan-badge {
            background: #e74c3c;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        
        .refresh-info {
            text-align: center;
            color: #95a5a6;
            margin-top: 20px;
            font-style: italic;
        }
        .no-data {
            color: #95a5a6;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }
        
        /* Info Banner */
        .info-banner {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            border: 2px solid #3498db;
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0 30px 0;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }
        .banner-content h3 {
            color: #3498db;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .banner-content p {
            color: #ecf0f1;
            margin-bottom: 20px;
            font-size: 1.1em;
        }
        .command-box {
            background: #1a1a2e;
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .command-box strong {
            color: #f39c12;
            display: block;
            margin-bottom: 8px;
        }
        .command-box code {
            color: #3498db;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            background: #0f3460;
            padding: 8px 12px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⛓️ Blockchain Network Dashboard</h1>
        
        <!-- Info Banner -->
        <div id="info-banner" class="info-banner" style="display: none;">
            <div class="banner-content">
                <h3>🚀 No Blockchain Network Detected</h3>
                <p>To start the blockchain simulation, run one of these commands in your terminal:</p>
                <div class="command-box">
                    <strong>Basic Demo:</strong><br>
                    <code>python BlockChain-Simulation/scripts/demo_basic.py</code>
                </div>
                <div class="command-box">
                    <strong>Fault Tolerance Demo:</strong><br>
                    <code>python BlockChain-Simulation/scripts/demo_faults.py</code>
                </div>
                <div class="command-box">
                    <strong>Stress Test:</strong><br>
                    <code>python BlockChain-Simulation/scripts/demo_stress.py</code>
                </div>
            </div>
        </div>
        
        <!-- Metrics Section -->
        <h2>📊 Network Metrics</h2>
        <div id="metrics-container" class="metrics-grid"></div>
        
        <!-- Nodes Section -->
        <h2>🖥️ Network Nodes</h2>
        <div id="nodes-container" class="nodes-grid"></div>
        
        <!-- Recent Blocks Section -->
        <h2>📦 Recent Blocks</h2>
        <div id="blocks-container"></div>
        
        <div class="refresh-info">Auto-refreshing every 2 seconds...</div>
    </div>

    <script>
        async function fetchData() {
            try {
                const [statusRes, metricsRes] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/metrics')
                ]);
                
                const nodes = await statusRes.json();
                const metrics = await metricsRes.json();
                
                renderMetrics(metrics);
                renderNodes(nodes);
                renderRecentBlocks(metrics.recent_blocks);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }
        
        function formatNumber(num, decimals = 2) {
            if (num === null || num === undefined) return 'N/A';
            return num.toFixed(decimals);
        }
        
        function formatMs(seconds) {
            if (seconds === null || seconds === undefined) return 'N/A';
            return (seconds * 1000).toFixed(1) + 'ms';
        }

        function renderMetrics(data) {
            const summary = data.summary;
            const container = document.getElementById('metrics-container');
            
            container.innerHTML = `
                <div class="metric-card">
                    <div class="metric-value highlight">${formatNumber(summary.current_tps)}</div>
                    <div class="metric-label">Current TPS</div>
                    <div class="metric-unit">transactions/second</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatNumber(summary.average_tps)}</div>
                    <div class="metric-label">Average TPS</div>
                    <div class="metric-unit">transactions/second</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value success">${summary.total_blocks}</div>
                    <div class="metric-label">Total Blocks</div>
                    <div class="metric-unit">mined</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${summary.total_transactions}</div>
                    <div class="metric-label">Total Transactions</div>
                    <div class="metric-unit">processed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatNumber(summary.average_block_time)}</div>
                    <div class="metric-label">Avg Block Time</div>
                    <div class="metric-unit">seconds</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatMs(summary.average_propagation_delay)}</div>
                    <div class="metric-label">Propagation Delay</div>
                    <div class="metric-unit">average</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value ${summary.orphan_rate_percent > 5 ? 'warning' : 'success'}">${formatNumber(summary.orphan_rate_percent)}%</div>
                    <div class="metric-label">Orphan Rate</div>
                    <div class="metric-unit">${summary.total_orphans} orphans</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatNumber(summary.average_confirmation_latency)}</div>
                    <div class="metric-label">Confirmation Latency</div>
                    <div class="metric-unit">seconds</div>
                </div>
            `;
        }

        function renderNodes(nodes) {
            const container = document.getElementById('nodes-container');
            const banner = document.getElementById('info-banner');
            
            // Show/hide banner based on whether nodes exist
            if (!nodes || nodes.length === 0) {
                banner.style.display = 'block';
                container.innerHTML = '<div class="no-data">Waiting for blockchain network to start...</div>';
                return;
            } else {
                banner.style.display = 'none';
            }
            
            container.innerHTML = nodes.map(node => `
                <div class="node-card ${node.is_mining ? 'mining' : ''}">
                    <div class="node-header">
                        <div class="node-id">${node.node_id}</div>
                        <div class="status-badge ${node.is_mining ? 'status-mining' : 'status-idle'}">
                            ${node.is_mining ? '⛏️ MINING' : '✓ IDLE'}
                        </div>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Chain Length:</span>
                        <span class="info-value">${node.chain_length} blocks</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Chain Tip:</span>
                        <span class="info-value hash">${node.chain_tip.substring(0, 16)}...</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Balance:</span>
                        <span class="info-value">${node.balance.toFixed(2)} coins</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Mempool:</span>
                        <span class="info-value">${node.mempool_size} transactions</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="info-label">Peers:</span>
                        <span class="info-value">${node.peer_count} connected</span>
                    </div>
                    
                    ${node.peers.length > 0 ? `
                    <div class="mempool-section">
                        <div class="section-title">Connected Peers</div>
                        <div class="peers-list">
                            ${node.peers.map(peer => `<span class="peer-badge">${peer}</span>`).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${node.mempool_transactions && node.mempool_transactions.length > 0 ? `
                    <div class="mempool-section">
                        <div class="section-title">Mempool (Recent)</div>
                        <div class="tx-list">
                            ${node.mempool_transactions.map(tx => `
                                <div class="tx-item">
                                    ${tx.sender.substring(0, 8)}... → ${tx.receiver.substring(0, 8)}...: 
                                    <strong>${tx.amount.toFixed(2)}</strong> coins
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
            `).join('');
        }
        
        function renderRecentBlocks(blocks) {
            const container = document.getElementById('blocks-container');
            
            if (!blocks || blocks.length === 0) {
                container.innerHTML = '<div class="no-data">No blocks mined yet...</div>';
                return;
            }
            
            container.innerHTML = `
                <table class="blocks-table">
                    <thead>
                        <tr>
                            <th>Block #</th>
                            <th>Hash</th>
                            <th>Miner</th>
                            <th>Transactions</th>
                            <th>Mining Time</th>
                            <th>Propagation</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${blocks.map(block => `
                            <tr>
                                <td><strong>${block.index}</strong></td>
                                <td class="hash-cell">${block.hash}</td>
                                <td>${block.miner}</td>
                                <td>${block.tx_count}</td>
                                <td>${block.mining_time}s</td>
                                <td>${block.propagation_delay_mean ? (block.propagation_delay_mean * 1000).toFixed(1) + 'ms' : 'N/A'}</td>
                                <td>${block.is_orphan ? '<span class="orphan-badge">ORPHAN</span>' : '✓'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        // Initial fetch
        fetchData();
        
        // Auto-refresh every 2 seconds
        setInterval(fetchData, 2000);
    </script>
</body>
</html>
"""
