# Bitcoin-Inspired Blockchain Simulation

A distributed blockchain system implementing peer-to-peer networking, Proof-of-Work consensus, and fault tolerance for educational purposes.

## 🎯 Project Overview

This project implements a miniature blockchain system inspired by Bitcoin, demonstrating core distributed systems concepts:
- **P2P Networking**: Decentralized gossip-based communication
- **Hash-Linked Blockchain**: Tamper-evident chain using SHA-256
- **Proof-of-Work Consensus**: Simulated mining with adjustable difficulty
- **Transaction Propagation**: Network-wide transaction distribution
- **Fault Tolerance**: Recovery from partitions, crashes, and invalid data
- **Visualization**: Real-time web dashboard

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Blockchain Node                    │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │Blockchain│  │  Mempool │  │ Proof-of-Work   │  │
│  │ (Ledger) │  │  (Txs)   │  │  (Consensus)    │  │
│  └──────────┘  └──────────┘  └─────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │         P2P Network (Gossip Protocol)         │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
           │                │                │
           └────────────────┴────────────────┘
                          ↓
              ┌─────────────────────┐
              │  Other Nodes (Peers)│
              └─────────────────────┘
```

### Core Components

- **`src/transaction.py`**: Transaction structure with HMAC signatures
- **`src/block.py`**: Block structure with hash-linking and PoW validation
- **`src/blockchain.py`**: Ledger with fork resolution and state management
- **`src/mempool.py`**: Pending transaction pool
- **`src/network.py`**: Asyncio-based P2P networking with gossip protocol
- **`src/consensus.py`**: Proof-of-Work mining mechanism
- **`src/node.py`**: Complete blockchain node integrating all components
- **`src/dashboard.py`**: Flask web dashboard for visualization
- **`src/faults.py`**: Fault injection for testing

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Basic Demo

```bash
# Run basic demo with 4 nodes
python scripts/demo_basic.py
```

This demo:
1. Creates 4 blockchain nodes
2. Connects them in a ring topology
3. Mines initial blocks to give nodes coins
4. Submits transactions and observes propagation
5. Mines transactions into blocks
6. Launches web dashboard at http://localhost:5000

### Running the Fault Tolerance Demo

```bash
# Run fault tolerance demo
python scripts/demo_faults.py
```

This demo:
1. Creates a mesh network of 4 nodes
2. Partitions the network into two groups
3. Mines blocks in both partitions (creates fork)
4. Heals partition and demonstrates chain convergence
5. Crashes a node, mines blocks, and recovers it (resync)
6. Tests invalid transaction rejection

### Running the Stress Test (10+ Nodes)

```bash
# Run stress test with default settings (10 nodes)
python scripts/demo_stress.py

# Customize the stress test
python scripts/demo_stress.py --nodes 15 --transactions 100 --mining-rounds 10
```

This demo:
1. Creates a network with 10+ nodes
2. Connects them in ring topology with shortcuts
3. Generates many transactions to test throughput
4. Measures TPS, propagation delay, and orphan rate
5. Displays comprehensive performance metrics

## 📊 Web Dashboard

Access the dashboard at **http://localhost:5000** when running demos.

Features:
- Real-time node status (chain length, balance, mining status)
- Mempool monitoring
- Peer connections visualization
- **Performance metrics**: TPS, block time, propagation delay, orphan rate
- Recent blocks table with mining statistics
- Auto-refresh every 2 seconds

## 🔬 Testing Fault Scenarios

### Network Partition

```python
from src.faults import FaultInjector

fault_injector = FaultInjector(nodes)
await fault_injector.partition_network(["node0", "node1"], ["node2", "node3"])
# ... mine blocks ...
await fault_injector.heal_partition()
```

### Node Crash/Recovery

```python
await fault_injector.crash_node("node1")
# ... continue operations ...
await fault_injector.restart_node("node1")
```

### Message Drop

```python
fault_injector.set_message_drop_rate("node0", 0.3)  # 30% drop rate
```

## 🎓 Educational Features

### Implemented (Iterations 1-3)

✅ **P2P Networking**
- Gossip protocol with duplicate suppression
- Mesh/ring topology support
- Asynchronous message handling

✅ **Blockchain & Consensus**
- SHA-256 hash-linked blocks
- Proof-of-Work with adjustable difficulty
- Longest-chain fork resolution

✅ **Transactions**
- Account-based model (balances + nonces)
- Transaction validation and signing
- Fee mechanism

✅ **Rewards System**
- Block rewards (50 coins per block)
- Transaction fee collection
- Coinbase transactions

✅ **Fault Tolerance**
- Network partition recovery
- Node crash/restart with chain resync
- Invalid transaction rejection

✅ **Merkle Trees**
- Binary Merkle tree for transaction aggregation
- O(log n) proof of inclusion
- Efficient transaction verification

✅ **Scalability Testing**
- Stress test with 10+ nodes
- Configurable network topology
- Performance benchmarking

✅ **Metrics & Monitoring**
- Transactions per second (TPS)
- Block propagation delay
- Orphan/stale block rate
- Confirmation latency

### Future Work (Optional)

⏳ Persistent storage  
⏳ Real ECDSA signatures (currently uses HMAC)

## 📁 Project Structure

```
Bitcoin (Blockchain)/
├── src/
│   ├── __init__.py
│   ├── transaction.py      # Transaction logic
│   ├── block.py            # Block structure with Merkle root
│   ├── blockchain.py       # Blockchain ledger
│   ├── mempool.py          # Transaction pool
│   ├── network.py          # P2P networking
│   ├── consensus.py        # Proof-of-Work
│   ├── node.py             # Complete node
│   ├── dashboard.py        # Web visualization with metrics
│   ├── faults.py           # Fault injection
│   ├── merkle.py           # Merkle tree implementation
│   └── metrics.py          # Performance metrics collection
├── scripts/
│   ├── demo_basic.py       # Basic demo
│   ├── demo_faults.py      # Fault tolerance demo
│   └── demo_stress.py      # Stress test (10+ nodes)
├── tests/
│   ├── test_transaction.py
│   ├── test_block.py
│   ├── test_blockchain.py
│   ├── test_merkle.py      # Merkle tree tests
│   └── test_metrics.py     # Metrics tests
├── requirements.txt
└── README.md
```

## 🔍 Key Concepts Demonstrated

### 1. Hash-Linked Immutability

Each block contains:
```python
{
    'index': 5,
    'previous_hash': '00a3f7b2...', 
    'transactions': [...],
    'nonce': 12847,
    'hash': '0012c4e9...'
}
```

Changing any past block invalidates all subsequent blocks.

### 2. Proof-of-Work Consensus

Mining requires finding a nonce such that:
```
SHA256(block_data + nonce).startswith('00')  # Difficulty = 2
```

This computational puzzle ensures:
- Agreement on the next block
- Resistance to trivial attacks
- Controlled block production rate

### 3. Gossip Protocol

Message propagation:
1. Node receives message
2. Checks if seen before (duplicate suppression)
3. Processes message
4. Forwards to all peers (except sender)

Results in network-wide propagation with O(log N) hops.

### 4. Longest-Chain Rule

When forks occur:
- Each partition mines its own chain
- Upon healing, nodes adopt the longest valid chain
- Ensures eventual consistency

### 5. Merkle Trees

Transaction aggregation:
```
        Merkle Root
        /         \
     H(AB)       H(CD)
     /   \       /   \
   H(A)  H(B)  H(C)  H(D)
    |     |     |     |
   Tx1   Tx2   Tx3   Tx4
```

Benefits:
- Single root hash represents all transactions
- O(log n) proof of inclusion
- Efficient light client verification

### 6. Performance Metrics

Real-time tracking of:
- **TPS**: Transactions processed per second
- **Block propagation delay**: Time for blocks to reach all nodes
- **Orphan rate**: Percentage of blocks not in main chain
- **Confirmation latency**: Time from tx submission to confirmation

## 🧪 Example Usage

```python
import asyncio
from src.node import BlockchainNode
from src.transaction import Transaction

async def example():
    # Create node
    node = BlockchainNode("node0", "127.0.0.1", 8000)
    await node.start()
    
    # Create transaction
    tx = Transaction(
        sender="alice",
        receiver="bob",
        amount=10.0,
        fee=0.5,
        nonce=0
    )
    tx.sign("alice")
    
    # Submit transaction
    await node.submit_transaction(tx)
    
    # Mine block
    block = await node.mine_next_block()
    print(f"Mined block: {block.hash}")

asyncio.run(example())
```

## 📈 Performance Notes

- **Difficulty 2**: ~0.1-1s per block (demo-friendly)
- **Difficulty 3**: ~1-10s per block
- **Difficulty 4**: ~10-100s per block

Adjust difficulty in node creation:
```python
node = BlockchainNode(..., difficulty=3)
```

## 🤝 Contributing

This is an educational project for Minerva University's Distributed Systems course (IL181.007).

---

**Note**: This is a simplified blockchain for educational purposes. It uses toy signatures (HMAC) instead of real cryptographic signatures (ECDSA) and is not suitable for production use.

