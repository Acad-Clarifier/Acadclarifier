#!/usr/bin/env python3
"""Test script to verify end-to-end pipeline connectivity"""

import sys
import json
from pathlib import Path

# Add paths
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

RETRIEVAL_DIR = ROOT_DIR / "services" / "retrieval-local" / "scripts"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

print("=" * 70)
print("TESTING: Complete Frontend-Backend Pipeline")
print("=" * 70)

# Test 1: Import backend modules
print("\n✓ Test 1: Import backend modules")
try:
    from apps.backend.local_retrieval_bridge import run_local_retrieval_pipeline
    print("  ✅ local_retrieval_bridge imported successfully")
except Exception as e:
    print(f"  ❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Import retrieval orchestrator
print("\n✓ Test 2: Import runtime orchestrator")
try:
    import runtime_orchestrator
    print("  ✅ runtime_orchestrator imported successfully")
except Exception as e:
    print(f"  ❌ Failed to import: {e}")
    sys.exit(1)

# Test 3: Check function exists
print("\n✓ Test 3: Check run_local_retrieval_pipeline function")
try:
    assert hasattr(runtime_orchestrator, 'run_local_retrieval_pipeline')
    print("  ✅ run_local_retrieval_pipeline function exists")
except AssertionError:
    print("  ❌ Function not found in module")
    sys.exit(1)

# Test 4: Verify embedding data exists
print("\n✓ Test 4: Check for book embeddings/chromadb data")
embeddings_dir = ROOT_DIR / "services" / "retrieval-local" / "outputs" / "embeddings_output"
if embeddings_dir.exists():
    books = [d.name for d in embeddings_dir.iterdir() if d.is_dir()]
    print(f"  ✅ Found {len(books)} book collections: {books}")
else:
    print(f"  ⚠️  Embeddings directory not found: {embeddings_dir}")
    print("    (This will cause retrieval to fail)")

# Test 5: Check ChromaDB data files
print("\n✓ Test 5: Check ChromaDB storage files")
chroma_dir = ROOT_DIR / "services" / "retrieval-local" / "outputs"
if chroma_dir.exists():
    chroma_files = list(chroma_dir.glob("**/chroma.sqlite3"))
    print(f"  ✅ Found {len(chroma_files)} ChromaDB files")
    for f in chroma_files[:5]:
        print(f"    - {f.relative_to(ROOT_DIR)}")
else:
    print(f"  ❌ Output directory not found: {chroma_dir}")

# Test 6: Attempt a retrieval call (without actually running it)
print("\n✓ Test 6: Test retrieval function signature")
try:
    import inspect
    
    # Get signature
    sig = inspect.signature(run_local_retrieval_pipeline)
    params = list(sig.parameters.keys())
    
    print(f"  ✅ Function signature: run_local_retrieval_pipeline({', '.join(params)})")
    print(f"  Parameters: query_text, book_ref, query_id, request_metadata, api_key, save_artifacts")
    
except Exception as e:
    print(f"  ❌ Could not inspect function: {e}")

# Test 7: Validate .env configuration
print("\n✓ Test 7: Check environment configuration")
try:
    from dotenv import load_dotenv
    import os
    
    env_path = RETRIEVAL_DIR / ".env"
    if not env_path.exists():
        env_path = ROOT_DIR / "services" / "retrieval-local" / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        api_key = os.getenv('GEMINI_API_KEY', '')
        if api_key:
            masked_key = api_key[:10] + '*' * (len(api_key) - 20) + api_key[-10:]
            print(f"  ✅ GEMINI_API_KEY found: {masked_key}")
        else:
            print(f"  ⚠️  GEMINI_API_KEY not set in {env_path}")
    else:
        print(f"  ⚠️  .env file not found at {env_path}")
        
except Exception as e:
    print(f"  ⚠️  Could not load env: {e}")

# Test 8: Test dependencies
print("\n✓ Test 8: Verify critical dependencies")
dependencies = {
    'chromadb': 'ChromaDB (vector store)',
    'sentence_transformers': 'SentenceTransformers (embeddings)',
    'google.generativeai': 'Google Generative AI (Gemini)',
    'flask': 'Flask (web framework)',
    'flask_cors': 'Flask-CORS',
}

for module, description in dependencies.items():
    try:
        __import__(module)
        print(f"  ✅ {description}")
    except ImportError:
        print(f"  ❌ {description} - NOT INSTALLED")

print("\n" + "=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
print("\nNext step: Run the browser diagnostic tool:")
print("  1. Open http://localhost:8501 in your browser")
print("  2. Open Developer Tools (F12)")
print("  3. Go to Console tab")
print("  4. Run: testBackendConnection()")
print("\nOr test directly:")
print(f"  python -c \"import sys; sys.path.insert(0, '{RETRIEVAL_DIR}')\"")
print(f"  python -c \"from runtime_orchestrator import run_local_retrieval_pipeline; print('Pipeline ready!')\"")
