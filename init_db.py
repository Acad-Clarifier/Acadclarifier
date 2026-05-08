#!/usr/bin/env python3
"""Initialize the SQLite database for local development"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 70)
print("INITIALIZING SQLITE DATABASE")
print("=" * 70)

import os
os.makedirs(ROOT_DIR / "data", exist_ok=True)

db_path = ROOT_DIR / "data" / "acadclarifier.db"
print(f"\n✓ Database: {db_path}")

try:
    # Create Flask app and initialize database
    from flask import Flask
    from apps.backend.config import Config
    from apps.backend.db import db
    from apps.backend.models import Book  # Import to register models
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        print("✓ Creating database tables...")
        db.create_all()
        print("  ✅ Database tables created successfully!")
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ Database is ready!")
print("=" * 70)
print("\nNext steps:")
print("  1. Stop any running backend (Ctrl+C)")
print("  2. Restart backend: python -m apps.backend.server")
print("  3. Browser should now load library without errors")


