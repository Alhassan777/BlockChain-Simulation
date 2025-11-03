# Quick Start Guide

## For the Midterm Check-in Demo

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Demo (Choose One)

#### Option A: Basic Demo (Recommended for first run)
Shows transaction propagation and mining:

```bash
python scripts/demo_basic.py
```

**What it demonstrates:**
- 4 nodes connecting in a P2P network
- Transaction submission and propagation
- Block mining with Proof-of-Work
- Chain synchronization across nodes

#### Option B: Fault Tolerance Demo (For advanced demo)
Shows partition recovery and crash handling:

```bash
python scripts/demo_faults.py
```

**What it demonstrates:**
- Network partition → fork → healing → convergence
- Node crash → restart → chain resync
- Invalid transaction rejection

### 3. Open the Dashboard

While the demo is running, open your browser to:

```
http://localhost:5000
```

The dashboard auto-refreshes every 2 seconds and shows:
- Chain length and tip hash for each node
- Node balances (coins earned from mining)
- Mempool size (pending transactions)
- Peer connections
- Mining status

### 4. Watch the Terminal Output

The terminal will show detailed logs of:
- Nodes starting and connecting
- Transactions being created and propagated
- Mining progress (nonce attempts, time taken)
- Blocks being added to chains
- Final state summary

### 5. Stop the Demo

Press `Ctrl+C` in the terminal to gracefully shut down all nodes.

---

## For Testing Individual Components

### Run Unit Tests

```bash
python scripts/run_tests.py
```

This tests:
- Transaction validation and signing
- Block hashing and mining
- Blockchain state management
- Fork resolution logic

---

## Recording Your Demo Video

1. **Start the demo** (`python scripts/demo_basic.py` or `demo_faults.py`)
2. **Arrange windows**: Terminal on left, browser (dashboard) on right
3. **Increase font size** in terminal for readability
4. **Record 2-5 minutes** showing:
   - Nodes starting and connecting
   - Dashboard with real-time updates
   - Transaction propagation (mempool growth)
   - Block mining (chain length increasing)
   - For faults demo: partition/heal or crash/restart
5. **Narrate** what's happening as you record

See `docs/DEMO_SCRIPT.md` for detailed recording guidance.

---

## Common Issues

### Port Already in Use
If you see "Address already in use" errors:
- Kill any previous demo processes
- Change ports in the demo script (e.g., `base_port = 8100`)

### Module Not Found
If you see import errors:
- Make sure you're in the project root directory
- Run: `export PYTHONPATH=$PYTHONPATH:$(pwd)` (Linux/Mac)
- Or: `$env:PYTHONPATH="$env:PYTHONPATH;$(pwd)"` (Windows PowerShell)

### Mining Too Slow
If mining takes too long:
- Difficulty is set to 2 (should take <1 second per block)
- Check CPU usage - close other applications

---

## Next Steps After Midterm

- [ ] Scale to 10+ nodes
- [ ] Implement Merkle trees
- [ ] Add metrics collection
- [ ] Create blockchain explorer UI
- [ ] Performance benchmarking

---

**Need help?** Check `README.md` for detailed documentation or `docs/DEMO_SCRIPT.md` for recording tips.

