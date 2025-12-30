#!/usr/bin/env python3
"""
Run all database and integration tests

Usage:
    python run_all_tests.py
    python run_all_tests.py --verbose
    python run_all_tests.py --coverage
"""
import sys
import subprocess
import argparse


def run_tests(test_file=None, verbose=False, coverage=False):
    """Run pytest tests"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append(".")
    
    cmd.extend([
        "--tb=short",
        "-x",  # Stop on first failure
    ])
    
    print("=" * 60)
    print("Running Database Tests")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    print()
    
    result = subprocess.run(cmd, cwd="Db_Tests")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run database tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--file", "-f", help="Run specific test file")
    
    args = parser.parse_args()
    
    success = run_tests(
        test_file=args.file,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

