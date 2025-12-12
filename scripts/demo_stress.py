"""
Stress test demo: Scale up to 10+ nodes and measure performance metrics.
Tests network scalability, throughput, and propagation characteristics.
"""

import asyncio
import sys
import os

# Windows-specific: Set event loop policy before any async operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.node import BlockchainNode
from src.transaction import Transaction
from src.block import Block
from src.dashboard import Dashboard
from src.metrics import get_metrics_collector, reset_metrics
import threading
import time
import random

# Force unbuffered output for real-time display
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


def flush_print(*args, **kwargs):
    """Print with immediate flush."""
    print(*args, **kwargs)
    sys.stdout.flush()


def check_port_available(port):
    """Check if a port is available."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


async def create_nodes(num_nodes: int, genesis: Block, difficulty: int = 2):
    """Create and start multiple nodes."""
    nodes = []
    base_port = 8000

    print(f"Creating {num_nodes} nodes...")
    for i in range(num_nodes):
        node = BlockchainNode(
            node_id=f"node{i}",
            host="127.0.0.1",
            port=base_port + i,
            difficulty=difficulty,
            block_reward=50.0,
            miner_address=f"miner{i}",
            genesis_block=genesis,
        )
        nodes.append(node)

    # Start all nodes
    print("Starting nodes...")
    for node in nodes:
        await node.start()
        await asyncio.sleep(0.02)  # Small delay between starts

    return nodes


async def connect_mesh(nodes):
    """Connect nodes in a full mesh topology."""
    print("Connecting nodes in mesh topology...")
    connection_count = 0

    for i, node1 in enumerate(nodes):
        for node2 in nodes[i + 1 :]:
            await node1.connect_to_peer(
                node2.node_id, node2.network.host, node2.network.port
            )
            connection_count += 1
            await asyncio.sleep(0.01)  # Small delay between connections

    print(f"  Created {connection_count} connections")


async def connect_ring_with_shortcuts(nodes, shortcut_count: int = 5):
    """
    Connect nodes in a ring with random shortcuts.
    More realistic topology than full mesh for large networks.
    """
    print("Connecting nodes in ring topology with shortcuts...")
    n = len(nodes)

    # Create ring
    for i in range(n):
        next_i = (i + 1) % n
        await nodes[i].connect_to_peer(
            nodes[next_i].node_id,
            nodes[next_i].network.host,
            nodes[next_i].network.port,
        )
        await asyncio.sleep(0.01)

    # Add random shortcuts
    shortcuts_added = 0
    while shortcuts_added < shortcut_count:
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)

        # Skip if same node or adjacent in ring
        if abs(i - j) <= 1 or abs(i - j) == n - 1:
            continue

        # Check if not already connected
        if nodes[j].node_id not in nodes[i].network.peers:
            await nodes[i].connect_to_peer(
                nodes[j].node_id, nodes[j].network.host, nodes[j].network.port
            )
            shortcuts_added += 1
            await asyncio.sleep(0.01)

    print(f"  Created ring + {shortcut_count} shortcuts")


async def bootstrap_economy(nodes, blocks_per_node: int = 1):
    """Mine initial blocks to give nodes coins."""
    print(f"\nBootstrapping economy ({blocks_per_node} block(s) per node)...")

    for round_num in range(blocks_per_node):
        for node in nodes:
            block = await node.mine_next_block(max_iterations=50000)
            if block:
                print(
                    f"  Round {round_num + 1}: {node.node_id} mined block #{block.index}"
                )
            await asyncio.sleep(0.2)  # Let block propagate


async def generate_transactions(nodes, count: int, delay_ms: int = 100):
    """Generate random transactions between nodes."""
    print(f"\nGenerating {count} random transactions...")

    for i in range(count):
        # Pick random sender and receiver
        sender_node = random.choice(nodes)
        receiver_node = random.choice([n for n in nodes if n != sender_node])

        sender_balance = sender_node.blockchain.get_balance(sender_node.miner_address)
        if sender_balance < 1.5:  # Need at least 1.0 + fee
            continue

        # Create transaction
        amount = min(random.uniform(0.5, 5.0), sender_balance - 0.5)
        tx = Transaction(
            sender=sender_node.miner_address,
            receiver=receiver_node.miner_address,
            amount=amount,
            fee=random.uniform(0.01, 0.1),
            nonce=sender_node.blockchain.get_nonce(sender_node.miner_address),
        )
        tx.sign(sender_node.miner_address)

        await sender_node.submit_transaction(tx)

        if (i + 1) % 10 == 0:
            print(f"  Submitted {i + 1}/{count} transactions")

        await asyncio.sleep(delay_ms / 1000.0)

    print(f"  ✓ Submitted {count} transactions")


async def mine_transactions(nodes, rounds: int = 3):
    """Have nodes compete to mine transactions."""
    print(f"\nMining transactions ({rounds} rounds)...")

    for round_num in range(rounds):
        # Pick a random miner
        miner = random.choice(nodes)

        print(f"  Round {round_num + 1}: {miner.node_id} mining...")
        block = await miner.mine_next_block(max_iterations=100000)

        if block:
            print(
                f"    ✓ Mined block #{block.index} with {len(block.transactions)} transactions"
            )

        await asyncio.sleep(1)  # Let block propagate


async def verify_convergence(nodes):
    """Verify all nodes have converged to the same chain."""
    print("\nVerifying chain convergence...")

    tips = {}
    for node in nodes:
        tip = node.blockchain.get_latest_block().hash
        tips[node.node_id] = tip

    unique_tips = set(tips.values())

    if len(unique_tips) == 1:
        print(f"  ✓ All {len(nodes)} nodes converged to the same chain!")
        return True
    else:
        print(f"  ⚠ Warning: {len(unique_tips)} different chain tips detected:")
        for tip in unique_tips:
            count = sum(1 for t in tips.values() if t == tip)
            print(f"    - {tip[:16]}... ({count} nodes)")
        return False


async def run_stress_test(
    num_nodes: int = 10, difficulty: int = 2, tx_count: int = 50, mining_rounds: int = 5
):
    """Run the full stress test."""

    print("\n" + "=" * 70)
    print(f"BLOCKCHAIN STRESS TEST - {num_nodes} NODES")
    print("=" * 70)

    # Reset metrics
    reset_metrics()
    metrics = get_metrics_collector()

    # Create shared genesis block
    print("\nCreating shared genesis block...")
    genesis = Block.create_genesis_block()
    print(f"  Genesis hash: {genesis.hash[:16]}...")

    # Create and start nodes
    nodes = await create_nodes(num_nodes, genesis, difficulty)

    # Connect topology based on network size
    if num_nodes <= 6:
        await connect_mesh(nodes)
    else:
        # Use ring with shortcuts for larger networks
        shortcut_count = min(num_nodes, 10)
        await connect_ring_with_shortcuts(nodes, shortcut_count)

    await asyncio.sleep(1)

    # Start dashboard
    print("\nStarting web dashboard...")
    dashboard = Dashboard(nodes, port=5001)
    dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
    dashboard_thread.start()
    await asyncio.sleep(2)

    # Phase 1: Bootstrap
    print("\n" + "=" * 70)
    print("PHASE 1: Bootstrap Economy")
    print("=" * 70)
    await bootstrap_economy(nodes, blocks_per_node=1)
    await asyncio.sleep(2)

    # Phase 2: Transaction stress
    print("\n" + "=" * 70)
    print("PHASE 2: Transaction Stress Test")
    print("=" * 70)

    start_time = time.time()
    await generate_transactions(nodes, count=tx_count, delay_ms=50)
    tx_generation_time = time.time() - start_time

    print(f"\n  Transaction generation rate: {tx_count / tx_generation_time:.2f} tx/s")

    await asyncio.sleep(2)

    # Phase 3: Mining stress
    print("\n" + "=" * 70)
    print("PHASE 3: Mining Stress Test")
    print("=" * 70)

    start_time = time.time()
    await mine_transactions(nodes, rounds=mining_rounds)
    mining_time = time.time() - start_time

    await asyncio.sleep(3)

    # Phase 4: Verification
    print("\n" + "=" * 70)
    print("PHASE 4: Verification")
    print("=" * 70)

    converged = await verify_convergence(nodes)

    # Phase 5: Metrics Summary
    print("\n" + "=" * 70)
    print("PHASE 5: Performance Metrics")
    print("=" * 70)

    metrics.print_summary()

    # Node summary
    print("\n" + "=" * 70)
    print("NODE STATUS SUMMARY")
    print("=" * 70)

    print(f"\n{'Node':<10} {'Blocks':<10} {'Balance':<12} {'Mempool':<10} {'Peers':<8}")
    print("-" * 50)

    for node in nodes:
        status = node.get_status()
        print(
            f"{status['node_id']:<10} "
            f"{status['chain_length']:<10} "
            f"{status['balance']:<12.2f} "
            f"{status['mempool_size']:<10} "
            f"{status['peer_count']:<8}"
        )

    # Final summary
    print("\n" + "=" * 70)
    print("STRESS TEST COMPLETE!")
    print("=" * 70)
    print(f"\n✓ Tested with {num_nodes} nodes")
    print(f"✓ Generated {tx_count} transactions in {tx_generation_time:.2f}s")
    print(f"✓ Mined {mining_rounds} rounds in {mining_time:.2f}s")
    print(f"✓ Chain convergence: {'PASSED' if converged else 'FAILED'}")
    print(f"\nDashboard: http://localhost:5001")
    print("Press Ctrl+C to exit")
    print("=" * 70 + "\n")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        for node in nodes:
            await node.stop()


async def main():
    """Main entry point with configurable parameters."""
    import argparse

    parser = argparse.ArgumentParser(description="Blockchain Stress Test")
    parser.add_argument(
        "--nodes", type=int, default=10, help="Number of nodes (default: 10)"
    )
    parser.add_argument(
        "--difficulty", type=int, default=2, help="Mining difficulty (default: 2)"
    )
    parser.add_argument(
        "--transactions",
        type=int,
        default=50,
        help="Number of transactions (default: 50)",
    )
    parser.add_argument(
        "--mining-rounds", type=int, default=5, help="Mining rounds (default: 5)"
    )

    args = parser.parse_args()

    await run_stress_test(
        num_nodes=args.nodes,
        difficulty=args.difficulty,
        tx_count=args.transactions,
        mining_rounds=args.mining_rounds,
    )


if __name__ == "__main__":
    asyncio.run(main())
