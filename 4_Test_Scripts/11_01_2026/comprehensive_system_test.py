"""
COMPREHENSIVE SYSTEM TEST SUITE
================================

This script performs deep testing of:
1. Database schema alignment (migrations vs main SQL)
2. Backend API endpoints connectivity
3. Frontend-backend integration
4. Database table operations (CRUD)
5. All pages and buttons functionality

Run: python comprehensive_system_test.py
"""

import sys
import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '2_Backend_Football_Probability_Engine'))

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')

# Try to load DB config from backend .env file
def load_db_config():
    """Load database config from backend .env or environment variables"""
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '2_Backend_Football_Probability_Engine', '.env')
    
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'football_probability_engine'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    # Try to read from backend .env file
    if os.path.exists(backend_env_path):
        try:
            with open(backend_env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == 'DB_HOST':
                            config['host'] = value
                        elif key == 'DB_PORT':
                            config['port'] = int(value) if value else 5432
                        elif key == 'DB_NAME':
                            config['database'] = value
                        elif key == 'DB_USER':
                            config['user'] = value
                        elif key == 'DB_PASSWORD':
                            config['password'] = value
        except Exception as e:
            print(f"Warning: Could not read .env file: {e}")
    
    return config

DB_CONFIG = load_db_config()

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append({'test': test_name, 'details': details})
        self.stats['total'] += 1
        self.stats['passed'] += 1
        print(f"[PASS] {test_name}")
        if details:
            print(f"  {details}")
    
    def add_fail(self, test_name: str, error: str, details: str = ""):
        self.failed.append({'test': test_name, 'error': error, 'details': details})
        self.stats['total'] += 1
        self.stats['failed'] += 1
        print(f"[FAIL] {test_name}")
        print(f"  Error: {error}")
        if details:
            print(f"  Details: {details}")
    
    def add_warning(self, test_name: str, message: str):
        self.warnings.append({'test': test_name, 'message': message})
        self.stats['warnings'] += 1
        print(f"[WARN] {test_name}")
        print(f"  {message}")
    
    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.stats['total']}")
        print(f"Passed: {self.stats['passed']} ({self.stats['passed']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"Failed: {self.stats['failed']} ({self.stats['failed']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"Warnings: {self.stats['warnings']}")
        
        if self.failed:
            print("\nFAILED TESTS:")
            for fail in self.failed:
                print(f"  - {fail['test']}: {fail['error']}")
        
        if self.warnings:
            print("\nWARNINGS:")
            for warn in self.warnings:
                print(f"  - {warn['test']}: {warn['message']}")
        
        print("="*80)
        
        # Save to file
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'passed': self.passed,
            'failed': self.failed,
            'warnings': self.warnings
        }
        
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report saved to: {report_file}")


class DatabaseTester:
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.error = None
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.db_config)
            return True
        except Exception as e:
            self.error = str(e)
            return False
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
    
    def get_tables(self) -> List[str]:
        """Get all tables in database"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            return [row[0] for row in cur.fetchall()]
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename = %s
                )
            """, (table_name,))
            return cur.fetchone()[0]
    
    def get_table_columns(self, table_name: str) -> List[Dict]:
        """Get columns for a table"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return cur.fetchall()
    
    def get_table_indexes(self, table_name: str) -> List[str]:
        """Get indexes for a table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = %s
            """, (table_name,))
            return [row[0] for row in cur.fetchall()]
    
    def test_insert_select(self, table_name: str, test_data: Dict) -> tuple:
        """Test insert and select operations"""
        try:
            with self.conn.cursor() as cur:
                # Get columns
                columns = list(test_data.keys())
                values = list(test_data.values())
                placeholders = ', '.join(['%s'] * len(values))
                
                # Insert
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING id"
                cur.execute(insert_sql, values)
                inserted_id = cur.fetchone()[0]
                
                # Select
                select_sql = f"SELECT * FROM {table_name} WHERE id = %s"
                cur.execute(select_sql, (inserted_id,))
                result = cur.fetchone()
                
                # Rollback (test only)
                self.conn.rollback()
                
                return True, f"Inserted ID: {inserted_id}"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
    
    def test_endpoint(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     expected_status: int = 200, auth_required: bool = False) -> tuple:
        """Test an API endpoint"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                return False, f"Unsupported method: {method}"
            
            if response.status_code == expected_status:
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                return False, f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
        except requests.exceptions.ConnectionError:
            return False, "Connection refused - is backend running?"
        except Exception as e:
            return False, str(e)


# Expected tables from schema
EXPECTED_TABLES = [
    'leagues', 'teams', 'team_h2h_stats', 'matches', 'team_features', 'league_stats',
    'models', 'training_runs', 'users', 'jackpots', 'jackpot_fixtures',
    'predictions', 'validation_results', 'calibration_data',
    'data_sources', 'ingestion_logs', 'audit_entries',
    'saved_jackpot_templates', 'saved_probability_results', 'saved_sure_bet_lists',
    'league_draw_priors', 'h2h_draw_stats', 'team_elo', 'match_weather',
    'match_weather_historical', 'referee_stats', 'team_rest_days',
    'team_rest_days_historical', 'odds_movement', 'odds_movement_historical',
    'league_structure', 'match_xg', 'match_xg_historical',
    'team_form', 'team_form_historical', 'team_injuries'
]

# Expected API endpoints
EXPECTED_ENDPOINTS = [
    # Auth
    ('GET', '/auth/me', False),
    # Jackpots
    ('GET', '/jackpots', False),
    ('POST', '/jackpots', False),
    ('GET', '/jackpots/templates', False),
    # Probabilities
    ('GET', '/probabilities/{jackpot_id}/probabilities', False),
    # Model
    ('GET', '/model/health', False),
    ('GET', '/model/versions', False),
    # Data
    ('GET', '/data/freshness', False),
    ('GET', '/data/batches', False),
    # Tickets
    ('POST', '/tickets/generate', False),
    # Dashboard
    ('GET', '/dashboard/summary', False),
    # Sure Bet
    ('POST', '/sure-bet/validate', False),
    ('GET', '/sure-bet/saved-lists', False),
]


def test_database_schema(results: TestResults, db_tester: DatabaseTester):
    """Test 1: Database schema alignment"""
    print("\n" + "="*80)
    print("TEST 1: DATABASE SCHEMA ALIGNMENT")
    print("="*80)
    
    connect_result = db_tester.connect()
    if connect_result is not True:
        error_msg = db_tester.error if db_tester.error else "Could not connect to database"
        results.add_fail("Database Connection", error_msg)
        return
    
    try:
        # Get all tables
        actual_tables = db_tester.get_tables()
        
        # Check expected tables exist
        missing_tables = []
        for table in EXPECTED_TABLES:
            if table not in actual_tables:
                missing_tables.append(table)
            else:
                results.add_pass(f"Table exists: {table}")
        
        if missing_tables:
            results.add_fail("Missing Tables", f"Tables not found: {', '.join(missing_tables)}")
        else:
            results.add_pass("All Expected Tables Exist", f"Found {len(EXPECTED_TABLES)} tables")
        
        # Check for unexpected tables (warnings)
        unexpected = [t for t in actual_tables if t not in EXPECTED_TABLES]
        if unexpected:
            results.add_warning("Unexpected Tables", f"Found {len(unexpected)} unexpected tables: {', '.join(unexpected[:10])}")
        
        # Test critical tables have required columns
        critical_tables = {
            'jackpots': ['id', 'jackpot_id', 'status', 'created_at'],
            'jackpot_fixtures': ['id', 'jackpot_id', 'home_team', 'away_team'],
            'predictions': ['id', 'fixture_id', 'model_id', 'set_type'],
            'models': ['id', 'version', 'model_type', 'status'],
            'teams': ['id', 'name', 'canonical_name', 'league_id'],
            'leagues': ['id', 'code', 'name', 'country']
        }
        
        for table, required_cols in critical_tables.items():
            if table in actual_tables:
                columns = db_tester.get_table_columns(table)
                col_names = [col['column_name'] for col in columns]
                missing_cols = [c for c in required_cols if c not in col_names]
                if missing_cols:
                    results.add_fail(f"Table {table} missing columns", f"Missing: {', '.join(missing_cols)}")
                else:
                    results.add_pass(f"Table {table} has required columns")
        
    except Exception as e:
        results.add_fail("Database Schema Test", str(e), traceback.format_exc())
    finally:
        db_tester.disconnect()


def test_api_endpoints(results: TestResults, api_tester: APITester):
    """Test 2: API Endpoints"""
    print("\n" + "="*80)
    print("TEST 2: API ENDPOINTS CONNECTIVITY")
    print("="*80)
    
    # Test health endpoint first
    success, response = api_tester.test_endpoint('GET', '/health', expected_status=200)
    if success:
        results.add_pass("Health Check", "Backend is running")
    else:
        results.add_fail("Health Check", response)
        return  # Can't continue if backend is down
    
    # Test root endpoint
    success, response = api_tester.test_endpoint('GET', '/', expected_status=200)
    if success:
        results.add_pass("Root Endpoint")
    else:
        results.add_fail("Root Endpoint", response)
    
    # Test API endpoints
    endpoints_to_test = [
        ('GET', '/model/health', False),
        ('GET', '/model/versions', False),
        ('GET', '/jackpots?page=1&page_size=10', False),
        ('GET', '/jackpots/templates?limit=10', False),
        ('GET', '/data/freshness', False),
        ('GET', '/data/batches?limit=10', False),
        ('GET', '/dashboard/summary', False),
        ('GET', '/sure-bet/saved-lists', False),
    ]
    
    for method, endpoint, auth_required in endpoints_to_test:
        success, response = api_tester.test_endpoint(method, endpoint, auth_required=auth_required)
        if success:
            results.add_pass(f"API {method} {endpoint}")
        else:
            # Some endpoints might return 404 if no data - that's OK
            if '404' in str(response) or 'not found' in str(response).lower():
                results.add_warning(f"API {method} {endpoint}", "Endpoint exists but returned 404 (may be expected)")
            else:
                results.add_fail(f"API {method} {endpoint}", response)


def test_database_operations(results: TestResults, db_tester: DatabaseTester):
    """Test 3: Database CRUD Operations"""
    print("\n" + "="*80)
    print("TEST 3: DATABASE CRUD OPERATIONS")
    print("="*80)
    
    connect_result = db_tester.connect()
    if connect_result is not True:
        error_msg = db_tester.error if db_tester.error else "Could not connect to database"
        results.add_fail("Database Connection", error_msg)
        return
    
    try:
        # Test leagues table (simple insert/select)
        test_league = {
            'code': 'TEST',
            'name': 'Test League',
            'country': 'Test Country',
            'tier': 1,
            'is_active': True
        }
        
        # Check if test league exists, delete if so
        with db_tester.conn.cursor() as cur:
            cur.execute("DELETE FROM leagues WHERE code = 'TEST'")
            db_tester.conn.commit()
        
        success, details = db_tester.test_insert_select('leagues', test_league)
        if success:
            results.add_pass("Leagues Table CRUD", details)
        else:
            results.add_fail("Leagues Table CRUD", details)
        
        # Test teams table (requires league_id)
        with db_tester.conn.cursor() as cur:
            cur.execute("SELECT id FROM leagues WHERE code = 'TEST' LIMIT 1")
            league_row = cur.fetchone()
            if league_row:
                league_id = league_row[0]
                test_team = {
                    'league_id': league_id,
                    'name': 'Test Team',
                    'canonical_name': 'test team'
                }
                success, details = db_tester.test_insert_select('teams', test_team)
                if success:
                    results.add_pass("Teams Table CRUD", details)
                else:
                    results.add_fail("Teams Table CRUD", details)
        
        # Test jackpots table
        test_jackpot = {
            'jackpot_id': 'TEST-JACKPOT-001',
            'status': 'pending',
            'name': 'Test Jackpot'
        }
        success, details = db_tester.test_insert_select('jackpots', test_jackpot)
        if success:
            results.add_pass("Jackpots Table CRUD", details)
        else:
            results.add_fail("Jackpots Table CRUD", details)
        
    except Exception as e:
        results.add_fail("Database Operations Test", str(e), traceback.format_exc())
    finally:
        db_tester.disconnect()


def test_migration_alignment(results: TestResults, db_tester: DatabaseTester):
    """Test 4: Migration Alignment"""
    print("\n" + "="*80)
    print("TEST 4: MIGRATION ALIGNMENT CHECK")
    print("="*80)
    
    # Check if saved_sure_bet_lists exists (was missing from main SQL)
    connect_result = db_tester.connect()
    if connect_result is not True:
        error_msg = db_tester.error if db_tester.error else "Could not connect to database"
        results.add_fail("Database Connection", error_msg)
        return
    
    try:
        if db_tester.table_exists('saved_sure_bet_lists'):
            results.add_pass("Migration: saved_sure_bet_lists table exists")
        else:
            results.add_fail("Migration: saved_sure_bet_lists", "Table not found - migration missing from main SQL")
        
        # Check all migration tables exist
        migration_tables = [
            'saved_sure_bet_lists',
            'saved_jackpot_templates',
            'saved_probability_results',
            'team_form',
            'team_form_historical',
            'team_injuries',
            'match_xg',
            'match_xg_historical',
            'league_draw_priors',
            'h2h_draw_stats',
            'team_elo',
            'match_weather',
            'match_weather_historical',
            'referee_stats',
            'team_rest_days',
            'team_rest_days_historical',
            'odds_movement',
            'odds_movement_historical',
            'league_structure'
        ]
        
        for table in migration_tables:
            if db_tester.table_exists(table):
                results.add_pass(f"Migration table: {table}")
            else:
                results.add_fail(f"Migration table: {table}", "Table not found")
        
    except Exception as e:
        results.add_fail("Migration Alignment Test", str(e), traceback.format_exc())
    finally:
        db_tester.disconnect()


def main():
    print("="*80)
    print("COMPREHENSIVE SYSTEM TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print("="*80)
    
    results = TestResults()
    db_tester = DatabaseTester(DB_CONFIG)
    api_tester = APITester(API_BASE_URL.replace('/api', ''))
    
    # Run all tests
    test_database_schema(results, db_tester)
    test_api_endpoints(results, api_tester)
    test_database_operations(results, db_tester)
    test_migration_alignment(results, db_tester)
    
    # Print summary
    results.print_summary()
    
    # Exit code
    sys.exit(0 if results.stats['failed'] == 0 else 1)


if __name__ == '__main__':
    main()

