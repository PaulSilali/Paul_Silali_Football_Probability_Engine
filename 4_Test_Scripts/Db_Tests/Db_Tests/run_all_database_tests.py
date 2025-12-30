#!/usr/bin/env python3
"""
Run all database tests as specified in RUN_TESTS.md

This script:
1. Checks database connection
2. Runs full test suite with database
3. Checks for missing tables using test_table_completeness.py
4. Verifies API endpoints work correctly
"""
import sys
import subprocess
import os
from pathlib import Path

# Set up environment
backend_dir = Path(__file__).parent.parent / "2_Backend_Football_Probability_Engine"
if backend_dir.exists():
    os.environ['PYTHONPATH'] = str(backend_dir)

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def run_test(test_file, test_name=None):
    """Run a specific test file"""
    cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
    if test_name:
        cmd.append(f"::{test_name}")
    
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    if test_name:
        print(f"Test: {test_name}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    """Run all tests"""
    print("="*70)
    print("Football Probability Engine - Full Test Suite")
    print("="*70)
    print("\nThis will run:")
    print("1. Database connection check")
    print("2. Full test suite with database")
    print("3. Check for missing tables")
    print("4. Verify API endpoints")
    print("="*70)
    
    results = {}
    
    # Step 1: Check database connection (via test_no_db first)
    print("\n[STEP 1] Running tests that don't require database...")
    results['no_db'] = run_test("test_no_db.py")
    
    # Step 2: Check table completeness
    print("\n[STEP 2] Checking table completeness...")
    results['table_completeness'] = run_test("test_table_completeness.py")
    
    # Step 3: Test database schema
    print("\n[STEP 3] Testing database schema...")
    results['schema'] = run_test("test_database_schema.py")
    
    # Step 4: Test backend API
    print("\n[STEP 4] Testing backend API endpoints...")
    results['api'] = run_test("test_backend_api.py")
    
    # Step 5: Test integration
    print("\n[STEP 5] Testing frontend-backend integration...")
    results['integration'] = run_test("test_integration.py")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} test suites passed")
    print("="*70)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

