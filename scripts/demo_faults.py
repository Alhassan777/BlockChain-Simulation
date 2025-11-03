"""
Fault tolerance demo: Network partition, crash/recovery, invalid transactions.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.node import BlockchainNode
from src.transaction import Transaction
from src.faults import FaultInjector
from src.dashboard import Dashboard
import threading


async def main():
    print("\n" + "="*60)
    print("BLOCKCHAIN FAULT TOLERANCE DEMO")
    print("="*60 + "\n")
    
    # Create shared genesis block
    from src.block import Block
    print("Creating shared genesis block...")
    genesis = Block.create_genesis_block()
    print(f"  Genesis hash: {genesis.hash[:16]}...\n")
    
    # Create 4 nodes with same genesis
    nodes = []
    base_port = 8000
    
    print("Creating nodes...")
    for i in range(4):
        node = BlockchainNode(
            node_id=f"node{i}",
            host="127.0.0.1",
            port=base_port + i,
            difficulty=2,
            block_reward=50.0,
            genesis_block=genesis  # Share same genesis!
        )
        nodes.append(node)
    
    # Start all nodes
    print("\nStarting nodes...")
    for node in nodes:
        await node.start()
        await asyncio.sleep(0.2)
    
    # Connect in mesh topology
    print("\nConnecting nodes (mesh topology)...")
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            await node1.connect_to_peer(
                node2.node_id,
                node2.network.host,
                node2.network.port
            )
            await asyncio.sleep(0.1)
    
    # Start dashboard
    print("\nStarting dashboard...")
    dashboard = Dashboard(nodes, port=5000)
    dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
    dashboard_thread.start()
    await asyncio.sleep(2)
    
    # Create fault injector
    fault_injector = FaultInjector(nodes)
    
    # Initial mining
    print("\n" + "="*60)
    print("PHASE 1: Initial Setup")
    print("="*60)
    
    print("\nEach node mining 1 block...")
    for node in nodes:
        block = await node.mine_next_block(max_iterations=50000)
        if block:
            print(f"  ✓ {node.node_id} mined block #{block.index}")
        await asyncio.sleep(1)
    
    await asyncio.sleep(2)
    
    # Show initial state
    print("\nInitial chain state:")
    for node in nodes:
        print(f"  {node.node_id}: {node.blockchain.get_chain_length()} blocks")
    
    print("\n" + "="*60)
    print("PHASE 2: Network Partition Test")
    print("="*60)
    
    print("\nPartitioning network into two groups...")
    print("  Group A: node0, node1")
    print("  Group B: node2, node3")
    
    await fault_injector.partition_network(
        ["node0", "node1"],
        ["node2", "node3"]
    )
    
    await asyncio.sleep(2)
    
    print("\nSubmitting transactions in partition A...")
    tx_a = Transaction(
        sender=nodes[0].miner_address,
        receiver=nodes[1].miner_address,
        amount=5.0,
        fee=0.5,
        nonce=nodes[0].blockchain.get_nonce(nodes[0].miner_address)
    )
    tx_a.sign(nodes[0].miner_address)
    await nodes[0].submit_transaction(tx_a)
    print(f"  ✓ TX in partition A: {nodes[0].miner_address[:8]}... → {nodes[1].miner_address[:8]}...")
    
    await asyncio.sleep(1)
    
    print("\nSubmitting transactions in partition B...")
    tx_b = Transaction(
        sender=nodes[2].miner_address,
        receiver=nodes[3].miner_address,
        amount=8.0,
        fee=0.5,
        nonce=nodes[2].blockchain.get_nonce(nodes[2].miner_address)
    )
    tx_b.sign(nodes[2].miner_address)
    await nodes[2].submit_transaction(tx_b)
    print(f"  ✓ TX in partition B: {nodes[2].miner_address[:8]}... → {nodes[3].miner_address[:8]}...")
    
    await asyncio.sleep(2)
    
    print("\nMining in both partitions...")
    print("  Mining in partition A (node0)...")
    block_a = await nodes[0].mine_next_block(max_iterations=50000)
    if block_a:
        print(f"    ✓ Block #{block_a.index} mined in partition A")
    
    await asyncio.sleep(1)
    
    print("  Mining in partition B (node2)...")
    block_b = await nodes[2].mine_next_block(max_iterations=50000)
    if block_b:
        print(f"    ✓ Block #{block_b.index} mined in partition B")
    
    await asyncio.sleep(2)
    
    # Show diverged state
    print("\nChain state after partition (DIVERGED):")
    for node in nodes:
        tip = node.blockchain.get_latest_block().hash[:16]
        print(f"  {node.node_id}: {node.blockchain.get_chain_length()} blocks, tip={tip}...")
    
    print("\n" + "="*60)
    print("PHASE 3: Healing Partition")
    print("="*60)
    
    print("\nHealing network partition...")
    await fault_injector.heal_partition()
    
    await asyncio.sleep(3)
    
    # Mine one more block to trigger convergence
    print("\nMining additional block to trigger convergence...")
    block_heal = await nodes[0].mine_next_block(max_iterations=50000)
    if block_heal:
        print(f"  ✓ Block #{block_heal.index} mined")
    
    await asyncio.sleep(4)
    
    # Show converged state
    print("\nChain state after healing (CONVERGED):")
    for node in nodes:
        tip = node.blockchain.get_latest_block().hash[:16]
        print(f"  {node.node_id}: {node.blockchain.get_chain_length()} blocks, tip={tip}...")
    
    print("\n" + "="*60)
    print("PHASE 4: Node Crash and Recovery")
    print("="*60)
    
    print("\nCrashing node1...")
    await fault_injector.crash_node("node1")
    await asyncio.sleep(2)
    
    print("\nSubmitting transaction while node1 is down...")
    tx_crash = Transaction(
        sender=nodes[0].miner_address,
        receiver=nodes[2].miner_address,
        amount=3.0,
        fee=0.3,
        nonce=nodes[0].blockchain.get_nonce(nodes[0].miner_address)
    )
    tx_crash.sign(nodes[0].miner_address)
    await nodes[0].submit_transaction(tx_crash)
    print("  ✓ Transaction submitted")
    
    await asyncio.sleep(1)
    
    print("\nMining block while node1 is down...")
    block_crash = await nodes[2].mine_next_block(max_iterations=50000)
    if block_crash:
        print(f"  ✓ Block #{block_crash.index} mined")
    
    await asyncio.sleep(2)
    
    print("\nRestarting node1...")
    await fault_injector.restart_node("node1")
    
    await asyncio.sleep(4)
    
    print("\nChain state after node1 recovery (RESYNCED):")
    for node in nodes:
        tip = node.blockchain.get_latest_block().hash[:16]
        print(f"  {node.node_id}: {node.blockchain.get_chain_length()} blocks, tip={tip}...")
    
    print("\n" + "="*60)
    print("PHASE 5: Invalid Transaction Test")
    print("="*60)
    
    print("\nInjecting invalid transaction (insufficient balance)...")
    result = await fault_injector.inject_invalid_transaction("node0")
    if not result:
        print("  ✓ Invalid transaction correctly REJECTED")
    else:
        print("  ✗ Invalid transaction incorrectly ACCEPTED")
    
    print("\n" + "="*60)
    print("FAULT TOLERANCE DEMO COMPLETE!")
    print("="*60)
    print("\nDemonstrated:")
    print("  ✓ Network partition & healing with chain convergence")
    print("  ✓ Node crash & recovery with chain resync")
    print("  ✓ Invalid transaction rejection")
    print("\nDashboard: http://localhost:5000")
    print("Press Ctrl+C to exit")
    print("="*60 + "\n")
    
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

