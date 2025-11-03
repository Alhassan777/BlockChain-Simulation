"""
Run all unit tests for the blockchain system.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests import test_transaction, test_block, test_blockchain

def run_all_tests():
    """Run all test suites."""
    print("="*60)
    print("RUNNING BLOCKCHAIN SYSTEM TESTS")
    print("="*60 + "\n")
    
    test_suites = [
        ("Transaction Tests", [
            test_transaction.test_transaction_creation,
            test_transaction.test_transaction_hash,
            test_transaction.test_transaction_signature,
            test_transaction.test_transaction_validation,
            test_transaction.test_coinbase_transaction,
            test_transaction.test_transaction_serialization,
        ]),
        ("Block Tests", [
            test_block.test_block_creation,
            test_block.test_block_hash,
            test_block.test_block_mining,
            test_block.test_block_validation,
            test_block.test_genesis_block,
            test_block.test_block_serialization,
        ]),
        ("Blockchain Tests", [
            test_blockchain.test_blockchain_creation,
            test_blockchain.test_add_block,
            test_blockchain.test_balance_tracking,
            test_blockchain.test_transaction_validation,
            test_blockchain.test_nonce_tracking,
            test_blockchain.test_fork_resolution,
            test_blockchain.test_chain_validation,
        ]),
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for suite_name, tests in test_suites:
        print(f"\n{suite_name}")
        print("-" * 40)
        
        for test_func in tests:
            test_name = test_func.__name__
            total_tests += 1
            
            try:
                test_func()
                print(f"  ✓ {test_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  ✗ {test_name}: {e}")
                failed_tests.append((suite_name, test_name, str(e)))
            except Exception as e:
                print(f"  ✗ {test_name}: Unexpected error: {e}")
                failed_tests.append((suite_name, test_name, f"Unexpected: {e}"))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for suite, test, error in failed_tests:
            print(f"  - [{suite}] {test}: {error}")
        print("\n" + "="*60)
        return False
    else:
        print("\n✓ ALL TESTS PASSED!")
        print("="*60)
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

