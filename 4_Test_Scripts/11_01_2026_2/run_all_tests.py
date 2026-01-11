"""
Run All Tests and Generate Report
==================================

Executes all test suites and generates a comprehensive test report.
"""
import pytest
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

# Test files to run
TEST_FILES = [
    "test_probabilities.py",
    "test_decision_intelligence.py",
    "test_ticket_archetypes.py",
    "test_portfolio_scoring.py",
    "test_end_to_end_flow.py"
]


def run_tests():
    """Run all test files and collect results."""
    test_dir = Path(__file__).parent
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_files": [],
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        },
        "failures": []
    }
    
    for test_file in TEST_FILES:
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"Warning: Test file {test_file} not found, skipping...")
            continue
        
        print(f"\n{'='*60}")
        print(f"Running {test_file}...")
        print(f"{'='*60}\n")
        
        # Run pytest on this file
        exit_code = pytest.main([
            str(test_path),
            "-v",
            "--tb=short",
            "-q"
        ])
        
        # Note: pytest.main returns 0 for success, non-zero for failures
        # We can't easily capture detailed results without using pytest's API
        # For now, we'll note the exit code
        
        file_result = {
            "file": test_file,
            "exit_code": exit_code,
            "status": "PASSED" if exit_code == 0 else "FAILED"
        }
        
        results["test_files"].append(file_result)
        
        if exit_code == 0:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
            results["failures"].append({
                "file": test_file,
                "exit_code": exit_code
            })
    
    results["summary"]["total_tests"] = len(results["test_files"])
    
    return results


def generate_report(results):
    """Generate test report in markdown format."""
    report_lines = [
        "# FOOTBALL PROBABILITY ENGINE – TEST REPORT",
        "=" * 50,
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Tester:** Automated Test Suite",
        f"**Code Version:** v2.0 (Professional Hardening)",
        "",
        "## 1. AUTOMATED TESTS",
        "-" * 50,
        "",
        f"**Total test files run:** {results['summary']['total_tests']}",
        f"**Tests passed:** {results['summary']['passed']}",
        f"**Tests failed:** {results['summary']['failed']}",
        "",
    ]
    
    if results["failures"]:
        report_lines.extend([
            "### Failures:",
            ""
        ])
        for failure in results["failures"]:
            report_lines.extend([
                f"- **{failure['file']}:**",
                f"  - Exit code: {failure['exit_code']}",
                f"  - Status: FAILED",
                ""
            ])
    else:
        report_lines.append("**No failures detected.**\n")
    
    report_lines.extend([
        "## 2. PROBABILITY & MODEL CHECKS",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] xG confidence propagated correctly",
        "- [ ] xG confidence clamped (0.1–1.0)",
        "- [ ] Dixon–Coles gating correct",
        "- [ ] dc_applied visible in API",
        "",
        "## 3. DECISION INTELLIGENCE",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] Hard contradictions block tickets",
        "- [ ] EV score monotonic with confidence",
        "- [ ] Structural penalties applied correctly",
        "- [ ] UDS threshold gating correct",
        "",
        "## 4. TICKET ARCHETYPES",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] Favorite Lock enforced",
        "- [ ] Draw Selective enforced",
        "- [ ] Away Edge enforced",
        "- [ ] Mixed-bias tickets prevented",
        "",
        "## 5. PORTFOLIO LOGIC",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] Correlation computed correctly",
        "- [ ] Correlation penalty applied",
        "- [ ] Portfolio EV prefers diverse tickets",
        "",
        "## 6. FRONTEND VALIDATION",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] Decision metrics visible",
        "- [ ] Contradiction warnings visible",
        "- [ ] No false confidence language",
        "",
        "## 7. DATABASE & LEARNING",
        "-" * 50,
        "",
        "**Note:** Run manual verification for:",
        "- [ ] decision_version stored",
        "- [ ] prediction_snapshot populated",
        "- [ ] ticket_pick populated",
        "",
        "## OVERALL RESULT",
        "-" * 50,
        "",
    ])
    
    if results["summary"]["failed"] == 0:
        report_lines.append("**PASS** ✅")
    elif results["summary"]["failed"] < results["summary"]["total_tests"]:
        report_lines.append("**CONDITIONAL PASS** ⚠️")
    else:
        report_lines.append("**FAIL** ❌")
    
    report_lines.extend([
        "",
        "## Notes / Observations",
        "",
        "- Automated tests completed",
        "- Manual verification checklist provided above",
        "- See detailed pytest output for specific test results",
        "",
        "## NEXT ACTIONS",
        "",
        "- [ ] Complete manual verification checklist",
        "- [ ] Review any test failures",
        "- [ ] Verify database schema updates",
        "- [ ] Test frontend integration",
        ""
    ])
    
    return "\n".join(report_lines)


def main():
    """Main test execution function."""
    print("=" * 60)
    print("FOOTBALL PROBABILITY ENGINE - TEST SUITE")
    print("=" * 60)
    print(f"Test execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run tests
    results = run_tests()
    
    # Generate report
    report = generate_report(results)
    
    # Save report
    report_file = Path(__file__).parent / "TEST_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    # Save JSON results
    json_file = Path(__file__).parent / "TEST_RESULTS.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("TEST EXECUTION COMPLETE")
    print("=" * 60)
    print(f"\nResults saved to:")
    print(f"  - {report_file}")
    print(f"  - {json_file}")
    print(f"\nSummary:")
    print(f"  - Total test files: {results['summary']['total_tests']}")
    print(f"  - Passed: {results['summary']['passed']}")
    print(f"  - Failed: {results['summary']['failed']}")
    
    return results["summary"]["failed"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

