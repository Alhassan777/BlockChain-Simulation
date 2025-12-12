# ⛓️ Blockchain Simulation

A complete miniature blockchain system inspired by Bitcoin, implemented in Python. This educational project demonstrates core distributed systems concepts including P2P networking, consensus mechanisms, cryptographic hashing, and fault tolerance.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Tests](https://img.shields.io/badge/Tests-87-passing.svg)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Running the Demos](#-running-the-demos)
- [Running Tests](#-running-tests)
- [Project Structure](#-project-structure)
- [Components](#-components)
- [API Reference](#-api-reference)
- [Distributed Systems Concepts](#-distributed-systems-concepts)
- [Failure Modes Tested](#-failure-modes-tested)
- [Performance Metrics](#-performance-metrics)

## ✨ Features

### Core Blockchain Features

- **SHA-256 Cryptographic Hashing** - Tamper-evident block linking
- **Merkle Trees** - Efficient transaction verification with O(log n) proofs
- **Proof-of-Work Consensus** - Adjustable difficulty mining
- **Leader-Based Consensus** - Alternative round-robin block proposal
- **Account-Based State** - Balance and nonce tracking per address
- **Transaction Fees & Rewards** - Economic incentive system

### Networking

- **P2P Gossip Protocol** - Decentralized message propagation
- **asyncio TCP Networking** - High-performance async I/O
- **Duplicate Suppression** - Efficient message deduplication
- **Multiple Topologies** - Ring, mesh, and custom configurations

### Fault Tolerance

- **Network Partitions** - Split and heal network simulations
- **Node Crash/Recovery** - Automatic chain resynchronization
- **Message Loss & Delay** - Configurable fault injection
- **Fork Resolution** - Longest-chain rule implementation

### Observability

- **Real-time Web Dashboard** - Live network visualization
- **Comprehensive Metrics** - TPS, propagation delay, orphan rate
- **Detailed Logging** - Per-node activity tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BLOCKCHAIN NODE                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Network   │  │  Consensus  │  │  Blockchain │  │   Mempool  │ │
│  │   (P2P)     │◄─┤   (PoW)     │◄─┤   (State)   │◄─┤   (Txns)   │ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Message Types                                 ││
│  │  • NEW_TX (Transaction broadcast)                               ││
│  │  • NEW_BLOCK (Block announcement)                               ││
│  │  • GET_CHAIN / CHAIN_RESPONSE (Sync)                           ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/blockchain-simulation.git
cd blockchain-simulation

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the basic demo
python scripts/demo_basic.py

# Open dashboard in browser
# http://localhost:5001
```

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Step-by-Step Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/blockchain-simulation.git
   cd blockchain-simulation
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv venv

   # Activate on macOS/Linux:
   source venv/bin/activate

   # Activate on Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python scripts/run_tests.py --quick
   ```

### Dependencies

| Package    | Version | Purpose                       |
| ---------- | ------- | ----------------------------- |
| flask      | 3.0.0   | Web dashboard server          |
| flask-cors | 4.0.0   | Cross-origin resource sharing |
| aiohttp    | 3.9.1   | Async HTTP support            |
| pytest     | 7.4.3   | Testing framework             |

## 🎮 Running the Demos

### Demo 1: Basic Functionality

Demonstrates node creation, P2P connections, transaction propagation, and mining.

```bash
python scripts/demo_basic.py
```

**What you'll see:**

- 4 nodes starting and connecting in a ring topology
- Initial mining to bootstrap the economy
- Transaction submission and propagation
- Block mining with transaction inclusion
- Final state showing balances and chain sync

### Demo 2: Fault Tolerance

Tests network resilience under adverse conditions.

```bash
python scripts/demo_faults.py
```

**Scenarios tested:**

- Network partition (split into two groups)
- Chain divergence during partition
- Partition healing and convergence
- Node crash and recovery
- Invalid transaction rejection

### Demo 3: Stress Test

Measures performance under high load.

```bash
python scripts/demo_stress.py

# With custom parameters:
python scripts/demo_stress.py --nodes 15 --transactions 100 --mining-rounds 10
```

**Parameters:**

- `--nodes`: Number of nodes (default: 10)
- `--difficulty`: Mining difficulty (default: 2)
- `--transactions`: Number of transactions (default: 50)
- `--mining-rounds`: Mining rounds (default: 5)

### Web Dashboard

All demos start a web dashboard at **http://localhost:5001** showing:

- Network metrics (TPS, block time, orphan rate)
- Node status (chain length, balance, peers)
- Recent blocks (miner, transactions, propagation)
- Real-time updates every 2 seconds

## 🧪 Running Tests

### Run All Tests

```bash
# Using the test runner script (recommended)
python scripts/run_tests.py

# Using pytest directly
pytest tests/ -v
```

### Quick Tests (Core Only)

```bash
# Skip all integration tests - fastest option
python scripts/run_tests.py --quick

# Run only the core unit tests
python scripts/run_tests.py --core
```

### Include Network Integration Tests

```bash
# Network tests are skipped by default (they can be slow)
RUN_NETWORK_TESTS=1 python scripts/run_tests.py
```

### Verbose Output

```bash
python scripts/run_tests.py -v
```

### Run Specific Test File

```bash
pytest tests/test_blockchain.py -v
pytest tests/test_merkle.py -v
pytest tests/test_double_spend.py -v
```

### Test Coverage

| Test File            | Tests   | Coverage                               |
| -------------------- | ------- | -------------------------------------- |
| test_transaction.py  | 6       | Transaction creation, hashing, signing |
| test_block.py        | 6       | Block creation, mining, validation     |
| test_blockchain.py   | 7       | Chain management, fork resolution      |
| test_merkle.py       | 19      | Merkle tree, proofs, verification      |
| test_metrics.py      | 14      | Performance metric collection          |
| test_orphans.py      | 6       | Orphan block tracking                  |
| test_double_spend.py | 6       | Double-spend prevention                |
| test_consensus.py    | 14      | PoW and leader consensus               |
| test_mempool.py      | 18      | Transaction pool management            |
| test_network.py      | 10      | P2P networking (unit + integration)    |
| test_faults.py       | 8       | Fault injection (unit + integration)   |
| test_node.py         | 15      | BlockchainNode (unit + integration)    |
| test_dashboard.py    | 10      | Dashboard API endpoints                |
| **Total**            | **139** | 87 discovered, 17 network (skipped)    |

> **Note:** Network integration tests are skipped by default (they can be slow). Run with `RUN_NETWORK_TESTS=1` to include them.

## 📁 Project Structure

```
blockchain-simulation/
├── README.md              # This file
├── LICENSE                # MIT License
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── architecture.svg       # Architecture diagram
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── transaction.py     # Transaction class
│   ├── block.py           # Block with Merkle root
│   ├── blockchain.py      # Chain and state management
│   ├── consensus.py       # PoW and leader consensus
│   ├── network.py         # P2P networking
│   ├── node.py            # Complete blockchain node
│   ├── mempool.py         # Transaction pool
│   ├── merkle.py          # Merkle tree implementation
│   ├── metrics.py         # Performance metrics
│   ├── faults.py          # Fault injection
│   └── dashboard.py       # Web dashboard
│
├── scripts/               # Runnable scripts
│   ├── demo_basic.py      # Basic functionality demo
│   ├── demo_faults.py     # Fault tolerance demo
│   ├── demo_stress.py     # Stress test demo
│   └── run_tests.py       # Test runner
│
└── tests/                 # Unit tests (139 tests)
    ├── __init__.py
    ├── test_transaction.py
    ├── test_block.py
    ├── test_blockchain.py
    ├── test_merkle.py
    ├── test_metrics.py
    ├── test_orphans.py
    ├── test_double_spend.py
    ├── test_consensus.py
    ├── test_mempool.py
    ├── test_network.py
    ├── test_faults.py
    ├── test_node.py
    └── test_dashboard.py
```

## 🔧 Components

### Transaction (`src/transaction.py`)

```python
from src.transaction import Transaction

# Create a transaction
tx = Transaction(
    sender="alice",
    receiver="bob",
    amount=10.0,
    fee=0.5,
    nonce=0
)

# Sign it (toy HMAC signature)
tx.sign("alice_private_key")

# Validate
is_valid, error = tx.is_valid()

# Create coinbase (mining reward)
coinbase = Transaction.create_coinbase("miner_address", reward=50.0)
```

### Block (`src/block.py`)

```python
from src.block import Block

# Create a block
block = Block(
    index=1,
    transactions=[coinbase, tx1, tx2],
    previous_hash="abc123...",
    difficulty=2
)

# Mine it (find valid nonce)
success = block.mine(max_iterations=100000)

# Verify Merkle proof for a transaction
proof = block.get_transaction_proof(tx_index=1)
is_valid = block.verify_transaction_proof(tx, proof)
```

### Blockchain (`src/blockchain.py`)

```python
from src.blockchain import Blockchain

# Create blockchain (auto-creates genesis)
blockchain = Blockchain(difficulty=2)

# Add a block
added, error = blockchain.add_block(block)

# Check balance
balance = blockchain.get_balance("alice")

# Fork resolution (longest chain wins)
replaced, error = blockchain.replace_chain(longer_chain)
```

### Node (`src/node.py`)

```python
from src.node import BlockchainNode
import asyncio

async def main():
    # Create node
    node = BlockchainNode(
        node_id="node0",
        host="127.0.0.1",
        port=8000,
        difficulty=2,
        block_reward=50.0
    )

    # Start networking
    await node.start()

    # Connect to peer
    await node.connect_to_peer("node1", "127.0.0.1", 8001)

    # Submit transaction
    await node.submit_transaction(tx)

    # Mine next block
    block = await node.mine_next_block()

    # Get status
    status = node.get_status()

asyncio.run(main())
```

### Merkle Tree (`src/merkle.py`)

```python
from src.merkle import MerkleTree, compute_merkle_root

# Build tree from transactions
tree = MerkleTree(transactions)

# Get root hash
root = tree.root

# Generate proof for transaction
proof = tree.get_proof(tx_index=2)

# Verify proof
is_valid = tree.verify_proof(tx_hash, proof, root)
```

## 📚 API Reference

### BlockchainNode Methods

| Method                            | Description                        |
| --------------------------------- | ---------------------------------- |
| `start()`                         | Start the node's TCP server        |
| `stop()`                          | Stop node and close connections    |
| `connect_to_peer(id, host, port)` | Connect to another node            |
| `submit_transaction(tx)`          | Submit transaction to network      |
| `mine_next_block()`               | Mine a new block                   |
| `get_status()`                    | Get node status dict               |
| `enable_auto_mining()`            | Auto-mine when transactions arrive |

### Blockchain Methods

| Method                      | Description               |
| --------------------------- | ------------------------- |
| `add_block(block)`          | Add block to chain        |
| `replace_chain(chain)`      | Replace with longer chain |
| `get_balance(address)`      | Get account balance       |
| `get_nonce(address)`        | Get account nonce         |
| `can_apply_transaction(tx)` | Check if tx is valid      |
| `validate_chain(chain)`     | Validate entire chain     |

### Metrics Methods

| Method                              | Description                 |
| ----------------------------------- | --------------------------- |
| `calculate_tps()`                   | Current transactions/second |
| `get_orphan_rate()`                 | Orphan block percentage     |
| `get_average_block_time()`          | Mean time between blocks    |
| `get_block_propagation_delay(hash)` | Block propagation stats     |
| `get_summary()`                     | All metrics as dict         |
| `print_summary()`                   | Print formatted metrics     |

## 🎓 Distributed Systems Concepts

This project demonstrates several key distributed systems concepts:

### 1. Gossip Protocol

Messages (transactions, blocks) propagate through the network via gossip. Each node forwards messages to its peers, with duplicate suppression preventing infinite loops.

### 2. Consensus

Two mechanisms are implemented:

- **Proof-of-Work**: Nodes compete to find a valid hash (leading zeros)
- **Leader-Based**: Round-robin leader proposes blocks

### 3. Fork Resolution

When multiple valid chains exist, the **longest-chain rule** determines the canonical chain. Shorter chains are orphaned.

### 4. State Machine Replication

All nodes maintain the same state (balances, nonces) by applying the same transactions in the same order.

### 5. Fault Tolerance

The system handles:

- **Crash failures**: Nodes restart and resync
- **Network partitions**: Chains diverge, then converge after healing
- **Byzantine behavior**: Invalid transactions are rejected

### 6. Eventual Consistency

Nodes may temporarily disagree but eventually converge to the same state through gossip and fork resolution.

## 🔥 Failure Modes Tested

| Failure Mode         | Implementation                               | Demo                 |
| -------------------- | -------------------------------------------- | -------------------- |
| Node crash/restart   | `FaultInjector.crash_node()`                 | demo_faults.py       |
| Message loss         | `network.message_drop_prob`                  | Configurable         |
| Message delay        | `network.message_delay_ms`                   | Configurable         |
| Network partition    | `FaultInjector.partition_network()`          | demo_faults.py       |
| Invalid transactions | `FaultInjector.inject_invalid_transaction()` | demo_faults.py       |
| Double-spend         | Nonce validation                             | test_double_spend.py |
| High load            | demo_stress.py                               | demo_stress.py       |

## 📊 Performance Metrics

The system tracks comprehensive performance metrics:

| Metric               | Description                             | Method                               |
| -------------------- | --------------------------------------- | ------------------------------------ |
| TPS                  | Transactions per second                 | `calculate_tps()`                    |
| Block Time           | Average time between blocks             | `get_average_block_time()`           |
| Propagation Delay    | Time for blocks to reach all nodes      | `get_block_propagation_delay()`      |
| Orphan Rate          | Percentage of orphaned blocks           | `get_orphan_rate()`                  |
| Confirmation Latency | Time from tx submission to confirmation | `get_average_confirmation_latency()` |
| Mining Time          | Time to mine each block                 | `get_average_mining_time()`          |

### Sample Stress Test Results (10 nodes, difficulty 2)

```
📦 Blocks:
  Total mined: 15
  Blocks/minute: 12.5
  Average block time: 4.8s

📝 Transactions:
  Total processed: 50
  Average TPS: 2.1
  Avg confirmation latency: 8.5s

🌐 Network:
  Avg propagation delay: 45ms
  Orphan rate: 6.67%
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Bitcoin whitepaper by Satoshi Nakamoto
- "The Little Book of Bitcoin"
- "Inventing Bitcoin" by Yan Pritzker
- Kalam fi El-Programming podcast (Episode 32)

---

**Built for educational purposes to demonstrate blockchain and distributed systems concepts.**
