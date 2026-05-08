#!/usr/bin/env python3
"""Test CORS headers from Flask backend"""

import requests
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 70)
print("TESTING: Backend CORS Headers")
print("=" * 70)

# Test 1: Health endpoint
print("\n[1/3] Testing /health endpoint for CORS headers...")
try:
    response = requests.get('http://localhost:5000/health')
    print(f"  Status: {response.status_code}")
    print(f"  Headers:")
    cors_header = response.headers.get('Access-Control-Allow-Origin')
    for key, value in response.headers.items():
        if key.lower().startswith('access-control'):
            print(f"    {key}: {value}")
    
    if cors_header:
        print(f"  ✅ CORS header present: {cors_header}")
    else:
        print(f"  ❌ CORS header MISSING!")
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 2: /library endpoint
print("\n[2/3] Testing /library endpoint for CORS headers...")
try:
    response = requests.get('http://localhost:5000/library?page=1&page_size=10')
    print(f"  Status: {response.status_code}")
    cors_header = response.headers.get('Access-Control-Allow-Origin')
    for key, value in response.headers.items():
        if key.lower().startswith('access-control'):
            print(f"    {key}: {value}")
    
    if cors_header:
        print(f"  ✅ CORS header present: {cors_header}")
    else:
        print(f"  ❌ CORS header MISSING!")
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 3: OPTIONS preflight
print("\n[3/3] Testing OPTIONS preflight for CORS...")
try:
    response = requests.options(
        'http://localhost:5000/ask',
        headers={
            'Origin': 'http://localhost:8501',
            'Access-Control-Request-Method': 'POST',
        }
    )
    print(f"  Status: {response.status_code}")
    for key, value in response.headers.items():
        if key.lower().startswith('access-control'):
            print(f"    {key}: {value}")
    
    if response.headers.get('Access-Control-Allow-Origin'):
        print(f"  ✅ Preflight response valid")
    else:
        print(f"  ⚠️  Preflight might not be working correctly")
        
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 70)
print("NEXT: Restart backend with new CORS config:")
print("  python -m apps.backend.server")
print("=" * 70)
