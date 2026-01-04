"""
Continuous Test Runner
Runs comprehensive table tests continuously until all tables are populated
"""
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

def main():
    """Run tests continuously"""
    print("="*80)
    print("CONTINUOUS TABLE TEST RUNNER")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop")
    print("="*80)
    
    iteration = 0
    max_iterations = 1200  # Safety limit (1200 iterations × 1 second = 20 minutes max)
    
    try:
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}\n")
            
            # Run the comprehensive test
            result = subprocess.run(
                [sys.executable, "test_all_tables_comprehensive.py"],
                cwd=Path(__file__).parent,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n✅ Test iteration {iteration} completed successfully")
            else:
                print(f"\n⚠️  Test iteration {iteration} completed with errors (return code: {result.returncode})")
            
            # Wait before next iteration
            wait_time = 1  # 1 second for faster testing
            print(f"\n⏳ Waiting {wait_time} second before next iteration...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("STOPPED BY USER")
        print("="*80)
        print(f"Total iterations: {iteration}")
        print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise

if __name__ == "__main__":
    main()

