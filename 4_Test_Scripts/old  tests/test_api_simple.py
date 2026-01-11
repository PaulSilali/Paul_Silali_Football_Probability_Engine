import requests
api_key = 'b41227796150918ad901f64b9bdf3b76'
print('=' * 60)
print('API-Football API Key Test')
print('=' * 60)
print(f'Testing API Key: {api_key[:10]}...{api_key[-4:]}')
print()

url = 'https://v3.football.api-sports.io/leagues'
headers = {'x-apisports-key': api_key}

try:
    r = requests.get(url, headers=headers, timeout=30)
    print(f'Status Code: {r.status_code}')
    print(f'Rate Limit Remaining: {r.headers.get("X-RateLimit-Remaining", "N/A")}')
    print(f'Daily Limit Remaining: {r.headers.get("x-ratelimit-requests-remaining", "N/A")}')
    print()
    
    if r.status_code == 200:
        data = r.json()
        leagues = len(data.get('response', []))
        print(f'✓ API Key is VALID!')
        print(f'✓ Retrieved {leagues} leagues')
        print()
        print('Sample leagues:')
        for i, league in enumerate(data['response'][:5], 1):
            name = league.get('league', {}).get('name', 'N/A')
            country = league.get('country', {}).get('name', 'N/A')
            print(f'  {i}. {name} ({country})')
        print()
        print('=' * 60)
        print('✓ TEST PASSED - API Key is working!')
    elif r.status_code == 401:
        print('❌ API Key is INVALID or EXPIRED')
        print('=' * 60)
        print('❌ TEST FAILED')
    elif r.status_code == 403:
        print('❌ API Key is FORBIDDEN')
        print('=' * 60)
        print('❌ TEST FAILED')
    elif r.status_code == 429:
        print('⚠ Rate Limit EXCEEDED')
        print('=' * 60)
        print('⚠ TEST INCONCLUSIVE - Try again later')
    else:
        print(f'❌ Unexpected status: {r.status_code}')
        print(f'Response: {r.text[:200]}')
        print('=' * 60)
        print('❌ TEST FAILED')
except Exception as e:
    print(f'❌ ERROR: {e}')
    print('=' * 60)
    print('❌ TEST FAILED')

