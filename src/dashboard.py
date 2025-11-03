"""
Web dashboard for visualizing blockchain network state.
"""

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from typing import List, Dict
import logging


class Dashboard:
    """Flask-based web dashboard for blockchain visualization."""
    
    def __init__(self, nodes: List, port: int = 5000):
        self.nodes = nodes  # List of BlockchainNode instances
        self.app = Flask(__name__)
        CORS(self.app)
        self.port = port
        
        # Disable Flask logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)
        
        @self.app.route('/api/status')
        def get_status():
            """Get status of all nodes."""
            status = []
            for node in self.nodes:
                node_status = node.get_status()
                node_status['mempool_transactions'] = [
                    tx.to_dict() for tx in node.mempool.get_all_transactions()[:10]
                ]
                status.append(node_status)
            return jsonify(status)
        
        @self.app.route('/api/chain/<node_id>')
        def get_chain(node_id):
            """Get full blockchain for a specific node."""
            node = next((n for n in self.nodes if n.node_id == node_id), None)
            if not node:
                return jsonify({'error': 'Node not found'}), 404
            
            chain_data = []
            for block in node.blockchain.chain:
                block_dict = block.to_dict()
                # Limit transactions to prevent huge response
                if len(block_dict['transactions']) > 20:
                    block_dict['transactions'] = block_dict['transactions'][:20]
                    block_dict['transactions_truncated'] = True
                chain_data.append(block_dict)
            
            return jsonify({
                'node_id': node_id,
                'chain': chain_data,
                'state': node.blockchain.state
            })
        
        @self.app.route('/api/network')
        def get_network():
            """Get network topology."""
            topology = {
                'nodes': [],
                'edges': []
            }
            
            for node in self.nodes:
                topology['nodes'].append({
                    'id': node.node_id,
                    'label': node.node_id,
                    'chain_length': node.blockchain.get_chain_length(),
                    'mempool_size': node.mempool.size()
                })
                
                for peer_id in node.network.get_peer_ids():
                    # Add edge (avoid duplicates by sorting IDs)
                    edge_id = '-'.join(sorted([node.node_id, peer_id]))
                    if edge_id not in [e['id'] for e in topology['edges']]:
                        topology['edges'].append({
                            'id': edge_id,
                            'from': node.node_id,
                            'to': peer_id
                        })
            
            return jsonify(topology)
    
    def run(self):
        """Run the dashboard server."""
        print(f"\n{'='*60}")
        print(f"Dashboard running at http://localhost:{self.port}")
        print(f"{'='*60}\n")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)


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
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .nodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
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
        .network-section {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-top: 30px;
        }
        .peers-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        .peer-badge {
            background: #0f3460;
            padding: 8px 15px;
            border-radius: 20px;
            color: #3498db;
            font-weight: bold;
            border: 2px solid #3498db;
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
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⛓️ Blockchain Network Dashboard</h1>
        <div id="nodes-container" class="nodes-grid"></div>
        <div class="refresh-info">Auto-refreshing every 2 seconds...</div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const nodes = await response.json();
                renderNodes(nodes);
            } catch (error) {
                console.error('Error fetching status:', error);
            }
        }

        function renderNodes(nodes) {
            const container = document.getElementById('nodes-container');
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
                                    <strong>${tx.amount}</strong> coins (fee: ${tx.fee})
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
            `).join('');
        }

        // Initial fetch
        fetchStatus();
        
        // Auto-refresh every 2 seconds
        setInterval(fetchStatus, 2000);
    </script>
</body>
</html>
"""

