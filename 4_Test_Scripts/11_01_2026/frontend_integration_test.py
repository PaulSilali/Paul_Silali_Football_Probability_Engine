"""
FRONTEND INTEGRATION TEST
==========================

Tests all frontend pages and their API connections.
Simulates user interactions and verifies backend connectivity.
"""

import sys
import os
import json
import requests
from typing import Dict, List, Any
from datetime import datetime

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')

# Frontend pages and their expected API calls
FRONTEND_PAGES = {
    'Dashboard': {
        'endpoints': [
            ('GET', '/dashboard/summary'),
            ('GET', '/model/health'),
            ('GET', '/data/freshness'),
        ]
    },
    'JackpotInput': {
        'endpoints': [
            ('GET', '/jackpots/templates'),
            ('POST', '/jackpots'),
            ('GET', '/teams/all'),
        ]
    },
    'ProbabilityOutput': {
        'endpoints': [
            ('GET', '/probabilities/{jackpot_id}/probabilities'),
            ('POST', '/probabilities/{jackpot_id}/save-result'),
            ('GET', '/probabilities/{jackpot_id}/saved-results'),
        ]
    },
    'TicketConstruction': {
        'endpoints': [
            ('POST', '/tickets/generate'),
            ('POST', '/tickets/save'),
            ('GET', '/probabilities/{jackpot_id}/probabilities'),
        ]
    },
    'JackpotValidation': {
        'endpoints': [
            ('GET', '/probabilities/saved-results/all'),
            ('GET', '/probabilities/{jackpot_id}/probabilities'),
            ('PUT', '/probabilities/saved-results/{id}/actual-results'),
        ]
    },
    'SureBet': {
        'endpoints': [
            ('POST', '/sure-bet/validate'),
            ('POST', '/sure-bet/analyze'),
            ('POST', '/sure-bet/save-list'),
            ('GET', '/sure-bet/saved-lists'),
            ('POST', '/sure-bet/import-pdf'),
        ]
    },
    'DataIngestion': {
        'endpoints': [
            ('POST', '/data/batch-download'),
            ('GET', '/data/batches'),
            ('GET', '/data/league-stats'),
        ]
    },
    'MLTraining': {
        'endpoints': [
            ('POST', '/model/train'),
            ('GET', '/model/training-history'),
            ('GET', '/model/versions'),
        ]
    },
    'ModelHealth': {
        'endpoints': [
            ('GET', '/model/health'),
            ('GET', '/model/versions'),
        ]
    },
    'FeatureStore': {
        'endpoints': [
            ('GET', '/feature-store/stats'),
            ('GET', '/feature-store/teams'),
        ]
    },
    'DrawIngestion': {
        'endpoints': [
            ('POST', '/draw-ingestion/league-priors'),
            ('GET', '/draw-ingestion/league-priors/summary'),
            ('POST', '/draw-ingestion/h2h/batch'),
        ]
    },
    'Backtesting': {
        'endpoints': [
            ('GET', '/probabilities/saved-results/all'),
            ('GET', '/probabilities/validation/export-status'),
        ]
    },
}

class FrontendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None) -> tuple:
        """Test endpoint with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Replace placeholders
        url = url.replace('{jackpot_id}', 'TEST-JACKPOT')
        url = url.replace('{id}', '1')
        
        try:
            if method == 'GET':
                response = self.session.get(url, timeout=5)
            elif method == 'POST':
                response = self.session.post(url, json=data or {}, timeout=5)
            elif method == 'PUT':
                response = self.session.put(url, json=data or {}, timeout=5)
            elif method == 'DELETE':
                response = self.session.delete(url, timeout=5)
            else:
                return False, f"Unknown method: {method}"
            
            # Accept 200, 201, 404 (not found is OK for some endpoints)
            if response.status_code in [200, 201]:
                return True, "OK"
            elif response.status_code == 404:
                return None, "Not found (may be expected)"
            else:
                return False, f"Status {response.status_code}: {response.text[:100]}"
        except requests.exceptions.ConnectionError:
            return False, "Backend not running"
        except Exception as e:
            return False, str(e)
    
    def test_page(self, page_name: str, endpoints: List[tuple]):
        """Test all endpoints for a page"""
        print(f"\nTesting page: {page_name}")
        print("-" * 60)
        
        page_passed = 0
        page_failed = 0
        page_warnings = 0
        
        for method, endpoint in endpoints:
            success, message = self.test_endpoint(method, endpoint)
            
            if success is True:
                print(f"  [PASS] {method} {endpoint}")
                page_passed += 1
                self.results['passed'].append(f"{page_name}: {method} {endpoint}")
            elif success is None:
                print(f"  [WARN] {method} {endpoint} - {message}")
                page_warnings += 1
                self.results['warnings'].append(f"{page_name}: {method} {endpoint} - {message}")
            else:
                print(f"  [FAIL] {method} {endpoint} - {message}")
                page_failed += 1
                self.results['failed'].append(f"{page_name}: {method} {endpoint} - {message}")
        
        return page_passed, page_failed, page_warnings
    
    def run_all_tests(self):
        """Run tests for all pages"""
        print("="*80)
        print("FRONTEND INTEGRATION TEST")
        print("="*80)
        print(f"API Base URL: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        total_warnings = 0
        
        for page_name, page_config in FRONTEND_PAGES.items():
            passed, failed, warnings = self.test_page(page_name, page_config['endpoints'])
            total_passed += passed
            total_failed += failed
            total_warnings += warnings
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Passed: {total_passed}")
        print(f"Total Failed: {total_failed}")
        print(f"Total Warnings: {total_warnings}")
        
        if self.results['failed']:
            print("\nFAILED ENDPOINTS:")
            for fail in self.results['failed']:
                print(f"  - {fail}")
        
        print("="*80)
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'passed': total_passed,
                'failed': total_failed,
                'warnings': total_warnings
            },
            'results': self.results
        }
        
        report_file = f"frontend_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_file}")
        
        return total_failed == 0


if __name__ == '__main__':
    tester = FrontendTester(API_BASE_URL)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

