import sqlite3
import os

print(f"Current working directory: {os.getcwd()}")
db_path = "library.db"

# Remove existing database if it exists
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Removed existing database file: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print(f"✓ Created new database: {db_path}")
except Exception as e:
    print(f"✗ Failed to create database: {e}")
    exit(1)

try:
    cur.execute("""
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT,
    title TEXT,
    author TEXT,
    category TEXT,
    year INTEGER,
    summary TEXT,
    processed BOOLEAN DEFAULT 0
)
""")
    conn.commit()
    print("✓ Successfully created 'books' table with schema")
except Exception as e:
    print(f"✗ Failed to create table: {e}")
    conn.rollback()
finally:
    conn.close()
    print("✓ Database initialization complete")