#!/usr/bin/env python3
"""
Run all unit tests for the blockchain system.

Usage:
    python scripts/run_tests.py              # Run all unit tests (no network tests)
    python scripts/run_tests.py -v           # Verbose output
    python scripts/run_tests.py --quick      # Skip slow tests
    python scripts/run_tests.py --core       # Run only core tests (fastest)

    # To include network integration tests:
    RUN_NETWORK_TESTS=1 python scripts/run_tests.py
"""

import sys
import os
import argparse
import unittest
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def discover_and_run_tests(verbose: bool = False, quick: bool = False):
    """Discover and run all tests in the tests directory."""

    print("=" * 70)
    print("BLOCKCHAIN SIMULATION - TEST SUITE")
    print("=" * 70)
    print()

    # Discover tests
    test_dir = os.path.join(os.path.dirname(__file__), "..", "tests")
    loader = unittest.TestLoader()

    if quick:
        # Skip network tests which can be slow
        print("⚡ Quick mode: Skipping network integration tests")
        suite = unittest.TestSuite()

        # Load specific test modules (excluding slow ones)
        quick_modules = [
            "test_transaction",
            "test_block",
            "test_blockchain",
            "test_merkle",
            "test_metrics",
            "test_orphans",
            "test_double_spend",
            "test_consensus",
        ]

        for module_name in quick_modules:
            try:
                module_path = os.path.join(test_dir, f"{module_name}.py")
                if os.path.exists(module_path):
                    tests = loader.discover(test_dir, pattern=f"{module_name}.py")
                    suite.addTests(tests)
            except Exception as e:
                print(f"  Warning: Could not load {module_name}: {e}")
    else:
        # Discover all tests
        suite = loader.discover(test_dir, pattern="test_*.py")

    # Count tests
    test_count = suite.countTestCases()
    print(f"📋 Discovered {test_count} tests")
    print()

    # Run tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)

    start_time = time.time()
    result = runner.run(suite)
    elapsed_time = time.time() - start_time

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"  Tests run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures:  {len(result.failures)}")
    print(f"  Errors:    {len(result.errors)}")
    print(f"  Time:      {elapsed_time:.2f}s")
    print()

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")

        if result.failures:
            print("\nFailed tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")

        if result.errors:
            print("\nTest errors:")
            for test, traceback in result.errors:
                print(f"  - {test}")

    print("=" * 70)

    return result.wasSuccessful()


def run_specific_tests():
    """Run tests from specific modules for quick verification."""

    from tests import (
        test_transaction,
        test_block,
        test_blockchain,
    )

    print("=" * 70)
    print("RUNNING CORE UNIT TESTS")
    print("=" * 70 + "\n")

    test_suites = [
        (
            "Transaction Tests",
            [
                test_transaction.test_transaction_creation,
                test_transaction.test_transaction_hash,
                test_transaction.test_transaction_signature,
                test_transaction.test_transaction_validation,
                test_transaction.test_coinbase_transaction,
                test_transaction.test_transaction_serialization,
            ],
        ),
        (
            "Block Tests",
            [
                test_block.test_block_creation,
                test_block.test_block_hash,
                test_block.test_block_mining,
                test_block.test_block_validation,
                test_block.test_genesis_block,
                test_block.test_block_serialization,
            ],
        ),
        (
            "Blockchain Tests",
            [
                test_blockchain.test_blockchain_creation,
                test_blockchain.test_add_block,
                test_blockchain.test_balance_tracking,
                test_blockchain.test_transaction_validation,
                test_blockchain.test_nonce_tracking,
                test_blockchain.test_fork_resolution,
                test_blockchain.test_chain_validation,
            ],
        ),
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
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print("\nFailed Tests:")
        for suite, test, error in failed_tests:
            print(f"  - [{suite}] {test}: {error}")
        print("\n" + "=" * 70)
        return False
    else:
        print("\n✅ ALL TESTS PASSED!")
        print("=" * 70)
        return True


def main():
    parser = argparse.ArgumentParser(description="Run blockchain system tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: skip slow network integration tests",
    )
    parser.add_argument(
        "--core",
        action="store_true",
        help="Run only core unit tests (fast, no async)",
    )

    args = parser.parse_args()

    if args.core:
        success = run_specific_tests()
    else:
        success = discover_and_run_tests(verbose=args.verbose, quick=args.quick)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
