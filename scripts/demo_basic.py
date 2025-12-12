"""
Basic demo: Start nodes, submit transactions, mine blocks.
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
from src.dashboard import Dashboard
import threading
import time

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


async def main():
    flush_print("\n" + "=" * 60)
    flush_print("BLOCKCHAIN BASIC DEMO")
    flush_print("=" * 60 + "\n")

    # Create shared genesis block
    from src.block import Block

    flush_print("Creating shared genesis block...")
    genesis = Block.create_genesis_block()
    flush_print(f"  Genesis hash: {genesis.hash[:16]}...\n")

    # Create 4 nodes with same genesis
    nodes = []
    base_port = 8000

    # Check if ports are available
    flush_print("Checking port availability...")
    for i in range(4):
        if not check_port_available(base_port + i):
            flush_print(
                f"  ⚠ Port {base_port + i} is in use! Please close other instances."
            )
            return
    flush_print("  ✓ All ports available\n")

    flush_print("Creating nodes...")
    for i in range(4):
        node = BlockchainNode(
            node_id=f"node{i}",
            host="127.0.0.1",
            port=base_port + i,
            difficulty=2,  # Easy difficulty for demo
            block_reward=50.0,
            miner_address=f"miner{i}",
            genesis_block=genesis,  # Share same genesis!
        )
        nodes.append(node)
        flush_print(f"  - Node {i} created on port {base_port + i}")

    # Start all nodes
    flush_print("\nStarting nodes...")
    for node in nodes:
        await node.start()
        await asyncio.sleep(0.1)

    # Connect nodes in a ring topology
    print("\nConnecting nodes (ring topology)...")
    for i in range(len(nodes)):
        next_i = (i + 1) % len(nodes)
        await nodes[i].connect_to_peer(
            nodes[next_i].node_id,
            nodes[next_i].network.host,
            nodes[next_i].network.port,
        )
        await asyncio.sleep(0.1)

    print("\n" + "=" * 60)
    print("Network established! Nodes connected.")
    print("=" * 60)

    # Start dashboard in separate thread
    print("\nStarting web dashboard...")
    dashboard = Dashboard(nodes, port=5001)
    dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
    dashboard_thread.start()
    await asyncio.sleep(2)

    # Give nodes initial balances via mining
    print("\n" + "=" * 60)
    print("PHASE 1: Initial Mining (giving nodes coins)")
    print("=" * 60)
    print("Mining empty blocks (coinbase only) to bootstrap the economy...\n")

    # Mine blocks sequentially to avoid race conditions
    for round_num in range(2):  # 2 rounds
        for node in nodes:
            print(f"Round {round_num + 1}: {node.node_id} mining block...")
            block = await node.mine_next_block(max_iterations=50000)
            if block:
                print(f"  ✓ Block #{block.index} mined by {node.node_id}")
                print(
                    f"  ✓ {node.node_id} balance: {node.blockchain.get_balance(node.miner_address):.2f} coins"
                )
            else:
                print(f"  ✗ Mining stopped (another node mined first)")

            # Wait for block propagation to all nodes
            await asyncio.sleep(2)

    # Verify synchronization
    print("\nVerifying chain synchronization...")
    tips = [node.blockchain.get_latest_block().hash for node in nodes]
    if len(set(tips)) == 1:
        print("  ✓ All nodes have the same chain tip!")
    else:
        print(f"  ⚠ Warning: Nodes have different chain tips: {set(tips)}")

    print("\nChain status after initial mining:")
    for node in nodes:
        print(
            f"  {node.node_id}: {node.blockchain.get_chain_length()} blocks, balance={node.blockchain.get_balance(node.miner_address):.2f} coins"
        )

    print("\n" + "=" * 60)
    print("PHASE 2: Transaction Propagation Test")
    print("=" * 60)

    # Create and submit transactions
    print("\nSubmitting transactions...")

    # Transaction 1: node0 -> node1
    tx1 = Transaction(
        sender="miner0",
        receiver="miner1",
        amount=10.0,
        fee=0.5,
        nonce=nodes[0].blockchain.get_nonce("miner0"),
    )
    tx1.sign("miner0")
    await nodes[0].submit_transaction(tx1)
    print(f"  ✓ TX1: miner0 → miner1 (10 coins, fee=0.5)")

    await asyncio.sleep(1)

    # Transaction 2: node1 -> node2
    tx2 = Transaction(
        sender="miner1",
        receiver="miner2",
        amount=15.0,
        fee=1.0,
        nonce=nodes[1].blockchain.get_nonce("miner1"),
    )
    tx2.sign("miner1")
    await nodes[1].submit_transaction(tx2)
    print(f"  ✓ TX2: miner1 → miner2 (15 coins, fee=1.0)")

    await asyncio.sleep(1)

    # Transaction 3: node2 -> node3
    tx3 = Transaction(
        sender="miner2",
        receiver="miner3",
        amount=20.0,
        fee=0.75,
        nonce=nodes[2].blockchain.get_nonce("miner2"),
    )
    tx3.sign("miner2")
    await nodes[2].submit_transaction(tx3)
    print(f"  ✓ TX3: miner2 → miner3 (20 coins, fee=0.75)")

    # Wait for gossip propagation
    print("\nWaiting for transaction propagation...")
    await asyncio.sleep(3)

    # Check mempool sizes
    print("\nMempool status:")
    for node in nodes:
        print(f"  {node.node_id}: {node.mempool.size()} transactions")

    print("\n" + "=" * 60)
    print("PHASE 3: Mining Transactions into Blocks")
    print("=" * 60)

    # Mine transactions
    print(f"\nnode3 mining transactions into block...")
    block = await nodes[3].mine_next_block(max_iterations=100000)
    if block:
        print(
            f"  ✓ Block #{block.index} mined with {len(block.transactions)} transactions"
        )
        print(f"  ✓ node3 received reward + fees: {block.transactions[0].amount}")

    await asyncio.sleep(2)

    # Check final state
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    for node in nodes:
        status = node.get_status()
        print(f"\n{status['node_id']}:")
        print(f"  Chain length: {status['chain_length']}")
        print(f"  Chain tip: {status['chain_tip'][:16]}...")
        print(f"  Balance: {status['balance']:.2f} coins")
        print(f"  Mempool: {status['mempool_size']} transactions")
        print(f"  Peers: {status['peer_count']}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE!")
    print("Dashboard running at http://localhost:5001")
    print("Press Ctrl+C to exit")
    print("=" * 60 + "\n")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        for node in nodes:
            await node.stop()


if __name__ == "__main__":
    asyncio.run(main())
